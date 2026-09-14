from __future__ import annotations

import io
import json
import os
import shutil
import socket
import subprocess
import threading
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import serial
from serial.tools import list_ports
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "photos"
STATIC = Path(__file__).resolve().parent / "static"
CONFIG_PATH = ROOT / "config.json"
PHOTOS.mkdir(exist_ok=True)

DEFAULT_CONFIG = {
    "retention_hours": 168,
    "port": "COM8",
    "baud": 115200,
    "night_start": 20,
    "night_end": 8,
    "wifi_ssid": "",
    "wifi_password": "",
    "listen_host": "0.0.0.0",
    "listen_port": 8080,
}

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
last_alive = 0.0
lock = threading.Lock()
serial_lock = threading.Lock()

app = FastAPI(title="Entrada Escritorio")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.mount("/photos", StaticFiles(directory=PHOTOS), name="photos")


class SettingsIn(BaseModel):
    retention_hours: int | None = None
    night_start: int | None = None
    night_end: int | None = None


def push_event(kind: str, **extra) -> None:
    with lock:
        events.append({"type": kind, "ts": time.time(), **extra})
        if len(events) > 300:
            del events[:150]


def lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def desktop_dir() -> Path:
    home = Path.home()
    for candidate in (
        home / "Desktop",
        home / "Ambiente de Trabalho",
        home / "OneDrive" / "Desktop",
        Path(os.environ.get("USERPROFILE", str(home))) / "Desktop",
    ):
        if candidate.is_dir():
            return candidate
    fallback = home / "Desktop"
    fallback.mkdir(exist_ok=True)
    return fallback


def notify_pc(title: str, msg: str) -> None:
    def _run() -> None:
        try:
            from winotify import Notification

            toast = Notification(app_id="beta-security-lab", title=title, msg=msg)
            toast.show()
            return
        except Exception:
            pass
        try:
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-WindowStyle",
                    "Hidden",
                    "-Command",
                    f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; $t = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("beta-security-lab"); $xml = [Windows.Data.Xml.Dom.XmlDocument]::new(); $xml.LoadXml("<toast><visual><binding template=\\"ToastGeneric\\"><text>{title}</text><text>{msg}</text></binding></visual></toast>"); $n = [Windows.UI.Notifications.ToastNotification]::new($xml); $t.Show($n)',
                ],
                check=False,
                capture_output=True,
            )
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def parse_name(name: str) -> dict:
    stem = Path(name).stem
    source = "pir" if "-pir" in stem else "manual" if "-manual" in stem else "usb"
    day = ""
    if len(stem) >= 8 and stem[:8].isdigit():
        day = f"{stem[0:4]}-{stem[4:6]}-{stem[6:8]}"
    return {"source": source, "day": day}


def photo_list(day: str = "", source: str = "") -> list[dict]:
    items = []
    for path in sorted(PHOTOS.glob("*.jpg"), reverse=True):
        meta = parse_name(path.name)
        if day and meta["day"] != day:
            continue
        if source and source != "all" and meta["source"] != source:
            continue
        items.append(
            {
                "name": path.name,
                "url": f"/photos/{path.name}",
                "mtime": path.stat().st_mtime,
                "size": path.stat().st_size,
                "source": meta["source"],
                "day": meta["day"],
            }
        )
    return items


def unique_path(stamp: str, source: str, burst: int) -> Path:
    tag = source if source in {"pir", "manual", "wifi"} else "usb"
    extra = f"-{burst}" if burst else ""
    name = f"{stamp}-{tag}{extra}.jpg"
    path = PHOTOS / name
    n = 1
    while path.exists():
        name = f"{stamp}-{tag}{extra}-{n}.jpg"
        path = PHOTOS / name
        n += 1
    return path


def save_jpeg(data: bytes, source: str, burst: int, notify: bool = True) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = unique_path(stamp, source, burst)
    path.write_bytes(data)
    push_event("photo", name=path.name, url=f"/photos/{path.name}", source=source)
    if notify and (source == "manual" or burst in (0, 1)):
        label = "Movimento na entrada" if source == "pir" else "Nova foto"
        notify_pc("Entrada do escritorio", f"{label}: {path.name}")
    return path.name


def photos_for_day(day: datetime) -> list[Path]:
    prefix = day.strftime("%Y%m%d")
    return [p for p in PHOTOS.glob("*.jpg") if p.name.startswith(prefix)]


def export_day_folder(day: datetime) -> Path | None:
    files = photos_for_day(day)
    if not files:
        return None
    dest = desktop_dir() / f"entrada-{day.strftime('%Y-%m-%d')}"
    dest.mkdir(parents=True, exist_ok=True)
    for path in files:
        target = dest / path.name
        if target.exists():
            target = dest / f"{path.stem}-c{path.suffix}"
        shutil.move(str(path), str(target))
    push_event("exported", folder=str(dest), count=len(files))
    notify_pc("Entrada do escritorio", f"Exportado {len(files)} foto(s) para {dest.name}")
    return dest


def export_previous_days() -> None:
    today = datetime.now().date()
    days = set()
    for path in PHOTOS.glob("*.jpg"):
        meta = parse_name(path.name)
        if meta["day"]:
            try:
                d = datetime.strptime(meta["day"], "%Y-%m-%d").date()
            except ValueError:
                continue
            if d < today:
                days.add(d)
    for d in sorted(days):
        export_day_folder(datetime.combine(d, datetime.min.time()))


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


