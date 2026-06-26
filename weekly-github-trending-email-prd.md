# 需求文档：GitHub 周度热门项目邮件推送

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.1 |
| 创建日期 | 2026-06-26 |
| 更新日期 | 2026-06-26 |
| 负责人 | zhinuo（wszzn6@gmail.com） |
| 发件邮箱 | your-alias@agent.qq.com（固定） |
| 收件邮箱 | 可配置（默认 your-alias@agent.qq.com） |
| 发送通道 | Agently CLI（`@tencent-qqmail/agently-cli`） |

### 已确认决策（v1.1）
- 发件人固定为 `your-alias@agent.qq.com`；**收件人可配置**。
- 榜单口径：**综合榜**（不限语言/主题）。
- 邮件格式：**HTML 富文本**。
- 发送时间：**可配置**（默认周一 09:00 Asia/Shanghai）。

---

## 1. 背景与目标

希望每周自动收到一封邮件，汇总过去一周 GitHub 上热度最高的前 10 个项目，并附上每个项目「大概是做什么的」的简短说明，方便快速跟进开源动态，无需手动刷 GitHub Trending。

**核心目标：** 每周一封、低维护、内容一眼能看懂、可点击直达仓库。

---

## 2. 范围

### 2.1 在范围内
- 抓取过去一周 GitHub 热度最高的项目并排名取前 10。
- 为每个项目生成一句话功能说明。
- 按固定格式渲染成邮件并定时发送到指定邮箱。

### 2.2 不在范围内（首期）
- 按编程语言/主题分类的多份榜单（**已确认只做综合榜**）。
- 邮件内的交互（订阅管理、退订页面等）。
- 历史榜单归档与趋势对比。
- 群发 / 多收件人列表管理（收件人虽可配置，但首期按单一收件人处理）。

---

## 3. 功能需求

### 3.1 数据采集（Data Source）

**热度定义：** 以「过去 7 天内新增 star 数」作为主要排序指标（即 GitHub Trending 的周榜口径），而非仓库总 star 数，以反映「本周热度」。

候选数据来源（按优先级）：
1. **GitHub Search API**：`GET /search/repositories`，用 `created:` 或 `pushed:` 配合 `sort=stars` 做近似；更精确的周增量需自行计算。
2. **GitHub Trending 周榜**：`https://github.com/trending?since=weekly`（无官方 API，需解析页面或用第三方镜像 API，如 `ghapi`/非官方 trending API）。
3. 兜底：若当周抓取失败，发送一封说明邮件而非空邮件。

> 说明：GitHub 官方未提供「周新增 star」的直接接口，需在采集层做近似或增量计算，此为关键技术点，详见第 6 节。

**字段需求（每个项目）：**
| 字段 | 说明 | 必填 |
|------|------|------|
| 仓库名 | `owner/repo` | 是 |
| 仓库链接 | HTTPS URL | 是 |
| 一句话简介 | 该项目大概做什么 | 是 |
| 主要语言 | 如 Python、Rust | 否 |
| 本周新增 star | 用于排序与展示 | 是 |
| 累计 star | 参考热度 | 否 |

### 3.2 内容生成

- **排名**：按「本周新增 star」降序取前 10。
- **一句话简介**：优先取仓库的 `description` 字段；若描述为空或过于简略，用 LLM 基于 README 摘要生成一句中文说明（≤ 40 字）。
- **语言一致性**：项目简介统一输出中文（项目名/技术名保留英文）。

### 3.3 邮件渲染

- **主题（Subject）**：`GitHub 周报 · {YYYY-MM-DD} 本周热门 Top 10`
- **正文格式**：**HTML 富文本**（带链接、加粗、排版清晰），纯文本作为兜底。
- **每条结构**：
  ```
  N. owner/repo  (语言 · 本周 +X★)
     👉 https://github.com/owner/repo
     简介：……
  ```
- **页脚**：注明数据口径（过去 7 天新增 star）与生成时间。

### 3.4 发送

- 通过 `agently-cli` 发送，发件人固定 `your-alias@agent.qq.com`，**收件人取配置项 `RECIPIENT`**。
- 参考命令（具体参数以 `agently-cli message --help` 为准）：
  ```bash
  agently-cli message send \
    --to "${RECIPIENT}" \
    --subject "GitHub 周报 · 2026-06-26 本周热门 Top 10" \
    --html "<已渲染的正文>"
  ```

### 3.5 可配置项（Config）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `RECIPIENT` | 收件人邮箱 | `your-alias@agent.qq.com` |
| `SEND_CRON` | 发送时间（cron 表达式） | `0 9 * * 1`（周一 09:00） |
| `TIMEZONE` | 时区 | `Asia/Shanghai` |
| `TOP_N` | 榜单数量 | `10` |

