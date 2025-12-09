# app/services/ai_generator.py

import os
import base64
from openai import OpenAI
from fastapi import HTTPException
from dotenv import load_dotenv

# .env 읽어오기 (OPENAI_API_KEY=... )
load_dotenv()

MODEL_NAME = "gpt-4.1-mini"
MAX_TOKENS = 64
TEMPERATURE = 0.7


def get_client() -> OpenAI:
    """
    코랩에서 했던 `client = OpenAI()`를 서버 스타일로 감싼 함수.
    환경변수에 키가 없으면 500 에러.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.",
        )
    return OpenAI(api_key=api_key)


def encode_file_to_base64(file_bytes: bytes) -> str:
    """
    .ipynb에서는 파일 경로를 받아서 open(...,"rb") 했는데,
    백엔드에서는 이미 UploadFile.read()로 bytes를 갖고 있으니까
    그대로 base64로 인코딩만 해주면 됨.
    """
    return base64.b64encode(file_bytes).decode("utf-8")


async def generate_one_line_diary(image_data: bytes, user_prompt: str) -> str:
    """
    .ipynb의 generate_one_line_diary_from_image()를
    '이미지 경로' 대신 '이미지 바이트'를 받도록 바꾼 버전.
    user_prompt에는 코랩에서 쓰던 그 긴 프롬프트 문자열이 들어옴.
    """
    image_b64 = encode_file_to_base64(image_data)

    # 코랩의 system_prompt 그대로
    system_prompt = (
        "너는 부모를 위한 육아 일기 도우미야. "
        "아기 또는 아이의 사진을 보고 오늘 있었던 순간을 떠올리듯이, "
        "감성적인 한국어 한 줄 일기를 만들어주는 역할을 한다."
    )

    client = get_client()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt,  # 코랩에서 user_prompt 쓰던 부분
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        },
                    },
                ],
            },
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )

    one_line = response.choices[0].message.content.strip()
    return one_line


async def generate_daily_summary(one_line_diaries: list[str], date_str: str) -> str:
    joined = "\n".join(f"- {line}" for line in one_line_diaries)

    system_prompt = (
        "너는 부모를 위한 육아 일기 요약 도우미야. "
        "하루 동안 찍은 아이 사진들에 대해 이미 생성된 '한 줄 일기'들을 바탕으로, "
        "부모가 하루를 회상하며 읽을 수 있는 감성적인 한국어 일기를 작성해줘. "
        "말투는 따뜻하고 부드럽게, 일기 형식의 문단 1~2개 정도로 만들어."
    )

    user_prompt = (
        f"날짜: {date_str}\n\n"
        "아래는 이 날에 대한 한 줄 일기 목록이야.\n"
        "이 한 줄 일기들을 바탕으로 하루를 정리하는 줄글 일기를 작성해줘.\n\n"
        f"{joined}"
    )

    client = get_client()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=512,
        temperature=0.7,
    )

    summary = response.choices[0].message.content.strip()
    return summary
