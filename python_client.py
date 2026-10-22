"""Desktop/LAN companion client for testing the master hub without Flutter."""

from __future__ import annotations

import argparse
import json
import platform
import socket
import threading
import time
import uuid

try:
    import websocket
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install websocket-client: pip install websocket-client") from exc


def _battery() -> int:
    try:
        import psutil

        batt = psutil.sensors_battery()
        if batt:
            return int(batt.percent)
    except Exception:
        pass
    return -1


def run(host: str, port: int = 5000) -> None:
    device_id = f"{platform.node()}-{uuid.getnode():x}"[:24]
    url = f"ws://{host}:{port}/ws/companion"
    print(f"Connecting {device_id} -> {url}")

    def on_message(_ws, message: str) -> None:
        data = json.loads(message)
        commands = data.get("commands") or []
        if data.get("type") == "command":
            commands.append(data)
        for command in commands:
            action = command.get("action")
            print(f"Remote command: {action}")
            locked = action == "lock"
            if action == "unlock":
                locked = False
            _ws.send(
                json.dumps(
                    {
                        "type": "telemetry",
                        "device_id": device_id,
                        "ip": socket.gethostbyname(socket.gethostname()),
                        "log": f"Executed {action} on companion",
                        "status": "locked" if locked else "online",
                        "active_app": "python_client",
                        "battery": _battery(),
                    }
                )
            )

    def on_open(ws) -> None:
        def heartbeat() -> None:
            while True:
                ws.send(
                    json.dumps(
                        {
                            "type": "telemetry",
                            "device_id": device_id,
                            "ip": socket.gethostbyname(socket.gethostname()),
                            "battery": _battery(),
                            "status": "online",
                            "active_app": "python_client",
                        }
                    )
                )
                time.sleep(3)

        threading.Thread(target=heartbeat, daemon=True).start()

    ws_app = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message)
    ws_app.run_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jarvis companion (Python)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    run(args.host, args.port)
