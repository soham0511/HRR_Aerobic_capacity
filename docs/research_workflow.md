# Research workflow and submission checklist

## Phase 1 — Set up
- Download the two CSV files and license from PhysioNet version 1.0.1.
- Preserve untouched source files in `data/raw/`; never edit them manually.
- Create `data/processed/`, `notebooks/`, `src/`, `outputs/figures/` and `outputs/tables/`.
- Record Python version and package versions.

## Phase 2 — Read before analysing
- Read the PhysioNet dataset description, access terms and original HRR paper.
- For Project 1, focus the literature review on HRR definitions, recovery protocol dependence, autonomic physiology and VO2peak/VO2max.
- For Project 2, focus on age and cardiorespiratory fitness, sex differences, BMI limitations, ratio scaling and cross-sectional inference.
- Keep a literature matrix: citation, population, design, measures, findings, limitations and relevance.

## Phase 3 — Protocol and data audit
- Write the research question, hypotheses, population, unit of analysis and primary outcome before modelling.
- Make a data flow diagram and missingness summary.
- Define end exercise, peak VO2 and HRR time windows in writing.
- Check whether athlete-status classification actually exists before attempting subgroup comparisons.

## Phase 4 — Analysis
- Build one test-level dataset with a row per `ID_test`.
- Keep participant ID (`ID`) for repeated-measures handling.
- Save every transformation in code.
- Use descriptive statistics, plots, regression and diagnostics.
- Run sensitivity analyses and retain both primary and sensitivity results.

## Phase 5 — Write-up
- Abstract: background, objective, methods, key results and conclusion.
- Introduction: rationale, literature gap and explicit research question.
- Methods: dataset, population, variables, operational definitions, statistics and missing data.
- Results: sample flow, descriptive statistics, estimates and uncertainty.
- Discussion: main findings, comparison with literature, physiological interpretation and alternative explanations.
- Limitations: selection, cross-sectional design, repeated tests, measurement/protocol issues, missingness and proxy measures.
- Conclusion: answer only what the data support.

## Reproducibility checklist
- [ ] Data source/version and access date documented.
- [ ] License retained and terms followed.
- [ ] Raw data unchanged.
- [ ] One command or notebook sequence reproduces derived data and outputs.
- [ ] Software dependencies listed.
- [ ] Exclusions and missing data documented.
- [ ] Figures have units, sample sizes and clear captions.
- [ ] Tables report effect sizes and confidence intervals.
- [ ] No causal claims from cross-sectional associations.
- [ ] No invented athlete-status or body-fat variables.
