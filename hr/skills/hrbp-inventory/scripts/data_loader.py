#!/usr/bin/env python3
"""
数据加载模块 v2.0
负责从真实文件格式读取：员工名册、评分数据、KPI数据
唯一键：员工代码（档案号）+ 姓名 + 职位（联合展示主键）
层级：直接从 ☆评管理 / ☆评员工 两张评分表读取，无需关键词匹配
"""
import json
import re
from pathlib import Path
import pandas as pd


# === 评分文件字段映射 ===
SCORE_COLS_EMPLOYEE = {
    "rater_pos":    "评价官\n岗位",
    "rater_name":   "评价官\n姓名",
    "dept_l1":      "一级部门",
    "dept_l2":      "二级部门",
    "ratee_pos":    "被评价\n员工岗位",
    "ratee_name":   "被评价\n员工姓名",
    "score":        "小计",
}
SCORE_COLS_MGR = {
    "rater_pos":    "评价官\n岗位",
    "rater_name":   "评价官\n姓名",
    "dept_l1":      "一级部门",
    "dept_l2":      "二级部门",
    "ratee_pos":    "被评价\n管理层岗位",
    "ratee_name":   "被评价\n管理层姓名",
    "score":        "小计",
}

# KPI文件通用字段（各中心格式相似）
KPI_STANDARD_COLS = {
    "dept_l1":  "一级部门",
    "dept_l2":  "二级部门",
    "pos":      "岗位",
    "name":     "姓名",
    "kpi":      "KPI",
    "weight":   "权重",
    "actual":   "实际",
    "target":   "目标",
    "rate":     "达成率",
}


def load_score_file(filepath: str) -> pd.DataFrame:
    """
    读取评分文件（支持 bae333bc 格式）
    返回标准化 DataFrame，含字段：
      ratee_name, ratee_pos, dept_l1, dept_l2, rater_name, rater_pos, score, level(管理层/员工层)
    """
    path = Path(filepath)
    xl = pd.ExcelFile(path)

    frames = []

    # 员工层评分
    if "☆评员工" in xl.sheet_names:
        df_e = xl.parse("☆评员工", header=0)
        df_e.columns = [str(c).strip() for c in df_e.columns]
        df_e = df_e[df_e["序号"].notna()].copy()
        col_map = {v: k for k, v in SCORE_COLS_EMPLOYEE.items()}
        df_e = df_e.rename(columns=col_map)
        df_e["level"] = "员工层"
        frames.append(df_e[["ratee_name", "ratee_pos", "dept_l1", "dept_l2",
                              "rater_name", "rater_pos", "score", "level"]])

    # 管理层评分
    if "☆评管理" in xl.sheet_names:
        df_m = xl.parse("☆评管理", header=0)
        df_m.columns = [str(c).strip() for c in df_m.columns]
        df_m = df_m[df_m["序号"].notna()].copy()
        col_map = {v: k for k, v in SCORE_COLS_MGR.items()}
        df_m = df_m.rename(columns=col_map)
        df_m["level"] = "管理层"
        frames.append(df_m[["ratee_name", "ratee_pos", "dept_l1", "dept_l2",
                              "rater_name", "rater_pos", "score", "level"]])

    if not frames:
        raise ValueError(f"评分文件中未找到 ☆评员工 或 ☆评管理 sheet：{filepath}")

    df = pd.concat(frames, ignore_index=True)
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df = df.dropna(subset=["score", "ratee_name"])
    df["unique_key"] = df["ratee_name"].str.strip() + "|" + df["ratee_pos"].fillna("").str.strip()
    return df


