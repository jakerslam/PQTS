#!/usr/bin/env python3
"""Download historical OHLCV from Binance/Coinbase for research datasets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List
import sys

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if SRC.exists():
    src_str = str(SRC)
    if src_str not in sys.path:
        sys.path[:] = [src_str, *sys.path]
if str(ROOT) not in sys.path:
    sys.path[:] = [str(ROOT), *sys.path]

from research.historical_data import HistoricalDataDownloader


def _parse_date(value: str) -> datetime:
    # Accept YYYY-MM-DD and normalize to UTC midnight.
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return parsed.replace(tzinfo=timezone.utc)


def _split_csv(value: str) -> List[str]:
    return [token.strip() for token in value.split(",") if token.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venue", choices=["binance", "coinbase", "all"], default="all")
    parser.add_argument("--binance-symbols", default="BTCUSDT,ETHUSDT")
    parser.add_argument("--coinbase-symbols", default="BTC-USD,ETH-USD")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output-dir", default="data/historical")
    parser.add_argument("--format", choices=["csv", "parquet"], default="csv")
    parser.add_argument(
        "--cache-mode",
        choices=["use", "refresh"],
        default="use",
        help="use=load checksum-verified cached dataset when present; refresh=always redownload",
    )
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-backoff-seconds", type=float, default=0.75)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = _parse_date(args.start)
    end = _parse_date(args.end)

    if end <= start:
        raise ValueError("--end must be strictly after --start")

    downloader = HistoricalDataDownloader(
        output_dir=args.output_dir,
        max_retries=int(args.max_retries),
        retry_backoff_seconds=float(args.retry_backoff_seconds),
    )

    if args.venue in {"binance", "all"}:
        for symbol in _split_csv(args.binance_symbols):
            frame = None
            if args.cache_mode == "use":
                frame = downloader.load_cached_dataset(
                    venue="binance",
                    symbol=symbol,
                    interval=args.interval,
                    start=start,
                    end=end,
                    fmt=args.format,
                )
            cache_hit = frame is not None
            if frame is None:
                frame = downloader.download_binance_ohlcv(
                    symbol=symbol,
                    interval=args.interval,
                    start=start,
                    end=end,
                )
            quality = downloader.quality_summary(frame, interval=args.interval)
            saved = downloader.save_dataset(
                frame,
                venue="binance",
                symbol=symbol,
                interval=args.interval,
                start=start,
                end=end,
                fmt=args.format,
            )
            print(
                f"binance {symbol}: rows={quality.rows} completeness={quality.completeness:.4f} "
                f"missing={quality.missing_intervals} cache={'hit' if cache_hit else 'miss'} "
                f"saved={saved}"
            )

    if args.venue in {"coinbase", "all"}:
        for symbol in _split_csv(args.coinbase_symbols):
            frame = None
            if args.cache_mode == "use":
                frame = downloader.load_cached_dataset(
                    venue="coinbase",
                    symbol=symbol,
                    interval=args.interval,
                    start=start,
                    end=end,
                    fmt=args.format,
                )
            cache_hit = frame is not None
            if frame is None:
                frame = downloader.download_coinbase_ohlcv(
                    product_id=symbol,
                    interval=args.interval,
                    start=start,
                    end=end,
                )
            quality = downloader.quality_summary(frame, interval=args.interval)
            saved = downloader.save_dataset(
                frame,
                venue="coinbase",
                symbol=symbol,
                interval=args.interval,
                start=start,
                end=end,
                fmt=args.format,
            )
            print(
                f"coinbase {symbol}: rows={quality.rows} completeness={quality.completeness:.4f} "
                f"missing={quality.missing_intervals} cache={'hit' if cache_hit else 'miss'} "
                f"saved={saved}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
