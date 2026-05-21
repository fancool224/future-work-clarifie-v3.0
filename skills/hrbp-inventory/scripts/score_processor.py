#!/usr/bin/env python3
"""
素质评分处理 v2.0
- 唯一键：姓名 + 职位
- 调平单元：按"一级部门"（评分者所在部门） ← 与盘点单元不同
- 层级：从评分文件直接读取（管理层/员工层），不做关键词匹配
- 素质最高分上限：管理层145，员工层120

用法:
  python3 scripts/score_processor.py --action full \
    --inventory 2026H1 \
    --input <评分文件.xlsx> \
    --data_dir data/inventories
"""
import argparse, json, sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from data_loader import load_score_file


MAX_SCORE = {"管理层": 145, "员工层": 120}


def load_config(inventory: str, data_dir: str) -> dict:
    p = Path(data_dir) / inventory / "config.json"
    if not p.exists():
        print(json.dumps({"error": f"配置文件不存在：{p}"}, ensure_ascii=False))
        sys.exit(1)
    return json.loads(p.read_text(encoding="utf-8"))


def detect_anomaly_raters(df: pd.DataFrame, std_threshold: float = 0.3) -> dict:
    """
    检测异常评分者（平均主义/偏高/偏低）
    调平单元内执行：按 rater_name × level 分组
    使用 median + 3×MAD，不用 mean + 2σ
    """
    anomaly = {}
    global_median = df["score"].median()
    mad = (df["score"] - global_median).abs().median()
    effective_threshold = max(std_threshold, 1.0)

    for (rater, level), grp in df.groupby(["rater_name", "level"]):
        if len(grp) < 3:
            continue
        std_val = grp["score"].std()
        mean_val = grp["score"].mean()

        flags = []
        if std_val < effective_threshold:
            flags.append("平均主义")
        if mean_val > global_median + 3 * mad:
            flags.append("偏高")
        elif mean_val < global_median - 3 * mad:
            flags.append("偏低")

        if flags:
            anomaly[f"{rater}|{level}"] = {
                "rater": rater,
                "level": level,
                "std": round(std_val, 4),
                "mean": round(mean_val, 4),
                "count": len(grp),
                "flag": "、".join(flags),
                "reason": (
                    f"评分标准差{std_val:.3f}低于阈值{effective_threshold}，打分高度集中（可能大锅饭）"
                    if "平均主义" in flags else
                    f"均分{mean_val:.1f}与全局中位数{global_median:.1f}偏差超过3×MAD"
                )
            }
    return anomaly


def normalize_scores(
    df: pd.DataFrame,
    anomaly_raters: dict,
    iqr_multiplier: float = 1.5
) -> pd.DataFrame:
    """
    按"调平单元 = 一级部门 × 层级"执行中位数调平
    严格执行顺序：① 标记异常评分者 → ② 用非异常数据算IQR → ③ 标记极值 → ④ 调平
    """
    df = df.copy()
    # 标记异常评分者
    df["anomaly_rater_excluded"] = df.apply(
        lambda r: f"{r['rater_name']}|{r['level']}" in anomaly_raters, axis=1
    )

    results = []
    # 调平单元 = dept_l1（部门） × level（层级）
    for (dept, level), grp in df.groupby(["dept_l1", "level"]):
        grp = grp.copy()
        max_score = MAX_SCORE.get(level, 120)
        # 非异常评分者数据
        valid = grp[~grp["anomaly_rater_excluded"]]

        # IQR 去极值（仅用非异常数据算边界）
        grp["outlier"] = False
        if len(valid) >= 4:
            q1 = valid["score"].quantile(0.25)
            q3 = valid["score"].quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lo = q1 - iqr_multiplier * iqr
                hi = q3 + iqr_multiplier * iqr
                grp.loc[~grp["anomaly_rater_excluded"] & ((grp["score"] < lo) | (grp["score"] > hi)), "outlier"] = True

        # 有效数据 = 非异常评分者 且 非极值
        valid_final = grp[~grp["anomaly_rater_excluded"] & ~grp["outlier"]]
        fallback = False
        if len(valid_final) > 0:
            m_g = valid_final["score"].median()
        else:
            m_g = grp["score"].median()
            fallback = True

        grp["M_g"] = m_g
        grp["fallback"] = fallback
        results.append(grp)

    df_out = pd.concat(results, ignore_index=True)

    # 全局基准：各 (dept, level) 中位数的中位数
    group_medians = df_out.groupby(["dept_l1", "level"])["M_g"].first()
    m_global = group_medians.median()
    df_out["M_global"] = m_global
    df_out["delta"] = m_global - df_out["M_g"]

    # 调平分
    df_out["score_adjusted"] = df_out.apply(
        lambda r: float(np.clip(r["score"] + r["delta"], 0, MAX_SCORE.get(r["level"], 120))),
        axis=1
    )
    return df_out, m_global


