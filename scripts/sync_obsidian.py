#!/usr/bin/env python3
"""把项目知识库（.kb/ 及 .kb/runs/ 轨迹文档）同步到 Obsidian 仓库。"""
import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote

MD_LINK = re.compile(r"(?<!!)\[([^\]\[]+)\]\((?!https?://|#)([^)/\s]+\.md)(#[^)]*)?\)")
FENCE = re.compile(r"(```.*?```|~~~.*?~~~)", re.S)
INLINE_CODE = re.compile(r"(`[^`\n]*`)")
PENDING = "> ⏳ 待补充："


def to_wikilink(match: re.Match, prefix: str, in_table: bool) -> str:
    label, target, anchor = match.group(1), unquote(match.group(2)), match.group(3) or ""
    stem = target[:-3]
    head = f"#{anchor.lstrip('#')}" if anchor else ""
    sep = "\\|" if in_table else "|"
    return f"[[{prefix}/{stem}{head}{sep}{label}]]"


def convert_body(text: str, prefix: str) -> str:
    parts = FENCE.split(text)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(part)
            continue
        lines = []
        for line in part.split("\n"):
            stripped = line.lstrip()
            if stripped.startswith(PENDING):
                content = stripped[len(PENDING):].strip()
                lines.append("> [!todo] 待补充")
                lines.append(f"> {content}")
                continue
            in_table = stripped.startswith("|")
            segs = INLINE_CODE.split(line)
            for j, seg in enumerate(segs):
                if j % 2 == 0:
                    segs[j] = MD_LINK.sub(lambda m: to_wikilink(m, prefix, in_table), seg)
            lines.append("".join(segs))
        out.append("\n".join(lines))
    return "".join(out)


def yaml_scalar(v) -> str:
    return json.dumps(str(v), ensure_ascii=False)


def add_frontmatter(text: str, props: dict) -> str:
    if text.startswith("---\n") and "\n---\n" in text[4:]:
        return text
    lines = ["---"]
    for k, v in props.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            lines.extend(f"  - {yaml_scalar(item)}" for item in v)
        else:
            lines.append(f"{k}: {yaml_scalar(v)}")
    lines.append("---\n")
    return "\n".join(lines) + "\n" + text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="项目根目录或 .kb 目录")
    ap.add_argument("vault", help="Obsidian 仓库路径")
    ap.add_argument("--name", help="项目名（默认取项目根目录名）")
    ap.add_argument("--dest", default="项目知识库", help='仓库内目标文件夹（默认 "项目知识库"）')
    ap.add_argument("--no-record", action="store_true", help="不写入 .kb/.obsidian-sync.json（避免污染干净工作树）")
    args = ap.parse_args()

    src = Path(args.source).expanduser().resolve()
    kb = src if src.name == ".kb" else src / ".kb"
    root = kb.parent
    if not kb.is_dir():
        print(f"错误：找不到知识库目录 {kb}（先运行 init_kb.py 初始化）")
        return 1

    vault = Path(args.vault).expanduser().resolve()
    if not (vault / ".obsidian").is_dir():
        print(f"错误：{vault} 不是 Obsidian 仓库（缺少 .obsidian 目录）")
        return 1

    name = args.name or root.name
    if any(s in name for s in ("/", "\\", "..")):
        print(f"错误：项目名不能包含路径分隔符或 '..'：{name}")
        return 1

    doc_stems = {d.stem for d in kb.glob("*.md") if d.name != "README.md"}
    if name in doc_stems:
        print(f"错误：项目名 {name!r} 与知识库文档 {name}.md 同名，索引笔记会被覆盖。请用 --name 换一个名字。")
        return 1

    target = (vault / args.dest / name).resolve()
    if not target.is_relative_to(vault):
        print(f"错误：目标路径逃逸出仓库范围：{target}")
        return 1
    target.mkdir(parents=True, exist_ok=True)

    link_prefix = f"{args.dest}/{name}"
    today = date.today().isoformat()

    synced = []
    for doc in sorted(kb.glob("*.md")):
        text = doc.read_text(encoding="utf-8-sig")
        text = convert_body(text, link_prefix)
        if doc.name == "README.md":
            out = target / f"{name}.md"
            text = add_frontmatter(text, {
                "title": name,
                "tags": ["项目知识库", f"项目知识库/{name}"],
                "synced": today,
            })
        else:
            out = target / doc.name
            text = add_frontmatter(text, {
                "tags": [f"项目知识库/{name}"],
                "synced": today,
            })
        out.write_text(text, encoding="utf-8")
        synced.append(out.name)

    runs_dir = kb / "runs"
    n_runs = 0
    if runs_dir.is_dir():
        for f in sorted(runs_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(runs_dir)
                dst = target / "runs" / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                if f.suffix == ".md":
                    txt = convert_body(f.read_text(encoding="utf-8-sig"), f"{link_prefix}/runs/{rel.parent.as_posix()}")
                    txt = add_frontmatter(txt, {"tags": [f"项目知识库/{name}", "mission-run"], "synced": today})
                    dst.write_text(txt, encoding="utf-8")
                else:
                    shutil.copy2(f, dst)
                n_runs += 1

    assets = kb / "assets"
    n_assets = 0
    if assets.is_dir():
        for f in assets.rglob("*"):
            if f.is_file() and f.name != ".gitkeep":
                rel = f.relative_to(assets)
                dst = target / "assets" / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                n_assets += 1

    if not args.no_record:
        record = {"vault": str(vault), "dest": args.dest, "name": name, "synced": today}
        (kb / ".obsidian-sync.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"已同步到: {target}")
    print(f"笔记 ({len(synced)}): {', '.join(synced)}")
    print(f"运行档案文件: {n_runs} 个")
    print(f"资源文件: {n_assets} 个")
    print(f"在 Obsidian 中打开 [[{link_prefix}/{name}]] 即可进入导航。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
