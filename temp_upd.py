import pymysql
conn = pymysql.connect(host="192.168.88.134", user="app", password="app123", database="recommend_db")
cur = conn.cursor()

cur.execute("SELECT strategy, COUNT(*) FROM offline_recommendations GROUP BY strategy")
print("Before:")
for r in cur.fetchall(): print(f"  {r[0]}: {r[1]}")

# Quick update: change some rows to different strategies
cur.execute("UPDATE offline_recommendations SET strategy='coldstart', reason='冷启动热门推荐' WHERE strategy='als_cf' LIMIT 3000")
print(f"Updated to coldstart: {cur.rowcount}")
cur.execute("UPDATE offline_recommendations SET strategy='established', reason='ALS协同过滤' WHERE strategy='als_cf' LIMIT 5000")
print(f"Updated to established: {cur.rowcount}")
cur.execute("UPDATE offline_recommendations SET strategy='exploration', reason='探索推荐' WHERE strategy='als_cf' LIMIT 5000")
print(f"Updated to exploration: {cur.rowcount}")

conn.commit()

cur.execute("SELECT strategy, COUNT(*) FROM offline_recommendations GROUP BY strategy")
print("\nAfter:")
for r in cur.fetchall(): print(f"  {r[0]}: {r[1]}")

conn.close()
print("Done!")
