#!/usr/bin/env python3
"""CLI entry point for the StallionBot racing results notification engine."""

import argparse
import json
import sys
import time
import hashlib
from dataclasses import asdict

from models import RaceResult
from engine import NotificationEngine
from tba_parser import parse_tba_csv
from racing_api import RacingAPIClient


def load_filter(filter_path: str) -> dict:
    with open(filter_path) as f:
        return json.load(f)


def load_results(results_path: str) -> list[RaceResult]:
    with open(results_path) as f:
        raw = json.load(f)
    return [RaceResult(**item) for item in raw]


def file_hash(path: str) -> str:
    """MD5 hash of a file's contents for change detection."""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def run_batch(engine: NotificationEngine, results_path: str) -> None:
    results = load_results(results_path)
    alerts = engine.process_batch(results)
    for alert in alerts:
        print(alert)
        print()


def run_tba(engine: NotificationEngine, csv_path: str) -> None:
    results = parse_tba_csv(csv_path)
    alerts = engine.process_batch(results)
    for alert in alerts:
        print(alert)
        print()
    if not alerts:
        print("No matching winners found.")


def run_api(engine: NotificationEngine, client: RacingAPIClient, start_date: str, end_date: str) -> None:
    """Fetch today's results from the Racing API and fire alerts."""
    results = client.get_all_results(start_date=start_date, end_date=end_date)
    alerts = engine.process_batch(results)
    for alert in alerts:
        print(alert)
        print()
    if not alerts:
        print("No matching winners found.")


def run_api_watch(engine: NotificationEngine, client: RacingAPIClient, interval: int) -> None:
    """Poll the Racing API every `interval` seconds for today's results."""
    from datetime import date as dt
    print(f"Polling Racing API every {interval}s (Ctrl+C to stop)...")

    while True:
        today = dt.today().isoformat()
        try:
            results = client.get_all_results(start_date=today, end_date=today)
            alerts = engine.process_batch(results)
            for alert in alerts:
                print(alert)
                print()
        except Exception as e:
            print(f"[WARNING] API error: {e}", file=sys.stderr)
        time.sleep(interval)


def run_watch(engine: NotificationEngine, results_path: str) -> None:
    print(f"Watching {results_path} for changes (Ctrl+C to stop)...")
    last_file_hash = None

    while True:
        try:
            current_hash = file_hash(results_path)
        except FileNotFoundError:
            time.sleep(2)
            continue

        if current_hash != last_file_hash:
            last_file_hash = current_hash
            try:
                results = load_results(results_path)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"[WARNING] Failed to parse {results_path}: {e}", file=sys.stderr)
                time.sleep(2)
                continue

            alerts = engine.process_batch(results)
            for alert in alerts:
                print(alert)
                print()

        time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="StallionBot: Racing results notification engine"
    )
    parser.add_argument("--filter", metavar="FILTER_JSON", help="Path to filter config JSON file")
    parser.add_argument("--input", metavar="RESULTS_JSON", help="Batch mode: path to results JSON file")
    parser.add_argument("--tba", metavar="TBA_CSV", help="TBA export mode: path to TBA results CSV/TSV file")
    parser.add_argument("--watch", metavar="RESULTS_JSON", help="Watch mode: poll results JSON file every 2s")
    parser.add_argument("--api-user", metavar="USERNAME", help="Racing API username/key")
    parser.add_argument("--api-pass", metavar="PASSWORD", help="Racing API password")
    parser.add_argument("--api-date", metavar="YYYY-MM-DD", help="Fetch results for this date (default: today)")
    parser.add_argument("--api-watch", action="store_true", help="Poll Racing API continuously")
    parser.add_argument("--api-interval", metavar="SECONDS", type=int, default=60, help="Poll interval in seconds (default: 60)")

    args = parser.parse_args()

    if not args.filter:
        print("No filter provided. No alerts will be generated.", file=sys.stderr)
        sys.exit(0)

    filter_config = load_filter(args.filter)
    engine = NotificationEngine(filter_config=filter_config)

    if args.api_watch or args.api_date:
        if not args.api_user or not args.api_pass:
            print("Error: --api-user and --api-pass are required for API mode.", file=sys.stderr)
            sys.exit(1)
        client = RacingAPIClient(username=args.api_user, password=args.api_pass)
        if args.api_watch:
            try:
                run_api_watch(engine, client, interval=args.api_interval)
            except KeyboardInterrupt:
                print("\nStopped polling.")
        else:
            from datetime import date as dt
            query_date = args.api_date or dt.today().isoformat()
            run_api(engine, client, start_date=query_date, end_date=query_date)
    elif args.tba:
        run_tba(engine, args.tba)
    elif args.input:
        run_batch(engine, args.input)
    elif args.watch:
        try:
            run_watch(engine, args.watch)
        except KeyboardInterrupt:
            print("\nStopped watching.")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
