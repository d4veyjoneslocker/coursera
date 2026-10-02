import json

from backend.email.monthly_brief import (
    build_monthly_brief,
)


ORG_ID = "67a96381-5014-4a9b-bfe8-a14e6da5affe"


brief = build_monthly_brief(
    org_id=ORG_ID,
    end_month="2026-09",
)


with open(
    "backend/email/smearcase_september_brief.json",
    "w",
) as f:
    json.dump(
        brief,
        f,
        indent=2,
    )


print(
    json.dumps(
        brief,
        indent=2,
    )
)