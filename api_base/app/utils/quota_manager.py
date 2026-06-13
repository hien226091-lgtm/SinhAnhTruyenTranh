"""Quota & plan management.

Free plan: 20 images total
Pro plan:  unlimited (capped at 9999 for safety)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from api_base.app.models.schema_db import RequestLog, User


FREE_PLAN_LIMIT = 20
PRO_PLAN_LIMIT = 9999
MAX_REQUESTS_PER_MINUTE = 5


def get_plan_limit(plan: str) -> int:
    """Return the image generation limit for a given plan."""
    if plan == "pro":
        return PRO_PLAN_LIMIT
    return FREE_PLAN_LIMIT


def check_quota_and_log(db: Session, user_id: int, model_name: str) -> bool:
    """
    Check rate-limit quota (requests/minute).
    Returns False if user exceeded rate limit.
    """
    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
    count = db.query(RequestLog).filter(
        RequestLog.UserID == user_id,
        RequestLog.Timestamp >= one_minute_ago
    ).count()
    if count >= MAX_REQUESTS_PER_MINUTE:
        return False
    new_log = RequestLog(UserID=user_id, ModelName=model_name, Status="success")
    db.add(new_log)
    db.commit()
    return True


def check_generation_quota(db: Session, user: User) -> tuple[bool, str]:
    """
    Check if user can generate more images based on their plan.
    Returns (allowed: bool, message: str).
    """
    limit = get_plan_limit(user.Plan or "free")
    used = user.ImagesGenerated or 0
    if used >= limit:
        plan_name = "Miễn phí" if (user.Plan or "free") == "free" else "Pro"
        return False, (
            f"Bạn đã sử dụng hết {used}/{limit} ảnh của gói {plan_name}. "
            "Hãy nâng cấp lên gói Pro để sinh không giới hạn!"
        )
    remaining = limit - used
    return True, f"Còn {remaining}/{limit} lượt sinh ảnh"


def increment_generated_count(db: Session, user: User, count: int = 1) -> None:
    """Increment the ImagesGenerated counter for a user."""
    user.ImagesGenerated = (user.ImagesGenerated or 0) + count
    db.commit()
