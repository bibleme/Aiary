import json
from pathlib import Path

from app.config import settings


def load_monthly_reports() -> dict:
    report_path = Path(settings.MONTHLY_REPORT_JSON_PATH)
    if not report_path.exists():
        raise FileNotFoundError(f"월별 리포트 JSON 파일을 찾을 수 없습니다: {report_path}")

    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_monthly_report_for_user(user_id: int, target_month: str) -> dict | None:
    reports = load_monthly_reports()
    user_key = str(user_id)

    if user_key not in reports:
        return None

    user_reports = reports[user_key]
    if target_month not in user_reports:
        return None

    report = user_reports[target_month].copy()
    report["user_id"] = user_id
    report["month"] = target_month
    return report
