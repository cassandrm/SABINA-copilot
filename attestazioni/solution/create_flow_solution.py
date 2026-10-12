#!/usr/bin/env python3
"""
Genera FlowSalvaAttestazione_1_0_0_0.zip — solution con solo il flow PA.
Le tabelle Dataverse sono già state create separatamente.

Import:
    python3 create_flow_solution.py   # genera il ZIP
    python3 import_flow_solution.py   # importa via API
"""

import hashlib
import json
import zipfile

SOLUTION_NAME = "FlowSalvaAttestazione"
VERSION       = "1.0.0.0"
PREFIX        = "hkt"
LANG          = "1040"
ATT_SET       = "hkt_attestazionesoas"
CERT_SET      = "hkt_certificazionesoas"
OUTPUT_ZIP    = f"{SOLUTION_NAME}_{VERSION.replace('.','_')}.zip"


def guid(seed):
    h = hashlib.md5(seed.encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


FLOW_GUID = guid("SalvaAttestazioneSuDataverse_flow_v2")
FLOW_NAME = "SalvaAttestazioneSuDataverse"
FLOW_FILE = f"Workflows/{FLOW_NAME}_{FLOW_GUID.replace('-','')}.json"

CONTENT_TYPES = """\
<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/octet-stream"/>
  <Default Extension="json" ContentType="application/octet-stream"/>
</Types>"""

SOLUTION_XML = f"""\
<?xml version="1.0" encoding="utf-8"?>
<ImportExportXml version="9.2.0.0" SolutionPackageVersion="9.2" languagecode="1040" generatedBy="Script">
  <SolutionManifest>
    <UniqueName>{SOLUTION_NAME}</UniqueName>
    <LocalizedNames>
      <LocalizedName description="Flow Salva Attestazione" languagecode="{LANG}" />
    </LocalizedNames>
    <Descriptions/>
    <Version>{VERSION}</Version>
    <Managed>0</Managed>
    <Publisher>
      <UniqueName>HKT</UniqueName>
      <LocalizedNames>
        <LocalizedName description="HKT_Poste" languagecode="{LANG}" />
      </LocalizedNames>
      <Descriptions/>
      <EMailAddress/>
      <SupportingWebsiteUrl/>
      <CustomizationPrefix>{PREFIX}</CustomizationPrefix>
      <CustomizationOptionValuePrefix>81601</CustomizationOptionValuePrefix>
      <Addresses>
        <Address>
          <AddressNumber>1</AddressNumber>
          <AddressTypeCode>1</AddressTypeCode>
          <ShippingMethodCode>1</ShippingMethodCode>
          <ImportSequenceNumber>0</ImportSequenceNumber>
          <Latitude>0</Latitude>
          <Longitude>0</Longitude>
          <TimeZoneRuleVersionNumber>0</TimeZoneRuleVersionNumber>
          <UTCOffset>0</UTCOffset>
        </Address>
      </Addresses>
    </Publisher>
    <RootComponents>
      <RootComponent type="29" id="{{{FLOW_GUID}}}" behavior="0" />
    </RootComponents>
    <MissingDependencies/>
  </SolutionManifest>
</ImportExportXml>"""

CUSTOMIZATIONS_XML = f"""\
<?xml version="1.0" encoding="utf-8"?>
<ImportExportXml version="9.2.0.0" SolutionPackageVersion="9.2" languagecode="1040" generatedBy="Script">
  <Entities/>
  <Roles/>
  <Workflows>
    <Workflow WorkflowId="{{{FLOW_GUID}}}" Name="{FLOW_NAME}" Category="5" Type="1">
      <JsonFileName>{FLOW_FILE}</JsonFileName>
    </Workflow>
  </Workflows>
  <FieldSecurityProfiles/>
  <Templates/>
  <EntityMaps/>
  <EntityRelationships/>
  <OrganizationSettings/>
  <optionsets/>
  <CustomControls/>
  <SolutionPluginAssemblies/>
  <SdkMessageFilterIds/>
  <connections/>
</ImportExportXml>"""

ENV_ID = "8888de39-af12-ed69-be38-971c5020e54b"

FLOW_JSON = {
    "properties": {
        "displayName": FLOW_NAME,
        "description": "Salva dati attestazione SOA su Dataverse",
        "environment": {
            "name": f"environments/{ENV_ID}",
            "type": "Microsoft.ProcessSimple/environments",
            "id": f"/providers/Microsoft.ProcessSimple/environments/{ENV_ID}",
        },
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
                    "kind": "Button",
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
                                        "denominazione":         {"type": "string"},
                                        "codice_fiscale":        {"type": "string"},
                                        "partita_iva":           {"type": "string"},
                                        "sede":                  {"type": "string"},
                                        "cap":                   {"type": "string"},
                                        "provincia":             {"type": "string"},
                                        "indirizzo":             {"type": "string"},
                                        "rappresentante_legale": {"type": "string"},
                                    },
                                },
                                "certificazioni": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "categoria":       {"type": "string"},
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
                            "item/hkt_denominazione":        "@body('Parse_JSON')?['dati_anagrafici']?['denominazione']",
                            "item/hkt_codicefiscale":        "@body('Parse_JSON')?['dati_anagrafici']?['codice_fiscale']",
                            "item/hkt_partitaiva":           "@body('Parse_JSON')?['dati_anagrafici']?['partita_iva']",
                            "item/hkt_sede":                 "@body('Parse_JSON')?['dati_anagrafici']?['sede']",
                            "item/hkt_cap":                  "@body('Parse_JSON')?['dati_anagrafici']?['cap']",
                            "item/hkt_provincia":            "@body('Parse_JSON')?['dati_anagrafici']?['provincia']",
                            "item/hkt_indirizzo":            "@body('Parse_JSON')?['dati_anagrafici']?['indirizzo']",
                            "item/hkt_rappresentantelegale": "@body('Parse_JSON')?['dati_anagrafici']?['rappresentante_legale']",
                            "item/hkt_datascadenza":         "@body('Parse_JSON')?['data_scadenza']",
                            "item/hkt_jsonoriginale":        "@triggerBody()['text']",
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
                                    "item/hkt_categoria":       "@items('Apply_to_each_certificazione')['categoria']",
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
    }
}


def build():
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("solution.xml",        SOLUTION_XML)
        z.writestr("customizations.xml",  CUSTOMIZATIONS_XML)
        z.writestr(FLOW_FILE,             json.dumps(FLOW_JSON, indent=2, ensure_ascii=False))
    print(f"✓ {OUTPUT_ZIP}")
    print(f"  Flow GUID: {FLOW_GUID}")
    print(f"  Flow file: {FLOW_FILE}")


if __name__ == "__main__":
    build()
