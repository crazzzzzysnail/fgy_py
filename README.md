# 自动化签到任务脚本

这是一个基于Python的自动化任务执行脚本，可以通过解析HAR文件来模拟HTTP请求，并支持多任务并行执行、日志记录和WxPusher消息通知。

## 功能特性

- **多任务并行**: 使用线程池并行执行多个任务，提高效率。
- **HAR文件解析**: 自动解析HAR文件以构建HTTP请求，简化配置。
- **灵活的任务配置**: 通过 `tasks.json` 文件定义需要执行的任务列表、次数和间隔。
- **可配置的日志系统**:
  - 支持调试模式和简洁模式。
  - 日志同时输出到控制台和 `task.log` 文件。
- **WxPusher通知**: 在任务完成后，通过WxPusher发送成功或失败的通知。
- **集中化配置**: 所有可配置项都集中在 `.env` 文件中，方便管理。

## 如何使用

### 1. 准备HAR文件

直接使用网络抓包工具（如 Fiddler, Charles, ProxyPin）导出的 `.har` 文件作为请求模板。

### 2. 配置任务

编辑 `tasks.json` 文件，定义您要执行的任务。每个任务都是一个JSON对象，可以包含以下字段：

- `name`: (必需) 任务的名称，用于日志记录。
- `har_file`: (必需) 与此任务关联的HAR文件的路径。
- `count`: (可选) 任务执行的次数，默认为 `1`。
- `interval_seconds`: (可选) 每次执行之间的间隔时间（秒），默认为 `0`。

### 3. 配置环境变量

在项目根目录下创建一个名为 `.env` 的文件，并根据需要修改以下配置：

```dotenv
# --- 日志配置 ---
# 是否开启调试模式。True: 记录详细请求和响应信息; False: 只记录基本信息。
DEBUG_MODE=False
# 是否开启控制台简洁模式。True: 控制台只输出关键信息; False: 控制台输出所有信息。
CONSOLE_CONCISE_MODE=True

# --- WxPusher 配置 ---
# 默认从系统环境变量或者 .env 文件中获取配置。
# 如果不需要通知，请将值留空。
# 在这里填入你的 WxPusher 应用令牌 (在 https://wxpusher.zjiecode.com/admin/main/app/appToken 获取)
WXPUSHER_APP_TOKEN=""
# 在这里填入你的 WxPusher 用户 UID (在 https://wxpusher.zjiecode.com/admin/main/user/page 获取)
WXPUSHER_UIDS=""
```

### 4. 运行脚本

配置完成后，直接运行 `main.py` 即可：

```bash
python main.py
```

## 文件结构

```
.
├── .env                # 环境变量配置文件
├── config.py           # 配置加载模块
├── har/                # 存放HAR文件的目录
│   └── example.har
├── har_parser.py       # HAR文件解析器
├── logger_setup.py     # 日志系统配置
├── main.py             # 主执行脚本
├── notify.py           # WxPusher通知模块
├── request_sender.py   # HTTP请求发送器
├── status.json         # 存储脚本状态
├── tasks.json          # 任务定义文件
└── README.md           # 项目说明文档