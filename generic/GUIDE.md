# 未来工作厘定助手（通用版）— 操作指南

> 一份指南，两套语言：AI 读左边，人读右边。

---

## 🤖 FOR AI AGENTS（机器可读）

```yaml
package: future-work-clarifier-general
version: 0.2.1
role: work-decomposition-co-creation-agent
lang: [zh, en]
entry_file: CLAUDE.md
entry_command: /workshop
skill_path: skills/general-workshop/SKILL.md
```

### What this package is

A structured co-creation agent that helps any role decompose their work into granular units, judge AI-era value migration, and proactively search GitHub for mature open-source reference implementations.

### When to invoke

**Invoke when user says things like:**
- "我是 XX 岗位，想看看工作哪些能被 AI 做"
- "帮我拆解一下我的工作"
- "我想知道我的工作未来怎么变"
- "哪些工作可以先让 AI 帮我做"
- Any phrase matching: 工作拆解 | 岗位分析 | AI 替代 | 工作厘定 | 未来工作

**Do NOT invoke when:**
- User asks a factual policy/regulation question (用普通搜索)
- User wants tool recommendations without analysis (先引导拆解)
- User wants career advice / job market predictions

### How to load

**Claude Code:**
```
cd future-work-general-edition-v2/
# CLAUDE.md auto-loads. Type:
/workshop
```

**WorkBuddy / 其他支持 CLAUDE.md 的工具:**
```
在项目根目录放置此包的 CLAUDE.md，或将 CLAUDE.md 内容注入 system prompt。
确保 references/ 和 skills/ 目录可被 Agent 访问。
```

**Cursor / Windsurf / 通用 IDE Agent:**
```
将 CLAUDE.md 粘贴为 Project Rules。
将 skills/general-workshop/SKILL.md 作为上下文注入。
所有 references/ 路径需要调整为实际路径。
```

**Generic / API-based Agent:**
```
1. 将 CLAUDE.md 的全部内容作为 system prompt 注入
2. 将 skills/general-workshop/SKILL.md 追加为 skill context
3. 将 references/core/framework-overview.md 追加为 framework context
4. 其他 references/ 文件按需加载（标注标准、锚定规则、提问规则、GitHub 搜索协议、交互层设计、对话模板）
5. 将 references/tools/work-inventory-template.xlsx 路径告知用户（S2 阶段按需引入）
6. 提供 /workshop 命令入口
```

### Core workflow (do not skip steps)

```
S1 工作性质 → S2 颗粒度拆解 → S3 问题模式 → S4 执行主体 → S5 价值增益 → S6-A 能力映射 → S6-B 约束 → (Gate) → S6-C GitHub 搜索
```

### Critical rules

1. Never expose S1-S6 terminology to the user — use the translation table in `references/product/interaction-layer.md`
2. Always confirm user perspective (manager vs individual) in Phase 1
3. For granules with S4 ∈ {自动接管, AI主辅协同} AND S6-B pass → MUST proactively search GitHub
4. End every turn with: "这一轮我们先确认了：___。接下来最值得继续看的，是：___。"
5. Never fabricate GitHub repos — if search fails, honestly report and suggest alternatives

### Output contract (5+1)

1. 工作颗粒度地图 (table)
2. 四维标记表 S3-S6 (table)
3. 未来变化判断 (4 categorized lists)
4. 跨角色关键议题清单 (table)
5. 工作未来命题 ("从 X 转向 Y" format)
6. 🆕 开源参考实现建议 (recommendation cards — if S6-C triggered)

### Key reference files

| File | Load when |
|------|-----------|
| `references/core/framework-overview.md` | Entering analysis |
| `references/core/labeling-standard.md` | S2-S6 labeling |
| `references/core/anchoring-rules.md` | Self-check before each step |
| `references/core/questioning-rules.md` | Guiding user at each S-stage |
| `references/core/github-search-protocol.md` | S6-C triggered |
| `references/product/interaction-layer.md` | Every user-facing turn |
| `references/product/conversation-patterns.md` | Scene-matching in dialogue |
| `references/product/output-spec.md` | Final output composition |
| `references/tools/work-inventory-template.xlsx` | S2 when user is scattered |

### Dependency declaration

- No Python packages required
- No external binaries required
- Requires: WebSearch tool (for GitHub search)
- Nice to have: WebFetch tool (for repo detail scoring)

---

## 👤 FOR HUMANS（人类可读）

### 这是什么

一个 AI 工具，帮你搞清楚：**你的工作到底由什么组成、哪些部分会被 AI 接走、哪些会升值、现在能用什么开源工具开始做。**

它不是问答机器人，更像一个带着你把工作拆开、看清、判断的工作伙伴。

### 适合谁用

