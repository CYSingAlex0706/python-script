# azure_common.py
# 共用：認證 + 取得所有訂閱

import os
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.subscription import SubscriptionClient

try:
    import config
    HAS_CONFIG = True
    print("✓ 已載入 config.py")
except ImportError:
    HAS_CONFIG = False
    print("ℹ 沒有 config.py，將使用 DefaultAzureCredential")


def get_credential():
    if HAS_CONFIG:
        try:
            cred = ClientSecretCredential(
                tenant_id     = config.TENANT_ID,
                client_id     = config.CLIENT_ID,
                client_secret = config.CLIENT_SECRET,
            )
            print("✓ 使用 config.py 中的服務主體認證")
            return cred
        except Exception as e:
            print(f"✗ 服務主體認證失敗：{e} → 改用預設認證")

    print("→ 使用 DefaultAzureCredential（az login / env / managed identity）")
    return DefaultAzureCredential()


def get_all_subscriptions(credential=None):
    if credential is None:
        credential = get_credential()

    try:
        client = SubscriptionClient(credential)
        subs = client.subscriptions.list()

        result = [
            {
                'subscription_id': s.subscription_id,
                'display_name': s.display_name or "(無名稱)",
                'state': s.state.value if hasattr(s.state, 'value') else str(s.state),
            }
            for s in subs
        ]

        print(f"✓ 成功取得 {len(result)} 個訂閱")
        return result

    except Exception as e:
        print(f"✗ 取得訂閱失敗：{str(e)}")
        if "AuthorizationFailed" in str(e):
            print("   → 請確認認證至少有 Reader 角色")
        return []