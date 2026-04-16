"""
weight_calculator.py
Computes per-provider, per-metric accuracy weights by comparing forecast_snapshots
to actuals and updates the provider_weights table.

Algorithm:
  1. Load all forecast snapshots that have a matching actuals row.
  2. For each (provider, metric), compute MAE = mean(|forecast - actual|).
  3. Normalise: weight = median_MAE_across_providers / this_provider_MAE
       → better than median  ⟹  weight > 1.0
       → worse  than median  ⟹  weight < 1.0
  4. Confidence smoothing: blend toward 1.0 until MIN_SAMPLES reached.
  5. Upsert provider_weights (skip rows with is_manual_override = true).
  6. Compute overall = geometric mean of the four metric weights.

Called after:
  - actuals_fetcher stores new data  (via actuals_fetcher.py)
  - user submits ground truth         (via ground_truth.py route)
  - admin presses "Recalculate"       (via admin.py route)
"""

import logging
import math
from services.supabase_client import get_client
import services.weight_loader as weight_loader

logger = logging.getLogger(__name__)

MIN_SAMPLES = 10   # below this, weights blend toward 1.0

# Metric → (snapshot column, actuals column)
_NUMERIC_METRICS = {
    "temperature":   ("temp_avg_c",       "temp_avg_c"),
    "precipitation": ("precipitation_mm",  "precipitation_mm"),
    "wind":          ("wind_max_kmh",      "wind_max_kmh"),
}


