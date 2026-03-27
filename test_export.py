import requests
try:
    response = requests.get("http://localhost:8001/api/export/unit/1")
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
