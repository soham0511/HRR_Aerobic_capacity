# Post-exercise heart-rate recovery and peak oxygen uptake in treadmill-tested athletes

*Project 1 — research report. Data: PhysioNet "Treadmill Maximal Exercise Tests from the Exercise Physiology and Human Performance Lab of the University of Malaga", v1.0.1. All numbers below are produced by `src/prep.py` and `src/project1_hrr_vo2.py`.*

---

## Abstract

**Background.** Heart-rate recovery (HRR), the fall in heart rate after exercise stops, is a simple index of post-exercise autonomic reactivation. Whether it tracks aerobic capacity in athletic populations, and which recovery interval does so best, depends on how the end of exercise and the recovery time points are defined.

**Objective.** To estimate the association between HRR at 60, 120 and 180 s (HRR60/120/180) and peak oxygen uptake (VO2peak, mL·kg⁻¹·min⁻¹), adjusted for age, sex and BMI.

**Methods.** Cross-sectional analysis of 992 breath-by-breath maximal treadmill tests from 857 participants. End of exercise was defined as the last sample at peak treadmill speed. Recovery HR was the nearest despiked HR observation within ±10 s of each target time. VO2peak was the highest 15-s rolling mean of VO2 during the exercise phase. Linear regression with participant-clustered robust standard errors was fitted separately for each HRR interval. HRR60 was prespecified as the primary exposure. Thirteen sensitivity analyses were run.

**Results.** The primary sample comprised 896 tests from 785 participants (mean age 29.1 ± 10.1 y; 15% of tests from female participants; VO2peak 47.4 ± 8.8 mL·kg⁻¹·min⁻¹). All three HRR measures were positively correlated with VO2peak: r = 0.28 for HRR60, 0.32 for HRR120 and 0.35 for HRR180. After adjustment, each 10-bpm larger HRR was associated with a higher VO2peak:

| Exposure | Difference per 10 bpm, mL·kg⁻¹·min⁻¹ (95% CI) | Holm-adjusted p |
|---|---|---|
| HRR60 | 1.19 (0.76–1.63) | < 0.001 |
| HRR120 | 1.35 (0.94–1.76) | < 0.001 |
| HRR180 | 1.66 (1.23–2.09) | < 0.001 |

On a common sample, the partial correlation increased with recovery duration (0.18 → 0.22 → 0.26). All pairwise differences had bootstrap 95% CIs that excluded zero. Every sensitivity analysis kept the same direction, with all CIs excluding zero.

**Conclusion.** Faster heart-rate recovery is modestly but robustly associated with higher peak aerobic capacity in this cohort, independent of age, sex and BMI. Later recovery intervals carry more information than HRR60. HRR adds only 2–5% explained variance beyond age, sex and BMI, so it is a correlate of fitness rather than a substitute for measuring VO2.

---

## 1. Introduction

After a bout of exercise, heart rate falls rapidly. The early, fast phase of recovery is attributed mainly to parasympathetic (vagal) reactivation, and the slower later phase to the withdrawal of sympathetic activity and circulating catecholamines (Imai et al., 1994). Attenuated HRR has prognostic value in clinical populations (Cole et al., 1999). In sport it is used as a low-cost marker of autonomic function and training status (Buchheit et al., 2007; Daanen et al., 2012).

Peak oxygen uptake is the reference measure of cardiorespiratory fitness, but it needs a gas analyser and a maximal effort. If HRR tracks VO2peak, it could serve as a cheap field proxy. HRR is not a single quantity, though. It depends on:

- how "end of exercise" is identified;
- which recovery time point is used;
- whether recovery is active or passive;
- how artefacts in the HR signal are handled.

Breath-by-breath laboratory data make these choices explicit and testable.

**Research question.** Among participants with usable maximal treadmill-test data, are larger HRR60, HRR120 and HRR180 associated with higher VO2peak after accounting for age, sex and BMI? Secondary questions:

1. Which interval has the strongest association?
2. Are associations similar in adults only?
3. How sensitive are findings to the operational definitions?

**Hypotheses** (stated before modelling):

- **H1:** HRR60 is positively associated with VO2peak.
- **H2:** HRR120 and HRR180 are also positively associated.
- **H3:** The associations persist after adjustment for age, sex and BMI.

## 2. Methods

### 2.1 Data source

The dataset (PhysioNet, v1.0.1) contains 992 graded maximal treadmill tests from 857 participants aged 10–63 y, collected at the University of Malaga. `subject-info.csv` holds one row per test: age, weight, height, sex, temperature and humidity. `test_measure.csv` holds 575,087 breath-by-breath rows: time, speed, HR, VO2, VCO2, RR and VE.

