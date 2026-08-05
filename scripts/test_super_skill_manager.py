#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_super_skill_manager.py — super-skill-manager 端到端测试

测试方法（用户要求：构造输入 → 验证输出 → 清理，不只验证命令不报错）：
1. 构造临时技能库（含正常/缺字段/断链/重复/冲突 5 种场景）
2. 跑 4 个脚本，验证输出符合预期
3. 清理临时目录

用法：python scripts/test_super_skill_manager.py
"""
import os
import sys
import re
import shutil
import tempfile
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
PASS = 0
FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")

def make_skill(root, name, function, deps="[]", triggers="[触发词A]", tags="[测试]", status="active", include_body="正文内容"):
    """创建测试技能"""
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    content = f"""---
name: {name}
description: 测试技能 {name}
tags: {tags}
function: {function}
dependencies: {deps}
triggers: {triggers}
status: {status}
---

# {name}

{include_body}
"""
    (d / "SKILL.md").write_text(content, encoding="utf-8")

def run_script(script, skills_root, wiki_root=None, timeout=60):
    """跑脚本，返回 (stdout, stderr, exit_code)"""
    env = os.environ.copy()
    env["SSM_SKILLS_ROOT"] = str(skills_root)
    if wiki_root:
        env["SSM_WIKI_ROOT"] = str(wiki_root)
    cmd = [sys.executable, str(SCRIPTS_DIR / script)]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout, encoding="utf-8")
    return p.stdout, p.stderr, p.returncode

def test_check_frontmatter(root):
    print("\n=== 测试 check_frontmatter.py（体检） ===")
    # 正常技能（5 字段齐全，不该报缺）
    make_skill(root, "good-skill", "功能正常", "[python]", "[查东西]", "[测试]", "active")
    # 缺字段技能（只有 name/description）
    d = root / "bad-skill"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text("---\nname: bad-skill\ndescription: 缺字段\n---\n# bad", encoding="utf-8")
    out, err, code = run_script("check_frontmatter.py", root)
    check("脚本正常退出", code == 0, f"exit={code}, err={err}")
    check("报出缺字段技能", "bad-skill" in out, out[-300:])
    check("缺字段技能标出 5 字段", "tags" in out and "status" in out, "")
    # good-skill 五字段齐全，不计入缺字段
    missing_section = out.split("缺字段技能")[-1].split("无 frontmatter")[0]
    check("正常技能不计入缺字段", "good-skill" not in missing_section, missing_section[:200])

def test_scan_deps(root):
    print("\n=== 测试 scan_deps.py（依赖断链） ===")
    # A 依赖 B（存在）→ 正常
    make_skill(root, "skill-a", "功能A", "[skill-b]", "[触发A]")
    # B 存在
    make_skill(root, "skill-b", "功能B", "[]", "[触发B]")
    # C 依赖不存在的技能 → 断链
    make_skill(root, "skill-c", "功能C", "[ghost-skill]", "[触发C]")
    # D 依赖外部工具（python）→ 不算断链（外部依赖）
    make_skill(root, "skill-d", "功能D", "[python, pandoc]", "[触发D]")
    out, err, code = run_script("scan_deps.py", root)
    check("脚本正常退出", code == 0, f"exit={code}, err={err}")
    check("报出断链 ghost-skill", "ghost-skill" in out, out[-300:])
    # python 是外部依赖（工具），登记在"外部依赖"段，不在"断链"段
    broken_section = out.split("断链")[-1].split("外部依赖")[0] if "断链" in out else out
    check("不把 python 当断链", "python" not in broken_section, broken_section[:200])

def test_scan_dupes(root):
    print("\n=== 测试 scan_dupes.py（功能重复 + 触发词冲突） ===")
    # 两个功能相似技能
    make_skill(root, "dup-a", "盘点 git 仓库并清理分支", "[git]", "[清理分支]")
    make_skill(root, "dup-b", "盘点全盘 git 仓库清理分支", "[git]", "[清理分支]")
    # 两个触发词冲突技能
    make_skill(root, "conf-a", "功能完全不同的A", "[]", "[技能体检]")
    make_skill(root, "conf-b", "功能完全不同的B", "[]", "[技能体检]")
    out, err, code = run_script("scan_dupes.py", root)
    check("脚本正常退出", code == 0, f"exit={code}, err={err}")
    check("报出功能相似对", "dup-a" in out and "dup-b" in out, out[-400:])
    check("报出触发词冲突", "技能体检" in out, "")

def test_generate_index(root, wiki_root):
    print("\n=== 测试 generate_index.py all（wiki 生成） ===")
    make_skill(root, "index-skill", "索引功能", "[python, other-skill]", "[查索引]", "[测试]", "active")
    make_skill(root, "other-skill", "其他功能", "[]", "[查其他]", "[测试]", "active")
    out, err, code = run_script("generate_index.py", root, wiki_root)
    check("脚本正常退出", code == 0, f"exit={code}, err={err}")
    # 验证 6 个文件生成
    for f in ["index.md", "concepts/技能详情.md", "views/触发词图谱.md",
              "views/工具依赖图谱.md", "views/技能依赖图谱.md", "views/功能图谱.md"]:
        check(f"生成 {f}", (wiki_root / f).exists(), str(wiki_root / f))
    # 验证 index.md 内容
    index_content = (wiki_root / "index.md").read_text(encoding="utf-8")
    check("index 含技能", "index-skill" in index_content, "")
    check("index 含 one-line summary 格式", "- `index-skill` —" in index_content, index_content[:200])
    # 验证技能详情含依赖分类
    catalog_content = (wiki_root / "concepts/技能详情.md").read_text(encoding="utf-8")
    check("技能详情含技能依赖", "[[other-skill]]" in catalog_content, catalog_content[:400])
    check("技能详情含能力依赖", "python" in catalog_content, "")
    # 验证 log 自动追加
    log_content = (wiki_root / "log.md").read_text(encoding="utf-8")
    check("log 自动追加", "auto-sync" in log_content, log_content[-200:])

def main():
    print("=" * 60)
    print("super-skill-manager 端到端测试")
    print("=" * 60)

    # 构造临时测试环境（用未来日期避免撞车）
    base = Path(tempfile.mkdtemp(prefix="ssm_test_"))
    skills_root = base / "skills"
    wiki_root = base / "wiki"
    skills_root.mkdir(parents=True, exist_ok=True)
    print(f"\n测试库: {skills_root}")
    print(f"测试wiki: {wiki_root}")

    try:
        test_check_frontmatter(skills_root)
        test_scan_deps(skills_root)
        test_scan_dupes(skills_root)
        test_generate_index(skills_root, wiki_root)
    finally:
        # 清理
        shutil.rmtree(base, ignore_errors=True)
        print(f"\n清理测试环境: {base}")

    print("\n" + "=" * 60)
    print(f"结果: {PASS} 通过, {FAIL} 失败")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)

if __name__ == "__main__":
    main()
