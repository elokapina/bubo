import requests
import json

def get_headers(Config):
    headers = {
        'Pindora-Api-Key': f'{Config.pindora_token}',
        'Content-Type': 'application/json'
        }
    return headers


def create_new_key(pindora, year, month, day, start_time, end_time, timezone, Config):
    url = "https://admin.pindora.fi/api/integration/pins"

    payload = json.dumps({
        "validity_rules": [{
            "pindora": {
                "id": f"{pindora}",
            },
            "date_from": f"{year}-{month}-{day}T{start_time}:00+{timezone}:00",
            "date_to": f"{year}-{month}-{day}T{end_time}:00+{timezone}:00",
        }],
        "magic_enabled": True,
    })
    

    response = requests.request("POST", url, headers=get_headers(Config), data=payload)
    if "code" in response.json():
        return response.json()["code"]

def create_permanent_key(pindora, Config):
    url = "https://admin.pindora.fi/api/integration/pins"

    payload = json.dumps({
        "validity_rules": [{
            "pindora": {
                "id": f"{pindora}",
            },
        }],
        "magic_enabled": True,
    })

    response = requests.request("POST", url, headers=get_headers(Config), data=payload)
    if "code" in response.json():
        return response.json()["code"]
    else:
        return "null"
