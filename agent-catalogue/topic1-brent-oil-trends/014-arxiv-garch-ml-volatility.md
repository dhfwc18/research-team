---
source_url: https://arxiv.org/html/2405.19849v1
licence: arXiv standard (CC BY 4.0 or author copyright)
date_accessed: 2026-04-06
version: arXiv:2405.19849v1, May 2024
type: academic-paper-preprint-html
---

# arXiv 2405.19849 -- Energy Market Volatility Using GARCH and Machine Learning

**Author:** Seulki Chung
**Institution:** GSEFM, Department of Empirical Economics, Technische Universitat Darmstadt
**Date:** May 2024

## Description

Comparative study of GARCH-family models and machine learning approaches for energy market
volatility forecasting. Covers daily data 2006-2023 for crude oil, gasoline, heating oil,
and natural gas. GARCH variants tested: GARCH(1,1), EGARCH, GJR-GARCH (univariate and
multivariate BEKK). ML models: linear regression, ridge/lasso/elastic net, Bayesian ridge,
decision trees, random forests, XGBoost, SVM, KNN, MLP. Data sources: EIA, FRED, NASA GISS,
Global Economic Policy Uncertainty Index. Code availability not stated.

## Key Findings

- ML models substantially outperform GARCH in out-of-sample forecasting for most commodities
- GARCH tends to overpredict; ML tends to underestimate
- Volatility transmission flows from crude oil to refined products; natural gas isolated
- XGBoost is the top performer; SHAP analysis reveals key drivers

## Usefulness Assessment

**Relevant** -- Directly applicable to the volatility modelling component of the project.
Provides both methodological guidance and empirical results for crude oil volatility
that can inform the macroeconomic stress-test scenarios.

## Possible Application

- GARCH and ML architecture reference for the Backend Engineer's volatility module
- Volatility estimates for scenario construction (low/medium/high price volatility regimes)
- XGBoost + SHAP framework for feature importance in the renewable investment model

## Flag

**CODE ANALYST:** Full HTML paper available (not PDF). Detailed methodology for GARCH and ML
volatility modelling of crude oil. Check for code repository links in paper.

**DATA ANALYST:** Uses EIA, FRED, NASA GISS, GEPU data -- all publicly available. Methodology
section details exact data construction.
