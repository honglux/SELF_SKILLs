"""emit_result.py — Generate stdout JSON status envelope from alerts.json.

Usage: python scripts/emit_result.py <session_id> <output_dir>
"""
import json
import os
import sys
from datetime import datetime, timezone


def main():
    if len(sys.argv) != 3:
        envelope = {
            "session_id": "",
            "status": "error",
            "output_file": "",
            "alert_count": 0,
            "error": f"Usage: python {sys.argv[0]} <session_id> <output_dir>",
            "summary": {
                "total_scanned": 0, "high_risk": 0, "medium_risk": 0,
                "low_risk": 0, "false_positive_likely": 0
            }
        }
        print(json.dumps(envelope, ensure_ascii=False))
        return

    session_id = sys.argv[1]
    output_dir = sys.argv[2]
    alerts_path = os.path.join(output_dir, session_id, "alerts.json")

    if not os.path.isfile(alerts_path):
        envelope = {
            "session_id": session_id,
            "status": "error",
            "output_file": "",
            "alert_count": 0,
            "error": f"Result file not found: {alerts_path}",
            "summary": {
                "total_scanned": 0, "high_risk": 0, "medium_risk": 0,
                "low_risk": 0, "false_positive_likely": 0
            }
        }
        print(json.dumps(envelope, ensure_ascii=False))
        return

    try:
        with open(alerts_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        envelope = {
            "session_id": session_id,
            "status": "error",
            "output_file": os.path.abspath(alerts_path),
            "alert_count": 0,
            "error": f"Failed to parse result file as JSON: {e}",
            "summary": {
                "total_scanned": 0, "high_risk": 0, "medium_risk": 0,
                "low_risk": 0, "false_positive_likely": 0
            }
        }
        print(json.dumps(envelope, ensure_ascii=False))
        return

    alerts = data.get("alerts", [])
    high_risk = sum(1 for a in alerts if a.get("severity") == "high")
    medium_risk = sum(1 for a in alerts if a.get("severity") == "medium")
    low_risk = sum(1 for a in alerts if a.get("severity") == "low")
    false_positive = sum(1 for a in alerts if a.get("severity") == "info")

    envelope = {
        "session_id": session_id,
        "status": "completed",
        "output_file": os.path.abspath(alerts_path),
        "alert_count": len(alerts),
        "summary": {
            "total_scanned": 1,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "false_positive_likely": false_positive
        }
    }
    print(json.dumps(envelope, ensure_ascii=False))


if __name__ == "__main__":
    main()
