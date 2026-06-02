import jwt
from pathlib import Path
from typing import Optional, List
from functools import cache
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config.config_manager import get_config_manager
from core.config.env_manager import get_env_manager


class JwtAuthenticator:
    def __init__(self, key: str, algorithms: List[str], user_id_claim: str,
                 issuer: Optional[str], audience: Optional[str]) -> None:
        self.key           = key
        self.algorithms    = algorithms
        self.user_id_claim = user_id_claim
        self.issuer        = issuer
        self.audience      = audience

    def resolve_user_id(self, token: str) -> str:
        decode_kwargs = {"algorithms": self.algorithms}
        if self.issuer:
            decode_kwargs["issuer"] = self.issuer
        if self.audience:
            decode_kwargs["audience"] = self.audience

        payload = jwt.decode(token, self.key, **decode_kwargs)
        user_id = payload.get(self.user_id_claim)
        if not user_id:
            raise ValueError(f"missing claim: {self.user_id_claim}")

        return str(user_id)


@cache
def get_jwt_authenticator() -> JwtAuthenticator:
    config   = get_config_manager().get_config("auth.jwt", {})
    key_path = get_env_manager().JWT_PUBLIC_KEY_PATH
    if not key_path:
        raise RuntimeError("JWT_PUBLIC_KEY_PATH is not set")

    public_key = Path(key_path).read_text()
    return JwtAuthenticator(
        key=public_key,
        algorithms=config.get("algorithms", ["RS256"]),
        user_id_claim=config.get("user_id_claim", "sub"),
        issuer=config.get("issuer"),
        audience=config.get("audience"),
    )


_bearer = HTTPBearer(auto_error=True)


def require_user_id(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    try:
        return get_jwt_authenticator().resolve_user_id(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
