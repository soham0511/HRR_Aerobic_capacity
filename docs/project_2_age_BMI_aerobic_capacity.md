# Project 2 — Age, BMI and aerobic capacity

## Working title
**Age and body-mass index as correlates of peak aerobic capacity in amateur and professional athletes undergoing treadmill exercise testing**

## Why this project
This is the more independent project. It builds on the same dataset but asks you to define and defend a broader epidemiological question. The original idea was to examine age, body composition and aerobic capacity, potentially comparing amateur and professional athletes. The available dataset supports age, height, weight, BMI and cardiorespiratory performance measures. It does not provide direct body-fat percentage, fat-free mass, sport type, training volume or a clear athlete-level amateur/professional classification in the documented metadata. Do not invent these variables or claim to measure body composition directly.

## Primary research question
How are age and BMI associated with peak oxygen uptake (mL·kg⁻¹·min⁻¹) among adults represented in the University of Malaga treadmill-test dataset?

## Secondary questions
1. Does the age–peak VO2 association appear nonlinear?
2. Does the BMI–peak VO2 association differ by sex?
3. Are conclusions similar when peak VO2 is expressed in absolute terms (L/min) rather than relative to body mass (mL·kg⁻¹·min⁻¹)?
4. Do results change when restricting to one test per participant or accounting for repeated tests?

## Hypotheses to consider
- H1: Age is inversely associated with relative peak VO2.
- H2: BMI is associated with relative peak VO2, but interpretation is complicated because relative VO2 is divided by body mass and BMI also contains body mass.
- H3: Age and BMI associations may differ by sex.

You must refine these hypotheses after reviewing literature and checking the data. In particular, be alert to mathematical coupling between BMI and relative VO2. Absolute VO2 (L/min), allometrically scaled VO2, or models including height and mass separately can help assess whether an apparent BMI association is partly a consequence of ratio scaling.

## Dataset and population
Use PhysioNet dataset version 1.0.1. The dataset contains 992 tests from 857 participants, aged 10–63 years. For the primary adult analysis, restrict to age ≥18 years and report how many tests and unique participants remain. A secondary analysis may include all ages only if you have an appropriate rationale and address the distinct physiology and ethics of paediatric participants.

## Exposure and outcome variables
- Main exposures: age (years), BMI (kg/m²).
- Primary outcome: peak relative VO2 (mL·kg⁻¹·min⁻¹), derived from the maximal valid exercise-phase VO2 divided by body mass.
- Secondary outcome: peak absolute VO2 (L/min), calculated from mL/min.
- Potential covariates: sex, height, weight, and any other measured test-context variables justified by a causal/physiological rationale.
- Do not include HR, test duration or peak treadmill speed as covariates automatically. Decide whether they are confounders, mediators, protocol indicators or outcomes for a specific question.

## Athlete status limitation
The dataset description says participants include amateur and professional athletes, but the published variable list does not establish a usable athlete-status field. Inspect the actual metadata before proposing group comparisons. If there is no documented status variable, the amateur-versus-professional comparison is not answerable with this dataset. Reframe around the available cohort; do not infer athlete level from VO2, speed or HR.

## Analysis plan
1. Write a one-page protocol before analysis: target population, primary outcome, exposures, exclusions, hypotheses and model specification.
2. Audit and merge the data; derive BMI and peak VO2 using a documented exercise-phase definition.
3. Describe the adult sample overall and stratified by sex. Report tests and unique participants separately.
4. Plot age versus peak VO2 and BMI versus peak VO2; inspect scatter, outliers and potential nonlinear patterns.
5. Fit a base model with age and sex, then add BMI. Consider restricted cubic splines or another justified nonlinear form for age if visualisation and sample size support it.
6. Test age-by-sex and BMI-by-sex interactions only if prespecified or clearly labelled exploratory.
7. Compare relative and absolute VO2 outcomes. Consider models using height and body mass separately to address ratio scaling and mathematical coupling.
8. Account for repeated tests per participant using mixed-effects models or participant-clustered standard errors. Sensitivity analysis: one test per participant.
9. Report effect sizes with 95% confidence intervals, not only p-values. Evaluate residuals, influential cases, heteroscedasticity and collinearity.
10. Conduct sensitivity analyses for adults-only restriction, peak VO2 definition and missing data.

## Deliverables
- A concise preregistration-style protocol (1–2 pages) written before modelling.
- Reproducible analysis notebook/script.
- Table 1: sample characteristics overall and by sex.
- Figures: age–VO2 relationship, BMI–VO2 relationship, model-predicted age curve, and relative versus absolute VO2 comparison.
- Regression table with estimates, 95% CIs and model diagnostics.
- 2,000–3,000 word manuscript with abstract, introduction, methods, results, discussion, limitations and conclusion.
- A brief reflection explaining which research decisions you made independently and why.

## Interpretation boundaries
This is a selected cohort undergoing maximal treadmill testing, not a representative sample of all athletes. BMI is not a direct body-composition measure. Cross-sectional associations cannot establish ageing-related decline within individuals. Do not interpret a between-person age association as an individual's longitudinal loss of fitness.
