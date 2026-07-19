"""
Master parallel runner: processes ALL sections × ALL sites via DeepSeek Flash.
6 concurrent threads. Idempotent — skips cached files (use --force to reprocess).

Usage:
    python -m app.data.rewriters.rewrite_all          # all sections, all sites
    python -m app.data.rewriters.rewrite_all --force  # reprocess everything
    python -m app.data.rewriters.rewrite_all --site breast --section staging
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.data.rewriters.base import (
    CONCURRENCY,
    INTERMEDIATE_DIR,
    call_llm,
    load_handbook,
    read_cache,
    section_value,
    write_cache,
)
from app.data.rewriters.prompts import PROMPTS


def process_one_task(label: str, prompt: str, value: str, max_tokens: int,
                     site_id: str, section: str) -> str:
    try:
        result = call_llm(prompt, value, label, max_tokens=max_tokens)
        if result:
            result["_section"] = section
            result["_site_id"] = site_id
            result["_chars_in"] = len(value)
            write_cache(site_id, section, result)
            return "ok"
        return "fail"
    except Exception as e:
        return f"err:{e}"


def main():
    force = "--force" in sys.argv
    site_filter = None
    section_filter = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg.startswith("--site="):
            site_filter = arg.split("=", 1)[1]
        elif arg == "--site" and i + 1 < len(sys.argv) - 1:
            site_filter = sys.argv[i + 2]
        elif arg.startswith("--section="):
            section_filter = arg.split("=", 1)[1]

    sections = {section_filter} if section_filter else set(PROMPTS)
    site_dirs = sorted([d for d in INTERMEDIATE_DIR.iterdir() if d.is_dir()],
                       key=lambda d: d.name.lower())
    if site_filter:
        site_dirs = [d for d in site_dirs if d.name == site_filter]

    # Build task list
    tasks = []
    for site_dir in site_dirs:
        site_id = site_dir.name
        hb, _ = load_handbook(site_id)
        if not hb:
            continue
        for section in sections:
            if not force and read_cache(site_id, section):
                continue
            value = section_value(hb, section)
            if value is None:
                continue
            if len(value) > 5000:
                value = value[:5000]
            config = PROMPTS[section]
            label = f"{site_id}/{section}"
            tasks.append((label, config["prompt"], value,
                         config["max_tokens"], site_id, section))

    if not tasks:
        print("No tasks to process (all cached). Use --force to reprocess.")
        return

    print(f"\nParallel Rewriter — {len(site_dirs)} sites × {len(sections)} sections")
    print(f"  {len(tasks)} API calls, {CONCURRENCY} concurrent threads")
    print(f"  Model: deepseek-v4-flash\n")

    t0 = time.monotonic()
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {pool.submit(process_one_task, *t): t[0] for t in tasks}
        for f in as_completed(futures):
            status = f.result()
            if status == "ok":
                ok += 1
            else:
                fail += 1
            print(f"  [{ok+fail}/{len(tasks)}] {futures[f]}: {status}")

    elapsed = time.monotonic() - t0
    print(f"\nDone in {elapsed:.0f}s. {ok} ok, {fail} fail ({len(tasks)} total)")

