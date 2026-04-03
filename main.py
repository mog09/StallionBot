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
    parser.add_argument("--watch", metavar="RESULTS_JSON", help="Watch mode: poll results JSON file every 2s")

    args = parser.parse_args()

    if not args.filter:
        print("No filter provided. No alerts will be generated.", file=sys.stderr)
        sys.exit(0)

    filter_config = load_filter(args.filter)
    engine = NotificationEngine(filter_config=filter_config)

    if args.input:
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
