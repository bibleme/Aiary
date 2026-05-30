# app/services/daily_diary_generator.py
from __future__ import annotations

import os
from typing import Dict, List

from app.config import settings

from app.services.daily_diary_generator_v2 import generate_daily_diary_v2
from app.services.daily_diary_generator_v3_eval import generate_daily_diary_v3_eval
from app.services.daily_diary_generator_realistic_daily import generate_daily_diary_realistic_daily

DEFAULT_DAILY_DIARY_MODEL_VERSION = settings.DAILY_DIARY_RUNTIME_VERSION.strip().lower()


async def generate_daily_diary(
    one_line_list: List[str],
    model_version: str | None = None,
) -> Dict[str, object]:
    """
    운영 API용 하루일기 생성 공식 진입점.

    원칙:
    - endpoint는 이 파일만 import한다.
    - 내부에서 실제 생성 버전(v2 / v3_eval)을 선택한다.
    - 현재 기본 운영 버전은 DAILY_DIARY_RUNTIME_VERSION 환경변수로 제어 가능하며,
      값이 없으면 v3_eval을 기본으로 사용한다.

    지원 버전:
    - v2
    - v3
    - v3_eval
    """
    selected_version = (model_version or DEFAULT_DAILY_DIARY_MODEL_VERSION).strip().lower()

    if selected_version == "v2":
        result = await generate_daily_diary_v2(one_line_list)
    elif selected_version in {"realistic_daily", "v4", "round5_realistic"}:
    	result = await generate_daily_diary_realistic_daily(one_line_list)
    elif selected_version in {"v3", "v3_eval"}:
        result = await generate_daily_diary_v3_eval(one_line_list)
    else:
        raise ValueError(
            f"지원하지 않는 하루일기 모델 버전입니다: {selected_version}. "
            f"허용값: v2, v3, v3_eval, realistic_daily, v4, round5_realistic"
        )

    return {
        "generated_diary": result["generated_diary"],
        "model_version": result.get("model_version", selected_version),
        "one_lines_count": result.get("one_lines_count", len(one_line_list)),
        "one_lines": result.get("one_lines", one_line_list),
        "bullet_lines": result.get("bullet_lines"),
        "combined_summary": result.get("combined_summary"),
	    "model_input": result.get("model_input"),
	    "decode_config": result.get("decode_config"),
	    "decode_score": result.get("decode_score"),
	    "generation_meta": result.get("generation_meta"),
    }
