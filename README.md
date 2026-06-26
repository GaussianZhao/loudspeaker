# loudspeaker

每周自动给自己发一封邮件，汇总本周 **GitHub Trending 周榜 Top 10** 项目，
并为每个项目附上一句中文说明（用本机 Claude CLI 生成）。邮件通过
[Agently CLI](https://www.npmjs.com/package/@tencent-qqmail/agently-cli) 发送。

## 它做什么

- 抓取 `github.com/trending?since=weekly`，取本周新增 star 最多的 10 个项目
- 用本机 **Claude Code CLI**（`claude -p`）把简介翻成中文一句话（失败自动降级为原文）
- 渲染成 HTML 富文本邮件，经 **Agently CLI** 发送
- 用 macOS **LaunchAgent** 每周定时触发（默认周一 09:00 Asia/Shanghai）
- 抓取/发送失败时发一封失败通知，避免静默漏发

## 文件

| 文件 | 说明 |
|------|------|
| `weekly_github_trending.py` | 主脚本：抓取 → 翻译 → 渲染 → 发送 |
| `install_launchagent.sh` | 探测路径、生成并加载 LaunchAgent 定时任务 |
| `config.env.example` | 配置模板（复制为 `config.env` 填真实值，后者不提交） |
| `DEPLOY.md` | 在 Mac 上的逐步部署说明 |
| `weekly-github-trending-email-prd.md` | 需求文档 |

## 快速开始

```bash
# 1) 装并登录两个 CLI
npm install -g @tencent-qqmail/agently-cli && agently-cli auth login
curl -fsSL https://claude.ai/install.sh | bash && claude   # 首次 /login

# 2) 配置
cp config.env.example config.env   # 编辑 RECIPIENT 等

# 3) 预览（不发送）
DRY_RUN=1 python3 weekly_github_trending.py

# 4) 装定时任务
chmod +x install_launchagent.sh && ./install_launchagent.sh
```

详见 [DEPLOY.md](DEPLOY.md)。

## 配置项

见 `config.env.example`：`RECIPIENT` / `TOP_N` / `TRANSLATE` / `CLAUDE_BIN` /
`SEND_WEEKDAY` / `SEND_HOUR` / `SEND_MINUTE`。运行时环境变量优先级高于 `config.env`。

## 说明

- 数据源是对 GitHub Trending 页面的解析，GitHub 改版时可能需要更新解析规则。
- 需要运行机器常开或可定时唤醒，否则关机时段的任务会顺延到下次唤醒补发。
