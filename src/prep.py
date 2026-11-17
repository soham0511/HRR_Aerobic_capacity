"""Build the test-level analysis table from the breath-by-breath PhysioNet data.

Shared by Project 1 (HRR vs peak VO2) and Project 2 (age/BMI vs peak VO2).

Run from the project root:
    python src/prep.py

Outputs
    data/processed/test_level.csv        one row per ID_test with all derived measures
    outputs/audit/data_audit.txt         audit summary (dimensions, missingness, ranges)
    outputs/audit/phase_flags.csv        per-test event-detection flags for manual review

All operational definitions live in DEFINITIONS below and in docs/operational_definitions.md.
They were fixed after inspecting speed/HR traces and *before* looking at any
HRR-VO2 association.
"""
from __future__ import annotations

from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROCESSED = DATA / "processed"
AUDIT = ROOT / "outputs" / "audit"

DEFINITIONS = {
    # HR samples outside this range are treated as sensor artefacts (set to NaN).
    "hr_valid_range": (30, 230),
    # End-of-exercise HR: last valid HR within this many seconds before end exercise.
    "hr_end_lookback_s": 5,
    # Recovery HR: nearest valid HR to end+t within +/- this tolerance.
    "recovery_tolerance_s": 10,
    "recovery_targets_s": (60, 120, 180),
    # Alternate (sensitivity) definition: window means.
    # HR despiking: centred rolling median over this many samples, applied
    # separately within the exercise and recovery phases.
    "hr_median_filter_samples": 5,
    # HR_end artefact rule: if filtered HR_end is more than this many bpm below the
    # filtered exercise-phase HR peak, the end-exercise HR is treated as signal loss
    # and all HRR values for the test are set missing (logged).
    "hr_end_artefact_drop_bpm": 20,
    "alt_hr_end_window_s": 10,       # mean HR over the final 10 s of exercise
    "alt_recovery_half_window_s": 5, # mean HR over end+t +/- 5 s
    "alt_recovery_tolerance_s": 5,   # stricter nearest-observation tolerance
    # Peak VO2: max of a time-based rolling mean over the exercise phase.
    "peak_vo2_window_s": 15,
    "alt_peak_vo2_window_s": 30,
    # Recovery is "active" if median treadmill speed in the first 180 s of recovery >= this.
    "active_recovery_min_kmh": 3.0,
    # Ramp vs step protocol: median positive speed increment <= this is a ramp.
    "ramp_max_increment_kmh": 0.2,
}

SEX_LABELS = {0: "Male", 1: "Female"}  # verified: PhysioNet page defines Sex = 1 as female


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_source_data():
    subjects = pd.read_csv(DATA / "subject-info.csv")
    measures = pd.read_csv(DATA / "test_measure.csv")
    return subjects, measures


def clean_measures(measures: pd.DataFrame) -> pd.DataFrame:
    """Sort, and set physiologically impossible values to NaN (never to zero)."""
    m = measures.sort_values(["ID_test", "time"], kind="stable").reset_index(drop=True)
    lo, hi = DEFINITIONS["hr_valid_range"]
    m["HR"] = m["HR"].where(m["HR"].between(lo, hi))
    for col in ["VO2", "VCO2"]:
        m[col] = m[col].where(m[col] > 0)
    return m


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
def audit(subjects: pd.DataFrame, measures: pd.DataFrame) -> str:
    buf = StringIO()
    p = lambda *a: print(*a, file=buf)
    p("DATA AUDIT — PhysioNet treadmill-exercise-cardioresp v1.0.1")
    p("=" * 70)
    p(f"subject-info.csv : {subjects.shape[0]} rows x {subjects.shape[1]} cols")
    p(f"test_measure.csv : {measures.shape[0]} rows x {measures.shape[1]} cols")
    p(f"subject columns  : {subjects.columns.tolist()}")
    p(f"measure columns  : {measures.columns.tolist()}")
    p(f"unique participants (ID)      : {subjects['ID'].nunique()}")
    p(f"unique tests (ID_test) meta   : {subjects['ID_test'].nunique()}")
    p(f"unique tests in measurements  : {measures['ID_test'].nunique()}")
    p(f"duplicate ID_test in metadata : {subjects['ID_test'].duplicated().sum()}")
    p(f"tests in measures w/o metadata: {len(set(measures['ID_test']) - set(subjects['ID_test']))}")
    p(f"tests in metadata w/o measures: {len(set(subjects['ID_test']) - set(measures['ID_test']))}")
    tpp = subjects.groupby("ID").size()
    p(f"tests per participant: 1 test={int((tpp == 1).sum())}, 2+={int((tpp > 1).sum())}, max={tpp.max()}")
    p(f"sex coding counts (0=male, 1=female): {subjects['Sex'].value_counts().to_dict()}")
    p("\nMetadata ranges:")
    p(subjects.drop(columns=["ID", "ID_test"]).describe().T.round(2).to_string())
    p("\nMetadata missing (n):")
    p(subjects.isna().sum().to_string())
    p("\nBreath-level ranges (raw):")
    p(measures.drop(columns=["ID"]).describe().T.round(1).to_string())
    p("\nBreath-level missing (n rows):")
    p(measures.isna().sum().to_string())
    d = measures.sort_values(["ID_test", "time"], kind="stable").groupby("ID_test")["time"].diff()
    p(f"\nrepeated timestamps (same second within a test): {(d == 0).sum()} rows; "
      f"backward steps: {(d < 0).sum()}")
    p(f"HR <= 0 rows: {(measures['HR'] <= 0).sum()}; VO2 <= 0 rows: {(measures['VO2'] <= 0).sum()}")
    vo2_missing_tests = measures.groupby("ID_test")["VO2"].apply(lambda s: s.isna().all())
    p(f"tests with no VO2 data at all: {int(vo2_missing_tests.sum())} "
      "(PhysioNet page states 30; discrepancy noted)")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Per-test derivations