def parse_meta(prefix: bytes) -> tuple[str, int]:
    source = "pir"
    burst = 0
    text = prefix.decode("ascii", errors="ignore")
    for line in text.splitlines():
        if line.startswith("PHOTO"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2 and parts[1]:
                source = parts[1]
            if len(parts) >= 3 and parts[2].isdigit():
                burst = int(parts[2])
        if line.startswith("ALIVE"):
            pass
    return source, burst


def send_cfg(ser: serial.Serial) -> None:
    hour = datetime.now().hour
    ip = lan_ip()
    port = int(config.get("listen_port", 8080))
    ssid = str(config.get("wifi_ssid") or "")
    password = str(config.get("wifi_password") or "")
    with serial_lock:
        ser.write(f"PING {hour}\n".encode("ascii"))
        ser.write(f"HOST\t{ip}\t{port}\n".encode("ascii"))
        if ssid:
            ser.write(f"WIFI\t{ssid}\t{password}\n".encode("utf-8"))
        ser.flush()


def serial_loop() -> None:
    global connected, last_alive
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
        last_alive = time.time()
        push_event("status", message=f"Ligado a {port}")
        try:
            send_cfg(ser)
        except Exception:
            pass
        buf = bytearray()
        last_ping = 0.0
        try:
            while True:
                now = time.time()
                if now - last_ping > 2:
                    try:
                        with serial_lock:
                            ser.write(f"PING {datetime.now().hour}\n".encode("ascii"))
                        last_ping = now
                    except Exception:
                        raise
                chunk = ser.read(4096)
                if chunk:
                    last_alive = time.time()
                    connected = True
                    buf.extend(chunk)
                elif time.time() - last_alive > 8:
                    connected = False
                while True:
                    idx = buf.find(b"TCS3")
                    if idx < 0:
                        if len(buf) > 80:
                            del buf[:-20]
                        break
                    meta_src, meta_burst = parse_meta(bytes(buf[:idx])) if idx else ("pir", 0)
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
                    save_jpeg(jpeg, meta_src, meta_burst)
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
def api_photos(day: str = "", source: str = "all"):
    return {
        "photos": photo_list(day, source),
        "connected": connected and (time.time() - last_alive < 8 if last_alive else False),
    }


@app.get("/api/events")
def api_events(after: float = 0):
    with lock:
        fresh = [e for e in events if e["ts"] > after]
        last = events[-1]["ts"] if events else after
    live = connected and (time.time() - last_alive < 8 if last_alive else False)
    return {"events": fresh, "last": last, "connected": live}


@app.get("/api/settings")
def api_settings():
    live = connected and (time.time() - last_alive < 8 if last_alive else False)
    return {
        "retention_hours": config["retention_hours"],
        "night_start": config.get("night_start", 20),
        "night_end": config.get("night_end", 8),
        "port": config.get("port"),
        "connected": live,
        "count": len(list(PHOTOS.glob("*.jpg"))),
        "lan_url": f"http://{lan_ip()}:{config.get('listen_port', 8080)}",
        "wifi_configured": bool(config.get("wifi_ssid")),
    }


@app.post("/api/settings")
def api_settings_save(body: SettingsIn):
    if body.retention_hours is not None:
        if body.retention_hours < 0 or body.retention_hours > 24 * 365:
            raise HTTPException(400, "valor invalido")
        config["retention_hours"] = body.retention_hours
    if body.night_start is not None:
        if not 0 <= body.night_start <= 23:
            raise HTTPException(400, "hora invalida")
        config["night_start"] = body.night_start
    if body.night_end is not None:
        if not 0 <= body.night_end <= 23:
            raise HTTPException(400, "hora invalida")
        config["night_end"] = body.night_end
    save_config(config)
    return api_settings()


@app.post("/api/upload")
async def api_upload(
    request: Request,
    x_source: str = Header(default="wifi"),
    x_burst: str = Header(default="0"),
):
    data = await request.body()
    if len(data) < 100:
        raise HTTPException(400, "jpeg invalido")
    burst = int(x_burst) if str(x_burst).isdigit() else 0
    name = save_jpeg(data, x_source or "wifi", burst)
    return {"ok": True, "name": name}


@app.get("/api/export.zip")
def api_export_zip(day: str = "", source: str = "all"):
    items = photo_list(day, source)
    if not items:
        raise HTTPException(404, "sem fotos")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in items:
            path = PHOTOS / item["name"]
            if path.exists():
                zf.write(path, item["name"])
    buf.seek(0)
    stamp = day or datetime.now().strftime("%Y-%m-%d")
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="entrada-{stamp}.zip"'},
    )


@app.post("/api/export-desktop")
def api_export_desktop(day: str = Query(default="")):
    if day:
        d = datetime.strptime(day, "%Y-%m-%d")
    else:
        d = datetime.now()
    dest = export_day_folder(d)
    if not dest:
        raise HTTPException(404, "sem fotos nesse dia")
    return {"folder": str(dest)}


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


def _housekeeping() -> None:
    global connected
    export_previous_days()
    last_date = datetime.now().date()
    while True:
        time.sleep(30)
        today = datetime.now().date()
        if today != last_date:
            export_day_folder(datetime.combine(last_date, datetime.min.time()))
            last_date = today
        purge_old()
        if last_alive and time.time() - last_alive > 8:
            global connected
            connected = False


threading.Thread(target=serial_loop, daemon=True).start()
threading.Thread(target=_housekeeping, daemon=True).start()
