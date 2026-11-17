"""Project 1 — Heart-rate recovery and peak VO2.

Run from the project root (after `python src/prep.py`):
    python src/project1_hrr_vo2.py

Primary analysis
    Unit: exercise test (ID_test), all ages, tests with valid peak VO2 and HRR_t.
    Model: OLS  VO2peak_rel ~ HRR_t + Age + female + BMI, with participant-clustered
           (ID) robust standard errors, fitted separately for t = 60, 120, 180 s.
    HRR60 is the primary exposure; HRR120/180 secondary. Holm correction across the
    three is reported alongside unadjusted p-values.

Outputs go to outputs/project1/{tables,figures}.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from matplotlib.patches import FancyBboxPatch
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.outliers_influence import variance_inflation_factor

from prep import DATA, DEFINITIONS, PROCESSED, ROOT, clean_measures

OUT = ROOT / "outputs" / "project1"
FIG = OUT / "figures"
TAB = OUT / "tables"
TARGETS = DEFINITIONS["recovery_targets_s"]
OUTCOME = "VO2peak_rel"
COVARS = "Age + female + BMI"

# ---------------------------------------------------------------------------
# Plot style (validated categorical slots 1-3; recessive axes/grid)
# ---------------------------------------------------------------------------
PAL = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a",
     "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#8a8984", "grid": "#e4e3df",
     "surface": "#fcfcfb"}
HRR_COLOR = {60: PAL["blue"], 120: PAL["orange"], 180: PAL["aqua"]}
plt.rcParams.update({
    "figure.facecolor": PAL["surface"], "axes.facecolor": PAL["surface"],
    "savefig.facecolor": PAL["surface"], "font.size": 10, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.edgecolor": PAL["muted"], "axes.labelcolor": PAL["ink2"],
    "xtick.color": PAL["ink2"], "ytick.color": PAL["ink2"], "text.color": PAL["ink"],
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": PAL["grid"], "grid.linewidth": 0.8,
    "legend.frameon": False, "axes.axisbelow": True, "figure.dpi": 110, "savefig.dpi": 200,
})


def savefig(fig, name):
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Sample selection
# ---------------------------------------------------------------------------
def sample_flow(t: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Sequential exclusions for the primary (HRR60) analysis sample."""
    steps = [("All tests in dataset", pd.Series(True, index=t.index))]
    keep = pd.Series(True, index=t.index)
    rules = [
        ("No VO2 data recorded", t["VO2peak_rel"].isna()),
        ("End-exercise HR signal loss (artefact rule)", t["HR_end_artefact"]),
        ("No HR within ±10 s of 60 s recovery", t["HRR60"].isna()),
    ]
    log = [dict(step="All tests in dataset", excluded=0, tests=len(t), participants=t["ID"].nunique())]
    for label, bad in rules:
        drop = keep & bad
        keep = keep & ~bad
        log.append(dict(step=label, excluded=int(drop.sum()), tests=int(keep.sum()),
                        participants=int(t.loc[keep, "ID"].nunique())))
    return t[keep].copy(), log


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------
def describe_continuous(s: pd.Series, skewed: bool, dp: int = 1) -> str:
    s = s.dropna()
    if skewed:
        q1, q3 = s.quantile([0.25, 0.75])
        return f"{s.median():.{dp}f} [{q1:.{dp}f}–{q3:.{dp}f}]"
    return f"{s.mean():.{dp}f} ± {s.std():.{dp}f}"


