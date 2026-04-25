from difflib import get_close_matches

import pandas as pd

SALES_KEYWORDS = ["jami", "total", "amount", "price", "summa", "sotuv", "savdo", "revenue"]
PRODUCT_KEYWORDS = ["mahsulot", "product", "item", "nomi", "name"]
REGION_KEYWORDS = ["hudud", "region", "city", "shahar", "manzil", "viloyat"]
DATE_KEYWORDS = ["sana", "date", "kun", "oy", "yil", "vaqt", "time"]


def normalize_text(value):
    return str(value).strip().lower()


def safe_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, pd.Period)):
        return str(value)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def clean_records(frame):
    records = frame.to_dict(orient="records")
    return [{k: clean_value(v) for k, v in row.items()} for row in records]


def find_column_by_keywords(df, keywords, numeric_only=False):
    for col in df.columns:
        col_name = normalize_text(col)
        if any(keyword in col_name for keyword in keywords):
            if numeric_only and not pd.api.types.is_numeric_dtype(df[col]):
                continue
            return col
    return None


def resolve_column(df, hint=None, numeric_only=False):
    if hint is None:
        return None

    hint_normalized = normalize_text(hint)
    columns = list(df.columns)

    for col in columns:
        if normalize_text(col) == hint_normalized:
            if numeric_only and not pd.api.types.is_numeric_dtype(df[col]):
                return None
            return col

    for col in columns:
        col_normalized = normalize_text(col)
        if hint_normalized in col_normalized or col_normalized in hint_normalized:
            if numeric_only and not pd.api.types.is_numeric_dtype(df[col]):
                continue
            return col

    normalized_map = {normalize_text(col): col for col in columns}
    close_matches = get_close_matches(hint_normalized, list(normalized_map.keys()), n=1, cutoff=0.6)
    if close_matches:
        best = normalized_map[close_matches[0]]
        if numeric_only and not pd.api.types.is_numeric_dtype(df[best]):
            return None
        return best

    return None


def detect_default_columns(df):
    sales_col = find_column_by_keywords(df, SALES_KEYWORDS, numeric_only=True)
    if sales_col is None:
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        sales_col = numeric_cols[0] if numeric_cols else None

    product_col = find_column_by_keywords(df, PRODUCT_KEYWORDS)
    region_col = find_column_by_keywords(df, REGION_KEYWORDS)
    date_col = find_column_by_keywords(df, DATE_KEYWORDS)

    return {
        "sales_column": sales_col,
        "product_column": product_col,
        "region_column": region_col,
        "date_column": date_col,
    }


def resolve_value_column(df, value_column=None):
    if value_column:
        resolved = resolve_column(df, value_column, numeric_only=True)
        if resolved:
            return resolved
    return detect_default_columns(df).get("sales_column")
