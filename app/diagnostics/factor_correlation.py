from __future__ import annotations

import pandas as pd


def factor_correlation_matrix(df: pd.DataFrame, factor_cols: list[str]) -> pd.DataFrame:
    return df[factor_cols].corr().fillna(0.0)
