"""Admin API — 用户管理 + 系统设置"""

from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app.extensions import db
from app.models.user import SysUser
from app.models.role import SysRole, SysUserRole
from app.auth.services import hash_password
from app.permissions.decorators import require_role
from app.utils.audit import write_audit
from app.utils.validators import validate_pagination

admin_bp = Blueprint("admin", __name__)


# ── 用户列表 ──

@admin_bp.route("/users", methods=["GET"])
@require_role("admin")
def list_users():
    users = SysUser.query.all()
    result = []
    for u in users:
        roles = [r.name for r in u.roles]
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": roles[0] if roles else "end_user",
            "roles": roles,
            "status": "active" if u.is_active else "inactive",
            "created_at": str(u.created_at) if u.created_at else None,
        })
    return jsonify({"code": 200, "data": result}), 200


# ── 创建用户 ──

@admin_bp.route("/users", methods=["POST"])
@require_role("admin")
def create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role_name = data.get("role", "end_user")

    if not username or not email or not password:
        return jsonify({"code": 400, "message": "Missing required fields"}), 400
    if SysUser.query.filter_by(username=username).first():
        return jsonify({"code": 400, "message": "Username already exists"}), 400
    if SysUser.query.filter_by(email=email).first():
        return jsonify({"code": 400, "message": "Email already registered"}), 400

    user = SysUser(
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_active=True,
        is_verified=True,
    )
    db.session.add(user)
    db.session.flush()

    role = SysRole.query.filter_by(name=role_name).first()
    if role:
        db.session.add(SysUserRole(user_id=user.id, role_id=role.id))

    db.session.commit()
    write_audit("create_user", f"user:{username}", {"role": role_name})

    return jsonify({
        "code": 201,
        "message": "User created",
        "data": {"id": user.id, "username": user.username},
    }), 201


# ── 编辑用户 ──

@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@require_role("admin")
def update_user(user_id):
    user = SysUser.query.get(user_id)
    if not user:
        return jsonify({"code": 404, "message": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role_name = data.get("role")

    if username and username != user.username:
        if SysUser.query.filter_by(username=username).first():
            return jsonify({"code": 400, "message": "Username already taken"}), 400
        user.username = username
    if email and email != user.email:
        if SysUser.query.filter_by(email=email).first():
            return jsonify({"code": 400, "message": "Email already taken"}), 400
        user.email = email
    if password:
        user.password_hash = hash_password(password)
    if role_name:
        SysUserRole.query.filter_by(user_id=user.id).delete()
        role = SysRole.query.filter_by(name=role_name).first()
        if role:
            db.session.add(SysUserRole(user_id=user.id, role_id=role.id))

    db.session.commit()
    write_audit("update_user", f"user:{user.username}", {"role": role_name})

    return jsonify({"code": 200, "message": "User updated"}), 200


# ── 切换用户状态 ──

@admin_bp.route("/users/<int:user_id>/status", methods=["PUT"])
@require_role("admin")
def toggle_user_status(user_id):
    user = SysUser.query.get(user_id)
    if not user:
        return jsonify({"code": 404, "message": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "active")
    user.is_active = (new_status == "active")
    db.session.commit()
    write_audit("toggle_user", f"user:{user.username}", {"status": new_status})

    return jsonify({"code": 200, "message": "Status updated"}), 200


# ── 删除用户 ──

@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_role("admin")
def delete_user(user_id):
    user = SysUser.query.get(user_id)
    if not user:
        return jsonify({"code": 404, "message": "User not found"}), 404

    SysUserRole.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    write_audit("delete_user", f"user:{user.username}")

    return jsonify({"code": 200, "message": "User deleted"}), 200


# ── 系统设置（持久化到 JSON 文件，重启不丢失） ──

import json, os

_settings_file = os.path.join(os.path.dirname(__file__), "..", "..", "settings.json")
_defaults = {
    "refreshInterval": 6,
    "recommendCount": 20,
    "clusterCount": 8,
    "musicRatio": 60,
}


def _load_settings():
    try:
        with open(_settings_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        return {**_defaults, **saved}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_defaults)


def _save_settings(data):
    with open(_settings_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@admin_bp.route("/settings", methods=["PUT", "GET"])
@require_role("admin")
def system_settings():
    if request.method == "GET":
        return jsonify({"code": 200, "data": _load_settings()}), 200

    current = _load_settings()
    data = request.get_json(silent=True) or {}
    for key in _defaults:
        if key in data:
            current[key] = data[key]
    _save_settings(current)
    write_audit("update_settings", "system", data)

    return jsonify({"code": 200, "message": "Settings saved", "data": current}), 200


# ── 审计日志查询 ──

@admin_bp.route("/audit-logs", methods=["GET"])
@require_role("admin")
def list_audit_logs():
    page, size = validate_pagination(
        request.args.get("page"), request.args.get("size")
    )
    offset = (page - 1) * size

    action = request.args.get("action")
    operator_id = request.args.get("operator_id", type=int)

    where = ["1=1"]
    params: dict = {}
    if action:
        where.append("action = :action")
        params["action"] = action
    if operator_id:
        where.append("operator_id = :operator_id")
        params["operator_id"] = operator_id

    where_clause = " AND ".join(where)

    rows = db.session.execute(
        text(
            f"SELECT id, operator_id, action, target, detail, ip_address, created_at "
            f"FROM sys_audit_log "
            f"WHERE {where_clause} "
            f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": size, "offset": offset},
    ).fetchall()

    total = db.session.execute(
        text(f"SELECT COUNT(*) FROM sys_audit_log WHERE {where_clause}"),
        params,
    ).scalar()

    result = []
    for r in rows:
        result.append({
            "id": r.id,
            "operator_id": r.operator_id,
            "action": r.action,
            "target": r.target,
            "detail": r.detail,
            "ip_address": r.ip_address,
            "created_at": str(r.created_at),
        })

    write_audit("query", "audit-logs", {"action": action})
    return jsonify({
        "code": 200,
        "data": result,
        "pagination": {"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size)},
    }), 200
