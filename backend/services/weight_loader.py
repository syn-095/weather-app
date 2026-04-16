"""
weight_loader.py
Loads current provider weights from Supabase with a 30-minute in-memory TTL cache.
Falls back to all-1.0 weights if the table is empty or the DB is unavailable —
the aggregator degrades gracefully to a plain arithmetic mean.

Public API:
    get_weights()        -> dict[provider][metric] = float
    invalidate_cache()   -> forces next call to reload from DB
"""

import logging
import time
from services.supabase_client import get_client

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 30 * 60   # 30 minutes
_cache: dict = {}
_cache_loaded_at: float = 0.0


def get_weights() -> dict:
    """
    Return a nested dict: { provider: { metric: weight } }.

    Example:
        {
          "open_meteo":  {"temperature": 1.2, "precipitation": 0.9, "overall": 1.05},
          "yr_no":       {"temperature": 0.8, "precipitation": 1.3, "overall": 1.02},
          ...
        }
    If no weights exist yet, returns an empty dict (aggregator defaults to 1.0).
    """
    global _cache, _cache_loaded_at

    now = time.monotonic()
    if _cache and (now - _cache_loaded_at) < _CACHE_TTL_SECONDS:
        return _cache

    try:
        resp = get_client().table("provider_weights") \
            .select("provider,metric,weight") \
            .execute()
        rows = resp.data or []
    except Exception as exc:
        logger.warning("weight_loader: failed to load weights: %s", exc)
        return _cache  # return stale cache rather than failing

    weights: dict = {}
    for row in rows:
        provider = row.get("provider")
        metric   = row.get("metric")
        weight   = row.get("weight")
        if provider and metric and weight is not None:
            weights.setdefault(provider, {})[metric] = float(weight)

    _cache = weights
    _cache_loaded_at = now
    logger.debug("weight_loader: loaded %d weight entries", len(rows))
    return _cache


def invalidate_cache():
    """Force the next get_weights() call to reload from Supabase."""
    global _cache_loaded_at
    _cache_loaded_at = 0.0
