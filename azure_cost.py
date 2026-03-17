# azure_cost.py
# 查詢 Microsoft Defender for Cloud 相關費用（使用 Cost Management API）

from datetime import datetime, timedelta
import pandas as pd
import os
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import (
    QueryDefinition, QueryTimePeriod, QueryDataset, QueryAggregation,
    QueryGrouping
)
from azure_common import get_credential, get_all_subscriptions

def get_defender_cost(credential, sub_id, start_date, end_date):
    scope = f"/subscriptions/{sub_id}"
    client = CostManagementClient(credential)

    query = QueryDefinition(
        type="Usage",
        timeframe="Custom",
        time_period=QueryTimePeriod(from_property=start_date, to=end_date),
        dataset=QueryDataset(
            granularity="Daily",
            aggregation={"totalCost": QueryAggregation(name="PreTaxCost", function="Sum")},
            grouping=[
                QueryGrouping(type="Dimension", name="ServiceName"),
                QueryGrouping(type="Dimension", name="Product"),
                QueryGrouping(type="Dimension", name="MeterCategory")
            ]
        )
    )

    try:
        result = client.query.usage(scope=scope, parameters=query)
        rows = result.rows or []
        columns = {col.name: col for col in result.columns}

        total_defender = 0.0
        details = []

        for row in rows:
            row_dict = dict(zip([c.name for c in result.columns], row))
            cost = row_dict.get("PreTaxCost", 0) or 0

            product = str(row_dict.get("Product", "")).lower()
            meter_cat = str(row_dict.get("MeterCategory", "")).lower()
            service_name = str(row_dict.get("ServiceName", "")).lower()

            keywords = ["defender", "security center", "microsoft defender", "mdc", "azure defender"]
            if any(kw in text for kw in keywords for text in [product, meter_cat, service_name]):
                total_defender += cost
                details.append({
                    "Date": row_dict.get("Date", ""),
                    "SubscriptionId": sub_id,
                    "Product": row_dict.get("Product", ""),
                    "MeterCategory": row_dict.get("MeterCategory", ""),
                    "ServiceName": row_dict.get("ServiceName", ""),
                    "Cost": cost
                })

        currency = columns.get("PreTaxCost", {}).units if "PreTaxCost" in columns else "未知"

        return {
            "total_defender_cost": round(total_defender, 4),
            "currency": currency,
            "details": details,
            "period": f"{start_date.date()} 至 {end_date.date()}"
        }

    except Exception as e:
        err = str(e)
        print(f"  ✗ 查詢失敗 ({sub_id})：{err}")
        if "AuthorizationFailed" in err or "permissions" in err.lower():
            print("   → 需要 Cost Management Reader 角色")
        return {"total_defender_cost": 0.0, "currency": "N/A", "details": [], "period": "失敗"}

if __name__ == "__main__":
    cred = get_credential()
    subs = get_all_subscriptions(cred)

    if not subs:
        print("無法取得訂閱，結束")
        exit(1)

    end = datetime.utcnow()
    start = end - timedelta(days=30)

    print(f"\n查詢 Defender for Cloud 費用：{start.date()} ~ {end.date()}\n")

    summary_rows = []
    all_details = []

    for sub in subs:
        sub_id = sub['subscription_id']
        name = sub['display_name']
        print(f"→ {name} ({sub_id})")

        info = get_defender_cost(cred, sub_id, start, end)
        summary_rows.append({
            "訂閱名稱": name,
            "訂閱 ID": sub_id,
            "Defender 費用": info["total_defender_cost"],
            "貨幣": info["currency"],
            "期間": info["period"]
        })
        all_details.extend(info["details"])

    df_summary = pd.DataFrame(summary_rows)
    grand_total = df_summary["Defender 費用"].sum()

    print("\n" + "="*80)
    print("Microsoft Defender for Cloud 費用總覽（最近 30 天）")
    print("="*80)
    print(df_summary.to_string(index=False))
    print(f"\n總計 Defender 費用：{grand_total:.4f} {df_summary['貨幣'].iloc[0] if not df_summary.empty else 'N/A'}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    f_summary = f"defender_summary_{ts}.xlsx"
    f_details = f"defender_details_{ts}.xlsx"

    df_summary.to_excel(f_summary, index=False, engine='openpyxl')
    if all_details:
        pd.DataFrame(all_details).to_excel(f_details, index=False, engine='openpyxl')

    print(f"\n已儲存：")
    print(f"  總覽 → {os.path.abspath(f_summary)}")
    if all_details:
        print(f"  明細 → {os.path.abspath(f_details)}")
    else:
        print("  （無 Defender 相關費用明細）")