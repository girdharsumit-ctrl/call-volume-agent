"""Generate synthetic 15-minute call volume data (4 weeks, one queue).

Columns: interval_start, queue, calls_offered
Known pattern is planted on purpose so the agent's answer can be checked:
  - Morning peak around 10-11am
  - Lunch dip around 12-1pm
  - Smaller afternoon bump around 2-3pm
  - Mondays busier, Fridays lighter, Saturdays about half a weekday
Hours open: Mon-Fri 07:00-19:00, Sat 08:00-16:00, Sun closed.
"""
import csv
import math
import random
import sys
from datetime import datetime, timedelta

SEED = 42
START_MONDAY = datetime(2026, 10, 12)  # first Monday of the 4 weeks
WEEKS = 4
QUEUE = "General"

# Expected calls per 15 minutes by hour of day (weekday baseline)
HOUR_PROFILE = {
    7: 6, 8: 12, 9: 22, 10: 34, 11: 31, 12: 18,
    13: 17, 14: 26, 15: 24, 16: 16, 17: 11, 18: 7,
}
DAY_FACTOR = {0: 1.15, 1: 1.00, 2: 0.98, 3: 1.00, 4: 0.88, 5: 0.50}  # Mon..Sat


def poisson(lam, rng):
    """Poisson sample using Knuth for small lam, normal approx for large."""
    if lam > 30:
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def main(out_path):
    rng = random.Random(SEED)
    rows = []
    for d in range(WEEKS * 7):
        day = START_MONDAY + timedelta(days=d)
        wd = day.weekday()
        if wd == 6:
            continue  # closed Sunday
        open_h, close_h = (7, 19) if wd < 5 else (8, 16)
        t = day.replace(hour=open_h)
        end = day.replace(hour=close_h)
        while t < end:
            lam = HOUR_PROFILE[t.hour] * DAY_FACTOR[wd]
            rows.append((t.strftime("%Y-%m-%d %H:%M"), QUEUE, poisson(lam, rng)))
            t += timedelta(minutes=15)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["interval_start", "queue", "calls_offered"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sample_calls_4wk.csv")
