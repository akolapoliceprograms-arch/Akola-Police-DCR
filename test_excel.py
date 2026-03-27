import pandas as pd
import io
import os

try:
    data = [{"Test": "Data"}]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    # Long sheet name
    long_name = "Murtizapur Rural (मुर्तीजापूर ग्रामीण) History"
    print(f"Sheet name length: {len(long_name)}")
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=long_name)
    print("Success")
except Exception as e:
    print(f"Failed with: {e}")
