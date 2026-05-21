---
name: hrbp-inventory
description: >
  HRBP人才盘点技能。覆盖盘点全流程：初始化盘点配置（命名/阈值/KPI规则）、
  素质评分异常检测与中位数调平、KPI绩效数据导入、25格落位计算、
  输出分析报告Excel（矩阵图/员工明细/梯队名单/数据质量报告/统计摘要）。
  触发词：开始盘点、人才盘点、落位、梯队、打分异常、调平、绩效素质、九宫格、25格、哪些人还没交、进度怎么样、出报告。
metadata: {"openclaw":{"emoji":"📊","requires":{"bins":["uv"]}}}
---

# HRBP 人才盘点

## 角色定位

你是 HRBP，负责推进盘点全流程：收集数据、清洗处理、落位计算、输出报告。
提醒范围：**只提醒 HRBP 本人**（你），不直接联系业务团队。

---

## 盘点全流程

### 阶段1：初始化盘点

**触发**：用户说"开始盘点"、"发起新一轮盘点"、"我要做盘点"

**步骤（一次问一个，不要一次全问）：**

> 第1问：本次盘点的名称是什么？（例：2025H1、2025年度）
> 第2问：覆盖时间范围？（例：2025-01-01 至 2025-06-30）
> 第3问：绩效轴分档——优秀≥?%，合格≥?%？（默认：优秀≥110%，合格≥80%，沿用直接说"沿用"）
> 第4问：素质轴分档——优秀≥?分，良好≥?分，合格≥?分？（默认：110/90/75，沿用直接说"沿用"）
> 第5问：哪些部门用非综合绩效指标？（默认：加盟中心=开店数，其余=综合绩效达成率）

确认后保存配置：
```bash
python3 skills/hrbp-inventory/scripts/init_inventory.py \
  --action save \
  --name <盘点名称> \
  --config_json '<JSON字符串>'
```

---

### 阶段2：素质评分处理

**触发**：用户上传素质评分文件，或说"帮我处理评分数据"

**处理逻辑（严格执行，不可修改）：**

```
执行顺序（顺序不可颠倒）：
  ① 先标记异常评分者
  ② 再基于非异常评分者数据计算IQR边界
  ③ 最后标记极值

Step 1：异常评分者检测（使用 median + 3×MAD，对离群值鲁棒）
  global_median = median(所有S_raw)
  MAD = median(|S_raw_i - global_median|)
  effective_threshold = max(config.std_threshold, 1.0)

  对每个评分者 rater_i（评分数 ≥ 3）：
    std_i = std(rater_i打出的所有分数)
    mean_i = mean(rater_i打出的所有分数)

    若 std_i < effective_threshold → 标记"平均主义"（打分高度集中）
    若 mean_i > global_median + 3×MAD → 标记"偏高"
    若 mean_i < global_median - 3×MAD → 标记"偏低"

  注意：使用median+3×MAD而非mean+2σ，防止偏高/偏低评分者本身拉偏全局基准

Step 2：IQR去极值（组内，仅基于非异常评分者数据计算边界）
  对每个部门 g（有效样本 ≥ 4）：
    valid_g = 部门g中非异常评分者的评分数据
    Q1_g = valid_g.quantile(0.25)
    Q3_g = valid_g.quantile(0.75)
    IQR_g = Q3_g - Q1_g
    若 IQR_g == 0：跳过（防止全同分时误判）
    保留范围：[Q1_g - 1.5×IQR_g, Q3_g + 1.5×IQR_g]
    超出范围的非异常评分者记录：标记 outlier=True

Step 3：计算组内中位数
  valid_final_g = 部门g中 outlier=False 且 anomaly_rater_excluded=False 的记录
  若 len(valid_final_g) > 0：
    M_g = median(valid_final_g.S_raw)
  否则（全部被排除，fallback）：
    M_g = median(部门g全量原始数据)
    标记 fallback=True，输出警告"建议人工复核"

Step 4：全局基准
  M_global = median([M_g for all g])  ← 各组中位数的中位数，非全员中位数

Step 5：调平系数
  δ_g = M_global - M_g

Step 6：调平后分数
  S_adj = clip(S_raw + δ_g, 0, max_score)
  max_score：管理层=145分，员工层=120分
```