def table1(d: pd.DataFrame) -> pd.DataFrame:
    """Mean ± SD, or median [IQR] when |skew| > 1 in the overall sample (same format across columns)."""
    rows = [
        ("Age (years)", "Age", 1), ("Height (cm)", "Height", 1), ("Body mass (kg)", "Weight", 1),
        ("BMI (kg/m²)", "BMI", 1), ("Peak VO2 (mL·kg⁻¹·min⁻¹)", "VO2peak_rel", 1),
        ("Peak VO2 (L/min)", "VO2peak_L_min", 2), ("RER at peak VO2", "RER_at_peak", 2),
        ("Peak HR (bpm)", "HR_peak", 1), ("Peak HR (% age-predicted)", "HR_peak_pct_pred", 1),
        ("HR at end exercise (bpm)", "HR_end", 1), ("HRR60 (bpm)", "HRR60", 1),
        ("HRR120 (bpm)", "HRR120", 1), ("HRR180 (bpm)", "HRR180", 1),
        ("Exercise duration (s)", "t_end_s", 0), ("Peak treadmill speed (km/h)", "peak_speed_kmh", 1),
    ]
    skewed = {v: abs(stats.skew(d[v].dropna())) > 1 for _, v, _ in rows}
    groups = {"Overall": d, "Male": d[d.female == 0], "Female": d[d.female == 1]}
    out = {"Characteristic": ["Tests, n", "Participants, n", "Adults ≥18 y, n (%)",
                              "Ramp protocol, n (%)", "Active recovery, n (%)"]
           + [lab + (", median [IQR]" if skewed[v] else ", mean ± SD") for lab, v, _ in rows]}
    for name, g in groups.items():
        col = [str(len(g)), str(g["ID"].nunique()),
               f"{g['adult'].sum()} ({100 * g['adult'].mean():.0f}%)",
               f"{(g['protocol'] == 'ramp').sum()} ({100 * (g['protocol'] == 'ramp').mean():.0f}%)",
               f"{g['active_recovery'].sum()} ({100 * g['active_recovery'].mean():.0f}%)"]
        col += [describe_continuous(g[v], skewed[v], dp) for _, v, dp in rows]
        out[name] = col
    return pd.DataFrame(out)


