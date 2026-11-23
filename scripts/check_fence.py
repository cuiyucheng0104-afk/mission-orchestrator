#!/usr/bin/env python3
"""门 1 硬墙：自 --base 以来改动的每个文件必须落在 contract.yaml 的 fence 内、forbidden 外。

exit 0 = 全部合规；exit 1 = 有越界 / 契约没填完 / git 出错。
匹配规则：fnmatch 通配（`*` 可跨目录）；以目录写法结尾（`src/`）即匹配其下所有文件；
一项里用逗号可写多个模式（`"*.mp4, *.mov"`，所以不支持路径本身带逗号）。forbidden 优先于 fence。
看不到的：被 .gitignore 忽略的文件（git 不报告它们，也分不清是不是这次改的）。
"""
import argparse
import json
import re
import subprocess
import sys
from fnmatch import fnmatchcase
from pathlib import Path

ITEM = re.compile(r"""^-\s+(?:"((?:[^"\\]|\\.)*)"|'([^']*)'|([^#]*?))\s*(?:#.*)?$""")


def read_lists(contract: Path) -> dict:
    # shortcut: 只认 init_mission.py 生成的块状列表（`fence:` 换行后跟 `- "项"`），
    # 行内写法 `fence: [a, b]` 直接报错退出；不看缩进层级，同名键出现多次取并集。
    # 契约格式变复杂时换 PyYAML。
    out, key = {"fence": [], "forbidden": []}, None
    for line in contract.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = ITEM.match(s)
        if m and key:
            dq, sq, bare = m.groups()
            item = json.loads(f'"{dq}"') if dq is not None else (sq if sq is not None else bare)
            out[key].extend(p.strip() for p in item.split(",") if p.strip())
        elif not m:
            name, _, rest = s.split("#")[0].partition(":")
            key = name.strip() if name.strip() in out else None
            if key and rest.strip():
                # 行内写法若被当成空列表，forbidden 就整个失效 → 必须拒绝
                print(f"[check_fence] 不支持行内写法 `{s}`，请改成块状列表（每项一行 `- \"路径\"`）", file=sys.stderr)
                sys.exit(1)
    return out


def git(repo: Path, *args: str) -> list:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if p.returncode != 0:
        print(f"[check_fence] git {' '.join(args)} 失败: {p.stderr.decode('utf-8', 'replace').strip()}", file=sys.stderr)
        sys.exit(1)
    return [x for x in p.stdout.decode("utf-8", "surrogateescape").split("\0") if x]


def matches(path: str, pattern: str) -> bool:
    p = pattern.rstrip("/")
    # 以 / 结尾 = 只匹配该目录之下（`pkgs/*/` 不误伤同级文件 `pkgs/list.tsv`）
    return fnmatchcase(path, p + "/*") or (not pattern.endswith("/") and fnmatchcase(path, p))


def main() -> None:
    ap = argparse.ArgumentParser(description="Check changed files against contract.yaml fence/forbidden.")
    ap.add_argument("run_dir", help="Path to .kb/runs/<run-id>/")
    ap.add_argument("--base", required=True, help="基准分支/提交（与 HEAD 取 merge-base 后比较）")
    ap.add_argument("--repo", default=".", help="被检查的 git 工作树（默认当前目录）")
    args = ap.parse_args()

    contract = Path(args.run_dir) / "contract.yaml"
    if not contract.is_file():
        print(f"[check_fence] 找不到契约: {contract}", file=sys.stderr)
        sys.exit(1)
    lists = read_lists(contract)
    fence, forbidden = lists["fence"], lists["forbidden"]
    if not fence or any(f.startswith("⏳") for f in fence):
        print("FAILED   fence\nEXPECTED contract.yaml 的 constraints.fence 已填写真实路径\n"
              f"SAW      {fence or '空'}", file=sys.stderr)
        sys.exit(1)

    # 统一到仓库根：在子目录里 ls-files 只列该子目录，会漏掉别处的未跟踪文件
    repo = Path(git(Path(args.repo), "rev-parse", "--show-toplevel")[0].strip())
    base = git(repo, "merge-base", args.base, "HEAD")[0].strip()
    # --no-renames：把文件移出 forbidden 目录也算碰了它
    changed = set(git(repo, "diff", "--name-only", "--no-renames", "-z", base))
    changed |= set(git(repo, "ls-files", "--others", "--exclude-standard", "-z"))

    if not changed:
        print(f"FAILED   fence\nEXPECTED 相对 --base 至少有一个改动文件\nSAW      0 个改动（base={base[:7]}，--base 写错了？）", file=sys.stderr)
        sys.exit(1)

    bad = []
    for f in sorted(changed):
        hit = next((p for p in forbidden if matches(f, p)), None)
        if hit:
            bad.append(f"{f}  ← forbidden: {hit}")
        elif not any(matches(f, p) for p in fence):
            bad.append(f"{f}  ← 不在 fence 内")
    if bad:
        print("FAILED   fence\nEXPECTED 所有改动落在 fence 内且不碰 forbidden（要扩范围先改 contract.yaml）\n"
              "SAW      " + "\n         ".join(bad), file=sys.stderr)
        sys.exit(1)
    print(f"[check_fence] OK：{len(changed)} 个改动文件全部在 fence 内（base={base[:7]}）")


if __name__ == "__main__":
    main()
