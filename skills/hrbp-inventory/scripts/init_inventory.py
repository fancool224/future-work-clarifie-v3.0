#!/usr/bin/env python3
"""
盘点初始化脚本
用法:
  python3 scripts/init_inventory.py --action init
  python3 scripts/init_inventory.py --action save --name 2025H1 --config_json '{...}'
"""
import argparse, json, os, sys
from datetime import datetime
from pathlib import Path

DEFAULT_CONFIG = {
    "time_range": {"start": None, "end": None},
    "kpi_rules": [
        {"dept": "加盟中心", "metric": "开店数", "field": "开店数"},
        {"dept": "默认", "metric": "综合绩效", "field": "综合绩效达成率"}
    ],
    "performance_thresholds": {"优秀": 1.1, "合格": 0.8},
    "competency_thresholds": {"优秀": 110, "良好": 90, "合格": 75},
    "grid_size": 25,
    "tier_rules": [
        {"grid_ids": [25, 24, 23], "tier": "第一梯队"},
        {"grid_ids": [22, 21, 20], "tier": "第二梯队"},
        {"grid_ids": [19, 18, 17], "tier": "骨干员工"},
        {"grid_ids": list(range(8, 17)), "tier": "待发展员工"},
        {"grid_ids": [7, 6, 5], "tier": "待改进员工"},
        {"grid_ids": [4, 3, 2, 1], "tier": "问题员工"}
    ],
    "anomaly_detection": {"std_threshold": 0.3, "iqr_multiplier": 1.5}
}

INIT_QUESTIONS = [
    {"id": "name",
     "question": "本次盘点的名称是什么？（例：2025H1、2025年度、2025Q3）",
     "default": None},
    {"id": "time_range",
     "question": "本次盘点覆盖的时间范围？（例：2025-01-01 至 2025-06-30）",
     "default": None},
    {"id": "performance_thresholds",
     "question": "绩效轴分档阈值：优秀≥?%，合格≥?%（低于合格=待改进）",
     "default": "优秀≥110%，合格≥80%"},
    {"id": "competency_thresholds",
     "question": "素质轴分档阈值：优秀≥?分，良好≥?分，合格≥?分（管理层满分145分，员工层满分120分）",
     "default": "优秀≥110分，良好≥90分，合格≥75分"},
    {"id": "grid_size",
     "question": "落位格数：9格还是25格？",
     "default": "25格"},
    {"id": "kpi_rules",
     "question": "哪些部门使用非综合绩效指标？（例：加盟中心=开店数，其余默认综合绩效达成率）",
     "default": "加盟中心=开店数，其余=综合绩效达成率"}
]


def cmd_init():
    print(json.dumps({
        "action": "confirm",
        "tip": "请逐一回答以下问题，完成后调用 --action save 保存配置",
        "questions": INIT_QUESTIONS
    }, ensure_ascii=False, indent=2))


def cmd_save(name, config_json, data_dir):
    if not name:
        print(json.dumps({"error": "缺少 --name 参数"}, ensure_ascii=False))
        sys.exit(1)

    try:
        user_cfg = json.loads(config_json) if config_json else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"config_json 解析失败: {e}"}, ensure_ascii=False))
        sys.exit(1)

    config = DEFAULT_CONFIG.copy()
    config.update(user_cfg)
    config["name"] = name
    config["created_at"] = datetime.now().isoformat()

    inv_dir = Path(data_dir) / name
    inv_dir.mkdir(parents=True, exist_ok=True)
    config_path = inv_dir / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "status": "ok",
        "inventory": name,
        "config_path": str(config_path),
        "summary": {
            "time_range": config.get("time_range"),
            "performance_thresholds": config["performance_thresholds"],
            "competency_thresholds": config["competency_thresholds"],
            "grid_size": config["grid_size"],
            "kpi_rules": config["kpi_rules"]
        },
        "next_step": "上传素质评分数据，调用 score_processor.py --action full"
    }, ensure_ascii=False, indent=2))


def cmd_list(data_dir):
    d = Path(data_dir)
    if not d.exists():
        print(json.dumps({"inventories": []}, ensure_ascii=False))
        return
    items = []
    for p in sorted(d.iterdir()):
        cfg_file = p / "config.json"
        if cfg_file.exists():
            with open(cfg_file, encoding="utf-8") as f:
                cfg = json.load(f)
            items.append({"name": p.name, "created_at": cfg.get("created_at"), "grid_size": cfg.get("grid_size")})
    print(json.dumps({"inventories": items}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="盘点初始化")
    parser.add_argument("--action", choices=["init", "save", "list"], required=True)
    parser.add_argument("--name", default=None)
    parser.add_argument("--config_json", default=None)
    parser.add_argument("--data_dir", default="data/inventories")
    args = parser.parse_args()

    if args.action == "init":
        cmd_init()
    elif args.action == "save":
        cmd_save(args.name, args.config_json, args.data_dir)
    elif args.action == "list":
        cmd_list(args.data_dir)


if __name__ == "__main__":
    main()
