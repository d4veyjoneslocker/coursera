from backend.insights.insights_helper import format_float, format_number, format_float, format_pct

def format_metric_display(value, formatter):
    if formatter == "percent":
        return format_pct(value, decimals=1)

    if formatter == "integer":
        return format_number(value)

    if formatter == "decimal_1":
        return format_float(value, decimals=1)

    return str(value)