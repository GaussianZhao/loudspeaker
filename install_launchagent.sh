#!/bin/bash
# Installs the weekly GitHub trending LaunchAgent on this Mac.
# Run this ON THE MAC MINI, from the directory that contains
# weekly_github_trending.py. It auto-detects python3 / claude paths,
# writes the LaunchAgent plist, and loads it.
#
# Prerequisites (install + log in BEFORE running this — see DEPLOY.md):
#   - agently-cli  (npm i -g @tencent-qqmail/agently-cli  &&  agently-cli auth login)
#   - claude       (curl -fsSL https://claude.ai/install.sh | bash  &&  claude  -> /login)
#
# Config (override via env when running this script):
#   RECIPIENT (default you@example.com), TOP_N (10),
#   SEND_HOUR (9), SEND_MINUTE (0), SEND_WEEKDAY (1 = Monday)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load real values from config.env (gitignored) if present; env still wins.
if [ -f "$SCRIPT_DIR/config.env" ]; then
  set -a; . "$SCRIPT_DIR/config.env"; set +a
fi

PY="$(command -v python3 || true)"
CLAUDE="$(command -v claude || true)"
LABEL="com.${USER}.weekly-github-trending"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

RECIPIENT="${RECIPIENT:-you@example.com}"
TOP_N="${TOP_N:-10}"
SEND_HOUR="${SEND_HOUR:-9}"
SEND_MINUTE="${SEND_MINUTE:-0}"
SEND_WEEKDAY="${SEND_WEEKDAY:-1}"

[ -n "$PY" ] || { echo "ERROR: python3 not found on PATH"; exit 1; }
[ -f "$SCRIPT_DIR/weekly_github_trending.py" ] || { echo "ERROR: weekly_github_trending.py not next to this script"; exit 1; }
if [ -z "$CLAUDE" ]; then
  echo "WARN: 'claude' not on PATH — email will fall back to English descriptions until Claude CLI is installed & logged in."
fi

# Include common bin dirs so launchd (minimal PATH) can find curl/agently-cli/claude.
RUN_PATH="/opt/homebrew/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PY}</string>
        <string>${SCRIPT_DIR}/weekly_github_trending.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>${RUN_PATH}</string>
        <key>RECIPIENT</key>
        <string>${RECIPIENT}</string>
        <key>TOP_N</key>
        <string>${TOP_N}</string>
        <key>TIMEZONE</key>
        <string>Asia/Shanghai</string>
        <key>TRANSLATE</key>
        <string>1</string>
        <key>CLAUDE_BIN</key>
        <string>claude</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>${SEND_WEEKDAY}</integer>
        <key>Hour</key>
        <integer>${SEND_HOUR}</integer>
        <key>Minute</key>
        <integer>${SEND_MINUTE}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/weekly_trending.log</string>
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/weekly_trending.log</string>
</dict>
</plist>
PLISTEOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "Installed and loaded: $PLIST"
echo "  python3 : $PY"
echo "  claude  : ${CLAUDE:-<not found>}"
echo "  schedule: weekday=${SEND_WEEKDAY} ${SEND_HOUR}:$(printf '%02d' "$SEND_MINUTE") (Asia/Shanghai)"
echo "  recipient: $RECIPIENT"
launchctl list | grep "weekly-github-trending" || echo "  (not in launchctl list — check errors above)"
echo
echo "Test now without waiting for the schedule:"
echo "  DRY_RUN=1 python3 \"$SCRIPT_DIR/weekly_github_trending.py\"   # preview, no send"
echo "  launchctl start ${LABEL}                                      # real run now"
