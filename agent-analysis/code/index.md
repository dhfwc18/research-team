# Code Analysis Index

**Project:** Brent crude oil prices and renewable energy investment analysis
**Analyst:** Code Analyst (claude-sonnet-4-6)
**Date:** 2026-04-06
**Branch:** example-study

---

## Files in This Directory

| File | Catalogue Entry | Description |
|---|---|---|
| [059-usher-esom-gsa-analysis.md](059-usher-esom-gsa-analysis.md) | 059 | Usher et al. GSA code (MIT) -- Morris screening, SALib, Snakemake |
| [014-garch-ml-volatility-analysis.md](014-garch-ml-volatility-analysis.md) | 014 | Chung (2024) GARCH/ML volatility methodology |
| [012-lstm-brent-analysis.md](012-lstm-brent-analysis.md) | 012 | Zhao et al. LSTM Brent forecasting architecture |
| [035-mercure-salas-fttpower-analysis.md](035-mercure-salas-fttpower-analysis.md) | 035 | Mercure/Salas FTT:Power marginal cost framework |
| [synthesis-backend-recommendations.md](synthesis-backend-recommendations.md) | -- | Cross-codebase synthesis and Backend Engineer recommendations |

---

## Codebase Access Summary

| Entry | Open-Source Code | Language | Licence | Status |
|---|---|---|---|---|
| 059 | YES -- GitHub | Python | MIT | Fully analysed |
| 014 | NO | Python (inferred) | arXiv | Methodology extracted |
| 012 | NO | Python (inferred) | arXiv | Architecture documented |
| 035 | NO | Fortran/Python | Proprietary | Math framework extracted |

Only entry 059 has an open-source codebase. Entries 012, 014, and 035 are
academic papers; implementations are blueprinted from methodology descriptions.

---

## Top Reusable Components (Priority Order)

1. **SALib Morris sampler** (059) -- `create_sample.py` + `utils.py`
   Drop-in for CES model sensitivity analysis. 3 SALib calls needed.

2. **GARCH(1,1) volatility module** (014) -- implement with `arch` library
   Essential for stress scenario volatility regime classification.

3. **XGBoost + SHAP volatility predictor** (014) -- implement with `xgboost`/`shap`
   Outperforms GARCH out-of-sample; SHAP identifies key price drivers.

4. **CES substitution function** (035) -- ~30 lines of pure Python/numpy
   Core microeconomic model. Parameterise with Papageorgiou sigma=1.8.

5. **MarginalCostModel** (035) -- depletion dynamics (optional long-run extension)
   Use only if model horizon extends beyond 2035 or depletion sensitivity needed.

6. **LSTM BrentLSTM** (012) -- benchmarking only, not for stress scenarios

---

## Key Dependencies for Backend Engineer

```
# Core scientific stack (already expected)
numpy>=1.24
pandas>=2.0
scipy>=1.10

# Sensitivity analysis
SALib>=1.4        # MIT -- Morris sampling and analysis

# Volatility modelling
arch>=5.0         # BSD -- GARCH family estimation
xgboost>=1.7      # Apache 2.0 -- gradient boosting
shap>=0.42        # MIT -- TreeSHAP interpretability

# Optional (LSTM component)
torch>=2.0        # BSD -- PyTorch for LSTM

# Visualisation (already in SALib workflow)
matplotlib>=3.7
```

All packages are pip/uv-installable and permissively licenced.
