import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials
from core.config.env_manager import get_env_manager
from core.services.auth.auth_service import get_auth_service

_bearer      = HTTPBearer(auto_error=True)
_admin_basic = HTTPBasic()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    try:
        return await get_auth_service().get_user_id(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")


def verify_admin(credentials: HTTPBasicCredentials = Depends(_admin_basic)) -> None:
    env_manager = get_env_manager()
    username    = env_manager.ADMIN_USERNAME
    password    = env_manager.ADMIN_PASSWORD

    if not (username and password):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="admin access not configured")

    valid_username = secrets.compare_digest(credentials.username, username)
    valid_password = secrets.compare_digest(credentials.password, password)
    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