| 你可能是 | 你会得到 |
|----------|---------|
| 团队/部门负责人 | 团队工作全景图、哪些值得先改、试点优先级 |
| 普通员工/骨干 | 你的工作拆解图、危险区 vs 升值区、AI 起步建议 |
| 任何想搞清楚"我的工作未来怎么变"的人 | 一份结构化的分析，不是几句鸡汤 |

### 怎么开始

你不需要准备任何文档。只要说清楚三件事：

1. 你想讨论什么工作（比如"我是连锁门店的经营督导"）
2. 当前最大的困扰（比如"我每周花 3 天填检查表"）
3. 你是看自己还是看团队

然后说一句"/workshop"，就开始了。

### 三种开始方式

| 方式 | 你可以这样说 |
|------|------------|
| 按岗位 | "我是 XX，想看看这个岗位未来怎么变" |
| 按具体工作 | "我想拆解客户跟进这件事" |
| 按痛点 | "我每天做很多重复劳动，哪些可以让 AI 做" |

### 过程大概什么样

总共大概 5-15 分钟，6 步：

1. **先看清** — 你的工作本质上更像规则型、风险型还是设计型？
2. **拆开** — 把大工作拆成不同颗粒度，哪些是高频低价值、哪些是低频高价值？
3. **判断** — 每类问题应该怎么处理？需要明确答案还是看风险？
4. **分工** — 哪些 AI 可以直接做？哪些 AI 先做一层你再判断？
5. **找工具** — AI 直接帮你去 GitHub 搜现成的开源项目，告诉你哪个能用、怎么用
6. **收口** — 你得到一份完整的分析 + 下一步动作建议

### 不同工具怎么用

#### Claude Code（推荐）
直接把整个 `future-work-general-edition-v2/` 目录放到你的项目里，在里面启动 Claude Code，输入：
```
/workshop
```

#### WorkBuddy
将目录放到工作区，确保 CLAUDE.md 能被 WorkBuddy 识别。然后在对话中输入：
```
按照 skills/general-workshop/SKILL.md 的定义，帮我做一次工作厘定。
我是 [你的岗位]，想看看 [你想讨论的]
```

#### Cursor
1. 将 `CLAUDE.md` 的内容粘贴到 Cursor 的 Project Rules 中
2. 在对话中说："请按照 Project Rules 中的未来工作厘定流程，帮我分析我的工作"

#### 通义灵码 / Copilot / 其他 AI 助手
在对话开头粘贴以下提示词：
```
你是一个工作厘定助手。请按以下流程带我分析：
1. 先帮我缩小讨论对象
2. 把我的工作拆成不同颗粒度
3. 判断每类工作的性质
4. 判断哪些适合 AI 接管
5. 帮我去 GitHub 搜开源实现
不要一上来就甩术语，用我能听懂的话。
```

### 最后你会得到什么

- 📊 一张工作颗粒度地图（你的工作到底由什么组成）
- 🏷️ 一张标记表（每个颗粒度的 AI 可行性和变化幅度）
- 🔮 未来变化判断（哪些会被接走、哪些会升值）
- 🔗 跨角色议题清单（哪些事需要拉别人一起看）
- 💬 一句"从 X 转向 Y"的判断（你的工作未来方向）
- 🛠️ GitHub 开源参考实现建议（如果能 AI 化，现在有哪些现成的开源项目可以直接用或参考）

### 需要准备材料吗

不需要。材料是加速器，不是门票。聊着聊着如果觉得判断不够稳，AI 会主动问你要不要补个工作清单或流程说明。

### 一个真实例子

> 用户："我是连锁加盟品牌的经营督导，想看看我的工作哪些可以先让 AI 帮我做"
>
> AI："好。经营督导我大概理解——跑店检查、数据汇总、整改追踪、加盟商沟通。在往下走之前，你是从管理者角度看团队，还是从自己的角度看个人工作？"
>
> 【5 分钟后】
>
> AI："我们确认了——你的 6 个工作中，检查表填写、数据汇总、报表生成可以直接让系统接管。我在 GitHub 上帮你搜到了 3 类共 9 个开源工具，最匹配的是积木报表（5k+ Stars），你可以这周就注册在线版试试。"

---

## 📦 包结构速查

```
future-work-general-edition-v2/
├── CLAUDE.md              ← Agent 主提示词（AI 入口）
├── agent-pack.yaml        ← 包清单
├── GUIDE.md               ← 本文件
├── agent/SOUL.md          ← 人格定义
├── skills/general-workshop/SKILL.md  ← 核心技能定义
└── references/            ← 框架定义 + 交互规范 + 工具表
    ├── core/              ← S1-S6 框架 + 标注标准 + 搜索协议
    ├── product/           ← 交互层 + 对话模板 + 输入输出规范
    ├── user/              ← 用户手册
    └── tools/             ← S2 颗粒度拆解工具表 (.xlsx)
```
