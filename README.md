# 生辰灯塔（农历 / 阳历生日提醒）

`生辰灯塔` 是一个本地生日管理项目，支持：

- 录入好友生日，区分阳历和农历
- 每年自动换算并提醒（农历自动转当年阳历日期）
- 命令行、网页和桌面应用三种使用方式

## 1) 使用 uv 安装依赖

```bash
cd "/Users/skystellan/Documents/New project"
uv sync
```

## 2) 命令行模式

添加生日：

```bash
uv run python birthday_reminder.py add --name "小明" --calendar solar --date 08-19
uv run python birthday_reminder.py add --name "小红" --calendar lunar --date 01-03
uv run python birthday_reminder.py add --name "小李" --calendar lunar --date 04-12 --leap-month
```

查看 / 删除：

```bash
uv run python birthday_reminder.py list
uv run python birthday_reminder.py remove --id <ID>
```

提醒相关：

```bash
uv run python birthday_reminder.py due --notify
uv run python birthday_reminder.py upcoming --days 30
```

## 3) 可视化网页

启动：

```bash
uv run python web_app.py --host 127.0.0.1 --port 8031
```

浏览器打开：

```text
http://127.0.0.1:8031
```

功能包括：

- 仪表盘统计（总人数、今日生日、农历/阳历数量）
- 录入表单（姓名、类型、生日、闰月、备注）
- 今天提醒和未来 30 天预览
- 未来 12 个月分布图
- 全部记录表格、编辑与删除

## 4) 桌面应用（macOS）

直接启动桌面版：

```bash
uv run python desktop_app.py
```

说明：

- 在应用内嵌窗口中直接显示界面（不依赖浏览器）
- 启动时会自动检查“今天生日”并触发系统通知（同一天只提醒一次）
- 默认数据文件位于 `~/Library/Application Support/生辰灯塔/birthdays.json`

仅测试场景可用无窗口模式：

```bash
uv run python desktop_app.py --headless
```

打包成 `.app`：

```bash
./scripts/build_macos_app.sh
```

生成路径：

```text
dist/生辰灯塔.app
```

打包脚本会自动：

- 生成并注入 `.icns` 图标
- 写入 Finder / 启动台应用名与 Bundle 元信息

## 5) 导入已有数据到桌面应用

将当前项目里的生日数据导入桌面应用默认目录：

```bash
./scripts/import_data_to_desktop_app.sh
```

也可指定来源文件：

```bash
./scripts/import_data_to_desktop_app.sh /path/to/birthdays.json
```

## 6) 自动提醒（launchd）

推荐使用 macOS `launchd`（默认每天 09:00）：

```bash
./scripts/install_launchd_reminder.sh
```

自定义时间（例如每天 08:30）：

```bash
./scripts/install_launchd_reminder.sh 8 30
```

移除自动提醒：

```bash
./scripts/uninstall_launchd_reminder.sh
```

如果你仍然想用 `cron`，可用下面命令：

```cron
0 9 * * * /bin/zsh -lc 'cd /Users/skystellan/Documents/New\ project && uv run python birthday_reminder.py --db "$HOME/Library/Application Support/生辰灯塔/birthdays.json" due --notify --notify-once-per-day --notify-state-file "$HOME/Library/Application Support/生辰灯塔/notify_state.json"'
```

编辑 crontab：

```bash
crontab -e
```

## 7) 数据文件

默认生日数据库（命令行和网页）：

```text
/Users/skystellan/Documents/New project/birthdays.json
```

桌面应用默认数据库：

```text
~/Library/Application Support/生辰灯塔/birthdays.json
```

可通过 `--db` 自定义：

```bash
uv run python birthday_reminder.py --db /path/to/your_birthdays.json list
uv run python web_app.py --db /path/to/your_birthdays.json
uv run python desktop_app.py --db /path/to/your_birthdays.json
uv run python birthday_reminder.py --db /path/to/your_birthdays.json due --notify --notify-once-per-day
```

## 8) 规则说明

- 农历生日：每年换算到对应阳历后提醒。
- 农历闰月生日：非闰月年份会回退为同月非闰月提醒。
- 阳历 `02-29`：非闰年按 `02-28` 提醒。