According to the dataset page, Sex = 1 denotes female. This is consistent with the anthropometrics: Sex = 1 participants were on average 9.6 cm shorter and 12.6 kg lighter. Tests used either a continuous ramp (0.1 km/h every ~6 s; 66% of analysed tests) or 1 km/h steps each minute. Both protocols were followed by walking recovery at ~5 km/h.

### 2.2 Data audit

The audit (`outputs/audit/data_audit.txt`) found:

- No duplicate test IDs in the metadata, and no unmatched records between the two files.
- 100 participants with more than one test, up to five.
- Time increasing monotonically within every test. 3,021 rows shared a timestamp with the previous breath; their HR values were averaged.
- One HR value of 0 and one negative VO2 value, both set to missing rather than zero.
- 11 tests with no VO2 data at all. The PhysioNet page says 30; this discrepancy is recorded rather than resolved.

### 2.3 Operational definitions

All definitions were fixed after inspecting raw traces and before any HRR–VO2 association was examined. They are coded in `DEFINITIONS` in `src/prep.py`.

- **End of exercise.** The last sample at the test's maximum treadmill speed. In every test, speed then falls abruptly to recovery speed (median drop 11.8 km/h). In three tests the treadmill decelerated over a few seconds; the rule still marks the onset of the HR decline. The final row of the recording is never used. Figure 1 shows the rule applied to one ramp and one step test.
- **HR cleaning.** HR outside 30–230 bpm was set to missing. HR was despiked with a centred 5-sample rolling median, applied separately within the exercise and recovery phases so the filter never crosses the end-of-exercise boundary.
- **HR_end.** The last despiked HR within the 5 s up to end of exercise.
- **HR artefact rule.** Inspection showed that most negative HRR values came from HR signal dropouts in the final seconds of exercise, for example a recorded HR of 88 bpm in a test whose peak HR was 175 bpm. The rule: if HR_end was more than 20 bpm below the test's despiked exercise-phase peak HR, the end-exercise HR was treated as signal loss and that test's HRR values were set to missing. This affected 85 tests.
- **Recovery HR.** The despiked HR observation nearest to end + t s (t = 60, 120, 180), accepted only if it lay within ±10 s. Otherwise the value was left missing; nothing was extrapolated. In practice the nearest observation was a median of 0 s from the target.
- **HRR_t.** HR_end − HR_(end+t), in bpm. Positive values mean HR fell.
- **VO2peak.** The highest 15-s time-based rolling mean of VO2 during the exercise phase, divided by body mass. A rolling mean was chosen over the single highest breath because breath-by-breath maxima are noisy (Robergs et al., 2010). The highest breath and a 30-s mean were kept as sensitivity definitions.
- **Covariates.** Age (y), sex (female = 1), and BMI = weight / height².

### 2.4 Sample

Exclusions were applied in sequence (Figure 5; `tables/exclusion_log.csv`):

| Step | Tests excluded | Tests remaining | Participants remaining |
|---|---|---|---|
| All tests | — | 992 | 857 |
| No VO2 data | 11 | 981 | 846 |
| End-exercise HR artefact | 84 | 897 | 786 |
| No HR within ±10 s of 60 s | 1 | 896 | 785 |

HRR120 was available for 885 tests and HRR180 for 825. HRR180 was missing mostly because the recovery recording ended before about 170 s, not because of signal quality. Excluded tests did not differ meaningfully from included tests in age, BMI, sex, peak speed or exercise duration (all Mann–Whitney p > 0.28).

One artefact-flagged test also had no VO2 data and is counted under "No VO2 data", which is why 84 rather than 85 appear at the artefact step.

### 2.5 Statistical analysis

Descriptives are reported as mean ± SD, or as median [IQR] when |skew| > 1. Unadjusted associations were assessed with Pearson r (Fisher-z 95% CI) and Spearman ρ.

The primary models were ordinary least squares regressions of the form VO2peak ~ HRR_t + age + sex + BMI, one per interval. They used cluster-robust (sandwich) standard errors grouped by participant, because 227 of the 896 tests came from participants with repeated tests. Estimates are reported per 10 bpm of HRR and per 1 SD of HRR.

HRR60 was the prespecified primary exposure. Holm-adjusted p-values across the three intervals are also reported.

Diagnostics covered residual plots, Q–Q plots (Figure 6), the Breusch–Pagan test, Cook's distance and VIFs.

