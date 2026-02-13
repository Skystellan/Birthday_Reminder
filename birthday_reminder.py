#!/usr/bin/env python3
"""Birthday reminder CLI with solar/lunar calendar support."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from lunardate import LunarDate
except ImportError:  # pragma: no cover - optional dependency in runtime
    LunarDate = None


DEFAULT_DB_PATH = Path(__file__).with_name("birthdays.json")


@dataclass
class Entry:
    id: str
    name: str
    calendar: str
    month: int
    day: int
    leap_month: bool = False
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "calendar": self.calendar,
            "month": self.month,
            "day": self.day,
            "leap_month": self.leap_month,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Entry":
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            calendar=str(payload["calendar"]),
            month=int(payload["month"]),
            day=int(payload["day"]),
            leap_month=bool(payload.get("leap_month", False)),
            note=str(payload.get("note", "")),
        )


def parse_month_day(value: str) -> tuple[int, int]:
    pieces = value.split("-")
    if len(pieces) != 2:
        raise argparse.ArgumentTypeError("日期格式必须是 MM-DD，例如 08-19")
    try:
        month, day = int(pieces[0]), int(pieces[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("日期必须是数字，例如 08-19") from exc
    try:
        # Use leap year for broadest validation (e.g. 02-29).
        dt.date(2024, month, day)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("无效日期，请检查月和日") from exc
    return month, day


def normalize_calendar(value: str) -> str:
    text = value.strip().lower()
    if text in {"solar", "gregorian", "阳历", "公历"}:
        return "solar"
    if text in {"lunar", "农历", "阴历"}:
        return "lunar"
    raise argparse.ArgumentTypeError("日历类型仅支持 solar/lunar 或 阳历/农历")


def load_entries(db_path: Path) -> list[Entry]:
    if not db_path.exists():
        return []
    with db_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError(f"{db_path} 数据格式错误，应为列表")
    return [Entry.from_dict(item) for item in raw]


def save_entries(db_path: Path, entries: list[Entry]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with db_path.open("w", encoding="utf-8") as f:
        json.dump([entry.to_dict() for entry in entries], f, ensure_ascii=False, indent=2)


def load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {}
    try:
        with state_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def save_state(state_path: Path, payload: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def lunar_to_solar(year: int, month: int, day: int, leap_month: bool) -> dt.date | None:
    if LunarDate is None:
        raise RuntimeError("缺少 lunardate 依赖，请先执行: uv sync")
    try:
        return LunarDate(year, month, day, leap_month).toSolarDate()
    except ValueError:
        # 闰月生日在非闰月年常见做法是按同月(非闰)庆祝，自动回退。
        if leap_month:
            try:
                return LunarDate(year, month, day, False).toSolarDate()
            except ValueError:
                return None
        return None


def birthday_on_year(entry: Entry, year: int) -> dt.date | None:
    if entry.calendar == "solar":
        if entry.month == 2 and entry.day == 29:
            try:
                return dt.date(year, 2, 29)
            except ValueError:
                return dt.date(year, 2, 28)
        try:
            return dt.date(year, entry.month, entry.day)
        except ValueError:
            return None
    if entry.calendar == "lunar":
        return lunar_to_solar(year, entry.month, entry.day, entry.leap_month)
    return None


def next_birthday(entry: Entry, start_date: dt.date) -> dt.date | None:
    this_year = birthday_on_year(entry, start_date.year)
    if this_year and this_year >= start_date:
        return this_year
    return birthday_on_year(entry, start_date.year + 1)


def send_notification(title: str, message: str) -> None:
    if sys.platform != "darwin":
        print("当前系统非 macOS，跳过桌面通知。")
        return
    esc_title = title.replace("\\", "\\\\").replace('"', '\\"')
    esc_msg = message.replace("\\", "\\\\").replace('"', '\\"')
    script = f'display notification "{esc_msg}" with title "{esc_title}"'
    subprocess.run(["osascript", "-e", script], check=False)


def format_calendar(entry: Entry) -> str:
    return "农历" if entry.calendar == "lunar" else "阳历"


def parse_iso_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%Y-%m-%d").date()


def due_entries_on_date(entries: list[Entry], target: dt.date) -> list[Entry]:
    due_entries: list[Entry] = []
    for entry in entries:
        date_on_target_year = birthday_on_year(entry, target.year)
        if date_on_target_year == target:
            due_entries.append(entry)
    return due_entries


def upcoming_entries(
    entries: list[Entry],
    start: dt.date,
    days: int,
) -> list[tuple[dt.date, Entry]]:
    within = dt.timedelta(days=days)
    upcoming: list[tuple[dt.date, Entry]] = []
    for entry in entries:
        nxt = next_birthday(entry, start)
        if not nxt:
            continue
        if nxt - start <= within:
            upcoming.append((nxt, entry))
    return sorted(upcoming, key=lambda item: item[0])


def send_birthday_notification(
    names: str,
    target: dt.date,
    *,
    once_per_day: bool = False,
    state_path: Path | None = None,
) -> bool:
    if once_per_day:
        if state_path is None:
            raise ValueError("启用每日去重通知时，必须提供状态文件路径")
        state = load_state(state_path)
        if state.get("last_notified_date") == target.isoformat():
            return False

    send_notification("生日提醒", f"今天记得祝 {names} 生日快乐")

    if once_per_day and state_path is not None:
        save_state(
            state_path,
            {
                "last_notified_date": target.isoformat(),
                "last_notified_names": names,
                "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
            },
        )
    return True


def command_add(args: argparse.Namespace) -> None:
    db_path = Path(args.db).expanduser().resolve()
    entries = load_entries(db_path)
    month, day = parse_month_day(args.date)
    calendar = normalize_calendar(args.calendar)
    if calendar == "lunar" and LunarDate is None:
        raise RuntimeError("添加农历生日需要 lunardate，请先执行: uv sync")
    entry = Entry(
        id=uuid.uuid4().hex[:8],
        name=args.name.strip(),
        calendar=calendar,
        month=month,
        day=day,
        leap_month=bool(args.leap_month),
        note=(args.note or "").strip(),
    )
    entries.append(entry)
    save_entries(db_path, entries)
    calendar_text = format_calendar(entry)
    leap_text = " (闰月)" if entry.calendar == "lunar" and entry.leap_month else ""
    print(f"已添加: [{entry.id}] {entry.name} {calendar_text} {entry.month:02d}-{entry.day:02d}{leap_text}")


def command_list(args: argparse.Namespace) -> None:
    db_path = Path(args.db).expanduser().resolve()
    entries = load_entries(db_path)
    if not entries:
        print("暂无生日记录。")
        return
    for entry in entries:
        calendar_text = format_calendar(entry)
        leap_text = " (闰月)" if entry.calendar == "lunar" and entry.leap_month else ""
        note_text = f" | 备注: {entry.note}" if entry.note else ""
        print(
            f"[{entry.id}] {entry.name} | {calendar_text} {entry.month:02d}-{entry.day:02d}{leap_text}{note_text}"
        )


def command_remove(args: argparse.Namespace) -> None:
    db_path = Path(args.db).expanduser().resolve()
    entries = load_entries(db_path)
    left = [entry for entry in entries if entry.id != args.id]
    if len(left) == len(entries):
        print(f"未找到 ID: {args.id}")
        return
    save_entries(db_path, left)
    print(f"已删除 ID: {args.id}")


def command_due(args: argparse.Namespace) -> None:
    db_path = Path(args.db).expanduser().resolve()
    entries = load_entries(db_path)
    target = parse_iso_date(args.date) if args.date else dt.date.today()
    due_entries = due_entries_on_date(entries, target)

    if not due_entries:
        print(f"{target.isoformat()} 没有生日提醒。")
        return

    names = "、".join(entry.name for entry in due_entries)
    print(f"{target.isoformat()} 今天过生日: {names}")
    for entry in due_entries:
        calendar_text = format_calendar(entry)
        print(f"- {entry.name} ({calendar_text} {entry.month:02d}-{entry.day:02d})")

    if args.notify:
        state_path: Path | None = None
        if args.notify_once_per_day:
            state_path = (
                Path(args.notify_state_file).expanduser().resolve()
                if args.notify_state_file
                else db_path.with_name("notify_state.json")
            )
        sent = send_birthday_notification(
            names,
            target,
            once_per_day=args.notify_once_per_day,
            state_path=state_path,
        )
        if args.notify_once_per_day and not sent:
            print(f"{target.isoformat()} 已通知过，跳过重复通知。")


def command_upcoming(args: argparse.Namespace) -> None:
    db_path = Path(args.db).expanduser().resolve()
    entries = load_entries(db_path)
    start = parse_iso_date(args.date) if args.date else dt.date.today()
    upcoming = upcoming_entries(entries, start, args.days)
    if not upcoming:
        print(f"从 {start.isoformat()} 起 {args.days} 天内没有生日提醒。")
        return
    for when, entry in upcoming:
        calendar_text = format_calendar(entry)
        print(f"{when.isoformat()} - {entry.name} ({calendar_text} {entry.month:02d}-{entry.day:02d})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="好友生日提醒工具（支持农历/阳历）")
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"生日数据库路径（默认: {DEFAULT_DB_PATH}）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="添加生日")
    add_parser.add_argument("--name", required=True, help="好友姓名")
    add_parser.add_argument(
        "--calendar",
        required=True,
        type=normalize_calendar,
        help="日历类型: solar/lunar 或 阳历/农历",
    )
    add_parser.add_argument("--date", required=True, help="生日（MM-DD）")
    add_parser.add_argument("--leap-month", action="store_true", help="仅农历：是否闰月")
    add_parser.add_argument("--note", help="备注")
    add_parser.set_defaults(func=command_add)

    list_parser = subparsers.add_parser("list", help="查看所有生日")
    list_parser.set_defaults(func=command_list)

    remove_parser = subparsers.add_parser("remove", help="按 ID 删除生日")
    remove_parser.add_argument("--id", required=True, help="生日记录 ID")
    remove_parser.set_defaults(func=command_remove)

    due_parser = subparsers.add_parser("due", help="查看某天是否有人生日")
    due_parser.add_argument("--date", help="目标日期（YYYY-MM-DD，默认今天）")
    due_parser.add_argument("--notify", action="store_true", help="同时触发桌面通知（macOS）")
    due_parser.add_argument(
        "--notify-once-per-day",
        action="store_true",
        help="同一天仅通知一次（需与 --notify 一起使用）",
    )
    due_parser.add_argument(
        "--notify-state-file",
        help="通知状态文件路径（默认与数据库同目录下 notify_state.json）",
    )
    due_parser.set_defaults(func=command_due)

    upcoming_parser = subparsers.add_parser("upcoming", help="查看未来 N 天内生日")
    upcoming_parser.add_argument("--days", type=int, default=30, help="未来天数，默认 30")
    upcoming_parser.add_argument("--date", help="起始日期（YYYY-MM-DD，默认今天）")
    upcoming_parser.set_defaults(func=command_upcoming)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
