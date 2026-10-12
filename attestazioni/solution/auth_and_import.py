#!/usr/bin/env python3
"""
Crea le tabelle Dataverse per AttestazioniAgent via Metadata API.

Crea:
  - hkt_attestazionesoa  (Attestazione SOA)
  - hkt_certificazionesoa (Certificazione SOA, lookup su AttestazioneSoa)

Utilizzo:
    python3 auth_and_import.py
    oppure:
    DATAVERSE_TOKEN=<token> python3 auth_and_import.py
"""

import json
import os
import sys
import time
import uuid

import requests

TENANT_ID     = "761de76f-3d5c-4174-917c-5ad4d06360cb"
CLIENT_ID     = "1950a258-227b-4e31-a9cf-717495945fc2"
ENV_ID        = "8888de39-af12-ed69-be38-971c5020e54b"
DATAVERSE_URL = "https://org8aea528f.crm4.dynamics.com"
SCOPE         = f"{DATAVERSE_URL}/.default"
PA_SCOPE      = "https://service.flow.microsoft.com/.default"
TOKEN_URL     = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
DEVICE_URL    = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/devicecode"
API_BASE      = f"{DATAVERSE_URL}/api/data/v9.2"
PA_BASE       = "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple"
LANG          = 1040
ATT_SET       = "hkt_attestazionesoas"
CERT_SET      = "hkt_certificazionesoas"
CONN_ID       = "05d3d6b8af4c42eaac7826f104a3c4bf"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_token() -> str:
    env_token = os.environ.get("DATAVERSE_TOKEN", "").strip()
    if env_token:
        print("✓ Token da variabile DATAVERSE_TOKEN")
        return env_token

    r = requests.post(DEVICE_URL, data={"client_id": CLIENT_ID, "scope": SCOPE})
    r.raise_for_status()
    info = r.json()
    print()
    print("=" * 60)
    print(f"  Apri: {info['verification_uri']}")
    print(f"  Codice: {info['user_code']}")
    print("=" * 60)
    print()
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
    print("✗ Timeout")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Dataverse helpers
# ---------------------------------------------------------------------------

def hdrs(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }


def get(token, path):
    r = requests.get(f"{API_BASE}/{path}", headers=hdrs(token))
    return r.status_code, r.json() if r.content else {}


def post(token, path, body):
    r = requests.post(f"{API_BASE}/{path}", headers=hdrs(token), json=body)
    return r.status_code, r.json() if r.content else {}


def label(text):
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [{
            "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
            "Label": text, "LanguageCode": LANG
        }],
        "UserLocalizedLabel": {
            "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
            "Label": text, "LanguageCode": LANG
        }
    }


def req_level(value="None"):
    return {"Value": value, "@odata.type": "Microsoft.Dynamics.CRM.AttributeRequiredLevelManagedProperty"}


# ---------------------------------------------------------------------------
# Attribute builders
# ---------------------------------------------------------------------------

def str_attr(schema, display, maxlen=500, required="None", primary=False):
    a = {
        "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
        "SchemaName": schema,
        "LogicalName": schema.lower(),
        "DisplayName": label(display),
        "RequiredLevel": req_level(required),
        "MaxLength": maxlen,
        "FormatName": {"Value": "Text"},
    }
    if primary:
        a["IsPrimaryName"] = True
    return a


def memo_attr(schema, display, maxlen=8000):
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
        "SchemaName": schema,
        "LogicalName": schema.lower(),
        "DisplayName": label(display),
        "RequiredLevel": req_level(),
        "MaxLength": maxlen,
    }


def date_attr(schema, display):
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
        "SchemaName": schema,
        "LogicalName": schema.lower(),
        "DisplayName": label(display),
        "RequiredLevel": req_level(),
        "Format": "DateOnly",
        "DateTimeBehavior": {"Value": "DateOnly"},
    }


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------

def entity_exists(token, logical_name):
    status, resp = get(token, f"EntityDefinitions?$filter=LogicalName eq '{logical_name}'&$select=LogicalName,EntitySetName")
    return status == 200 and bool(resp.get("value"))


