import argparse
import json
import logging
import os
from typing import Any, Dict, List, Optional

from extractors.crypto_parser import CryptoScraper, build_records
from extractors.data_utils import (
 load_json_file,
 merge_cli_over_config,
 normalize_currency_list,
 sort_records,
)
from outputs.exporter import export_json

def configure_logging(verbosity: int) -> None:
 level = logging.WARNING
 if verbosity == 1:
 level = logging.INFO
 elif verbosity >= 2:
 level = logging.DEBUG
 logging.basicConfig(
 level=level,
 format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
 )

def parse_args() -> argparse.Namespace:
 parser = argparse.ArgumentParser(
 description="Crypto Market Rates Scraper (CoinGecko-powered)"
 )
 parser.add_argument(
 "--config",
 type=str,
 default=None,
 help="Path to settings JSON (see src/config/settings.example.json)",
 )
 parser.add_argument(
 "--currencies",
 type=str,
 default=None,
 help="Comma-separated currency codes, e.g. USD,BTC,ETH",
 )
 parser.add_argument("--page", type=int, default=None, help="Results page (1-based)")
 parser.add_argument(
 "--limit", type=int, default=None, help="Results per page (max 250 on API)"
 )
 parser.add_argument(
 "--sort_by",
 type=str,
 default=None,
 help="rank | gainer_loser_24h | trending_7d | volume_24h | price_desc | price_asc",
 )
 parser.add_argument(
 "--tag_slugs",
 type=str,
 default=None,
 help="Comma-separated categories (CoinGecko category ids), e.g. decentralized_finance_defi,gaming",
 )
 parser.add_argument(
 "--audited_only",
 action="store_true",
 help="(Not enforced on CoinGecko) flag preserved for compatibility",
 )
 parser.add_argument(
 "--output",
 type=str,
 default=None,
 help="Output JSON file path. If omitted, prints to stdout.",
 )
 parser.add_argument(
 "--timeout",
 type=float,
 default=None,
 help="HTTP timeout in seconds (default 25).",
 )
 parser.add_argument(
 "-v", "--verbose", action="count", default=0, help="Increase log verbosity"
 )
 return parser.parse_args()

def main() -> None:
 args = parse_args()
 configure_logging(args.verbose)
 log = logging.getLogger("main")

 # Load config file if provided
 cfg: Dict[str, Any] = {}
 if args.config:
 if not os.path.exists(args.config):
 raise FileNotFoundError(f"Config not found: {args.config}")
 cfg = load_json_file(args.config)

 # Merge CLI over config
 options = merge_cli_over_config(
 cfg,
 {
 "currencies": args.currencies,
 "page": args.page,
 "limit": args.limit,
 "sort_by": args.sort_by,
 "tag_slugs": args.tag_slugs,
 "audited_only": args.audited_only,
 "timeout": args.timeout,
 "output": args.output,
 },
 )

 currencies: List[str] = normalize_currency_list(options.get("currencies"))
 page: int = int(options.get("page", 1) or 1)
 limit: int = int(options.get("limit", 100) or 100)
 sort_by: Optional[str] = options.get("sort_by") or "rank"
 tag_slugs: List[str] = normalize_currency_list(options.get("tag_slugs"))
 audited_only: bool = bool(options.get("audited_only", False))
 timeout: float = float(options.get("timeout", 25) or 25)
 output_path: Optional[str] = options.get("output")

 if audited_only:
 log.info("audited_only flag provided (no direct CoinGecko filter; kept for parity).")

 scraper = CryptoScraper(timeout=timeout)
 try:
 # CoinGecko supports one vs_currency per request, so we merge results across currencies
 log.info(
 "Fetching coins: page=%s limit=%s currencies=%s categories=%s",
 page,
 limit,
 ",".join(currencies),
 ",".join(tag_slugs) if tag_slugs else "(none)",
 )
 raw_by_currency = scraper.fetch_multi_currency(
 currencies=currencies, page=page, per_page=limit, categories=tag_slugs
 )
 records = build_records(raw_by_currency)
 records = sort_records(records, sort_by=sort_by)
 except Exception as exc:
 log.exception("Failed to fetch/parse crypto data: %s", exc)
 raise

 # Export
 if output_path:
 export_json(records, output_path)
 print(output_path)
 else:
 print(json.dumps(records, indent=2))

if __name__ == "__main__":
 main()