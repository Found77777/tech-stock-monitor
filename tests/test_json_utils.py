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
