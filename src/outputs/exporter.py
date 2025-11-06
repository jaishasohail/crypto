import json
import os
import tempfile
from typing import Any, List

def export_json(data: Any, path: str) -> None:
 """
 Atomically write JSON to a file path with UTF-8 encoding.
 """
 os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
 fd, tmp_path = tempfile.mkstemp(prefix=".tmp_export_", suffix=".json", dir=os.path.dirname(path) or ".")
 try:
 with os.fdopen(fd, "w", encoding="utf-8") as f:
 json.dump(data, f, ensure_ascii=False, indent=2)
 os.replace(tmp_path, path)
 finally:
 # If an exception occurs after writing but before replace,
 # best-effort cleanup of the temp file.
 if os.path.exists(tmp_path):
 try:
 os.remove(tmp_path)
 except OSError:
 pass