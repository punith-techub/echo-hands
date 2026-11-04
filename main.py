"""
ECHOHANDS 5.0 - Main Server Entrypoint
Launches the FastAPI server on http://localhost:8000
"""

import uvicorn
import os
import sys
import socket
import argparse

# Ensure project root is in python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def resolve_port(preferred_port: int = 8000) -> int:
    if not is_port_in_use(preferred_port):
        return preferred_port
    print(f"[*] Port {preferred_port} is currently occupied by another process.")
    for candidate in [8050, 8080, 8001, 8002]:
        if not is_port_in_use(candidate):
            print(f"[*] Dynamically assigned free port: {candidate}")
            return candidate
    return preferred_port

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ECHOHANDS 5.0 ISL Translator Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on (auto-detected if omitted)")
    args = parser.parse_args()

    port = args.port or resolve_port(8000)

    print("=" * 70)
    print("  ECHOHANDS 5.0 // ASTRA-VISION TACTICAL NEURAL HUD")
    print("  Real-time Indian Sign Language (ISL) to Text & Speech Translator")
    print(f"  Server active at: http://localhost:{port}")
    print("=" * 70)
    uvicorn.run("CORE.app:app", host=args.host, port=port, reload=False)
