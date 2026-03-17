# main.py
from datetime import datetime
import pandas as pd
import os
from azure_common import get_credential, get_all_subscriptions

if __name__ == "__main__":
    credential = get_credential()
    subscriptions = get_all_subscriptions(credential)

    if not subscriptions:
        print("\n沒有取得訂閱，請檢查：")
        print("1. az login 是否成功")
        print("2. config.py 是否正確")
        print("3. 服務主體是否有至少 Reader 權限")
    else:
        df = pd.DataFrame(subscriptions)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"azure_subscriptions_{ts}.xlsx"
        try:
            df.to_excel(filename, index=False, engine='openpyxl')
            print(f"已儲存至：{os.path.abspath(filename)}")
        except Exception as e:
            print(f"儲存失敗：{e}")