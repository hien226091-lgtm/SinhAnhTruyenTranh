# api_base/app/security/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from api_base.app.models.base_db import get_db
from api_base.app.security.security import decode_access_token
from api_base.app.models.schema_db import User

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception as e:
        print(f"DEBUG: Giải mã token lỗi: {e}") # Xem trong Terminal
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token lỗi")
    
    user = db.query(User).filter(User.Username == payload.sub).first()
    if not user:
        print(f"DEBUG: Không tìm thấy user với username: {payload.sub}") # Xem trong Terminal
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User không tồn tại")
    
    return user