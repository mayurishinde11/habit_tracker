from datetime import date, timedelta
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


def build_features(dates_done: list, days_ahead: int = 7):
    """
    Train a LogisticRegression on historical check-in data and predict
    completion probability for the next `days_ahead` days.
    Returns (DataFrame[date, probability], None) or (None, error_message).
    """
    if len(dates_done) < 5:
        return None, "Not enough data (need at least 5 check-ins)"

    dates_done_set = set(dates_done)
    first_date = min(dates_done)
    today = date.today()

    # Build full date range from first check-in to today
    start = date.fromisoformat(first_date)
    all_dates = []
    cur = start
    while cur <= today:
        all_dates.append(cur)
        cur += timedelta(days=1)

    df = pd.DataFrame({"date": all_dates})
    df["date_str"] = df["date"].astype(str)
    df["completed"] = df["date_str"].apply(lambda d: 1 if d in dates_done_set else 0)

    # Feature engineering
    df["day_of_week"] = df["date"].apply(lambda d: d.weekday())
    df["day_of_month"] = df["date"].apply(lambda d: d.day)
    df["week_number"] = df["date"].apply(lambda d: d.isocalendar()[1])
    df["month"] = df["date"].apply(lambda d: d.month)
    df["day_index"] = range(len(df))
    df["rolling_rate"] = (
        df["completed"]
        .rolling(7, min_periods=1)
        .mean()
        .shift(1)
        .fillna(0)
    )

    feature_cols = ["day_of_week", "day_of_month", "week_number", "month", "day_index", "rolling_rate"]

    X = df[feature_cols].values
    y = df["completed"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LogisticRegression(max_iter=500)
    model.fit(X_scaled, y)

    # Build future rows
    future_rows = []
    last_rolling = df["rolling_rate"].iloc[-1]
    last_completed = df["completed"].iloc[-1]
    # Update rolling rate using the last known data point
    recent = df["completed"].tail(7).tolist()

    for i in range(1, days_ahead + 1):
        future_date = today + timedelta(days=i)
        recent_rate = sum(recent[-6:]) / 7 if len(recent) >= 7 else (sum(recent) / 7)
        future_rows.append({
            "date": future_date,
            "day_of_week": future_date.weekday(),
            "day_of_month": future_date.day,
            "week_number": future_date.isocalendar()[1],
            "month": future_date.month,
            "day_index": len(df) + i,
            "rolling_rate": recent_rate,
        })
        recent.append(0)  # conservative: assume not done for rolling calc

    future_df = pd.DataFrame(future_rows)
    X_future = future_df[feature_cols].values
    X_future_scaled = scaler.transform(X_future)

    probs = model.predict_proba(X_future_scaled)[:, 1] * 100
    result = pd.DataFrame({
        "date": [str(d) for d in future_df["date"]],
        "probability": [round(p, 1) for p in probs],
    })

    return result, None


def streak_stats(dates_done: list):
    """
    Returns (current_streak, longest_streak) as integers.
    """
    if not dates_done:
        return 0, 0

    sorted_dates = sorted(set(dates_done))
    date_objs = [date.fromisoformat(d) for d in sorted_dates]

    # Longest streak
    longest = 1
    current_run = 1
    for i in range(1, len(date_objs)):
        if (date_objs[i] - date_objs[i - 1]).days == 1:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 1

    # Current streak: count backwards from today
    today = date.today()
    current = 0
    check = today
    date_set = set(date_objs)
    while check in date_set:
        current += 1
        check -= timedelta(days=1)

    # Also count if yesterday was the last entry (streak still alive)
    if current == 0:
        yesterday = today - timedelta(days=1)
        check = yesterday
        while check in date_set:
            current += 1
            check -= timedelta(days=1)

    return current, longest


def weekly_completion(checkins: list):
    """
    Returns a DataFrame pivot of weeks × habit names, values = count of completions.
    """
    if not checkins:
        return pd.DataFrame()

    df = pd.DataFrame(checkins)
    df["date"] = pd.to_datetime(df["date"])
    df["week"] = df["date"].dt.to_period("W").astype(str)
    df["count"] = 1

    pivot = df.pivot_table(
        index="week",
        columns="name",
        values="count",
        aggfunc="sum",
        fill_value=0,
    )
    return pivot


def best_day_of_week(dates_done: list):
    """
    Returns dict {"Mon": n, "Tue": n, ..., "Sun": n}.
    """
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    counts = {d: 0 for d in day_labels}

    for ds in dates_done:
        try:
            d = date.fromisoformat(ds)
            label = day_labels[d.weekday()]
            counts[label] += 1
        except Exception:
            continue

    return counts