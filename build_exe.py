"""
Build the self-contained desktop .exe for Oncology Interactive Handbook.
Run: python build_exe.py
Output: dist/oncology_handbook/oncology_handbook.exe
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "oncology_handbook"


def main():
    print("Cleaning previous build...")
    for d in [DIST, ROOT / "build"]:
        try:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass
    import time; time.sleep(1)

    print("Running PyInstaller...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "oncology_handbook.spec",
         "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"),
         "--noconfirm", "--clean"],
        cwd=str(ROOT),
        capture_output=False,
    )

    if result.returncode != 0:
        print("\n[ERROR] PyInstaller build failed!")
        sys.exit(1)

    exe_path = DIST.parent / "oncology_handbook.exe"
    if not exe_path.exists():
        exe_path = DIST / "oncology_handbook.exe"
    exe_size_mb = exe_path.stat().st_size / (1024 * 1024) if exe_path.exists() else 0

    # Create .zip for GitHub release
    zip_path = ROOT / "oncology_handbook_desktop.zip"
    print(f"\nCreating {zip_path.name} ({exe_size_mb:.0f} MB exe)...")
    import zipfile
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_path, "oncology_handbook.exe")
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024) if zip_path.exists() else 0

    print(f"\n[OK] Build complete!")
    print(f"  .exe: {exe_path} ({exe_size_mb:.0f} MB)")
    print(f"  .zip: {zip_path} ({zip_size_mb:.0f} MB)")
    print(f"\nTo test: double-click {exe_path}")
    print(f"To release: upload {zip_path.name} to GitHub Releases")


if __name__ == "__main__":
    main()
