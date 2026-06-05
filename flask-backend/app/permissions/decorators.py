"""FR-11 RBAC permission decorator — JWT claims-based role check"""

from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def require_role(*roles: str):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_roles = set(claims.get("roles", []))
            required = set(roles)
            if not user_roles.intersection(required):
                from flask import jsonify
                return jsonify({
                    "code": 403,
                    "message": "Insufficient permissions",
                    "detail": {"required": list(required), "current": list(user_roles)},
                }), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper
