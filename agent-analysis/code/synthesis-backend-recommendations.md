# Synthesis: Backend Engineer Recommendations

**For:** Backend Engineer (claude-sonnet-4-6)
**From:** Code Analyst (claude-sonnet-4-6)
**Date:** 2026-04-06
**Context:** CES substitution model with stress-testing for Brent oil / renewable investment project

---

## Executive Summary

Of the four flagged codebases, only one (Usher et al. esom_gsa) has open-source
code. The others are academic papers from which implementation blueprints have
been extracted. The Backend Engineer should build a Python library with four
submodules, drawing on reusable patterns from each source.

---

## Recommended Package Architecture

```
ces_model/                     # top-level package
  __init__.py
  core/
    ces.py                     -- CES substitution function (from 035 analysis)
    marginal_cost.py           -- MarginalCostModel (from 035 analysis, optional)
  volatility/
    garch.py                   -- GARCH family wrappers (from 014 analysis)
    xgb_vol.py                 -- XGBoost + SHAP predictor (from 014 analysis)
    features.py                -- log-return, vol proxy, macro feature pipeline
    evaluate.py                -- RMSE, MAE, MMEO, MMEU metrics
    regimes.py                 -- map vol forecasts -> stress regime labels
  sensitivity/
    problem.py                 -- SALib problem builder (adapted from 059 utils.py)
    sampler.py                 -- Morris sampler (adapted from 059 create_sample.py)
    expander.py                -- parameter expansion (adapted from 059 expand_sample.py)
    runner.py                  -- run CES model for each Morris sample row
    analyser.py                -- SALib analyze.morris + CSV/PNG output (from 059)
  scenarios/
    ngfs.py                    -- NGFS Phase V scenario oil price paths
    iea.py                     -- IEA STEPS/APS/NZE price paths
    custom.py                  -- user-defined scenario support
  notebooks/
    01_ces_baseline.ipynb
    02_sensitivity_analysis.ipynb
    03_stress_testing.ipynb
```

---

## Module-by-Module Build Instructions

### 1. `core/ces.py` -- CES Substitution (PRIORITY 1)

**Source:** Mercure/Salas (035) mathematical framework + Papageorgiou (030) parameters

Implement `ces_substitution(price_oil, price_renew, elasticity_sigma, alpha)`.
See full blueprint in `035-mercure-salas-fttpower-analysis.md`, Section 6.

**Key parameter values from research:**
- `elasticity_sigma = 1.8` (Papageorgiou et al. 2017, electricity sector)
- `alpha` = calibrated to observed 2024 renewable share (~30% of new capacity)
- Empirical anchor: 1% rise in oil price -> 0.16% rise in renewable consumption
  (Mukhtarov et al. 2024) -- use to validate alpha calibration

**Test:**
```python
# At parity (price_oil == price_renew), renew_share should equal alpha
result = ces_substitution(100.0, 100.0, sigma=1.8, alpha=0.5)
assert abs(result['renew_share'] - 0.5) < 1e-6

# At oil_price = 2x renew_price, renewable share should exceed 0.5
result = ces_substitution(100.0, 50.0, sigma=1.8, alpha=0.5)
assert result['renew_share'] > 0.5
```

### 2. `sensitivity/` -- Morris Screening (PRIORITY 2)

**Source:** Usher et al. esom_gsa (059) -- MIT licence, directly reusable

Adapt `utils.create_salib_problem()` and `create_sample.py:main()` verbatim
with the following substitutions:
- Replace `parameter['indexes']` with CES model parameter names:
  `{'sigma', 'alpha', 'oil_price_2025', 'oil_price_2035', 'discount_rate', 'renew_capex'}`
- Remove Snakemake dependency; replace with `multiprocessing.Pool` for parallel runs
- Keep `seed=42` for reproducibility

**Parameter ranges for CES model (Backend Engineer to confirm):**
```yaml
# parameters.yaml
parameters:
  - name: sigma
    group: substitution
    min_value: 1.0      # lower bound: near-Leontief
    max_value: 3.0      # upper bound: high substitutability
  - name: oil_price_2025
    group: oil_price
    min_value: 30.0     # NZE stress scenario (Boer et al.)
    max_value: 110.0    # geopolitical shock
  - name: oil_price_2035
    group: oil_price
    min_value: 25.0
    max_value: 130.0
  - name: discount_rate
    group: finance
    min_value: 0.05
    max_value: 0.15
  - name: renew_capex_decline
    group: technology
    min_value: 0.0      # no learning curve
    max_value: 0.5      # 50% cost decline by 2035
```

**Expected run count:** With 5 groups and replicates=10: (5+1)*10 = 60 model runs.
Each CES model run is microseconds; total GSA runtime is negligible.

### 3. `volatility/` -- GARCH and XGBoost (PRIORITY 3)

**Source:** Chung (2024) GARCH/ML paper (014) -- no code, implement from spec

Implement `garch.py` using the `arch` library:
```
arch_model(returns * 100, vol='GARCH', p=1, q=1, dist='t').fit()
```

