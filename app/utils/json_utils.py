"""Utilities to sanitize Python/numpy/pandas objects for JSON responses."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def sanitize_for_json(obj: Any) -> Any:
    if obj is None:
        return None

    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        val = float(obj)
        return None if (math.isnan(val) or math.isinf(val)) else val

    if isinstance(obj, (float,)):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, (int, str, bool)):
        return obj

    # pandas missing values (NaN, NaT, pd.NA)
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass

    if isinstance(obj, pd.DataFrame):
        return sanitize_for_json(obj.to_dict(orient="records"))
    if isinstance(obj, pd.Series):
        return sanitize_for_json(obj.tolist())

    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(v) for v in obj]

    return obj
