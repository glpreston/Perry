import requests


def get_models_for_server(host):
    try:
        resp = requests.get(f"{host}/api/tags", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []
    return []


def check_server_status(host):
    try:
        resp = requests.get(f"{host}/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False
