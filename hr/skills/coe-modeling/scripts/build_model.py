#!/usr/bin/env python3
"""
引导用户为任意企业构建胜任力模型，输出标准格式 JSON + Excel
用法: uv run --python 3.12 scripts/build_model.py --action <init|add_dimension|add_element|add_indicator|finalize|export>
      --state <state_json_path> [其他参数]
"""
import argparse, json, sys, uuid
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
TEMPLATE_PATH = SKILL_DIR / "references" / "universal_template.json"

# 通用维度模板（可选）
UNIVERSAL_DIMENSIONS = [
    {"name": "认知与思维", "suggestion": "学习能力、结构化思维、数据分析、战略判断"},
    {"name": "执行与结果", "suggestion": "目标设定、计划推进、问题解决、结果交付"},
    {"name": "协作与沟通", "suggestion": "团队协作、跨部门沟通、影响力、冲突处理"},
    {"name": "领导与发展", "suggestion": "团队激励、人才培育、授权赋能（管理层）"},
    {"name": "创新与变革", "suggestion": "创新思维、变革推动、持续改进"},
    {"name": "客户与服务", "suggestion": "客户意识、服务精神、需求洞察"},
    {"name": "价值观与文化", "suggestion": "企业文化认同、职业道德、廉洁自律（企业自定义）"},
]

SCORING_TEMPLATE = {
    "A": {"label": "一贯遵从", "score": 5, "desc": "行为高频出现，几乎在所有相关场景中都会发生"},
    "B": {"label": "经常发生", "score": 3, "desc": "在多数情况下会出现，成为日常工作中的常见行为模式"},
    "C": {"label": "偶尔发生", "score": 2, "desc": "出现频率较低，未形成习惯或常态"},
    "D": {"label": "极少发生", "score": 1, "desc": "极低频率，通常在特定触发条件下才会发生"},
    "E": {"label": "从未发生", "score": 0, "desc": "在评估周期内完全未出现"}
}

def new_model(company, model_name):
    return {
        "company": company,
        "model_name": model_name,
        "version": "1.0",
        "scoring": SCORING_TEMPLATE,
        "layers": {
            "management": {"label": "管理层", "total_indicators": 0},
            "staff": {"label": "员工层", "total_indicators": 0}
        },
        "dimensions": []
    }

def load_state(path):
    if not Path(path).exists():
        print(json.dumps({"error": f"状态文件不存在: {path}"}, ensure_ascii=False))
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_state(model, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)

def count_indicators(model):
    mgmt = 0
    staff = 0
    for dim in model["dimensions"]:
        for elem in dim["elements"]:
            for ind in elem.get("indicators", []):
                if ind.get("mgmt_seq"):
                    mgmt += 1
                if ind.get("staff_seq"):
                    staff += 1
    model["layers"]["management"]["total_indicators"] = mgmt
    model["layers"]["staff"]["total_indicators"] = staff

def cmd_init(args):
    if not args.company or not args.model_name:
        print(json.dumps({"error": "需要 --company 和 --model_name"}, ensure_ascii=False))
        sys.exit(1)
    model = new_model(args.company, args.model_name)
    save_state(model, args.state)
    print(json.dumps({
        "status": "ok",
        "message": f"已创建 [{args.company}] 的胜任力模型草稿",
        "state_file": args.state,
        "next_step": "使用 --action add_dimension 添加维度",
        "suggested_dimensions": UNIVERSAL_DIMENSIONS
    }, ensure_ascii=False, indent=2))

def cmd_add_dimension(args):
    model = load_state(args.state)
    dim_id = f"D{len(model['dimensions'])+1}"
    new_dim = {"id": dim_id, "name": args.dim_name, "elements": []}
    model["dimensions"].append(new_dim)
    save_state(model, args.state)
    print(json.dumps({
        "status": "ok",
        "message": f"维度【{args.dim_name}】已添加（{dim_id}）",
        "total_dimensions": len(model["dimensions"]),
        "next_step": f"使用 --action add_element --dim_name {args.dim_name} 为该维度添加要素"
    }, ensure_ascii=False, indent=2))

