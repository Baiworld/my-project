"""Role and permission service logic"""

from app.extensions import db


ROLES = ["end_user", "operator", "admin"]


def get_user_roles(user_id: int) -> list[str]:
    rows = db.session.execute(
        "SELECT sr.name FROM sys_user_role sur "
        "JOIN sys_role sr ON sur.role_id = sr.id "
        "WHERE sur.user_id = :user_id",
        {"user_id": user_id},
    ).fetchall()
    return [r[0] for r in rows]


def has_permission(user_id: int, required_role: str) -> bool:
    count = db.session.execute(
        "SELECT COUNT(*) FROM sys_user_role sur "
        "JOIN sys_role sr ON sur.role_id = sr.id "
        "WHERE sur.user_id = :user_id AND sr.name = :role_name",
        {"user_id": user_id, "role_name": required_role},
    ).scalar()
    return count > 0


def assign_role(user_id: int, role_name: str, assigned_by: int = None) -> bool:
    role = db.session.execute(
        "SELECT id FROM sys_role WHERE name = :name", {"name": role_name}
    ).fetchone()
    if not role:
        raise ValueError(f"Role '{role_name}' does not exist")

    db.session.execute(
        "INSERT IGNORE INTO sys_user_role (user_id, role_id, assigned_by) "
        "VALUES (:user_id, :role_id, :assigned_by)",
        {"user_id": user_id, "role_id": role[0], "assigned_by": assigned_by},
    )
    db.session.commit()
    return True


def revoke_role(user_id: int, role_name: str) -> bool:
    db.session.execute(
        "DELETE sur FROM sys_user_role sur "
        "JOIN sys_role sr ON sur.role_id = sr.id "
        "WHERE sur.user_id = :user_id AND sr.name = :role_name",
        {"user_id": user_id, "role_name": role_name},
    )
    db.session.commit()
    return True
