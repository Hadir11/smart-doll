import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SECRET = os.environ["JWT_SECRET"]
bearer = HTTPBearer()


def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def make_token(parent_id: int) -> str:
    payload = {"sub": str(parent_id),
               "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, SECRET, algorithm="HS256")


def current_parent(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    try:
        data = jwt.decode(cred.credentials, SECRET, algorithms=["HS256"])
        return int(data["sub"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")