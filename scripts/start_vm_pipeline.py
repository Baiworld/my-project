import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.88.134", username="root", password="123456", timeout=10)
print("Connected to VM")

# Start the pipeline (rate=5 events/sec in session mode)
print("Starting Kafka + Flume + Generator (rate=5)...")
channel = c.get_transport().open_session()
channel.exec_command("bash /opt/data-generator-vm/start_all_v2.sh 5 2>&1")
channel.setblocking(False)

# Read output for a few seconds
start = time.time()
while time.time() - start < 15:
    time.sleep(0.5)
    while channel.recv_ready():
        data = channel.recv(65536)
        print(data.decode(errors="replace"), end="", flush=True)
    while channel.recv_stderr_ready():
        data = channel.recv_stderr(65536)
        print(data.decode(errors="replace"), end="", flush=True)

print("\n\nPipeline startup command sent. Checking status...")

# Check status
s, o, e = c.exec_command("bash /opt/data-generator-vm/start_all_v2.sh status 2>&1")
print(o.read().decode(errors="replace"))

c.close()
print("\nDone. Pipeline should be running.")
