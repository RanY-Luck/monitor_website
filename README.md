# 🔍 Website Monitor Bot

这是一个简单的网站API状态监控工具。它会定期检查指定的 URL，验证返回的 JSON 数据是否符合预期，并通过企业微信机器人发送精美的 Markdown 报告。

## ✨ 功能特点

- **⏱️ 定时监控**: 可配置检查间隔（默认 60秒）。
- **📊 智能报告**: 仅在发现异常或状态变更时推送，避免消息打扰（可配置）。
- **🎨 精美排版**: 企业微信推送采用 Markdown 格式，清晰展示状态概览和详情。
- **🐳 Docker 支持**: 提供 Dockerfile 和 docker-compose.yml，一键部署。
- **🛡️ 严格校验**: 不仅检查 HTTP 状态码，还检查 JSON 响应内容是否匹配预期。

## 🛠️ 快速开始

### 方式一：Docker 部署 (推荐)

1. **配置环境变量**
   复制示例配置并修改：
   ```bash
   cp .env.example .env
   ```
   修改 `.env` 文件，填入你的配置：
   - `WEBHOOK_URL`: 企业微信机器人地址
   - `MONITOR_URL_PROD`: 正式服 API 地址
   - `MONITOR_URL_TEST`: 测试服 API 地址
   - `MONITOR_INTERVAL`: 检查间隔（秒）

2. **启动服务**
   ```bash
   docker-compose up -d --build
   ```

### 方式二：本地运行

1. **安装依赖**
   需要 Python 3.9+
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**
   同上，创建并修改 `.env` 文件。

3. **运行**
   ```bash
   python monitor.py
   ```

4. **Docker 部署 (推荐)**

**构建镜像：**
```bash
# 构建
docker build -t monitor_website:latest .
# 导出
docker save -o monitor_website.tar monitor_website:latest
# 导入
docker load -i monitor_website.tar
```

**运行容器：**

1. 确保目录下有配置文件 `.env` (可从 `.env.example` 复制修改)。
2. 执行启动命令：
   ```bash
   docker run -d \
     --name monitor_website \
     --restart always \
     -v $(pwd)/monitor.log:/app/monitor.log \
     monitor_website:latest
   ```
   *(注：如果您已将 `.env` 打包在镜像中，则无需 `--env-file` 参数；否则请在宿主机创建 `.env` 并添加 `--env-file .env`)*


## ⚙️ 配置说明 (.env)

| 变量名 | 说明 | 默认值/示例 |
| :--- | :--- | :--- |
| `WEBHOOK_URL` | 企业微信机器人的 Webhook 地址 | `https://qyapi.weixin.qq.com/...` |
| `MONITOR_URL_PROD` | 监控目标1（正式服）URL | `https://api.example.com/...` |
| `MONITOR_URL_TEST` | 监控目标2（测试服）URL | `https://test.example.com/...` |
| `MONITOR_INTERVAL` | 循环监控的间隔时间（秒） | `60` |
| `REPORT_ONLY_ON_ERROR` | 是否仅在报错时推送 (true/false) | `true` |

## 📂 项目结构

```
.
├── bot.py           # 企业微信通知模块
├── monitor.py       # 核心监控逻辑
├── logger.py        # 日志配置
├── .env             # 配置文件 (不要提交到 git)
├── .env.example     # 配置文件模板
├── Dockerfile       # Docker 构建文件
├── docker-compose.yml # Docker 编排文件
└── requirements.txt # Python 依赖
```

## 📝 监控逻辑

1. 每隔 `MONITOR_INTERVAL` 秒检查一次配置的 URL。
2. 验证：
   - HTTP 状态码是否为 200。
   - 响应内容是否为有效 JSON。
   - 响应内容是否完全匹配预期 `{'statusCode': 200, 'message': None, 'data': '1'}`。
3. 如果发现任何异常（或配置为总是推送），将通过企业微信发送报告。

## 🤝 贡献
欢迎提交 Issue 或 PR 改进此项目。
