# 部署到 Mac mini

每周一 09:00（北京时间）自动发送一封 GitHub 周报邮件，内容为本周 trending 周榜
Top 10，含中文一句话简介（由本机 Claude CLI 生成）。

整套东西都要装在**实际跑任务的那台 Mac mini 上**：邮件授权（Agently）、Claude 登录、
定时任务，三者必须在同一台机器。

---

## 0. 拷贝文件到 Mac mini

把这三个文件放到 Mac mini 的同一个目录（示例用 `~/weekly-trending/`）：

- `weekly_github_trending.py`  — 主脚本
- `install_launchagent.sh`     — 定时任务安装脚本
- `DEPLOY.md`                  — 本文档

---

## 1. 装 Agently CLI 并登录（邮件发送通道）

```bash
npm install -g @tencent-qqmail/agently-cli
agently-cli auth login          # 浏览器里完成 QQ 邮箱授权
agently-cli +me                 # 看到账户信息即成功
```

> 需要 Node.js（建议 18+）。没有就先 `brew install node`。

## 2. 装 Claude CLI 并登录（生成中文简介）

```bash
curl -fsSL https://claude.ai/install.sh | bash    # 装到 ~/.local/bin/claude
# 如果装完 which claude 找不到，把 ~/.local/bin 加进 PATH：
#   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
claude                          # 首次启动按提示 /login 登录你的 Claude 账号，然后退出
claude -p "说: 你好"            # 能正常输出即说明 CLI 可用
```

> 不装 Claude 也能跑——只是简介会保持 GitHub 原始（多为英文）。装了就是中文。

## 3. 填配置

```bash
cd ~/weekly-trending            # 文件所在目录
cp config.env.example config.env
vi config.env                   # 至少把 RECIPIENT 改成你的收件邮箱
```

> `config.env` 已被 `.gitignore` 忽略，不会提交，放心填真实邮箱。

## 4. 安装定时任务

```bash
chmod +x install_launchagent.sh
./install_launchagent.sh        # 自动读取 config.env，生成并加载 LaunchAgent
```

脚本会自动探测 `python3` / `claude` 路径，生成并加载 LaunchAgent。
默认收件人 `you@example.com`、周一 09:00。要改：

```bash
RECIPIENT=you@example.com SEND_HOUR=8 SEND_WEEKDAY=1 ./install_launchagent.sh
```

（`SEND_WEEKDAY`：1=周一 … 6=周六，0/7=周日）

## 5. 立即验证（不用等到周一）

```bash
DRY_RUN=1 python3 weekly_github_trending.py     # 只预览，不发邮件、不调 Claude 翻译
launchctl start com.$USER.weekly-github-trending # 真实跑一次（会翻译+发邮件）
cat weekly_trending.log                          # 看运行结果/报错
```

---

## 常用维护

| 操作 | 命令 |
|------|------|
| 看下次是否已注册 | `launchctl list \| grep weekly-github-trending` |
| 手动立即发一次 | `launchctl start com.$USER.weekly-github-trending` |
| 改时间/收件人 | 重新跑 `install_launchagent.sh`（带新的 env 变量） |
| 临时停用 | `launchctl unload ~/Library/LaunchAgents/com.$USER.weekly-github-trending.plist` |
| 重新启用 | `launchctl load ~/Library/LaunchAgents/com.$USER.weekly-github-trending.plist` |
| 看日志 | `cat weekly_trending.log` |

## 环境变量（脚本可配置项）

| 变量 | 默认 | 说明 |
|------|------|------|
| `RECIPIENT` | `you@example.com` | 收件人 |
| `TOP_N` | `10` | 榜单数量 |
| `TRANSLATE` | `1` | 是否用 Claude 翻译中文简介（`0` 关闭） |
| `CLAUDE_BIN` | `claude` | Claude CLI 路径/命令名 |
| `DRY_RUN` | `0` | `1` = 只预览不发送 |

## 注意事项

- **关机/休眠**：若周一 9 点 Mac mini 没开机，macOS 会在下次唤醒后补跑一次（时间可能偏移，不会漏）。要严格准时，保持 Mac mini 常开或设自动唤醒。
- **登录失效**：Agently / Claude 的登录态可能过期；脚本对 Claude 失败会自动降级为英文简介，对 Agently 发送失败会发一封「抓取/发送失败」通知邮件。
- 数据源用 `curl` 抓取 `github.com/trending?since=weekly`，是页面解析，GitHub 改版可能需要更新解析规则。
