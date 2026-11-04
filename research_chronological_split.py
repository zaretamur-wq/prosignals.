"""Chronological research split helper. Never routes orders or tunes on test data."""
import argparse
import json
from pathlib import Path

def chronological_splits(rows, train_fraction=0.60, validation_fraction=0.20, embargo=0):
    """Return non-overlapping train/validation/test rows in original time order.

    Rows must already be sorted chronologically. An embargo removes rows between
    partitions to reduce boundary leakage for overlapping signal horizons.
    """
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1 or train_fraction + validation_fraction >= 1:
        raise ValueError("invalid split fractions")
    if not isinstance(embargo, int) or isinstance(embargo, bool) or embargo < 0:
        raise ValueError("embargo must be a nonnegative integer")
    n = len(rows)
    a = int(n * train_fraction)
    b = int(n * (train_fraction + validation_fraction))
    if a <= 0 or b - a <= embargo or n - b <= embargo:
        raise ValueError("not enough rows for split and embargo")
    return rows[:a], rows[a + embargo:b], rows[b + embargo:]

def split_csv(source, destination, embargo=0):
    import pandas as pd
    frame = pd.read_csv(source)
    if "time" not in frame:
        raise ValueError("CSV requires time column")
    times = pd.to_datetime(frame["time"], utc=True, errors="raise")
    if times.isna().any() or not times.is_monotonic_increasing or times.duplicated().any():
        raise ValueError("timestamps must be unique and strictly increasing")
    train, validation, test = chronological_splits(frame, embargo=embargo)
    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    for name, part in (("train", train), ("validation", validation), ("test", test)):
        part.to_csv(output / (name + ".csv"), index=False)
    report = {"source_rows":len(frame), "train_rows":len(train),
              "validation_rows":len(validation), "test_rows":len(test),
              "embargo_rows_each_boundary":embargo,
              "note":"Split only; no performance claim. Fit on train, select on validation, evaluate test once."}
    (output / "split_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--embargo", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(split_csv(args.source, args.destination, args.embargo), indent=2))
