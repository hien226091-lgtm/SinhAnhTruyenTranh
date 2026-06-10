from fastapi import HTTPException, status, Depends
from api_base.app.security.deps import get_current_user
from api_base.app.models.schema_db import User

def verify_admin(current_user: User = Depends(get_current_user)) -> User:
    """Chỉ Admin mới được qua vòng này."""
    # Kiểm tra email cứng hoặc role admin
    if current_user.Email != "vvhien2004@gmail.com": 
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phải Admin, cấm vào đây!"
        )
    return current_user