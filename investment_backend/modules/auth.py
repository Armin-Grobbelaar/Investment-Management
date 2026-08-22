"""
auth.py
=======
Authentication, password hashing, and JWT token management for multi-tenant security.
"""

import os
import json
import base64
import hmac
import hashlib
import time
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "antigravity_super_secret_key_change_in_prod_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600 * 24 * 7  # 7 days

security_bearer = HTTPBearer(auto_error=False)

class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    database_name: Optional[str] = None

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)

def create_jwt_token(payload: Dict[str, Any], secret: str = SECRET_KEY) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload_copy = payload.copy()
    if "exp" not in payload_copy:
        payload_copy["exp"] = int(time.time()) + ACCESS_TOKEN_EXPIRE_SECONDS
    
    header_bytes = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_bytes = json.dumps(payload_copy, separators=(',', ':')).encode('utf-8')
    
    token_base = f"{base64url_encode(header_bytes)}.{base64url_encode(payload_bytes)}"
    signature = hmac.new(secret.encode('utf-8'), token_base.encode('utf-8'), hashlib.sha256).digest()
    
    return f"{token_base}.{base64url_encode(signature)}"

def verify_jwt_token(token: str, secret: str = SECRET_KEY) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        token_base = f"{header_b64}.{payload_b64}"
        
        expected_sig = hmac.new(secret.encode('utf-8'), token_base.encode('utf-8'), hashlib.sha256).digest()
        actual_sig = base64url_decode(sig_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
            
        payload = json.loads(base64url_decode(payload_b64).decode('utf-8'))
        if payload.get("exp") and payload["exp"] < time.time():
            return None
            
        return payload
    except Exception:
        return None

def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> User:
    """
    FastAPI dependency to extract and verify the current authenticated user.
    Supports Bearer header, X-Authorization header, or session query token.
    """
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    elif "authorization" in request.headers:
        auth_header = request.headers["authorization"]
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = auth_header
    elif "token" in request.query_params:
        token = request.query_params["token"]

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required: Missing Authorization token")

    payload = verify_jwt_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

    user_id = int(payload["sub"])
    username = payload.get("username", "user")
    email = payload.get("email", "")
    full_name = payload.get("full_name")
    database_name = payload.get("database_name", "investments_app")

    return User(
        id=user_id,
        username=username,
        email=email,
        full_name=full_name,
        database_name=database_name
    )

def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> Optional[User]:
    try:
        return get_current_user(request, credentials)
    except HTTPException:
        return None
