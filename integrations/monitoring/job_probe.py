#!/usr/bin/env python3
"""Check the last result and age of an existing backup or restore-drill report."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


def report(path):
    with path.open() as stream:
        return json.load(stream)


def evaluate(latest, success, expected, hours, now):
    errors = []
    if latest.get("result") != expected:
        errors.append("latest run failed")
    timestamp = datetime.fromisoformat(success["finished_at"])
    if timestamp.tzinfo is None or timestamp > now + timedelta(minutes=5):
        errors.append("last success has an invalid timestamp")
    elif success.get("result") != expected:
        errors.append("no successful run recorded")
    elif now - timestamp > timedelta(hours=hours):
        errors.append(f"last success older than {hours:g} hours")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("latest", type=Path)
    parser.add_argument("success", type=Path)
    parser.add_argument("expected", choices=["succeeded", "passed"])
    parser.add_argument("max_hours", type=int)
    args = parser.parse_args()
    if args.max_hours < 1:
        parser.error("max_hours must be positive")
    try:
        errors = evaluate(report(args.latest), report(args.success), args.expected,
                          args.max_hours, datetime.now(timezone.utc))
    except (OSError, KeyError, TypeError, ValueError, AttributeError):
        errors = ["missing or invalid job report"]
    if errors:
        for error in errors:
            print(f"DOWN {args.name} ({error})")
        return 1
    print(f"OK {args.name} (latest run passed and success is current)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
