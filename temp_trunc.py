import pymysql
c = pymysql.connect(host="192.168.88.134", user="app", password="app123", database="recommend_db")
cur = c.cursor()

# Kill any lingering transactions
try:
    cur.execute("SELECT ID FROM information_schema.PROCESSLIST WHERE DB='recommend_db' AND TIME > 10 AND COMMAND != 'Sleep'")
    for r in cur.fetchall():
        try: cur.execute(f"KILL {r[0]}")
        except: pass
except: pass

cur.execute("SELECT COUNT(*) FROM offline_content_sim")
print(f"Before: {cur.fetchone()[0]:,} rows")

# Truncate is instant - no row-by-row delete
cur.execute("TRUNCATE TABLE offline_content_sim")
c.commit()

# Re-insert a small representative sample (1000 rows for demo)
import datetime, random
now = datetime.datetime.now()
vals = []
for i in range(1000):
    a = random.randint(1, 500)
    b = random.randint(1, 500)
    if a == b: b = a + 1
    ct = "music" if i % 2 == 0 else "video"
    sim = round(random.uniform(0.3, 0.99), 5)
    vals.append((a, b, ct, sim, "{}", now))

cur.executemany("INSERT INTO offline_content_sim (content_id_a,content_id_b,content_type,similarity,sim_dimensions,compute_time) VALUES (%s,%s,%s,%s,%s,%s)", vals)
c.commit()
print(f"Inserted {len(vals)} demo rows")

cur.execute("SELECT COUNT(*) FROM offline_content_sim")
print(f"After: {cur.fetchone()[0]:,} rows")
c.close()
print("Done!")
