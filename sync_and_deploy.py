#!/usr/bin/env python3
"""
Sync & Deploy Script — Oncology Interactive Handbook

Scans the source oncology pipeline project for updated data files,
copies them into this project's data/ directory, and pushes to GitHub
(triggering automatic Cloud Run deployment via Cloud Build).

Usage:
    python sync_and_deploy.py               # Sync data + push to GitHub
    python sync_and_deploy.py --data-only   # Only sync data, skip git push
    python sync_and_deploy.py --push-only   # Only git push, skip data sync
    python sync_and_deploy.py --dry-run     # Preview what would be synced
    python sync_and_deploy.py --source "D:\path\to\Oncology topics page"
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
MERGED_DIR = DATA_DIR / "merged"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
SITES_REGISTRY_FILE = DATA_DIR / "sites_registry.json"

DEFAULT_SOURCE = r"C:\Users\dpsri\OneDrive\Desktop\Educational webpage project\Oncology topics page"


def run_git(args: list[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd or SCRIPT_DIR),
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def git_has_changes() -> bool:
    code, out, _ = run_git(["status", "--porcelain"])
    return code == 0 and bool(out)


def git_is_repo() -> bool:
    code, _, _ = run_git(["rev-parse", "--git-dir"])
    return code == 0


def get_site_ids(source_path: Path) -> list[str]:
    registry_path = source_path / "sites_registry.json"
    if not registry_path.exists():
        print(f"[ERROR] sites_registry.json not found at {registry_path}")
        return []
    with open(registry_path, encoding="utf-8") as f:
        registry = json.load(f)
    return [s["id"] for s in registry.get("sites", []) if s.get("status") == "active"]


def sync_registry(source_path: Path, dry_run: bool = False) -> bool:
    src = source_path / "sites_registry.json"
    if not src.exists():
        print("[SKIP] Source sites_registry.json not found")
        return False
    if SITES_REGISTRY_FILE.exists():
        src_mtime = src.stat().st_mtime
        dst_mtime = SITES_REGISTRY_FILE.stat().st_mtime
        if src_mtime <= dst_mtime:
            return False
    msg = f"  sites_registry.json  ({datetime.fromtimestamp(src.stat().st_mtime):%Y-%m-%d %H:%M})"
    if dry_run:
        print(f"[DRY-RUN] Would copy: {msg}")
    else:
        shutil.copy2(src, SITES_REGISTRY_FILE)
        print(f"[COPY] {msg}")
    return True


def sync_merged_data(source_path: Path, site_ids: list[str], dry_run: bool = False) -> int:
    count = 0
    for site_id in site_ids:
        src = source_path / "deployment" / "Oncology" / site_id / "data" / f"{site_id}_data.json"
        dst = MERGED_DIR / f"{site_id}.json"
        if not src.exists():
            continue
        if dst.exists() and src.stat().st_mtime <= dst.stat().st_mtime:
            continue
        msg = f"  merged/{site_id}.json  ({datetime.fromtimestamp(src.stat().st_mtime):%Y-%m-%d %H:%M})"
        if dry_run:
            print(f"[DRY-RUN] Would copy: {msg}")
        else:
            shutil.copy2(src, dst)
            print(f"[COPY] {msg}")
        count += 1
    return count


def sync_intermediate_data(source_path: Path, site_ids: list[str], dry_run: bool = False) -> int:
    count = 0
    for site_id in site_ids:
        src_dir = source_path / "intermediate_json" / site_id
        dst_dir = INTERMEDIATE_DIR / site_id
        if not src_dir.exists():
            continue
        dst_dir.mkdir(parents=True, exist_ok=True)
        for src_file in src_dir.glob("*.json"):
            dst_file = dst_dir / src_file.name
            if dst_file.exists() and src_file.stat().st_mtime <= dst_file.stat().st_mtime:
                continue
            msg = f"  intermediate/{site_id}/{src_file.name}  ({datetime.fromtimestamp(src_file.stat().st_mtime):%Y-%m-%d %H:%M})"
            if dry_run:
                print(f"[DRY-RUN] Would copy: {msg}")
            else:
                shutil.copy2(src_file, dst_file)
                print(f"[COPY] {msg}")
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Sync oncology data files from source pipeline and push to GitHub"
    )
    parser.add_argument(
        "--source", type=str, default=DEFAULT_SOURCE,
        help=f"Path to the Oncology topics page source project (default: {DEFAULT_SOURCE})"
    )
    parser.add_argument("--data-only", action="store_true", help="Only sync data, skip git operations")
    parser.add_argument("--push-only", action="store_true", help="Only commit and push, skip data sync")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without copying or pushing")
    parser.add_argument("--skip-push", action="store_true", help="Sync and commit but do not push")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"[ERROR] Source path not found: {source_path}")
        sys.exit(1)

    if not git_is_repo() and not args.push_only:
        print("[ERROR] Not a git repository. Run from the interactive-oncology-app directory.")
        sys.exit(1)

    print(f"Source: {source_path}")
    print(f"Target: {SCRIPT_DIR}")
    print(f"Mode:   {'dry-run' if args.dry_run else 'live'}{' (data only)' if args.data_only else ''}{' (push only)' if args.push_only else ''}")
    print("-" * 50)

    total_copied = 0

    if not args.push_only:
        site_ids = get_site_ids(source_path)
        print(f"Found {len(site_ids)} active sites in source registry")

        registry_updated = sync_registry(source_path, args.dry_run)
        merged_count = sync_merged_data(source_path, site_ids, args.dry_run)
        inter_count = sync_intermediate_data(source_path, site_ids, args.dry_run)
        total_copied = (1 if registry_updated else 0) + merged_count + inter_count

        if args.dry_run:
            print(f"\n[DRY-RUN] Would copy {total_copied} file(s)")
            return

        print(f"\n[SYNC] Copied {total_copied} file(s)")

    if args.data_only:
        print("[DONE] Data sync complete (--data-only, no git operations).")
        return

    if args.dry_run:
        return

    if not git_has_changes() and not args.push_only:
        print("[GIT] No changes to commit — everything is up to date.")
        return

    if not args.push_only and total_copied == 0 and git_has_changes():
        pass

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_msg = f"sync: data update — {timestamp}"

    print("\n[GIT] Staging changes...")
    code, out, err = run_git(["add", "-A", "data/"])
    if code != 0:
        print(f"[ERROR] git add failed: {err}")

    code, _, err = run_git(["commit", "-m", commit_msg])
    if code != 0 and "nothing to commit" not in err:
        if args.push_only:
            print(f"[GIT] No changes to commit.")
            return
        print(f"[GIT] Commit: {err}")

    if args.skip_push:
        print("[GIT] Committed locally (--skip-push, not pushing to remote).")
        return

    print("[GIT] Pushing to origin/main...")
    code, out, err = run_git(["push", "origin", "main"])
    if code == 0:
        print(f"[GIT] Push successful — Cloud Build will auto-deploy to Cloud Run")
        if out:
            print(out)
    else:
        print(f"[ERROR] Push failed: {err}")
        print("Check your GitHub credentials. You may need to:")
        print("  1. Set up a Personal Access Token (PAT)")
        print("  2. Run: git remote set-url origin https://TOKEN@github.com/psdevraj-creator/oncology-reference.git")
        sys.exit(1)


if __name__ == "__main__":
    main()
