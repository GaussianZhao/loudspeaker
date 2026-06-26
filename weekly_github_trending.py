#!/usr/bin/env python3
"""Weekly GitHub trending email.

Fetches the GitHub weekly trending board, renders the top-N repos as an HTML
email, and sends it through Agently CLI (agently-cli message +send).

Config via environment variables:
  RECIPIENT   recipient email           (default: you@example.com)
  TOP_N       number of repos           (default: 10)
  TIMEZONE    label only, for footer    (default: Asia/Shanghai)
  DRY_RUN     "1" to render but not send (default: 0)

Usage:
  python3 weekly_github_trending.py              # fetch, render, send
  DRY_RUN=1 python3 weekly_github_trending.py    # fetch + render only
"""
from __future__ import annotations

import html
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

TRENDING_URL = "https://github.com/trending?since=weekly"
USER_AGENT = "Mozilla/5.0 (weekly-trending-bot)"


def _load_config() -> None:
    """Load KEY=VALUE pairs from config.env next to this script into the
    environment (without overriding values already set in the environment)."""
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.env")
    if not os.path.exists(cfg):
        return
    with open(cfg, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_config()

RECIPIENT = os.environ.get("RECIPIENT", "you@example.com")
TOP_N = int(os.environ.get("TOP_N", "10"))
TZ_LABEL = os.environ.get("TIMEZONE", "Asia/Shanghai")
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

# Chinese-summary translation via the Claude Code CLI (print mode).
# TRANSLATE=0 disables it; CLAUDE_BIN overrides the binary path/name.
TRANSLATE = os.environ.get("TRANSLATE", "1") == "1"
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")


def fetch_html(url: str) -> str:
    # Use curl: verifies certs via the system trust store and avoids the
    # CERTIFICATE_VERIFY_FAILED issues seen with some macOS Python builds.
    p = subprocess.run(
        ["curl", "-sSL", "--fail", "--max-time", "60", "-A", USER_AGENT, url],
        capture_output=True, text=True, timeout=70,
    )
    if p.returncode != 0:
        raise RuntimeError(f"curl failed ({p.returncode}): {p.stderr.strip()}")
    return p.stdout


def _clean(text: str) -> str:
    """Strip tags + collapse whitespace + unescape HTML entities."""
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_trending(page: str) -> list[dict]:
    rows = page.split('<article class="Box-row">')[1:]
    repos: list[dict] = []
    for row in rows:
        # repo path: <h2 ...><a href="/owner/repo" ...>
        m = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"', row)
        if not m:
            continue
        full = m.group(1).strip().strip("/")
        if full.count("/") != 1:
            continue

        desc_m = re.search(r'<p[^>]*class="col-9[^"]*"[^>]*>(.*?)</p>', row, re.S)
        description = _clean(desc_m.group(1)) if desc_m else ""

        lang_m = re.search(r'<span itemprop="programmingLanguage">(.*?)</span>', row, re.S)
        language = _clean(lang_m.group(1)) if lang_m else ""

        total_m = re.search(r'href="/' + re.escape(full) + r'/stargazers"[^>]*>(.*?)</a>', row, re.S)
        total_stars = _clean(total_m.group(1)) if total_m else ""

        week_m = re.search(r'([\d,]+)\s*stars?\s*this\s*week', row)
        week_stars = week_m.group(1) if week_m else ""

        repos.append({
            "full": full,
            "url": f"https://github.com/{full}",
            "description": description,
            "language": language,
            "total_stars": total_stars,
            "week_stars": week_stars,
        })
        if len(repos) >= TOP_N:
            break

    # Order by weekly new stars (desc), per the PRD acceptance criterion.
    def _wk(r: dict) -> int:
        return int(r["week_stars"].replace(",", "")) if r["week_stars"] else 0

    repos.sort(key=_wk, reverse=True)
    return repos


def translate_descriptions(repos: list[dict]) -> None:
    """Rewrite each repo['description'] into a short Chinese one-liner using the
    Claude Code CLI. Best-effort: on any failure the original text is kept."""
    if not (TRANSLATE and repos):
        return
    numbered = "\n".join(
        f"{i}. {r['full']}: {r['description'] or '(no description)'}"
        for i, r in enumerate(repos, 1)
    )
    prompt = (
        "下面是若干 GitHub 项目的名称与英文简介。请为每个项目用中文写一句"
        "不超过 35 字的「大概是做什么」的说明，保留专有名词/技术名英文原文，"
        "已是中文的精简即可。\n"
        f"严格只输出 {len(repos)} 行，每行格式为「序号. 中文说明」，不要任何额外文字。\n\n"
        f"{numbered}"
    )
    try:
        p = subprocess.run(
            [CLAUDE_BIN, "-p", prompt],
            capture_output=True, text=True, timeout=180,
        )
        if p.returncode != 0 or not p.stdout.strip():
            return
        parsed: dict[int, str] = {}
        for line in p.stdout.splitlines():
            m = re.match(r"\s*(\d+)\s*[.、)]\s*(.+?)\s*$", line)
            if m:
                parsed[int(m.group(1))] = m.group(2).strip()
        for i, r in enumerate(repos, 1):
            if parsed.get(i):
                r["description"] = parsed[i]
    except Exception:  # noqa: BLE001 — translation is optional, never block sending
        return


def render_html(repos: list[dict], date_str: str) -> str:
    items = []
    for i, r in enumerate(repos, 1):
        meta = []
        if r["language"]:
            meta.append(html.escape(r["language"]))
        if r["week_stars"]:
            meta.append(f"本周 +{html.escape(r['week_stars'])}★")
        if r["total_stars"]:
            meta.append(f"累计 {html.escape(r['total_stars'])}★")
        meta_str = " · ".join(meta)
        desc = html.escape(r["description"]) or "<span style='color:#999'>（无项目描述）</span>"
        items.append(f"""
        <li style="margin:0 0 18px 0;">
          <div style="font-size:16px;font-weight:600;">
            {i}. <a href="{html.escape(r['url'])}" style="color:#0969da;text-decoration:none;">{html.escape(r['full'])}</a>
          </div>
          <div style="font-size:12px;color:#57606a;margin:2px 0;">{meta_str}</div>
          <div style="font-size:14px;color:#24292f;">{desc}</div>
        </li>""")
    body = "".join(items)
    return f"""<!DOCTYPE html>
<html><body style="margin:0;background:#f6f8fa;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;">
  <div style="max-width:680px;margin:0 auto;padding:24px;">
    <h1 style="font-size:20px;color:#24292f;margin:0 0 4px;">📈 GitHub 周报 · 本周热门 Top {len(repos)}</h1>
    <div style="font-size:13px;color:#57606a;margin-bottom:20px;">数据口径：过去 7 天新增 star（GitHub Trending 周榜）</div>
    <ol style="list-style:none;padding:0;margin:0;">{body}</ol>
    <hr style="border:none;border-top:1px solid #d0d7de;margin:24px 0 12px;">
    <div style="font-size:12px;color:#8b949e;">
      生成时间：{date_str}（{html.escape(TZ_LABEL)}）· 来源 <a href="{TRENDING_URL}" style="color:#8b949e;">github.com/trending</a>
    </div>
  </div>
</body></html>"""


def send_email(subject: str, html_body: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     dir=os.getcwd(), encoding="utf-8") as f:
        body_file = os.path.basename(f.name)
        f.write(html_body)
    try:
        base = ["agently-cli", "message", "+send", "--to", RECIPIENT,
                "--subject", subject, "--body-file", body_file]
        # phase 1: get confirmation token
        p1 = subprocess.run(base, capture_output=True, text=True, timeout=60)
        out = p1.stdout + p1.stderr
        if p1.returncode != 0:
            raise RuntimeError(f"send phase-1 failed: {out}")
        tok_m = re.search(r'"confirmation_token"\s*:\s*"([^"]+)"', out)
        if not tok_m:
            raise RuntimeError(f"no confirmation_token in output: {out}")
        # phase 2: confirm
        p2 = subprocess.run(base + ["--confirmation-token", tok_m.group(1)],
                            capture_output=True, text=True, timeout=60)
        out2 = p2.stdout + p2.stderr
        if p2.returncode != 0:
            raise RuntimeError(f"send phase-2 failed: {out2}")
        print("Sent OK:", out2.strip()[:300])
    finally:
        try:
            os.remove(body_file)
        except OSError:
            pass


def main() -> int:
    date_str = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    short_date = date_str.split(" ")[0]
    try:
        page = fetch_html(TRENDING_URL)
        repos = parse_trending(page)
        if not repos:
            raise RuntimeError("parsed 0 repos from trending page")
    except Exception as e:  # noqa: BLE001
        subject = f"⚠️ GitHub 周报抓取失败 · {short_date}"
        fail_html = f"<p>本周 GitHub 周报抓取/解析失败：</p><pre>{html.escape(str(e))}</pre>"
        if DRY_RUN:
            print(subject)
            print(fail_html)
            return 1
        try:
            send_email(subject, fail_html)
        except Exception as e2:  # noqa: BLE001
            print("Failure notice also failed:", e2, file=sys.stderr)
        return 1

    translate_descriptions(repos)
    subject = f"GitHub 周报 · {short_date} 本周热门 Top {len(repos)}"
    body = render_html(repos, date_str)
    if DRY_RUN:
        print(f"[DRY_RUN] subject: {subject}")
        print(f"[DRY_RUN] parsed {len(repos)} repos -> {RECIPIENT}")
        out = os.path.join(tempfile.gettempdir(), "weekly_trending_preview.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"[DRY_RUN] preview written to {out}")
        for r in repos:
            print(f"  {r['full']:<45} +{r['week_stars']:<6} {r['language']}")
        return 0

    send_email(subject, body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
