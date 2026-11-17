"""Starter utilities for the two sports-science projects.

Download PhysioNet version 1.0.1 and place subject-info.csv and
 test_measure.csv in ../data/ before running.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_source_data():
    subjects = pd.read_csv(DATA / "subject-info.csv")
    measures = pd.read_csv(DATA / "test_measure.csv")
    return subjects, measures


def inspect_data(subjects, measures):
    print("subject-info:", subjects.shape)
    print("test_measure:", measures.shape)
    print("subject columns:", subjects.columns.tolist())
    print("measure columns:", measures.columns.tolist())
    for frame, name in [(subjects, "subjects"), (measures, "measures")]:
        print(f"\n{name} missingness (%):")
        print((frame.isna().mean() * 100).sort_values(ascending=False).head(20))
    print("unique participants:", subjects["ID"].nunique())
    print("unique tests in metadata:", subjects["ID_test"].nunique())
    print("unique tests in measurements:", measures["ID_test"].nunique())


def merge_metadata(subjects, measures):
    # Validate metadata uniqueness before the many-to-one merge.
    if subjects["ID_test"].duplicated().any():
        raise ValueError("subject-info.csv has duplicate ID_test values; inspect before merging")
    merged = measures.merge(
        subjects,
        on=["ID", "ID_test"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_meta"),
        indicator=True,
    )
    unmatched = merged["_merge"].ne("both").sum()
    print("measurement rows without matched metadata:", unmatched)
    return merged.drop(columns="_merge")


def derive_bmi(subjects):
    """Adapt column names below to the exact names in the downloaded CSV."""
    out = subjects.copy()
    # Common source labels are Weight and Height; verify units before use.
    if not {"Weight", "Height"}.issubset(out.columns):
        raise KeyError("Check source column names for weight and height, then update this function")
    out["height_m"] = out["Height"] / 100.0
    out["BMI"] = out["Weight"] / out["height_m"] ** 2
    return out


def create_test_level_peak_vo2(merged, metadata):
    """Preliminary peak VO2 only; exercise-phase filtering must be added.

    This deliberately does not label the maximum across the entire recording
    as VO2max. Define the maximal exercise phase from the treadmill protocol
    and trace before using the result in a scientific analysis.
    """
    if "VO2" not in merged.columns:
        raise KeyError("VO2 column not found")
    peak = (merged.groupby("ID_test", as_index=False)["VO2"]
            .max().rename(columns={"VO2": "peak_VO2_mL_min_unfiltered"}))
    out = metadata.merge(peak, on="ID_test", how="left", validate="one_to_one")
    return out


if __name__ == "__main__":
    s, m = load_source_data()
    inspect_data(s, m)
    merged = merge_metadata(s, m)
    print("Merged shape:", merged.shape)
    print("Next: inspect representative Speed/HR traces and implement a documented exercise/recovery phase rule.")
