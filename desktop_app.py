#!/usr/bin/env python3
"""Desktop launcher for the birthday dashboard."""

from __future__ import annotations

import argparse
import atexit
import datetime as dt
import signal
import socket
import sys
from pathlib import Path
from threading import Event, Thread

from werkzeug.serving import make_server

from birthday_reminder import due_entries_on_date, load_entries, send_birthday_notification
from web_app import PROJECT_NAME, create_app

try:
    import webview
except ImportError:  # pragma: no cover - runtime dependency
    webview = None


def resolve_resource_path(name: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / name  # pyright: ignore[reportAttributeAccessIssue]
    return Path(__file__).resolve().parent / name


def resolve_default_db_path() -> Path:
    base_dir = resolve_app_support_dir()
    return base_dir / "birthdays.json"


def resolve_app_support_dir() -> Path:
    if sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support" / PROJECT_NAME
    else:
        base_dir = Path.home() / f".{PROJECT_NAME}"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def pick_open_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class DashboardServer:
    def __init__(self, db_path: Path, port: int, stop_event: Event):
        template_dir = resolve_resource_path("templates")
        static_dir = resolve_resource_path("static")
        app = create_app(
            db_path,
            template_folder=str(template_dir),
            static_folder=str(static_dir),
        )
        self.server = make_server("127.0.0.1", port, app, threaded=True)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.url = f"http://127.0.0.1:{port}"
        self._stopped = False

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self.server.shutdown()
        self.thread.join(timeout=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{PROJECT_NAME} 桌面应用")
    parser.add_argument("--db", help="生日数据库路径（默认存到用户目录）")
    parser.add_argument("--port", type=int, help="固定端口（默认自动分配）")
    parser.add_argument("--headless", action="store_true", help="无窗口模式（仅测试用）")
    parser.add_argument("--skip-startup-notify", action="store_true", help="启动时不自动检查生日通知")
    return parser.parse_args()


def run_headless(stop_event: Event) -> None:
    try:
        while not stop_event.wait(0.5):
            continue
    except KeyboardInterrupt:
        stop_event.set()


def run_webview(url: str, stop_event: Event) -> None:
    if webview is None:
        raise RuntimeError("缺少 pywebview 依赖，请先执行: uv sync")

    window = webview.create_window(
        PROJECT_NAME,
        url=url,
        width=1220,
        height=820,
        min_size=(980, 680),
    )

    def on_start() -> None:
        def close_when_stop() -> None:
            stop_event.wait()
            try:
                window.destroy()
            except Exception:
                pass

        Thread(target=close_when_stop, daemon=True).start()

    webview.start(on_start, window)
    stop_event.set()


def startup_notify_if_due(db_path: Path, state_path: Path) -> None:
    entries = load_entries(db_path)
    today = dt.date.today()
    due_entries = due_entries_on_date(entries, today)
    if not due_entries:
        return
    names = "、".join(entry.name for entry in due_entries)
    send_birthday_notification(
        names,
        today,
        once_per_day=True,
        state_path=state_path,
    )


def main() -> None:
    args = parse_args()
    db_path = Path(args.db).expanduser().resolve() if args.db else resolve_default_db_path()
    state_path = db_path.with_name("notify_state.json")
    port = args.port or pick_open_port()
    stop_event = Event()

    server = DashboardServer(db_path=db_path, port=port, stop_event=stop_event)
    server.start()
    atexit.register(server.stop)

    def on_signal(_: int, __) -> None:
        stop_event.set()

    try:
        signal.signal(signal.SIGINT, on_signal)
        signal.signal(signal.SIGTERM, on_signal)
    except Exception:
        pass

    if not args.skip_startup_notify:
        startup_notify_if_due(db_path, state_path)

    try:
        if args.headless:
            run_headless(stop_event)
        else:
            run_webview(server.url, stop_event)
    finally:
        stop_event.set()
        server.stop()


if __name__ == "__main__":
    main()
