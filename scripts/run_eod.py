"""Make the end-of-day summary now (instead of waiting for 23:59), "email" it, and post it.

    python -m scripts.run_eod              # today so far
    python -m scripts.run_eod 2026-10-25   # a specific day

The email is mocked: look in data/outbox/ for the .eml (double-click to open it in Mail).
"""

import sys
from datetime import date

from shared.db import init_db
from shared.summary import end_of_day

if __name__ == "__main__":
    init_db()
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    row = end_of_day(day)
    print(row["markdown"])
    print(f"\nSaved as summary #{row['id']}; email written to {row['delivered_to'] or '(see log)'}")
