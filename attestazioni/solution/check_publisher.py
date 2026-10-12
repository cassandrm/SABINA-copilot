#!/usr/bin/env python3
"""Stampa i dettagli del publisher 'hkt' nell'ambiente Dataverse."""

import os, sys, time, json, requests

TENANT_ID  = "761de76f-3d5c-4174-917c-5ad4d06360cb"
CLIENT_ID  = "1950a258-227b-4e31-a9cf-717495945fc2"
DV_URL     = "https://org8aea528f.crm4.dynamics.com"
SCOPE      = f"{DV_URL}/.default"
TOKEN_URL  = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
DEVICE_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/devicecode"

def get_token():
    t = os.environ.get("DATAVERSE_TOKEN","").strip()
    if t: return t
    r = requests.post(DEVICE_URL, data={"client_id":CLIENT_ID,"scope":SCOPE}); r.raise_for_status()
    i = r.json()
    print(f"\nApri: {i['verification_uri']}  Codice: {i['user_code']}\n")
    interval, deadline = int(i.get("interval",5)), time.time()+int(i.get("expires_in",900))
    while time.time() < deadline:
        time.sleep(interval)
        resp = requests.post(TOKEN_URL, data={"client_id":CLIENT_ID,"grant_type":"urn:ietf:params:oauth:grant-type:device_code","device_code":i["device_code"]}).json()
        if "access_token" in resp: return resp["access_token"]
        if resp.get("error") not in ("authorization_pending","slow_down"): sys.exit(1)
    sys.exit(1)

token = get_token()
r = requests.get(f"{DV_URL}/api/data/v9.2/publishers?$filter=uniquename eq 'hkt'",
    headers={"Authorization":f"Bearer {token}","Accept":"application/json","OData-Version":"4.0"})
data = r.json()
if data.get("value"):
    print("Publisher 'hkt' trovato:")
    print(json.dumps(data["value"][0], indent=2, ensure_ascii=False))
else:
    print("Publisher 'hkt' NON trovato nell'ambiente.")
    r2 = requests.get(f"{DV_URL}/api/data/v9.2/publishers?$select=uniquename,customizationprefix,friendlyname",
        headers={"Authorization":f"Bearer {token}","Accept":"application/json","OData-Version":"4.0"})
    print("Publisher disponibili:")
    for p in r2.json().get("value",[]):
        print(f"  {p['uniquename']} / {p['customizationprefix']} — {p['friendlyname']}")
