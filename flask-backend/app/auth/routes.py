"""FR-10 Authentication routes — register, login, logout, token refresh"""

import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, unset_jwt_cookies
from app.auth.services import register_user, login_user, refresh_access_token


auth_bp = Blueprint("auth", __name__)

_USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{2,31}$")
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def _validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    categories = 0
    if re.search(r"[A-Z]", password):
        categories += 1
    if re.search(r"[a-z]", password):
        categories += 1
    if re.search(r"\d", password):
        categories += 1
    if re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~]", password):
        categories += 1
    if categories < 3:
        return False, "Password must contain at least 3 of: uppercase, lowercase, digit, special character"
    return True, ""


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not username or not email or not password:
        return jsonify({"code": 400, "message": "Missing required fields"}), 400
    if not _USERNAME_RE.match(username):
        return jsonify({"code": 400, "message": "Username must start with a letter, 3-32 chars, letters/digits/underscores only"}), 400
    if not _EMAIL_RE.match(email):
        return jsonify({"code": 400, "message": "Invalid email format"}), 400
    if password != confirm_password:
        return jsonify({"code": 400, "message": "Passwords do not match"}), 400

    valid, msg = _validate_password_strength(password)
    if not valid:
        return jsonify({"code": 400, "message": msg}), 400

    try:
        user = register_user(username, email, password)
        from app.utils.audit import write_audit
        write_audit("register", f"user:{username}", {"email": email})
        return jsonify({
            "code": 201,
            "message": "Registration successful",
            "data": {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "is_verified": user.is_verified,
            },
        }), 201
    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    account = (data.get("account") or data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    if not account or not password:
        return jsonify({"code": 400, "message": "Missing account or password"}), 400

    try:
        result = login_user(account, password)
        from app.utils.audit import write_audit
        write_audit("login", f"user:{account}")
        return jsonify({"code": 200, "message": "Login successful", "data": result}), 200
    except ValueError as e:
        return jsonify({"code": 401, "message": str(e)}), 401


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    response = jsonify({"code": 200, "message": "Successfully logged out"})
    unset_jwt_cookies(response)
    return response, 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    try:
        result = refresh_access_token()
        return jsonify({"code": 200, "message": "Token refreshed", "data": result}), 200
    except ValueError as e:
        return jsonify({"code": 401, "message": str(e)}), 401