def aggregate_person_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    每人多条评分 → 取调平后的中位数作为最终分
    主键：unique_key (姓名|职位)
    """
    # 每人的有效评分（排除异常评分者和极值）
    valid = df[~df["anomaly_rater_excluded"] & ~df["outlier"]].copy()
    if len(valid) == 0:
        valid = df.copy()  # fallback

    agg = valid.groupby("unique_key").agg(
        ratee_name=("ratee_name", "first"),
        ratee_pos=("ratee_pos", "first"),
        dept_l1=("dept_l1", "first"),
        level=("level", "first"),
        score_raw=("score", "median"),
        score_adjusted=("score_adjusted", "median"),
        delta=("delta", "first"),
        M_g=("M_g", "first"),
        M_global=("M_global", "first"),
        fallback=("fallback", "first"),
        rater_count=("rater_name", "nunique"),
    ).reset_index()
    return agg


def cmd_full(args):
    config = load_config(args.inventory, args.data_dir)
    anomaly_cfg = config.get("anomaly_detection", {})
    std_threshold = anomaly_cfg.get("std_threshold", 0.3)
    iqr_multiplier = anomaly_cfg.get("iqr_multiplier", 1.5)

    df = load_score_file(args.input)

    anomaly_raters = detect_anomaly_raters(df, std_threshold)
    df_norm, m_global = normalize_scores(df, anomaly_raters, iqr_multiplier)
    person_df = aggregate_person_scores(df_norm)

    # 组统计
    group_stats = []
    for (dept, level), grp in df_norm.groupby(["dept_l1", "level"]):
        valid_final = grp[~grp["anomaly_rater_excluded"] & ~grp["outlier"]]
        group_stats.append({
            "dept": dept,
            "level": level,
            "M_g": round(grp["M_g"].iloc[0], 4),
            "delta": round(grp["delta"].iloc[0], 4),
            "n_total": len(grp),
            "n_valid": len(valid_final),
            "n_outlier": int(grp["outlier"].sum()),
            "n_anomaly_excluded": int(grp["anomaly_rater_excluded"].sum()),
            "fallback": bool(grp["fallback"].iloc[0]),
            "fallback_note": "⚠️ 全部评分被排除，使用全量数据调平，建议人工复核" if grp["fallback"].iloc[0] else ""
        })

    # 保存处理结果
    out_dir = Path(args.data_dir) / args.inventory
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "scores_processed.json"

    employees_out = []
    for _, row in person_df.iterrows():
        employees_out.append({
            "unique_key": row["unique_key"],
            "name": row["ratee_name"],
            "pos": row["ratee_pos"],
            "dept_l1": row["dept_l1"],
            "level": row["level"],
            "score_raw": round(row["score_raw"], 2),
            "score_adjusted": round(row["score_adjusted"], 2),
            "delta": round(row["delta"], 4),
            "rater_count": int(row["rater_count"]),
            "fallback": bool(row["fallback"]),
        })

    result = {
        "inventory": args.inventory,
        "processed_at": datetime.now().isoformat(),
        "M_global": round(m_global, 4),
        "anomaly_raters": list(anomaly_raters.values()),
        "group_stats": group_stats,
        "employees": employees_out,
        "summary": {
            "total_records": len(df_norm),
            "total_persons": len(person_df),
            "anomaly_rater_count": len(anomaly_raters),
            "anomaly_excluded_records": int(df_norm["anomaly_rater_excluded"].sum()),
            "outlier_records": int(df_norm["outlier"].sum()),
        }
    }

    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="素质评分处理 v2.0：异常检测+调平（按部门×层级）")
    parser.add_argument("--action", choices=["full"], required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--data_dir", default="data/inventories")
    args = parser.parse_args()
    cmd_full(args)


if __name__ == "__main__":
    main()
