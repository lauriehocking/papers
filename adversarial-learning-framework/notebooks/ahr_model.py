"""
Adversarial Harm Rating (AHR) — reference implementation
ALF-141 · Adversarial Learning Framework

A single model with three axes:

  Victim Impact   -- tiered judgment (Low/Medium/High), informed by a
                     reference source (sentencing guidelines, an
                     established categorization system, or an
                     org-defined harm sub-type -> tier table). Always
                     categorical: this axis is never converted into a
                     manufactured numeric score.

  Scale           -- tiered judgment (Low/Medium/High), derived from
                     exposure indicators (recipients, views, ad spend).
                     Genuinely continuous, so this axis supports optional
                     added sophistication: percentile-derived boundaries
                     instead of fixed cutoffs, and/or multiple weighted
                     indicators combined before bucketing.

  External Pressure -- tiered judgment (Low/Medium/High/Critical), rated
                     independently of Harm. Reported as an escalation
                     flag, not blended into the Harm Tier by default.
                     Individual indicators that are genuinely countable
                     (e.g. litigation count) may use the same continuous
                     treatment as Scale; indicators that are really a
                     proxy dressed as a number (e.g. "media volume")
                     should stay a direct tier judgment.

Victim Impact + Scale combine via a lookup table into a Harm Tier — the
primary ranking key. External Pressure is reported alongside it as an
escalation flag. An optional composite mode exists for high-volume
triage, and remains decomposable back into Harm Tier and Pressure Tier.

This is a reference implementation, not a prescription. All tables,
weights, and boundaries marked PLACEHOLDER below are illustrative
starting points that belong in an external config file (e.g. YAML/JSON)
in production, owned by the relevant function, and versioned
independently of this code.
"""

from dataclasses import dataclass, field
from typing import Optional
import math


# ---------------------------------------------------------------------------
# PLACEHOLDER — Harm Lookup Table: Victim Impact x Scale -> Harm Tier
# This is the one piece of genuine editorial judgment in the model. It
# should be authored deliberately and reviewed periodically, not left as
# a default. In production this belongs in a config file.
# ---------------------------------------------------------------------------
HARM_LOOKUP_TABLE = {
    ("Low", "Low"): "Low",
    ("Low", "Medium"): "Low",
    ("Low", "High"): "Medium",
    ("Medium", "Low"): "Low",
    ("Medium", "Medium"): "Medium",
    ("Medium", "High"): "High",
    ("High", "Low"): "Medium",
    ("High", "Medium"): "High",
    ("High", "High"): "Critical",
}

# PLACEHOLDER — External Pressure tier definitions. In production this
# belongs to policy/legal, likely on its own review cadence — this axis
# is the most volatile and jurisdiction-dependent of the three.
PRESSURE_TIER_DEFINITIONS = {
    "Low": "No known reason for elevated risk.",
    "Medium": "Emerging elevation of risk.",
    "High": "Active sustained pressure requiring ongoing support.",
    "Critical": "Subject to high-profile action likely to cause substantial financial/reputational risk.",
}

# PLACEHOLDER — composite mode: tier numeric values and pressure
# multiplier. See ALF-141 Section 4 for the rationale behind these
# specific values and the insulation property they preserve (pressure
# alone should not promote a Low-harm incident above a Medium-harm one).
TIER_NUMERIC = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
PRESSURE_MULTIPLIER = {"Low": 1.0, "Medium": 1.15, "High": 1.35, "Critical": 1.6}

TIER_ORDER = ["Low", "Medium", "High", "Critical"]


# ---------------------------------------------------------------------------
# Boundary setting for continuous indicators (Scale, and any countable
# External Pressure indicators). Not used for Victim Impact, which is
# always tiered via reference table (see rate_victim_impact below).
# ---------------------------------------------------------------------------

def percentile_boundaries(historical_values: list[float],
                           percentiles: tuple[float, float] = (60, 90),
                           log_transform: bool = True) -> dict[str, float]:
    """Derive Low/Medium/High cutpoints from an organization's own
    historical distribution for this harm type, rather than an arbitrary
    fixed number.

    Recommended hierarchy: use an absolute/regulatory reference where one
    exists; fall back to this distribution-based approach only where no
    such reference is available. Recalibrate on a fixed cadence (e.g.
    quarterly) and version-stamp the boundary set used for any given
    scoring run.
    """
    values = [math.log1p(v) for v in historical_values] if log_transform else list(historical_values)
    values = sorted(values)

    def _pctile(p: float) -> float:
        k = (len(values) - 1) * (p / 100)
        f, c = math.floor(k), math.ceil(k)
        if f == c:
            return values[int(k)]
        return values[int(f)] + (values[int(c)] - values[int(f)]) * (k - f)

    return {"low_medium": _pctile(percentiles[0]), "medium_high": _pctile(percentiles[1])}


