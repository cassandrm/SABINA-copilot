"""
Transforms Azure Document Intelligence output format into a flat dict
suitable for validation. Each node with a 'valueString' is extracted
as a plain string value; 'valueObject' is traversed recursively;
'valueArray' is mapped to a list of transformed items.
"""


def _transform_node(node):
    if not isinstance(node, dict):
        return node

    node_type = node.get("type", "")

    if node_type == "object" or "valueObject" in node:
        value_obj = node.get("valueObject", {})
        return {k: _transform_node(v) for k, v in value_obj.items()}

    if node_type == "array" or "valueArray" in node:
        value_arr = node.get("valueArray", [])
        return [_transform_node(item) for item in value_arr]

    if "valueString" in node:
        return node["valueString"]

    if "valueNumber" in node:
        return node["valueNumber"]

    if "valueBoolean" in node:
        return node["valueBoolean"]

    if "valueDate" in node:
        return node["valueDate"]

    # Leaf node with no recognized value key — return None (field not extracted)
    return None


def transform_document_intelligence(raw: dict) -> dict:
    """
    Converts a Document Intelligence result dict into a plain nested dict.
    Top-level keys are preserved; each value is recursively transformed.
    """
    return {k: _transform_node(v) for k, v in raw.items()}
