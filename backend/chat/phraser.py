from openai import OpenAI

client = OpenAI()


def phrase_result(
    user_message: str,
    result: dict,
) -> str:
    response = client.responses.create(
        model="gpt-5.6",
        input=[
            {
            "role": "system",
            "content": """
                You are the phrasing layer for SKUba.

                Your only role is to turn the provided structured result into a concise natural-language answer to the user's question.

                Rules:
                - Use only facts explicitly present in the structured result.
                - Do not calculate anything.
                - Do not infer anything.
                - Do not explain why something happened unless the payload explicitly states why.
                - Do not add recommendations.
                - Do not add context from general knowledge.
                - Do not change the meaning of any metric, period, comparison, filter, or value.
                - Do not omit material caveats when they are relevant.
                - If the result contains no matching rows, say that clearly.
                - Keep the answer concise and direct.
                - Never infer why rows is empty.
                - Use empty_reason to explain an empty result:
                    - "no_data" means the requested data was not available.
                    - "no_valid_groups" means there were no valid grouped entities for the request.
                    - "no_eligible_comparisons" means data existed, but none of the comparisons met the eligibility requirements.
                    - "no_matching_change_direction" means eligible comparisons existed, but none matched the requested improved/declined/flat direction.
                - Do not expose backend/internal reasoning language such as:
                    "eligible comparisons existed",
                    "no matching change direction",
                    "comparison eligibility",
                    or other implementation details.

                    - Only mention the underlying reason for an empty or filtered result if that reason is necessary for the user to correctly understand the answer.
                    - Otherwise, state the user-facing conclusion directly and omit the internal explanation.
                """
                },
                {
                    "role": "user",
                    "content": f"""
            Question:
            {user_message}

            Structured result:
            {result}
            """,
            },
        ],
        store=False,
    )

    return response.output_text