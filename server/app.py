from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import serial
from serial.tools import list_ports
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "photos"
STATIC = Path(__file__).resolve().parent / "static"
CONFIG_PATH = ROOT / "config.json"
PHOTOS.mkdir(exist_ok=True)

DEFAULT_CONFIG = {"retention_hours": 168, "port": "COM8", "baud": 115200}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **data}
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


config = load_config()
events: list[dict] = []
connected = False
lock = threading.Lock()

app = FastAPI(title="Entrada Escritorio")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.mount("/photos", StaticFiles(directory=PHOTOS), name="photos")


class SettingsIn(BaseModel):
    retention_hours: int


def push_event(kind: str, **extra) -> None:
    with lock:
        events.append({"type": kind, "ts": time.time(), **extra})
        if len(events) > 200:
            del events[:100]


def photo_list() -> list[dict]:
    items = []
    for path in sorted(PHOTOS.glob("*.jpg"), reverse=True):
        items.append(
            {
                "name": path.name,
                "url": f"/photos/{path.name}",
                "mtime": path.stat().st_mtime,
                "size": path.stat().st_size,
            }
        )
    return items


def purge_old() -> int:
    hours = max(0, int(config.get("retention_hours", 0)))
    if hours <= 0:
        return 0
    cutoff = time.time() - hours * 3600
    removed = 0
    for path in PHOTOS.glob("*.jpg"):
        if path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def find_port() -> str | None:
    preferred = config.get("port", "COM8")
    ports = list(list_ports.comports())
    names = [p.device for p in ports]
    if preferred in names:
        return preferred
    for p in ports:
        desc = f"{p.description} {p.hwid}".upper()
        if "303A" in desc or "ESP32" in desc or "USB SERIAL" in desc:
            if p.device != "COM1":
                return p.device
    return None


def read_exact(ser: serial.Serial, n: int, timeout_s: float = 8.0) -> bytes:
    buf = bytearray()
    deadline = time.time() + timeout_s
    while len(buf) < n:
        if time.time() > deadline:
            raise TimeoutError("timeout a ler a foto")
        chunk = ser.read(n - len(buf))
        if chunk:
            buf.extend(chunk)
        else:
            time.sleep(0.01)
    return bytes(buf)


def serial_loop() -> None:
    global connected
    while True:
        port = find_port()
        if not port:
            connected = False
            time.sleep(1.5)
            continue
        try:
            ser = serial.Serial(port, config.get("baud", 115200), timeout=0.2)
        except serial.SerialException:
            connected = False
            time.sleep(1.5)
            continue

        connected = True
        push_event("status", message=f"Ligado a {port}")
        buf = bytearray()
        try:
            while True:
                chunk = ser.read(4096)
                if not chunk:
                    continue
                buf.extend(chunk)
                while True:
                    idx = buf.find(b"TCS3")
                    if idx < 0:
                        if len(buf) > 3:
                            del buf[:-3]
                        break
                    if idx > 0:
                        del buf[:idx]
                    if len(buf) < 8:
                        break
                    size = int.from_bytes(buf[4:8], "little", signed=False)
                    if size < 100 or size > 400_000:
                        del buf[:4]
                        continue
                    if len(buf) < 8 + size:
                        break
                    jpeg = bytes(buf[8 : 8 + size])
                    del buf[: 8 + size]
                    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    name = f"{stamp}.jpg"
                    path = PHOTOS / name
                    n = 1
                    while path.exists():
                        name = f"{stamp}-{n}.jpg"
                        path = PHOTOS / name
                        n += 1
                    path.write_bytes(jpeg)
                    purge_old()
                    push_event("photo", name=name, url=f"/photos/{name}")
        except Exception:
            connected = False
            try:
                ser.close()
            except Exception:
                pass
            time.sleep(1.0)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/photos")
def api_photos():
    purge_old()
    return {"photos": photo_list(), "connected": connected}


@app.get("/api/events")
def api_events(after: float = 0):
    with lock:
        fresh = [e for e in events if e["ts"] > after]
        last = events[-1]["ts"] if events else after
    return {"events": fresh, "last": last, "connected": connected}


@app.get("/api/settings")
def api_settings():
    return {
        "retention_hours": config["retention_hours"],
        "port": config.get("port"),
        "connected": connected,
        "count": len(photo_list()),
    }


@app.post("/api/settings")
def api_settings_save(body: SettingsIn):
    if body.retention_hours < 0 or body.retention_hours > 24 * 365:
        raise HTTPException(400, "valor invalido")
    config["retention_hours"] = body.retention_hours
    save_config(config)
    purge_old()
    return api_settings()


@app.delete("/api/photos")
def api_delete_all():
    n = 0
    for path in PHOTOS.glob("*.jpg"):
        path.unlink(missing_ok=True)
        n += 1
    push_event("cleared")
    return {"deleted": n}


@app.delete("/api/photos/{name}")
def api_delete_one(name: str):
    path = (PHOTOS / name).resolve()
    if path.parent != PHOTOS.resolve() or not path.exists():
        raise HTTPException(404, "foto inexistente")
    path.unlink()
    push_event("deleted", name=name)
    return {"deleted": name}


def _purge_loop():
    while True:
        time.sleep(60)
        purge_old()


threading.Thread(target=serial_loop, daemon=True).start()
threading.Thread(target=_purge_loop, daemon=True).start()