To compare intervals (secondary question 1), partial correlations adjusted for age, sex and BMI were computed on the 825 tests with all three HRR values. Pairwise differences were bootstrapped (2,000 resamples of participants, not tests).

Sensitivity analyses:

- a linear mixed model with a random intercept per participant;
- one (first) test per participant;
- adults ≥ 18 y only;
- the alternate VO2peak definitions (highest breath; 30-s mean);
- a stricter ±5 s recovery tolerance;
- the brief's literal rule on raw HR, with no despiking and no artefact rule;
- raw-HR window means (10 s at end of exercise; ±5 s at recovery targets);
- active-recovery tests only;
- tests meeting at least one secondary maximality criterion (RER ≥ 1.10 or peak HR ≥ 90% age-predicted);
- additional adjustment for protocol (ramp vs step);
- additional adjustment for HR_end (exploratory).

Analyses used Python 3.11 with pandas, statsmodels 0.14 and SciPy.

## 3. Results

### 3.1 Sample characteristics

Table 1 (`tables/table1_characteristics.csv`) summarises the 896 analysed tests:

| | Overall | Male | Female |
|---|---|---|---|
| Tests (participants) | 896 (785) | 765 (670) | 131 (115) |
| Age, y | 29.1 ± 10.1 | 29.6 ± 10.3 | 26.4 ± 8.9 |
| BMI, kg/m², median [IQR] | 23.7 [22.1–25.3] | 23.9 [22.5–25.5] | 22.2 [20.8–24.0] |
| VO2peak, mL·kg⁻¹·min⁻¹ | 47.4 ± 8.8 | 48.7 ± 8.5 | 39.8 ± 6.7 |
| VO2peak, L/min | 3.45 ± 0.73 | 3.62 ± 0.63 | 2.48 ± 0.52 |
| RER at VO2peak, median [IQR] | 1.12 [1.06–1.19] | 1.12 [1.06–1.19] | 1.11 [1.05–1.16] |
| Peak HR, % age-predicted | 97.9 ± 5.1 | 98.2 ± 5.1 | 96.3 ± 4.4 |
| HRR60, bpm | 29.0 ± 11.0 | 29.8 ± 10.9 | 24.2 ± 10.5 |
| HRR120, bpm | 50.9 ± 12.4 | 51.8 ± 12.2 | 45.6 ± 12.4 |
| HRR180, bpm | 60.4 ± 11.9 | 61.3 ± 11.4 | 55.4 ± 13.1 |

86% of tests were from adults. 96% met at least one secondary maximality criterion. Distributions are shown in Figure 2. HRR and VO2peak were approximately symmetric; age was right-skewed.

### 3.2 Unadjusted associations

All three HRR measures correlated positively with VO2peak (Figure 3). The Pearson and Spearman estimates agreed closely, which indicates the associations are not driven by outliers or non-linearity.

| Exposure | n | Pearson r (95% CI) | Spearman ρ |
|---|---|---|---|
| HRR60 | 896 | 0.28 (0.22–0.34) | 0.27 |
| HRR120 | 885 | 0.32 (0.26–0.38) | 0.30 |
| HRR180 | 825 | 0.35 (0.29–0.41) | 0.32 |

### 3.3 Adjusted associations (primary analysis)

Table 2 (`tables/table2_correlations_and_models.csv`) gives the adjusted estimates:

| Exposure | β per 10 bpm (95% CI) | β per 1 SD (95% CI) | Holm p | Model R² | ΔR² vs covariates only |
|---|---|---|---|---|---|
| HRR60 | 1.19 (0.76–1.63) | 1.32 (0.84–1.80) | < 0.001 | 0.355 | 0.021 |
| HRR120 | 1.35 (0.94–1.76) | 1.68 (1.17–2.19) | < 0.001 | 0.367 | 0.034 |
| HRR180 | 1.66 (1.23–2.09) | 1.97 (1.46–2.48) | < 0.001 | 0.385 | 0.045 |

Adjustment roughly halved the unadjusted slopes. For HRR60, for example, the slope fell from 2.26 to 1.19 per 10 bpm. Female sex and higher BMI were each strongly associated with lower relative VO2peak: about −10.5 mL·kg⁻¹·min⁻¹ for female sex and about −1.27 per kg/m² of BMI. Age was weakly associated, at about −0.06 per year. These covariate estimates were almost identical across the three models.

H1, H2 and H3 were all supported.

