#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_index.py — 扫描 Hermes 技能库所有 SKILL.md，
解析 frontmatter 生成 Obsidian skills-wiki 内容。

输出模式（通过命令行参数选择）：
  python generate_index.py all  → 生成全部 6 个文件写入 Obsidian

生成文件：
  index.md                      ← 导航入口（统计 + 依赖速查 + 一行摘要）
  concepts/技能详情.md           ← 全量技能详情（触发词/依赖/状态）
  concepts/能力清单.md           ← 工具能力（从技能内 references 同步，手动维护 wikilink）
  views/触发词图谱.md            ← 触发词冲突可视化（同一触发词被哪些技能共用）
  views/工具依赖图谱.md          ← 工具依赖可视化（哪些技能依赖同一工具）
  views/技能依赖图谱.md          ← 技能间依赖链（技能→技能 wikilink）
  views/功能图谱.md              ← 功能相似可视化（function 字段重叠的技能对）

只读扫描，不修改任何技能文件。仅用 Python 标准库。
"""

import os
import re
import sys
from pathlib import Path
from datetime import date

SKILLS_ROOT = Path(os.environ.get("SSM_SKILLS_ROOT", r"<SKILLS_ROOT>"))
WIKI_ROOT = Path(os.environ.get("SSM_WIKI_ROOT", r"<WIKI_ROOT>\skills-wiki"))
TODAY = date.today().isoformat()


def parse_frontmatter(text):
    if text.startswith("\ufeff"):
        text = text[1:]
    stripped = text.lstrip("\r\n")
    if not stripped.startswith("---"):
        return {}, "empty"
    after_open = stripped[3:]
    m = re.search(r"^---\s*$", after_open, re.MULTILINE)
    if not m:
        return {}, "broken"
    body = after_open[: m.start()]
    data = {}
    for line in body.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        km = re.match(r"^([A-Za-z_][A-Za-z0-9_\-]*?)\s*:\s*(.*)$", line)
        if not km:
            continue
        data[km.group(1).strip()] = km.group(2).strip()
    return data, "ok"


def clean_list_field(raw):
    if raw is None:
        return ""
    s = raw.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    parts = [p.strip().strip('"').strip("'").strip() for p in s.split(",")]
    parts = [p for p in parts if p]
    return ", ".join(parts)


def norm(s):
    if not s:
        return ""
    return re.sub(r"[\s，。、：:；;,.()（）\-_/\\'\"!?！？]", "", str(s)).lower()


def char_overlap(a, b):
    if not a or not b:
        return 0
    set_a, set_b = set(a), set(b)
    if not set_a or not set_b:
        return 0
    return len(set_a & set_b) / min(len(set_a), len(set_b))


def classify_deps(deps_str, skill_names):
    skill_deps, cap_deps = [], []
    for d in deps_str.split(", "):
        d = d.strip()
        if not d:
            continue
        if d in skill_names:
            skill_deps.append(d)
        else:
            cap_deps.append(d)
    return skill_deps, cap_deps


def scan_skills():
    records = []
    for root, dirs, files in os.walk(SKILLS_ROOT):
        if "SKILL.md" in files:
            p = Path(root) / "SKILL.md"
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                text = ""
            data, fm_status = parse_frontmatter(text)
            rel = p.relative_to(SKILLS_ROOT)
            parts = rel.parts
            category = parts[0] if len(parts) >= 2 else "(root)"
            sub_path = str(rel.parent).replace("\\", "/")
            name = data.get("name") or (sub_path.split("/")[-1] if sub_path else "(root)")
            records.append({
                "category": category,
                "name": name,
                "function": data.get("function") or "",
                "triggers": clean_list_field(data.get("triggers")),
                "tags": clean_list_field(data.get("tags")),
                "status": data.get("status") or "",
                "fm_status": fm_status,
                "path": sub_path,
                "dependencies": clean_list_field(data.get("dependencies")),
            })
    return records


def group_by_cat(records):
    by_cat = {}
    for r in records:
        by_cat.setdefault(r["category"], []).append(r)
    return by_cat


# ─── 生成 index.md ───

def gen_index(records):
    total = len(records)
    tagged = sum(1 for r in records if r["fm_status"] == "ok" and (r["tags"] or r["triggers"] or r["function"]))
    untagged = total - tagged
    dep_counter = {}
    for r in records:
        for d in (r["dependencies"] or "").split(", "):
            d = d.strip()
            if d:
                dep_counter[d] = dep_counter.get(d, 0) + 1
    by_cat = group_by_cat(records)

    out = []
    out.append("# Hermes 技能库索引")
    out.append("")
    out.append(f"> 扫描根目录：`{SKILLS_ROOT}` | 最后更新：{TODAY}")
    out.append("")
    out.append("## 统计")
    out.append("")
    out.append(f"- 技能总数：**{total}**")
    out.append(f"- 已贴标签数：**{tagged}**")
    out.append(f"- 未贴标签数：**{untagged}**")
    out.append("")
    out.append("## 导航")
    out.append("")
    out.append("### Concepts（静态事实）")
    out.append("- [[concepts/技能详情]] — 全量技能详情（触发词/依赖/状态）")
    out.append("- [[concepts/能力清单]] — 本机工具能力（替代映射 + 验证命令）")
    out.append("")
    out.append("### Views（图谱视角）")
    out.append("- [[views/触发词图谱]] — 触发词冲突可视化")
    out.append("- [[views/工具依赖图谱]] — 工具依赖可视化")
    out.append("- [[views/技能依赖图谱]] — 技能间依赖链")
    out.append("- [[views/功能图谱]] — 功能相似可视化")
    out.append("")
    out.append("### Raw")
    out.append("- `raw/` — 技能原始文件（符号链接实时同步）")
    out.append("")
    out.append("## 依赖速查（被依赖最多的 TOP 20）")
    out.append("")
    out.append("> 删/改名技能前先看这里：被 N 个技能依赖的，改了会断链。")
    out.append("")
    for d, cnt in sorted(dep_counter.items(), key=lambda x: -x[1])[:20]:
        out.append(f"- **{d}** ← 被 {cnt} 个技能依赖")
    out.append("")
    out.append("## 技能摘要（一行一个）")
    out.append("")
    for cat in sorted(by_cat.keys()):
        out.append(f"### {cat}")
        out.append("")
        for r in by_cat[cat]:
            func = r["function"] if r["function"] else "未贴标签"
            out.append(f"- `{r['name']}` — {func}")
        out.append("")
    return "\n".join(out)


# ─── 生成 concepts/技能详情.md ───

def gen_catalog(records):
    skill_names = {r["name"] for r in records}
    by_cat = group_by_cat(records)

    out = []
    out.append("---")
    out.append("title: 技能详情")
    out.append("created: 2026-08-04")
    out.append(f"updated: {TODAY}")
    out.append("type: concept")
    out.append("tags: [目录, 详情]")
    out.append("---")
    out.append("")
    out.append("# 技能详情")
    out.append("")
    out.append(f"> 共 {len(records)} 个技能，按分类排列。每行含触发词/依赖/状态。")
    out.append(f"> 生成自 generate_index.py | 最后更新：{TODAY}")
    out.append("")
    for cat in sorted(by_cat.keys()):
        out.append(f"## {cat}")
        out.append("")
        for r in by_cat[cat]:
            if r["fm_status"] != "ok":
                out.append(f"- `{r['name']}` — 无frontmatter")
                continue
            func = r["function"] if r["function"] else "未贴标签"
            trig = r["triggers"] if r["triggers"] else "—"
            st = r["status"] if r["status"] else "—"
            dep_str = r["dependencies"] if r["dependencies"] else ""
            if dep_str:
                s_deps, c_deps = classify_deps(dep_str, skill_names)
                parts = []
                if s_deps:
                    parts.append("技能依赖: " + ", ".join(f"[[{d}]]" for d in s_deps))
                if c_deps:
                    parts.append("能力依赖: " + ", ".join(c_deps))
                dep_disp = " | ".join(parts) if parts else "—"
            else:
                dep_disp = "—"
            out.append(f"- `{r['name']}` — {func} [触发词: {trig}] [{dep_disp}] [{st}]")
        out.append("")
    return "\n".join(out)


# ─── 生成 views/触发词图谱.md ───

def gen_trigger_view(records):
    # 触发词 → [技能名列表]
    trig_map = {}
    for r in records:
        trigs = r["triggers"]
        if not trigs or trigs == "未贴标签":
            continue
        for t in trigs.split(", "):
            t = t.strip()
            if t:
                trig_map.setdefault(t, []).append(r["name"])

    out = []
    out.append("---")
    out.append("title: 触发词图谱")
    out.append("created: 2026-08-04")
    out.append(f"updated: {TODAY}")
    out.append("type: view")
    out.append("tags: [触发词, 图谱, 冲突]")
    out.append("---")
    out.append("")
    out.append("# 触发词图谱")
    out.append("")
    out.append("> 同一触发词被多个技能共用 = 冲突（会抢加载）。")
    out.append(f"> 生成自 generate_index.py | 最后更新：{TODAY}")
    out.append("")
    # 只显示被 2+ 技能共用的触发词（有冲突的）
    conflicts = {t: skills for t, skills in trig_map.items() if len(skills) >= 2}
    if conflicts:
        out.append("## ⚠️ 冲突触发词（2+ 技能共用）")
        out.append("")
        for t in sorted(conflicts.keys()):
            skills = conflicts[t]
            links = ", ".join(f"[[{s}]]" for s in skills)
            out.append(f"- **{t}** → {links}（{len(skills)} 个技能抢）")
        out.append("")
    # 全量触发词索引
    out.append("## 全量触发词索引")
    out.append("")
    for t in sorted(trig_map.keys()):
        skills = trig_map[t]
        links = ", ".join(f"[[{s}]]" for s in skills)
        out.append(f"- {t} → {links}")
    out.append("")
    out.append(f"---")
    out.append(f"共 {len(trig_map)} 个触发词，其中 {len(conflicts)} 个有冲突")
    return "\n".join(out)


# ─── 生成 views/工具依赖图谱.md ───

def gen_tool_dep_view(records):
    skill_names = {r["name"] for r in records}
    # 工具 → [技能名列表]
    tool_map = {}
    for r in records:
        dep_str = r["dependencies"] if r["dependencies"] else ""
        if not dep_str:
            continue
        _, c_deps = classify_deps(dep_str, skill_names)
        for d in c_deps:
            tool_map.setdefault(d, []).append(r["name"])

    out = []
    out.append("---")
    out.append("title: 工具依赖图谱")
    out.append("created: 2026-08-04")
    out.append(f"updated: {TODAY}")
    out.append("type: view")
    out.append("tags: [工具, 依赖, 图谱]")
    out.append("---")
    out.append("")
    out.append("# 工具依赖图谱")
    out.append("")
    out.append("> 哪些技能依赖同一工具。工具消失 = 这些技能全断链。")
    out.append(f"> 生成自 generate_index.py | 最后更新：{TODAY}")
    out.append("")
    out.append("## 工具 → 技能（按被依赖数排序）")
    out.append("")
    for tool in sorted(tool_map.keys(), key=lambda t: -len(tool_map[t])):
        skills = tool_map[tool]
        links = ", ".join(f"[[{s}]]" for s in skills)
        out.append(f"- **{tool}** ← {links}（{len(skills)} 个技能）")
    out.append("")
    out.append(f"---")
    out.append(f"共 {len(tool_map)} 个工具被依赖")
    return "\n".join(out)


# ─── 生成 views/技能依赖图谱.md ───

def gen_skill_dep_view(records):
    skill_names = {r["name"] for r in records}
    by_cat = group_by_cat(records)
    dep_count = 0

    out = []
    out.append("---")
    out.append("title: 技能依赖图谱")
    out.append("created: 2026-08-04")
    out.append(f"updated: {TODAY}")
    out.append("type: view")
    out.append("tags: [技能, 依赖, 图谱]")
    out.append("---")
    out.append("")
    out.append("# 技能间依赖图谱")
    out.append("")
    out.append("> 技能→技能的依赖关系。Obsidian 图谱视图自动显示连线。")
    out.append(f"> 生成自 generate_index.py | 最后更新：{TODAY}")
    out.append("")
    out.append("## 依赖关系列表")
    out.append("")
    for cat in sorted(by_cat.keys()):
        cat_deps = []
        for r in by_cat[cat]:
            dep_str = r["dependencies"] if r["dependencies"] else ""
            if not dep_str:
                continue
            s_deps, _ = classify_deps(dep_str, skill_names)
            for d in s_deps:
                if r["name"] != d:  # 跳过自引用
                    cat_deps.append((r["name"], d))
                    dep_count += 1
        if cat_deps:
            out.append(f"### {cat}")
            out.append("")
            for src, dst in cat_deps:
                out.append(f"- [[{src}]] → [[{dst}]]")
            out.append("")
    out.append(f"---")
    out.append(f"共 {dep_count} 条技能间依赖")
    return "\n".join(out)


# ─── 生成 views/功能图谱.md ───

def gen_function_view(records):
    # function 相似度比对
    pairs = []
    recs = [r for r in records if r["function"]]
    for i in range(len(recs)):
        for j in range(i + 1, len(recs)):
            ov = char_overlap(norm(recs[i]["function"]), norm(recs[j]["function"]))
            if ov >= 0.5:
                pairs.append((recs[i]["name"], recs[j]["name"], recs[i]["function"], recs[j]["function"], ov))

    out = []
    out.append("---")
    out.append("title: 功能图谱")
    out.append("created: 2026-08-04")
    out.append(f"updated: {TODAY}")
    out.append("type: view")
    out.append("tags: [功能, 相似, 图谱]")
    out.append("---")
    out.append("")
    out.append("# 功能图谱")
    out.append("")
    out.append("> function 字段字符重叠率 ≥ 50% 的技能对 = 功能可能重复。")
    out.append(f"> 生成自 generate_index.py | 最后更新：{TODAY}")
    out.append("")
    if pairs:
        out.append("## ⚠️ 功能相似候选")
        out.append("")
        for n1, n2, f1, f2, ov in sorted(pairs, key=lambda x: -x[4]):
            out.append(f"- [[{n1}]] ↔ [[{n2}]]（重叠率 {ov:.0%}）")
            out.append(f"  - {f1}")
            out.append(f"  - {f2}")
        out.append("")
    else:
        out.append("## ✅ 无功能相似候选")
        out.append("")
    out.append(f"---")
    out.append(f"共 {len(pairs)} 对功能相似候选")
    return "\n".join(out)


# ─── 主函数 ───

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    records = scan_skills()

    if mode == "all":
        # 确保目录存在
        (WIKI_ROOT / "concepts").mkdir(parents=True, exist_ok=True)
        (WIKI_ROOT / "views").mkdir(parents=True, exist_ok=True)
        (WIKI_ROOT / "entities").mkdir(parents=True, exist_ok=True)

        # 生成 6 个文件（能力清单手动维护，不覆盖）
        files = {
            "index.md": gen_index(records),
            "concepts/技能详情.md": gen_catalog(records),
            "views/触发词图谱.md": gen_trigger_view(records),
            "views/工具依赖图谱.md": gen_tool_dep_view(records),
            "views/技能依赖图谱.md": gen_skill_dep_view(records),
            "views/功能图谱.md": gen_function_view(records),
        }
        for rel_path, content in files.items():
            full_path = WIKI_ROOT / rel_path
            full_path.write_text(content, encoding="utf-8")
            lines = len(content.splitlines())
            print(f"  ✓ {rel_path} ({lines} 行)")
        print(f"\n✓ 已生成 {len(files)} 个文件到 {WIKI_ROOT}")
        print(f"  （concepts/能力清单.md 为手动维护，未覆盖）")

        # 自动追加 log
        append_log(records)
    else:
        print(f"用法: python generate_index.py [all]")
        sys.exit(1)


def append_log(records):
    """生成后自动追加 log.md 一条，记录本次刷新。"""
    total = len(records)
    today = date.today().isoformat()
    now = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
    log_path = WIKI_ROOT / "log.md"

    tagged = sum(1 for r in records if r["fm_status"] == "ok" and (r["tags"] or r["triggers"] or r["function"]))
    untagged = total - tagged
    with_deps = sum(1 for r in records if r["dependencies"])

    entry = (
        f"\n## [{today}] auto-sync | generate_index.py 全量刷新\n"
        f"- 生成时间：{now}\n"
        f"- 技能总数：{total}（已贴标签 {tagged}，未贴 {untagged}，声明依赖 {with_deps}）\n"
        f"- 重新生成：index.md / concepts/技能详情.md / views/触发词图谱.md / views/工具依赖图谱.md / views/技能依赖图谱.md / views/功能图谱.md\n"
        f"- 来源：脚本自动记录（generate_index.py all 模式）\n"
    )

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"  ✓ log.md 已自动追加")


if __name__ == "__main__":
    main()
