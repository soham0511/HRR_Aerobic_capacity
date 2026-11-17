# Data dictionary and quality-control guide

## Source files

### `subject-info.csv`
One row per exercise test (992 rows in the documented release). `ID` identifies a participant; `ID_test` identifies a particular test. Documented fields include age, weight, height, humidity, temperature and sex. Check the exact column spellings in the downloaded file before coding.

### `test_measure.csv`
One row per breath-by-breath measurement (575,087 rows in the documented release). Fields documented by PhysioNet: `time` (seconds since recording began), `Speed` (km/h), `HR` (beats/min), `VO2` (mL/min), `VCO2` (mL/min), `RR` (breaths/min), `VE` (L/min), `ID`, `ID_test`.

## Important derived measures
- Height_m = height_cm / 100 (if source height is in cm).
- BMI_kg_m2 = weight_kg / height_m².
- Relative VO2 = VO2_mL_min / body_mass_kg (mL·kg⁻¹·min⁻¹).
- Absolute peak VO2 in L/min = peak VO2 in mL/min / 1000.
- HRR_t = HR at end exercise − HR at t seconds into recovery.

## Quality checks
- Confirm unique `ID_test` count and number of unique `ID` values.
- Confirm one metadata row per `ID_test`; check duplicates before merging.
- Join on `ID` and `ID_test`, not `ID` alone.
- Confirm that all test IDs in the time-series file have matching metadata.
- Check plausible ranges and units for age, height, weight, HR, VO2, Speed and time.
- Check monotonicity/order of time within each test; sort by `ID_test`, then `time`.
- Count missing values by variable and by test. Some tests lack VO2/VCO2/VE data.
- Identify tests with repeated or irregular timestamps, very short duration, implausible values or no identifiable recovery phase.
- Plot representative HR and Speed traces. Establish end exercise from the protocol and trace, not from the final recording row.
- Record all exclusions and keep a reproducible exclusion log.

## Sex coding
Use the codebook on the PhysioNet page / source files to map the numeric sex field. Do not assume coding from memory; verify it in the downloaded release and report the mapping.

## Missing data
Do not replace missing physiological measurements with zero. Report missingness, compare included and excluded tests where possible, and justify complete-case analysis or any imputation strategy. Avoid imputing time-series HRR values without a defensible method.
