#!/usr/bin/env python3
"""
Importa FlowSalvaAttestazione_1_0_0_0.zip su Dataverse via API.
Le tabelle sono già state create da auth_and_import.py.

Utilizzo:
    python3 import_flow_solution.py
    oppure:
    DATAVERSE_TOKEN=<token> python3 import_flow_solution.py
"""

import base64
import json
import os
import sys
import time
import uuid

import requests

TENANT_ID     = "761de76f-3d5c-4174-917c-5ad4d06360cb"
CLIENT_ID     = "1950a258-227b-4e31-a9cf-717495945fc2"
DATAVERSE_URL = "https://org8aea528f.crm4.dynamics.com"
SCOPE         = f"{DATAVERSE_URL}/.default"
TOKEN_URL     = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
DEVICE_URL    = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/devicecode"
API_BASE      = f"{DATAVERSE_URL}/api/data/v9.2"
ZIP_PATH      = "FlowSalvaAttestazione_1_0_0_0.zip"
CONN_REF      = "hkt_DataverseAttestazioniConn"
CONN_ID       = "05d3d6b8af4c42eaac7826f104a3c4bf"
CONNECTOR_API = "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps"


def get_token():
    env_tok = os.environ.get("DATAVERSE_TOKEN", "").strip()
    if env_tok:
        print("✓ Token da DATAVERSE_TOKEN")
        return env_tok
    r = requests.post(DEVICE_URL, data={"client_id": CLIENT_ID, "scope": SCOPE})
    r.raise_for_status()
    info = r.json()
    print(f"\n{'='*60}")
    print(f"  Apri: {info['verification_uri']}")
    print(f"  Codice: {info['user_code']}")
    print(f"{'='*60}\n")
    interval, deadline = int(info.get("interval", 5)), time.time() + int(info.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(interval)
        resp = requests.post(TOKEN_URL, data={
            "client_id": CLIENT_ID,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": info["device_code"],
        }).json()
        if "access_token" in resp:
            print("✓ Autenticazione completata")
            return resp["access_token"]
        if resp.get("error") == "slow_down":
            interval += 5
        elif resp.get("error") != "authorization_pending":
            print(f"✗ {resp.get('error_description', resp.get('error'))}")
            sys.exit(1)
    sys.exit(1)


def hdrs(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }


def import_solution(token):
    print(f"Importo {ZIP_PATH} ...")
    with open(ZIP_PATH, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    import_job_id = str(uuid.uuid4())
    r = requests.post(f"{API_BASE}/ImportSolution", headers=hdrs(token), json={
        "CustomizationFile": content,
        "OverwriteUnmanagedCustomizations": True,
        "PublishWorkflows": True,
        "ImportJobId": import_job_id,
    })
    if r.status_code in (200, 204):
        print("✓ Solution importata")
        return True
    err = r.json().get("error", {})
    print(f"✗ Errore ({r.status_code}): {err.get('message', r.text[:300])}")
    return False


def update_conn_ref(token):
    print("Collego connection reference ...")
    r = requests.get(
        f"{API_BASE}/connectionreferences"
        f"?$filter=connectionreferencelogicalname eq '{CONN_REF}'"
        f"&$select=connectionreferenceid",
        headers=hdrs(token)
    )
    if r.status_code != 200 or not r.json().get("value"):
        print("  Non trovata (attendere qualche secondo e riprovare)")
        return
    ref_id = r.json()["value"][0]["connectionreferenceid"]
    r2 = requests.patch(
        f"{API_BASE}/connectionreferences({ref_id})",
        headers=hdrs(token),
        json={"connectionid": f"{CONNECTOR_API}/connections/{CONN_ID}"},
    )
    if r2.status_code in (200, 204):
        print("✓ Connection reference collegata")
    else:
        print(f"✗ Errore ({r2.status_code}): {r2.text[:200]}")


def main():
    if not os.path.exists(ZIP_PATH):
        print(f"Errore: {ZIP_PATH} non trovato.")
        print("Esegui prima: python3 create_flow_solution.py")
        sys.exit(1)

    token = get_token()
    ok = import_solution(token)
    if not ok:
        sys.exit(1)

    print("Attendo propagazione (10s) ...")
    time.sleep(10)
    update_conn_ref(token)
    print("\n✓ Flow importato e connection reference collegata.")
    print("Prossimo passo: push + publish dell'agente Copilot Studio")


if __name__ == "__main__":
    main()