def tier_from_value(value: float, boundaries: dict[str, float],
                     log_transform: bool = True) -> str:
    """Apply a boundary set produced by percentile_boundaries() (or any
    fixed equivalent) to a raw value, returning Low / Medium / High."""
    v = math.log1p(value) if log_transform else value
    if v < boundaries["low_medium"]:
        return "Low"
    if v < boundaries["medium_high"]:
        return "Medium"
    return "High"


# ---------------------------------------------------------------------------
# Optional sophistication: multiple weighted indicators combined into a
# single continuous value before bucketing into a tier. Applies to Scale,
# and to any External Pressure indicator that is genuinely countable.
# ---------------------------------------------------------------------------

@dataclass
class Indicator:
    name: str
    weight: float
    value_range: tuple[float, float]
    log_transform: bool = False


def normalize(value: float, indicator: Indicator) -> float:
    """Map a raw indicator value to 0-100, with optional log transform
    for power-law-distributed count/volume indicators."""
    lo, hi = indicator.value_range
    v = value
    if indicator.log_transform:
        v, lo, hi = math.log1p(max(v, 0)), math.log1p(max(lo, 0)), math.log1p(max(hi, 0))
    if hi <= lo:
        raise ValueError(f"Invalid range for {indicator.name}: {indicator.value_range}")
    return max(0.0, min(100.0, (v - lo) / (hi - lo) * 100))


def weighted_indicator_score(indicators: list[Indicator], raw_values: dict[str, float]) -> float:
    """Combine several weighted, normalized indicators into one 0-100
    value. Use this only where indicators are genuinely continuous
    measurements of the incident itself — not categorical judgments
    (e.g. 'assumed average loss for this harm sub-type') dressed up as
    numbers. See ALF-141 Section 4 for this distinction."""
    total = 0.0
    for ind in indicators:
        if ind.name not in raw_values:
            raise KeyError(f"Missing value for indicator '{ind.name}'")
        total += normalize(raw_values[ind.name], ind) * ind.weight
    return total


# ---------------------------------------------------------------------------
# Axis rating functions
# ---------------------------------------------------------------------------

# PLACEHOLDER — Victim Impact reference table: harm sub-type -> tier.
# Always categorical. Populate from sentencing guidelines, an established
# categorization system (e.g. CSAM's ABC categories), or org judgment.
VICTIM_IMPACT_REFERENCE_TABLE = {
    "scam_low_value_nondelivery": "Low",
    "scam_investment_fraud": "High",
    "influence_op_low_engagement": "Low",
    "influence_op_election_targeted": "High",
}


def rate_victim_impact(harm_subtype: str) -> str:
    """Victim Impact is always a tiered judgment, never a manufactured
    numeric score — the underlying reality is 'which kind of harm is
    this', not a continuous measurement of this specific incident."""
    if harm_subtype not in VICTIM_IMPACT_REFERENCE_TABLE:
        raise KeyError(f"No Victim Impact reference entry for harm sub-type '{harm_subtype}'")
    return VICTIM_IMPACT_REFERENCE_TABLE[harm_subtype]


def rate_scale(raw_values: dict[str, float],
               indicators: Optional[list[Indicator]] = None,
               boundaries: Optional[dict[str, float]] = None,
               single_indicator_name: str = "exposure") -> str:
    """Rate Scale as Low/Medium/High.

    Simplest form: pass a single exposure value under
    raw_values[single_indicator_name] and a boundaries dict (from
    percentile_boundaries or a fixed equivalent).

    More sophisticated form: pass a list of weighted Indicators plus
    matching raw_values; these are combined into one continuous value
    before bucketing against the same boundaries.
    """
    if boundaries is None:
        raise ValueError("Scale requires a boundary set — see percentile_boundaries()")

    if indicators:
        value = weighted_indicator_score(indicators, raw_values)
        return tier_from_value(value, boundaries, log_transform=False)  # already normalized 0-100
    else:
        return tier_from_value(raw_values[single_indicator_name], boundaries, log_transform=True)


