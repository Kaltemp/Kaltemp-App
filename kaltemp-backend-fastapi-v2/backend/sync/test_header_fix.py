import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"), override=True)
API_KEY = os.getenv("ENVIAME_API_KEY")

url = "https://api.enviame.io/api/v1/prices"
headers = {
    "x-api-key": API_KEY,
    "Accept": "application/json",
}
params = {
    "from_place": "Santiago",
    "to_place": "Providencia",
    "weight": 1.0, "length": 10, "width": 10, "height": 10,
}

res = requests.get(url, headers=headers, params=params, timeout=15)
print(f"Status: {res.status_code}")
print(res.text[:1500])