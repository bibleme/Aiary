# app/services/daily_diary_generator.py
from __future__ import annotations

import os
import re
import gc
from pathlib import Path
from typing import List, Dict

import torch
import emoji
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# -------------------------------------------------------------------
# 1) 경로 및 디바이스 설정
# -------------------------------------------------------------------
# BASE_DIR: backend 폴더를 가리킵니다.
BASE_DIR = Path(__file__).resolve().parents[2]

# ✅ LLM 담당자님이 전달해주신 최종 모델 경로 (kobart_student_round5)
MODEL_DIR = BASE_DIR / "models" / "kobart_student_round5"

# lazy-loading 을 위한 전역 변수
_tokenizer = None
_model = None
_device = None

def get_device():
    if torch.cuda.is_available(): return torch.device("cuda")
    if torch.backends.mps.is_available(): return torch.device("mps")
    return torch.device("cpu")

def cleanup_torch():
    gc.collect()
    if torch.cuda.is_available(): torch.cuda.empty_cache()
    if torch.backends.mps.is_available():
        try: torch.mps.empty_cache()
        except: pass

def _load_model_if_needed():
    """FastAPI 서버가 켜진 후 최초 1회만 모델을 로드하여 속도를 최적화합니다."""
    global _tokenizer, _model, _device

    if _model is not None and _tokenizer is not None:
        return

    if not MODEL_DIR.exists():
        raise FileNotFoundError(f"AI 모델 경로를 찾을 수 없습니다: {MODEL_DIR}")

    print("[INFO] 하루일기 AI 모델 로드 중...", flush=True)

    _device = get_device()
    _tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), use_fast=True)
    _model = AutoModelForSeq2SeqLM.from_pretrained(str(MODEL_DIR)).to(_device)
    _model.eval()

    print(f"[INFO] device = {_device}", flush=True)
    print("[INFO] AI 모델 로드 완료!", flush=True)

# -------------------------------------------------------------------
# 2) 텍스트 전처리 (v5 코드의 꼼꼼한 노이즈 제거 + 이모지 제거)
# -------------------------------------------------------------------
def _remove_emoji(text: str) -> str:
    text = emoji.replace_emoji(text, "")
    emoji_pattern = re.compile(r"[\p{Emoji}\p{Emoji_Presentation}\p{Extended_Pictographic}]", flags=re.UNICODE)
    return emoji_pattern.sub("", text)

