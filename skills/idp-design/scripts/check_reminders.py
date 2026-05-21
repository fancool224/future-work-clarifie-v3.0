#!/usr/bin/env python3
"""
check_reminders.py
IDP 跟进提醒引擎——月底扫描 + 里程碑临期预警（A+C组合）。

两种触发方式：
  1. 月底固定扫描（手动或定时）：
     python3 skills/idp-design/scripts/check_reminders.py --mode monthly --inventory 2025H1

  2. 里程碑临期检查（任务截止日前N天）：
     python3 skills/idp-design/scripts/check_reminders.py --mode milestone --inventory 2025H1 --warn_days 14

  3. 两种合并输出：
     python3 skills/idp-design/scripts/check_reminders.py --mode both --inventory 2025H1 --warn_days 14

输出：
  JSON格式提醒列表，由 Agent 读取后组织成自然语言告知 HRBP
"""
import argparse, json, sys
from pathlib import Path
from datetime import datetime, timedelta

BASE = Path(__file__).resolve().parent.parent.parent.parent
PROFILE_FILE = BASE / "data" / "talent_profiles.json"


def load_profiles():
    if not PROFILE_FILE.exists():
        return {}
    with open(PROFILE_FILE, encoding="utf-8") as f:
        return json.load(f)


def check_monthly(profiles, inventory):
    """月底扫描：找出整个月内没有任何任务更新的人"""
    today = datetime.today()
    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    alerts = []

    for name, p in profiles.get("talents", {}).items():
        idp = p.get("idp", {}).get(inventory)
        if not idp:
            continue
        tasks = idp.get("tasks", [])
        if not tasks:
            continue

        # 检查是否有任务在本月内被更新过
        has_update = any(
            t.get("last_updated", "")[:10] >= month_start
            for t in tasks
        )
        in_progress = any(t.get("status") == "进行中" for t in tasks)
        todo = any(t.get("status") == "未开始" for t in tasks)

        completion = sum(1 for t in tasks if t.get("status") == "已完成") / len(tasks) * 100

        if not has_update and (in_progress or todo):
            alerts.append({
                "type": "monthly_no_update",
                "name": name,
                "dept": p.get("dept", ""),
                "tier": p.get("latest_tier"),
                "mentor": idp.get("mentor", ""),
                "completion": f"{completion:.0f}%",
                "in_progress": sum(1 for t in tasks if t.get("status") == "进行中"),
                "todo": sum(1 for t in tasks if t.get("status") == "未开始"),
                "message": f"{name}（{p.get('dept','')}）本月暂无IDP进展更新，当前完成率{completion:.0f}%，请跟进"
            })

    return alerts


def check_milestones(profiles, inventory, warn_days=14):
    """里程碑临期预警：任务截止日前N天 + 已逾期未完成"""
    today = datetime.today()
    warn_date = (today + timedelta(days=warn_days)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    alerts = []

    for name, p in profiles.get("talents", {}).items():
        idp = p.get("idp", {}).get(inventory)
        if not idp:
            continue
        tasks = idp.get("tasks", [])

        for i, t in enumerate(tasks):
            if t.get("status") in ("已完成", "已取消"):
                continue
            due = t.get("due_date", "")
            if not due:
                continue

            if due < today_str:
                # 已逾期
                alerts.append({
                    "type": "overdue",
                    "name": name,
                    "dept": p.get("dept", ""),
                    "tier": p.get("latest_tier"),
                    "mentor": idp.get("mentor", ""),
                    "task_index": i,
                    "task": t["task"],
                    "dim": t["dim"],
                    "due_date": due,
                    "status": t["status"],
                    "days_overdue": (today - datetime.strptime(due, "%Y-%m-%d")).days,
                    "message": f"{name} 的任务【{t['task'][:20]}...】已逾期{(today - datetime.strptime(due, '%Y-%m-%d')).days}天（截止{due}），当前状态：{t['status']}"
                })
            elif due <= warn_date:
                # 临期预警
                days_left = (datetime.strptime(due, "%Y-%m-%d") - today).days
                alerts.append({
                    "type": "upcoming",
                    "name": name,
                    "dept": p.get("dept", ""),
                    "tier": p.get("latest_tier"),
                    "mentor": idp.get("mentor", ""),
                    "task_index": i,
                    "task": t["task"],
                    "dim": t["dim"],
                    "due_date": due,
                    "status": t["status"],
                    "days_left": days_left,
                    "message": f"{name} 的任务【{t['task'][:20]}...】将在{days_left}天后截止（{due}），当前状态：{t['status']}"
                })

    return alerts


def format_summary(monthly_alerts, milestone_alerts, inventory):
    overdue = [a for a in milestone_alerts if a["type"] == "overdue"]
    upcoming = [a for a in milestone_alerts if a["type"] == "upcoming"]
    no_update = monthly_alerts

    summary_lines = [f"📋 IDP跟进提醒汇总（盘点：{inventory}，{datetime.today().strftime('%Y-%m-%d')}）\n"]

    if overdue:
        summary_lines.append(f"🔴 逾期未完成任务（{len(overdue)}条）：")
        for a in overdue:
            summary_lines.append(f"  • {a['message']}")
        summary_lines.append("")

    if upcoming:
        summary_lines.append(f"🟡 即将截止任务（{len(upcoming)}条）：")
        for a in upcoming:
            summary_lines.append(f"  • {a['message']}")
        summary_lines.append("")

    if no_update:
        summary_lines.append(f"⚪ 本月无进展更新（{len(no_update)}人）：")
        for a in no_update:
            summary_lines.append(f"  • {a['message']}")
        summary_lines.append("")

    if not (overdue or upcoming or no_update):
        summary_lines.append("✅ 暂无需要跟进的IDP提醒，所有进展正常。")

    return "\n".join(summary_lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--mode", default="both", choices=["monthly", "milestone", "both"])
    parser.add_argument("--warn_days", type=int, default=14, help="提前几天预警（默认14天）")
    parser.add_argument("--format", default="json", choices=["json", "text"])
    args = parser.parse_args()

    profiles = load_profiles()
    if not profiles:
        print(json.dumps({"status": "error", "message": "人才档案为空"}, ensure_ascii=False))
        sys.exit(1)

    monthly_alerts = []
    milestone_alerts = []

    if args.mode in ("monthly", "both"):
        monthly_alerts = check_monthly(profiles, args.inventory)
    if args.mode in ("milestone", "both"):
        milestone_alerts = check_milestones(profiles, args.inventory, args.warn_days)

    if args.format == "text":
        print(format_summary(monthly_alerts, milestone_alerts, args.inventory))
        return

    print(json.dumps({
        "status": "ok",
        "inventory": args.inventory,
        "checked_at": datetime.now().isoformat(),
        "monthly_no_update": len(monthly_alerts),
        "overdue": len([a for a in milestone_alerts if a["type"] == "overdue"]),
        "upcoming": len([a for a in milestone_alerts if a["type"] == "upcoming"]),
        "alerts": monthly_alerts + milestone_alerts,
        "summary_text": format_summary(monthly_alerts, milestone_alerts, args.inventory)
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
