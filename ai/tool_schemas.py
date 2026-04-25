TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_columns",
            "description": "Dataset ustunlari va avtomatik aniqlangan ustunlarni qaytaradi.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dataset_summary",
            "description": "Dataset bo'yicha umumiy ma'lumot (qatorlar, ustunlar, namuna) qaytaradi.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "aggregate_metric",
            "description": "Sonli ustun bo'yicha agregatsiya hisoblaydi (sum, mean, min, max, count).",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["sum", "mean", "min", "max", "count"]},
                    "value_column": {"type": "string"},
                },
                "required": ["metric"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "group_metric",
            "description": "Guruhlash va agregatsiya bajaradi; masalan mahsulot yoki hudud bo'yicha sotuv.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_column": {"type": "string"},
                    "value_column": {"type": "string"},
                    "metric": {"type": "string", "enum": ["sum", "mean", "min", "max", "count"]},
                    "top_n": {"type": "integer", "minimum": 1, "maximum": 100},
                    "ascending": {"type": "boolean"},
                },
                "required": ["metric"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_metric",
            "description": "Filtrlangan qatorlar bo'yicha agregatsiya hisoblaydi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_column": {"type": "string"},
                    "filter_value": {"type": ["string", "number", "boolean"]},
                    "operator": {"type": "string", "enum": ["eq", "contains", "gt", "gte", "lt", "lte"]},
                    "metric": {"type": "string", "enum": ["sum", "mean", "min", "max", "count"]},
                    "value_column": {"type": "string"},
                },
                "required": ["filter_column", "filter_value", "metric"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trend_over_time",
            "description": "Sana ustuni bo'yicha vaqt trendini hisoblaydi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_column": {"type": "string"},
                    "value_column": {"type": "string"},
                    "metric": {"type": "string", "enum": ["sum", "mean", "min", "max", "count"]},
                    "freq": {"type": "string", "enum": ["D", "W", "M", "Q", "Y"]},
                    "top_n": {"type": "integer", "minimum": 1, "maximum": 120},
                },
                "required": ["metric"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_unique_values",
            "description": "Ustundagi eng ko'p uchraydigan qiymatlarni qaytaradi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "top_n": {"type": "integer", "minimum": 1, "maximum": 100},
                },
                "required": ["column"],
                "additionalProperties": False,
            },
        },
    },
]
