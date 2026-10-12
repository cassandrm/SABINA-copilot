#!/usr/bin/env python3
"""
Genera HktAttestazioniSoa_1_0_0_0.zip — solution package Power Platform.

Crea:
  - hkt_attestazionesoa  : tabella principale con dati anagrafici e data scadenza
  - hkt_certificazionesoa: tabella figlia con categoria/classificazione (lookup su AttestazioneSoa)
  - SalvaAttestazioneSuDataverse: flow Power Automate (trigger Copilot Studio)

Importa con:
    pac solution import \\
        --path HktAttestazioniSoa_1_0_0_0.zip \\
        --environment 8888de39-af12-ed69-be38-971c5020e54b \\
        --settings-file deployment_settings.json

Dopo l'import configura la connection reference in deployment_settings.json
puntando a una connessione Dataverse valida dell'ambiente.
"""

import hashlib
import json
import os
import zipfile

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
PREFIX = "hkt"
SOL_NAME = "HktAttestazioniSoa"
SOL_VERSION = "1.0.0.0"
LANG = "1040"  # italiano
ENV_ID = "8888de39-af12-ed69-be38-971c5020e54b"
DATAVERSE_URL = "https://org8aea528f.crm4.dynamics.com"
CONN_REF_LOGICAL = "hkt_DataverseAttestazioniConn"
OUTPUT_ZIP = f"{SOL_NAME}_{SOL_VERSION.replace('.', '_')}.zip"


