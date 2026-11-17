# Data (not included in this repository)

The source data are licensed under the **PhysioNet Contributor Review Health Data License 1.5.0** and are not redistributed here.

1. Download `subject-info.csv` and `test_measure.csv` from
   https://physionet.org/content/treadmill-exercise-cardioresp/1.0.1/
2. Put both files in this `data/` folder.
3. Run `python src/prep.py`. This creates `data/processed/test_level.csv`.

**Dataset citation:** Mongin D, García Romero J, Alvero Cruz JR. *Treadmill Maximal Exercise Tests from the Exercise Physiology and Human Performance Lab of the University of Malaga* (version 1.0.1). PhysioNet; 2021. https://doi.org/10.13026/7ezk-j442