---

## 4. 非功能需求

| 类别 | 要求 |
|------|------|
| 定时 | 每周固定一次（建议 **周一 09:00**，时区 Asia/Shanghai，可调） |
| 可靠性 | 抓取/发送失败需重试，最终失败也要发一封失败通知，避免「静默漏发」 |
| 配额 | 受 Agently 限制：每日发送 ≤ 50 封、每小时 ≤ 200 次请求、每分钟 ≤ 10 次（本需求每周 1 封，远低于上限） |
| 幂等 | 同一周不重复发送（用「年-周」标记去重） |
| 可维护 | 数据源、收件人、发送时间、Top N 数量均为可配置项 |
| 日志 | 记录每次运行的时间、抓取结果数量、发送状态 |

---

## 5. 调度方案（建议）

可选其一：
1. **Claude Code 定时任务 / cron 路由**：用 `/schedule` 创建每周一的云端定时 agent，自动执行抓取 → 渲染 → 发送。
2. **本机 crontab**：`0 9 * * 1` 触发一个脚本完成全流程。
3. **GitHub Actions**：`schedule: cron` 触发，适合脚本托管在仓库时。

> 推荐方案 1，与当前 Agently CLI 环境最贴合，免维护本机调度。

---

## 6. 关键技术点 / 待确认问题

### 已确认
- 榜单：综合榜 ✅
- 邮件：HTML 富文本 ✅
- 收件人：可配置 ✅ ；发送时间：可配置 ✅

### 仍待确认
1. **「周热度」口径**：GitHub 无官方周增量 star 接口。
   - 方案 A：解析 `github.com/trending?since=weekly`（最贴近直觉，但依赖页面结构）。
   - 方案 B：每周自存一次各热门仓库 star 数，下周做差值（更准但需持久化）。
   - **待确认**：能接受用 Trending 页面解析（方案 A）作为首期方案吗？
2. **简介生成**：是否允许用 LLM 兜底生成中文简介，还是只用 GitHub 原始 description（可能为空/英文）？

---

## 7. 验收标准

- [ ] 每周在约定时间收到 1 封邮件，主题含当周日期。
- [ ] 邮件含正好 10 个项目，按本周热度降序。
- [ ] 每个项目有可点击链接 + 一句话中文简介 + 本周新增 star。
- [ ] 抓取或发送失败时，能收到一封失败说明邮件。
- [ ] 同一周不重复收到多封。

---

## 8. 里程碑（建议）

| 阶段 | 交付物 |
|------|--------|
| M1 | 数据采集脚本，能输出本周 Top 10 结构化数据 |
| M2 | 邮件渲染 + `agently-cli` 发送，手动跑通一次 |
| M3 | 接入定时调度，自动每周发送 |
| M4 | 失败重试 / 通知 + 去重，稳定运行 |

---

## 9. 实现记录（v1.2）

**部署模型：** 全部组件运行在用户的 **Mac mini**（与本次开发机不同的另一台机器）。
邮件授权（Agently）、Claude 登录、定时任务三者必须同机。

| 组件 | 文件 / 位置 | 状态 |
|------|-----------|------|
| 采集 + 翻译 + 渲染 + 发送脚本 | `weekly_github_trending.py` | ✅ 已实现，发送链路已真实跑通 |
| 定时任务安装脚本 | `install_launchagent.sh` | ✅ 自动探测路径、生成并加载 LaunchAgent |
| 部署文档 | `DEPLOY.md` | ✅ Mac mini 上的逐步操作 |
| 运行日志 | `weekly_trending.log` | ✅ |

**处理链路：** `curl` 抓取 `trending?since=weekly` → 取 Top 10 → 按本周新增 star 降序
→ **调用本机 `claude -p` 批量生成中文一句话简介**（失败/未登录则降级为原始描述）
→ HTML 富文本 → `agently-cli message +send`（两段式确认）→ 失败兜底发通知邮件。

**中文简介（已落地）：** 用 Mac mini 上已登录的 **Claude Code CLI**（`claude -p` 打印模式）
翻译，无需额外 API key。开关 `TRANSLATE`、路径 `CLAUDE_BIN` 可配置；任何失败都会
静默降级为 GitHub 原始描述，不影响发送。

**常用操作（在 Mac mini 上）：**
- 预览不发送：`DRY_RUN=1 python3 weekly_github_trending.py`
- 立即真实发一次：`launchctl start com.$USER.weekly-github-trending`
- 改收件人/时间：带 env 重跑 `install_launchagent.sh`
- 停用：`launchctl unload ~/Library/LaunchAgents/com.$USER.weekly-github-trending.plist`

详见 `DEPLOY.md`。
