import requests
import json
from config import Config
def get_headers():
    headers = {
        'Pindora-Api-Key': f'{Config.pindora_token}',
        'Content-Type': 'application/json'
        }
    return headers
def create_new_key(pindora, month, day, start_time, end_time, timezone):
    url = "https://admin.pindora.fi/api/integration/pins"

    payload = json.dumps({
    "validity_rules": [
        {
        "pindora": {
            "id": f"{pindora}"
        },
        "date_from": f"2022-{month}-{day}T{start_time}:00+{timezone}:00",
        "date_to": f"2022-{month}-{day}T{end_time}:00+{timezone}:00"
        }
    ],
    "magic_enabled": True
    })
    

    response = requests.request("POST", url, headers=get_headers(), data=payload)
    if "code" in response.json():
        return response.json()["code"]
    else:
        return "null"
def create_permanent_key(pindora):
    url = "https://admin.pindora.fi/api/integration/pins"

    payload = json.dumps({
    "validity_rules": [
        {
        "pindora": {
            "id": f"{pindora}"
        }}
    ],
    "magic_enabled": True
    })

    response = requests.request("POST", url, headers=get_headers(), data=payload)
    if "code" in response.json():
        return response.json()["code"]
    else:
        return "null"
