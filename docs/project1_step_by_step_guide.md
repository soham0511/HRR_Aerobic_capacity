# Project 1: Step-by-Step Guide to Reproducing the Analysis Yourself

This guide walks through every step behind the Project 1 figures, tables and results. Each step tells you **what** to do, **why** it is done that way, **how** to do it in Excel and/or Python, and gives a **checkpoint** number so you can confirm you got it right.

**Which tool to use for what**

| Work | Excel | Python | Why |
|---|---|---|---|
| Explore one test, define events, compute HRR & peak VO2 by hand | ✅ (recommended) | ✅ | Doing one test by hand is the best way to understand the rules |
| Apply those rules to all 992 tests | ❌ | ✅ | 575,087 rows × 992 loops is impractical in Excel |
| Sample flow, Table 1, correlations | ✅ | ✅ | Simple formulas on a 992-row table |
| OLS regression (coefficients) | ✅ ToolPak / LINEST | ✅ | Identical point estimates |
| Cluster-robust SEs, mixed models, bootstrap, Cook's D | ❌ | ✅ | Not available in Excel |
| Simple charts (histogram, scatter, trace) | ✅ | ✅ | |
| Forest plot, flow diagram | ⚠️ painful | ✅ | |

**Suggested test-run route:** Part A (setup), then Part B (one test by hand in Excel), then Part C (scale up in Python), then Parts D–G (statistics in Excel, then the same in Python to compare), then Part H (charts).

> Excel formulas below assume **Excel 365 / Excel 2021+** (`FILTER`, `LET`, `UNIQUE`, `MAXIFS`, `TAKE`). Where an older-Excel alternative exists, it is noted.

---

## Part A: Setup

### A1. Python environment
```bash
cd "Sports Science Projects"
pip install -r requirements.txt
python -c "import pandas, statsmodels, scipy, matplotlib; print('ok')"
```

### A2. Excel Analysis ToolPak
File → Options → Add-ins → *Manage: Excel Add-ins* → Go → tick **Analysis ToolPak**. You'll then see **Data → Data Analysis**.

### A3. Folder conventions
- `data/`: raw CSVs. **Never edit or re-save these.** Always work on copies.
- Make a working folder, e.g. `practice/`, for your own Excel files and scripts.

---

## Part B: Understand the Data and Process ONE Test by Hand

### B1. Look at the two files

**Excel:** open `data/subject-info.csv` (992 rows, so fine to open directly). Columns: `Age, Weight, Height, Humidity, Temperature, Sex, ID, ID_test`.

Quick checks with formulas (put them in a spare column):

| Check | Formula | Expected |
|---|---|---|
| Number of tests | `=COUNTA(H2:H993)` | 992 |
| Unique participants | `=COUNTA(UNIQUE(G2:G993))` | 857 |
| Duplicate test IDs | `=COUNTA(H2:H993)-COUNTA(UNIQUE(H2:H993))` | 0 |
| Sex counts | `=COUNTIF(F2:F993,0)`, `=COUNTIF(F2:F993,1)` | 843, 149 |
| Mean height by sex | `=AVERAGEIFS(C2:C993,F2:F993,0)` / `…,1)` | 176.3 / 166.8 cm |

The height difference is how we sanity-check the PhysioNet coding **Sex = 1 → female**.

`test_measure.csv` has 575,087 rows. Excel *can* open it (limit is 1,048,576), but it is slow. Don't open it whole; extract one test instead (B2).

**Python equivalent:**
```python
import pandas as pd
s = pd.read_csv("data/subject-info.csv")
m = pd.read_csv("data/test_measure.csv")
print(s.shape, m.shape)                       # (992, 8) (575087, 9)
print(s.ID.nunique(), s.ID_test.nunique())    # 857 992
print(s.groupby("Sex")[["Height","Weight"]].mean())
print(m.isna().sum())                         # HR 981, VO2 4871, VCO2 4871 missing rows
print(set(m.ID_test) - set(s.ID_test))        # set() → every test has metadata
# tests with no VO2 at all
print(m.groupby("ID_test").VO2.apply(lambda x: x.isna().all()).sum())   # 11
```
Full audit: `src/prep.py` → function `audit()` → output in `outputs/audit/data_audit.txt`.

### B2. Extract one test to work on

We'll use **test `100_1`** (a ramp test with 592 rows, no duplicate timestamps and 3 missing HR values), then repeat on **`705_1`** (a step test) as a second exercise.