def load_kpi_file(filepath: str, config: dict) -> pd.DataFrame:
    """
    读取 KPI 文件（支持各中心格式）
    返回标准化 DataFrame，含：
      name, pos, dept_l1, dept_l2, kpi_rate(加权达成率), kpi_metric(绩效指标名), kpi_type(封顶/可突破)
    """
    path = Path(filepath)
    xl = pd.ExcelFile(path)

    # 自动找 KPI sheet
    kpi_sheet = next((s for s in xl.sheet_names if "KPI" in s.upper() or "kpi" in s), None)
    if not kpi_sheet:
        # fallback: 取第一个 sheet
        kpi_sheet = xl.sheet_names[0]

    # 找 header 行（跳过标题行）
    raw = xl.parse(kpi_sheet, header=None)
    header_row = None
    for i, row in raw.iterrows():
        vals = [str(v) for v in row if pd.notna(v)]
        if any("姓名" in v or "岗位" in v for v in vals):
            header_row = i
            break

    if header_row is None:
        raise ValueError(f"在 {kpi_sheet} 中未找到表头行（需含'姓名'或'岗位'列）")

    df = xl.parse(kpi_sheet, header=header_row)
    df.columns = [str(c).strip() for c in df.columns]

    # 列名自适应匹配
    def find_col(keywords, columns):
        for kw in keywords:
            for c in columns:
                if kw in c:
                    return c
        return None

    name_col = find_col(["姓名"], df.columns)
    pos_col = find_col(["岗位", "职位"], df.columns)
    dept1_col = find_col(["一级部门"], df.columns)
    dept2_col = find_col(["二级部门", "部门"], df.columns)
    rate_col = find_col(["达成率", "完成率"], df.columns)
    kpi_name_col = find_col(["KPI", "指标"], df.columns)
    weight_col = find_col(["权重"], df.columns)
    target_col = find_col(["目标"], df.columns)
    actual_col = find_col(["实际", "累计达成"], df.columns)

    if not name_col:
        raise ValueError(f"KPI文件 {filepath} 缺少姓名列")

    df = df[df[name_col].notna()].copy()
    df["_name"] = df[name_col].astype(str).str.strip()
    df["_pos"] = df[pos_col].astype(str).str.strip() if pos_col else ""
    df["_dept_l1"] = df[dept1_col].astype(str).str.strip() if dept1_col else ""
    df["_dept_l2"] = df[dept2_col].astype(str).str.strip() if dept2_col else ""

    # 计算加权达成率
    if rate_col and weight_col:
        df["_rate"] = pd.to_numeric(df[rate_col], errors="coerce")
        df["_weight"] = pd.to_numeric(df[weight_col], errors="coerce")
        # 按人汇总加权达成率
        grp = df.groupby("_name").apply(
            lambda x: (x["_rate"] * x["_weight"]).sum() / x["_weight"].sum()
            if x["_weight"].sum() > 0 else x["_rate"].mean()
        ).reset_index()
        grp.columns = ["name", "kpi_rate"]
        # 补充其他字段（取第一条）
        meta = df.groupby("_name").first().reset_index()[["_name", "_pos", "_dept_l1", "_dept_l2"]]
        meta.columns = ["name", "pos", "dept_l1", "dept_l2"]
        result = meta.merge(grp, on="name")
    elif rate_col:
        df["_rate"] = pd.to_numeric(df[rate_col], errors="coerce")
        result = df[["_name", "_pos", "_dept_l1", "_dept_l2", "_rate"]].drop_duplicates("_name")
        result.columns = ["name", "pos", "dept_l1", "dept_l2", "kpi_rate"]
    else:
        raise ValueError(f"KPI文件 {filepath} 缺少达成率列")

    # 判断绩效类型（从 config 的 kpi_rules 中读取）
    kpi_rules = config.get("kpi_rules", [])
    def get_kpi_type(dept):
        for rule in kpi_rules:
            if rule.get("dept") == dept:
                return rule.get("kpi_type", "可突破")  # 默认可突破
        return "可突破"

    result["kpi_type"] = result["dept_l1"].apply(get_kpi_type)
    result["unique_key"] = result["name"] + "|" + result["pos"]
    return result


def load_roster(filepath: str) -> pd.DataFrame:
    """
    读取员工花名册（86e435f6 格式，员工资料 sheet）
    返回标准化 DataFrame，含：
      emp_code, name, pos, dept_l1, dept_l2, level(从评分表推断，此处默认空)
    """
    path = Path(filepath)
    xl = pd.ExcelFile(path)

    if "员工资料" not in xl.sheet_names:
        return pd.DataFrame()

    df = xl.parse("员工资料", header=0)
    df.columns = [str(c).strip() for c in df.columns]

    # 字段映射
    code_col = next((c for c in df.columns if "员工" in c and "代码" in c), None)
    name_col = next((c for c in df.columns if c == "姓名"), None)
    pos_col = next((c for c in df.columns if "职位" in c or "职务" in c), None)
    dept1_col = next((c for c in df.columns if "一级部门" in c), None)
    dept2_col = next((c for c in df.columns if "二级部门" in c), None)
    archive_col = next((c for c in df.columns if "档案号" in c), None)

    result = pd.DataFrame()
    result["emp_code"] = df[code_col].astype(str) if code_col else df[archive_col].astype(str)
    result["name"] = df[name_col].astype(str).str.strip() if name_col else ""
    result["pos"] = df[pos_col].astype(str).str.strip() if pos_col else ""
    result["dept_l1"] = df[dept1_col].astype(str).str.strip() if dept1_col else ""
    result["dept_l2"] = df[dept2_col].astype(str).str.strip() if dept2_col else ""
    result["unique_key"] = result["name"] + "|" + result["pos"]
    result = result[result["name"].notna() & (result["name"] != "") & (result["name"] != "nan")]
    return result


if __name__ == "__main__":
    # 自检
    INBOUND = "/usr/local/lib/node_modules/openclaw/.openclaw/media/inbound/"
    scores = load_score_file(INBOUND + "bae333bc-e2e3-498a-a72f-ac8e933fdb85.xlsx")
    print(f"评分数据: {len(scores)} 行，员工层 {len(scores[scores.level=='员工层'])} 管理层 {len(scores[scores.level=='管理层'])}")
    print(f"涉及部门: {sorted(scores.dept_l1.dropna().unique())}")
    print(f"样例:\n{scores.head(3).to_string()}")
