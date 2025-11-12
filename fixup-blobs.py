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


def list_needed(path: Path) -> list[str]:
    """Return DT_NEEDED entries of ELF using readelf."""
    output = run_cmd(["readelf", "-d", str(path)])
    needed = []
    for line in output.splitlines():
        if "Shared library:" in line:
            needed.append(line.split("[")[1].split("]")[0])
    return needed


def add_needed(path: Path, lib: str):
    """Add DT_NEEDED with patchelf if not already present."""
    if lib not in list_needed(path):
        run_cmd(["patchelf", "--add-needed", lib, str(path)])


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
    return new_path


def fixup_blob(path: Path, fix):
    """Apply blob fixups and check results."""
    ok = True
    if "add" in fix:
        for lib in fix["add"]:
            add_needed(path, lib)
            if lib not in list_needed(path):
                print(f"[WARN] {path}: failed to add_needed {lib}")
                ok = False
    if "replace" in fix:
        for old, new in fix["replace"].items():
            replace_needed(path, old, new)
            if new not in list_needed(path):
                print(f"[WARN] {path}: failed to replace {old} -> {new}")
                ok = False
    return ok


# ------------------------------------------------------------
# Fixup rules
# ------------------------------------------------------------

# Blob-specific DT_NEEDED fixups (full list from original script)
#vendor.qti.hardware.qteeconnector@1.0.so
#com.qualcomm.qti.dpm.api@1.0_vendor.so

#vendor.display.color@1.0.so
#vendor.qti.imsrtpservice@1.0_vendor.so
#vendor.qti.hardware.radio.ims@1.0.so
#com.quicinc.cne.api@1.0.so

#com.qualcomm.qti.imscmservice@2.0.so
#vendor.qti.hardware.fm@1.0_vendor.so

BLOB_FIXUPS = {
    "vendor/lib64/vendor.qti.hardware.tui_comm@1.0_vendor.so": {"add": ["libhidlbase-v32.so"]},
    "vendor/lib64/vendor.qti.hardware.qteeconnector@1.0.so": {"add": ["libhidlbase-v32.so"]},
    "vendor/lib64/com.qualcomm.qti.dpm.api@1.0_vendor.so": {"add": ["libhidlbase-v32.so"]},

    "vendor/lib64/vendor.display.color@1.0.so": {"add": ["libhidlbase-v32.so"]},
    "vendor/lib64/vendor.qti.imsrtpservice@1.0_vendor.so": {"add": ["libhidlbase-v32.so"]},
    "vendor/lib64/vendor.qti.hardware.radio.ims@1.0.so": {"add": ["libhidlbase-v32.so"]},
    "vendor/lib64/com.quicinc.cne.api@1.0.so": {"add": ["libhidlbase-v32.so"]},
    "vendor/lib64/com.qualcomm.qti.imscmservice@2.0.so": {"add": ["libhidlbase-v32.so"]},
    "vendor/lib64/vendor.qti.hardware.fm@1.0_vendor.so": {"add": ["libhidlbase-v32.so"]},
    "vendor/lib/hw/audio.primary.sdm660.so": {"add": ["libprocessgroup.so"]},
    "vendor/lib64/hw/audio.primary.sdm660.so": {"add": ["libprocessgroup.so"]},
}

# Library rename fixups (like original extract-utils)
def lib_fixup_vendor_suffix(lib: str, partition: str):
    """Apply _vendor suffix if partition is vendor."""
    return f"{lib}_{partition}" if partition == "vendor" else None



# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def apply_blob_fixups(folder: Path):
    for relpath, rules in BLOB_FIXUPS.items():
        matches = list(folder.rglob(os.path.basename(relpath)))
        if not matches:
            print(f"[INFO] {relpath} not found in {folder}")
            continue
        for match in matches:
            print(f"[INFO] Fixing {match}")
            success = fixup_blob(match, rules)
            print(f"[{'OK' if success else 'FAIL'}] {match}")



def main(folder: str):
    folder = Path(folder)
    if not folder.is_dir():
        print(f"Error: {folder} is not a directory")
        sys.exit(1)

    apply_blob_fixups(folder)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        main("./proprietary")
    else:
        main(sys.argv[1])
