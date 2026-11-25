#!/usr/bin/env python3
"""Compute the reproducible CEB fixture digest. Keep the inventory outside the fixture directory."""
import argparse, hashlib, json, pathlib, sys
p = argparse.ArgumentParser()
p.add_argument("directory", type=pathlib.Path)
p.add_argument("--inventory", type=pathlib.Path)
args = p.parse_args()
root = args.directory.resolve(strict=True)
if not root.is_dir():
    p.error("fixture must be a directory")
if args.inventory and args.inventory.resolve().is_relative_to(root):
    p.error("inventory must be outside the fixture directory")
rows = []
for f in root.rglob("*"):
    if f.is_symlink():
        p.error("symlinks are forbidden")
    if f.is_file():
        h = hashlib.sha256()
        with f.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
        rows.append({"path": f.relative_to(root).as_posix(), "sha256": h.hexdigest()})
    elif not f.is_dir():
        p.error("nonregular fixture entries are forbidden")
if not rows:
    p.error("fixture must contain at least one file")
rows.sort(key=lambda r: r["path"])
encoded = json.dumps(rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
if args.inventory:
    args.inventory.write_bytes(encoded)
print(hashlib.sha256(encoded).hexdigest())