# ---------------------------------------------------------------------------
def _collapse_hr(g: pd.DataFrame) -> pd.Series:
    """HR indexed by time with duplicate timestamps averaged, NaNs dropped."""
    return g.groupby("time")["HR"].mean().dropna()


def _despike(hr: pd.Series) -> pd.Series:
    k = DEFINITIONS["hr_median_filter_samples"]
    return hr.rolling(k, center=True, min_periods=(k + 1) // 2).median()


def _nearest_hr(hr: pd.Series, target: float, tol: float) -> tuple[float, float]:
    """Nearest valid HR to target time within +/- tol. Returns (HR, time offset)."""
    if hr.empty:
        return np.nan, np.nan
    dist = (hr.index.to_numpy() - target)
    idx = np.argmin(np.abs(dist))
    if abs(dist[idx]) > tol:
        return np.nan, np.nan
    return float(hr.iloc[idx]), float(dist[idx])


def _window_mean(hr: pd.Series, lo: float, hi: float) -> float:
    w = hr[(hr.index >= lo) & (hr.index <= hi)]
    return float(w.mean()) if len(w) else np.nan


def _rolling_peak(ex: pd.DataFrame, window_s: int) -> tuple[float, float]:
    """Max of time-based rolling mean VO2 over the exercise phase; RER at that point."""
    v = ex[["time", "VO2", "VCO2"]].dropna()
    if v.empty:
        return np.nan, np.nan
    v = v.set_index(pd.to_timedelta(v["time"], unit="s"))
    roll = v[["VO2", "VCO2"]].rolling(f"{window_s}s").mean()
    # require the window to be (nearly) full so the first breaths do not dominate
    roll = roll[v["time"].to_numpy() >= v["time"].iloc[0] + window_s]
    if roll.empty:
        return np.nan, np.nan
    i = roll["VO2"].to_numpy().argmax()
    return float(roll["VO2"].iloc[i]), float(roll["VCO2"].iloc[i] / roll["VO2"].iloc[i])


def derive_test(g: pd.DataFrame) -> dict:
    D = DEFINITIONS
    sp = g["Speed"].to_numpy()
    tm = g["time"].to_numpy()
    i_end = np.flatnonzero(sp == sp.max())[-1]
    t_end = float(tm[i_end])
    ex = g[g["time"] <= t_end]
    rec = g[g["time"] > t_end]

    # protocol & recovery descriptors
    incs = np.diff(ex["Speed"].to_numpy())
    incs = incs[incs > 0]
    protocol = "ramp" if len(incs) and np.median(incs) <= D["ramp_max_increment_kmh"] else "step"
    rec180 = rec[rec["time"] <= t_end + 180]
    rec_speed = float(rec180["Speed"].median()) if len(rec180) else np.nan

    hr = _collapse_hr(g)
    hr_ex_raw = hr[hr.index <= t_end]
    hr_rec_raw = hr[hr.index > t_end]
    hr_ex = _despike(hr_ex_raw)
    hr_rec = _despike(hr_rec_raw)

    def last_in_lookback(series):
        w = series[series.index >= t_end - D["hr_end_lookback_s"]]
        return float(w.iloc[-1]) if len(w) else np.nan

    # primary HR_end: last despiked HR within lookback
    hr_end = last_in_lookback(hr_ex)
    hr_end_raw = last_in_lookback(hr_ex_raw)
    hr_end_alt = _window_mean(hr_ex_raw, t_end - D["alt_hr_end_window_s"], t_end)
    hr_peak_f = float(hr_ex.max()) if len(hr_ex) else np.nan
    hr_end_artefact = bool(hr_end < hr_peak_f - D["hr_end_artefact_drop_bpm"]) if not np.isnan(hr_end) else True

    out = dict(
        ID_test=g["ID_test"].iloc[0],
        t_end_s=t_end,
        peak_speed_kmh=float(sp.max()),
        protocol=protocol,
        recovery_duration_s=float(tm[-1] - t_end),
        recovery_speed_kmh=rec_speed,
        active_recovery=bool(rec_speed >= D["active_recovery_min_kmh"]) if not np.isnan(rec_speed) else False,
        HR_end=hr_end,
        HR_end_raw=hr_end_raw,
        HR_end_alt=hr_end_alt,
        HR_peak=hr_peak_f,
        HR_end_artefact=hr_end_artefact,
        n_breaths_ex=int(len(ex)),
        has_vo2=bool(g["VO2"].notna().any()),
    )
    for t in D["recovery_targets_s"]:
        hr_t, off = _nearest_hr(hr_rec, t_end + t, D["recovery_tolerance_s"])
        hr_t_strict, _ = _nearest_hr(hr_rec, t_end + t, D["alt_recovery_tolerance_s"])
        hr_t_raw, _ = _nearest_hr(hr_rec_raw, t_end + t, D["recovery_tolerance_s"])
        hr_t_win = _window_mean(hr_rec_raw, t_end + t - D["alt_recovery_half_window_s"],
                                t_end + t + D["alt_recovery_half_window_s"])
        keep = 0 if hr_end_artefact else 1
        out[f"HR_{t}"] = hr_t
        out[f"HR_{t}_offset_s"] = off
        # primary: despiked series, artefact rule applied
        out[f"HRR{t}"] = (hr_end - hr_t) if keep else np.nan
        # sensitivity: despiked, stricter +/-5 s tolerance
        out[f"HRR{t}_strict"] = (hr_end - hr_t_strict) if keep else np.nan
        # sensitivity: brief's literal rule on raw HR, no despiking, no artefact rule
        out[f"HRR{t}_raw"] = hr_end_raw - hr_t_raw
        # sensitivity: window means on raw HR (10 s end window, +/-5 s recovery window)
        out[f"HRR{t}_window"] = hr_end_alt - hr_t_win

    pk, rer = _rolling_peak(ex, D["peak_vo2_window_s"])
    pk_alt, _ = _rolling_peak(ex, D["alt_peak_vo2_window_s"])
    out["VO2peak_mL_min"] = pk
    out["VO2peak_mL_min_30s"] = pk_alt
    out["VO2peak_mL_min_breath"] = float(ex["VO2"].max()) if ex["VO2"].notna().any() else np.nan
    out["RER_at_peak"] = rer
    return out


def build_test_level(subjects: pd.DataFrame, measures: pd.DataFrame) -> pd.DataFrame:
    if subjects["ID_test"].duplicated().any():
        raise ValueError("duplicate ID_test in subject-info.csv")
    m = clean_measures(measures)
    rows = [derive_test(g) for _, g in m.groupby("ID_test", sort=False)]
    derived = pd.DataFrame(rows)

    t = subjects.merge(derived, on="ID_test", how="left", validate="one_to_one")
    t["sex"] = t["Sex"].map(SEX_LABELS)
    t["female"] = t["Sex"]
    t["height_m"] = t["Height"] / 100.0
    t["BMI"] = t["Weight"] / t["height_m"] ** 2
    t["adult"] = t["Age"] >= 18
    for suffix in ["", "_30s", "_breath"]:
        t[f"VO2peak_rel{suffix}"] = t[f"VO2peak_mL_min{suffix}"] / t["Weight"]
    t["VO2peak_L_min"] = t["VO2peak_mL_min"] / 1000.0
    t["HR_peak_pct_pred"] = 100 * t["HR_peak"] / (220 - t["Age"])
    # secondary maximality criteria (descriptive / sensitivity only)
    t["max_criterion_met"] = (t["RER_at_peak"] >= 1.10) | (t["HR_peak_pct_pred"] >= 90)

    # test order within participant: numeric suffix of ID_test
    t["test_seq"] = t["ID_test"].str.split("_").str[1].astype(int)
    t["first_test"] = t["test_seq"] == t.groupby("ID")["test_seq"].transform("min")
    t["n_tests_participant"] = t.groupby("ID")["ID_test"].transform("size")
    return t


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    subjects, measures = load_source_data()
    report = audit(subjects, measures)
    (AUDIT / "data_audit.txt").write_text(report, encoding="utf-8")
    print(report)

    t = build_test_level(subjects, measures)
    t.to_csv(PROCESSED / "test_level.csv", index=False)

    flags = t[["ID_test", "t_end_s", "peak_speed_kmh", "protocol", "recovery_duration_s",
               "recovery_speed_kmh", "active_recovery", "HR_end", "HRR60", "HRR120", "HRR180",
               "has_vo2", "RER_at_peak", "HR_peak_pct_pred"]].copy()
    flags["flag_short_recovery_lt170s"] = t["recovery_duration_s"] < 170
    flags["flag_passive_recovery"] = ~t["active_recovery"]
    flags["flag_HR_end_artefact"] = t["HR_end_artefact"]
    flags["flag_negative_HRR60"] = t["HRR60"] < 0
    flags["flag_negative_HRR60_raw"] = t["HRR60_raw"] < 0
    flags["flag_low_peak_speed_lt8"] = t["peak_speed_kmh"] < 8
    flags.to_csv(AUDIT / "phase_flags.csv", index=False)
    print(f"\nWrote {PROCESSED / 'test_level.csv'} ({len(t)} tests)")
    print(flags.filter(like="flag_").sum().to_string())


if __name__ == "__main__":
    main()
