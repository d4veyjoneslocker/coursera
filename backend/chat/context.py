from openai import OpenAI

from .schemas import MetricRequest


client = OpenAI()


SUMMARY_MODEL = "gpt-5.6"


def build_structured_state(
    request: MetricRequest,
    result: dict | None = None,
) -> dict:
    """
    Build the deterministic conversation state from the parsed request
    and the resolved SKUba result.

    This state should contain facts the system can safely reuse on
    follow-up questions without relying on the LLM to remember them.
    """

    state = {
        "request_type": request.request_type,
        "metric": request.metric,
        "period": request.period,
        "year": request.year,
        "distributor": request.distributor,
        "chain": request.chain,
        "sku": request.sku,
        "dc": request.dc,
        "group_by": request.group_by,
        "comparison_type": request.comparison_type,
        "ranking_intent": request.ranking_intent,
        "change_direction": request.change_direction,
    }

    if not result:
        return state

    # Normal metric/ranking responses return period as a resolved dict.
    result_period = result.get("period")

    if isinstance(result_period, dict):
        state["resolved_period"] = {
            "label": result_period.get("label"),
            "start": result_period.get("start"),
            "end": result_period.get("end"),
        }

    # Comparison responses return current_period/comparison_period.
    current_period = result.get("current_period")

    if isinstance(current_period, dict):
        state["resolved_period"] = {
            "label": current_period.get("label"),
            "start": current_period.get("start"),
            "end": current_period.get("end"),
        }

    comparison_period = result.get("comparison_period")

    if isinstance(comparison_period, dict):
        state["resolved_comparison_period"] = {
            "label": comparison_period.get("label"),
            "start": comparison_period.get("start"),
            "end": comparison_period.get("end"),
        }

    return state

def merge_request_with_context(
    request: MetricRequest,
    context: dict | None,
) -> MetricRequest:
    """
    For a conversational follow-up, preserve fields from the
    previous completed request unless the user changed them.
    """

    if not request.use_context or not context:
        return request

    previous_state = context.get("state") or {}

    if not previous_state:
        return request

    request_data = request.model_dump()

    fields_to_preserve = [
        "metric",
        "period",
        "year",
        "distributor",
        "chain",
        "sku",
        "dc",
        "group_by",
        "comparison_type",
        "ranking_intent",
        "change_direction",
        "limit",
    ]

    for field in fields_to_preserve:
        if (
            request_data.get(field) is None
            and previous_state.get(field) is not None
        ):
            request_data[field] = previous_state[field]

    return MetricRequest(**request_data)


def update_conversation_summary(
    previous_summary: str | None,
    user_message: str,
    answer: str,
    state: dict,
) -> str:
    """
    Update the compact running conversation summary.

    The summary is intentionally separate from structured state:
    - structured state contains deterministic facts
    - summary contains softer conversational context that may help
      interpret future follow-up questions
    """

    previous_summary = previous_summary or ""

    response = client.responses.create(
        model=SUMMARY_MODEL,
        input=[
            {
                "role": "system",
                "content": """
You maintain a short running summary of a SKUba analytics conversation.

Your job is only to preserve conversational context that may matter for future follow-up questions.

Keep:
- what the user is currently investigating
- metrics being discussed
- relevant retailers, chains, SKUs, DCs, or distributors
- time periods being discussed
- comparison periods when relevant
- unresolved questions or clarification threads
- context needed to understand references such as "that", "those", "same period", "what about them", or "do the same"

Rules:
- Treat the structured state as authoritative.
- Do not invent facts.
- Do not calculate anything.
- Do not infer causes.
- Do not include implementation details.
- Do not include long lists of results.
- Do not preserve every number unless it is likely to be referenced later.
- Prefer replacing stale context with newer context rather than endlessly appending.
- Keep the summary under 120 words.
- Return only the updated summary.
""",
            },
            {
                "role": "user",
                "content": f"""
Previous summary:
{previous_summary or "None"}

Current structured state:
{state}

Latest user message:
{user_message}

Latest SKUba answer:
{answer}

Update the running conversation summary.
""",
            },
        ],
        store=False,
    )

    return response.output_text.strip()


def build_conversation_context(
    previous_context: dict | None,
    request: MetricRequest,
    result: dict | None,
    user_message: str,
    answer: str,
) -> dict:
    """
    Build the complete context object returned to the frontend
    and sent back on the next chat turn.
    """

    previous_context = previous_context or {}

    state = build_structured_state(
        request=request,
        result=result,
    )

    summary = update_conversation_summary(
        previous_summary=previous_context.get("summary"),
        user_message=user_message,
        answer=answer,
        state=state,
    )

    return {
        "state": state,
        "summary": summary,
    }

def build_pending_request(
    request: MetricRequest,
) -> dict:
    """
    Preserve an incomplete request while SKUba waits
    for the user's clarification.
    """

    if request.comparison_type or request.change_direction:
        intended_request_type = "comparison"

    elif request.ranking_intent:
        intended_request_type = "ranking"

    else:
        intended_request_type = "metric"

    return {
        "intended_request_type": intended_request_type,
        "metric": request.metric,
        "period": request.period,
        "year": request.year,
        "distributor": request.distributor,
        "chain": request.chain,
        "sku": request.sku,
        "dc": request.dc,
        "group_by": request.group_by,
        "sort_direction": request.sort_direction,
        "ranking_intent": request.ranking_intent,
        "comparison_type": request.comparison_type,
        "change_direction": request.change_direction,
        "limit": request.limit,
    }

def build_clarification_context(
    previous_context: dict | None,
    request: MetricRequest,
) -> dict:
    """
    Preserve the current conversation plus the incomplete
    request that SKUba is asking the user to clarify.
    """

    previous_context = previous_context or {}

    return {
        "state": previous_context.get("state", {}),
        "summary": previous_context.get("summary", ""),
        "pending_request": build_pending_request(request),
        "clarification_field": request.clarification_field,
    }