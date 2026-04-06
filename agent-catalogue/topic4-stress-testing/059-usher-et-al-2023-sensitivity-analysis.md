---
source_url: https://pmc.ncbi.nlm.nih.gov/articles/PMC10445882/
licence: CC BY 4.0 (Open Research Europe)
date_accessed: 2026-04-06
version: Open Research Europe, Vol. 3, February 13, 2023
type: academic-paper
code_available: true
code_url: https://github.com/KTH-dESA/esom_gsa (MIT License)
data_url: https://doi.org/10.5281/zenodo.7553059
---

# Usher et al. (2023) -- Global Sensitivity Analysis for Energy System Optimisation Modelling

**Authors:** William Usher, Trevor Barnes, Nandi Moksnes, Taco Niet
**Journal:** Open Research Europe, Volume 3
**Date:** February 13, 2023
**Funding:** EU Horizon 2020 ECEMF programme

## Description

Demonstrates application of global sensitivity analysis (GSA) to energy system optimisation
models (ESOMs) using the Morris screening method. Applies to three models of increasing
complexity (3, 10, and 42 parameters). Key findings: a small subset of parameters typically
dominates outcomes; demand and policy parameters are as influential as technology costs;
GSA prevents missing key drivers when designing scenarios. Code available on GitHub (MIT
licence), data and Jupyter notebooks on Zenodo.

## Key Findings

- Morris screening efficiently identifies dominant parameters (~10(k+1) model runs)
- Technology costs alone are insufficient -- demand and policy parameters equally critical
- Different output variables are sensitive to different parameter combinations

## Usefulness Assessment

**Relevant** -- GSA methodology is directly applicable to the project's stress-testing
component. Using Morris screening on the Python microeconomics model will identify which
Brent price assumptions drive renewable investment outcomes most strongly.

## Possible Application

- Morris screening for sensitivity analysis of the Python microeconomics model
- Parameter prioritisation for stress-test scenario design
- OSeMOSYS Global methodology reference for energy system modelling

## Download Note / Code

Code: https://github.com/KTH-dESA/esom_gsa (MIT licence -- freely usable)
Data + Notebooks: https://doi.org/10.5281/zenodo.7553059

## Flag

**CODE ANALYST:** Open-source GSA code (MIT licence) directly applicable to the Backend
Engineer's Python library. Check the GitHub repo for OSeMOSYS integration patterns.

**BACKEND ENGINEER:** Morris screening implementation available in the esom_gsa GitHub repo.
Consider adapting for sensitivity analysis of the microeconomics model.