Implement `xgb_vol.py` using `xgboost` + `shap` for SHAP importance.

The volatility module maps to stress scenario regimes:
```
Low vol (<= P10):   NGFS Current Policies baseline (~$65/bbl)
Medium vol (P10-P75): NGFS Delayed Transition (~$55/bbl)
High vol (> P75):   NGFS Net Zero 2050 / geopolitical shock ($25-$130/bbl)
```

### 4. `scenarios/` -- Price Path Definitions (PRIORITY 4)

Hard-code the four stress scenarios from research findings:
```python
SCENARIOS = {
    'baseline': {
        'name': 'IEA STEPS / NGFS Current Policies',
        'oil_2025': 65.0, 'oil_2030': 68.0, 'vol_regime': 'low',
        'source': 'IEA STEO March 2026; World Bank CMO'
    },
    'moderate_stress': {
        'name': 'IEA APS / NGFS Delayed Transition',
        'oil_2025': 60.0, 'oil_2030': 55.0, 'vol_regime': 'medium',
        'source': 'IEA WEO 2024 APS scenario'
    },
    'severe_stress': {
        'name': 'IEA NZE / NGFS Net Zero 2050',
        'oil_2025': 55.0, 'oil_2030': 25.0, 'vol_regime': 'high',
        'source': 'Boer, Pescatori, Stuermer IMF WP 23/160'
    },
    'upside_shock': {
        'name': 'Geopolitical Supply Disruption',
        'oil_2025': 100.0, 'oil_2030': 110.0, 'vol_regime': 'high',
        'source': 'IMF WEO upside risk scenario'
    }
}
```

---

## Critical Architectural Decisions

### Decision 1: LSTM vs GARCH for Scenario Generation
**Recommendation: GARCH + NGFS paths, not LSTM.**
- LSTM fails during sharp volatility (entry 012 self-reports this limitation)
- GARCH(1,1) provides conditional volatility with distributional uncertainty
- NGFS/IEA scenarios provide externally validated price levels
- LSTM is OPTIONAL as a benchmarking tool only

### Decision 2: Snakemake vs multiprocessing for GSA parallelism
**Recommendation: multiprocessing.Pool for the library.**
- Snakemake adds complexity and HPC-specific dependencies
- For 60 CES model runs (each microseconds), multiprocessing is sufficient
- Snakemake is appropriate only if model runs become computationally expensive
  (e.g., if CES is embedded in a larger OSeMOSYS-style optimisation model)

### Decision 3: Endogenous vs exogenous oil prices
**Recommendation: Exogenous (NGFS/IEA scenarios) for stress tests.**
- MarginalCostModel (from 035) is theoretically elegant but adds complexity
- The 10-year horizon (2025-2035) is too short for depletion effects to dominate
- Use MarginalCostModel as an OPTIONAL sensitivity check, not the main driver

### Decision 4: CES sigma parameterisation
**Use Papageorgiou et al. (2017) sigma=1.8 as baseline.**
- Validated on 26-country panel; electricity sector specifically
- Supported by Mukhtarov et al. (2024) 0.16% coefficient (consistent with sigma~1.8)
- Explore sigma range [1.0, 3.0] in Morris screening

---

## Security and Quality Notes

1. **MinMaxScaler fit-on-train only** (from LSTM analysis): Scaler must be fitted
   on training data and applied (not re-fitted) on test/scenario data.
2. **Seed for reproducibility**: All stochastic components (Morris sampler, any
   ML train/test splits) must use a fixed, documented seed.
3. **Parameter bounds validation**: Create guards (as in esom_gsa utils.py)
   ensuring num_vars >= 2 and num_groups >= 2 before Morris sampling.
4. **No hardcoded paths**: All file paths through configuration (YAML), not
   hardcoded strings.
5. **Type hints on all signatures**: Per CLAUDE.md project style guide.
6. **Line length 88**: Per CLAUDE.md (Ruff configuration).

---

## Dependency Summary

```
# Required
numpy>=1.24
pandas>=2.0
scipy>=1.10
SALib>=1.4       # MIT -- esom_gsa pattern directly reusable

# Volatility module
arch>=5.0        # BSD
xgboost>=1.7     # Apache 2.0
shap>=0.42       # MIT

# Visualisation
matplotlib>=3.7  # BSD

# Optional (LSTM)
torch>=2.0       # BSD

# Development
ruff             # Rust-based linter (CLAUDE.md requirement)
pytest>=7.0
uv               # Package manager (CLAUDE.md requirement)
```

All licences are permissive. No GPL dependencies.

---

## Files Produced by Code Analyst

1. `059-usher-esom-gsa-analysis.md` -- Full annotated analysis of esom_gsa
2. `014-garch-ml-volatility-analysis.md` -- GARCH/ML methodology blueprint
3. `012-lstm-brent-analysis.md` -- LSTM architecture and limitations
4. `035-mercure-salas-fttpower-analysis.md` -- FTT:Power framework and CES integration
5. `index.md` -- This index
6. `synthesis-backend-recommendations.md` -- This file

**Status:** Complete. All four flagged codebases analysed.
