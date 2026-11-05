import subprocess
import time
import sys

print("[Echo-Hands Tunnel Daemon] Starting persistent tunnel supervisor...", flush=True)

while True:
    try:
        print("[Echo-Hands Tunnel] Launching localtunnel for https://echohands-ai.loca.lt ...", flush=True)
        proc = subprocess.Popen(
            ["npx", "localtunnel", "--port", "8000", "--subdomain", "echohands-ai"],
            shell=True
        )
        proc.wait()
        print(f"[Echo-Hands Tunnel] Process exited with code {proc.returncode}. Reconnecting in 2s...", flush=True)
    except Exception as e:
        print(f"[Echo-Hands Tunnel] Error: {e}. Retrying in 3s...", flush=True)
    time.sleep(2)
