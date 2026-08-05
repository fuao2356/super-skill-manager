# -*- coding: utf-8 -*-
"""扫描 Hermes 技能库中所有 SKILL.md，检查 frontmatter 身份字段是否齐全。

只读扫描，不修改任何技能文件。
只用 Python 标准库。
"""
import os
import re
import sys
from pathlib import Path

# 让 Windows 下 print 不乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SCAN_ROOT = Path(os.environ.get("SSM_SKILLS_ROOT", r"<SKILLS_ROOT>"))
REQUIRED_FIELDS = ["tags", "function", "dependencies", "triggers", "status"]


def parse_frontmatter(text: str):
    """解析 YAML frontmatter，返回 (dict, status_str)。

    status_str 取值：
      "ok"            : 正常解析到 frontmatter
      "empty"         : 文件无 frontmatter（不以 --- 开头）
      "broken"        : frontmatter 起始 --- 后找不到结尾 ---
      "empty-body"    : frontmatter 块为空内容
    """
    # 去掉 BOM 和开头空白
    if text.startswith("\ufeff"):
        text = text[1:]
    stripped = text.lstrip("\r\n")

    if not stripped.startswith("---"):
        return {}, "empty"

    # 去掉第一个 ---
    after_open = stripped[3:]
    # 找结尾的 ---
    m = re.search(r"^---\s*$", after_open, re.MULTILINE)
    if not m:
        return {}, "broken"

    body = after_open[: m.start()]
    if not body.strip():
        return {}, "empty-body"

    data = {}
    # 行级简单解析：key: value 或 key:
    for line in body.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        # 只认顶级 key（不缩进）
        km = re.match(r"^([A-Za-z_][A-Za-z0-9_\-\s]*?)\s*:\s*(.*)$", line)
        if not km:
            continue
        key = km.group(1).strip()
        val = km.group(2).strip()
        data[key] = val
    return data, "ok"


def skill_name_from_path(skill_path: Path) -> str:
    return skill_path.parent.name


def collect_skills(root: Path):
    """递归收集所有 SKILL.md 路径。"""
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn == "SKILL.md":
                results.append(Path(dirpath) / fn)
    return results


def main():
    if not SCAN_ROOT.exists():
        print(f"扫描根目录不存在: {SCAN_ROOT}")
        sys.exit(1)

    skill_files = collect_skills(SCAN_ROOT)
    print(f"扫描根目录: {SCAN_ROOT}")
    print(f"找到 SKILL.md 文件数: {len(skill_files)}")
    print("=" * 60)

    complete = []   # 字段齐全
    missing = []     # 缺字段
    no_fm = []       # 无 frontmatter
    broken = []      # frontmatter 损坏 / 空

    for f in skill_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            broken.append((f, f"读取失败: {e}"))
            continue

        fm, status = parse_frontmatter(text)
        name = fm.get("name") or skill_name_from_path(f)

        if status in ("empty", "broken", "empty-body"):
            label = {
                "empty": "无frontmatter",
                "broken": "frontmatter损坏",
                "empty-body": "frontmatter损坏",
            }[status]
            broken.append((f, label))
            continue

        absent = [fld for fld in REQUIRED_FIELDS if fld not in fm]
        if not absent:
            complete.append(name)
        else:
            missing.append((name, absent))

    # 输出：缺字段技能
    print("\n【缺字段技能】")
    if missing:
        for name, absent in missing:
            print(f"{name}: 缺 {absent}")
    else:
        print("(无)")
    print(f"共 {len(missing)} 个")

    # 输出：无 frontmatter / 损坏
    print("\n【无 frontmatter 或损坏】")
    if broken:
        for f, label in broken:
            print(f"{skill_name_from_path(f)} ({f}): {label}")
    else:
        print("(无)")
    print(f"共 {len(broken)} 个")

    # 输出：字段齐全
    print("\n【字段齐全技能】")
    for n in complete:
        print(n)
    print(f"共 {len(complete)} 个技能字段齐全")

    print("\n" + "=" * 60)
    print("总计：")
    print(f"  字段齐全: {len(complete)}")
    print(f"  缺字段  : {len(missing)}")
    print(f"  无/损坏 : {len(broken)}")


if __name__ == "__main__":
    main()