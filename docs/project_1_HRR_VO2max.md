# Project 1 — Heart-rate recovery and aerobic capacity

## Working title
**Association between post-exercise heart-rate recovery and peak oxygen uptake in a cohort of amateur and professional athletes**

## Background and rationale
Heart rate rises during graded exercise and falls during recovery. Heart-rate recovery (HRR) is commonly operationalised as the fall in heart rate from the end of exercise to a specified recovery time. It is used as an indicator of post-exercise autonomic reactivation and is associated with cardiorespiratory fitness in several settings. However, HRR depends on how the end of exercise and recovery windows are defined, and on the recovery protocol. This project uses breath-by-breath treadmill test data to examine how HRR at 60, 120 and 180 seconds relates to peak oxygen uptake.

## Primary research question
Among participants with usable maximal treadmill test data, are larger HRR values at 60, 120 and 180 seconds associated with higher peak VO2, after accounting for age, sex and BMI?

## Secondary questions
1. Which recovery interval (60, 120 or 180 seconds) has the strongest association with peak VO2?
2. Are the associations materially different after restricting the sample to adults aged 18 or older?
3. How sensitive are the findings to reasonable choices for defining end exercise and selecting the recovery HR observation?

## Hypotheses
- H1: Higher HRR60 is positively associated with peak VO2 (mL·kg⁻¹·min⁻¹).
- H2: HRR120 and HRR180 are also positively associated with peak VO2.
- H3: Associations remain after adjustment for age, sex and BMI, although their magnitude may change.

These are hypotheses to test, not expected findings to force. Report null or contrary results honestly.

## Dataset and unit of analysis
Use the PhysioNet *Treadmill Maximal Exercise Tests from the Exercise Physiology and Human Performance Lab of the University of Malaga*, version 1.0.1. Metadata are in `subject-info.csv`; breath-level time series are in `test_measure.csv`. The primary unit is the exercise test (`ID_test`). Because 992 tests come from 857 participants, account for clustering/repeated tests by participant (`ID`) in inferential models, or select one eligible test per participant under a prespecified rule and run repeated-test analyses as sensitivity checks.

## Variables
- Outcome: peak VO2 expressed as mL·kg⁻¹·min⁻¹. Calculate as maximum valid VO2 (mL/min) divided by body mass (kg), multiplied by the appropriate conversion factor (divide mL/min by kg directly).
- Predictors: HRR60, HRR120, HRR180 in beats/min, calculated as HR at end exercise minus HR at the target recovery time.
- Covariates: age (years), sex as coded in the source documentation, BMI (kg/m²), and potentially test protocol/other available metadata if justified.
- Derived variables: BMI = weight (kg) / [height (m)]²; test duration; end-exercise time; recovery time relative to end exercise.

## Operational definitions — decide and document before modelling
1. Identify the end-of-exercise point from the treadmill speed/time series. The dataset may contain cool-down measurements; do not simply use the final row of the recording.
2. A defensible initial rule is the final measurement at the end of the maximal exercise phase immediately before the sustained cool-down. Inspect speed and HR plots for a sample of tests and write a reproducible rule. Record the rule and any ambiguous cases.
3. For each target recovery time (60/120/180 s), select the HR observation nearest to that time after end exercise, subject to a prespecified tolerance (for example ±10 s). If no observation falls within the tolerance, mark that HRR value missing rather than extrapolating silently.
4. HRR_t = HR_end − HR_(end+t). Positive values indicate a fall in HR. State clearly if the selected protocol makes this definition inappropriate for a test.
5. Peak VO2: use the maximum valid VO2 value during the exercise phase, not a recovery value. Also consider a short rolling average (e.g. 15–30 s) as a sensitivity definition because breath-by-breath maxima can be noisy. Specify the chosen window before examining associations.

## Analysis plan
1. Data audit: dimensions, variable names, missingness, duplicate IDs, repeated tests, ranges and units.
2. Merge participant metadata to breath-level measurements using both `ID` and `ID_test`; verify row counts and unmatched records.
3. Derive BMI, peak VO2 and HRR measures. Create a test-level analysis table with one row per `ID_test`.
4. Descriptive statistics: mean/SD or median/IQR as appropriate; distributions and missingness; scatterplots and histograms.
5. Bivariate analysis: Pearson correlation when assumptions are reasonable; Spearman rank correlation as a robustness comparison.
6. Primary models: linear regression of peak VO2 on each HRR measure, adjusted for age, sex and BMI. Standardise continuous predictors for comparing effect sizes. Check linearity, residual distribution, heteroscedasticity, influential observations and multicollinearity.
7. Repeated tests: use a mixed-effects model with participant (`ID`) as a random intercept if feasible, or use cluster-robust standard errors. Explain the chosen method. Do not treat 992 tests as 992 independent participants.
8. Multiple comparisons: identify HRR60 as the primary exposure and HRR120/180 as secondary, or apply a transparent correction (e.g. Holm) across the three tests.
9. Sensitivity analyses: adults only; one test per participant; alternate peak VO2 definition; alternate end-exercise/recovery tolerance; complete-case versus justified missing-data strategy.

## Deliverables
- Reproducible Python notebook or script.
- Data dictionary and sample flow diagram (tests/participants excluded and why).
- At least four figures: sample distributions; HRR vs peak VO2 scatterplots; adjusted model estimates with confidence intervals; representative HR/time/speed trace illustrating event detection.
- Table 1: participant/test characteristics.
- Table 2: unadjusted correlations and adjusted regression estimates.
- 1,500–2,500 word research report: abstract, introduction, methods, results, discussion, limitations and conclusion.
- A short README documenting environment, data source/version, processing decisions and how to reproduce outputs.

## Interpretation boundaries
An association does not establish that improving HRR causes VO2max to increase. HRR and VO2peak are both influenced by age, sex, training status, protocol and measurement choices. VO2peak from a test is not automatically equivalent to a verified VO2max unless plateau or other maximality criteria are established.
