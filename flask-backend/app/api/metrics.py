"""FR-12 GET /api/metrics — query recommendation metrics"""

from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app.extensions import db
from app.permissions.decorators import require_role
from app.utils.validators import validate_date_range
from app.utils.audit import write_audit

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/metrics", methods=["GET"])
@require_role("operator", "admin")
def get_metrics():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    group_by = request.args.get("group_by", "date")

    valid, msg = validate_date_range(start_date, end_date)
    if not valid:
        return jsonify({"code": 400, "message": msg}), 400

    order_clause = "ORDER BY metric_date"
    if group_by == "user_group":
        order_clause = "ORDER BY user_group, metric_date"
    elif group_by == "content_type":
        order_clause = "ORDER BY content_type, metric_date"

    sql = (
        "SELECT metric_date, user_group, content_type, ctr, cvr, "
        "avg_watch_duration, avg_interactions, coverage, diversity, "
        "coldstart_conversion, total_impressions, total_clicks, total_users "
        "FROM offline_metrics "
        f"WHERE metric_date BETWEEN :start_date AND :end_date {order_clause}"
    )
    rows = db.session.execute(
        text(sql), {"start_date": start_date, "end_date": end_date}
    ).fetchall()

    result = []
    for m in rows:
        result.append({
            "metric_date": str(m.metric_date),
            "user_group": m.user_group,
            "content_type": m.content_type,
            "ctr": float(m.ctr) if m.ctr is not None else None,
            "cvr": float(m.cvr) if m.cvr is not None else None,
            "avg_watch_duration": float(m.avg_watch_duration) if m.avg_watch_duration is not None else None,
            "avg_interactions": float(m.avg_interactions) if m.avg_interactions is not None else None,
            "coverage": float(m.coverage) if m.coverage is not None else None,
            "diversity": float(m.diversity) if m.diversity is not None else None,
            "coldstart_conversion": float(m.coldstart_conversion) if m.coldstart_conversion is not None else None,
            "total_impressions": m.total_impressions,
            "total_clicks": m.total_clicks,
            "total_users": m.total_users,
        })

    write_audit("query", "metrics", {"start_date": start_date, "end_date": end_date})
    return jsonify({"code": 200, "data": result}), 200
