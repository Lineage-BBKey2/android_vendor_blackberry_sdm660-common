#!/usr/bin/env python3
#
# SPDX-License-Identifier: Apache-2.0
#
# Standalone script to apply and verify fixups for sdm660-common blobs,
# including updating dependent libraries when a library is renamed.
#

import os
import subprocess
import sys
from pathlib import Path


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def run_cmd(cmd: list[str]) -> str:
    """Run a shell command and return stdout, raise on failure."""
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def is_elf(path: Path) -> bool:
    """Return True if file is ELF."""
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except Exception:
        return False


def list_needed(path: Path) -> list[str]:
    """Return DT_NEEDED entries of ELF using readelf."""
    output = run_cmd(["readelf", "-d", str(path)])
    needed = []
    for line in output.splitlines():
        if "Shared library:" in line:
            needed.append(line.split("[")[1].split("]")[0])
    return needed


def replace_needed(path: Path, old: str, new: str):
    """Replace DT_NEEDED entry with patchelf if present."""
    needed = list_needed(path)
    if old in needed and new not in needed:
        run_cmd(["patchelf", "--replace-needed", old, new, str(path)])


def rename_lib(path: Path, new_name: str) -> Path:
    """Rename library file and return the new Path."""
    new_path = path.with_name(new_name)
    if new_path.exists():
        print(f"[WARN] {new_path} already exists, skipping rename of {path}")
        return path
    path.rename(new_path)
    run_cmd(["patchelf", "--set-soname", f"{new_name}", str(new_path)])
    return new_path


# ------------------------------------------------------------
# Library rename fixups (like extract-utils)
# ------------------------------------------------------------

def lib_fixup_vendor_suffix(lib: str, partition: str):
    """Apply _vendor suffix if partition is vendor."""
    return f"{lib}_{partition}" if partition == "vendor" else None


LIB_FIXUPS = {
    (
        # Add libraries to rename if needed:
        # "vendor.qti.hardware.qteeconnector@1.0",
        # "vendor.qti.imsrtpservice@1.0",
        # "vendor.qti.hardware.tui_comm@1.0",
        # "vendor.qti.hardware.fm@1.0",
        # "libtrueportrait",
#AFTER PIE BLOBS
#        "com.qualcomm.qti.dpm.api@1.0",
#         "vendor.qti.imsrtpservice@1.0",
#          "vendor.qti.hardware.radio.am@1.0",
#           "android.hardware.radio.config@1.0",
#            "android.hardware.secure_element@1.0",
#             "android.hardware.radio.deprecated@1.0",
              "vendor.qti.imsrtpservice@1.0",
    ): lib_fixup_vendor_suffix,
}


# ------------------------------------------------------------
# Main logic
# ------------------------------------------------------------

def apply_lib_fixups(folder: Path, renamed_libs):
    """Apply library renames and update DT_NEEDED across all ELF files."""
    # Rename target libs
    for libs, func in LIB_FIXUPS.items():
        for lib in libs:
            for match in folder.rglob(f"{lib}.so"):
                # detect partition from path
                if "vendor" in str(match):
                    partition = "vendor"
                elif "system" in str(match):
                    partition = "system"
                else:
                    partition = "unknown"

                new_name = func(lib, partition)
                if new_name:
                    new_file = rename_lib(match, f"{new_name}.so")
                    print(f"[OK] Renamed {match.name} -> {new_file.name}")
                    renamed_libs[match.name] = new_file.name

def patch_needed(folder: Path, renamed_libs):
    # Update all ELF files (both .so and executables)
    for file_path in folder.rglob("*"):
        if not file_path.is_file():
            continue
        if not is_elf(file_path):
            continue

        try:
            needed = list_needed(file_path)
            for old, new in renamed_libs.items():
                if old in needed:
                    replace_needed(file_path, old, new)
                    print(f"[OK] Updated DT_NEEDED in {file_path} ({old} -> {new})")
        except subprocess.CalledProcessError:
            print(f"[WARN] Skipping unreadable ELF {file_path}")


def main(folders: list[str]):
    renamed_libs = {}
    for folder in folders:
        path = Path(folder)
        if not path.is_dir():
            print(f"[ERROR] {path} is not a directory, skipping.")
            continue
        print(f"\n=== Processing LIB->VENDOR {path} ===")
        apply_lib_fixups(path, renamed_libs)
    for folder in folders:
        path = Path(folder)
        if not path.is_dir():
            print(f"[ERROR] {path} is not a directory, skipping.")
            continue
        print(f"\n=== Processing DEPs for NEEDED {path} ===")
        patch_needed(path, renamed_libs)

# ------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default folders
        default_dirs = [
            "/data3/LOS22/vendor/blackberry/sdm660-common/proprietary/vendor/lib64",
            "/data3/LOS22/vendor/blackberry/sdm660-common/proprietary/vendor/bin",
            "/data3/LOS22/vendor/blackberry/sdm660-common/proprietary/vendor/bin/hw",
        ]
        main(default_dirs)
    else:
        main(sys.argv[1:])
