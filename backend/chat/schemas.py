from typing import Literal

from pydantic import BaseModel


MetricName = Literal[
    "units",
    "buying_stores",
    "active_pods",
    "active_pod_opportunities",
    "velocity",
    "reorder_rate",
    "pod_reorder_rate",
    "fill_rate",
    "average_skus_per_store",
    "new_pods",
    "active_skus",
    "skus_selling",
    "order_velocity",
]

RequestType = Literal[
    "metric",
    "ranking",
    "comparison",
    "unsupported",
    "clarification"
]

ComparisonType = Literal[
    "PY",
    "PP",
]

Period = Literal[
    "L1M",
    "L2M",
    "L3M",
    "L4M",
    "L5M",
    "L6M",
    "L7M",
    "L8M",
    "L9M",
    "L10M",
    "L11M",
    "L12M",
    "L1Q",
    "L2Q",
    "L3Q",
    "L4Q",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "H1",
    "H2",
    "FY",
]


GroupBy = Literal[
    "distributor",
    "chain",
    "sku",
    "dc",
]


ClarificationField = Literal[
    "metric",
    "period",
    "distributor",
    "chain",
    "sku",
    "dc",
    "group_by",
]

RankingIntent = Literal[
    "highest",
    "lowest",
    "best",
    "worst",
]

ChangeDirection = Literal[
    "improved",
    "declined",
    "flat",
]


class MetricRequest(BaseModel):
    request_type: RequestType
    use_context: bool = False

    metric: MetricName | None = None
    period: Period | None = None
    year: int | None = None

    distributor: str | None = None
    chain: str | None = None
    sku: str | None = None
    dc: str | None = None

    group_by: GroupBy | None = None

    sort_direction: Literal[
        "ascending",
        "descending",
    ] | None = None
    change_direction: ChangeDirection | None = None
    ranking_intent: RankingIntent | None = None
    comparison_type: ComparisonType | None = None

    limit: int | None = None

    clarification_field: ClarificationField | None = None
    message: str | None = None