# Research Findings Summary

**Project:** Brent Crude Oil Prices and Renewable Energy Investment Analysis
**Date:** 2026-04-06
**Researcher:** Researcher agent (claude-sonnet-4-6)

---

## Scope

This summary covers research across four topics relevant to the project objective of analysing
how changes in Brent crude oil prices affect long-term growth of renewable energy investment,
stress-tested with macroeconomic scenarios and grounded in microeconomic modelling.

---

## Topic 1: Brent Crude Oil Price Trends and Forecasts

**File:** agent-findings/01-brent-crude-oil-prices.md
**Source count:** 15

**Key findings:**
- Primary historical datasets: EIA monthly Brent spot prices (May 1987-present) and Our World in
  Data inflation-adjusted series (1861-2025). Both are downloadable.
- Current institutional price outlook (2025-2026): World Bank forecasts Brent at $60-68/bbl;
  IMF at $65-69/bbl. EIA STEO (March 2026) provides the most current near-term projections.
- IEA WEO 2024 projects structural oil supply overhang emerging late 2020s with spare capacity
  rising to 8 mb/d by 2030, pointing to sustained downward price pressure -- a critical input
  for stress scenario design.
- Key methodological papers: Hamilton (2008) for fundamentals; Kilian (2009) for structural VAR
  shock decomposition; arXiv papers for LSTM and GARCH-ML forecasting.

**Recommended baseline data sources for the model:**
- EIA daily/monthly Brent spot prices (eia.gov/dnav/pet/hist/rbrtem.htm)
- World Bank Commodity Markets Outlook for forward price assumptions
- IMF WEO for macro-consistent price paths

---

## Topic 2: Renewable Energy Investment Trends

**File:** agent-findings/02-renewable-energy-investment.md
**Source count:** 14

**Key findings:**
- Global renewable investment hit $807 billion in 2024 (IRENA/CPI), dominated by solar at 69%
  of the total. BloombergNEF records total energy transition investment at $2.3 trillion in 2025
  (up 8%), led by electrified transport.
- IEA projects global energy investment reaching $3.3 trillion in 2025 with clean energy at 2:1
  ratio to fossil fuels. Clean energy spending is now a structurally dominant investment category.
- Growth is decelerating: renewable investment grew only 7.3% in 2024 vs. 32% in 2023, and China
  saw its first renewable funding decline since 2013 in 2025.
- IEA Renewables 2024 projects capacity additions rising from 666 GW (2024) to 935 GW by 2030.
- Regional disparities persist: cost-of-capital barriers in emerging markets are a primary
  constraint, per World Bank RISE 2024 and academic literature.

**Recommended data series for the model:**
- IRENA Renewable Capacity Statistics 2025 (capacity by country/technology)
- IEA World Energy Investment 2024/2025 (investment flows by category)
- BloombergNEF Energy Transition Investment Trends 2025 (abridged PDF publicly accessible)

---

## Topic 3: Microeconomic Models Linking Oil Prices to Renewable Substitution

**File:** agent-findings/03-oil-price-renewable-substitution-models.md
**Source count:** 15

**Key findings:**
- Substitution elasticity between clean and dirty energy: Papageorgiou et al. (2017) find the
  macroeconomic elasticity exceeds 1 (~1.8 in electricity sectors), indicating gross
  substitutability. This is the central parameter for the core model.
- Oil price effect on renewable consumption: Mukhtarov et al. (2024) estimate a 1% increase in
  oil prices raises renewable energy consumption by 0.16% in China (canonical cointegrating
  regression). This is a key empirically-grounded coefficient.
- Shock decomposition matters: Esmaeili et al. (2024) show oil-specific demand shocks (vs. supply
  shocks) have the strongest positive effect on clean energy adoption. Kilian (2009) structural
  VAR framework is the baseline for this decomposition.
- Oil price uncertainty (rather than level) is an important driver: Zaghdoudi (2024) finds
  uncertainty has a symmetric negative long-run effect on renewable R&D investment regardless of
  direction -- relevant for stress test design.
- Non-linearity: 71-country panel (2025) documents an N-shaped nonlinear relationship between
  oil price uncertainty and energy transition. NARDL/ARDL methodology is the dominant empirical
  approach.
- Endogenous substitution models: Stockl (2020) provides a growth model where substitutability
  itself is endogenous through investment -- relevant if the project wants a richer structural
  foundation.

**Model recommendations:**
- Use Papageorgiou et al. elasticity parameters as the baseline for the substitution function
- Use Mukhtarov et al. coefficient as empirical calibration anchor
- Consider NARDL or canonical cointegrating regression as the estimation strategy
- Incorporate Kilian shock decomposition to distinguish demand vs. supply oil price effects

---

## Topic 4: Stress Testing Methodologies for Energy Economics

**File:** agent-findings/04-stress-testing-energy-economics.md
**Source count:** 15

**Key findings:**
- NGFS Phase V scenarios (November 2024) are the canonical framework for climate/energy
  transition stress tests. The suite includes: Net Zero 2050, Below 2C, Delayed Transition,
  Divergent Net Zero, Nationally Determined Contributions, Current Policies.
- IEA's three scenarios -- STEPS, APS, NZE -- provide energy-sector-specific benchmarks.
  These map well onto the NGFS framework and are easier to parameterize for an energy model.
- IMF WP 23/160 (Boer, Pescatori, Stuermer 2023) is the most directly relevant paper: it shows
  demand-side vs. supply-side climate policies produce Brent price paths ranging from $25 to
  $130/barrel by 2030, providing ready-made stress scenario oil price trajectories.
- The ECB's 2023 stress test (Occasional Paper 328) is the most methodologically complete
  operational framework; the DNB 2018 paper (Vermeulen et al.) is the pioneering energy-sector
  stress test and the most useful methodological template for this project.
- For sensitivity analysis within the model: Usher et al. (2023) provide a global sensitivity
  analysis methodology (Morris method) validated for energy system models.

**Recommended scenario design for the project:**
- Baseline: IEA STEPS / NGFS Current Policies (oil price ~$65-68/bbl through 2030)
- Moderate stress: IEA APS / NGFS Delayed Transition (demand erosion but no price collapse)
- Severe stress: IEA NZE / NGFS Net Zero 2050 (Boer et al. $25/bbl supply-side scenario)
- Upside shock: IMF WEO oil price shock (geopolitical/supply disruption, $100+/bbl)

---

## Sources Forwarded to Curator

All 59 sources documented in the four topic files have been forwarded to the Curator agent for
fetching and cataloguing. Links were grouped by topic.

---

## Gaps and Recommendations

1. **BloombergNEF data:** Full NEF datasets are behind a paywall. The abridged 2025 PDF is
   publicly accessible. Data Analyst may need to work from summary statistics.
2. **Time series alignment:** Brent price data starts May 1987 on EIA; renewable investment data
   is sparse before 2000. The econometric model may be best calibrated on 2000-2024.
3. **Elasticity variation by region:** Most substitution elasticity studies are China-centric.
   A global model may need to rely on Papageorgiou et al. (26 countries) as the cross-country
   estimate.
4. **Python implementation:** The arXiv papers (LSTM, GARCH, FTT:Power model) provide code
   references; Backend Engineer should check GitHub repos for existing implementations before
   building from scratch.
