from openai import OpenAI
from dotenv import load_dotenv

from .schemas import MetricRequest

load_dotenv()
client = OpenAI()

def parse_metric_request(
    user_message: str,
    context: dict | None = None,
) -> MetricRequest:
    context = context or {}

    response = client.responses.parse(
        model="gpt-5.6",
        input=[
            {
                "role": "system",
                "content": """
                You convert user questions about SKUba metrics into MetricRequest.

                Rules:
                - Do not calculate anything.
                - Do not invent metrics or filters.
                - Use prior structured context when a follow-up refers to "that", "it", "those", etc.
                - Correct obvious typos when confidence is high.
                - Normalize:
                "last month" -> L1M
                "last 3 months" -> L3M
                - group_by is only used for explicit breakdown requests like "by chain", "by SKU", or "by DC".
                - If the request cannot be resolved confidently, do not guess.
                - Treat "sales" as unit sales unless the user explicitly asks for dollars, revenue, or sales dollars.
                - If request_type is "clarification":
                - set clarification_field to the specific field that needs clarification
                - set message to a short user-facing clarification question
                - do not invent possible chain, SKU, DC, or distributor values
                - For ranking requests, if the user specifies a number such as "top 5" or "bottom 3", set limit to that number.
                - If the user does not specify a number, leave limit as null.
                - For ranking requests, set ranking_intent based on the user's wording:
                    - highest / most / top -> "highest"
                    - lowest / least / bottom -> "lowest"
                    - best / strongest -> "best"
                    - worst / weakest -> "worst"
                - Do not decide whether "best" or "worst" means ascending or descending. That is determined by the metric definition.
                - For ranking requests, set ranking_intent based on the user's wording:
                    - highest / most / top -> "highest"
                    - lowest / least / bottom -> "lowest"
                    - best / strongest -> "best"
                    - worst / weakest -> "worst"

                - Do not decide whether "best" or "worst" means ascending or descending.
                That is determined by the metric definition.

                - Comparison requests may also include ranking intent.

                - For comparison requests, set comparison_type only when the user communicates a comparison basis:
                    - last year / year-over-year / YoY / a year ago -> "PY"
                    - previous period / prior period -> "PP"
                    - otherwise leave comparison_type=null

                - For comparison requests, set change_direction based on the user's wording:
                    - improved / increased / grew / went up -> "improved"
                    - declined / decreased / fell / dropped / went down -> "declined"
                    - flat / unchanged / no change -> "flat"
                    - otherwise leave change_direction=null

                - A missing period is NOT by itself a reason to return request_type="clarification".
                - If the user is clearly making a comparison request but does not specify a period:
                    - leave period=null
                    - keep request_type="comparison"

                - If the user does not specify a comparison basis:
                    - leave comparison_type=null
                    - do not ask for clarification

                - If the user explicitly names a calendar year, set year to that year.

                - For calendar periods Q1, Q2, Q3, Q4, H1, H2, or FY:
                    - use the explicitly stated year when present
                    - if the user says "this year", use the current year

                - Do not invent a year for rolling periods like L1M, L3M, L1Q, etc.

                - Examples:
                    - "which chains improved the most vs last quarter?"
                        -> request_type="comparison"
                        -> group_by="chain"
                        -> ranking_intent="best"
                        -> change_direction="improved"
                        -> comparison_type="PP"

                    - "which SKUs declined the most vs last year?"
                        -> request_type="comparison"
                        -> group_by="sku"
                        -> ranking_intent="worst"
                        -> change_direction="declined"
                        -> comparison_type="PY"

                CONVERSATION CONTEXT

                The context may contain:
                - state: the last completed analytics state
                - summary: a short summary of the conversation
                - pending_request: an incomplete request waiting for clarification
                - clarification_field: the field SKUba asked the user to clarify

                If pending_request is present:

                - Treat the user's latest message as an answer to that pending clarification unless the user clearly starts a new topic.
                - Preserve all non-null fields from pending_request unless the user explicitly changes them.
                - Use the user's reply to fill or update the clarification_field.
                - Do not reinterpret a short clarification answer such as "units", "Sprouts", "last quarter", or a SKU name as a standalone request.
                - Once the clarification is resolved, set request_type to pending_request.intended_request_type.

                If there is no pending_request:

                - Use state and summary to understand conversational references and follow-up questions.
                - Treat structured state as authoritative when it conflicts with the summary.
                - Determine whether the user is modifying/referring to the previous analysis or starting a new request.

                - If the user is modifying or referring to the previous analysis, set use_context=true.
                - If the user is clearly starting a new standalone request, set use_context=false.

                When use_context=true:

                - Populate only the fields the user explicitly states, changes, or clearly refers to.
                - Leave unrelated fields null.
                - Do not reconstruct the full previous request from context; the backend will preserve unchanged fields.

                Examples:

                Previous analysis:
                metric=units, period=Q3, year=2026, chain=SPROUTS

                "What about Whole Foods?"
                → use_context=true, chain=WHOLE FOODS

                "What about velocity?"
                → use_context=true, metric=velocity

                "Do Q2 instead"
                → use_context=true, period=Q2

                "Change the period from Q3 2026 to Q2 2026"
                → use_context=true, period=Q2, year=2026

                If the user explicitly states a calendar year, populate year.
                If the user does not state a year, leave year null.
                """,
            },
            {
                "role": "user",
                "content": f"""
    Prior context:
    {context}

    New message:
    {user_message}
    """,
                },
            ],
            text_format=MetricRequest,
            store=False,
        )

    return response.output_parsed

def main():
    test_prompts = [
        "what was our reorder rate at sprouts last quarter?",
        "show me sprouts sales last quarter",
        "what was fill rate over the last two quarters?",
    ]

    for prompt in test_prompts:
        print("\n" + "=" * 70)
        print("PROMPT:")
        print(prompt)

        request = parse_metric_request(prompt)

        print("\nPARSED:")
        print(request)


if __name__ == "__main__":
    main()