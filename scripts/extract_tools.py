#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_tools.py — SKILL.md 工具引用提取（super-skill-manager 模式1 本地化）
读一个技能的 SKILL.md，提取它要求的工具/依赖：
  1. frontmatter dependencies 字段
  2. 正文代码块里的命令（python/pip/node/gh/curl 等开头）
  3. URL 里的域名（判断网络通道）
输出：工具引用清单，供对照本机能力清单
用法: python extract_tools.py <skill目录或SKILL.md路径>
"""
import re
import sys
from pathlib import Path

def extract_deps(content):
    m = re.search(r"^dependencies:\s*\[([^\]]*)\]", content, re.MULTILINE)
    if not m:
        return []
    return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]

def extract_commands(content):
    """提取代码块/行内代码里的命令"""
    cmds = set()
    # 行内代码 `xxx`
    for m in re.finditer(r"`([^`]+)`", content):
        tok = m.group(1).strip()
        first = tok.split()[0] if tok.split() else ""
        # 常见命令行工具
        if re.match(r"^(python|python3|pip|pip3|node|npm|npx|gh|git|curl|wget|"
                    r"opencode|claude|pandoc|ffmpeg|mysql|sqlite3|schtasks|"
                    r"everything|es\.exe|uv|docker|ollama|nssm|wmic|cmd|"
                    r"powershell|powershell\.exe|bash|sh|paddleocr|paddlex|"
                    r"playwright|modelscope|winget|mklink)$", first):
            cmds.add(first)
    return sorted(cmds)

def extract_urls(content):
    """提取 URL 域名"""
    domains = set()
    for m in re.finditer(r"https?://([^/\s\"'<>]+)", content):
        host = m.group(1)
        # 去 www. 和端口
        host = re.sub(r"^www\.", "", host)
        host = host.split(":")[0]
        domains.add(host)
    return sorted(domains)

def main():
    if len(sys.argv) < 2:
        print("用法: python extract_tools.py <skill目录或SKILL.md路径>")
        sys.exit(1)
    p = Path(sys.argv[1])
    if p.is_dir():
        p = p / "SKILL.md"
    if not p.exists():
        print(f"✗ 找不到文件: {p}")
        sys.exit(1)

    content = p.read_text(encoding="utf-8", errors="ignore")
    name = p.parent.name

    print(f"=== 技能 [{name}] 工具引用提取 ===")
    print(f"来源: {p}\n")

    deps = extract_deps(content)
    cmds = extract_commands(content)
    urls = extract_urls(content)

    if deps:
        print("📦 frontmatter dependencies:")
        for d in deps:
            print(f"  - {d}")
    else:
        print("📦 frontmatter dependencies: （无）")

    if cmds:
        print("\n🔧 正文命令引用:")
        for c in cmds:
            print(f"  - {c}")
    else:
        print("\n🔧 正文命令引用: （无）")

    if urls:
        print("\n🌐 URL 域名（网络通道检查用）:")
        for u in urls:
            print(f"  - {u}")
    else:
        print("\n🌐 URL 域名: （无）")

    print(f"\n--- 共 {len(deps)} 依赖 / {len(cmds)} 命令 / {len(urls)} 域名 ---")

if __name__ == "__main__":
    main()
