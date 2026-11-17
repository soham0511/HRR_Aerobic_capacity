# Sports Science Research Starter Pack

Two portfolio projects using the University of Malaga Treadmill Maximal Exercise Tests dataset (PhysioNet, version 1.0.1).

## First: obtain the source data

The data are hosted by PhysioNet and are not bundled in this ZIP because the runtime used to prepare this pack could not retrieve the remote CSV files. Download them directly from the official dataset page:

https://physionet.org/content/treadmill-exercise-cardioresp/1.0.1/

Download `subject-info.csv`, `test_measure.csv`, and `LICENSE.txt`. Put the two CSV files in the `data/` folder. Keep the license with your working copy and follow its terms. Alternatively, from a terminal with Python and the PhysioNet package installed:

```bash
pip install physionet
physionet download treadmill-exercise-cardioresp --version 1.0.1
```

The dataset page documents 992 exercise tests from 857 people. `subject-info.csv` contains one row per test; `test_measure.csv` contains breath-by-breath measurements. Some participants have repeated tests. Treat `ID` as participant identifier and `ID_test` as test identifier.

## Contents

- `docs/project_1_HRR_VO2max.md`: detailed question, hypotheses, variables, analysis plan and reporting requirements.
- `docs/project_2_age_BMI_aerobic_capacity.md`: detailed independent-study brief and limitations.
- `docs/data_dictionary_and_quality_checks.md`: variable guide, joins, unit conversions and quality checks.
- `docs/research_workflow.md`: reproducible workflow, ethics, literature review and submission checklist.
- `src/starter_analysis.py`: Python starter script for loading, merging and deriving test-level measures.
- `requirements.txt`: Python dependencies.

## Recommended order

Complete Project 1 first. It is more tightly specified and teaches you to turn breath-level data into defensible test-level physiological measures. Then complete Project 2 using the same cleaned analysis table but formulate and defend your own hypothesis.

## Project 1 — status: complete

**Question:** Is faster post-exercise heart-rate recovery (HRR at 60/120/180 s) associated with higher peak VO2, adjusted for age, sex and BMI?
**Answer (896 tests, 785 participants):** Yes. Each 10 bpm of extra HRR goes with +1.2 (HRR60), +1.3 (HRR120) and +1.7 (HRR180) mL·kg⁻¹·min⁻¹ of peak VO2. The association gets stronger at later recovery intervals and holds in all 13 sensitivity analyses. Full write-up: [reports/project1_report.md](reports/project1_report.md).

### Reproduce

```bash
pip install -r requirements.txt
python src/prep.py              # breath-level -> data/processed/test_level.csv (+ outputs/audit/)
python src/project1_hrr_vo2.py  # tables + figures -> outputs/project1/ (~1 min)
```

Environment used: Python 3.11.9, pandas 3.0, statsmodels 0.14.6. Data: PhysioNet treadmill-exercise-cardioresp v1.0.1. Raw CSVs in `data/` are never modified.

### Layout

| Path | What it is |
|---|---|
| `src/prep.py` | Data audit plus derivation of test-level measures. All operational definitions are in its `DEFINITIONS` dict. Shared with Project 2. |
| `src/project1_hrr_vo2.py` | Sample flow, Table 1/2, primary models, diagnostics, interval comparison, sensitivity analyses, figures. |
| `src/starter_analysis.py` | The original starter script, superseded by the two files above. |
| `data/processed/test_level.csv` | One row per `ID_test` with every derived variable. |
| `outputs/audit/` | Data audit report and per-test phase/artefact flags for manual review. |
| `outputs/project1/tables/` | All result tables as CSV, including the exclusion log. |
| `outputs/project1/figures/` | Figures 1–6. |
| `reports/project1_report.md` | The research report. |

### Key processing decisions (details in the report, §2.3)

- **End of exercise:** the last sample at peak treadmill speed, never the final row of the recording.
- **HR cleaning:** HR is despiked with a 5-sample rolling median, applied within each phase.
- **Artefact rule:** a test's HRR is set to missing if HR_end is more than 20 bpm below the exercise peak HR (end-of-test signal dropout; 85 tests).
- **Recovery HR:** the nearest despiked observation to end + t, within ±10 s. Otherwise the value is missing.
- **Peak VO2:** the highest 15-s rolling mean during the exercise phase, divided by body mass.
- **Repeated tests:** handled with participant-clustered robust standard errors. A mixed model and a one-test-per-participant analysis are run as sensitivity checks.
- **Sex coding:** 1 = female, confirmed from the PhysioNet page.
- **VO2 discrepancy:** 11 tests have no VO2 data, whereas the PhysioNet page says 30. This is noted, not resolved.

## Important scientific cautions

1. This is an observational, cross-sectional dataset. Associations are not causal effects.
2. There are 992 tests but 857 participants. Repeated tests from the same person are not independent.
3. BMI is calculated from height and weight; it is not a direct measure of body fat or lean mass.
4. The data include participants aged 10–63. Decide in advance whether to restrict analyses to adults (18+) and justify it.
5. Do not assume the last recorded HR value is exactly 60, 120 or 180 seconds after exercise. Establish the end-of-exercise time and implement a documented time-window rule.
6. Do not assume that every test has valid VO2 data. The PhysioNet documentation notes missing VO2, VCO2 and VE measurements for some tests.
7. Do not claim that this dataset represents all athletes or the general population.
