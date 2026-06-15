#!/usr/bin/env python3
"""
查询胜任力模型知识库
用法: uv run --python 3.12 scripts/query_model.py --action <action> [--keyword <kw>] [--layer <管理层|员工层>] [--element <要素名>]
"""
import argparse, json, sys
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "references" / "tangjiu_model.json"

def load_model():
    with open(MODEL_PATH, encoding="utf-8") as f:
        return json.load(f)

def get_all_elements(model):
    """返回所有维度→要素的扁平列表"""
    result = []
    for dim in model["dimensions"]:
        for elem in dim["elements"]:
            result.append({"dimension": dim["name"], "element": elem})
    return result

def search(model, keyword=None, layer=None, element_name=None):
    """搜索相关指标"""
    results = []
    for dim in model["dimensions"]:
        for elem in dim["elements"]:
            # 按要素名过滤
            if element_name and element_name not in elem["name"]:
                continue
            for ind in elem["indicators"]:
                # 按层级过滤
                if layer == "管理层" and ind["mgmt_seq"] is None:
                    continue
                if layer == "员工层" and ind["staff_seq"] is None:
                    continue
                # 按关键词过滤
                if keyword and keyword not in ind["behavior"] and keyword not in elem["name"] and keyword not in dim["name"] and keyword not in elem["definition"]:
                    continue
                results.append({
                    "dimension": dim["name"],
                    "element": elem["name"],
                    "element_def": elem["definition"],
                    "index": ind["index"],
                    "behavior": ind["behavior"],
                    "mgmt_seq": ind["mgmt_seq"],
                    "staff_seq": ind["staff_seq"]
                })
    return results

def format_indicator(ind, model):
    """格式化单个指标输出"""
    layers = []
    if ind["mgmt_seq"]:
        layers.append(f"管理层第{ind['mgmt_seq']}条")
    if ind["staff_seq"]:
        layers.append(f"员工层第{ind['staff_seq']}条")
    layer_str = "、".join(layers) if layers else "（未分配层级）"

    scoring = model["scoring"]
    score_guide = " | ".join([f"{k}={v['label']}({v['score']}分)" for k, v in scoring.items()])

    return {
        "维度": ind["dimension"],
        "要素": ind["element"],
        "要素定义": ind["element_def"],
        "行为指标": ind["behavior"],
        "适用层级": layer_str,
        "评分参考": score_guide
    }

def cmd_overview(model):
    """输出模型总览"""
    out = {
        "model_name": model["model_name"],
        "structure": "7维度 × 17要素 × 43条行为指标",
        "layers": model["layers"],
        "scoring_note": "A=5分 B=3分 C=2分 D=1分 E=0分（非线性，A级权重有意放大）",
        "dimensions": []
    }
    for dim in model["dimensions"]:
        dim_info = {
            "name": dim["name"],
            "elements": []
        }
        for elem in dim["elements"]:
            mgmt_count = sum(1 for i in elem["indicators"] if i["mgmt_seq"])
            staff_count = sum(1 for i in elem["indicators"] if i["staff_seq"])
            dim_info["elements"].append({
                "name": elem["name"],
                "definition": elem["definition"],
                "mgmt_indicators": mgmt_count,
                "staff_indicators": staff_count,
                "total": len(elem["indicators"])
            })
        out["dimensions"].append(dim_info)
    print(json.dumps(out, ensure_ascii=False, indent=2))

def cmd_search(model, keyword, layer, element_name):
    """搜索并输出结果"""
    results = search(model, keyword=keyword, layer=layer, element_name=element_name)
    if not results:
        print(json.dumps({"found": 0, "results": [], "tip": "未找到匹配内容，请尝试其他关键词"}, ensure_ascii=False, indent=2))
        return
    formatted = [format_indicator(r, model) for r in results]
    print(json.dumps({"found": len(formatted), "results": formatted}, ensure_ascii=False, indent=2))

def cmd_scoring_guide(model):
    """输出评分标准说明"""
    scoring = model["scoring"]
    out = {
        "title": "能力评估评分标准",
        "note": "注意：评分非连续线性，A与B之间差距2分，体现高绩效行为的刻意放大",
        "levels": [
            {"level": k, "label": v["label"], "score": v["score"], "description": v["desc"]}
            for k, v in scoring.items()
        ]
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["overview", "search", "scoring", "element"], required=True)
    parser.add_argument("--keyword", default=None, help="搜索关键词")
    parser.add_argument("--layer", choices=["管理层", "员工层"], default=None)
    parser.add_argument("--element", default=None, help="要素名称")
    args = parser.parse_args()

    model = load_model()

    if args.action == "overview":
        cmd_overview(model)
    elif args.action == "search":
        cmd_search(model, keyword=args.keyword, layer=args.layer, element_name=args.element)
    elif args.action == "scoring":
        cmd_scoring_guide(model)
    elif args.action == "element":
        if not args.element:
            print(json.dumps({"error": "请用 --element 指定要素名称"}, ensure_ascii=False))
            sys.exit(1)
        cmd_search(model, element_name=args.element)

if __name__ == "__main__":
    main()
