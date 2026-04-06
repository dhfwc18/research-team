# Brent Crude Oil Price Impact on Renewable Energy Investment

An analysis of how changes in Brent crude oil prices affect long-term growth of renewable
energy investment, built on a CES (Constant Elasticity of Substitution) microeconomic model
with macroeconomic stress testing.

## Key Findings

- A 1% rise in Brent crude oil prices is associated with a 0.16% increase in renewable energy
  consumption (Mukhtarov et al. 2024)
- CES substitution elasticity between fossil and renewable energy is 1.8 (Papageorgiou et al. 2017),
  indicating strong substitutability
- Under the Net Zero Emissions scenario ($44/bbl by 2030), renewable investment grows significantly
  faster than under the baseline STEPS scenario ($65/bbl)
- Brent price volatility is 40.1% annualised with fat tails (kurtosis 63.4), making GARCH modelling
  appropriate for stress testing
- Clean energy investment reached 2x fossil fuel investment in 2024

## Project Structure

```
src/ces_model/           Core Python library
  core/                  CES substitution model and investment response
  data/                  EIA Brent price loader and data cleaning
  scenarios/             5 calibrated price paths and stress testing
  sensitivity/           Morris global sensitivity analysis (SALib)
  volatility/            GARCH(1,1) volatility modelling

notebooks/               Jupyter notebooks with executed analysis
  01_model_calibration   CES share curve, alpha calibration, elasticity validation
  02_scenario_analysis   Investment trajectories, fan chart, policy multiplier
  03_sensitivity         Morris GSA results, parameter importance

tests/                   100 unit tests + 64 integration tests (164/164 passing)

agent-report/            Final deliverables
  brent-renewables-report.pptx   23-slide presentation
  brent-renewables-report.pdf    Landscape A4 document
  generate_report.py             Rerunnable report generator

agent-findings/          Research findings (59 sources across 4 topics)
agent-catalogue/         Catalogued resources with metadata
agent-analysis/          Data profiling, visualisations, and code analysis
```

## Model Overview

The core model uses a CES production function to capture substitution between fossil and
renewable energy inputs:

```
s_renewable = alpha * p_fossil^(1 - sigma) / [alpha * p_fossil^(1 - sigma) + (1 - alpha) * p_renewable^(1 - sigma)]
```

Where sigma = 1.8 (substitution elasticity) and alpha is calibrated to a 30% renewable share
at $80/bbl Brent crude. The investment response module translates share changes into investment
trajectories, anchored to the empirical Mukhtarov elasticity.

### Stress Scenarios

| Scenario | 2030 Brent Price | Description |
|---|---|---|
| STEPS | $65/bbl | Stated Policies (baseline) |
| APS | $55/bbl | Announced Pledges |
| NZE | $44/bbl | Net Zero Emissions by 2050 |
| HIGH_SHOCK | $130/bbl | Supply disruption / geopolitical shock |
| LOW_SHOCK | $25/bbl | Demand collapse / oversupply |

## Quick Start

```bash
# Install dependencies
uv sync

# Run the model
uv run python -c "from ces_model.scenarios.stress_test import StressTest; print(StressTest().run())"

# Run tests
uv run pytest

# Regenerate reports
uv run python agent-report/generate_report.py

# Launch notebooks
uv run jupyter lab notebooks/
```

## How This Was Built

This project was produced by a multi-agent research team coordinated through Claude Code agent
teams in tmux split pane mode. Nine agents collaborated across five stages:

| Stage | Agents | Duration | Output |
|---|---|---|---|
| 1. Research | Researcher, Curator | ~35 min | 59 sources found and catalogued |
| 2. Analysis | Data Analyst, Code Analyst | ~25 min | Dataset profiling, 7 figures, codebase review |
| 3. Build | Backend Engineer | ~100 min | Python library, 3 notebooks, 100 unit tests |
| 4. QA | QA Engineer | ~25 min | 64 integration tests, 164/164 passing |
| 5. Report | Reporter | ~12 min | 23-slide PPTX + PDF with watermark |
| **Total** | **8 agents dispatched** | **~3 hr 15 min** | **Full research-to-report pipeline** |

## Licence

See [LICENSE](LICENSE).
