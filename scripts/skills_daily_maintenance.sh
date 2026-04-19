#!/bin/bash
# Skills 定时维护任务
# 每天 00:30 执行

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT="$HERMES_HOME/hermes-agent"
LOG_FILE="$HERMES_HOME/logs/skills_maintenance.log"

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

# 激活虚拟环境
source "$HERMES_AGENT/venv/bin/activate"

# 执行维护任务
echo "=== $(date) ===" >> "$LOG_FILE"
python3 "$HERMES_AGENT/tools/skills_maintenance.py" all >> "$LOG_FILE" 2>&1

# 清理旧日志（保留 30 天）
find "$(dirname "$LOG_FILE")" -name "*.log" -mtime +30 -delete 2>/dev/null
