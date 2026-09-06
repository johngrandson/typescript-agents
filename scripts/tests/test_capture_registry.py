import hashlib
import json

import pytest

from scripts.capture_registry import capture


def test_captured_metadata_has_verifiable_hashes_and_no_safety_claim(tmp_path):
    calls = []

    def fetch(url):
        calls.append(url)
        return b'{"name":"@scope/example","version":"1.2.3"}'

    result = capture({"@scope/example": "1.2.3"}, tmp_path, fetch=fetch)
    assert calls == ["https://registry.npmjs.org/@scope%2Fexample/1.2.3"]
    assert result["kind"] == "captured"
    assert result["status"] == "complete"
    assert result["tarballs"] == {}
    relative = next(iter(result["files"]))
    assert result["files"][relative] == hashlib.sha256((tmp_path / relative).read_bytes()).hexdigest()
    assert "not a security approval" in result["attestation"]


def test_failed_capture_is_preserved_as_incomplete(tmp_path):
    with pytest.raises(ValueError, match="differs"):
        capture({"example": "1.2.3"}, tmp_path, fetch=lambda _: b'{"name":"other","version":"1.2.3"}')
    assert json.loads((tmp_path / "index.json").read_text())["status"] == "incomplete"
