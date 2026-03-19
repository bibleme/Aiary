import re
import gc
import torch

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from app.config import settings

# ----------------------------
# 글로벌 캐시
# ----------------------------
_tokenizer = None
_model = None
_device = None

# ----------------------------
# device
# ----------------------------
def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


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
# util (원본 유지)
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
# postprocess (원본 유지)
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
# model load (서버용 최소 수정)
# ----------------------------
def load_model():
    global _tokenizer, _model, _device

    if _model is not None:
        return _tokenizer, _model, _device

    cleanup_torch()

    _device = get_device()
    print("[v3_eval] loading model from:", settings.DAILY_DIARY_MODEL_DIR)

    _tokenizer = AutoTokenizer.from_pretrained(
        settings.DAILY_DIARY_MODEL_DIR,
        use_fast=True,
        local_files_only=True,
    )
    _model = AutoModelForSeq2SeqLM.from_pretrained(
        settings.DAILY_DIARY_MODEL_DIR,
        local_files_only=True,
    ).to(_device)

    _model.eval()
    return _tokenizer, _model, _device

# ----------------------------
# inference (원본 최대 유지)
# ----------------------------
def generate_diary(model, tok, one_lines, device, max_input_length=512):
    src = normalize_joined(safe_join_one_lines(one_lines))

    enc = tok(
        src,
        return_tensors="pt",
        truncation=True,
        max_length=max_input_length
    )
    enc = {k: v.to(device) for k, v in enc.items()}
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
# 서버/평가용 엔트리
# ----------------------------
async def generate_daily_diary_v3_eval(one_line_diaries: list[str]) -> dict:
    tok, model, device = load_model()
    generated_diary = generate_diary(model, tok, one_line_diaries, device)

    return {
        "one_lines_count": len(one_line_diaries),
        "one_lines": one_line_diaries,
        "generated_diary": generated_diary,
        "model_version": "v3_eval_original_like",
    }
