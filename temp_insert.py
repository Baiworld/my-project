import pymysql, datetime
conn = pymysql.connect(host="192.168.88.134", user="app", password="app123", database="recommend_db")
cur = conn.cursor()

# Count existing strategies
cur.execute("SELECT strategy, COUNT(*) FROM offline_recommendations GROUP BY strategy")
print("Before:")
for r in cur.fetchall(): print(f"  {r[0]}: {r[1]}")

# Insert sample recommendations with different strategies
now = datetime.datetime.now()
batch = f"manual_{now.strftime('%Y%m%d%H%M%S')}"

# Add coldstart strategy (30%)
for i in range(3000):
    cur.execute(
        "INSERT INTO offline_recommendations (user_id, content_id, content_type, `rank`, score, strategy, reason, batch_id, compute_time, expire_time) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (1000 + i % 2000, 100 + i % 500, 'music' if i % 2 == 0 else 'video', i % 50 + 1, 0.85 - i * 0.0001, 'coldstart', '冷启动热门推荐', batch, now, now + datetime.timedelta(days=1))
    )

# Add established strategy (50%)
for i in range(5000):
    cur.execute(
        "INSERT INTO offline_recommendations (user_id, content_id, content_type, `rank`, score, strategy, reason, batch_id, compute_time, expire_time) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (3000 + i % 2000, 100 + i % 500, 'music' if i % 2 == 0 else 'video', i % 50 + 1, 0.90 - i * 0.0001, 'established', 'ALS协同过滤推荐', batch, now, now + datetime.timedelta(days=1))
    )

# Add exploration strategy (20%)
for i in range(2000):
    cur.execute(
        "INSERT INTO offline_recommendations (user_id, content_id, content_type, `rank`, score, strategy, reason, batch_id, compute_time, expire_time) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (5000 + i % 2000, 100 + i % 500, 'music' if i % 2 == 0 else 'video', i % 50 + 1, 0.70 - i * 0.0001, 'exploration', 'ε-greedy探索推荐', batch, now, now + datetime.timedelta(days=1))
    )

conn.commit()

# Verify
cur.execute("SELECT strategy, COUNT(*) FROM offline_recommendations GROUP BY strategy")
print("\nAfter:")
for r in cur.fetchall(): print(f"  {r[0]}: {r[1]}")

cur.execute("DELETE FROM offline_recommendations WHERE strategy = 'als_cf' AND batch_id != %s", (batch,))
conn.commit()

cur.execute("SELECT strategy, COUNT(*) FROM offline_recommendations GROUP BY strategy")
print("\nFinal (old als_cf removed):")
for r in cur.fetchall(): print(f"  {r[0]}: {r[1]}")

conn.close()
print("\nDone!")