def normalize_space(s: str):
    if not s: return ""
    s = _remove_emoji(s)
    s = s.replace("\u200b", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def normalize_joined(s: str):
    if not s: return ""
    s = s.strip().replace("에서에서", "에서").replace("있다하다가", "있다가").replace("해본다하더니", "해보더니")
    s = re.sub(r"\s*을\(를\)\s*", " ", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def safe_join_one_lines(one_lines: List[str]):
    return "\n".join([normalize_space(x) for x in one_lines if x and str(x).strip()])

# -------------------------------------------------------------------
# 3) 텍스트 후처리 (v5 코드의 핵심: AI 헛소리 및 반복 방지 필터)
# -------------------------------------------------------------------
_SENT_END = r"[.!?。！？]"
_SENT_SPLIT_RE = re.compile(rf"(?<={_SENT_END})\s+|\n+")

def split_sentences(text):
    t = normalize_space(text or "")
    if not t: return []
    return [x.strip() for x in _SENT_SPLIT_RE.split(t) if x.strip()]

def ensure_ends_with_sentence(text: str) -> str:
    if not text: return ""
    t = text.strip()
    if re.search(rf"{_SENT_END}\s*$", t): return t
    last = max(t.rfind("."), t.rfind("!"), t.rfind("?"), t.rfind("。"), t.rfind("！"), t.rfind("？"))
    if last != -1 and last >= 20:
        t = t[: last + 1].strip()
        if re.search(rf"{_SENT_END}\s*$", t): return t
    if len(t) >= 30: return (t + ".").strip()
    return t.strip()

def cut_to_max_sentences(text: str, max_sents: int = 11) -> str:
    sents = split_sentences(text)
    if len(sents) <= max_sents: return ensure_ends_with_sentence(" ".join(sents).strip())
    return ensure_ends_with_sentence(" ".join(sents[:max_sents]).strip())

def _norm_sent_for_dup(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", re.sub(r"\s+", "", s))

def cut_after_duplicate_sentence(text: str, min_chars: int = 12) -> str:
    sents = split_sentences(text)
    if len(sents) <= 1: return ensure_ends_with_sentence(" ".join(sents).strip())
    seen = set()
    kept = []
    for s in sents:
        key = _norm_sent_for_dup(s)
        if len(key) >= min_chars:
            if key in seen: break
            seen.add(key)
        kept.append(s)
    return ensure_ends_with_sentence(" ".join(kept).strip())

def has_repeated_4gram(sentence: str, min_repeats: int = 2) -> bool:
    toks = re.findall(r"[가-힣]{1,}|[A-Za-z]{1,}|[0-9]+", sentence or "")
    if len(toks) < 8: return False
    cnt = {}
    for i in range(len(toks) - 4 + 1):
        g = tuple(toks[i:i+4])
        cnt[g] = cnt.get(g, 0) + 1
        if cnt[g] >= min_repeats: return True
    return False

def drop_sentences_with_repeated_4gram(text: str) -> str:
    sents = split_sentences(text)
    kept = [s for s in sents if not has_repeated_4gram(s, min_repeats=2)]
    return ensure_ends_with_sentence(" ".join(kept).strip())

def postprocess_diary(text: str, max_sents: int = 11) -> str:
    t = normalize_space(text or "")
    t = ensure_ends_with_sentence(t)
    t = drop_sentences_with_repeated_4gram(t)
    t = cut_after_duplicate_sentence(t)
    t = cut_to_max_sentences(t, max_sents=max_sents)
    return ensure_ends_with_sentence(t).strip()

# -------------------------------------------------------------------
# 4) AI 생성 로직 및 FastAPI 비동기 래퍼
# -------------------------------------------------------------------
def _run_generation_sync(one_line_list: List[str]) -> str:
    """실제 AI 모델을 돌리는 동기 함수"""
    _load_model_if_needed()

    src = normalize_joined(safe_join_one_lines(one_line_list))
    if not src:
        raise ValueError("유효한 메모가 없습니다.")

    enc = _tokenizer(src, return_tensors="pt", truncation=True, max_length=512)
    enc = {k: v.to(_device) for k, v in enc.items()}
    enc.pop("token_type_ids", None)

    with torch.inference_mode():
        out = _model.generate(
            **enc,
            max_new_tokens=180,
            min_new_tokens=0,
            num_beams=2,
            do_sample=False,
            early_stopping=True,
            no_repeat_ngram_size=4,
            repetition_penalty=1.10,
            length_penalty=0.85,
            eos_token_id=_tokenizer.eos_token_id,
            pad_token_id=_tokenizer.pad_token_id
        )

    raw_text = _tokenizer.decode(out[0], skip_special_tokens=True)
    final_text = postprocess_diary(raw_text, max_sents=11)
    cleanup_torch()
    return final_text

async def generate_daily_diary(one_line_list: List[str]) -> Dict[str, object]:
    """
    FastAPI 라우터에서 호출할 최종 비동기 함수.
    새로운 DB 스키마(DailyDiary)의 컬럼명에 맞춰 반환합니다.
    """
    from anyio import to_thread

    def _run():
        diary_text = _run_generation_sync(one_line_list)
        # ✅ API 라우터(diary.py)가 받을 수 있게 딕셔너리로 반환!
        return {
            "content": diary_text,
            "source_count": len(one_line_list)
        }

    # 서버 성능 저하를 막기 위해 별도 쓰레드에서 실행
    result = await to_thread.run_sync(_run)
    return result