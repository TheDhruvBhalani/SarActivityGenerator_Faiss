"""
Authentication and Authorization
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from config.settings import APIConfig, ROLES


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class AuthManager:
    """Handles authentication and authorization"""

    PASSWORD_HASHES = None
    DEMO_MODE = False

    USER_DB = {
        "analyst1": {
            "username": "analyst1",
            "role": "ANALYST",
            "fullname": "Analyst"
        },
        "compliance1": {
            "username": "compliance1",
            "role": "COMPLIANCE_OFFICER",
            "fullname": "Compliance Officer"
        },
        "admin": {
            "username": "admin",
            "role": "ADMIN",
            "fullname": "Admin User"
        },
    }

    @classmethod
    def init_passwords(cls):
        """Initialize password hashes"""
        if cls.PASSWORD_HASHES is not None:
            return

        try:
            cls.PASSWORD_HASHES = {
                "analyst1": pwd_context.hash("pass123"),
                "compliance1": pwd_context.hash("comply123"),
                "admin": pwd_context.hash("admin123"),
            }
            print("Password hashing initialized")
        except Exception as e:
            print(f"Password hashing failed: {e}")
            cls.DEMO_MODE = True

    @classmethod
    def verify_password(cls, plain_password: str, username: str) -> bool:
        """Verify user password"""
        if cls.DEMO_MODE:
            demo_passwords = {
                "analyst1": "pass123",
                "compliance1": "comply123",
                "admin": "admin123"
            }
            return demo_passwords.get(username) == plain_password

        hashed = cls.PASSWORD_HASHES.get(username)
        if not hashed:
            return False
        return pwd_context.verify(plain_password, hashed)

    @classmethod
    def get_user(cls, username: str) -> Optional[Dict]:
        """Get user by username"""
        return cls.USER_DB.get(username)

    @classmethod
    def authenticate_user(cls, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with username and password"""
        user = cls.get_user(username)
        if not user:
            return None
        if not cls.verify_password(password, username):
            return None
        return user

    @classmethod
    def create_access_token(cls, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=APIConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, APIConfig.SECRET_KEY, algorithm=APIConfig.ALGORITHM)

    @classmethod
    def decode_token(cls, token: str) -> Dict:
        """Decode JWT token"""
        try:
            return jwt.decode(token, APIConfig.SECRET_KEY, algorithms=[APIConfig.ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    @classmethod
    def check_permission(cls, role: str, permission: str) -> bool:
        """Check if role has permission"""
        role_permissions = ROLES.get(role, [])
        return "*" in role_permissions or permission in role_permissions


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """Get current authenticated user from token"""
    payload = AuthManager.decode_token(credentials.credentials)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = AuthManager.get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_role = payload.get("role")
    if token_role:
        user = dict(user)
        user["role"] = token_role

    return user


def require_permission(permission: str):
    """Dependency to require specific permission"""
    async def checker(user: Dict = Depends(get_current_user)):
        if not AuthManager.check_permission(user["role"], permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission}"
            )
        return user
    return checker
