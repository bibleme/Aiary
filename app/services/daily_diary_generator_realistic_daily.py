# app/services/daily_diary_generator_realistic_daily.py

from __future__ import annotations

import asyncio
import gc
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from app.config import settings


# ============================
# Global model cache
# ============================

_tokenizer = None
_model = None
_device = None
_model_load_lock = asyncio.Lock()


# ============================
# Realistic daily inference constants
# ============================

TIME_MARKERS = [
    "아침", "오전", "점심", "낮", "낮잠", "오후", "저녁", "밤",
    "하원", "등원", "집에 와", "집에 돌아", "돌아와", "돌아오",
    "씻고", "잠들기 전", "일어나",
]

CLICHE_PATTERNS = [
    "소소한 순간",
    "작은 순간들이 모여",
    "마음이 놓였다",
    "마음이 놓이는",
    "행복한 하루",
    "즐거운 시간을 보냈다",
    "즐거운 하루",
    "앞으로도",
    "참 소중",
    "소중한 기억",
    "뿌듯했다",
    "흐뭇했다",
    "특별한 하루",
    "특별하게 느껴졌다",
    "오래 기억에 남는 날",
]

STOPWORDS = {"오늘", "아이", "아기", "우리", "모습", "하루", "시간", "정말", "조금"}

WORD_RE = re.compile(r"[가-힣]{2,}|[A-Za-z]{2,}|[0-9]+")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|\n+")


@dataclass(frozen=True)
class DecodeConfig:
    name: str
    max_new_tokens: int
    min_new_tokens: int
    num_beams: int
    no_repeat_ngram_size: int
    repetition_penalty: float
    length_penalty: float


# ============================
# Device / cleanup
# ============================

def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def cleanup_torch() -> None:
    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    if torch.backends.mps.is_available():
        try:
            torch.mps.empty_cache()
        except Exception:
            pass


# ============================
# Text utilities
# ============================

