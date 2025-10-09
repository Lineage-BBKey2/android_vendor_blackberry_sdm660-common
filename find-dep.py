#!/usr/bin/env python3

import subprocess
import os
import sys

def get_deps(lib_path):
    """
    Run ldd on a shared library and return its dependencies as a dict.
    """
    try:
        output = subprocess.check_output(["ldd", lib_path], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(f"Error running ldd on {lib_path}: {e.output.decode()}")
        return {}

    deps = {}
    for line in output.decode().splitlines():
        line = line.strip()
        if "=>" in line:
            parts = line.split("=>")
            lib = parts[0].strip()
            path_part = parts[1].strip()
            if path_part == "not found":
                deps[lib] = None
            else:
                real_path = path_part.split()[0]
                deps[lib] = real_path
        else:
            parts = line.split()
            if len(parts) > 0:
                deps[parts[0]] = parts[-1] if len(parts) > 1 else None
    return deps


def resolve_deps(lib_path, resolved=None, seen=None):
    """
    Recursively resolve dependencies for a library.
    """
    if resolved is None:
        resolved = {}
    if seen is None:
        seen = set()

    if lib_path in seen:
        return resolved
    seen.add(lib_path)

    deps = get_deps(lib_path)
    resolved[lib_path] = deps

    for dep, dep_path in deps.items():
        print(str(dep))
        if dep_path and os.path.exists(dep_path):
            resolve_deps(dep_path, resolved, seen)

    return resolved


def all_deps_contain(resolved, target_lib_name):
    """
    Check if all dependencies (recursive) contain a link to target_lib_name.
    """
    for lib, deps in resolved.items():
        found = any(target_lib_name in (dep_path or "") or target_lib_name in dep
                    for dep, dep_path in deps.items())
        if not found:
            print(f"❌ {lib} does NOT depend on {target_lib_name}")
            return False
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <path-to-shared-library> <target-lib-name>")
        sys.exit(1)

    target_lib = sys.argv[1]
    check_for = sys.argv[2]

    if not os.path.exists(target_lib):
        print(f"Error: {target_lib} does not exist.")
        sys.exit(1)

    all_deps = resolve_deps(target_lib)

    print("\nChecking if ALL dependencies contain:", check_for)
    result = all_deps_contain(all_deps, check_for)

    if result:
        print(f"\n✅ All dependencies eventually reference {check_for}")
    else:
        print(f"\n❌ Some dependencies do NOT reference {check_for}")
