import requests
import json
from datetime import datetime, timedelta
from pytz import timezone


def get_headers(pindora_token):
    headers = {
        'Pindora-Api-Key': f'{pindora_token}',
        'Content-Type': 'application/vdn.pindora.v1+json'
    }
    return headers


def create_new_key(pindora_id, pindora_token, name, pindora_timezone=None, hours=3):
    url = "https://admin.pindora.fi/api/integration/pins"
    if pindora_timezone is not None:
        now = datetime.now(timezone(pindora_timezone))
    else:
        now = datetime.now()

    to = now + timedelta(hours=hours)

    payload = json.dumps({
        "name": name,
        "validity_rules": [{
            "pindora": {
                "id": f"{pindora_id}",
            },
            "date_from": now.astimezone().isoformat('T', 'seconds'),
            "date_to": to.astimezone().isoformat('T', 'seconds')
        }],
        "magic_enabled": True,
    })

    response = requests.request(
        "POST", url, headers=get_headers(pindora_token), data=payload)
    response.raise_for_status()
    response_json = response.json()

    if "code" in response_json:
        code = response_json["code"]

    if "allowed_for_pindoras" in response_json:
        allowed_for_pindoras = response_json["allowed_for_pindoras"]
        if len(allowed_for_pindoras) > 0:
            if "magic_url" in allowed_for_pindoras[0]:
                magic_url = allowed_for_pindoras[0]["magic_url"]

    return code, magic_url
