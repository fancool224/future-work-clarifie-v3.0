#!/usr/bin/env python3
"""
update_progress.py
更新 IDP 任务进展，支持单条更新或批量导入。

用法：
  # 更新单条任务
  python3 skills/idp-design/scripts/update_progress.py \
    --name 张三 \
    --inventory 2025H1 \
    --task_index 0 \
    --status 进行中 \
    --note "已完成第一阶段"

  # 批量导入进展Excel（HRBP填写后上传）
  python3 skills/idp-design/scripts/update_progress.py \
    --input 进展更新.xlsx \
    --inventory 2025H1

  # 查看某人IDP进展
  python3 skills/idp-design/scripts/update_progress.py \
    --name 张三 \
    --inventory 2025H1 \
    --action view

状态枚举：未开始 / 进行中 / 已完成 / 已延期 / 已取消
"""
import argparse, json, sys
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent.parent.parent
PROFILE_FILE = BASE / "data" / "talent_profiles.json"

VALID_STATUS = {"未开始", "进行中", "已完成", "已延期", "已取消"}


def load_profiles():
    if not PROFILE_FILE.exists():
        return {}
    with open(PROFILE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_profiles(data):
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def calc_completion(tasks):
    if not tasks:
        return 0.0
    done = sum(1 for t in tasks if t.get("status") == "已完成")
    return round(done / len(tasks) * 100, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="员工姓名")
    parser.add_argument("--inventory", required=True, help="盘点名称")
    parser.add_argument("--task_index", type=int, help="任务序号（从0开始）")
    parser.add_argument("--status", choices=list(VALID_STATUS), help="新状态")
    parser.add_argument("--note", default="", help="进展备注")
    parser.add_argument("--input", help="批量更新Excel路径")
    parser.add_argument("--action", default="update", choices=["update", "view", "summary"])
    args = parser.parse_args()

    profiles = load_profiles()
    if not profiles:
        print(json.dumps({"status": "error", "message": "人才档案为空"}, ensure_ascii=False))
        sys.exit(1)

    # ── 查看单人进展 ──
    if args.action == "view" and args.name:
        person = profiles.get("talents", {}).get(args.name)
        if not person:
            print(json.dumps({"status": "error", "message": f"未找到：{args.name}"}, ensure_ascii=False))
            sys.exit(1)
        idp = person.get("idp", {}).get(args.inventory)
        if not idp:
            print(json.dumps({"status": "error", "message": f"{args.name} 在盘点 {args.inventory} 没有IDP记录"}, ensure_ascii=False))
            sys.exit(1)
        tasks = idp.get("tasks", [])
        completion = calc_completion(tasks)
        print(json.dumps({
            "name": args.name,
            "inventory": args.inventory,
            "goal": idp.get("goal"),
            "mentor": idp.get("mentor"),
            "completion": f"{completion}%",
            "tasks": [{
                "index": i,
                "dim": t["dim"],
                "category": t["category_label"],
                "task": t["task"],
                "status": t["status"],
                "due_date": t["due_date"],
                "note": t.get("progress_note", "")
            } for i, t in enumerate(tasks)]
        }, ensure_ascii=False, indent=2))
        return

    # ── 汇总所有人进展 ──
    if args.action == "summary":
        summary = []
        for name, p in profiles.get("talents", {}).items():
            idp = p.get("idp", {}).get(args.inventory)
            if not idp:
                continue
            tasks = idp.get("tasks", [])
            completion = calc_completion(tasks)
            overdue = [t for t in tasks if t.get("status") not in ("已完成", "已取消")
                       and t.get("due_date", "9999") < datetime.today().strftime("%Y-%m-%d")]
            summary.append({
                "name": name,
                "dept": p.get("dept"),
                "tier": p.get("latest_tier"),
                "completion": f"{completion}%",
                "task_count": len(tasks),
                "done": sum(1 for t in tasks if t.get("status") == "已完成"),
                "overdue": len(overdue),
                "mentor": idp.get("mentor")
            })
        print(json.dumps({
            "status": "ok",
            "inventory": args.inventory,
            "total_people": len(summary),
            "summary": summary
        }, ensure_ascii=False, indent=2))
        return

    # ── 批量更新 ──
    if args.input:
        try:
            import pandas as pd
        except ImportError:
            print(json.dumps({"status": "error", "message": "缺少 pandas"}, ensure_ascii=False))
            sys.exit(1)
        df = pd.read_excel(args.input)
        df.columns = [str(c).strip() for c in df.columns]
        required = ["员工姓名", "任务序号", "状态"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            print(json.dumps({"status": "error", "message": f"Excel缺少列：{missing}"}, ensure_ascii=False))
            sys.exit(1)

        updated = 0
        errors = []
        for _, row in df.iterrows():
            name = str(row["员工姓名"]).strip()
            try:
                idx = int(row["任务序号"])
            except:
                errors.append(f"{name}: 任务序号无效")
                continue
            status = str(row["状态"]).strip()
            if status not in VALID_STATUS:
                errors.append(f"{name}-任务{idx}: 状态'{status}'无效")
                continue
            note = str(row.get("进展备注", "")).strip()

            person = profiles.get("talents", {}).get(name)
            if not person:
                errors.append(f"{name}: 未找到")
                continue
            tasks = person.get("idp", {}).get(args.inventory, {}).get("tasks", [])
            if idx >= len(tasks):
                errors.append(f"{name}-任务{idx}: 序号超出范围（共{len(tasks)}条）")
                continue
            tasks[idx]["status"] = status
            if note and note != "nan":
                tasks[idx]["progress_note"] = note
            tasks[idx]["last_updated"] = datetime.now().isoformat()
            updated += 1

        save_profiles(profiles)
        print(json.dumps({
            "status": "ok",
            "updated": updated,
            "errors": errors
        }, ensure_ascii=False, indent=2))
        return

    # ── 单条更新 ──
    if not all([args.name, args.task_index is not None, args.status]):
        print(json.dumps({"status": "error", "message": "单条更新需要 --name、--task_index、--status"}, ensure_ascii=False))
        sys.exit(1)

    person = profiles.get("talents", {}).get(args.name)
    if not person:
        print(json.dumps({"status": "error", "message": f"未找到：{args.name}"}, ensure_ascii=False))
        sys.exit(1)

    tasks = person.get("idp", {}).get(args.inventory, {}).get("tasks", [])
    if args.task_index >= len(tasks):
        print(json.dumps({"status": "error", "message": f"任务序号超出范围（共{len(tasks)}条）"}, ensure_ascii=False))
        sys.exit(1)

    tasks[args.task_index]["status"] = args.status
    if args.note:
        tasks[args.task_index]["progress_note"] = args.note
    tasks[args.task_index]["last_updated"] = datetime.now().isoformat()

    completion = calc_completion(tasks)
    save_profiles(profiles)

    print(json.dumps({
        "status": "ok",
        "name": args.name,
        "task_index": args.task_index,
        "new_status": args.status,
        "overall_completion": f"{completion}%"
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
