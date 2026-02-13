#!/usr/bin/env python3
"""Web dashboard for birthday reminders."""

from __future__ import annotations

import argparse
import datetime as dt
import uuid
from pathlib import Path
from urllib.parse import urlencode

from flask import Flask, redirect, render_template, request, url_for

from birthday_reminder import (
    DEFAULT_DB_PATH,
    Entry,
    due_entries_on_date,
    format_calendar,
    load_entries,
    parse_month_day,
    save_entries,
    upcoming_entries,
)


PROJECT_NAME = "生辰灯塔"


def build_month_buckets(start: dt.date, months: int) -> list[tuple[int, int]]:
    buckets: list[tuple[int, int]] = []
    year = start.year
    month = start.month
    for _ in range(months):
        buckets.append((year, month))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return buckets


def find_entry(entries: list[Entry], entry_id: str) -> Entry | None:
    for entry in entries:
        if entry.id == entry_id:
            return entry
    return None


def parse_entry_form() -> tuple[str, str, int, int, bool, str]:
    name = request.form.get("name", "").strip()
    calendar = request.form.get("calendar", "").strip()
    date_text = request.form.get("date", "").strip()
    note = request.form.get("note", "").strip()
    leap_month = bool(request.form.get("leap_month"))

    if not name:
        raise ValueError("姓名不能为空")
    if calendar not in {"solar", "lunar"}:
        raise ValueError("日历类型不正确")
    month, day = parse_month_day(date_text)
    return name, calendar, month, day, leap_month if calendar == "lunar" else False, note


def create_app(
    db_path: Path,
    template_folder: str | None = None,
    static_folder: str | None = None,
) -> Flask:
    flask_kwargs: dict[str, str] = {}
    if template_folder is not None:
        flask_kwargs["template_folder"] = template_folder
    if static_folder is not None:
        flask_kwargs["static_folder"] = static_folder
    app = Flask(__name__, **flask_kwargs)
    db_file = db_path.expanduser().resolve()

    def redirect_with_message(
        message_type: str,
        text: str,
        extra: dict[str, str] | None = None,
        anchor: str = "",
    ):
        query_dict: dict[str, str] = {message_type: text}
        if extra:
            query_dict.update(extra)
        query = urlencode(query_dict)
        suffix = f"#{anchor}" if anchor else ""
        return redirect(f"{url_for('index')}?{query}{suffix}")

    @app.get("/")
    def index():
        entries = load_entries(db_file)
        today = dt.date.today()
        due_today = due_entries_on_date(entries, today)
        upcoming_30 = upcoming_entries(entries, today, 30)
        upcoming_365 = upcoming_entries(entries, today, 365)

        lunar_count = sum(1 for entry in entries if entry.calendar == "lunar")
        solar_count = len(entries) - lunar_count

        entry_rows = []
        for when, entry in upcoming_entries(entries, today, 3650):
            entry_rows.append(
                {
                    "id": entry.id,
                    "name": entry.name,
                    "calendar_text": format_calendar(entry),
                    "birthday_text": f"{entry.month:02d}-{entry.day:02d}",
                    "leap_text": "闰月" if entry.calendar == "lunar" and entry.leap_month else "-",
                    "next_date": when.isoformat(),
                    "days_left": (when - today).days,
                    "note": entry.note or "-",
                }
            )

        buckets = build_month_buckets(today, 12)
        month_counts = {(year, month): 0 for year, month in buckets}
        for when, _ in upcoming_365:
            key = (when.year, when.month)
            if key in month_counts:
                month_counts[key] += 1
        max_count = max(month_counts.values()) if month_counts else 1
        month_chart = [
            {
                "label": f"{year}-{month:02d}",
                "count": month_counts[(year, month)],
                "height": 18 if max_count == 0 else 18 + int(112 * (month_counts[(year, month)] / max_count)),
            }
            for year, month in buckets
        ]

        success_message = request.args.get("success", "")
        error_message = request.args.get("error", "")
        edit_id = request.args.get("edit_id", "").strip()
        edit_target = find_entry(entries, edit_id) if edit_id else None
        if edit_id and edit_target is None and not error_message:
            error_message = f"未找到 ID: {edit_id}"

        return render_template(
            "dashboard.html",
            project_name=PROJECT_NAME,
            today=today,
            due_today=due_today,
            upcoming_30=upcoming_30,
            entry_rows=entry_rows,
            month_chart=month_chart,
            total_count=len(entries),
            lunar_count=lunar_count,
            solar_count=solar_count,
            success_message=success_message,
            error_message=error_message,
            edit_target=edit_target,
        )

    @app.post("/add")
    def add_entry():
        entries = load_entries(db_file)
        try:
            name, calendar, month, day, leap_month, note = parse_entry_form()
        except Exception as exc:
            return redirect_with_message("error", str(exc))

        entry = Entry(
            id=uuid.uuid4().hex[:8],
            name=name,
            calendar=calendar,
            month=month,
            day=day,
            leap_month=leap_month if calendar == "lunar" else False,
            note=note,
        )
        entries.append(entry)
        save_entries(db_file, entries)
        return redirect_with_message("success", f"已添加 {name}")

    @app.post("/update/<entry_id>")
    def update_entry(entry_id: str):
        entries = load_entries(db_file)
        target = find_entry(entries, entry_id)
        if target is None:
            return redirect_with_message("error", f"未找到 ID: {entry_id}")

        try:
            name, calendar, month, day, leap_month, note = parse_entry_form()
        except Exception as exc:
            return redirect_with_message("error", str(exc), extra={"edit_id": entry_id}, anchor="editor")

        target.name = name
        target.calendar = calendar
        target.month = month
        target.day = day
        target.leap_month = leap_month
        target.note = note
        save_entries(db_file, entries)
        return redirect_with_message("success", f"已更新 {name}")

    @app.post("/delete/<entry_id>")
    def delete_entry(entry_id: str):
        entries = load_entries(db_file)
        left = [entry for entry in entries if entry.id != entry_id]
        if len(left) == len(entries):
            return redirect_with_message("error", f"未找到 ID: {entry_id}")
        save_entries(db_file, left)
        return redirect_with_message("success", "已删除记录")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="生日提醒可视化面板")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help=f"生日数据库路径（默认: {DEFAULT_DB_PATH}）")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    parser.add_argument("--port", type=int, default=8031, help="端口（默认 8031）")
    parser.add_argument("--debug", action="store_true", help="开启调试模式")
    args = parser.parse_args()

    app = create_app(Path(args.db))
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
