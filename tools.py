"""Step 3: the calculation tool.

Plain Python does the math so the agent never has to. Claude will later decide when to call this
and explain the result.

Run on its own to check it:  python tools.py data/sample_calls_4wk.csv
"""
import sys

import pandas as pd

REQUIRED_COLUMNS = ["interval_start", "queue", "calls_offered"]


def load_intervals(csv_path):
    """Read the 15-minute file and check it has the columns we expect."""
    df = pd.read_csv(csv_path, parse_dates=["interval_start"])
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"File is missing columns: {missing}. Expected: {REQUIRED_COLUMNS}")
    return df


def hourly_call_volume(csv_path, queue=None):
    """Roll 15-minute intervals up to hours and average them across days.

    Returns one row per hour of the day:
      hour            0-23
      total_calls     all calls in that hour across the whole file
      days_open       how many days had that hour open (Saturdays open fewer hours)
      avg_calls       average calls in that hour on a typical day (total_calls / days_open)

    queue: optional, limit to one queue. Default is all queues combined.
    """
    df = load_intervals(csv_path)
    if queue is not None:
        df = df[df["queue"] == queue]
        if df.empty:
            raise ValueError(f"No rows found for queue '{queue}'")

    df["date"] = df["interval_start"].dt.date
    df["hour"] = df["interval_start"].dt.hour

    # Step 1: calls per hour on each individual day
    per_day_hour = df.groupby(["date", "hour"], as_index=False)["calls_offered"].sum()

    # Step 2: combine the days. Divide by days that were open that hour, not by all days.
    out = per_day_hour.groupby("hour").agg(
        total_calls=("calls_offered", "sum"),
        days_open=("date", "nunique"),
    ).reset_index()
    out["avg_calls"] = (out["total_calls"] / out["days_open"]).round(1)
    return out


def top_hours(csv_path, n=3, queue=None):
    """The n busiest hours by average calls on a typical day."""
    table = hourly_call_volume(csv_path, queue)
    return table.sort_values("avg_calls", ascending=False).head(n).reset_index(drop=True)


def _hour_label(h):
    """0-23 to 12-hour label: 7 -> 7am, 14 -> 2pm."""
    return f"{h % 12 or 12}{'am' if h < 12 else 'pm'}"


def make_hourly_chart(csv_path, out_path=None, queue=None, label_top=3):
    """Step 6: draw average calls per hour on a typical day and save it as a PNG.

    One series, so no legend. The title names it, and only the busiest hours get number labels.
    Each chart gets the date and time in its file name, so nothing is overwritten (an old file
    that another program has open can never block a new chart).
    Returns the path of the saved image.
    """
    import os
    from datetime import datetime

    if out_path is None:
        out_path = os.path.join("output", f"hourly_call_volume_{datetime.now():%Y-%m-%d_%H%M%S}.png")

    import matplotlib

    matplotlib.use("Agg")  # draw to a file, no window needed
    import matplotlib.pyplot as plt

    table = hourly_call_volume(csv_path, queue)
    labels = [_hour_label(h) for h in table["hour"]]
    values = table["avg_calls"].tolist()
    top = set(table["avg_calls"].nlargest(label_top).index)

    surface, ink, ink_soft, grid, bar = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1", "#2a78d6"
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150, facecolor=surface)
    ax.set_facecolor(surface)
    bars = ax.bar(labels, values, width=0.6, color=bar, zorder=3)

    for i, b in enumerate(bars):
        if i in top:  # label only the busiest hours, not every bar
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + max(values) * 0.015,
                    f"{values[i]:.0f}", ha="center", va="bottom", fontsize=10, color=ink)

    scope = f"{queue} queue" if queue else "all queues"
    ax.set_title(f"Average calls per hour on a typical day ({scope})", loc="left",
                 fontsize=13, color=ink, pad=14)
    ax.set_ylabel("Average calls in the hour", fontsize=10, color=ink_soft)
    ax.set_xlabel("Hour of day", fontsize=10, color=ink_soft)
    ax.set_ylim(0, max(values) * 1.15)
    ax.yaxis.grid(True, color=grid, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(grid)
    ax.tick_params(colors=ink_soft, labelsize=9, length=0)
    fig.tight_layout()

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, facecolor=surface)
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_calls_4wk.csv"
    print("All hours:")
    print(hourly_call_volume(path).to_string(index=False))
    print("\nTop 3 hours:")
    print(top_hours(path, 3).to_string(index=False))
    print("\nChart saved to:", make_hourly_chart(path))
