"""Flask extensions — initialized here to avoid circular imports"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*")

# In-memory JWT blocklist — stores revoked JTIs until they naturally expire
_token_blocklist = set()


def is_token_revoked(jwt_header: dict, jwt_payload: dict) -> bool:
    """Check if a token's JTI is in the blocklist."""
    return jwt_payload.get("jti") in _token_blocklist


def revoke_token(jwt_payload: dict):
    """Add a token's JTI to the blocklist so it can't be reused."""
    jti = jwt_payload.get("jti")
    if jti:
        # Blocklist capped to prevent unbounded growth
        if len(_token_blocklist) > 10000:
            _token_blocklist.clear()
        _token_blocklist.add(jti)
