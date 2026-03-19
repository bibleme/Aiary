import asyncio
from app.services.daily_diary_generator_v3_eval import generate_daily_diary_v3_eval

sample_one_lines = [
    "오늘은 아기가 장난감을 꼭 쥔 채 환하게 웃었다.",
    "낮잠에서 막 깬 아이가 눈을 비비며 엄마를 찾았다.",
    "저녁에는 작은 손으로 이유식을 열심히 받아먹었다.",
    "하루 종일 재잘거리듯 옹알이를 하며 기분 좋은 시간을 보냈다.",
]


async def main():
    
    result = await generate_daily_diary_v3_eval(sample_one_lines)
    print("\n[RESULT]")
    print(result["generated_diary"])

    if "model_version" in result:
        print("\n[MODEL VERSION]")
        print(result["model_version"])


if __name__ == "__main__":
    asyncio.run(main())
