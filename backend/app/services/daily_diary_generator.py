# app/services/daily_diary_generator.py
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict

import torch
import regex as re
import emoji
from transformers import BartForConditionalGeneration, PreTrainedTokenizerFast

# 1) 모델 / 토크나이저 경로 설정

# 이 파일 위치: app/services/daily_diary_generator.py
# BASE_DIR: 프로젝트 루트 (Aiary/) 를 가리키도록 설정
BASE_DIR = Path(__file__).resolve().parents[2]

# 모델이 저장된 디렉터리
#   Aiary/
#     └─ models/
#          └─ day_diary_from_summary_v2/
MODEL_DIR = BASE_DIR / "models" / "day_diary_from_summary_v2"

# 인코딩/디코딩 길이 제한
MAX_INPUT_LEN = 256
MAX_TARGET_LEN = 220

# lazy-loading 을 위한 전역 변수 (최초 1회만 로드)
_tokenizer = None
_model = None
_device = None


def _load_model_if_needed():
    """
    KoBART 토크나이저와 모델을 **최초 1번만** 로드하는 함수.

    - FastAPI 서버 띄운 후 첫 호출에서만 모델을 실제로 로드.
    - 이후 호출에서는 이미 로드된 전역 객체를 재사용해서 속도/메모리 절약.
    """
    global _tokenizer, _model, _device

    if _model is not None and _tokenizer is not None:
        # 이미 로딩된 상태라면 그대로 사용
        return

    if not MODEL_DIR.exists():
        raise FileNotFoundError(f"하루일기 모델 디렉토리를 찾을 수 없습니다: {MODEL_DIR}")

    print("[INFO] 하루일기 모델 / 토크나이저 로드 중...", flush=True)

    # HuggingFace Transformers 형식으로 저장된 디렉터리에서 바로 로드
    _tokenizer = PreTrainedTokenizerFast.from_pretrained(str(MODEL_DIR))
    _model = BartForConditionalGeneration.from_pretrained(str(MODEL_DIR))

    # pad_token 이 없으면 eos_token을 pad 로 사용
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    # GPU가 있으면 cuda, 없으면 cpu 사용
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _model.to(_device)
    _model.eval()

    print(f"[INFO] device = {_device}", flush=True)
    print("[INFO] 하루일기 모델 로드 완료", flush=True)


# 2) 텍스트 정제 함수들

def _remove_emoji(text: str) -> str:
    """이모지 제거 (emoji 라이브러리 + regex 기반 이중 처리)."""
    text = emoji.replace_emoji(text, "")
    emoji_pattern = re.compile(
        r"[\p{Emoji}\p{Emoji_Presentation}\p{Extended_Pictographic}]",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text)


def _clean_sentence(text: str) -> str:
    """한 줄 일기 문장을 모델 입력에 맞게 간단히 정제."""
    text = str(text)
    text = _remove_emoji(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_summary_bullets(one_line_list: List[str]) -> Dict[str, object]:
    """
    여러 개의 한 줄 일기를 받아서:
      - 정제(clean)
      - '1. 문장' 형식 bullet 리스트
      - bullet들을 합친 combined_summary 문자열

    을 만들어 돌려줌.
    """
    cleaned = [_clean_sentence(s) for s in one_line_list if str(s).strip()]
    if not cleaned:
        raise ValueError("one_line_list 안에 유효한 문장이 없습니다.")

    bullet_lines = [f"{i}. {sent}" for i, sent in enumerate(cleaned, start=1)]
    combined_summary = "\n".join(bullet_lines)

    return {
        "cleaned_sentences": cleaned,
        "bullet_lines": bullet_lines,
        "combined_summary": combined_summary,
    }


# 3) 요약 -> 하루일기 생성 (실제 KoBART 호출)

def generate_diary_from_summary(summary_text: str, max_len: int = MAX_TARGET_LEN) -> str:
    """
    summary_text: '1. ~\\n2. ~\\n3. ~' 형태의 요약 문자열
    return: KoBART가 생성한 하루 일기 텍스트
    """
    _load_model_if_needed()

    # 학습 때 사용했던 포맷을 맞춰줌
    input_text = f"[SUMMARY]\n{summary_text}\n[DIARY]"

    enc = _tokenizer(
        input_text,
        max_length=MAX_INPUT_LEN,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )

    input_ids = enc["input_ids"].to(_device)
    attention_mask = enc["attention_mask"].to(_device)

    with torch.no_grad():
        outputs = _model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_len,
            min_length=40,
            no_repeat_ngram_size=3,
            repetition_penalty=2.0,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
            early_stopping=True,
            eos_token_id=_tokenizer.eos_token_id,
        )

    pred = _tokenizer.decode(outputs[0], skip_special_tokens=True)
    pred = pred.replace("[DIARY]", "").strip()
    return pred


# 4) FastAPI에서 쓸 비동기 래퍼

async def generate_daily_diary(one_line_list: List[str]) -> Dict[str, object]:
    """
    FastAPI 엔드포인트에서 호출할 비동기 래퍼.

    - one_line_list: DB에서 가져온 '한 줄 일기' 문자열 리스트
    - 내부에서:
        1) build_summary_bullets 로 bullet 요약 생성
        2) generate_diary_from_summary 로 KoBART 줄글 생성
    - 반환:
        {
          "generated_diary": "줄글 텍스트 ...",
          "bullet_lines": ["1. ...", "2. ...", ...],
          "combined_summary": "1. ...\\n2. ...\\n..."
        }
    """
    from anyio import to_thread  # anyio는 FastAPI에 기본 포함

    def _run():
        # 1) 한 줄 일기들로부터 bullet 요약 생성
        summary_info = build_summary_bullets(one_line_list)

        # 2) KoBART 호출 -> 하루 줄글 일기 생성
        diary_text = generate_diary_from_summary(summary_info["combined_summary"])

        return {
            "generated_diary": diary_text,
            "bullet_lines": summary_info["bullet_lines"],
            "combined_summary": summary_info["combined_summary"],
        }

    # 모델 추론은 CPU/GPU 연산이므로,
    # 메인 event loop 를 막지 않도록 쓰레드 풀에서 실행
    result = await to_thread.run_sync(_run)
    return result
