#!/usr/bin/env python3
"""
Skills 定时维护任务

通过 cron 定期执行：
- 更新 hot skills 列表
- 清理过期缓存
- 生成使用报告

用法:
    python3 skills_maintenance.py all      # 执行所有任务
    python3 skills_maintenance.py hot      # 仅更新 hot skills
    python3 skills_maintenance.py clean    # 仅清理缓存
    python3 skills_maintenance.py report   # 生成报告
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

# 设置路径
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
HOT_SKILLS_FILE = HERMES_HOME / ".hot_skills.json"
USAGE_STATS_FILE = HERMES_HOME / ".skills_usage_stats.json"
CACHE_FILE = HERMES_HOME / ".skills_prompt_snapshot.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def cleanup_cache() -> None:
    """清理过期缓存"""
    if CACHE_FILE.exists():
        try:
            mtime = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
            if datetime.now() - mtime > timedelta(hours=24):
                CACHE_FILE.unlink()
                logger.info("Cleaned up expired skills cache")
        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")


def get_usage_counts() -> Counter:
    """获取 Skills 使用统计"""
    counts = Counter()
    if USAGE_STATS_FILE.exists():
        try:
            data = json.loads(USAGE_STATS_FILE.read_text())
            for skill, info in data.items():
                if isinstance(info, dict):
                    counts[skill] = info.get("total_uses", 0)
        except Exception as e:
            logger.error(f"Failed to read usage stats: {e}")
    return counts


def update_hot_skills(top_n: int = 10) -> None:
    """更新 hot skills 列表"""
    counts = get_usage_counts()
    hot_skills = [skill for skill, _ in counts.most_common(top_n)]
    
    try:
        HOT_SKILLS_FILE.write_text(json.dumps(hot_skills, indent=2))
        logger.info(f"Updated hot skills: {hot_skills}")
    except Exception as e:
        logger.error(f"Failed to update hot skills: {e}")


def generate_report() -> str:
    """生成使用报告"""
    counts = get_usage_counts()
    
    report_lines = [
        f"# Skills Usage Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Top 20 Most Used Skills (last 30 days)",
        "",
    ]
    
    for skill, count in counts.most_common(20):
        report_lines.append(f"- **{skill}**: {count} uses")
    
    report_lines.extend([
        "",
        f"Total unique skills used: {len(counts)}",
        f"Total uses: {sum(counts.values())}",
    ])
    
    return "\n".join(report_lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 skills_maintenance.py [all|hot|clean|report]")
        sys.exit(1)
    
    task = sys.argv[1]
    
    if task == "all":
        cleanup_cache()
        update_hot_skills()
        print(generate_report())
    elif task == "hot":
        update_hot_skills()
    elif task == "clean":
        cleanup_cache()
    elif task == "report":
        print(generate_report())
    else:
        print(f"Unknown task: {task}")
        sys.exit(1)


if __name__ == "__main__":
    main()
