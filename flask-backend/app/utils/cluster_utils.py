"""Cluster name resolution — derives human-readable names from user interest tags"""

import json
from collections import Counter
from flask import current_app
from app.extensions import db


def get_cluster_distribution():
    """Return cluster list with semantic names derived from dominant interest tags.

    Queries rt_coldstart_cluster, counts interest tags per cluster, and picks
    the top 2 tag as the cluster label.  Falls back to device-based naming when
    no interest tags are available.
    """
    rows = db.session.execute(
        db.text("SELECT cluster_id, interest_tags FROM rt_coldstart_cluster "
                "WHERE interest_tags IS NOT NULL")
    ).fetchall()

    # Aggregate interest tags per cluster
    cluster_tags = {}
    cluster_counts = {}
    for r in rows:
        cid = r[0]
        cluster_counts[cid] = cluster_counts.get(cid, 0) + 1
        if cid not in cluster_tags:
            cluster_tags[cid] = Counter()
        try:
            tags = json.loads(r[1]) if r[1] else []
            cluster_tags[cid].update(tags)
        except (json.JSONDecodeError, TypeError):
            pass

    # Also include clusters that have 0 members with tags
    all_clusters = db.session.execute(
        db.text("SELECT cluster_id, COUNT(*) as cnt FROM rt_coldstart_cluster "
                "GROUP BY cluster_id ORDER BY cluster_id")
    ).fetchall()

    device_label = {0: "安卓用户", 1: "iOS用户", 2: "Web用户"}

    result = []
    for r in all_clusters:
        cid = r[0]
        count = r[1]
        if cid in cluster_tags and cluster_tags[cid]:
            top2 = [t for t, _ in cluster_tags[cid].most_common(2)]
            name = f"偏好{top2[0]}{'·' + top2[1] if len(top2) > 1 else ''}"
        else:
            name = device_label.get(cid, f"用户群组{cid}")
        result.append({"cluster_name": name, "count": count})

    return result
