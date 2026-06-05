"""FR-10 Authentication services — bcrypt hashing, JWT, registration, login"""

import bcrypt
from datetime import datetime, timezone
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity
from app.extensions import db
from app.models.user import SysUser
from app.models.role import SysRole


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def register_user(username: str, email: str, password: str) -> SysUser:
    if SysUser.query.filter_by(username=username).first():
        raise ValueError("Username already exists")
    if SysUser.query.filter_by(email=email).first():
        raise ValueError("Email already registered")

    user = SysUser(
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_active=True,
        is_verified=False,
    )
    db.session.add(user)
    db.session.flush()

    # Assign default end_user role
    end_user_role = SysRole.query.filter_by(name="end_user").first()
    if end_user_role:
        from app.models.role import SysUserRole
        db.session.add(SysUserRole(user_id=user.id, role_id=end_user_role.id))

    db.session.commit()
    return user


def login_user(username_or_email: str, password: str) -> dict:
    user = SysUser.query.filter(
        (SysUser.username == username_or_email) | (SysUser.email == username_or_email)
    ).first()

    if not user or not user.is_active:
        raise ValueError("Invalid credentials")
    if not verify_password(password, user.password_hash):
        raise ValueError("Invalid credentials")

    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    roles = [r.name for r in user.roles]
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"username": user.username, "roles": roles},
    )
    refresh_token = create_refresh_token(
        identity=str(user.id),
        additional_claims={"username": user.username, "roles": roles},
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 7200,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": roles,
        },
    }


def get_current_user() -> SysUser:
    user_id = get_jwt_identity()
    return SysUser.query.get(int(user_id))


def refresh_access_token() -> dict:
    user_id = get_jwt_identity()
    user = SysUser.query.get(int(user_id))
    if not user or not user.is_active:
        raise ValueError("User not found or inactive")

    roles = [r.name for r in user.roles]
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"username": user.username, "roles": roles},
    )
    return {"access_token": access_token}
