import json
import math

import numpy as np
import pandas as pd

from app.utils.json_utils import sanitize_for_json


def test_nan_inf_to_none():
    obj = {"a": math.nan, "b": math.inf, "c": -math.inf}
    out = sanitize_for_json(obj)
    assert out == {"a": None, "b": None, "c": None}


def test_numpy_types_json_serializable():
    obj = {"i": np.int64(3), "f": np.float64(2.5), "n": np.float64(np.nan)}
    out = sanitize_for_json(obj)
    assert out["i"] == 3 and isinstance(out["i"], int)
    assert out["f"] == 2.5 and isinstance(out["f"], float)
    assert out["n"] is None
    json.dumps(out)


def test_pandas_dataframe_serializable():
    df = pd.DataFrame({"a": [1, np.nan], "b": [pd.NaT, "x"]})
    out = sanitize_for_json(df)
    assert out[1]["a"] is None
    assert out[0]["b"] is None
    json.dumps(out)


def test_nested_dict_no_float_error():
    out = sanitize_for_json({"a": {"b": 1.2}})
    assert out == {"a": {"b": 1.2}}


def test_nested_metrics_nan_cleaned():
    out = sanitize_for_json({"metrics": {"sharpe": math.nan}})
    assert out == {"metrics": {"sharpe": None}}


def test_watchlist_like_reasons_no_float_cast():
    payload = [{"code": "600100", "reasons": ["趋势正常", {"risk": "low"}], "total_score": 55.2}]
    out = sanitize_for_json(payload)
    assert out[0]["reasons"][1]["risk"] == "low"
    json.dumps(out)
