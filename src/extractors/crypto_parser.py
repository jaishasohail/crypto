import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

from .data_utils import (
 stable_int_id,
 to_iso8601,
 make_quote_payload,
)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

log = logging.getLogger("crypto_parser")

class CryptoScraper:
 """
 Fetches market data from CoinGecko and adapts it to the repository's schema.

 Notes:
 - CoinGecko allows only a single 'vs_currency' per request. We aggregate multiple calls.
 - Category filtering uses CoinGecko 'category' query param (e.g., 'decentralized_finance_defi').
 """

 def __init__(self, timeout: float = 25.0, session: Optional[requests.Session] = None):
 self.timeout = float(timeout)
 self.session = session or requests.Session()
 self.session.headers.update(
 {
 "Accept": "application/json",
 "User-Agent": "CryptoMarketRatesScraper/1.0 (+https://bitbash.dev)",
 }
 )

 def _get(self, path: str, params: Dict[str, Any]) -> Any:
 """HTTP GET with basic retry/backoff for rate limits."""
 url = f"{COINGECKO_BASE}{path}"
 backoff = 1.5
 attempts = 0
 while True:
 attempts += 1
 try:
 resp = self.session.get(url, params=params, timeout=self.timeout)
 if resp.status_code == 429:
 # rate limited: backoff and retry a few times
 wait = min(10, backoff * attempts)
 log.warning("Rate limited (429). Backing off for %.1fs...", wait)
 time.sleep(wait)
 continue
 resp.raise_for_status()
 return resp.json()
 except requests.RequestException as e:
 if attempts List[Dict[str, Any]]:
 """Fetch a single page of market data for one currency."""
 params = {
 "vs_currency": vs_currency.lower(),
 "order": "market_cap_desc",
 "per_page": max(1, min(250, int(per_page))),
 "page": max(1, int(page)),
 "sparkline": "false",
 "price_change_percentage": "1h,24h,7d,30d,60d,90d",
 }
 # CoinGecko supports a single category id per request.
 results: List[Dict[str, Any]] = []
 if categories:
 for cat in categories:
 cat_params = dict(params)
 cat_params["category"] = cat
 data = self._get("/coins/markets", cat_params)
 for item in data:
 item["_cg_category"] = cat
 results.extend(data)
 else:
 results = self._get("/coins/markets", params)

 return results

 def fetch_multi_currency(
 self,
 currencies: List[str],
 page: int,
 per_page: int,
 categories: Optional[List[str]] = None,
 ) -> Dict[str, List[Dict[str, Any]]]:
 """
 Fetch markets for multiple currencies and return a dict keyed by vs_currency.
 """
 out: Dict[str, List[Dict[str, Any]]] = {}
 for cur in currencies:
 cur = cur.strip()
 if not cur:
 continue
 data = self.fetch_markets(cur, page=page, per_page=per_page, categories=categories)
 out[cur.upper()] = data
 return out

def _adapt_coin(cg_coin: Dict[str, Any]) -> Dict[str, Any]:
 """
 Map a CoinGecko markets coin object to the base fields (excluding 'quotes').
 """
 slug = cg_coin.get("id") or ""
 coin_id = stable_int_id(slug)
 record = {
 "id": coin_id,
 "name": cg_coin.get("name"),
 "symbol": (cg_coin.get("symbol") or "").upper(),
 "slug": slug,
 "cmcRank": cg_coin.get("market_cap_rank"),
 "marketPairCount": None, # not available on CoinGecko
 "circulatingSupply": cg_coin.get("circulating_supply"),
 "totalSupply": cg_coin.get("total_supply"),
 "maxSupply": cg_coin.get("max_supply"),
 "ath": cg_coin.get("ath"),
 "atl": cg_coin.get("atl"),
 "high24h": cg_coin.get("high_24h"),
 "low24h": cg_coin.get("low_24h"),
 "isActive": 1 if cg_coin.get("name") else 0,
 "lastUpdated": to_iso8601(cg_coin.get("last_updated")),
 "dateAdded": None, # not exposed by CoinGecko in this endpoint
 "quotes": [], # filled later
 }
 return record

def build_records(raw_by_currency: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
 """
 Merge coins across currencies and construct the final output schema.
 """
 # index by slug
 merged: Dict[str, Dict[str, Any]] = {}

 for currency, items in raw_by_currency.items():
 for cg in items:
 slug = cg.get("id")
 if not slug:
 # skip malformed
 continue

 if slug not in merged:
 merged[slug] = _adapt_coin(cg)

 quote = make_quote_payload(
 name=currency,
 price=cg.get("current_price"),
 volume24h=cg.get("total_volume"),
 market_cap=cg.get("market_cap"),
 pct_1h=cg.get("price_change_percentage_1h_in_currency"),
 pct_24h=cg.get("price_change_percentage_24h_in_currency"),
 pct_7d=cg.get("price_change_percentage_7d_in_currency"),
 pct_30d=cg.get("price_change_percentage_30d_in_currency"),
 pct_60d=cg.get("price_change_percentage_60d_in_currency"),
 pct_90d=cg.get("price_change_percentage_90d_in_currency"),
 )
 merged[slug]["quotes"].append(quote)

 # Convert to list
 records = list(merged.values())
 return records