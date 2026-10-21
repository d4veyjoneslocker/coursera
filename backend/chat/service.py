from .parser import parse_metric_request
from .tools import (
    get_metric,
    rank_metric,
    compare_metric_tool,
    get_clarification_options,
)
from .phraser import phrase_result
from .context import build_conversation_context, build_clarification_context, merge_request_with_context


def phrase_success(
    user_message: str,
    result: dict,
    request,
    previous_context: dict | None = None,
):
    answer = phrase_result(
        user_message=user_message,
        result=result,
    )

    conversation_context = build_conversation_context(
        previous_context=previous_context,
        request=request,
        result=result,
        user_message=user_message,
        answer=answer,
    )

    return {
        "status": "success",
        "answer": answer,
        "result": result,
        "context": conversation_context,
    }

def ask_metric(
    org_id: str,
    user_message: str,
    context: dict | None = None,
):
    request = parse_metric_request(
        user_message=user_message,
        context=context,
    )

    request = merge_request_with_context(
        request=request,
        context=context,
    )

    if request.request_type == "clarification":
        clarification_context = build_clarification_context(
            previous_context=context,
            request=request,
        )

        return {
            "status": "clarification",
            "clarification_field": request.clarification_field,
            "message": request.message,
            "options": get_clarification_options(
                org_id=org_id,
                request=request,
            ),
            "request": request.model_dump(),
            "context": clarification_context,
        }

    if request.request_type == "ranking":
        result = rank_metric(
            org_id=org_id,
            request=request,
        )

        return phrase_success(
            user_message=user_message,
            result=result,
            request=request,
            previous_context=context,
        )

    if request.request_type == "comparison":
        result = compare_metric_tool(
            org_id=org_id,
            request=request,
        )

        return phrase_success(
            user_message=user_message,
            result=result,
            request=request,
            previous_context=context,
        )

    if request.request_type != "metric":
        return {
            "status": request.request_type,
            "request": request.model_dump(),
            "context": context,
        }

    try:
        result = get_metric(
            org_id=org_id,
            request=request,
        )

        return phrase_success(
            user_message=user_message,
            result=result,
            request=request,
            previous_context=context,
        )

    except ValueError as e:
        return {
            "status": "clarification",
            "message": str(e),
            "options": None,
            "request": request.model_dump(),
            "context": context,
        }
    
def main():
    test_prompts = [
        "which chains improved the most in velocity vs last quarter?",
        "which skus declined the most in units vs last year?",
        "which dcs stayed flat in fill rate vs the prior period?",
        "which chains improved the least in units vs the prior period?",
        "which skus had the biggest increase in velocity vs last year?",
        "which chains had the biggest drop in units vs last quarter?",
    ]

    for prompt in test_prompts:
        print("\n" + "=" * 80)
        print("PROMPT:")
        print(prompt)

        try:
            result = ask_metric(
                org_id="67a96381-5014-4a9b-bfe8-a14e6da5affe",
                user_message=prompt,
            )

            print("\nRESULT:")
            print(result)

        except Exception as e:
            print("\nERROR:")
            print(type(e).__name__, str(e))


if __name__ == "__main__":
    main()