def normalize_space(text: Any) -> str:
    text = str(text or "").replace("\u200b", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_one_line(text: Any) -> str:
    text = normalize_space(text)
    return text.strip(" -•\t")


def dedupe_keep_order(items: Iterable[Any], max_items: int = 10) -> List[str]:
    out: List[str] = []
    seen = set()

    for item in items:
        text = clean_one_line(item)
        key = re.sub(r"\s+", "", text)

        if not text or key in seen:
            continue

        seen.add(key)
        out.append(text)

        if len(out) >= max_items:
            break

    return out


def sentence_hint(count: int) -> str:
    if count <= 2:
        return "2~3문장"
    if count <= 5:
        return "3~5문장"
    if count <= 8:
        return "5~7문장"
    return "6~9문장"


def sentence_bounds(count: int) -> Dict[str, int]:
    if count <= 2:
        return {"target_min": 2, "target_max": 3, "hard_max": 4}
    if count <= 5:
        return {"target_min": 3, "target_max": 5, "hard_max": 6}
    if count <= 8:
        return {"target_min": 5, "target_max": 7, "hard_max": 8}
    return {"target_min": 6, "target_max": 9, "hard_max": 10}


def build_model_input(one_lines: List[str]) -> str:
    lines = dedupe_keep_order(one_lines)
    bullets = "\n".join(f"- {line}" for line in lines)
    return f"[문장수: {sentence_hint(len(lines))}]\n[한줄일기]\n{bullets}"


def split_sentences(text: str) -> List[str]:
    text = normalize_space(text)
    return [s.strip() for s in SENT_SPLIT_RE.split(text) if s.strip()]


def count_sentences(text: str) -> int:
    return len(split_sentences(text))


def ensure_sentence_end(text: str) -> str:
    text = normalize_space(text)

    if not text:
        return ""

    if re.search(r"[.!?。！？]\s*$", text):
        return text

    last = max(
        text.rfind("."),
        text.rfind("!"),
        text.rfind("?"),
        text.rfind("。"),
        text.rfind("！"),
        text.rfind("？"),
    )

    if last >= 20:
        return text[: last + 1].strip()

    return text + "."


def fix_model_artifacts(text: str) -> str:
    text = normalize_space(text)
    text = text.replace("내가관", "왕관")
    text = text.replace("주토피아와 주토피아", "주토피아")
    text = text.replace("반짝 반짝", "반짝반짝")
    return text


def norm_sentence_for_dup(sentence: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", sentence or "")


def cut_after_duplicate_sentence(text: str) -> str:
    seen = set()
    kept = []

    for sentence in split_sentences(text):
        key = norm_sentence_for_dup(sentence)

        if len(key) >= 8 and key in seen:
            break

        if len(key) >= 8:
            seen.add(key)

        kept.append(sentence)

    return ensure_sentence_end(" ".join(kept))


def has_repeated_ngram(sentence: str, n: int = 4, min_repeats: int = 2) -> bool:
    toks = WORD_RE.findall(sentence or "")

    if len(toks) < n * 2:
        return False

    counts: Dict[Any, int] = {}

    for i in range(len(toks) - n + 1):
        gram = tuple(toks[i: i + n])
        counts[gram] = counts.get(gram, 0) + 1

        if counts[gram] >= min_repeats:
            return True

    return False


def drop_sentences_with_repeated_ngram(text: str) -> str:
    kept = [s for s in split_sentences(text) if not has_repeated_ngram(s)]
    return ensure_sentence_end(" ".join(kept))


def has_cliche(text: str) -> bool:
    return any(pattern in (text or "") for pattern in CLICHE_PATTERNS)


def drop_cliche_sentences(text: str, one_line_count: int) -> str:
    bounds = sentence_bounds(one_line_count)
    sentences = split_sentences(text)

    kept = [s for s in sentences if not has_cliche(s)]

    if len(kept) >= bounds["target_min"]:
        return ensure_sentence_end(" ".join(kept))

    return ensure_sentence_end(" ".join(sentences))


def postprocess_output(text: str, one_line_count: int) -> str:
    bounds = sentence_bounds(one_line_count)

    text = fix_model_artifacts(text)
    text = ensure_sentence_end(text)
    text = drop_sentences_with_repeated_ngram(text)
    text = cut_after_duplicate_sentence(text)
    text = drop_cliche_sentences(text, one_line_count)

    text = " ".join(split_sentences(text)[: bounds["hard_max"]])
    return ensure_sentence_end(text)


# ============================
# Scoring
# ============================

def ko_words(text: str) -> List[str]:
    return re.findall(r"[가-힣]{2,}", text or "")


def content_words(text: str) -> List[str]:
    out = []
    seen = set()

    for word in ko_words(text):
        if word in STOPWORDS or word in seen:
            continue

        seen.add(word)
        out.append(word)

    return out


def coverage_score(one_lines: List[str], diary: str) -> float:
    if not one_lines:
        return 0.0

    hit = 0

    for line in one_lines:
        kws = content_words(line)[:8]

        if not kws or any(k in diary for k in kws):
            hit += 1

    return hit / max(1, len(one_lines))


def repeated_ngram_ratio(text: str, n: int = 4) -> float:
    toks = WORD_RE.findall(text or "")

    if len(toks) < n * 2:
        return 0.0

    grams = [tuple(toks[i: i + n]) for i in range(len(toks) - n + 1)]
    return 1.0 - (len(set(grams)) / max(1, len(grams)))


def duplicate_sentence_ratio(text: str) -> float:
    sents = [norm_sentence_for_dup(s) for s in split_sentences(text)]
    sents = [s for s in sents if len(s) >= 8]

    if not sents:
        return 0.0

    return 1.0 - (len(set(sents)) / len(sents))


def unsupported_time_markers(one_lines: List[str], diary: str) -> List[str]:
    source = " ".join(one_lines)
    return [marker for marker in TIME_MARKERS if marker in diary and marker not in source]


def score_output(one_lines: List[str], diary: str) -> Dict[str, Any]:
    unsupported = unsupported_time_markers(one_lines, diary)

    return {
        "sent_count": count_sentences(diary),
        "coverage": round(coverage_score(one_lines, diary), 4),
        "has_cliche": has_cliche(diary),
        "repeated_ngram_ratio": round(repeated_ngram_ratio(diary), 4),
        "duplicate_sentence_ratio": round(duplicate_sentence_ratio(diary), 4),
        "unsupported_time_markers": unsupported,
        "unsupported_time_count": len(unsupported),
    }


def candidate_score(one_lines: List[str], text: str) -> float:
    metrics = score_output(one_lines, text)
    bounds = sentence_bounds(len(one_lines))

    score = 100.0
    score -= (1.0 - metrics["coverage"]) * 35.0
    score -= metrics["repeated_ngram_ratio"] * 40.0
    score -= metrics["duplicate_sentence_ratio"] * 45.0
    score -= metrics["unsupported_time_count"] * 30.0

    if metrics["has_cliche"]:
        score -= 24.0

    if metrics["sent_count"] < bounds["target_min"]:
        score -= (bounds["target_min"] - metrics["sent_count"]) * 8.0

    if metrics["sent_count"] > bounds["target_max"]:
        score -= (metrics["sent_count"] - bounds["target_max"]) * 7.0

    if not text:
        score -= 100.0

    return round(score, 4)


# ============================
# Decoding
# ============================

def decode_configs(one_line_count: int) -> List[DecodeConfig]:
    bounds = sentence_bounds(one_line_count)

    base_min_new_tokens = 20
    base_max_new_tokens = 300
    base_num_beams = 4
    base_no_repeat_ngram_size = 4
    base_repetition_penalty = 1.18

    token_floor = max(base_min_new_tokens, bounds["target_min"] * 18)
    token_mid = max(base_max_new_tokens, bounds["hard_max"] * 42)

    return [
        DecodeConfig(
            name="grounded_short",
            max_new_tokens=max(token_mid - 35, token_floor + 30),
            min_new_tokens=token_floor,
            num_beams=max(3, base_num_beams),
            no_repeat_ngram_size=base_no_repeat_ngram_size,
            repetition_penalty=max(base_repetition_penalty, 1.20),
            length_penalty=0.58,
        ),
        DecodeConfig(
            name="balanced",
            max_new_tokens=token_mid,
            min_new_tokens=token_floor,
            num_beams=max(4, base_num_beams),
            no_repeat_ngram_size=base_no_repeat_ngram_size,
            repetition_penalty=max(base_repetition_penalty, 1.16),
            length_penalty=0.72,
        ),
        DecodeConfig(
            name="coverage",
            max_new_tokens=token_mid + 30,
            min_new_tokens=token_floor,
            num_beams=max(4, base_num_beams),
            no_repeat_ngram_size=base_no_repeat_ngram_size,
            repetition_penalty=max(base_repetition_penalty, 1.14),
            length_penalty=0.86,
        ),
    ]


def generate_with_config(
    model: Any,
    tokenizer: Any,
    model_input: str,
    device: torch.device,
    cfg: DecodeConfig,
    max_src_len: int = 768,
) -> str:
    enc = tokenizer(
        model_input,
        return_tensors="pt",
        truncation=True,
        max_length=max_src_len,
    )

    enc = {k: v.to(device) for k, v in enc.items() if k != "token_type_ids"}

    with torch.inference_mode():
        out = model.generate(
            **enc,
            max_new_tokens=cfg.max_new_tokens,
            min_new_tokens=cfg.min_new_tokens,
            num_beams=cfg.num_beams,
            no_repeat_ngram_size=cfg.no_repeat_ngram_size,
            repetition_penalty=cfg.repetition_penalty,
            length_penalty=cfg.length_penalty,
            early_stopping=True,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )

    return normalize_space(tokenizer.decode(out[0], skip_special_tokens=True))


def generate_best(
    model: Any,
    tokenizer: Any,
    one_lines: List[str],
    device: torch.device,
) -> Dict[str, Any]:
    lines = dedupe_keep_order(one_lines)

    if not lines:
        raise ValueError("one_lines is empty")

    model_input = build_model_input(lines)
    candidates = []

    for cfg in decode_configs(len(lines)):
        raw = generate_with_config(model, tokenizer, model_input, device, cfg)
        text = postprocess_output(raw, len(lines))
        metrics = score_output(lines, text)

        candidates.append(
            {
                "decode_config": cfg.name,
                "decode_args": asdict(cfg),
                "text": text,
                "score": candidate_score(lines, text),
                "metrics": metrics,
            }
        )

    best = max(candidates, key=lambda c: c["score"])

    return {
        "one_lines": lines,
        "model_input": model_input,
        "diary": best["text"],
        "best": best,
        "candidates": candidates,
    }


# ============================
# Model loading
# ============================

def load_model():
    global _tokenizer, _model, _device

    if _model is not None:
        return _tokenizer, _model, _device

    cleanup_torch()

    _device = get_device()

    print("[realistic_daily] loading model from:", settings.DAILY_DIARY_MODEL_DIR, flush=True)

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

    print("[realistic_daily] model loaded successfully on device:", _device, flush=True)

    return _tokenizer, _model, _device


# ============================
# Server entrypoint
# ============================

async def generate_daily_diary_realistic_daily(one_line_diaries: List[str]) -> Dict[str, Any]:
    global _model, _tokenizer, _device

    lines = dedupe_keep_order(one_line_diaries)

    if not lines:
        raise ValueError("하루일기를 생성할 한줄일기가 없습니다.")

    if _model is None:
        async with _model_load_lock:
            if _model is None:
                load_model()

    tokenizer, model, device = _tokenizer, _model, _device
    result = generate_best(model, tokenizer, lines, device)

    return {
        "one_lines_count": len(result["one_lines"]),
        "one_lines": result["one_lines"],
        "generated_diary": result["diary"],
        "model_version": "realistic_daily_2026-05-13",
        "model_input": result["model_input"],
        "decode_config": result["best"]["decode_config"],
        "decode_score": result["best"]["score"],
        "generation_meta": {
            "best": result["best"],
            "candidates": result["candidates"],
        },
    }
