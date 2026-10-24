#!/usr/bin/env python3
"""Reveal later parts of this exercise's spec.

Usage:
    python reveal.py <n>

Appends parts 2..n (whichever are not yet revealed) to SPEC.md in this folder and
copies any extra files that come with those parts (example tests, data files, mock
server scenarios) into this folder. Only reveal a part after you have finished, or
decided to stop, the previous one: in the interview, the next part arrives when you
are done with the current one.
"""
import os
import shutil
import sys
from pathlib import Path

PROBLEM_ID = "int_m2_bikemap"
ROOT = Path(__file__).resolve().parent


def parts_dir() -> Path:
    base = Path(os.environ.get("STRIPE_PREP_KEYS", "~/Desktop/Stripe/keys")).expanduser()
    return base / PROBLEM_ID / "parts"


def marker(k: int) -> str:
    return f"<!-- revealed part {k} -->"


def main(argv) -> int:
    if len(argv) != 2 or not argv[1].isdigit():
        print(__doc__.strip())
        return 2
    want = int(argv[1])
    src_dir = parts_dir()
    if not src_dir.is_dir():
        print(f"Cannot find the spec parts folder: {src_dir}")
        return 1
    available = sorted(
        int(p.stem[4:]) for p in src_dir.glob("part*.md") if p.stem[4:].isdigit()
    )
    last = max(available, default=1)
    if want > last:
        print(f"This exercise has {last} parts; revealing up to part {last}.")
        want = last
    spec = ROOT / "SPEC.md"
    text = spec.read_text(encoding="utf-8")
    revealed_any = False
    for k in range(2, want + 1):
        if marker(k) in text:
            continue
        body = (src_dir / f"part{k}.md").read_text(encoding="utf-8")
        text = text.rstrip("\n") + f"\n\n{marker(k)}\n\n" + body.strip("\n") + "\n"
        extra = src_dir / f"part{k}_files"
        if extra.is_dir():
            for f in sorted(extra.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    dest = ROOT / f.relative_to(extra)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)
                    print(f"  added/updated {dest.relative_to(ROOT)}")
        print(f"Revealed part {k} (appended to SPEC.md)")
        revealed_any = True
    spec.write_text(text, encoding="utf-8")
    if not revealed_any:
        print("Nothing new to reveal.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
