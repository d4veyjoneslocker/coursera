def format_filter_values(values, max_items=3):
    if not values:
        return None

    if not isinstance(values, list):
        values = [values]

    values = [v for v in values if v]

    if len(values) == 1:
        return values[0]

    if len(values) == 2:
        return f"{values[0]} and {values[1]}"

    shown = values[:max_items]
    extra_count = len(values) - max_items

    text = f"{', '.join(shown[:-1])}, and {shown[-1]}"

    if extra_count > 0:
        text += f" + {extra_count} more"

    return text


def build_filter_context(filters, exclude_keys=None):
    if not filters:
        return "", []

    exclude_keys = exclude_keys or set()

    filter_labels = {
        "sku": "for",
        "channel": "in",
        "distributor": "in stores serviced by",
        "dc": "from DC",
        "state": "in",
        "chain": "in",
    }

    context_parts = []
    part_objects = []

    for key, prefix in filter_labels.items():
        if key in exclude_keys:
            continue

        value_text = format_filter_values(filters.get(key))
        if not value_text:
            continue

        context_parts.append(f"{prefix} {value_text}")
        part_objects.extend([
            {"type": "text", "value": f" {prefix} "},
            {"type": "chip", "value": value_text, "tone": "neutral"},
        ])

    context_str = " " + " ".join(context_parts) if context_parts else ""

    return context_str, part_objects