#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_dupes.py — 技能查重（super-skill-manager 模式2 定时维护 / 模式3 诊断）
扫描全库 SKILL.md 的 function 和 triggers 字段：
  1. function 相似：功能重复候选
  2. triggers 重叠：触发词冲突候选（会抢加载）
输出：候选对 + 相似度/重叠度
"""
import os
import re
from pathlib import Path

SKILLS_ROOT = Path(os.environ.get("SSM_SKILLS_ROOT", os.path.expanduser("~/AppData/Local/hermes/skills")))

def find_skill_dirs(root):
    for sk in root.rglob("SKILL.md"):
        yield sk.parent

def extract_field(skill_md, field):
    """提取 frontmatter 单行字段或列表字段"""
    content = skill_md.read_text(encoding="utf-8", errors="ignore")
    # 单行: function: xxx
    m = re.search(rf"^{field}:\s*(.+)$", content, re.MULTILINE)
    if m and not m.group(1).startswith("["):
        return m.group(1).strip()
    # 列表: field: [a, b]
    m2 = re.search(rf"^{field}:\s*\[([^\]]*)\]", content, re.MULTILINE)
    if m2:
        return [x.strip().strip("'\"") for x in m2.group(1).split(",") if x.strip()]
    # 多行列表: field:\n  - a\n  - b
    m3 = re.search(rf"^{field}:\s*$", content, re.MULTILINE)
    if m3:
        lines = content[m3.end():].split("\n")
        items = []
        for ln in lines[:15]:
            s = ln.strip()
            if s.startswith("- "):
                items.append(s[2:].strip())
            elif s and not s.startswith("#") and not s.startswith("---"):
                break
        return items if items else ""
    return ""

def norm(s):
    """归一化：去空格、标点、大小写"""
    if not s:
        return ""
    return re.sub(r"[\s，。、：:；;,.()（）\-_/\\'\"!?！？]", "", str(s)).lower()

def char_overlap(a, b):
    """字符级重叠率 0-1"""
    if not a or not b:
        return 0
    set_a, set_b = set(a), set(b)
    if not set_a or not set_b:
        return 0
    return len(set_a & set_b) / min(len(set_a), len(set_b))

def main():
    skills = []  # (name, function, triggers)
    for d in find_skill_dirs(SKILLS_ROOT):
        sm = d / "SKILL.md"
        fn = extract_field(sm, "function")
        tr = extract_field(sm, "triggers")
        if isinstance(tr, str):
            tr = [tr] if tr else []
        skills.append((d.name, fn, tr))

    print("=" * 60)
    print("技能查重报告（function 相似 + triggers 重叠）")
    print("=" * 60)

    # --- 功能相似 ---
    print("\n🔍 功能相似候选（function 字段字符重叠率 ≥ 0.5）：")
    found_fn = 0
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            n1, f1, _ = skills[i]
            n2, f2, _ = skills[j]
            if not f1 or not f2:
                continue
            ov = char_overlap(norm(f1), norm(f2))
            if ov >= 0.5:
                found_fn += 1
                print(f"  [{n1}] ↔ [{n2}]  重叠率 {ov:.0%}")
                print(f"      {f1}")
                print(f"      {f2}")
    if not found_fn:
        print("  （无）")

    # --- 触发词重叠 ---
    print("\n⚡ 触发词重叠候选（triggers 交集非空，会抢加载）：")
    found_tr = 0
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            n1, _, t1 = skills[i]
            n2, _, t2 = skills[j]
            if not t1 or not t2:
                continue
            inter = set(t1) & set(t2)
            if inter:
                found_tr += 1
                print(f"  [{n1}] ↔ [{n2}]  共用触发词: {', '.join(inter)}")
    if not found_tr:
        print("  （无）")

    print(f"\n📋 共扫描 {len(skills)} 个技能；功能相似 {found_fn} 对，触发词重叠 {found_tr} 对")

if __name__ == "__main__":
    main()
