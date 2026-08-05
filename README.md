# Super Skill Manager (超级技能管理器)

> 一个 Hermes Agent 技能，管理你的整个技能库生命周期：接入本地化 → 定时维护 → 单技能优化。

基于工程管理实践经验（作者是轨道交通工程总工）设计，把"施工方案要有好结构"的思维应用到技能管理上。

## 为什么需要它

AI 技能用久了会变"流水账"——踩坑记录、临时发现、过程叙述越堆越多，人和 AI 都看不懂。Super Skill Manager 通过**三模式**保持技能库健康：

```
模式1 接入本地化  新技能进来 → 扫描依赖 → 查能力清单 → 本地化改良 → 贴标签
模式2 定时维护    每周定时 → 体检 + 涟漪修改（依赖连锁更新）+ 更新 wiki + 日志
模式3 单技能优化  复盘工作流 → 框架内讨论 → 归位到骨架（治流水账、治结构错位）
```

## 核心思想

1. **技能 = 施工方案**：需要固定骨架——必备 4 段（身份/触发词/怎么用/注意事项）+ 按需 3 段（验证/出错/产出）
2. **流水账必然长出来**：关键是"吸收提取"机制——AI 自动总结 + 用户讨论定侧重点 → 归位到骨架
3. **触发词冲突是最大的雷**：两个技能响应同一句话 → 可能加载错误技能，必须检测
4. **单一真相源**：能力清单等数据只存一份，不复制（复制会分叉）

## 功能

- **脚本化体检**：check_frontmatter.py（字段齐全性）、scan_deps.py（依赖断链）、scan_dupes.py（功能重复/触发词冲突）
- **wiki 生成**：generate_index.py 自动生成技能目录 + 图谱（触发词/依赖/功能），Obsidian 可视化
- **端到端测试**：22 个断言，验证所有脚本行为

## 目录结构

```
super-skill-manager/
├── SKILL.md                      # 技能主体（三模式说明）
├── references/
│   └── 技能架构方法论.md          # 蓝图：什么是一个好技能（5 标准 + 固定骨架）
├── scripts/
│   ├── check_frontmatter.py      # 体检：frontmatter 字段齐全性
│   ├── scan_deps.py              # 依赖断链扫描
│   ├── scan_dupes.py             # 功能重复 + 触发词冲突检测
│   ├── generate_index.py         # wiki 生成（目录 + 图谱）
│   ├── extract_tools.py          # 工具引用提取
│   └── test_super_skill_manager.py  # 端到端测试（22 断言）
├── templates/
│   └── 精简技能流水账.md          # 批量精简提示词模板
└── prompts/
    └── 精简技能流水账.md
```

## 快速开始

```bash
# 体检：检查所有技能的 frontmatter 字段
python scripts/check_frontmatter.py

# 断链扫描
python scripts/scan_deps.py

# 查重（功能相似 + 触发词冲突）
python scripts/scan_dupes.py

# 生成 wiki（技能目录 + 图谱）
python scripts/generate_index.py all

# 测试
python scripts/test_super_skill_manager.py
```

脚本支持环境变量覆盖路径（不设则用默认）：
- `SSM_SKILLS_ROOT` — 技能库根目录
- `SSM_WIKI_ROOT` — wiki 输出目录

## 依赖

- Python 3.10+
- Hermes Agent（或任何支持 SKILL.md frontmatter 的 agent 框架）
- 可选：Obsidian（wiki 可视化）

## License

MIT
