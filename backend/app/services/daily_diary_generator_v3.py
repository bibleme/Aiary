# app/services/daily_diary_generator_v3.py
import os
import re
import json
import gc
import torch

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ----------------------------
# 경로
# ----------------------------
BASE_DIR = "./"

MODEL_PATH = os.path.join(
    BASE_DIR,
    "generated/aiary_v3_hybrid_20260220_014739/models/kobart_student_round5"
)

ONE_LINE_FILE = os.path.join(BASE_DIR, "data/one_line_texts.txt")

OUTPUT_JSON = os.path.join(BASE_DIR, "outputs/generated_diary_from_one_line.json")
OUTPUT_TXT  = os.path.join(BASE_DIR, "outputs/generated_diary_from_one_line.txt")

# ----------------------------
# device
# ----------------------------
def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

DEVICE = get_device()
print("DEVICE:", DEVICE)

def cleanup_torch():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    if torch.backends.mps.is_available():
        try:
            torch.mps.empty_cache()
        except Exception:
            pass

# ----------------------------
# util
# ----------------------------
def normalize_space(s: str):
    if not s:
        return ""
    s = s.replace("\u200b", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def normalize_joined(s: str):
    if not s:
        return ""
    s = s.strip()
    s = s.replace("에서에서", "에서")
    s = s.replace("있다하다가", "있다가")
    s = s.replace("해본다하더니", "해보더니")
    s = re.sub(r"\s*을\(를\)\s*", " ", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def safe_join_one_lines(one_lines):
    return "\n".join([normalize_space(x) for x in one_lines if x and x.strip()])

# ----------------------------
# postprocess
# ----------------------------
_SENT_END = r"[.!?。！？]"
_SENT_SPLIT_RE = re.compile(rf"(?<={_SENT_END})\s+|\n+")

def split_sentences(text):
    t = normalize_space(text or "")
    if not t:
        return []
    return [x.strip() for x in _SENT_SPLIT_RE.split(t) if x.strip()]

def ensure_ends_with_sentence(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    if re.search(rf"{_SENT_END}\s*$", t):
        return t

    last = max(
        t.rfind("."), t.rfind("!"), t.rfind("?"),
        t.rfind("。"), t.rfind("！"), t.rfind("？")
    )
    if last != -1 and last >= 20:
        t = t[: last + 1].strip()
        if re.search(rf"{_SENT_END}\s*$", t):
            return t

    if len(t) >= 30:
        return (t + ".").strip()
    return t.strip()

def cut_to_max_sentences(text: str, max_sents: int = 11) -> str:
    sents = split_sentences(text)
    if len(sents) <= max_sents:
        return ensure_ends_with_sentence(" ".join(sents).strip())
    return ensure_ends_with_sentence(" ".join(sents[:max_sents]).strip())

def _norm_sent_for_dup(s: str) -> str:
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^0-9A-Za-z가-힣]", "", s)
    return s

def cut_after_duplicate_sentence(text: str, min_chars: int = 12) -> str:
    sents = split_sentences(text)
    if len(sents) <= 1:
        return ensure_ends_with_sentence(" ".join(sents).strip())

    seen = set()
    kept = []

    for s in sents:
        key = _norm_sent_for_dup(s)
        if len(key) >= min_chars:
            if key in seen:
                break
            seen.add(key)
        kept.append(s)

    return ensure_ends_with_sentence(" ".join(kept).strip())

_WORD_RE = re.compile(r"[가-힣]{1,}|[A-Za-z]{1,}|[0-9]+")

def _word_tokens(s: str):
    return _WORD_RE.findall(s or "")

def has_repeated_4gram(sentence: str, min_repeats: int = 2) -> bool:
    toks = _word_tokens(sentence)
    if len(toks) < 8:
        return False

    cnt = {}
    for i in range(len(toks) - 4 + 1):
        g = tuple(toks[i:i+4])
        cnt[g] = cnt.get(g, 0) + 1
        if cnt[g] >= min_repeats:
            return True
    return False

def drop_sentences_with_repeated_4gram(text: str) -> str:
    sents = split_sentences(text)
    if not sents:
        return ""
    kept = []
    for s in sents:
        if has_repeated_4gram(s, min_repeats=2):
            continue
        kept.append(s)
    return ensure_ends_with_sentence(" ".join(kept).strip())

def postprocess_diary(text: str, max_sents: int = 11) -> str:
    t = normalize_space(text or "")
    t = ensure_ends_with_sentence(t)
    t = drop_sentences_with_repeated_4gram(t)
    t = cut_after_duplicate_sentence(t)
    t = cut_to_max_sentences(t, max_sents=max_sents)
    t = ensure_ends_with_sentence(t)
    return t.strip()

# ----------------------------
# 입력 파일: 모든 줄 읽기
# ----------------------------
def load_all_one_lines(path):
    one_lines = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = normalize_space(line)
            if not line:
                continue
            one_lines.append(line)

    return one_lines

# ----------------------------
# inference
# ----------------------------
def generate_diary(model, tok, one_lines, max_input_length=512):
    src = normalize_joined(safe_join_one_lines(one_lines))

    enc = tok(
        src,
        return_tensors="pt",
        truncation=True,
        max_length=max_input_length
    )
    enc = {k: v.to(DEVICE) for k, v in enc.items()}
    enc.pop("token_type_ids", None)

    with torch.inference_mode():
        out = model.generate(
            **enc,
            max_new_tokens=180,
            min_new_tokens=0,
            num_beams=2,
            do_sample=False,
            early_stopping=True,
            no_repeat_ngram_size=4,
            repetition_penalty=1.10,
            length_penalty=0.85,
            eos_token_id=tok.eos_token_id,
            pad_token_id=tok.pad_token_id
        )

    raw = tok.decode(out[0], skip_special_tokens=True)
    return postprocess_diary(raw, max_sents=11)

# ----------------------------
# main
# ----------------------------
cleanup_torch()

print("loading model...")
tok = AutoTokenizer.from_pretrained(MODEL_PATH, use_fast=True)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH).to(DEVICE)
model.eval()

print("loading all one-line diaries...")
one_lines = load_all_one_lines(ONE_LINE_FILE)

print("num one_lines:", len(one_lines))
for i, x in enumerate(one_lines[:10]):
    print(f"[{i}] {x}")
if len(one_lines) > 10:
    print("...")

generated_diary = generate_diary(model, tok, one_lines)

result = {
    "one_lines_count": len(one_lines),
    "one_lines": one_lines,
    "generated_diary": generated_diary
}

# json 저장
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# txt 저장
with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
    f.write("[INPUT ONE_LINES]\n")
    for x in one_lines:
        f.write("- " + x + "\n")

    f.write("\n[GENERATED DIARY]\n")
    f.write(generated_diary + "\n")

print("\n[GENERATED DIARY]")
print(generated_diary)

print("\nsaved:")
print(OUTPUT_JSON)
print(OUTPUT_TXT)

del model
del tok
cleanup_torch()