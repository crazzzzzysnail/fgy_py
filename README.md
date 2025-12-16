# 自动化签到助手

基于 Python 的自动化任务执行工具。通过解析 HAR 文件模拟网络请求，支持多任务并行执行、状态记录及消息推送。

## ✨ 核心特性

- **简单易用**: 直接解析抓包导出的 `.har` 文件，无需手动编写请求代码。
- **高效并行**: 使用线程池并发执行多个任务。
- **灵活配置**: 支持自定义任务执行次数、间隔时间及成功/失败提示。
- **消息通知**: 任务完成后自动推送 HTML 格式的统计报告（支持 WxPusher）。
- **状态追踪**: 自动记录累计签到天数及奖励情况。

## 🚀 快速开始

### 1. 准备 HAR 文件
使用抓包工具（如 Fiddler, Charles, ProxyPin）导出 `.har` 文件，并放入 `har/` 目录。

### 2. 配置任务 (`tasks.json`)
定义需要执行的任务列表。
- `name`: (必需) 任务的名称，用于日志记录。
- `har_file`: (必需) 与此任务关联的HAR文件的路径。
- `count`: (可选) 任务执行的次数，默认为 `1`。
- `interval_seconds`: (可选) 每次执行之间的间隔时间（秒），默认为 `0`。
- `success_msg`: (可选) 执行成功自定义通知信息。
- `fail_msg`: (可选) 执行失败自定义通知信息。
```json
[
  {
    "name": "每日签到",
    "har_file": "har/signin.har",
    "count": 1,
    "interval_seconds": 0,
    "success_msg": "签到成功",
    "fail_msg": "签到失败"
  }
]
```

### 3. 配置环境 (`.env`)
在项目根目录创建 `.env` 文件，配置通知和日志选项。
```ini
# --- WxPusher 通知配置 ---
WXPUSHER_APP_TOKEN="AT_xxx..."
WXPUSHER_UIDS="UID_xxx..." # 多UID使用逗号分隔

# --- 日志设置 ---
DEBUG_MODE=False          # 是否开启调试日志
CONSOLE_CONCISE_MODE=True # 控制台是否仅显示关键信息
```

### 4. 运行脚本
```bash
python main.py
```

## 📂 项目结构

```text
.
├── .env                # 环境变量
├── config.py           # 全局配置
├── har/                # 存放HAR文件
│   └── example.har
├── har_parser.py       # HAR文件解析
├── logger_setup.py     # 日志系统
├── main.py             # 程序入口
├── notify.py           # 通知模块
├── request_sender.py   # 请求发送
├── status.json         # 运行状态记录
├── tasks.json          # 任务定义文件
└── README.md           # 项目说明文档
```