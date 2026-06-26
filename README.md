# loudspeaker

每周自动给自己发一封邮件，汇总本周 **GitHub Trending 周榜 Top 10** 项目，
并为每个项目附上一句中文说明（用本机 Claude CLI 生成）。邮件通过
[Agently CLI](https://www.npmjs.com/package/@tencent-qqmail/agently-cli) 发送，
macOS **LaunchAgent** 定时触发。

## 特性

- 抓取 `github.com/trending?since=weekly`，取本周新增 star 最多的 10 个项目
- 用本机 **Claude Code CLI**（`claude -p`）把简介翻成中文一句话，失败自动降级为原文
- 渲染成 HTML 富文本邮件，经 **Agently CLI** 发送
- macOS **LaunchAgent** 每周定时（默认周一 09:00 Asia/Shanghai，可配）
- 抓取/发送失败时发一封失败通知，避免静默漏发

## 快速开始

```bash
# 1) 装并登录两个 CLI
npm install -g @tencent-qqmail/agently-cli && agently-cli auth login
curl -fsSL https://claude.ai/install.sh | bash && claude   # 首次 /login

# 2) 配置（复制模板，填入真实邮箱；config.env 不会提交）
cp config.env.example config.env && vi config.env

# 3) 预览（不发送）
DRY_RUN=1 python3 weekly_github_trending.py

# 4) 装定时任务
chmod +x install_launchagent.sh && ./install_launchagent.sh
```

完整步骤见 [docs/DEPLOY.md](docs/DEPLOY.md)。

## 仓库结构

| 路径 | 说明 |
|------|------|
| `weekly_github_trending.py` | 主脚本：抓取 → 翻译 → 渲染 → 发送 |
| `install_launchagent.sh` | 探测路径、生成并加载 LaunchAgent 定时任务 |
| `config.env.example` | 配置模板（复制为 `config.env` 填真实值，后者被忽略不提交） |
| `docs/DEPLOY.md` | 在 Mac 上的逐步部署说明 |
| `docs/PRD.md` | 需求文档 |

## 配置项

在 `config.env` 里设置（运行时同名环境变量优先级更高）：

| 变量 | 默认 | 说明 |
|------|------|------|
| `RECIPIENT` | `you@example.com` | 收件人邮箱 |
| `TOP_N` | `10` | 榜单数量 |
| `TRANSLATE` | `1` | 是否用 Claude 生成中文简介（`0` 关闭） |
| `CLAUDE_BIN` | `claude` | Claude CLI 命令名/路径 |
| `SEND_WEEKDAY` / `SEND_HOUR` / `SEND_MINUTE` | `1` / `9` / `0` | 发送时间（1=周一 … 0/7=周日） |

## 说明

- 数据源是对 GitHub Trending 页面的解析，GitHub 改版时可能需要更新解析规则。
- 需要运行机器常开或可定时唤醒，否则关机时段的任务会顺延到下次唤醒补发。
- 抓取用 `curl`（走系统证书校验），仅依赖 Python 标准库，无需 pip 安装。
