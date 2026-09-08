from pprint import pprint

from backend.onboarding.sku_reconciliation import (
    get_reconciliation_payload,
)


org_id = "0db03f67-b13b-438a-ab92-f808ca544ff8"

payload = get_reconciliation_payload(org_id)

products = payload["products"]
matches = payload["suggested_matches"]


print("\n===== SKU RECONCILIATION TEST =====")
print(f"Total products: {len(products)}")
print(f"Auto matches: {len(matches)}")


print("\n===== AUTO MATCHES =====")

for match in matches:
    pprint(match)


print("\n===== VALIDATION =====")

assert len(products) > 0

for match in matches:
    assert match["match_type"] == "upc"
    assert match["confidence"] == "high"
    assert match["normalized_upc"]
    assert len(match["products"]) >= 2

    sources = {
        product["source"]
        for product in match["products"]
    }

    assert len(sources) >= 2

print("✅ Auto-match validation complete")