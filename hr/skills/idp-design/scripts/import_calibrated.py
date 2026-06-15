#!/usr/bin/env python3
"""
import_calibrated.py
读取你校准后的盘点Excel，更新 data/talent_profiles.json 中的梯队/落位信息。

用法：
  python3 skills/idp-design/scripts/import_calibrated.py \
    --inventory 2025H1 \
    --input <校准后Excel路径>

Excel格式要求（员工明细Sheet）：
  必选列：员工姓名、部门、梯队、素质总分（调平后）、绩效分档
  可选列：素质各维度得分（专业/诚信/友好/利他/勤奋/责任/坚持）、目标层级、备注

输出：
  data/talent_profiles.json  —— 全量人才档案（追加/更新，不覆盖历史）
"""
import argparse, json, os, sys
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent.parent.parent  # workspace root
PROFILE_FILE = BASE / "data" / "talent_profiles.json"

TIER_ALIASES = {
    "第一梯队": 1, "一梯队": 1, "梯队一": 1, "1": 1, "一": 1,
    "第二梯队": 2, "二梯队": 2, "梯队二": 2, "2": 2, "二": 2,
    "第三梯队": 3, "三梯队": 3, "梯队三": 3, "3": 3, "三": 3,
    "观察": 0, "待观察": 0, "不入库": -1, "移出": -1,
}

COMPETENCY_DIMS = ["专业", "诚信", "友好", "利他", "勤奋", "责任", "坚持"]


def load_profiles():
    if PROFILE_FILE.exists():
        with open(PROFILE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"_meta": {"last_updated": ""}, "talents": {}}


def save_profiles(data):
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["_meta"]["last_updated"] = datetime.now().isoformat()
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_tier(raw):
    if raw is None:
        return None
    s = str(raw).strip()
    return TIER_ALIASES.get(s, None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True, help="盘点名称，例如 2025H1")
    parser.add_argument("--input", required=True, help="校准后Excel路径")
    args = parser.parse_args()

    try:
        import pandas as pd
    except ImportError:
        print(json.dumps({"status": "error", "message": "缺少 pandas，请先安装"}, ensure_ascii=False))
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(json.dumps({"status": "error", "message": f"文件不存在: {args.input}"}, ensure_ascii=False))
        sys.exit(1)

    # 自动找"员工明细"Sheet
    xl = pd.ExcelFile(input_path)
    sheet = None
    for s in xl.sheet_names:
        if "明细" in s or "员工" in s:
            sheet = s
            break
    if sheet is None:
        sheet = xl.sheet_names[0]

    df = pd.read_excel(input_path, sheet_name=sheet)
    df.columns = [str(c).strip() for c in df.columns]

    # 必选列检查
    required = ["员工姓名", "部门", "梯队"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(json.dumps({
            "status": "error",
            "message": f"Excel缺少必选列: {missing}，当前列: {list(df.columns)}"
        }, ensure_ascii=False))
        sys.exit(1)

    profiles = load_profiles()
    now = datetime.now().isoformat()

    updated = 0
    added = 0
    skipped = 0
    skipped_names = []

    for _, row in df.iterrows():
        name = str(row["员工姓名"]).strip()
        if not name or name == "nan":
            continue

        dept = str(row.get("部门", "")).strip()
        tier_raw = row.get("梯队", None)
        tier = parse_tier(tier_raw)

        if tier is None:
            skipped += 1
            skipped_names.append(f"{name}(梯队值={tier_raw}无法识别)")
            continue

        # 素质得分
        competency_total = None
        if "素质总分" in df.columns:
            v = row.get("素质总分")
            try:
                competency_total = float(v) if str(v) != "nan" else None
            except:
                pass

        # 各维度得分
        dim_scores = {}
        for dim in COMPETENCY_DIMS:
            if dim in df.columns:
                v = row.get(dim)
                try:
                    dim_scores[dim] = float(v) if str(v) != "nan" else None
                except:
                    dim_scores[dim] = None

        # 绩效分档
        perf_tier = str(row.get("绩效分档", "")).strip() if "绩效分档" in df.columns else ""

        # 目标层级
        target_level = str(row.get("目标层级", "")).strip() if "目标层级" in df.columns else ""

        # 备注
        remark = str(row.get("备注", "")).strip() if "备注" in df.columns else ""

        # 写入/更新 talent_profiles
        is_new = name not in profiles["talents"]
        if is_new:
            profiles["talents"][name] = {
                "name": name,
                "dept": dept,
                "inventories": {},
                "idp": {},
                "created_at": now
            }
            added += 1
        else:
            updated += 1

        # 每次盘点的快照独立存储
        profiles["talents"][name]["dept"] = dept  # 以最新盘点为准
        profiles["talents"][name]["inventories"][args.inventory] = {
            "tier": tier,
            "competency_total": competency_total,
            "dim_scores": dim_scores,
            "perf_tier": perf_tier,
            "target_level": target_level,
            "remark": remark,
            "calibrated": True,
            "imported_at": now
        }
        profiles["talents"][name]["latest_inventory"] = args.inventory
        profiles["talents"][name]["latest_tier"] = tier
        profiles["talents"][name]["updated_at"] = now

    save_profiles(profiles)

    result = {
        "status": "ok",
        "inventory": args.inventory,
        "sheet_used": sheet,
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "skipped_names": skipped_names,
        "total_talents": len(profiles["talents"]),
        "output": str(PROFILE_FILE.relative_to(BASE)),
        "next_step": "可调用 generate_idp.py 为第一/第二梯队人员生成IDP草稿"
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