def create_attestazione_soa(token):
    name = "hkt_attestazionesoa"
    if entity_exists(token, name):
        print(f"  → {name} già esistente, skip")
        return True

    print(f"  Creo {name} ...")
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": "hkt_AttestazioneSoa",
        "LogicalName": name,
        "DisplayName": label("Attestazione SOA"),
        "DisplayCollectionName": label("Attestazioni SOA"),
        "Description": label("Attestazione SOA estratta da documento"),
        "PrimaryNameAttribute": "hkt_denominazione",
        "OwnershipType": "UserOwned",
        "HasActivities": False,
        "HasNotes": False,
        "IsActivity": False,
        "Attributes": [
            str_attr("hkt_Denominazione",          "Denominazione",         500, "Recommended", primary=True),
            str_attr("hkt_CodiceFiscale",          "Codice Fiscale",         50),
            str_attr("hkt_PartitaIva",             "Partita IVA",            50),
            str_attr("hkt_Sede",                   "Sede",                  200),
            str_attr("hkt_Cap",                    "CAP",                    10),
            str_attr("hkt_Provincia",              "Provincia",             100),
            str_attr("hkt_Indirizzo",              "Indirizzo",             500),
            str_attr("hkt_RappresentanteLegale",   "Rappresentante Legale", 300),
            date_attr("hkt_DataScadenza",          "Data Scadenza"),
            memo_attr("hkt_JsonOriginale",         "JSON Originale"),
        ]
    }
    status, resp = post(token, "EntityDefinitions", body)
    if status in (200, 201, 204):
        print(f"  ✓ {name} creata")
        return True
    print(f"  ✗ Errore ({status}): {resp.get('error', {}).get('message', resp)}")
    return False


def create_certificazione_soa(token):
    name = "hkt_certificazionesoa"
    if entity_exists(token, name):
        print(f"  → {name} già esistente, skip")
        return True

    print(f"  Creo {name} ...")
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": "hkt_CertificazioneSoa",
        "LogicalName": name,
        "DisplayName": label("Certificazione SOA"),
        "DisplayCollectionName": label("Certificazioni SOA"),
        "Description": label("Coppia categoria/classificazione di un'attestazione SOA"),
        "PrimaryNameAttribute": "hkt_categoria",
        "OwnershipType": "UserOwned",
        "HasActivities": False,
        "HasNotes": False,
        "IsActivity": False,
        "Attributes": [
            str_attr("hkt_Categoria",      "Categoria",      200, "Recommended", primary=True),
            str_attr("hkt_Classificazione","Classificazione", 100),
        ]
    }
    status, resp = post(token, "EntityDefinitions", body)
    if status in (200, 201, 204):
        print(f"  ✓ {name} creata")
        return True
    print(f"  ✗ Errore ({status}): {resp.get('error', {}).get('message', resp)}")
    return False


def create_relationship(token):
    rel_name = "hkt_attestazionesoa_certificazionesoa"
    print(f"  Creo relazione lookup {rel_name} ...")

    # Verifica se esiste già
    status, resp = get(token, f"RelationshipDefinitions?$filter=SchemaName eq '{rel_name}'&$select=SchemaName")
    if status == 200 and resp.get("value"):
        print(f"  → relazione già esistente, skip")
        return True

    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
        "SchemaName": rel_name,
        "ReferencedEntity": "hkt_attestazionesoa",
        "ReferencingEntity": "hkt_certificazionesoa",
        "Lookup": {
            "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
            "SchemaName": "hkt_AttestazioneId",
            "LogicalName": "hkt_attestazioneid",
            "DisplayName": label("Attestazione SOA"),
            "RequiredLevel": req_level(),
        },
        "AssociatedMenuConfiguration": {
            "Behavior": "UseCollectionName",
            "Group": "Details",
            "Order": 10000,
            "IsCustomizable": True,
        },
        "CascadeConfiguration": {
            "Assign": "NoCascade",
            "Delete": "Restrict",
            "Merge": "NoCascade",
            "Reparent": "NoCascade",
            "Share": "NoCascade",
            "Unshare": "NoCascade",
        }
    }
    status, resp = post(token, "RelationshipDefinitions", body)
    if status in (200, 201, 204):
        print(f"  ✓ Relazione creata")
        return True
    print(f"  ✗ Errore ({status}): {resp.get('error', {}).get('message', resp)}")
    return False