def _guid(seed: str) -> str:
    h = hashlib.md5(seed.encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


FLOW_ID = _guid("SalvaAttestazioneSuDataverse_flow_v1")
FLOW_FILE = f"Workflows/SalvaAttestazioneSuDataverse_{FLOW_ID.replace('-', '')}.json"


# ---------------------------------------------------------------------------
# [Content_Types].xml
# ---------------------------------------------------------------------------
CONTENT_TYPES = """\
<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/octet-stream"/>
  <Default Extension="json" ContentType="application/octet-stream"/>
</Types>"""


# ---------------------------------------------------------------------------
# solution.xml
# ---------------------------------------------------------------------------
SOLUTION_XML = f"""\
<?xml version="1.0" encoding="utf-8"?>
<ImportExportXml version="9.2.0.0" SolutionPackageVersion="9.2" languagecode="1040" generatedBy="Script">
  <SolutionManifest>
    <UniqueName>{SOL_NAME}</UniqueName>
    <LocalizedNames>
      <LocalizedName description="Attestazioni SOA" languagecode="{LANG}" />
    </LocalizedNames>
    <Descriptions/>
    <Version>{SOL_VERSION}</Version>
    <Managed>0</Managed>
    <Publisher>
      <UniqueName>{PREFIX}</UniqueName>
      <LocalizedNames>
        <LocalizedName description="HKT" languagecode="{LANG}" />
      </LocalizedNames>
      <Descriptions/>
      <EMailAddress/>
      <SupportingWebsiteUrl/>
      <CustomizationPrefix>{PREFIX}</CustomizationPrefix>
      <CustomizationOptionValuePrefix>10000</CustomizationOptionValuePrefix>
      <Addresses>
        <Address>
          <AddressNumber>1</AddressNumber><AddressTypeCode>1</AddressTypeCode>
          <City/><County/><Country/><Fax/><FreightTermsCode/>
          <ImportSequenceNumber>0</ImportSequenceNumber>
          <Latitude>0</Latitude><Longitude>0</Longitude>
          <Line1/><Line2/><Line3/><Name/><PostalCode/><PostOfficeBox/>
          <PrimaryContactName/><ShippingMethodCode>1</ShippingMethodCode>
          <StateOrProvince/><Telephone1/><Telephone2/><Telephone3/>
          <TimeZoneRuleVersionNumber>0</TimeZoneRuleVersionNumber>
          <UPSZone/><UTCOffset>0</UTCOffset><WebSiteURL/>
        </Address>
      </Addresses>
    </Publisher>
    <RootComponents>
      <RootComponent type="1" schemaName="hkt_attestazionesoa" behavior="0" />
      <RootComponent type="1" schemaName="hkt_certificazionesoa" behavior="0" />
      <RootComponent type="29" id="{{{FLOW_ID}}}" behavior="0" />
    </RootComponents>
    <MissingDependencies/>
  </SolutionManifest>
</ImportExportXml>"""


# ---------------------------------------------------------------------------
# Helper: attribute XML builders
# ---------------------------------------------------------------------------
def _pk(entity_name, display):
    pk = f"{entity_name}id"
    return f"""\
        <attribute PhysicalName="{pk}">
          <Type>primarykey</Type>
          <Name>{pk}</Name>
          <LogicalName>{pk}</LogicalName>
          <RequiredLevel>systemrequired</RequiredLevel>
          <DisplayMask>ValidForAdvancedFind|ValidForForm|ValidForGrid</DisplayMask>
          <IsCustomField>0</IsCustomField>
          <IsCustomizable>0</IsCustomizable>
          <LocalizedNames><LocalizedName description="{display}" languagecode="{LANG}" /></LocalizedNames>
          <Descriptions/>
        </attribute>"""


def _text(logical, display, maxlen=500, required="none"):
    return f"""\
        <attribute PhysicalName="{logical}">
          <Type>nvarchar</Type>
          <Name>{logical}</Name>
          <LogicalName>{logical}</LogicalName>
          <RequiredLevel>{required}</RequiredLevel>
          <MaxLength>{maxlen}</MaxLength>
          <DisplayMask>ValidForAdvancedFind|ValidForForm|ValidForGrid</DisplayMask>
          <IsCustomField>1</IsCustomField>
          <IsCustomizable>1</IsCustomizable>
          <LocalizedNames><LocalizedName description="{display}" languagecode="{LANG}" /></LocalizedNames>
          <Descriptions/>
        </attribute>"""


def _date(logical, display):
    return f"""\
        <attribute PhysicalName="{logical}">
          <Type>datetime</Type>
          <Name>{logical}</Name>
          <LogicalName>{logical}</LogicalName>
          <RequiredLevel>none</RequiredLevel>
          <Format>DateOnly</Format>
          <ImeMode>disabled</ImeMode>
          <DisplayMask>ValidForAdvancedFind|ValidForForm|ValidForGrid</DisplayMask>
          <IsCustomField>1</IsCustomField>
          <IsCustomizable>1</IsCustomizable>
          <LocalizedNames><LocalizedName description="{display}" languagecode="{LANG}" /></LocalizedNames>
          <Descriptions/>
        </attribute>"""


def _memo(logical, display, maxlen=8000):
    return f"""\
        <attribute PhysicalName="{logical}">
          <Type>memo</Type>
          <Name>{logical}</Name>
          <LogicalName>{logical}</LogicalName>
          <RequiredLevel>none</RequiredLevel>
          <MaxLength>{maxlen}</MaxLength>
          <DisplayMask>ValidForAdvancedFind|ValidForForm|ValidForGrid</DisplayMask>
          <IsCustomField>1</IsCustomField>
          <IsCustomizable>1</IsCustomizable>
          <LocalizedNames><LocalizedName description="{display}" languagecode="{LANG}" /></LocalizedNames>
          <Descriptions/>
        </attribute>"""


def _lookup(logical, display, target):
    return f"""\
        <attribute PhysicalName="{logical}">
          <Type>lookup</Type>
          <Name>{logical}</Name>
          <LogicalName>{logical}</LogicalName>
          <RequiredLevel>none</RequiredLevel>
          <DisplayMask>ValidForAdvancedFind|ValidForForm|ValidForGrid</DisplayMask>
          <IsCustomField>1</IsCustomField>
          <IsCustomizable>1</IsCustomizable>
          <LocalizedNames><LocalizedName description="{display}" languagecode="{LANG}" /></LocalizedNames>
          <Descriptions/>
          <targets><target>{target}</target></targets>
        </attribute>"""


# ---------------------------------------------------------------------------
# customizations.xml
# ---------------------------------------------------------------------------
ATT_ATTRS = "\n".join([
    _pk("hkt_attestazionesoa", "ID Attestazione SOA"),
    _text("hkt_denominazione",          "Denominazione",         500, "recommended"),
    _text("hkt_codice_fiscale",          "Codice Fiscale",        50),
    _text("hkt_partita_iva",             "Partita IVA",           50),
    _text("hkt_sede",                    "Sede",                  200),
    _text("hkt_cap",                     "CAP",                   10),
    _text("hkt_provincia",               "Provincia",             100),
    _text("hkt_indirizzo",               "Indirizzo",             500),
    _text("hkt_rappresentante_legale",   "Rappresentante Legale", 300),
    _date("hkt_data_scadenza",           "Data Scadenza"),
    _memo("hkt_json_originale",          "JSON Originale"),
])

CERT_ATTRS = "\n".join([
    _pk("hkt_certificazionesoa", "ID Certificazione SOA"),
    _text("hkt_categoria",      "Categoria",      200, "recommended"),
    _text("hkt_classificazione","Classificazione", 100),
    _lookup("hkt_attestazioneid","Attestazione SOA","hkt_attestazionesoa"),
])

RELATIONSHIP = """\
  <EntityRelationship Name="hkt_attestazionesoa_certificazionesoa">
    <EntityRelationshipType>OneToMany</EntityRelationshipType>
    <IsCustomizable>1</IsCustomizable>
    <IsCustomRelationship>1</IsCustomRelationship>
    <IsValidForAdvancedFind>1</IsValidForAdvancedFind>
    <SchemaName>hkt_attestazionesoa_certificazionesoa</SchemaName>
    <SecurityTypes>None</SecurityTypes>
    <CascadeAssign>NoCascade</CascadeAssign>
    <CascadeDelete>Restrict</CascadeDelete>
    <CascadeReparent>NoCascade</CascadeReparent>
    <CascadeShare>NoCascade</CascadeShare>
    <CascadeUnshare>NoCascade</CascadeUnshare>
    <CascadeRollupView>NoCascade</CascadeRollupView>
    <IsParental>0</IsParental>
    <ReferencingEntityName>hkt_certificazionesoa</ReferencingEntityName>
    <ReferencedEntityName>hkt_attestazionesoa</ReferencedEntityName>
    <ReferencingAttributeName>hkt_attestazioneid</ReferencingAttributeName>
    <ReferencedAttributeName>hkt_attestazionesoaid</ReferencedAttributeName>
    <EntityRelationshipRoles>
      <EntityRelationshipRole>
        <NavPaneDisplayOption>UseCollectionName</NavPaneDisplayOption>
        <NavPaneOrder>10000</NavPaneOrder>
        <NavigationPropertyName>hkt_attestazioneid_hkt_certificazionesoa</NavigationPropertyName>
        <RelationshipRoleType>1</RelationshipRoleType>
      </EntityRelationshipRole>
      <EntityRelationshipRole>
        <NavPaneDisplayOption>DoNotDisplay</NavPaneDisplayOption>
        <NavPaneOrder>10000</NavPaneOrder>
        <NavigationPropertyName>hkt_attestazioneid</NavigationPropertyName>
        <RelationshipRoleType>0</RelationshipRoleType>
      </EntityRelationshipRole>
    </EntityRelationshipRoles>
  </EntityRelationship>"""

CUSTOMIZATIONS_XML = f"""\
<?xml version="1.0" encoding="utf-8"?>
<ImportExportXml version="9.2.0.0" SolutionPackageVersion="9.2" languagecode="1040" generatedBy="Script">
  <Entities>

    <Entity>
      <Name LocalizedName="Attestazione SOA" OriginalName="hkt_attestazionesoa">hkt_attestazionesoa</Name>
      <EntityInfo>
        <entity Name="hkt_attestazionesoa">
          <LocalizedNames>
            <LocalizedName description="Attestazione SOA" languagecode="{LANG}" />
          </LocalizedNames>
          <LocalizedCollectionNames>
            <LocalizedCollectionName description="Attestazioni SOA" languagecode="{LANG}" />
          </LocalizedCollectionNames>
          <Descriptions/>
          <attributes>
{ATT_ATTRS}
          </attributes>
        </entity>
      </EntityInfo>
      <FormXml>
        <forms type="main">
          <systemform>
            <formXml><![CDATA[<form><tabs/></form>]]></formXml>
          </systemform>
        </forms>
      </FormXml>
    </Entity>

    <Entity>
      <Name LocalizedName="Certificazione SOA" OriginalName="hkt_certificazionesoa">hkt_certificazionesoa</Name>
      <EntityInfo>
        <entity Name="hkt_certificazionesoa">
          <LocalizedNames>
            <LocalizedName description="Certificazione SOA" languagecode="{LANG}" />
          </LocalizedNames>
          <LocalizedCollectionNames>
            <LocalizedCollectionName description="Certificazioni SOA" languagecode="{LANG}" />
          </LocalizedCollectionNames>
          <Descriptions/>
          <attributes>
{CERT_ATTRS}
          </attributes>
        </entity>
      </EntityInfo>
      <FormXml>
        <forms type="main">
          <systemform>
            <formXml><![CDATA[<form><tabs/></form>]]></formXml>
          </systemform>
        </forms>
      </FormXml>
    </Entity>

  </Entities>
  <Roles/>
  <Workflows>
    <Workflow WorkflowId="{{{FLOW_ID}}}" Name="SalvaAttestazioneSuDataverse">
      <XmlFileName>{FLOW_FILE}</XmlFileName>
    </Workflow>
  </Workflows>
  <FieldSecurityProfiles/>
  <Templates/>
  <EntityMaps/>
  <EntityRelationships>
{RELATIONSHIP}
  </EntityRelationships>
  <OrganizationSettings/>
  <optionsets/>
  <CustomControls/>
  <SolutionPluginAssemblies/>
  <SdkMessageFilterIds/>
  <connections/>
</ImportExportXml>"""


# ---------------------------------------------------------------------------
# Flow definition (Logic Apps / Power Automate JSON)
# Nota: hkt_attestazionesoaes e hkt_certificazionesoaes sono i nomi entity set
# generati da Dataverse (suffisso "es" per tabelle che terminano in vocale).
# Se l'import li crea con nomi diversi, aggiorna le due costanti qui sotto.
# ---------------------------------------------------------------------------
ATT_SET  = "hkt_attestazionesoas"
CERT_SET = "hkt_certificazionesoas"

FLOW_JSON = {
    "properties": {
        "connectionReferences": {
            "shared_commondataserviceforapps": {
                "runtimeSource": "embedded",
                "connection": {
                    "connectionReferenceLogicalName": CONN_REF_LOGICAL
                },
                "api": {
                    "name": "shared_commondataserviceforapps"
                }
            }
        },
        "definition": {
            "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {
                "$connections": {"defaultValue": {}, "type": "Object"},
                "$authentication": {"defaultValue": {}, "type": "SecureObject"}
            },
            "triggers": {
                "manual": {
                    "type": "Request",
                    "kind": "PowerVirtualAgents",
                    "inputs": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "title": "JsonAttestazione",
                                    "x-ms-dynamically-added": True,
                                    "description": "JSON estratto dall'attestazione",
                                    "x-ms-content-hint": "TEXT",
                                    "type": "string"
                                }
                            },
                            "required": ["text"]
                        }
                    }
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
                                        "denominazione":        {"type": "string"},
                                        "codice_fiscale":       {"type": "string"},
                                        "partita_iva":          {"type": "string"},
                                        "sede":                 {"type": "string"},
                                        "cap":                  {"type": "string"},
                                        "provincia":            {"type": "string"},
                                        "indirizzo":            {"type": "string"},
                                        "rappresentante_legale":{"type": "string"}
                                    }
                                },
                                "certificazioni": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "categoria":      {"type": "string"},
                                            "classificazione":{"type": "string"}
                                        }
                                    }
                                },
                                "data_scadenza": {"type": "string"}
                            }
                        }
                    }
                },
                "Crea_AttestazioneSoa": {
                    "runAfter": {"Parse_JSON": ["Succeeded"]},
                    "type": "ApiConnection",
                    "inputs": {
                        "host": {
                            "apiId": "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps",
                            "connectionName": "shared_commondataserviceforapps",
                            "operationId": "CreateRecord"
                        },
                        "parameters": {
                            "entityName": ATT_SET,
                            "item/hkt_denominazione":           "@body('Parse_JSON')?['dati_anagrafici']?['denominazione']",
                            "item/hkt_codice_fiscale":          "@body('Parse_JSON')?['dati_anagrafici']?['codice_fiscale']",
                            "item/hkt_partita_iva":             "@body('Parse_JSON')?['dati_anagrafici']?['partita_iva']",
                            "item/hkt_sede":                    "@body('Parse_JSON')?['dati_anagrafici']?['sede']",
                            "item/hkt_cap":                     "@body('Parse_JSON')?['dati_anagrafici']?['cap']",
                            "item/hkt_provincia":               "@body('Parse_JSON')?['dati_anagrafici']?['provincia']",
                            "item/hkt_indirizzo":               "@body('Parse_JSON')?['dati_anagrafici']?['indirizzo']",
                            "item/hkt_rappresentante_legale":   "@body('Parse_JSON')?['dati_anagrafici']?['rappresentante_legale']",
                            "item/hkt_data_scadenza":           "@body('Parse_JSON')?['data_scadenza']",
                            "item/hkt_json_originale":          "@triggerBody()['text']"
                        },
                        "authentication": "@parameters('$authentication')"
                    }
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
                                    "operationId": "CreateRecord"
                                },
                                "parameters": {
                                    "entityName": CERT_SET,
                                    "item/hkt_categoria":       "@items('Apply_to_each_certificazione')['categoria']",
                                    "item/hkt_classificazione": "@items('Apply_to_each_certificazione')['classificazione']",
                                    "item/hkt_attestazioneid@odata.bind": f"@concat('{ATT_SET}(', body('Crea_AttestazioneSoa')?['hkt_attestazionesoaid'], ')')"
                                },
                                "authentication": "@parameters('$authentication')"
                            }
                        }
                    },
                    "runAfter": {"Crea_AttestazioneSoa": ["Succeeded"]},
                    "type": "Foreach"
                },
                "Respond_to_the_agent": {
                    "runAfter": {"Apply_to_each_certificazione": ["Succeeded"]},
                    "type": "Response",
                    "kind": "PowerVirtualAgents",
                    "inputs": {
                        "statusCode": 200,
                        "body": {
                            "Esito": "@concat('Attestazione salvata: ', body('Parse_JSON')?['dati_anagrafici']?['denominazione'])"
                        },
                        "schema": {
                            "type": "object",
                            "properties": {
                                "Esito": {
                                    "title": "Esito",
                                    "x-ms-dynamically-added": True,
                                    "type": "string"
                                }
                            }
                        }
                    }
                }
            },
            "outputs": {}
        }
    }
}


