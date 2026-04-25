import pandas as pd

from .data_helpers import (
    clean_records,
    detect_default_columns,
    normalize_text,
    resolve_column,
    resolve_value_column,
    safe_number,
)


def get_columns(df):
    numeric_columns = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    return {
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "numeric_columns": numeric_columns,
        "detected": detect_default_columns(df),
    }


def get_dataset_summary(df):
    columns_meta = []
    for col in df.columns:
        columns_meta.append(
            {
                "name": col,
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isna().sum()),
                "unique_count": int(df[col].nunique(dropna=True)),
            }
        )

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": columns_meta,
        "sample_rows": clean_records(df.head(5)),
    }


def aggregate_metric(df, metric="sum", value_column=None):
    metric = normalize_text(metric)
    allowed = {"sum", "mean", "min", "max", "count"}
    if metric not in allowed:
        return {"error": f"Noto'g'ri metric: {metric}"}

    if metric == "count":
        return {
            "metric": metric,
            "value": int(len(df)),
        }

    target_col = resolve_value_column(df, value_column)
    if not target_col:
        return {"error": "Hisoblash uchun mos sonli ustun topilmadi."}

    numeric_series = pd.to_numeric(df[target_col], errors="coerce").dropna()
    if numeric_series.empty:
        return {"error": f"{target_col} ustunida sonli qiymatlar topilmadi."}

    result_value = getattr(numeric_series, metric)()
    return {
        "metric": metric,
        "value_column": target_col,
        "value": float(result_value),
    }


def group_metric(df, group_column=None, value_column=None, metric="sum", top_n=10, ascending=False):
    metric = normalize_text(metric)
    allowed = {"sum", "mean", "min", "max", "count"}
    if metric not in allowed:
        return {"error": f"Noto'g'ri metric: {metric}"}

    defaults = detect_default_columns(df)
    target_group_col = resolve_column(df, group_column) if group_column else None
    if target_group_col is None:
        target_group_col = defaults.get("product_column") or defaults.get("region_column")

    if target_group_col is None:
        return {"error": "Guruhlash uchun ustun topilmadi."}

    top_n = max(1, min(int(top_n), 100))

    if metric == "count":
        grouped = df.groupby(target_group_col, dropna=False).size().reset_index(name="count")
        grouped = grouped.sort_values("count", ascending=bool(ascending)).head(top_n)
        return {
            "group_column": target_group_col,
            "metric": metric,
            "rows": clean_records(grouped),
        }

    target_value_col = resolve_value_column(df, value_column)
    if target_value_col is None:
        return {"error": "Hisoblash uchun sonli ustun topilmadi."}

    temp = df[[target_group_col, target_value_col]].copy()
    temp[target_value_col] = pd.to_numeric(temp[target_value_col], errors="coerce")
    temp = temp.dropna(subset=[target_value_col])
    if temp.empty:
        return {"error": "Guruhlash uchun yetarli sonli ma'lumot topilmadi."}

    grouped = (
        temp.groupby(target_group_col, dropna=False)[target_value_col]
        .agg(metric)
        .reset_index(name=metric)
        .sort_values(metric, ascending=bool(ascending))
        .head(top_n)
    )

    return {
        "group_column": target_group_col,
        "value_column": target_value_col,
        "metric": metric,
        "rows": clean_records(grouped),
    }


def filter_metric(
    df,
    filter_column,
    filter_value,
    operator="eq",
    metric="sum",
    value_column=None,
):
    target_filter_col = resolve_column(df, filter_column)
    if target_filter_col is None:
        return {"error": f"Filtr ustuni topilmadi: {filter_column}"}

    operator = normalize_text(operator)
    series = df[target_filter_col]

    if operator == "contains":
        mask = series.astype(str).str.contains(str(filter_value), case=False, na=False)
    elif operator in {"eq", "gt", "gte", "lt", "lte"}:
        left = pd.to_numeric(series, errors="coerce")
        right = safe_number(filter_value)
        if right is None:
            if operator != "eq":
                return {"error": "Raqamli solishtirish uchun filter_value son bo'lishi kerak."}
            mask = series.astype(str).str.lower() == str(filter_value).lower()
        else:
            if operator == "eq":
                mask = left == right
            elif operator == "gt":
                mask = left > right
            elif operator == "gte":
                mask = left >= right
            elif operator == "lt":
                mask = left < right
            else:
                mask = left <= right
    else:
        return {"error": f"Noto'g'ri operator: {operator}"}

    filtered = df[mask]
    if filtered.empty:
        return {
            "filter_column": target_filter_col,
            "filter_value": filter_value,
            "matched_rows": 0,
            "result": None,
        }

    result = aggregate_metric(filtered, metric=metric, value_column=value_column)
    return {
        "filter_column": target_filter_col,
        "filter_value": filter_value,
        "operator": operator,
        "matched_rows": int(len(filtered)),
        "result": result,
    }


def trend_over_time(df, date_column=None, value_column=None, metric="sum", freq="M", top_n=24):
    metric = normalize_text(metric)
    allowed_metrics = {"sum", "mean", "min", "max", "count"}
    if metric not in allowed_metrics:
        return {"error": f"Noto'g'ri metric: {metric}"}

    target_date_col = resolve_column(df, date_column) if date_column else None
    if target_date_col is None:
        target_date_col = detect_default_columns(df).get("date_column")

    if target_date_col is None:
        return {"error": "Vaqt trendi uchun sana ustuni topilmadi."}

    freq = str(freq).upper()
    if freq not in {"D", "W", "M", "Q", "Y"}:
        freq = "M"

    temp = pd.DataFrame()
    temp["_date"] = pd.to_datetime(df[target_date_col], errors="coerce")

    target_value_col = None
    if metric == "count":
        temp["_value"] = 1
    else:
        target_value_col = resolve_value_column(df, value_column)
        if target_value_col is None:
            return {"error": "Trend uchun sonli ustun topilmadi."}
        temp["_value"] = pd.to_numeric(df[target_value_col], errors="coerce")

    temp = temp.dropna(subset=["_date", "_value"])
    if temp.empty:
        return {"error": "Trend hisoblash uchun mos ma'lumot topilmadi."}

    trend = (
        temp.groupby(pd.Grouper(key="_date", freq=freq))["_value"]
        .agg(metric)
        .dropna()
        .reset_index(name=metric)
    )

    top_n = max(1, min(int(top_n), 120))
    trend = trend.sort_values("_date", ascending=True).tail(top_n)
    trend["period"] = trend["_date"].dt.strftime("%Y-%m-%d")

    return {
        "date_column": target_date_col,
        "value_column": target_value_col,
        "metric": metric,
        "freq": freq,
        "rows": clean_records(trend[["period", metric]]),
    }


def list_unique_values(df, column, top_n=20):
    target_col = resolve_column(df, column)
    if target_col is None:
        return {"error": f"Ustun topilmadi: {column}"}

    top_n = max(1, min(int(top_n), 100))
    counts = df[target_col].dropna().astype(str).value_counts().head(top_n)
    rows = [{"value": idx, "count": int(val)} for idx, val in counts.items()]

    return {
        "column": target_col,
        "rows": rows,
    }


TOOL_HANDLERS = {
    "get_columns": get_columns,
    "get_dataset_summary": get_dataset_summary,
    "aggregate_metric": aggregate_metric,
    "group_metric": group_metric,
    "filter_metric": filter_metric,
    "trend_over_time": trend_over_time,
    "list_unique_values": list_unique_values,
}
