---
layout: default
title: 'ALF-141 — Adversarial Harm Rating'
permalink: /alf-141-adversarial-harm-rating/
---
# ALF-141 — Adversarial Harm Rating

**Laurie Hocking**  
August 2026

## Executive Summary

#### The problem
In Trust & Safety, volume is a persistent challenge, there is often more adversarial activity than can be addressed at once. Making and communicating informed prioritization decisions requires a consistent method to weigh the harm posed by adversarial activity. Naive approaches (intuition-based ad-hoc assessments, or simple counts of accounts in a network) may suffice at low maturity, but as defensive functions scale, a more rigorous approach becomes necessary.

#### What this paper introduces
The Adversarial Harm Rating (AHR) – a flexible model rating harm across three axes: Victim Impact, Scale, and External Pressure. The first two measure impact to victims (individual severity and breadth of exposure); the third measures risk to the organization itself (regulatory, legal, and reputational). The model is designed so that it both preserves this decomposable distinction (separate ratings for the victim and organization focused impact) and provides an approach to combine them into a composite score providing a way to directly compare one adversarial network to another using a single score.
The model is intentionally flexible rather than prescriptive – indicators, boundary-setting methods, and the level of automation are all adaptable to an organization's size, maturity, and domain, while the three axes and their separation remain constant.

#### Who should use this
Anyone responsible for prioritizing/triaging/stack-ranking adversarial activity at scale: intelligence and investigations teams prioritizing leads, product teams hardening products against abuse and executive/policy stakeholders who need a methodology to help them focus on the most severe abuse within a given harm domain.

#### Where to find the model
The model itself, its five steps, the lookup table, and boundary-setting method is set out in full in Section 3 (The Adversarial Harm Rating Model). A ready-to-use Python reference implementation, structured to match those same five steps, is available as an accompanying Jupyter notebook (ahr_model.ipynb), with two fully worked hypothetical examples (one for an AI lab scams scenario and the other for a social media influence operation) – (AHR — Worked Hypothetical Examples) demonstrating it end to end. Both can be adopted and adapted directly, see Section 3 and the accompanying notebooks to get started.


## Paper

[Download the full paper (PDF)](paper.pdf)

## Framework

![Adversarial Harm Rating Framework](figures/framework.png)

## Supporting Materials

The analysis supporting this paper is available in the following
Jupyter notebooks:

- [Analysis](notebooks/analysis.ipynb)
- [Sensitivity analysis](notebooks/sensitivity.ipynb)
