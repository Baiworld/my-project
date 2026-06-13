"""GET /api/export — CSV/Excel 导出"""

from flask import Blueprint, request, jsonify, Response
from app.extensions import db
from app.permissions.decorators import require_role
from app.export.services import export_to_csv, export_to_excel
from sqlalchemy import text

export_bp = Blueprint("export", __name__)


def _query_table(table: str) -> list[dict]:
    allowed = {"offline_recommendations", "offline_metrics", "rt_content_hot",
               "offline_user_portrait", "rt_user_profile", "rt_coldstart_cluster",
               "content_metadata"}
    if table not in allowed:
        return []

    rows = db.session.execute(text(f"SELECT * FROM {table} LIMIT 5000")).fetchall()
    if not rows:
        return []
    keys = list(rows[0]._fields)
    return [{k: str(v) if v is not None else "" for k, v in zip(keys, row)} for row in rows]


@export_bp.route("/export/<table>", methods=["GET"])
@require_role("operator", "admin")
def export_table(table: str):
    fmt = request.args.get("format", "csv").lower()
    if fmt not in ("csv", "excel"):
        return jsonify({"code": 400, "message": "format must be csv or excel"}), 400

    rows = _query_table(table)
    if not rows:
        return jsonify({"code": 404, "message": f"No data in table '{table}'"}), 404

    if fmt == "csv":
        csv_content = export_to_csv(rows)
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={table}.csv"},
        )

    buf = export_to_excel(rows, sheet_name=table)
    return Response(
        buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={table}.xlsx"},
    )