# ---------------------------------------------------------------------------
# deployment_settings.json  (template — l'utente inserisce il ConnectionId)
# ---------------------------------------------------------------------------
DEPLOYMENT_SETTINGS = {
    "EnvironmentVariables": [],
    "ConnectionReferences": [
        {
            "LogicalName": CONN_REF_LOGICAL,
            "ConnectionId": "<INSERISCI_CONNECTION_ID>",
            "ConnectorId": "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps"
        }
    ]
}


# ---------------------------------------------------------------------------
# Build ZIP
# ---------------------------------------------------------------------------
def build_zip():
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("solution.xml",         SOLUTION_XML)
        z.writestr("customizations.xml",   CUSTOMIZATIONS_XML)
        z.writestr(FLOW_FILE,              json.dumps(FLOW_JSON, indent=2, ensure_ascii=False))
    print(f"✓ Generato: {OUTPUT_ZIP}")
    print(f"  Flow ID   : {FLOW_ID}")
    print(f"  Flow file : {FLOW_FILE}")


def build_settings():
    path = "deployment_settings.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(DEPLOYMENT_SETTINGS, f, indent=2, ensure_ascii=False)
    print(f"✓ Generato: {path}")
    print(f"  → Aggiorna ConnectionId prima di importare")


def print_import_instructions():
    print()
    print("=" * 60)
    print("IMPORT INSTRUCTIONS")
    print("=" * 60)
    print()
    print("1. Recupera il ConnectionId della connessione Dataverse")
    print("   nell'ambiente (da Power Platform admin center o API).")
    print("   Aggiorna deployment_settings.json con il ConnectionId.")
    print()
    print("2. Importa la solution:")
    print(f"   pac solution import \\")
    print(f"     --path {OUTPUT_ZIP} \\")
    print(f"     --environment {ENV_ID} \\")
    print(f"     --settings-file deployment_settings.json")
    print()
    print("3. Verifica le entity set name dopo l'import:")
    print(f"   GET {DATAVERSE_URL}/api/data/v9.2/EntityDefinitions?$select=LogicalName,EntitySetName&$filter=contains(LogicalName,'hkt_')")
    print()
    print("   Se i nomi EntitySetName differiscono da")
    print(f"   '{ATT_SET}' / '{CERT_SET}',")
    print(f"   aggiorna le costanti ATT_SET e CERT_SET in questo script")
    print(f"   e rigenera il ZIP prima di reimportare.")
    print()


if __name__ == "__main__":
    build_zip()
    build_settings()
    print_import_instructions()
