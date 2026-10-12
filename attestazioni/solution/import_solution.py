#!/usr/bin/env python3
"""
Importa HktAttestazioniSoa via Dataverse Web API.

Richiede un access token valido per l'ambiente Dataverse.
Per ottenerlo con Azure CLI:
    az account get-access-token --resource https://org8aea528f.crm4.dynamics.com \
        --tenant 761de76f-3d5c-4174-917c-5ad4d06360cb --query accessToken -o tsv

Oppure passalo come variabile d'ambiente:
    DATAVERSE_TOKEN=<token> python3 import_solution.py

Utilizzo:
    python3 import_solution.py [--token <access_token>] [--zip <path>]
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

DATAVERSE_URL = "https://org8aea528f.crm4.dynamics.com"
SOLUTION_ZIP  = "HktAttestazioniSoa_1_0_0_0.zip"
CONN_REF_LOGICAL = "hkt_DataverseAttestazioniConn"
CONNECTION_ID    = "05d3d6b8af4c42eaac7826f104a3c4bf"
ENV_ID           = "8888de39-af12-ed69-be38-971c5020e54b"


def get_token_from_az():
    """Prova a ottenere il token tramite Azure CLI."""
    try:
        result = subprocess.run(
            ["az", "account", "get-access-token",
             "--resource", DATAVERSE_URL,
             "--tenant", "761de76f-3d5c-4174-917c-5ad4d06360cb",
             "--query", "accessToken", "-o", "tsv"],
            capture_output=True, text=True, timeout=30
        )
        token = result.stdout.strip()
        if token and not token.startswith("ERROR"):
            print("✓ Token ottenuto tramite Azure CLI")
            return token
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def api_call(token, method, path, body=None):
    url = f"{DATAVERSE_URL}/api/data/v9.2/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw.decode(errors="replace")}


def import_solution(token, zip_path):
    print(f"\nImporting {zip_path} ...")
    with open(zip_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    body = {
        "CustomizationFile": content,
        "OverwriteUnmanagedCustomizations": True,
        "PublishWorkflows": True,
        "ImportJobId": None,
    }
    status, resp = api_call(token, "POST", "ImportSolution", body)
    if status in (200, 204):
        print("✓ Solution importata con successo")
        return True
    else:
        print(f"✗ Errore import ({status}): {json.dumps(resp, indent=2)}")
        return False


def update_connection_reference(token):
    """Collega la connection reference alla connessione Dataverse."""
    print(f"\nCercando connection reference '{CONN_REF_LOGICAL}' ...")
    status, resp = api_call(
        token, "GET",
        f"connectionreferences?$filter=connectionreferencelogicalname eq '{CONN_REF_LOGICAL}'&$select=connectionreferenceid,connectionreferencelogicalname"
    )
    if status != 200 or not resp.get("value"):
        print(f"  Connection reference non trovata (potrebbe richiedere qualche secondo dopo l'import).")
        return False

    ref_id = resp["value"][0]["connectionreferenceid"]
    print(f"  Found: {ref_id}")

    conn_id_full = f"/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps/connections/{CONNECTION_ID}"
    patch_status, patch_resp = api_call(
        token, "PATCH",
        f"connectionreferences({ref_id})",
        {"connectionid": conn_id_full}
    )
    if patch_status in (200, 204):
        print("✓ Connection reference collegata alla connessione Dataverse")
        return True
    else:
        print(f"✗ Errore aggiornamento connection reference ({patch_status}): {json.dumps(patch_resp, indent=2)}")
        return False


def verify_tables(token):
    """Verifica che le tabelle siano state create e stampa i loro EntitySetName."""
    print("\nVerifica tabelle create ...")
    for logical in ["hkt_attestazionesoa", "hkt_certificazionesoa"]:
        status, resp = api_call(
            token, "GET",
            f"EntityDefinitions?$filter=LogicalName eq '{logical}'&$select=LogicalName,EntitySetName,DisplayName"
        )
        if status == 200 and resp.get("value"):
            e = resp["value"][0]
            name = e.get("DisplayName", {}).get("UserLocalizedLabel", {}).get("Label", "")
            print(f"  ✓ {logical} → EntitySetName: {e.get('EntitySetName')} ({name})")
        else:
            print(f"  ✗ {logical} non trovata")


def main():
    parser = argparse.ArgumentParser(description="Importa solution HktAttestazioniSoa su Dataverse")
    parser.add_argument("--token", help="Access token Bearer per Dataverse")
    parser.add_argument("--zip", default=SOLUTION_ZIP, help=f"Path ZIP (default: {SOLUTION_ZIP})")
    args = parser.parse_args()

    # Ottieni token
    token = args.token or os.environ.get("DATAVERSE_TOKEN") or get_token_from_az()
    if not token:
        print("Errore: nessun access token disponibile.")
        print("Ottienilo con:")
        print(f"  az account get-access-token --resource {DATAVERSE_URL} \\")
        print(f"      --tenant 761de76f-3d5c-4174-917c-5ad4d06360cb --query accessToken -o tsv")
        print("Poi esegui:")
        print(f"  DATAVERSE_TOKEN=<token> python3 {sys.argv[0]}")
        sys.exit(1)

    zip_path = args.zip
    if not os.path.exists(zip_path):
        print(f"Errore: file non trovato: {zip_path}")
        sys.exit(1)

    # Import
    ok = import_solution(token, zip_path)
    if not ok:
        sys.exit(1)

    # Attendi che le risorse siano disponibili
    print("\nAttendo propagazione (10s) ...")
    time.sleep(10)

    # Collega connection reference
    update_connection_reference(token)

    # Verifica tabelle
    verify_tables(token)

    print("\nDone. Prossimo passo:")
    print("  Torna in Copilot Studio e fai push + publish dell'agente")
    print("  per attivare la chiamata al flow.")


if __name__ == "__main__":
    main()
