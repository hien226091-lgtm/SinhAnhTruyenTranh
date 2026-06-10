from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from api_base.app.models.schema_db import RequestLog

# Giới hạn 5 request mỗi phút (Bội Anh có thể chỉnh con số này tùy theo quota của Google)
MAX_REQUESTS_PER_MINUTE = 5

def check_quota_and_log(db: Session, user_id: int, model_name: str) -> bool:
    """
    Hàm kiểm tra quota:
    - Nếu trong 1 phút qua user gọi quá số lần cho phép -> Trả về False (Chặn)
    - Nếu còn quota -> Lưu log và trả về True (Cho phép)
    """
    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
    
    # Đếm số log của user trong 1 phút qua
    count = db.query(RequestLog).filter(
        RequestLog.UserID == user_id,
        RequestLog.Timestamp >= one_minute_ago
    ).count()
    
    if count >= MAX_REQUESTS_PER_MINUTE:
        return False 
    
    # Ghi log thành công
    new_log = RequestLog(UserID=user_id, ModelName=model_name, Status="success")
    db.add(new_log)
    db.commit()
    return True