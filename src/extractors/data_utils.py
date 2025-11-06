import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from zlib import crc32

log = logging.getLogger("data_utils")

def load_json_file(path: str) -> Dict[str, Any]:
 with open(path, "r", encoding="utf-8") as f:
 return json.load(f)

def merge_cli_over_config(config: Dict[str, Any], cli: Dict[str, Any]) -> Dict[str, Any]:
 merged = dict(config or {})
 for k, v in cli.items():
 if v is not None:
 merged[k] = v
 return merged

def normalize_currency_list(value: Any) -> List[str]:
 """
 Accepts list, comma-separated string, or None. Returns uppercased list.
 """
 if value is None:
 return []
 if isinstance(value, list):
 out = [str(x).strip().upper() for x in value if str(x).strip()]
 return [x for x in out if x]
 if isinstance(value, str):
 parts = [p.strip().upper() for p in value.split(",")]
 return [p for p in parts if p]
 return []

def stable_int_id(text_id: str) -> int:
 """
 Create a deterministic 32-bit integer from a string id (e.g., CoinGecko slug).
 """
 if text_id is None:
 text_id = ""
 value = crc32(text_id.encode("utf-8")) & 0xFFFFFFFF
 return int(value)

def to_iso8601(dt_str: Optional[str]) -> Optional[str]:
 if not dt_str:
 return None
 try:
 # Try parsing common formats
 # CoinGecko example: "2025-06-08T15:30:00.000Z"
 return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(