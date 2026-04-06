---
source_url: https://www.eia.gov/dnav/pet/hist/rbrtem.htm
licence: Public domain (U.S. Government data, no copyright)
date_accessed: 2026-04-06
version: Updated monthly; latest May 1987-present
type: dataset-page
---

# EIA Monthly Brent Crude Oil Spot Price (Historical)

**Organisation:** U.S. Energy Information Administration (EIA)

## Description

Monthly Brent crude oil spot price series from May 1987 to present, maintained by the EIA
under the Petroleum & Other Liquids section. The page renders a data table and chart; Excel
and CSV download options are available via the EIA DNAV interface. Units are dollars per barrel.

Note: The page returned only a header on fetch (likely JavaScript-rendered content). Data is
accessible via the EIA DNAV API and direct Excel download at the same domain.

## Usefulness Assessment

**Relevant** -- Core historical Brent price series for the full study period. Essential
for the microeconomics model and time-series analysis of oil price vs renewable investment.

## Possible Application

- Primary input for the Brent price time series in the Python model
- Basis for structural break and trend analysis
- Benchmarking against other price series (WTI, inflation-adjusted)

## Download Note

Dataset is freely downloadable as Excel/CSV directly from the EIA DNAV interface (file size
negligible -- well under 50MB). Recommend Data Analyst download directly from EIA DNAV API:
`https://api.eia.gov/v2/petroleum/pri/spt/data/` with series `EER_EPCBRENT_PF4_Y35NY_DPB`.

## Flag

**DATA ANALYST:** High-priority dataset. Monthly Brent price series May 1987-present.
