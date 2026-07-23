"""validate_json.py — Validate a JSON file using json.load().

Usage: python scripts/validate_json.py <file_path>
Exit: 0 if valid JSON, 1 if invalid or file not found.
"""
import json
import sys
import os


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_json.py <file_path>", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.isfile(file_path):
        print(f"ERROR: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json.load(f)
        print("VALID")
        sys.exit(0)
    except json.JSONDecodeError as e:
        print(f"INVALID: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