def rate_external_pressure(tier: str) -> str:
    """External Pressure is rated independently of Harm, by default as a
    direct tier judgment informed by named indicators (litigation count,
    presence of relevant legislation, media coverage). Where an
    individual indicator is genuinely countable, it may be pre-processed
    via weighted_indicator_score() / tier_from_value() before being
    passed in here as the resulting tier."""
    if tier not in PRESSURE_TIER_DEFINITIONS:
        raise KeyError(f"Unknown pressure tier: {tier!r}")
    return tier


# ---------------------------------------------------------------------------
# Core rating
# ---------------------------------------------------------------------------

@dataclass
class RatingResult:
    harm_tier: str
    pressure_tier: str
    composite_score: Optional[float] = None

    def as_dict(self) -> dict:
        return {
            "harm_tier": self.harm_tier,
            "pressure_tier": self.pressure_tier,
            "composite_score": round(self.composite_score, 2) if self.composite_score is not None else None,
        }


def rate_incident(victim_impact_tier: str, scale_tier: str, pressure_tier: str,
                   include_composite: bool = False) -> RatingResult:
    """Combine axis tiers into a Harm Tier (primary ranking key) and
    report Pressure Tier alongside it (escalation flag), never blended
    by default. A composite is computed only if explicitly requested,
    for high-volume triage only — the two-layer result remains the
    source of truth whenever a specific ranking decision needs to be
    explained or defended."""
    key = (victim_impact_tier, scale_tier)
    if key not in HARM_LOOKUP_TABLE:
        raise KeyError(f"No lookup entry for Victim Impact={victim_impact_tier!r}, Scale={scale_tier!r}")
    harm_tier = HARM_LOOKUP_TABLE[key]

    if pressure_tier not in PRESSURE_TIER_DEFINITIONS:
        raise KeyError(f"Unknown pressure tier: {pressure_tier!r}")

    composite = None
    if include_composite:
        composite = TIER_NUMERIC[harm_tier] * PRESSURE_MULTIPLIER[pressure_tier]

    return RatingResult(harm_tier, pressure_tier, composite)


def rank_queue(incidents: list[dict], use_composite: bool = False) -> list[dict]:
    """Stack-rank a list of incidents. Each incident dict must contain
    'id', 'victim_impact_tier', 'scale_tier', 'pressure_tier'.

    Default sort key is Harm Tier — organizational risk should not
    silently outrank victim harm. Set use_composite=True only for
    high-volume review; every composite result remains decomposable."""
    order = {t: i for i, t in enumerate(TIER_ORDER)}
    results = []
    for inc in incidents:
        r = rate_incident(inc["victim_impact_tier"], inc["scale_tier"],
                           inc["pressure_tier"], include_composite=use_composite)
        results.append({"id": inc["id"], **r.as_dict()})

    key = (lambda x: x["composite_score"]) if use_composite else (lambda x: order[x["harm_tier"]])
    return sorted(results, key=key, reverse=True)


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # --- Simple path: single Scale indicator, Victim Impact from reference table ---
    historical_exposure = [50, 200, 900, 3000, 8000, 15000, 60000, 250000, 1_200_000]
    scale_boundaries = percentile_boundaries(historical_exposure)

    incidents = [
        {
            "id": "SCAM-1042",
            "victim_impact_tier": rate_victim_impact("scam_investment_fraud"),
            "scale_tier": rate_scale({"exposure": 8000}, boundaries=scale_boundaries),
            "pressure_tier": rate_external_pressure("Medium"),
        },
        {
            "id": "SCAM-1043",
            "victim_impact_tier": rate_victim_impact("scam_low_value_nondelivery"),
            "scale_tier": rate_scale({"exposure": 1_200_000}, boundaries=scale_boundaries),
            "pressure_tier": rate_external_pressure("High"),
        },
    ]

    print("Ranked by Harm Tier (default triage order):\n")
    for row in rank_queue(incidents, use_composite=False):
        print(row)

    print("\nRanked by Composite Score (volume-triage mode, decomposable):\n")
    for row in rank_queue(incidents, use_composite=True):
        print(row)

    # --- More sophisticated path: multiple weighted indicators for Scale ---
    scale_indicators = [
        Indicator("recipients", weight=0.7, value_range=(1, 2_000_000), log_transform=True),
        Indicator("ad_spend_usd", weight=0.3, value_range=(0, 100_000), log_transform=True),
    ]
    multi_indicator_tier = rate_scale(
        {"recipients": 500_000, "ad_spend_usd": 20_000},
        indicators=scale_indicators,
        boundaries={"low_medium": 40, "medium_high": 70},  # boundaries in 0-100 space here
    )
    print(f"\nMulti-indicator Scale tier example: {multi_indicator_tier}")
