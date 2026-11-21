#!/usr/bin/env python3
"""Initialize .kb/ knowledge base, .kb/.gitignore, and runs/ directory idempotently."""
import os
import shutil
import sys
from pathlib import Path


def init_kb(project_root: str) -> None:
    root = Path(project_root).resolve()
    kb_dir = root / ".kb"
    templates_dir = Path(__file__).resolve().parent.parent / "assets" / "templates"

    kb_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("assets/diagrams", "assets/screenshots", "assets/icons", "runs"):
        (kb_dir / sub).mkdir(parents=True, exist_ok=True)

    gitignore = kb_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(".obsidian-sync.json\n", encoding="utf-8")

    created, skipped = [], []
    if templates_dir.exists():
        for tpl in sorted(templates_dir.glob("*.md")):
            dst = kb_dir / tpl.name
            if dst.exists():
                skipped.append(tpl.name)
            else:
                shutil.copy2(tpl, dst)
                created.append(tpl.name)

    print(f"[init_kb] root={kb_dir}")
    print(f"[init_kb] created={len(created)} {created}")
    print(f"[init_kb] skipped={len(skipped)}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    init_kb(target)
