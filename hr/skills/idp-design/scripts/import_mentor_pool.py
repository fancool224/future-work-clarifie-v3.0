#!/usr/bin/env python3
"""
import_mentor_pool.py
导入导师库到 data/mentor_pool.json。

支持两种输入方式：
  1. Excel文件（推荐）：
     python3 skills/idp-design/scripts/import_mentor_pool.py --input mentor.xlsx
  2. JSON直接传入：
     python3 skills/idp-design/scripts/import_mentor_pool.py --json '[{"name":"张三",...}]'

Excel格式（每行一位导师）：
  必选列：姓名
  可选列：部门、职级、擅长领域（逗号分隔）、备注

操作：
  --action add      追加（默认）
  --action replace  全量替换
  --action list     查看当前导师库
"""
import argparse, json, sys
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent.parent.parent
MENTOR_FILE = Path(__file__).resolve().parent.parent / "data" / "mentor_pool.json"


def load():
    if MENTOR_FILE.exists():
        with open(MENTOR_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"mentors": []}


def save(data):
    with open(MENTOR_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Excel文件路径")
    parser.add_argument("--json", dest="json_str", help="JSON字符串")
    parser.add_argument("--action", default="add", choices=["add", "replace", "list"])
    args = parser.parse_args()

    pool = load()

    if args.action == "list":
        print(json.dumps({
            "status": "ok",
            "count": len(pool["mentors"]),
            "mentors": pool["mentors"]
        }, ensure_ascii=False, indent=2))
        return

    new_mentors = []

    if args.input:
        try:
            import pandas as pd
        except ImportError:
            print(json.dumps({"status": "error", "message": "缺少 pandas"}, ensure_ascii=False))
            sys.exit(1)
        df = pd.read_excel(args.input)
        df.columns = [str(c).strip() for c in df.columns]
        name_col = next((c for c in df.columns if "姓名" in c or "名字" in c or c == "name"), None)
        if not name_col:
            print(json.dumps({"status": "error", "message": f"找不到姓名列，当前列：{list(df.columns)}"}, ensure_ascii=False))
            sys.exit(1)
        for _, row in df.iterrows():
            name = str(row[name_col]).strip()
            if not name or name == "nan":
                continue
            mentor = {
                "name": name,
                "dept": str(row.get("部门", "")).strip(),
                "level": str(row.get("职级", "")).strip(),
                "expertise": [x.strip() for x in str(row.get("擅长领域", "")).split(",") if x.strip() and x.strip() != "nan"],
                "remark": str(row.get("备注", "")).strip(),
                "added_at": datetime.now().isoformat()
            }
            new_mentors.append(mentor)

    elif args.json_str:
        try:
            new_mentors = json.loads(args.json_str)
            if not isinstance(new_mentors, list):
                new_mentors = [new_mentors]
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "error", "message": f"JSON解析失败: {e}"}, ensure_ascii=False))
            sys.exit(1)

    else:
        print(json.dumps({"status": "error", "message": "请提供 --input 或 --json"}, ensure_ascii=False))
        sys.exit(1)

    if args.action == "replace":
        pool["mentors"] = new_mentors
    else:
        # 追加，名字相同则更新
        existing_names = {m["name"] for m in pool["mentors"]}
        for m in new_mentors:
            if m["name"] in existing_names:
                pool["mentors"] = [x if x["name"] != m["name"] else m for x in pool["mentors"]]
            else:
                pool["mentors"].append(m)

    save(pool)
    print(json.dumps({
        "status": "ok",
        "action": args.action,
        "imported": len(new_mentors),
        "total": len(pool["mentors"]),
        "mentors": [m["name"] for m in pool["mentors"]]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
