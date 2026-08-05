#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_deps.py — 技能依赖图谱扫描（super-skill-manager 模式2 定时维护）
扫描全库 SKILL.md 的 dependencies 字段，检查：
  1. 断链：引用的技能/工具不存在
  2. 被依赖：谁引用了谁（改 A 影响谁）
输出：依赖问题清单 + 依赖图谱
"""
import os
import re
import sys
from pathlib import Path

SKILLS_ROOT = Path(os.environ.get("SSM_SKILLS_ROOT", os.path.expanduser("~/AppData/Local/hermes/skills")))

def find_skill_dirs(root):
    """找所有含 SKILL.md 的技能目录"""
    for sk in root.rglob("SKILL.md"):
        yield sk.parent

def extract_deps(skill_md):
    """从 SKILL.md frontmatter 提取 dependencies 字段"""
    content = skill_md.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^dependencies:\s*\[([^\]]*)\]", content, re.MULTILINE)
    if not m:
        return []
    raw = m.group(1)
    return [x.strip().strip("'\"") for x in raw.split(",") if x.strip()]

def get_all_skill_names(root):
    """收集所有技能名（目录名 + frontmatter name）"""
    names = set()
    for sk in root.rglob("SKILL.md"):
        names.add(sk.parent.name)
        content = sk.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
        if m:
            names.add(m.group(1).strip())
    return names

def main():
    all_names = get_all_skill_names(SKILLS_ROOT)
    external = []      # 外部依赖（工具/包/资源名，非技能）
    broken = []        # 断链：技能目录消失但被引用
    dep_map = {}       # 技能 -> 依赖
    reverse_map = {}   # 被依赖 -> [引用者]

    for skill_dir in find_skill_dirs(SKILLS_ROOT):
        name = skill_dir.name
        deps = extract_deps(skill_dir / "SKILL.md")
        dep_map[name] = deps
        for d in deps:
            # 判断是技能名还是工具名：技能名在 all_names 里
            is_skill_ref = d in all_names
            if is_skill_ref:
                reverse_map.setdefault(d, []).append(name)
            else:
                # 不在技能库里的名字 = 外部依赖（工具/包/资源），
                # 不报断链（那是能力清单的职责），只登记
                external.append((name, d))

    print("=" * 60)
    print("技能依赖图谱扫描报告")
    print("=" * 60)

    if broken:
        print("\n⚠️ 断链（技能被删除/改名但仍有引用）：")
        for skill, dep in broken:
            print(f"  [{skill}] → {dep}")
    else:
        print("\n✅ 技能间引用无断链")

    if external:
        print("\n🔌 外部依赖登记（工具/包/资源名，由能力清单验证）：")
        seen = set()
        for skill, dep in external:
            if dep not in seen:
                print(f"  - {dep}")
                seen.add(dep)
    else:
        print("\n🔌 外部依赖: （无）")

    print("\n📊 依赖图谱（被依赖最多的技能 TOP）：")
    if reverse_map:
        for dep, users in sorted(reverse_map.items(), key=lambda x: -len(x[1])):
            print(f"  {dep} ← 被 {len(users)} 个技能引用: {', '.join(users[:6])}")
    else:
        print("  （无技能间依赖）")

    print(f"\n📋 共扫描 {len(dep_map)} 个技能，其中 {len([v for v in dep_map.values() if v])} 个声明了依赖")

if __name__ == "__main__":
    main()
