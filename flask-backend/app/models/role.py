"""SysRole ORM model — sys_role + sys_user_role tables"""

from datetime import datetime
from app.extensions import db


class SysRole(db.Model):
    __tablename__ = "sys_role"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class SysUserRole(db.Model):
    __tablename__ = "sys_user_role"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("sys_user.id", ondelete="CASCADE"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("sys_role.id", ondelete="CASCADE"), nullable=False)
    assigned_by = db.Column(db.Integer, nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
