"""MISP object templates for SpiderFoot.

These templates help convert SpiderFoot data to structured MISP objects.
"""

from typing import Dict, Any, List

# Dictionary of MISP object templates for common SpiderFoot findings
MISP_OBJECT_TEMPLATES = {
    "domain-ip": {
        "name": "domain-ip",
        "description": "A domain and IP address observed to be related",
        "required": ["domain"],
        "attributes": [
            {
                "name": "domain",
                "type": "domain",
                "category": "Network activity",
                "to_ids": True,
                "object_relation": "domain"
            },
            {
                "name": "ip",
                "type": "ip-dst",
                "category": "Network activity", 
                "to_ids": True,
                "object_relation": "ip"
            }
        ]
    },
    "url": {
        "name": "url",
        "description": "URL object describing a url along with its normalized field",
        "required": ["url"],
        "attributes": [
            {
                "name": "url",
                "type": "url",
                "category": "Network activity",
                "to_ids": True,
                "object_relation": "url"
            },
            {
                "name": "domain",
                "type": "domain",
                "category": "Network activity",
                "to_ids": False,
                "object_relation": "domain"
            },
            {
                "name": "host",
                "type": "hostname",
                "category": "Network activity",
                "to_ids": False,
                "object_relation": "host"
            }
        ]
    },
    "vulnerability": {
        "name": "vulnerability",
        "description": "Vulnerability object",
        "required": ["id"],
        "attributes": [
            {
                "name": "id", 
                "type": "vulnerability",
                "category": "External analysis",
                "to_ids": False,
                "object_relation": "id"
            },
            {
                "name": "summary",
                "type": "text",
                "category": "External analysis",
                "to_ids": False,
                "object_relation": "summary"
            },
            {
                "name": "cvss-score",
                "type": "float",
                "category": "External analysis",
                "to_ids": False,
                "object_relation": "cvss-score"
            }
        ]
    },
    "ssl-certificate": {
        "name": "ssl-certificate",
        "description": "SSL certificate object",
        "required": ["x509-fingerprint-sha1"],
        "attributes": [
            {
                "name": "x509-fingerprint-sha1",
                "type": "x509-fingerprint-sha1",
                "category": "Network activity",
                "to_ids": False,
                "object_relation": "x509-fingerprint-sha1"
            },
            {
                "name": "serial-number",
                "type": "text",
                "category": "Network activity",
                "to_ids": False,
                "object_relation": "serial-number"
            },
            {
                "name": "issuer",
                "type": "text",
                "category": "Network activity",
                "to_ids": False,
                "object_relation": "issuer"
            },
            {
                "name": "subject",
                "type": "text",
                "category": "Network activity",
                "to_ids": False,
                "object_relation": "subject"
            }
        ]
    },
    "person": {
        "name": "person",
        "description": "Person object",
        "required": ["name"],
        "attributes": [
            {
                "name": "name",
                "type": "text",
                "category": "Person",
                "to_ids": False,
                "object_relation": "name"
            },
            {
                "name": "email",
                "type": "email",
                "category": "Person",
                "to_ids": False,
                "object_relation": "email"
            },
            {
                "name": "phone-number",
                "type": "phone-number",
                "category": "Person",
                "to_ids": False,
                "object_relation": "phone-number"
            }
        ]
    }
}


def get_template(object_type: str) -> Dict[str, Any]:
    """Get a MISP object template by type.

    Args:
        object_type: Type of object template to retrieve

    Returns:
        Dict: Template dictionary or empty dict if not found
    """
    return MISP_OBJECT_TEMPLATES.get(object_type, {})


def create_object_from_template(object_type: str, values: Dict[str, Any]) -> Dict[str, Any]:
    """Create a MISP object from a template.

    Args:
        object_type: Type of object to create
        values: Dictionary of values to fill in the template

    Returns:
        Dict: Filled template or empty dict if template not found
    """
    template = get_template(object_type)
    if not template:
        return {}
    
    # Create a copy of the template
    obj = {
        "name": template["name"],
        "description": template["description"],
        "Attribute": []
    }
    
    # Fill in the attributes
    for attr_template in template["attributes"]:
        attr_name = attr_template["name"]
        if attr_name in values:
            attribute = {
                "type": attr_template["type"],
                "category": attr_template["category"],
                "object_relation": attr_template["object_relation"],
                "to_ids": attr_template["to_ids"],
                "value": values[attr_name]
            }
            obj["Attribute"].append(attribute)
    
    # Check required attributes
    for required in template.get("required", []):
        if not any(a["object_relation"] == required for a in obj["Attribute"]):
            # Missing required attribute
            return {}
    
    return obj


def map_sf_event_to_misp_object(sf_event_type: str, sf_event_data: str) -> Dict[str, Any]:
    """Map SpiderFoot event to appropriate MISP object type.

    Args:
        sf_event_type: SpiderFoot event type
        sf_event_data: SpiderFoot event data

    Returns:
        Dict: Mapping information or empty dict if no mapping exists
    """
    mapping = {
        "INTERNET_NAME": {"object_type": "domain-ip", "attr_name": "domain"},
        "DOMAIN_NAME": {"object_type": "domain-ip", "attr_name": "domain"},
        "IP_ADDRESS": {"object_type": "domain-ip", "attr_name": "ip"},
        "URL": {"object_type": "url", "attr_name": "url"},
        "HUMAN_NAME": {"object_type": "person", "attr_name": "name"},
        "EMAILADDR": {"object_type": "person", "attr_name": "email"},
        "PHONE_NUMBER": {"object_type": "person", "attr_name": "phone-number"},
        "SSL_CERTIFICATE_RAW": {"object_type": "ssl-certificate", "attr_name": "x509-fingerprint-sha1"}
    }
    
    return mapping.get(sf_event_type, {})
