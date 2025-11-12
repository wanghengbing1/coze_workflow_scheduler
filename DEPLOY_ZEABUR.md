# Zeabur 部署与使用说明
本项目包含一个按日定时触发 Coze Workflow 的运行服务，核心脚本为 [`wewerss.py`](wewerss.py)。容器构建通过 [`Dockerfile`](Dockerfile)，依赖管理在 [`requirements.txt`](requirements.txt)。

功能概述
- 每天在固定时间点执行，时间可通过环境变量动态配置（如 SCHEDULE_TIME、TIMEZONE）。
- 执行报错时自动重试直到成功，采用指数退避并带随机抖动以缓解并发重试雪崩。
- 支持优雅关闭：在 Zeabur 停止或重启时收到终止信号后，服务会尽快退出，避免不一致状态。

必需与可选环境变量
- 必需：COZE_API_TOKEN（Coze API 访问令牌）
- 可选：WORKFLOW_ID（默认 7569877408963231763）
- 可选：SCHEDULE_TIME（默认 21:00，格式 HH:MM）
- 可选：TIMEZONE（默认 Asia/Shanghai，用于每日触发的时区）
- 可选：INITIAL_RETRY_DELAY（默认 5，单位秒）
- 可选：MAX_BACKOFF（默认 300，单位秒，指数退避上限）
- 可选：COZE_API_BASE_URL（显式指定 API 基础地址）
- 可选：COZE_REGION（设置为 cn 时自动使用 coze.cn）
- 可选：LOG_LEVEL（默认 INFO，可设为 DEBUG/INFO/WARN/ERROR）
- 可选：JITTER_MAX_SECONDS（默认 3，重试抖动最大秒数）
- 可选：SLEEP_CHUNK_SECONDS（默认 5，等待到下一次执行时的睡眠分片秒数）
- 可选：STOP_ON_SHUTDOWN（默认 true，收到终止信号后中断当前周期）

本地运行（说明性步骤）
1. 设置上述环境变量，至少包含 COZE_API_TOKEN。
2. 安装依赖，确保容器或本机具备 Python 3.11 及 tzdata（如需要时区数据库）。
3. 启动服务后保持常驻运行，服务会在指定时区的每日固定时间自动执行一次。

在 Zeabur 上部署
1. 新建服务并选择使用仓库中的 [`Dockerfile`](Dockerfile) 进行构建。
2. 在服务的环境变量配置页面添加上述变量，至少设置 COZE_API_TOKEN。
3. 保持服务常驻运行（规模至少 1 实例），以便守护进程能在每日固定时间触发。
4. 如需中国区加速，可设置 COZE_REGION=cn 或显式指定 COZE_API_BASE_URL。
5. 若需要特定时区，请设置 TIMEZONE，常见值示例：Asia/Shanghai、UTC 等。

运行与运维建议
- 日志级别可通过 LOG_LEVEL 动态调节；在生产环境推荐 INFO 或 WARN。
- 当接口返回错误时，服务会自动重试直到成功；可通过 INITIAL_RETRY_DELAY、MAX_BACKOFF 与 JITTER_MAX_SECONDS 调整重试节奏。
- 优雅关闭：Zeabur 在重启或停止时会发送终止信号，服务能感知并尽快退出。
- 若需调整等待至下一次执行时的日志和睡眠节奏，可通过 SLEEP_CHUNK_SECONDS 控制。

时间与时区注意事项
- SCHEDULE_TIME 使用 HH:MM 24 小时格式，并按 TIMEZONE 进行每日触发计算。
- 若容器基础镜像缺少时区数据库，建议安装 tzdata（已在 [`requirements.txt`](requirements.txt) 中添加）。
- 如需跨时区部署，确保 TIMEZONE 设置与业务期望一致。

故障排查指南
- 启动即退出并提示缺少令牌：检查 COZE_API_TOKEN 环境变量是否正确设置。
- 提示无法导入 cozepy：确认依赖已安装且网络可访问 PyPI。
- 重试过于频繁或日志刷屏：调大 INITIAL_RETRY_DELAY、MAX_BACKOFF 或减少 JITTER_MAX_SECONDS。
- 未按预期时间触发：检查 SCHEDULE_TIME 与 TIMEZONE 配置是否正确。

安全建议
- 将 COZE_API_TOKEN 作为机密变量存储，不要硬编码到仓库。
- 根据需求设置最小权限的令牌，避免过度授权。

文件结构速览
- 业务入口脚本：[`wewerss.py`](wewerss.py)
- 依赖列表：[`requirements.txt`](requirements.txt)
- 容器构建文件：[`Dockerfile`](Dockerfile)

完成度与后续扩展
- 已实现每日定时、失败重试与 Zeabur 兼容的优雅关闭。
- 如需支持更复杂的调度（如多时间点或工作日/节假日规则），可进一步扩展为 cron 表达式或引入调度框架。
- 如需可观测性增强（指标、报警），可接入外部日志与监控服务。