def get_pa_token() -> str:
    """Ottieni token per Power Automate Management API (scope diverso da Dataverse)."""
    r = requests.post(DEVICE_URL, data={"client_id": CLIENT_ID, "scope": PA_SCOPE})
    r.raise_for_status()
    info = r.json()
    print()
    print("=" * 60)
    print("  AUTENTICAZIONE POWER AUTOMATE")
    print(f"  Apri: {info['verification_uri']}")
    print(f"  Codice: {info['user_code']}")
    print("=" * 60)
    print()
    interval, deadline = int(info.get("interval", 5)), time.time() + int(info.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(interval)
        resp = requests.post(TOKEN_URL, data={
            "client_id": CLIENT_ID,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": info["device_code"],
        }).json()
        if "access_token" in resp:
            print("✓ Autenticazione PA completata")
            return resp["access_token"]
        if resp.get("error") == "slow_down":
            interval += 5
        elif resp.get("error") != "authorization_pending":
            print(f"✗ {resp.get('error_description', resp.get('error'))}")
            sys.exit(1)
    print("✗ Timeout")
    sys.exit(1)


def create_flow(pa_token: str) -> bool:
    """Crea il flow SalvaAttestazioneSuDataverse via PA Management API."""
    print("\nCreo flow Power Automate ...")

    # Verifica se esiste già
    r = requests.get(
        f"{PA_BASE}/environments/{ENV_ID}/flows",
        headers={"Authorization": f"Bearer {pa_token}", "Accept": "application/json"},
        params={"$filter": "properties/displayName eq 'SalvaAttestazioneSuDataverse'", "$top": 1}
    )
    if r.status_code == 200 and r.json().get("value"):
        print("  → Flow già esistente, skip")
        return True

    flow_def = {
        "properties": {
            "displayName": "SalvaAttestazioneSuDataverse",
            "definition": {
                "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
                "contentVersion": "1.0.0.0",
                "parameters": {
                    "$connections": {"defaultValue": {}, "type": "Object"},
                    "$authentication": {"defaultValue": {}, "type": "SecureObject"},
                },
                "triggers": {
                    "manual": {
                        "type": "Request",
                        "inputs": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "text": {
                                        "title": "JsonAttestazione",
                                        "x-ms-dynamically-added": True,
                                        "description": "JSON estratto dall'attestazione",
                                        "x-ms-content-hint": "TEXT",
                                        "type": "string",
                                    }
                                },
                                "required": ["text"],
                            }
                        },
                    }
                },
                "actions": {
                    "Parse_JSON": {
                        "runAfter": {},
                        "type": "ParseJson",
                        "inputs": {
                            "content": "@triggerBody()['text']",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "dati_anagrafici": {
                                        "type": "object",
                                        "properties": {
                                            "denominazione": {"type": "string"},
                                            "codice_fiscale": {"type": "string"},
                                            "partita_iva": {"type": "string"},
                                            "sede": {"type": "string"},
                                            "cap": {"type": "string"},
                                            "provincia": {"type": "string"},
                                            "indirizzo": {"type": "string"},
                                            "rappresentante_legale": {"type": "string"},
                                        },
                                    },
                                    "certificazioni": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "categoria": {"type": "string"},
                                                "classificazione": {"type": "string"},
                                            },
                                        },
                                    },
                                    "data_scadenza": {"type": "string"},
                                },
                            },
                        },
                    },
                    "Crea_AttestazioneSoa": {
                        "runAfter": {"Parse_JSON": ["Succeeded"]},
                        "type": "ApiConnection",
                        "inputs": {
                            "host": {
                                "apiId": "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps",
                                "connectionName": "shared_commondataserviceforapps",
                                "operationId": "CreateRecord",
                            },
                            "parameters": {
                                "entityName": ATT_SET,
                                "item/hkt_denominazione":         "@body('Parse_JSON')?['dati_anagrafici']?['denominazione']",
                                "item/hkt_codicefiscale":         "@body('Parse_JSON')?['dati_anagrafici']?['codice_fiscale']",
                                "item/hkt_partitaiva":            "@body('Parse_JSON')?['dati_anagrafici']?['partita_iva']",
                                "item/hkt_sede":                  "@body('Parse_JSON')?['dati_anagrafici']?['sede']",
                                "item/hkt_cap":                   "@body('Parse_JSON')?['dati_anagrafici']?['cap']",
                                "item/hkt_provincia":             "@body('Parse_JSON')?['dati_anagrafici']?['provincia']",
                                "item/hkt_indirizzo":             "@body('Parse_JSON')?['dati_anagrafici']?['indirizzo']",
                                "item/hkt_rappresentantelegale":  "@body('Parse_JSON')?['dati_anagrafici']?['rappresentante_legale']",
                                "item/hkt_datascadenza":          "@body('Parse_JSON')?['data_scadenza']",
                                "item/hkt_jsonoriginale":         "@triggerBody()['text']",
                            },
                            "authentication": "@parameters('$authentication')",
                        },
                    },
                    "Apply_to_each_certificazione": {
                        "foreach": "@body('Parse_JSON')?['certificazioni']",
                        "actions": {
                            "Crea_CertificazioneSoa": {
                                "runAfter": {},
                                "type": "ApiConnection",
                                "inputs": {
                                    "host": {
                                        "apiId": "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps",
                                        "connectionName": "shared_commondataserviceforapps",
                                        "operationId": "CreateRecord",
                                    },
                                    "parameters": {
                                        "entityName": CERT_SET,
                                        "item/hkt_categoria":      "@items('Apply_to_each_certificazione')['categoria']",
                                        "item/hkt_classificazione": "@items('Apply_to_each_certificazione')['classificazione']",
                                        "item/hkt_attestazioneid@odata.bind": f"@concat('{ATT_SET}(', body('Crea_AttestazioneSoa')?['hkt_attestazionesoaid'], ')')",
                                    },
                                    "authentication": "@parameters('$authentication')",
                                },
                            }
                        },
                        "runAfter": {"Crea_AttestazioneSoa": ["Succeeded"]},
                        "type": "Foreach",
                    },
                    "Respond_to_the_agent": {
                        "runAfter": {"Apply_to_each_certificazione": ["Succeeded"]},
                        "type": "Response",
                        "inputs": {
                            "statusCode": 200,
                            "body": {
                                "Esito": "@concat('Salvato: ', body('Parse_JSON')?['dati_anagrafici']?['denominazione'])"
                            },
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "Esito": {
                                        "title": "Esito",
                                        "x-ms-dynamically-added": True,
                                        "type": "string",
                                    }
                                },
                            },
                        },
                    },
                },
                "outputs": {},
            },
            "connectionReferences": {
                "shared_commondataserviceforapps": {
                    "connectionName": f"/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps/connections/{CONN_ID}",
                    "source": "Invoker",
                    "id": "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps",
                }
            },
        }
    }

    r = requests.post(
        f"{PA_BASE}/environments/{ENV_ID}/flows",
        headers={
            "Authorization": f"Bearer {pa_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=flow_def,
    )
    if r.status_code in (200, 201):
        flow_id = r.json().get("name", "?")
        print(f"  ✓ Flow creato: {flow_id}")
        return True
    print(f"  ✗ Errore ({r.status_code}): {r.text[:500]}")
    return False


def verify(token):
    print("\nVerifica tabelle ...")
    for logical in ["hkt_attestazionesoa", "hkt_certificazionesoa"]:
        status, resp = get(token, f"EntityDefinitions?$filter=LogicalName eq '{logical}'&$select=LogicalName,EntitySetName")
        if status == 200 and resp.get("value"):
            e = resp["value"][0]
            print(f"  ✓ {e['LogicalName']} → EntitySetName: {e['EntitySetName']}")
        else:
            print(f"  ✗ {logical} non trovata")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    token = get_token()

    print("\nCreazione tabelle Dataverse ...")
    ok1 = create_attestazione_soa(token)
    ok2 = create_certificazione_soa(token)

    if ok1 and ok2:
        print("\nAttendo propagazione metadati (5s) ...")
        time.sleep(5)
        ok3 = create_relationship(token)
    else:
        ok3 = False

    verify(token)

    # Flow PA (token separato — scope diverso)
    print("\nCreazione flow Power Automate ...")
    pa_token = os.environ.get("PA_TOKEN") or get_pa_token()
    ok4 = create_flow(pa_token)

    if ok1 and ok2 and ok3 and ok4:
        print("\n✓ Setup completato (tabelle + flow).")
        print("\nProssimo passo: push + publish dell'agente Copilot Studio")
    else:
        print("\n✗ Setup parziale — controlla gli errori sopra")
        sys.exit(1)


if __name__ == "__main__":
    main()