def calculate_weights():
    """Recompute all provider weights from available snapshot/actuals pairs."""
    client = get_client()

    # --- Load snapshots ---
    try:
        snap_resp = client.table("forecast_snapshots") \
            .select("provider,lat,lon,forecast_for_date,temp_avg_c,precipitation_mm,wind_max_kmh,conditions") \
            .execute()
        snapshots = snap_resp.data or []
    except Exception as exc:
        logger.warning("weight_calculator: failed to load snapshots: %s", exc)
        return

    if not snapshots:
        logger.info("weight_calculator: no snapshots yet, skipping")
        return

    # --- Load actuals ---
    try:
        act_resp = client.table("actuals") \
            .select("lat,lon,date,temp_avg_c,precipitation_mm,wind_max_kmh,conditions") \
            .execute()
        actuals_list = act_resp.data or []
    except Exception as exc:
        logger.warning("weight_calculator: failed to load actuals: %s", exc)
        return

    if not actuals_list:
        logger.info("weight_calculator: no actuals yet, skipping")
        return

    # Build actuals lookup: (lat, lon, date) → best actual row
    # Prefer open_meteo_historical over user_ground_truth for numeric metrics
    actuals_map = {}
    for a in actuals_list:
        key = (_round(a["lat"]), _round(a["lon"]), a["date"])
        existing = actuals_map.get(key)
        if existing is None or a.get("source") == "open_meteo_historical":
            actuals_map[key] = a

    # --- Accumulate errors per (provider, metric) ---
    # errors[provider][metric] = list of absolute errors
    errors: dict[str, dict[str, list]] = {}

    for snap in snapshots:
        key = (_round(snap["lat"]), _round(snap["lon"]), snap["forecast_for_date"])
        actual = actuals_map.get(key)
        if actual is None:
            continue

        provider = snap["provider"]
        if provider not in errors:
            errors[provider] = {m: [] for m in list(_NUMERIC_METRICS) + ["conditions"]}

        # Numeric metrics
        for metric, (s_col, a_col) in _NUMERIC_METRICS.items():
            s_val = snap.get(s_col)
            a_val = actual.get(a_col)
            if s_val is not None and a_val is not None:
                errors[provider][metric].append(abs(float(s_val) - float(a_val)))

        # Conditions: categorical — error is 0 (match) or 1 (mismatch)
        s_cond = snap.get("conditions")
        a_cond = actual.get("conditions")
        if s_cond and a_cond:
            errors[provider]["conditions"].append(0.0 if s_cond == a_cond else 1.0)

    if not errors:
        logger.info("weight_calculator: no overlapping snapshot/actuals pairs yet")
        return

    # --- Compute MAE per (provider, metric) ---
    mae_table: dict[str, dict[str, float]] = {}
    count_table: dict[str, dict[str, int]] = {}
    for provider, metrics in errors.items():
        mae_table[provider] = {}
        count_table[provider] = {}
        for metric, errs in metrics.items():
            if errs:
                mae_table[provider][metric] = sum(errs) / len(errs)
                count_table[provider][metric] = len(errs)

    # --- Load existing manual overrides so we skip them ---
    try:
        override_resp = client.table("provider_weights") \
            .select("provider,metric") \
            .eq("is_manual_override", True) \
            .execute()
        overrides = {(r["provider"], r["metric"]) for r in (override_resp.data or [])}
    except Exception:
        overrides = set()

    # --- Normalise and upsert ---
    all_metrics = list(_NUMERIC_METRICS) + ["conditions"]
    rows_to_upsert = []

    for metric in all_metrics:
        # Gather MAEs from all providers for this metric
        provider_maes = {
            p: mae_table[p][metric]
            for p in mae_table
            if metric in mae_table[p]
        }
        if len(provider_maes) < 2:
            continue  # need at least 2 providers to normalise

        median_mae = _median(list(provider_maes.values()))
        if median_mae == 0:
            continue

        for provider, mae in provider_maes.items():
            if (provider, metric) in overrides:
                continue
            n = count_table[provider].get(metric, 0)
            raw_weight = median_mae / mae if mae > 0 else 2.0
            # Confidence smoothing: blend toward 1.0 below MIN_SAMPLES
            confidence = min(n / MIN_SAMPLES, 1.0)
            weight = 1.0 + confidence * (raw_weight - 1.0)
            # Cap weights to [0.1, 3.0] to prevent runaway values
            weight = max(0.1, min(3.0, weight))

            rows_to_upsert.append({
                "provider":     provider,
                "metric":       metric,
                "weight":       round(weight, 3),
                "sample_count": n,
                "mae":          round(mae, 4),
                "is_manual_override": False,
            })

    # Add overall weight = geometric mean of the four metric weights
    for provider in set(r["provider"] for r in rows_to_upsert):
        if (provider, "overall") in overrides:
            continue
        metric_weights = [
            r["weight"] for r in rows_to_upsert
            if r["provider"] == provider and r["metric"] != "overall"
        ]
        if metric_weights:
            overall = _geometric_mean(metric_weights)
            overall = max(0.1, min(3.0, overall))
            total_samples = sum(
                r["sample_count"] for r in rows_to_upsert
                if r["provider"] == provider and r["metric"] != "overall"
            )
            rows_to_upsert.append({
                "provider":     provider,
                "metric":       "overall",
                "weight":       round(overall, 3),
                "sample_count": total_samples // max(len(metric_weights), 1),
                "mae":          None,
                "is_manual_override": False,
            })

    if not rows_to_upsert:
        logger.info("weight_calculator: nothing new to upsert")
        return

    try:
        # Supabase upsert on (provider, metric) unique constraint
        client.table("provider_weights").upsert(
            rows_to_upsert,
            on_conflict="provider,metric"
        ).execute()
        logger.info(
            "weight_calculator: upserted %d weight rows for %d providers",
            len(rows_to_upsert),
            len({r["provider"] for r in rows_to_upsert}),
        )
    except Exception as exc:
        logger.warning("weight_calculator: upsert failed: %s", exc)
        return

    weight_loader.invalidate_cache()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _round(v) -> float:
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return v


def _median(values: list) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _geometric_mean(values: list) -> float:
    if not values:
        return 1.0
    log_sum = sum(math.log(max(v, 1e-9)) for v in values)
    return math.exp(log_sum / len(values))