def compare_intervals(d: pd.DataFrame, n_boot: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Secondary Q1: which interval is most strongly associated with peak VO2?

    On the common sample with all three HRR values, compute the partial correlation
    of each HRR with peak VO2 (adjusted for age, sex, BMI) and bootstrap the pairwise
    differences, resampling participants (not tests) to respect clustering.
    """
    cols = ["HRR60", "HRR120", "HRR180"]
    dd = d.dropna(subset=cols + [OUTCOME, "Age", "BMI", "female"]).reset_index(drop=True)
    Z = np.column_stack([np.ones(len(dd)), dd[["Age", "female", "BMI"]].to_numpy()])

    def partial_rs(idx):
        z = Z[idx]
        resid = lambda v: v - z @ np.linalg.lstsq(z, v, rcond=None)[0]
        ry = resid(dd[OUTCOME].to_numpy()[idx])
        return np.array([np.corrcoef(resid(dd[c].to_numpy()[idx]), ry)[0, 1] for c in cols])

    est = partial_rs(np.arange(len(dd)))
    groups = dd.groupby("ID").indices
    ids = np.array(list(groups))
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        pick = rng.choice(ids, size=len(ids), replace=True)
        boots.append(partial_rs(np.concatenate([groups[i] for i in pick])))
    boots = np.array(boots)
    rows = [dict(comparison=f"partial r {c}", estimate=est[i],
                 lo=np.percentile(boots[:, i], 2.5), hi=np.percentile(boots[:, i], 97.5))
            for i, c in enumerate(cols)]
    for a, b in [(1, 0), (2, 0), (2, 1)]:
        diff = boots[:, a] - boots[:, b]
        rows.append(dict(comparison=f"{cols[a]} − {cols[b]}", estimate=est[a] - est[b],
                         lo=np.percentile(diff, 2.5), hi=np.percentile(diff, 97.5)))
    out = pd.DataFrame(rows)
    out["n_tests"] = len(dd)
    out["n_participants"] = dd["ID"].nunique()
    return out


def pearson_ci(r, n, alpha=0.05):
    z = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    zc = stats.norm.ppf(1 - alpha / 2)
    return np.tanh(z - zc * se), np.tanh(z + zc * se)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def fit_model(d, hrr_col, outcome=OUTCOME, covars=COVARS, method="cluster"):
    """Return dict of estimates for the HRR term (per 10 bpm and per SD)."""
    dd = d.dropna(subset=[hrr_col, outcome, "Age", "BMI", "female"]).copy()
    sd = dd[hrr_col].std()
    dd["x10"] = dd[hrr_col] / 10.0
    formula = f"{outcome} ~ x10" + (f" + {covars}" if covars else "")
    if method == "cluster":
        res = smf.ols(formula, dd).fit(cov_type="cluster", cov_kwds={"groups": dd["ID"]})
    elif method == "ols":
        res = smf.ols(formula, dd).fit()
    elif method == "mixed":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = smf.mixedlm(formula, dd, groups=dd["ID"]).fit(reml=True)
    else:
        raise ValueError(method)
    b, se, p = res.params["x10"], res.bse["x10"], res.pvalues["x10"]
    lo, hi = res.conf_int().loc["x10"]
    k = sd / 10.0  # rescale per-10-bpm -> per-SD
    return dict(n_tests=len(dd), n_participants=dd["ID"].nunique(),
                b_per10=b, lo_per10=lo, hi_per10=hi,
                b_perSD=b * k, lo_perSD=lo * k, hi_perSD=hi * k, sd_hrr=sd,
                p=p, r2=getattr(res, "rsquared", np.nan), res=res, data=dd)


def diagnostics(fit) -> dict:
    res, dd = fit["res"], fit["data"]
    X = res.model.exog
    infl = res.get_influence()
    cooks = infl.cooks_distance[0]
    bp = het_breuschpagan(res.resid, X)
    names = res.model.exog_names
    vifs = {n: variance_inflation_factor(X, i) for i, n in enumerate(names) if n != "Intercept"}
    return dict(n=len(dd), r2=res.rsquared, adj_r2=res.rsquared_adj,
                resid_skew=stats.skew(res.resid), resid_kurtosis=stats.kurtosis(res.resid),
                breusch_pagan_p=bp[1], max_cooks=cooks.max(),
                n_cooks_gt_4_over_n=int((cooks > 4 / len(dd)).sum()),
                max_VIF=max(vifs.values()),
                VIFs="; ".join(f"{k}={v:.2f}" for k, v in vifs.items()))


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def fig_trace(t: pd.DataFrame, measures: pd.DataFrame, test_ids: list[str]):
    """Speed and HR on separate stacked panels (no dual axis) with detected events."""
    fig, axes = plt.subplots(2, len(test_ids), figsize=(6 * len(test_ids), 5.6),
                             sharex="col", gridspec_kw={"height_ratios": [1, 1.6]})
    for j, tid in enumerate(test_ids):
        g = measures[measures.ID_test == tid]
        r = t.set_index("ID_test").loc[tid]
        te = r["t_end_s"]
        a1, a2 = axes[0, j], axes[1, j]
        a1.plot(g.time, g.Speed, color=PAL["ink2"], lw=2)
        a1.set_ylabel("Speed (km/h)")
        a1.set_title(f"Test {tid} — {r['protocol']} protocol", loc="left")
        a2.plot(g.time, g.HR, color=PAL["blue"], lw=1.2, alpha=0.9, label="HR (breath-aligned)")
        for a in (a1, a2):
            a.axvspan(te, g.time.max(), color=PAL["grid"], alpha=0.6, lw=0)
            a.axvline(te, color=PAL["ink"], lw=1, ls="--")
        a1.text(te - 8, 0.06, "end exercise ▸", transform=a1.get_xaxis_transform(),
                ha="right", va="bottom", color=PAL["ink2"], fontsize=9)
        a1.text(te + 8, 0.06, "recovery", transform=a1.get_xaxis_transform(),
                ha="left", va="bottom", color=PAL["ink2"], fontsize=9)
        a2.plot([te], [r["HR_end"]], "o", ms=8, color=PAL["ink"], mec=PAL["surface"], mew=2, zorder=5)
        a2.annotate(f"HR_end {r['HR_end']:.0f}", (te, r["HR_end"]), xytext=(-10, 8),
                    textcoords="offset points", ha="right", fontsize=9, color=PAL["ink"])
        for s in TARGETS:
            hr_s = r[f"HR_{s}"]
            if np.isnan(hr_s):
                continue
            x = te + s + r[f"HR_{s}_offset_s"]
            a2.plot([x], [hr_s], "o", ms=8, color=HRR_COLOR[s], mec=PAL["surface"], mew=2, zorder=5)
            a2.annotate(f"+{s}s: HRR {r[f'HRR{s}']:.0f}", (x, hr_s), xytext=(6, 6),
                        textcoords="offset points", fontsize=9, color=PAL["ink"])
        a2.set_ylabel("Heart rate (bpm)")
        a2.set_xlabel("Time since recording start (s)")
    fig.suptitle("Event detection: end exercise = last sample at peak treadmill speed; "
                 "recovery HR = nearest despiked HR within ±10 s of target",
                 x=0.01, ha="left", fontsize=10, color=PAL["ink2"])
    fig.tight_layout()
    savefig(fig, "fig1_event_detection_traces")


def fig_distributions(d: pd.DataFrame):
    panels = [("VO2peak_rel", "Peak VO2 (mL·kg⁻¹·min⁻¹)", PAL["ink2"]),
              ("HRR60", "HRR60 (bpm)", HRR_COLOR[60]),
              ("HRR120", "HRR120 (bpm)", HRR_COLOR[120]),
              ("HRR180", "HRR180 (bpm)", HRR_COLOR[180]),
              ("Age", "Age (years)", PAL["ink2"]), ("BMI", "BMI (kg/m²)", PAL["ink2"])]
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.5))
    for a, (col, lab, colr) in zip(axes.flat, panels):
        s = d[col].dropna()
        a.hist(s, bins=30, color=colr, edgecolor=PAL["surface"], linewidth=1)
        a.set_title(lab)
        a.set_xlabel(lab)
        a.set_ylabel("Tests")
        a.text(0.98, 0.95, f"n = {len(s)}\nmedian {s.median():.1f}", transform=a.transAxes,
               ha="right", va="top", fontsize=9, color=PAL["ink2"])
    fig.suptitle("Distributions in the analysis sample", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    savefig(fig, "fig2_distributions")


def fig_scatter(d: pd.DataFrame, corr: pd.DataFrame):
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6), sharey=True)
    for a, s in zip(axes, TARGETS):
        dd = d.dropna(subset=[f"HRR{s}", OUTCOME])
        x, y = dd[f"HRR{s}"], dd[OUTCOME]
        a.scatter(x, y, s=14, color=HRR_COLOR[s], alpha=0.45, edgecolor="none")
        slope, icpt = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 50)
        a.plot(xs, icpt + slope * xs, color=PAL["ink"], lw=2)
        c = corr.set_index("exposure").loc[f"HRR{s}"]
        a.set_title(f"HRR{s}")
        a.text(0.03, 0.97, f"n = {len(dd)}\nPearson r = {c['pearson_r']:.2f} "
               f"[{c['pearson_lo']:.2f}, {c['pearson_hi']:.2f}]\nSpearman ρ = {c['spearman_rho']:.2f}",
               transform=a.transAxes, va="top", fontsize=9, color=PAL["ink2"])
        a.set_xlabel(f"HRR{s} (bpm drop from end exercise)")
    axes[0].set_ylabel("Peak VO2 (mL·kg⁻¹·min⁻¹)")
    fig.suptitle("Unadjusted association of heart-rate recovery with peak VO2 (one dot = one test; line = OLS fit)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    savefig(fig, "fig3_hrr_vs_vo2_scatter")


def fig_forest(sens: pd.DataFrame):
    labels = list(dict.fromkeys(sens["analysis"]))
    fig, ax = plt.subplots(figsize=(9.5, 0.5 * len(labels) + 1.6))
    offsets = {60: -0.22, 120: 0.0, 180: 0.22}
    for s in TARGETS:
        sub = sens[sens.exposure == f"HRR{s}"].set_index("analysis").reindex(labels)
        ys = np.arange(len(labels))[::-1] + offsets[s]
        ax.hlines(ys, sub.lo_perSD, sub.hi_perSD, color=HRR_COLOR[s], lw=2)
        ax.plot(sub.b_perSD, ys, "o", ms=7, color=HRR_COLOR[s], mec=PAL["surface"], mew=1.5,
                label=f"HRR{s}")
    ax.axvline(0, color=PAL["ink2"], lw=1)
    ax.set_yticks(np.arange(len(labels))[::-1])
    ax.set_yticklabels(labels)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Adjusted difference in peak VO2 per 1 SD higher HRR (mL·kg⁻¹·min⁻¹), 95% CI")
    ax.legend(loc="lower right", ncol=3, bbox_to_anchor=(1, 1.0))
    ax.set_title("Adjusted associations (age, sex, BMI) — primary and sensitivity analyses", pad=26)
    fig.tight_layout()
    savefig(fig, "fig4_forest_adjusted_estimates")


def fig_flow(log: list[dict], extra: list[str]):
    fig, ax = plt.subplots(figsize=(8.5, 1.55 * len(log) + 0.6))
    ax.set_axis_off()
    n = len(log)
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.6, n * 2)
    for i, step in enumerate(log):
        y = (n - i) * 2 - 1.3
        text = (f"{step['tests']} tests · {step['participants']} participants" if i else
                f"{step['step']}\n{step['tests']} tests · {step['participants']} participants")
        if i == n - 1:
            text = f"Primary analysis sample (HRR60)\n{text}"
        box = FancyBboxPatch((0.4, y - 0.5), 4.8, 1.0, boxstyle="round,pad=0.05,rounding_size=0.15",
                             fc=PAL["surface"], ec=PAL["blue"] if i == n - 1 else PAL["ink2"], lw=1.5)
        ax.add_patch(box)
        ax.text(2.8, y, text, ha="center", va="center", fontsize=9.5)
        if i < n - 1:
            nxt = log[i + 1]
            ax.annotate("", xy=(2.8, y - 1.5), xytext=(2.8, y - 0.55),
                        arrowprops=dict(arrowstyle="-|>", color=PAL["ink2"], lw=1.2))
            ax.annotate("", xy=(5.6, y - 1.0), xytext=(2.8, y - 1.0),
                        arrowprops=dict(arrowstyle="-|>", color=PAL["ink2"], lw=1.2))
            ax.text(5.75, y - 1.0, f"Excluded: {nxt['step']}\n(n = {nxt['excluded']} test{'s' if nxt['excluded'] != 1 else ''})",
                    va="center", fontsize=9, color=PAL["ink2"])
    ax.text(0.4, -0.05, "\n".join(extra), fontsize=8.5, color=PAL["ink2"], va="top")
    ax.set_title("Sample flow", loc="left")
    savefig(fig, "fig5_sample_flow")


def fig_diagnostics(fits: dict):
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5))
    for j, s in enumerate(TARGETS):
        res = fits[s]["res"]
        a = axes[0, j]
        a.scatter(res.fittedvalues, res.resid, s=10, alpha=0.4, color=HRR_COLOR[s], edgecolor="none")
        a.axhline(0, color=PAL["ink2"], lw=1)
        a.set_title(f"HRR{s} model — residuals vs fitted")
        a.set_xlabel("Fitted peak VO2")
        a.set_ylabel("Residual")
        a = axes[1, j]
        (osm, osr), (sl, ic, _) = stats.probplot(res.resid, dist="norm")
        a.scatter(osm, osr, s=10, alpha=0.5, color=HRR_COLOR[s], edgecolor="none")
        a.plot(osm, ic + sl * osm, color=PAL["ink"], lw=1.5)
        a.set_title(f"HRR{s} model — normal Q–Q")
        a.set_xlabel("Theoretical quantile")
        a.set_ylabel("Ordered residual")
    fig.tight_layout()
    savefig(fig, "fig6_model_diagnostics")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    t = pd.read_csv(PROCESSED / "test_level.csv")

    analytic, log = sample_flow(t)
    pd.DataFrame(log).to_csv(TAB / "sample_flow.csv", index=False, encoding="utf-8-sig")
    excl = t[~t.ID_test.isin(analytic.ID_test)].copy()
    excl["reason"] = np.select(
        [excl.VO2peak_rel.isna(), excl.HR_end_artefact, excl.HRR60.isna()],
        ["no VO2 data", "end-exercise HR artefact", "no HR near 60 s"], "other")
    excl[["ID_test", "ID", "reason", "HR_end", "HR_peak", "HR_end_raw"]].to_csv(
        TAB / "exclusion_log.csv", index=False, encoding="utf-8-sig")

    # Compare included vs excluded (on variables available for everyone)
    cmp_rows = []
    for v in ["Age", "BMI", "female", "peak_speed_kmh", "t_end_s"]:
        a, b = analytic[v], excl[v]
        p = stats.mannwhitneyu(a, b).pvalue
        cmp_rows.append(dict(variable=v, included_mean=a.mean(), excluded_mean=b.mean(), mannwhitney_p=p))
    pd.DataFrame(cmp_rows).round(3).to_csv(TAB / "included_vs_excluded.csv", index=False, encoding="utf-8-sig")

    table1(analytic).to_csv(TAB / "table1_characteristics.csv", index=False, encoding="utf-8-sig")

    # Unadjusted correlations
    corr_rows = []
    for s in TARGETS:
        dd = analytic.dropna(subset=[f"HRR{s}", OUTCOME])
        r, p = stats.pearsonr(dd[f"HRR{s}"], dd[OUTCOME])
        lo, hi = pearson_ci(r, len(dd))
        rho, prho = stats.spearmanr(dd[f"HRR{s}"], dd[OUTCOME])
        corr_rows.append(dict(exposure=f"HRR{s}", n=len(dd), pearson_r=r, pearson_lo=lo,
                              pearson_hi=hi, pearson_p=p, spearman_rho=rho, spearman_p=prho))
    corr = pd.DataFrame(corr_rows)

    # Primary adjusted models
    fits = {s: fit_model(analytic, f"HRR{s}") for s in TARGETS}
    unadj = {s: fit_model(analytic, f"HRR{s}", covars="") for s in TARGETS}
    holm = multipletests([fits[s]["p"] for s in TARGETS], method="holm")[1]
    t2 = corr.copy()
    for i, s in enumerate(TARGETS):
        f, u = fits[s], unadj[s]
        t2.loc[i, "unadj_b_per10"] = u["b_per10"]
        t2.loc[i, "unadj_lo"] = u["lo_per10"]
        t2.loc[i, "unadj_hi"] = u["hi_per10"]
        t2.loc[i, "adj_n"] = f["n_tests"]
        t2.loc[i, "adj_participants"] = f["n_participants"]
        t2.loc[i, "adj_b_per10"] = f["b_per10"]
        t2.loc[i, "adj_lo_per10"] = f["lo_per10"]
        t2.loc[i, "adj_hi_per10"] = f["hi_per10"]
        t2.loc[i, "adj_b_perSD"] = f["b_perSD"]
        t2.loc[i, "adj_lo_perSD"] = f["lo_perSD"]
        t2.loc[i, "adj_hi_perSD"] = f["hi_perSD"]
        t2.loc[i, "adj_p"] = f["p"]
        t2.loc[i, "adj_p_holm"] = holm[i]
        t2.loc[i, "adj_R2"] = f["r2"]
    t2.to_csv(TAB / "table2_correlations_and_models.csv", index=False, encoding="utf-8-sig")

    # Full coefficient tables for primary models
    coef_rows = []
    for s in TARGETS:
        res = fits[s]["res"]
        ci = res.conf_int()
        for term in res.params.index:
            coef_rows.append(dict(model=f"HRR{s}", term=term.replace("x10", f"HRR{s} (per 10 bpm)"),
                                  estimate=res.params[term], lo=ci.loc[term, 0], hi=ci.loc[term, 1],
                                  p=res.pvalues[term]))
    pd.DataFrame(coef_rows).to_csv(TAB / "primary_model_coefficients.csv", index=False, encoding="utf-8-sig")

    # Diagnostics (on plain OLS fit of the same model; cluster SEs do not change residuals)
    diag = pd.DataFrame([dict(model=f"HRR{s}", **diagnostics(fit_model(analytic, f"HRR{s}", method="ols")))
                         for s in TARGETS])
    diag.to_csv(TAB / "model_diagnostics.csv", index=False, encoding="utf-8-sig")

    cmp_int = compare_intervals(analytic)
    cmp_int.to_csv(TAB / "interval_comparison_bootstrap.csv", index=False, encoding="utf-8-sig")

    # Sensitivity analyses — each row: (label, data, hrr column suffix, outcome, method, covars)
    base = t[t.VO2peak_rel.notna()]
    first = analytic[analytic.first_test]
    analyses = [
        ("Primary: all tests, cluster-robust SE", analytic, "", OUTCOME, "cluster", COVARS),
        ("Mixed model (random intercept for participant)", analytic, "", OUTCOME, "mixed", COVARS),
        ("One test per participant (first test)", first, "", OUTCOME, "ols", COVARS),
        ("Adults only (≥18 y)", analytic[analytic.adult], "", OUTCOME, "cluster", COVARS),
        ("Peak VO2: highest single breath", analytic, "", "VO2peak_rel_breath", "cluster", COVARS),
        ("Peak VO2: 30-s rolling mean", analytic, "", "VO2peak_rel_30s", "cluster", COVARS),
        ("Recovery HR tolerance ±5 s", analytic, "_strict", OUTCOME, "cluster", COVARS),
        ("Raw HR, nearest obs., no artefact rule", base, "_raw", OUTCOME, "cluster", COVARS),
        ("Raw HR, window means (10 s end / ±5 s)", base, "_window", OUTCOME, "cluster", COVARS),
        ("Active (walking) recovery only", analytic[analytic.active_recovery], "", OUTCOME, "cluster", COVARS),
        ("Met ≥1 maximality criterion", analytic[analytic.max_criterion_met], "", OUTCOME, "cluster", COVARS),
        ("+ protocol (ramp/step) covariate", analytic, "", OUTCOME, "cluster", COVARS + " + C(protocol)"),
        ("+ HR at end exercise covariate (exploratory)", analytic, "", OUTCOME, "cluster", COVARS + " + HR_end"),
        ("Unadjusted", analytic, "", OUTCOME, "cluster", ""),
    ]
    sens_rows = []
    for label, data, suf, outcome, method, cov in analyses:
        for s in TARGETS:
            f = fit_model(data, f"HRR{s}{suf}", outcome=outcome, covars=cov, method=method)
            sens_rows.append(dict(analysis=label, exposure=f"HRR{s}",
                                  **{k: v for k, v in f.items() if k not in ("res", "data")}))
    sens = pd.DataFrame(sens_rows)
    sens.to_csv(TAB / "sensitivity_analyses.csv", index=False, encoding="utf-8-sig")

    # Figures
    m = clean_measures(pd.read_csv(DATA / "test_measure.csv"))
    fig_trace(t, m, ["100_1", "705_1"])
    fig_distributions(analytic)
    fig_scatter(analytic, corr)
    fig_forest(sens[sens.analysis != "Unadjusted"])
    extra = [f"HRR120 available in {analytic.HRR120.notna().sum()} and HRR180 in "
             f"{analytic.HRR180.notna().sum()} of these tests",
             "(HRR180 often missing because recovery recording ended before 170 s)."]
    fig_flow(log, extra)
    fig_diagnostics({s: fit_model(analytic, f"HRR{s}", method="ols") for s in TARGETS})

    # Console summary
    pd.set_option("display.width", 200)
    print(pd.DataFrame(log).to_string(index=False))
    print("\nTable 1\n", table1(analytic).to_string(index=False))
    print("\nTable 2\n", t2.round(3).T.to_string())
    print("\nDiagnostics\n", diag.round(3).T.to_string())
    print("\nSensitivity (per SD)\n",
          sens.pivot(index="analysis", columns="exposure", values="b_perSD").round(2).to_string())
    print("\nSensitivity CI\n", sens.assign(ci=sens.apply(
        lambda r: f"{r.b_perSD:.2f} [{r.lo_perSD:.2f}, {r.hi_perSD:.2f}] n={r.n_tests}", axis=1))
        .pivot(index="analysis", columns="exposure", values="ci").to_string())
    print("\nIncluded vs excluded\n", pd.DataFrame(cmp_rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
