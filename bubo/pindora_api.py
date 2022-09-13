import requests
import json
def create_new_key(pindora, start_time_month, start_time_day, start_time_end, end_time_month, end_time_day, end_time_end, timezone):
    url = "https://admin.pindora.fi/api/integration/pins"

    payload = json.dumps({
    "validity_rules": [
        {
        "pindora": {
            "id": f"{pindora}"
        },
        "date_from": f"2022-{start_time_month}-{start_time_day}T{start_time_end}:00+{timezone}:00",
        "date_to": f"2022-{end_time_month}-{end_time_day}T{end_time_end}:00+{timezone}:00"
        }
    ],
    "magic_enabled": True
    })
    headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    if "code" in response.json():
        return response.json()["code"]
    else:
        return "000000"
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
    headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    if "code" in response.json():
        return response.json()["code"]
    else:
        return "000000"
