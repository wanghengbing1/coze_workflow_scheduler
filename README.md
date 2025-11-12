# Coze Workflow Daily Runner
本项目提供一个按日定时触发 Coze Workflow 的常驻服务，入口脚本为 [`wewerss.py`](wewerss.py)。
它支持动态配置时间、失败自动重试直到成功，并适配 Zeabur 部署。

## 主要特性
- 每日固定时间调度：通过环境变量 SCHEDULE_TIME（HH:MM）与 TIMEZONE 控制
- 失败自动重试：指数退避 + 随机抖动，直到成功
- 优雅关闭：捕获终止信号，确保在平台停止或重启时尽快退出
- 容器化与云部署：提供 [`Dockerfile`](Dockerfile) 与部署说明 [`DEPLOY_ZEABUR.md`](DEPLOY_ZEABUR.md)

## 文件结构
- 业务入口脚本：[`wewerss.py`](wewerss.py)
- 依赖清单：[`requirements.txt`](requirements.txt)
- 容器构建文件：[`Dockerfile`](Dockerfile)
- 部署说明：[`DEPLOY_ZEABUR.md`](DEPLOY_ZEABUR.md)

## 环境变量
必需：
- COZE_API_TOKEN：Coze API 访问令牌（必须通过平台或运行时注入）

可选（含默认值）：
- WORKFLOW_ID=7569877408963231763
- SCHEDULE_TIME=21:00
- TIMEZONE=Asia/Shanghai
- INITIAL_RETRY_DELAY=5
- MAX_BACKOFF=300
- COZE_API_BASE_URL（显式指定时生效）
- COZE_REGION（设为 cn 时自动使用 coze.cn）
- LOG_LEVEL=INFO
- JITTER_MAX_SECONDS=3
- SLEEP_CHUNK_SECONDS=5
- STOP_ON_SHUTDOWN=true

这些变量由服务在启动时从环境中读取，详见 [`wewerss.py`](wewerss.py)。也可参考容器内的默认声明，见 [`Dockerfile`](Dockerfile)。

## 本地运行
1. 准备 Python 3.11 环境，并安装依赖（参考 [`requirements.txt`](requirements.txt)）。
2. 设置环境变量（至少 COZE_API_TOKEN）。
3. 运行入口脚本以启动常驻服务（入口脚本：[`wewerss.py`](wewerss.py)）。

服务会在设定的时区与时间点每日执行一次；如当天时间已过，则顺延至次日。

## Docker 部署
- 使用 [`Dockerfile`](Dockerfile) 构建镜像；运行时通过平台或命令行注入环境变量。
- 镜像启动后将常驻运行，等待每日触发时间执行工作流。

## 在 Zeabur 上部署
- 详细步骤与运维建议见 [`DEPLOY_ZEABUR.md`](DEPLOY_ZEABUR.md)。
- 在服务的环境变量面板中设置上述键值（至少 COZE_API_TOKEN）。
- 如需中国区域加速，可设置 COZE_REGION=cn 或显式指定 COZE_API_BASE_URL。

## 故障排查
- 缺少令牌导致退出：检查 COZE_API_TOKEN 是否正确配置。
- 无法导入依赖：确认网络可访问 PyPI 并安装了 [`requirements.txt`](requirements.txt) 中的依赖。
- 重试过于频繁：调大 INITIAL_RETRY_DELAY、MAX_BACKOFF 或减少 JITTER_MAX_SECONDS。
- 未按预期时间触发：检查 SCHEDULE_TIME 与 TIMEZONE 设置是否符合期望。

## 安全建议
- 将 COZE_API_TOKEN 作为机密变量存储，避免硬编码。
- 令牌权限遵循最小化原则，仅授予必要范围。

## 许可
若无特别声明，默认以 MIT 许可分发；可根据你的合规需求调整。

## 致谢
感谢 Coze 平台与开源社区的支持。