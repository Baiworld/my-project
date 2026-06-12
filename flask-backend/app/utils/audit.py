"""审计日志写入工具"""

from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.extensions import db
from app.models.audit_log import SysAuditLog


def write_audit(action: str, target: str = "", detail: dict = None):
    try:
        verify_jwt_in_request(optional=True)
        claims = get_jwt_identity()
        operator_id = int(claims) if claims else None
    except Exception:
        operator_id = None

    log = SysAuditLog(
        operator_id=operator_id,
        action=action,
        target=target or request.path,
        detail=detail or {},
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()