```bash
python3 skills/hrbp-inventory/scripts/score_processor.py \
  --action full \
  --inventory <盘点名称> \
  --input <评分文件路径>
```

**输出后告知用户**：
- 发现了哪些异常评分者（平均主义/偏高/偏低）及原因
- 各部门调平系数δ
- 若有 fallback=True 的部门，明确提示"XX部门评分数据异常，调平结果仅供参考，建议人工复核"

---

### 阶段3：落位计算 + 报告输出

**触发**：用户上传KPI数据，或说"出报告"、"做落位"

```bash
python3 skills/hrbp-inventory/scripts/grid_placement.py \
  --inventory <盘点名称> \
  --kpi_input <KPI文件路径> \
  --output artifacts/<盘点名称>-盘点结果.xlsx
```

**输出Excel包含5个Sheet：**
1. **落位总览-25格矩阵** — 可视化矩阵，颜色区分梯队，每格内列员工名
2. **员工明细** — 每人一行，含绩效/素质/格子/梯队/备注
3. **梯队名单** — 第一/第二梯队等分列展示
4. **数据质量报告** — 异常评分者、极值、KPI缺失明细
5. **统计摘要** — 各部门梯队分布、整体概览

---

### 阶段4：进度提醒（HRBP侧）

**触发**：用户问"谁还没交"、"进度怎么样"、"有没有缺数据的"

根据已有数据和待收数据，告知 HRBP：
- 哪些部门的素质评分尚未上传
- KPI数据是否完整
- 数据缺失的员工名单

**不主动联系业务团队，只告知 HRBP。**

---

## 数据文件约定

| 文件 | 位置 | 说明 |
|------|------|------|
| 盘点配置 | `data/inventories/<名称>/config.json` | 每次盘点的参数 |
| 调平结果 | `data/inventories/<名称>/scores_processed.json` | 处理后的素质评分 |
| 输出报告 | `artifacts/<名称>-盘点结果.xlsx` | 最终交付文件 |

---

## 关键约束

- **每次盘点用命名隔离**，历史盘点数据不覆盖
- **异常数据不删除，只排除出调平计算**，最终报告透明说明
- **KPI取值规则**按部门配置，不统一套用综合绩效
- **落位规则**每次盘点开始前确认，不默认沿用上次

---

## 调平算法已知边界案例（经10场景测试验证）

### BUG-01：平均主义阈值过低漏检（已修复）
- **现象**：std阈值=0.3，评分者std=0.577未被检测为平均主义
- **根因**：量表满分145，正常评分者std通常>1.5，固定阈值0.3远低于实际需要
- **修复**：`effective_threshold = max(config.std_threshold, 1.0)`

### BUG-02：IQR执行顺序错误导致正常值误判（已修复）
- **现象**：平均主义评分者(std≈0)压缩组内方差，导致正常值被IQR判为极值排除
- **根因**：旧逻辑同步执行异常标记和IQR计算，平均主义数据污染了IQR边界
- **修复**：严格顺序 ① 标记异常评分者 → ② 仅用非异常评分者数据算IQR → ③ 标记极值

### BUG-03：偏高/偏低评分者用mean+2σ时漏检（已修复）
- **现象**：偏高评分者mean=120，全局mean+2σ=127，漏检
- **根因**：偏高/偏低评分者本身的数据拉偏了全局mean，σ自动放宽
- **修复**：改用 `global_median + 3×MAD`；MAD对离群值鲁棒，3×MAD≈正态分布2σ

### BUG-04：部门所有评分者被排除后employees为空（已修复）
- **现象**：某部门评分者全被判为平均主义，有效样本=0，中位数=NaN，employees列表空
- **根因**：未处理有效样本为0的边界情况
- **修复**：回退机制——有效样本=0时使用全量原始数据，标记`fallback=True`并输出警告

### 边界行为（非BUG，符合预期）

| 场景 | 行为 |
|------|------|
| 全员同分（IQR=0） | 跳过极值检测，delta=0，正常通过 |
| 单人部门（n<4） | 跳过IQR极值检测，避免小样本失真 |
| 唯一评分者 | std=NaN时不触发平均主义检测 |
| 含NaN分数 | 自动fillna(0)，不崩溃 |
| 调平后超界 | S_adj = clip(S_raw+δ, 0, max_score) 强制钳位 |
| 部门内排名 | δ对同部门所有人相同，部门内相对排名不变 |
