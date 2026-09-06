"""Explicitly capture public npm metadata; never attest to package safety."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REGISTRY = "https://registry.npmjs.org/"
MAX_BYTES = 32 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Registry capture refuses redirects")


def capture(packages: dict[str, str], output: Path, *, fetch=None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(NoRedirect)
    index = {"kind": "captured", "origin": REGISTRY, "files": {}, "metadata": {},
             "tarballs": {}, "capturedAt": datetime.now(timezone.utc).isoformat(),
             "status": "incomplete", "attestation": "metadata only; not a security approval"}
    index_path = output / "index.json"

    def save():
        staged = output / ".index.json.tmp"
        staged.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
        staged.replace(index_path)

    save()
    for name, version in sorted(packages.items()):
        if not re.fullmatch(r"(?:@[a-z0-9._-]+/)?[a-z0-9._-]+", name) or not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
            raise ValueError("Capture requires an npm package name and exact version")
        url = REGISTRY + urllib.parse.quote(name, safe="@") + "/" + urllib.parse.quote(version, safe="")
        if fetch is None:
            request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "typescript-starter-registry-capture/1"})
            with opener.open(request, timeout=30) as response:
                body = response.read(MAX_BYTES + 1)
        else:
            body = fetch(url)
        if len(body) > MAX_BYTES:
            raise ValueError("Registry metadata exceeds byte limit")
        data = json.loads(body)
        if data.get("name") != name or data.get("version") != version:
            raise ValueError("Registry metadata name/version differs from requested package")
        key = REGISTRY + "|" + name + "@" + version
        relative = hashlib.sha256(key.encode()).hexdigest() + ".json"
        (output / relative).write_bytes(body)
        index["files"][relative] = hashlib.sha256(body).hexdigest()
        index["metadata"][key] = relative
        save()
        if fetch is None:
            time.sleep(0.2)
    index["status"] = "complete"
    save()
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    index = capture(json.loads(args.packages_file.read_text()), args.output)
    print(f"Captured {len(index['metadata'])} exact-version metadata responses; no trust attestation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