**Option 1, Python (fastest):**
```python
import pandas as pd
from pathlib import Path
Path("practice").mkdir(exist_ok=True)
m = pd.read_csv("data/test_measure.csv")
for tid in ["100_1", "705_1", "473_1"]:
    m[m.ID_test == tid].sort_values("time").to_csv(f"practice/test_{tid}.csv", index=False)
```

**Option 2, Excel Power Query:** Data → Get Data → From Text/CSV → `test_measure.csv` → **Transform Data** → filter `ID_test` = `100_1` → Close & Load.

Open `practice/test_100_1.csv` and save as `practice/test_100_1.xlsx`. Name the sheet **raw**. Columns: A `time`, B `Speed`, C `HR`, D `VO2`, E `VCO2`, F `RR`, G `VE`, H `ID_test`, I `ID`. Data occupies rows 2–593.

### B3. Plot the trace (always look before you define rules)

**Excel:** select `time` and `Speed`, then Insert → Scatter with straight lines. Make a **second, separate** chart for `time` and `HR`, placed directly underneath. Never put Speed and HR on one chart with two y-axes, because dual axes mislead.

What you should see:
- 5 km/h warm-up for ~170 s
- linear ramp to 16.3 km/h
- sudden drop to 5 km/h (walking recovery)
- HR climbing to ~168 and then falling fast after the drop

That sudden drop is the **end of exercise**.

**Python:** `outputs/project1/figures/fig1_event_detection_traces.png` is this plot. Code: `fig_trace()` in `src/project1_hrr_vo2.py`.

### B4. Define the end of exercise

**Rule:** end of exercise = the **last** sample at the test's **maximum treadmill speed**.

**Why not the last row?** The recording continues through ~3 min of walking recovery. **Why the *last* sample at max speed?** Some tests hold peak speed for a while; exercise ends when it stops.

In sheet **raw**, set up these cells:

| Cell | Label | Formula | Checkpoint (100_1) |
|---|---|---|---|
| L2 | peak speed | `=MAX(B2:B593)` | **16.3** |
| L3 | t_end | `=MAXIFS(A2:A593,B2:B593,L2)` | **846** |
| L4 | recovery duration | `=MAX(A2:A593)-L3` | 180 |

`MAXIFS` returns the latest time at which speed equals the maximum. Because time always increases, this is the last sample at peak speed.

Add a **phase** column. In J1 type `phase`, and in J2 (fill down):
```
=IF(A2<=$L$3,"exercise","recovery")
```

**Optional: protocol type (ramp vs step).** In K1 type `incr`, and in K3 (fill down):
```
=IF(AND(J3="exercise",B3>B2),B3-B2,"")
```
Then `=MEDIAN(K3:K593)`. If it is ≤ 0.2 the test is a **ramp** (0.1 km/h steps); otherwise it is a **step** protocol. Checkpoint: 100_1 → ramp; 705_1 → step (~1 km/h).

**Optional: recovery type.** `=MEDIAN(FILTER(B2:B593,(A2:A593>L3)*(A2:A593<=L3+180)))` gives 5.0. A value of 3 or more counts as active (walking) recovery.

### B5. Clean the heart-rate signal

**Why:** chest-strap HR has dropouts and spikes. A single bad value at end of exercise creates a fake HRR (see B8). We do three things:

1. Treat HR outside 30–230 bpm as missing (never as zero).
2. Remove rows with missing HR from the HR series.
3. Despike with a **centred 5-sample rolling median**, applied **separately within exercise and within recovery**, so the filter never mixes the two phases. At the edges of each phase, use whatever samples exist (at least 3).

**Excel (exact replication):**

1. Create a new sheet **hr**. Copy `time` (A), `HR` (C) and `phase` (J) from **raw** and *Paste Special → Values* into columns A, B, C of **hr**, starting at **row 4**. Leave rows 2–3 empty. Headers in row 1: `time`, `HR`, `phase`.
2. Filter column B for **(Blanks)**, delete those rows, and clear the filter. For 100_1 this removes 3 rows. Also delete any rows with HR < 30 or > 230 (none in 100_1).
3. Find the boundary where `phase` switches from exercise to recovery. **Insert 2 empty rows** there. Make sure there are also at least 2 empty rows after the last data row.
4. In D1 type `HR_despiked`. In D4 enter the following and fill down to the end:
   ```
   =IF(B4="","",MEDIAN(B2:B6))
   ```
   The 2 blank rows at the top, between phases and at the bottom make each window stop at the phase edge. `MEDIAN` ignores blanks, which reproduces the edge rule automatically.