def cmd_add_element(args):
    model = load_state(args.state)
    dim = next((d for d in model["dimensions"] if d["name"] == args.dim_name), None)
    if not dim:
        print(json.dumps({"error": f"维度【{args.dim_name}】不存在"}, ensure_ascii=False))
        sys.exit(1)
    elem_id = f"{dim['id']}E{len(dim['elements'])+1}"
    new_elem = {
        "id": elem_id,
        "name": args.elem_name,
        "definition": args.definition or "",
        "indicators": []
    }
    dim["elements"].append(new_elem)
    save_state(model, args.state)
    print(json.dumps({
        "status": "ok",
        "message": f"要素【{args.elem_name}】已添加到维度【{args.dim_name}】",
        "next_step": f"使用 --action add_indicator --dim_name {args.dim_name} --elem_name {args.elem_name} --behavior '行为描述' --layers 管理层,员工层"
    }, ensure_ascii=False, indent=2))

def cmd_add_indicator(args):
    model = load_state(args.state)
    dim = next((d for d in model["dimensions"] if d["name"] == args.dim_name), None)
    if not dim:
        print(json.dumps({"error": f"维度【{args.dim_name}】不存在"}, ensure_ascii=False))
        sys.exit(1)
    elem = next((e for e in dim["elements"] if e["name"] == args.elem_name), None)
    if not elem:
        print(json.dumps({"error": f"要素【{args.elem_name}】不存在"}, ensure_ascii=False))
        sys.exit(1)

    layers = [l.strip() for l in (args.layers or "").split(",")]
    mgmt_seq = None
    staff_seq = None

    # 计算序号
    count_indicators(model)
    if "管理层" in layers:
        mgmt_seq = model["layers"]["management"]["total_indicators"] + 1
    if "员工层" in layers:
        staff_seq = model["layers"]["staff"]["total_indicators"] + 1

    new_ind = {
        "index": sum(len(e["indicators"]) for d in model["dimensions"] for e in d["elements"]) + 1,
        "behavior": args.behavior,
        "mgmt_seq": mgmt_seq,
        "staff_seq": staff_seq
    }
    elem["indicators"].append(new_ind)
    count_indicators(model)
    save_state(model, args.state)
    print(json.dumps({
        "status": "ok",
        "message": f"行为指标已添加",
        "behavior": args.behavior,
        "layers": layers,
        "mgmt_total": model["layers"]["management"]["total_indicators"],
        "staff_total": model["layers"]["staff"]["total_indicators"]
    }, ensure_ascii=False, indent=2))

def cmd_finalize(args):
    model = load_state(args.state)
    count_indicators(model)
    save_state(model, args.state)
    # 统计
    dims = len(model["dimensions"])
    elems = sum(len(d["elements"]) for d in model["dimensions"])
    inds = sum(len(e["indicators"]) for d in model["dimensions"] for e in d["elements"])
    print(json.dumps({
        "status": "ok",
        "summary": {
            "company": model["company"],
            "model_name": model["model_name"],
            "dimensions": dims,
            "elements": elems,
            "total_indicators": inds,
            "management_indicators": model["layers"]["management"]["total_indicators"],
            "staff_indicators": model["layers"]["staff"]["total_indicators"]
        },
        "next_step": "使用 --action export --output <路径> 导出Excel"
    }, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["init", "add_dimension", "add_element", "add_indicator", "finalize", "suggest"], required=True)
    parser.add_argument("--state", default="tmp/model_draft.json")
    parser.add_argument("--company", default=None)
    parser.add_argument("--model_name", default=None)
    parser.add_argument("--dim_name", default=None)
    parser.add_argument("--elem_name", default=None)
    parser.add_argument("--definition", default=None)
    parser.add_argument("--behavior", default=None)
    parser.add_argument("--layers", default="管理层,员工层", help="适用层级，逗号分隔")
    args = parser.parse_args()

    if args.action == "init":
        cmd_init(args)
    elif args.action == "add_dimension":
        cmd_add_dimension(args)
    elif args.action == "add_element":
        cmd_add_element(args)
    elif args.action == "add_indicator":
        cmd_add_indicator(args)
    elif args.action == "finalize":
        cmd_finalize(args)
    elif args.action == "suggest":
        print(json.dumps({"suggested_dimensions": UNIVERSAL_DIMENSIONS}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