**Diagnostics.** Residuals were close to normal (skew ≈ 0.02, excess kurtosis ≈ 0.6) with no visible structure (Figure 6). The Breusch–Pagan test suggested mild heteroscedasticity (p = 0.01–0.06); the cluster-robust standard errors are also heteroscedasticity-robust. No observation was highly influential (maximum Cook's D = 0.023). All VIFs were below 1.15.

### 3.4 Which recovery interval?

On the common sample of 825 tests from 729 participants, the adjusted partial correlation with VO2peak was:

- HRR60: 0.18 (bootstrap 95% CI 0.11–0.24)
- HRR120: 0.22 (0.16–0.28)
- HRR180: 0.26 (0.20–0.32)

| Comparison | Difference in partial r (95% CI) |
|---|---|
| HRR120 − HRR60 | 0.048 (0.008–0.085) |
| HRR180 − HRR60 | 0.086 (0.044–0.132) |
| HRR180 − HRR120 | 0.039 (0.006–0.074) |

The association strengthened with longer recovery, and every difference was distinguishable from zero.

### 3.5 Sensitivity analyses

Every one of the 13 sensitivity analyses (Figure 4; `tables/sensitivity_analyses.csv`) gave a positive association with a 95% CI excluding zero for all three intervals. The HRR60 < HRR120 < HRR180 ordering was preserved throughout.

Per-SD estimates for HRR60 ranged from 0.96 to 1.50 mL·kg⁻¹·min⁻¹:

- The mixed model (1.36), one test per participant (1.50) and adults-only (1.47) analyses closely matched the primary estimate (1.32).
- Restricting to active recovery, applying maximality criteria, using the stricter ±5 s tolerance and switching VO2peak definitions each changed the estimates by less than 0.1.
- Adding protocol as a covariate attenuated HRR60 slightly (1.13).
- The two raw-HR definitions without artefact handling gave the smallest estimates (0.96 and 1.01).

## 4. Discussion

In this cohort of 785 athletically active participants, faster post-exercise heart-rate recovery was associated with higher peak aerobic capacity, independently of age, sex and BMI. The association was consistent across modelling strategies and operational definitions.

The magnitude is modest. One SD (~11 bpm) of extra HRR60 corresponds to about 1.3 mL·kg⁻¹·min⁻¹ more VO2peak, roughly 0.15 SD of VO2peak. Adding HRR to a model already containing age, sex and BMI increased R² by only 2–5 percentage points. HRR is a real correlate of aerobic fitness, but it is not precise enough to estimate an individual's VO2peak.

**Later intervals were more informative.** HRR180 was more strongly associated with VO2peak than HRR60. One physiological reading is that HRR60 mainly reflects rapid vagal reactivation, which is already near-maximal in most well-trained individuals and so varies less with fitness in this population. Later recovery integrates sympathetic withdrawal, metabolite clearance and the restoration of blood volume and thermoregulatory load, all of which may scale more closely with aerobic capacity. A simpler, non-physiological explanation also fits: a larger absolute HR drop over a longer window has a better signal-to-noise ratio, because a measurement error of a few bpm is proportionally smaller. The present data cannot distinguish these explanations.

**Measurement choices matter.** The sensitivity analyses that used raw HR without artefact handling produced estimates about 25% smaller than the primary analysis. This is the expected effect of random measurement error in an exposure: regression dilution, which biases slopes toward zero. A handful of end-of-exercise HR dropouts produced spurious large negative HRR values. Such dropouts are plausibly common in chest-strap recordings at peak exertion. This supports the brief's warning that HRR cannot be computed by naïvely differencing recorded values. Reported HRR–fitness associations in other studies may be similarly diluted if signal quality was not addressed.

The protocol covariate attenuated HRR60 slightly. Ramp and step protocols end differently: ramps end at a moving target, steps at the end of a stage. This may affect HR_end and early recovery, so protocol is a sensible covariate for future work.

Adjusting for HR_end did not attenuate the associations; it strengthened them slightly. The HRR–VO2peak relationship is therefore not explained by fitter participants simply reaching higher end-exercise heart rates. That model is exploratory, because HR_end is mathematically part of HRR.

## 5. Limitations

1. **Cross-sectional and observational.** The associations are between people, not within them. Nothing here shows that improving HRR raises VO2peak, or that training changes both in parallel. Training status, genetics and body composition plausibly drive both.
2. **Selected population.** Participants were people referred for or choosing laboratory testing, mostly young men (85% of tests), described as amateur and professional athletes. Results should not be generalised to the general population, to clinical groups, or to women, whose sample was small.
3. **VO2peak is not verified VO2max.** No plateau criterion was applied. Secondary criteria (RER, %HRmax) were met by 96% of tests, and restricting to those tests did not change results. Age-predicted HRmax (220 − age) is itself imprecise.
4. **Recovery protocol.** Recovery was mostly active walking at ~5 km/h. HRR under passive recovery, or at other walking speeds, is not comparable. Only 7 analysed tests had passive recovery, too few to study.
5. **Artefact rule.** The 20-bpm rule and the 5-sample median filter are judgement calls. They were made blind to the outcome and are backed by the raw-HR sensitivity analyses, but they excluded 8.6% of tests.
6. **Missing HRR180.** HRR180 was missing in 8% of the primary sample, mainly because recordings were short. This is presumably unrelated to fitness, but if it were related, HRR180 estimates could be biased.
7. **Unmeasured covariates.** The dataset contains no training volume, sport, medication, caffeine, time of day or body composition, so residual confounding is likely.
8. **Undocumented ID conventions.** Test-order inference for the "first test" sensitivity analysis relies on the numeric suffix of `ID_test`, which is not formally documented.

## 6. Conclusion

In 896 maximal treadmill tests, larger HRR at 60, 120 and 180 s was associated with higher relative peak VO2 after adjustment for age, sex and BMI. The association grew stronger with longer recovery intervals and survived every sensitivity analysis examined.

HRR is a modest, robust correlate of aerobic capacity in this athletic cohort. Its value depends heavily on careful event detection and HR artefact handling, and it does not replace direct VO2 measurement.

---

## Figures and tables

| Item | File (under `outputs/project1/`) |
|---|---|
| Figure 1 — Event detection on representative ramp and step tests | `figures/fig1_event_detection_traces.png` |
| Figure 2 — Distributions in the analysis sample | `figures/fig2_distributions.png` |
| Figure 3 — HRR vs VO2peak scatterplots | `figures/fig3_hrr_vs_vo2_scatter.png` |
| Figure 4 — Forest plot of adjusted estimates across analyses | `figures/fig4_forest_adjusted_estimates.png` |
| Figure 5 — Sample flow | `figures/fig5_sample_flow.png` |
| Figure 6 — Model diagnostics | `figures/fig6_model_diagnostics.png` |
| Table 1 — Characteristics | `tables/table1_characteristics.csv` |
| Table 2 — Correlations and adjusted models | `tables/table2_correlations_and_models.csv` |
| Full coefficients · diagnostics · interval comparison · sensitivity · exclusions | `tables/*.csv` |

## References

*Verify each reference against the original source before submission.*

- Buchheit M, Papelier Y, Laursen PB, Ahmaidi S. Noninvasive assessment of cardiac parasympathetic function: post-exercise heart rate recovery or heart rate variability? *Am J Physiol Heart Circ Physiol.* 2007;293:H8–H10.
- Cole CR, Blackstone EH, Pashkow FJ, Snader CE, Lauer MS. Heart-rate recovery immediately after exercise as a predictor of mortality. *N Engl J Med.* 1999;341:1351–1357.
- Daanen HAM, Lamberts RP, Kallen VL, Jin A, Van Meeteren NLU. A systematic review on heart-rate recovery to monitor changes in training status in athletes. *Int J Sports Physiol Perform.* 2012;7:251–260.
- Goldberger AL, et al. PhysioBank, PhysioToolkit, and PhysioNet. *Circulation.* 2000;101:e215–e220.
- Imai K, Sato H, Hori M, et al. Vagally mediated heart rate recovery after exercise is accelerated in athletes but blunted in patients with chronic heart failure. *J Am Coll Cardiol.* 1994;24:1529–1535.
- Mongin D, García Romero J, Alvero Cruz JR. Treadmill Maximal Exercise Tests from the Exercise Physiology and Human Performance Lab of the University of Malaga (version 1.0.1). *PhysioNet.* 2021. https://doi.org/10.13026/7ezk-j442
- Mongin D, Chabert C, Courvoisier DS, García-Romero J, Alvero-Cruz JR. Heart rate recovery to assess fitness: comparison of different calculation methods in a large cross-sectional study. *Res Sports Med.* 2021. *(The original study behind this dataset. Read it and compare its HRR definitions with ours in the Discussion.)*
- Robergs RA, Dwyer D, Astorino T. Recommendations for improved data processing from expired gas analysis indirect calorimetry. *Sports Med.* 2010;40:95–111.
