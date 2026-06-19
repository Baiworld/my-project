import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.88.134", username="root", password="123456", timeout=10)
sftp = c.open_sftp()
sftp.put(r"E:\TraeBD\data-generator-vm\generate_data.py", "/opt/data-generator-vm/generate_data.py")
sftp.close()
print("Uploaded")

s, o, e = c.exec_command('python3 /opt/data-generator-vm/generate_data.py --help 2>&1; python3 -c "compile(open(\"/opt/data-generator-vm/generate_data.py\").read(), \"test\", \"exec\"); print(\"VM Syntax OK\")" 2>&1')
print(o.read().decode(errors="replace"))
c.close()
