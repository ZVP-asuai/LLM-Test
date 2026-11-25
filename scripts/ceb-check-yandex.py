"""Check the public mirror without credentials. Network failure must not block the site."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from datetime import datetime, timezone

p = Path("docs/ceb/v3")
d = json.loads((p / "engineering-delivery.json").read_text())
y = d.get("yandex_disk")
result = {"source": "yandex_disk", "status": "unconfigured",
          "url": y["url"] if y else None, "expected_sha256": d["expected_sha256"],
          "observed_sha256": None, "bytes": None, "checked_at": datetime.now(timezone.utc).isoformat()}
def get(url, params=None, limit=2_000_000):
    if params:
        url += "?" + urlencode(params)
    with urlopen(Request(url, headers={"User-Agent": "CEB-mirror-integrity-check/1"}), timeout=12) as response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Response exceeds allowed size")
        return data
def api(url, params):
    return json.loads(get(url, params, 500_000))
if y:
    try:
        params = {"public_key": y["url"]}
        resource = api(y["metadata_api"], {**params, "limit": 100})
        if resource.get("type") == "dir":
            items = resource.get("_embedded", {}).get("items", [])
            candidates = [i for i in items if i.get("name") == y["filename"] and i.get("type") == "file"]
            if len(candidates) != 1:
                raise ValueError("Expected exactly one engineering-inputs.zip in the shared folder root")
            resource = candidates[0]
            params["path"] = resource["path"]
        if resource.get("type") != "file" or resource.get("name") != y["filename"]:
            raise ValueError("Shared resource is not the expected ZIP filename")
        size = resource.get("size")
        if size != y["expected_bytes"]:
            result.update(status="size_mismatch", bytes=size)
        else:
            href = api(y["download_api"], params)["href"]
            if urlparse(href).scheme != "https":
                raise ValueError("Download URL must use HTTPS")
            data = get(href, limit=y["expected_bytes"])
            observed = hashlib.sha256(data).hexdigest()
            result.update(bytes=len(data), observed_sha256=observed,
                          status="verified" if observed == d["expected_sha256"] and len(data) == y["expected_bytes"] else "hash_mismatch")
    except Exception as e:
        result.update(status="unverified", error=type(e).__name__ + ": " + str(e)[:250])
(p / "engineering-yandex-status.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print("CEB mirror check:", json.dumps(result, ensure_ascii=False))
