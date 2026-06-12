"""SysAuditLog ORM model — sys_audit_log table"""

from datetime import datetime
from app.extensions import db


class SysAuditLog(db.Model):
    __tablename__ = "sys_audit_log"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    operator_id = db.Column(db.Integer, db.ForeignKey("sys_user.id"), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    target = db.Column(db.String(128), nullable=False)
    detail = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    operator = db.relationship("SysUser", backref="audit_logs", lazy="select")
