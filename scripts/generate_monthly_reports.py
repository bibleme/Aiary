# scripts/generate_monthly_reports.py
import asyncio
from datetime import datetime, timedelta, UTC

from sqlalchemy import select

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.db.model import User
from app.services.monthly_report_generator import (
    generate_and_store_monthly_report,
    get_monthly_report_status,
)


def get_previous_month() -> str:
    today = datetime.now(UTC)
    first_day_of_this_month = today.replace(day=1)
    last_day_of_previous_month = first_day_of_this_month - timedelta(days=1)
    return last_day_of_previous_month.strftime("%Y-%m")


async def run() -> None:
    target_month = get_previous_month()
    print(f"[CRON] target_month={target_month}")
    print(f"[CRON] GPT_REPORT={settings.MONTHLY_REPORT_USE_GPT_REPORT}")
    print(f"[CRON] MODEL={settings.MONTHLY_REPORT_OPENAI_MODEL}")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User.id).order_by(User.id.asc()))
        user_ids = [row[0] for row in result.all()]

        print(f"[CRON] found_users={len(user_ids)}")

        success_count = 0
        skip_count = 0
        error_count = 0

        for user_id in user_ids:
            try:
                print(f"[CRON] checking user_id={user_id}")

                status = await get_monthly_report_status(
                    db=db,
                    user_id=user_id,
                    target_month=target_month,
                )

                # 이미 최신이면 스킵
                if status["exists"] and status["is_up_to_date"]:
                    print(f"[CRON] skip user_id={user_id} reason=already_up_to_date")
                    skip_count += 1
                    continue

                print(f"[CRON] generating report for user_id={user_id}")

                report = await generate_and_store_monthly_report(
                    db=db,
                    user_id=user_id,
                    target_month=target_month,
                )

                print(
                    f"[CRON] success user_id={user_id} "
                    f"mode={report.get('mode')} month={report.get('month')}"
                )
                success_count += 1

                # GPT 호출/DB 부하 분산용 짧은 대기
                await asyncio.sleep(1.5)

            except Exception as e:
                print(f"[CRON][ERROR] user_id={user_id} error={e}")
                error_count += 1

        print(
            f"[CRON] done target_month={target_month} "
            f"success={success_count} skip={skip_count} error={error_count}"
        )


if __name__ == "__main__":
    asyncio.run(run())