**Python equivalent** (from `src/prep.py`, `derive_test()`):
```python
g = pd.read_csv("practice/test_100_1.csv")
t_end = g.loc[g.Speed == g.Speed.max(), "time"].max()          # 846
g["HR"] = g["HR"].where(g["HR"].between(30, 230))               # bad → NaN
hr = g.groupby("time")["HR"].mean().dropna()                    # average duplicate timestamps
despike = lambda s: s.rolling(5, center=True, min_periods=3).median()
hr_ex  = despike(hr[hr.index <= t_end])
hr_rec = despike(hr[hr.index >  t_end])
```
(Excel step 2 matches `.dropna()`. Duplicate timestamps don't occur in 100_1. For tests that have them, Python averages HR across rows sharing a second.)

### B6. HR at end of exercise and peak HR

**Rule:** HR_end = the **last despiked HR at or before t_end, no more than 5 s earlier**.

In sheet **hr** (put `t_end` = 846 in cell G1, or reference `raw!L3`):

| Cell | Label | Formula | Checkpoint (100_1) |
|---|---|---|---|
| G2 | HR_end | `=TAKE(FILTER(D4:D700,(A4:A700<=G1)*(A4:A700>=G1-5)*(D4:D700<>"")),-1)` | **168** |
| G3 | HR_peak (despiked, exercise) | `=MAXIFS(D4:D700,C4:C700,"exercise")` | **168** |
| G4 | artefact? | `=G2<G3-20` | **FALSE** |

*Older Excel alternative for G2:* `=LOOKUP(2,1/((A4:A700<=G1)*(A4:A700>=G1-5)*(D4:D700<>"")),D4:D700)` (enter with Ctrl+Shift+Enter in very old versions).

**The artefact rule:** if HR_end is more than 20 bpm below the test's own despiked peak HR, the HR signal almost certainly dropped out at the moment of exhaustion. That test's HRR values are then set to **missing**. Physiologically, HR at exhaustion should be at or near its peak.

**Second exercise: see why this rule exists.** Repeat B4–B6 on `practice/test_473_1.csv`:
- raw last HR before end = **88 bpm**
- despiked HR_end = **110**
- despiked peak = **172**
- 110 < 172 − 20, so **artefact = TRUE**

With the raw value, HRR60 would come out as **−69 bpm** (HR "rising" by 69 after stopping), which is physiologically absurd. Across the dataset, 85 tests trip this rule.

### B7. Recovery HR at +60, +120 and +180 s, and HRR

**Rule:** for each target T = t_end + 60 (then +120, +180), take the despiked recovery HR whose time is **closest to T**. Accept it only if it is **within ±10 s**; otherwise the value is missing. Never extrapolate.

In sheet **hr**, G6 (HR at +60):
```
=LET(tt,$G$1+60,
     ok,(C4:C700="recovery")*(D4:D700<>""),
     d, IF(ok, ABS(A4:A700-tt), 1E9),
     m, MIN(d),
     IF(m<=10, INDEX(D4:D700, MATCH(m,d,0)), "missing"))
```
Copy to G7 and G8, changing `+60` to `+120` and `+180`. (`MATCH` returns the first, i.e. earlier, sample on a tie, matching Python.)

Then compute HRR (only if G4 is FALSE):

| Cell | Formula | Checkpoint (100_1) |
|---|---|---|
| G6 HR_60 | (above) | **130** |
| G7 HR_120 | (above, +120) | **108** |
| G8 HR_180 | (above, +180) | **93** |
| H6 HRR60 | `=IF($G$4,"missing",$G$2-G6)` | **38** |
| H7 HRR120 | `=IF($G$4,"missing",$G$2-G7)` | **60** |
| H8 HRR180 | `=IF($G$4,"missing",$G$2-G8)` | **75** |

Step test 705_1 checkpoints: t_end 1129, HR_end 193, HRR60 **27**, HRR120 **47**, HRR180 **58**.

**Python:**
```python
def nearest(series, target, tol=10):
    if series.dropna().empty: return float("nan")
    s = series.dropna()
    d = (s.index - target)
    i = abs(d).argmin()
    return s.iloc[i] if abs(d[i]) <= tol else float("nan")

hr_end = hr_ex[hr_ex.index >= t_end - 5].dropna().iloc[-1]       # 168
artefact = hr_end < hr_ex.max() - 20                              # False
hrr = {t: (hr_end - nearest(hr_rec, t_end + t)) if not artefact else None for t in (60,120,180)}
```

### B8. Peak VO2 (15-s rolling mean)

**Why not the single highest breath?** Breath-by-breath VO2 is noisy, and a single big breath inflates the "peak". A 15-s time-based average is a common, defensible choice (Robergs et al., 2010). We keep the single-breath and 30-s values for sensitivity analysis.

**Rule:** for each exercise-phase breath at time *t*, average all VO2 values with time in **(t − 15, t]**. This window includes *t* and excludes exactly *t* − 15. Only use breaths at least 15 s after the first breath, so the very first breaths don't form a short, unrepresentative window. Peak VO2 = the maximum of these averages. Missing VO2 values are skipped (never treated as 0).

In sheet **raw**:

| Col / Cell | Formula (row 2, fill down) | Notes |
|---|---|---|
| M1 header `VO2_roll15` | `=IF(AND(J2="exercise",A2>=$A$2+15), AVERAGEIFS($D$2:$D$593,$A$2:$A$593,">"&A2-15,$A$2:$A$593,"<="&A2), "")` | blank VO2 cells are ignored by AVERAGEIFS |
| N1 header `VCO2_roll15` | same, with `$E$2:$E$593` | for RER |

Summary cells:

| Cell | Label | Formula | Checkpoint (100_1) |
|---|---|---|---|
| L6 | VO2peak (mL/min, 15 s) | `=MAX(M2:M593)` | **3193.7** |
| L7 | VO2peak (single breath) | `=MAXIFS(D2:D593,J2:J593,"exercise")` | **3272** |
| L8 | RER at peak | `=INDEX(N2:N593,MATCH(L6,M2:M593,0))/L6` | **1.21** |
| L9 | body mass (kg) | from subject-info: 76.0 | |
| L10 | VO2peak relative (mL·kg⁻¹·min⁻¹) | `=L6/L9` | **42.02** |

For the 30-s version (sensitivity), change 15 to 30 in both places. Checkpoint: 3151.0 mL/min.

**Python:**
```python
ex = g[g.time <= t_end].dropna(subset=["VO2"]).copy()
ex.index = pd.to_timedelta(ex.time, unit="s")
roll = ex[["VO2", "VCO2"]].rolling("15s").mean()        # window (t-15, t]
roll = roll[ex.time.values >= ex.time.iloc[0] + 15]
peak = roll.VO2.max()                                    # 3193.69
```

### B9. Body-size variables

From `subject-info.csv` for ID_test 100_1: Weight 76.0 kg, Height 167 cm.
- `height_m = Height/100` → 1.67
- `BMI = Weight/height_m^2` → **27.25**

---

## Part C: Scale Up to All 992 Tests (Python)

Part B was done for one test. Now apply the same rules to every test with a loop. This is exactly what `src/prep.py` does:

```bash
python src/prep.py
```

Read the code in this order:
1. `DEFINITIONS`: every rule parameter in one place (5 s lookback, ±10 s tolerance, 20 bpm artefact, 15-s window…).
2. `clean_measures()`: sort; invalid HR/VO2 → NaN.
3. `derive_test(g)`: everything you did in B4–B8, for one test `g`.
4. `build_test_level()`: loops `derive_test` over `groupby("ID_test")`, merges metadata on `ID_test`, and adds `BMI`, `VO2peak_rel`, `adult` (Age ≥ 18), `female`, `first_test`, `max_criterion_met`.

Writing your own minimal version is a great exercise:
```python
rows = []
for tid, g in m.sort_values(["ID_test","time"]).groupby("ID_test"):
    rows.append(my_derive_test(g))           # your function from Part B
derived = pd.DataFrame(rows)
table = s.merge(derived, on="ID_test", how="left", validate="one_to_one")
```

**Checkpoint:** open `data/processed/test_level.csv`, filter to `ID_test = 100_1`, and compare with your Excel sheet:

| Column | Value |
|---|---|
| t_end_s | 846 |
| HR_end | 168 |
| HRR60 / HRR120 / HRR180 | 38 / 60 / 75 |
| VO2peak_mL_min | 3193.69 |
| VO2peak_rel | 42.02 |
| RER_at_peak | 1.214 |
| BMI | 27.25 |

If your Excel numbers match, you have independently verified the pipeline.

**Extra columns used later** (all in `test_level.csv`):
- `HRR60_strict`: ±5 s tolerance instead of ±10 s
- `HRR60_raw`: brief's literal rule on raw HR (no despike, no artefact rule)
- `HRR60_window`: mean raw HR over the last 10 s of exercise, minus mean HR over target ±5 s
- `VO2peak_rel_breath`, `VO2peak_rel_30s`: alternate peak definitions
- `protocol`, `active_recovery`, `HR_peak_pct_pred = 100·HR_peak/(220−Age)`
- `max_criterion_met = RER_at_peak ≥ 1.10 OR HR_peak_pct_pred ≥ 90`
- `first_test`: the participant's lowest ID_test suffix (e.g. 351_1 before 351_61)

---

## Part D: Sample Flow and Exclusions

Open `data/processed/test_level.csv` in Excel and save as `practice/project1_analysis.xlsx`, sheet **tests**. Convert to a Table (Ctrl+T) named **T** so you can write `T[HRR60]` etc. TRUE/FALSE columns import as Excel booleans, and NaN imports as blank.

Add a column `include` (primary analysis sample):
```
=AND([@VO2peak_rel]<>"", [@HR_end_artefact]=FALSE, [@HRR60]<>"")
```

Sequential exclusion counts:

| Step | Tests formula | Participants formula | Checkpoint |
|---|---|---|---|
| All | `=ROWS(T[ID_test])` | `=COUNTA(UNIQUE(T[ID]))` | 992 / 857 |
| − no VO2 | `=COUNTIFS(T[VO2peak_rel],"<>")` | `=COUNTA(UNIQUE(FILTER(T[ID],T[VO2peak_rel]<>"")))` | 981 / 846 |
| − HR artefact | `=COUNTIFS(T[VO2peak_rel],"<>",T[HR_end_artefact],FALSE)` | (same pattern with both conditions) | 897 / 786 |
| − no HR near 60 s | `=COUNTIF(T[include],TRUE)` | `=COUNTA(UNIQUE(FILTER(T[ID],T[include])))` | **896 / 785** |

Within the 896: `HRR120` is non-blank in 885 and `HRR180` in 825. HRR180 is mostly missing because the recording stopped before ~170 s of recovery (check `recovery_duration_s`).

**Included vs excluded check:** compare mean Age, BMI and female % between `include = TRUE` and `FALSE` (`AVERAGEIFS`). They should be similar (Age 29.1 vs 27.9, BMI 23.9 vs 24.0). In Python, `included_vs_excluded.csv` adds Mann–Whitney p-values (all > 0.28).

**Python:** `sample_flow()` in `src/project1_hrr_vo2.py` produces `outputs/project1/tables/sample_flow.csv` and `exclusion_log.csv`.

---

## Part E: Descriptive Statistics (Table 1)

### E1. Choose mean ± SD or median [IQR]

For each variable, compute skewness in the analysis sample:
```
=SKEW(FILTER(T[BMI],T[include]))
```
If |skew| > 1, report **median [Q1–Q3]**; otherwise **mean ± SD**. Use the same format in all columns (overall / male / female).

Checkpoints: Age 0.61 → mean ± SD; BMI 1.01 → median [IQR]; VO2peak_rel 0.09 → mean ± SD; RER 1.33 → median [IQR].

### E2. Formulas

Overall column (replace `BMI` with each variable):

| Statistic | Formula |
|---|---|
| mean | `=AVERAGE(FILTER(T[Age],T[include]))` |
| SD | `=STDEV.S(FILTER(T[Age],T[include]))` |
| median | `=MEDIAN(FILTER(T[BMI],T[include]))` |
| Q1 / Q3 | `=QUARTILE.INC(FILTER(T[BMI],T[include]),1)` / `…,3)` |

For HRR120/HRR180, add `*(T[HRR120]<>"")` inside FILTER, because blanks would break STDEV. By sex, multiply the condition: `FILTER(T[Age],T[include]*(T[female]=1))`.

Counts: `=COUNTIFS(T[include],TRUE,T[female],1)` tests; participants via `UNIQUE(FILTER(...))`.

Format one cell, e.g. `=TEXT(mean,"0.0")&" ± "&TEXT(sd,"0.0")`.

### E3. Checkpoints (overall, n = 896)

| Variable | Value |
|---|---|
| Age | 29.1 ± 10.1 |
| BMI | 23.7 [22.1–25.3] |
| VO2peak_rel | 47.4 ± 8.8 |
| VO2peak (L/min) | 3.45 ± 0.73 |
| HRR60 | 29.0 ± 11.0 |
| HRR120 | 50.9 ± 12.4 |
| HRR180 | 60.4 ± 11.9 |
| Female VO2peak_rel | 39.8 ± 6.7 |

**Python:** `table1()` → `tables/table1_characteristics.csv`.

---

## Part F: Associations

### F1. Unadjusted correlations (Pearson with 95% CI, and Spearman)

Make a sheet **hrr60** containing only rows with `include = TRUE` (use `=FILTER(T[[ID]:[ID_test]]…)` or copy-paste visible rows after filtering). It needs columns `ID, VO2peak_rel, HRR60, Age, female, BMI`. Repeat with sheets **hrr120** and **hrr180**, keeping only rows where that HRR is non-blank.

| Quantity | Formula |
|---|---|
| n | `=COUNT(C:C)` |
| Pearson r | `=CORREL(C2:C897,B2:B897)` |
| Fisher z | `=FISHER(r)` |
| SE | `=1/SQRT(n-3)` |
| 95% CI | `=FISHERINV(z-1.96*SE)` and `=FISHERINV(z+1.96*SE)` |
| p-value | `t=r*SQRT((n-2)/(1-r^2))`, then `=T.DIST.2T(ABS(t),n-2)` |
| Spearman ρ | add `=RANK.AVG(C2,C$2:C$897,1)` and the same for B, then `CORREL` of the two rank columns |

**Why both?** Pearson assumes a linear relationship and is sensitive to outliers. Spearman uses ranks. If they agree, outliers aren't driving the result.

Checkpoints:

| | n | r [95% CI] | ρ |
|---|---|---|---|
| HRR60 | 896 | 0.28 [0.22, 0.34] | 0.27 |
| HRR120 | 885 | 0.32 [0.26, 0.38] | 0.30 |
| HRR180 | 825 | 0.35 [0.29, 0.41] | 0.32 |

### F2. Adjusted regression (the primary model)

**Model:** `VO2peak_rel = b0 + b1·HRR + b2·Age + b3·female + b4·BMI`, fitted separately for HRR60, HRR120 and HRR180.

**Excel, ToolPak:** Data → Data Analysis → Regression.
- Y range: VO2peak_rel
- X range: HRR60, Age, female, BMI. These must be **adjacent columns with no blanks**, so arrange them that way in sheet hrr60.
- Tick *Labels*, *Residuals* and *Residual Plots*.

**Excel, formula alternative:** `=LINEST(Y, X, TRUE, TRUE)` returns a 5×5 block. Note that **coefficients come out in reverse column order** (BMI, female, Age, HRR60, intercept), with SEs in the row below.

Checkpoints for HRR60 (n = 896):

| Term | Coefficient | Excel SE (ordinary) | Excel 95% CI |
|---|---|---|---|
| Intercept | 77.54 | 2.28 | |
| HRR60 (per bpm) | **0.1194** | 0.0222 | 0.076 – 0.163 |
| Age | −0.0567 | 0.0242 | |
| female | −10.61 | 0.71 | |
| BMI | −1.275 | 0.087 | |
| R² | **0.355** | | |

**Report per 10 bpm:** multiply by 10 to get **1.19 [0.76, 1.63]**.
**Report per 1 SD of HRR:** multiply the per-bpm coefficient by `STDEV.S(HRR60)` in the model sample (≈ 11.05) to get **1.32**.

Expected per-10-bpm results: HRR120 → 1.35 [0.94, 1.76]; HRR180 → 1.66 [1.23, 2.09].

**Why Python's CI differs slightly from Excel's:** 100 participants contributed more than one test (227 of the 896 tests). Tests from the same person aren't independent, so ordinary SEs are a bit too optimistic. Python uses **cluster-robust standard errors grouped by participant ID**. The coefficients are identical; only the SEs/CIs change, and here barely: Python gives 0.757–1.631 per 10 bpm. Excel can't do clustered SEs, which is why this step needs Python:

```python
import statsmodels.formula.api as smf
d = t[t.include].copy()                      # or use sample_flow()
fit = smf.ols("VO2peak_rel ~ HRR60 + Age + female + BMI", d)\
         .fit(cov_type="cluster", cov_kwds={"groups": d["ID"]})
print(fit.summary())
```

**Incremental R² (how much HRR adds):** run the regression *without* HRR (Age, female, BMI only) on the same rows and subtract R²s. Checkpoints: HRR60 +0.021, HRR120 +0.034, HRR180 +0.045. This is the basis for the claim that HRR is a "modest correlate".

### F3. Multiple-comparison correction (Holm)

You have 3 p-values (one per interval). Holm's method:
1. Sort the p-values ascending: p(1) ≤ p(2) ≤ p(3).
2. Multiply them by 3, 2 and 1 respectively.
3. Take a running maximum down the list, so an adjusted p can never be smaller than the one above it, and cap at 1.

In Excel, with the sorted p-values in B2:B4: C2 `=MIN(1,B2*3)`, C3 `=MIN(1,MAX(C2,B3*2))`, C4 `=MIN(1,MAX(C3,B4*1))`. All three stay < 0.001 here.

Python: `statsmodels.stats.multitest.multipletests(pvals, method="holm")`.

### F4. Which interval is strongest? (partial correlations + bootstrap)

**Idea:** compare the three HRRs on the **same** tests (825 that have all three), after removing the effect of age, sex and BMI.

**Excel (the point estimate):**
1. On the 825-row common sample, regress VO2peak_rel on Age, female and BMI. Save the residuals (call them `rY`).
2. Regress HRR60 on Age, female and BMI. Save the residuals (`rX`).
3. `=CORREL(rX, rY)` gives the **partial correlation**. Checkpoint: **0.176** for HRR60, 0.224 for HRR120 and 0.262 for HRR180.

**Python (the uncertainty):** is 0.262 really bigger than 0.176, or is that chance? We use a **cluster bootstrap**: resample *participants* (not tests) with replacement 2,000 times, recompute all three partial correlations each time, and take the 2.5th and 97.5th percentiles of the differences. See `compare_intervals()` in `src/project1_hrr_vo2.py`. Checkpoints: HRR180 − HRR60 = 0.086 [0.044, 0.132]; all three differences exclude 0.

### F5. Model diagnostics

| Check | What it tells you | Excel | Python |
|---|---|---|---|
| Residuals vs fitted | non-linearity, uneven spread | ToolPak *Residual Plots*, or scatter predicted vs residual | `fig6_model_diagnostics.png` |
| Normality | Q–Q shape | Sort residuals; theoretical quantile `=NORM.S.INV((RANK.AVG(e,all,1)-0.5)/n)`; scatter | `scipy.stats.probplot` |
| Breusch–Pagan (heteroscedasticity) | does residual spread depend on X? | Square the residuals, regress e² on the same 4 X's, then LM = n × R² and `p=CHISQ.DIST.RT(LM,4)` | `het_breuschpagan` → p = 0.012 |
| VIF (collinearity) | are predictors redundant? | Regress each X on the other three: `VIF=1/(1-R²)` | `variance_inflation_factor` → all < 1.15 |
| Cook's distance (influence) | does any single test drive the fit? | not practical | `get_influence().cooks_distance` → max 0.022 |

**Interpretation:** BP p ≈ 0.01 means mild heteroscedasticity. The cluster-robust SEs are also heteroscedasticity-robust, so the inference is still valid. VIFs near 1 mean no collinearity problem, and max Cook's D far below 1 means no single influential point.

---

## Part G: Sensitivity Analyses

The question: *does the conclusion survive reasonable alternative choices?* Each analysis reruns the F2 model with one thing changed.

| # | Analysis | What to change | Excel? | Checkpoint: HRR60, per SD [95% CI] |
|---|---|---|---|---|
| 1 | Primary | n/a | coef ✅ / CI ❌ | 1.32 [0.84, 1.80] |
| 2 | Mixed model | random intercept per participant | ❌ | 1.36 [0.88, 1.85] |
| 3 | One test per participant | keep `first_test = TRUE` | ✅ **exact** (ordinary OLS is correct here) | 1.50 [0.99, 2.00], n = 774 |
| 4 | Adults only | keep `adult = TRUE` | coef ✅ | 1.47 |
| 5 | Peak VO2: highest breath | Y = `VO2peak_rel_breath` | coef ✅ | 1.23 |
| 6 | Peak VO2: 30 s | Y = `VO2peak_rel_30s` | coef ✅ | 1.34 |
| 7 | Tolerance ±5 s | X = `HRR60_strict` | coef ✅ | 1.32 |
| 8 | Raw HR, no artefact rule | X = `HRR60_raw`, sample = all tests with VO2 | coef ✅ | 0.96 |
| 9 | Raw HR window means | X = `HRR60_window`, same sample as 8 | coef ✅ | 1.01 |
| 10 | Active recovery only | keep `active_recovery = TRUE` | coef ✅ | 1.30 |
| 11 | Maximal tests only | keep `max_criterion_met = TRUE` | coef ✅ | 1.32 |
| 12 | + protocol | add X column `ramp = IF(protocol="ramp",1,0)` | coef ✅ | 1.13 |
| 13 | + HR_end (exploratory) | add X column `HR_end` | coef ✅ | 1.39 |

Note: per-SD = per-bpm coefficient × SD of that HRR column *in that analysis's sample*.

**Mixed model in Python:**
```python
mm = smf.mixedlm("VO2peak_rel ~ HRR60 + Age + female + BMI", d, groups=d["ID"]).fit(reml=True)
print(mm.summary())
```

**How to read the results:** every row is positive with a CI excluding 0. The raw-HR rows (8–9) are about 25% smaller. That is **regression dilution**: random error in an exposure biases its slope toward zero. It shows the artefact handling matters.

Python: the `analyses` list in `main()` of `src/project1_hrr_vo2.py` → `tables/sensitivity_analyses.csv`.

---

## Part H: Figures

| Figure | Excel how-to | Python function |
|---|---|---|
| Fig 1: event-detection traces | Two stacked line charts per test (Speed above, HR below, same x-range). Add a vertical line at t_end: add a 2-point series (t_end, 0) and (t_end, max) and format it as a dashed line. Mark HR_end and the +60/+120/+180 points as extra scatter series. | `fig_trace()` |
| Fig 2: distributions | Insert → Statistic Chart → **Histogram** for each variable; set bin count ≈ 30 in Format Axis | `fig_distributions()` |
| Fig 3: HRR vs VO2peak scatter | Scatter; right-click → Add Trendline → Linear, tick "Display R²". Note √R² = r. | `fig_scatter()` |
| Fig 4: forest plot | Hard in Excel: scatter of estimates with custom horizontal error bars (Format Error Bars → Custom: CI − estimate) | `fig_forest()` |
| Fig 5: sample flow | Insert → Shapes (boxes + arrows) using your Part D counts | `fig_flow()` |
| Fig 6: diagnostics | See F5 | `fig_diagnostics()` |

**Good chart habits used here:**
- No dual y-axes.
- Units on every axis.
- n written on every panel.
- The same colour means the same HRR interval in every figure (blue = 60, orange = 120, green = 180).
- Light gridlines behind the data.

---

## Part I: From Results to Write-up (How the Numbers Became Sentences)

| Report statement | Comes from |
|---|---|
| "896 tests from 785 participants" | Part D |
| "r = 0.28, 0.32, 0.35" | F1 |
| "+1.19 mL·kg⁻¹·min⁻¹ per 10 bpm HRR60…" | F2 (Python cluster CIs) |
| "HRR adds only 2–5% explained variance" | F2 incremental R² |
| "association strengthened with longer recovery" | F4 bootstrap |
| "robust across 13 sensitivity analyses" | Part G |
| "raw HR gave ~25% smaller estimates (regression dilution)" | G rows 8–9 vs 1 |
| "associational, not causal" | design: cross-sectional, observational |

---

## Part J: Common Pitfalls

1. **Using the last row as end of exercise.** That point is ~3 min into recovery.
2. **Replacing missing VO2/HR with 0.** This creates impossible values. Always leave them blank.
3. **Merging on `ID` alone.** Participants have several tests, so merge on `ID_test`.
4. **Treating 896 tests as 896 independent people.** Use clustered SEs, a mixed model, or one test per person.
5. **Forgetting that rolling windows include the warm-up.** Harmless for the peak, but the "≥ 15 s after the first breath" rule matters.
6. **Excel `MEDIAN`/`AVERAGE` over ranges with text like "NaN".** Make sure missing values are truly blank cells.
7. **Peeking at the outcome before fixing rules.** The despike filter and artefact rule were fixed by looking only at HR traces, never at HRR–VO2 plots. Keep that discipline, and say so in your methods.
8. **LINEST's reversed coefficient order.** Easy to misread.
