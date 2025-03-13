"""SpiderFoot MISP integration module.

This module provides integration with the MISP data model, allowing
SpiderFoot to use standardized threat intelligence formats and
taxonomies.
"""

import json
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Union

from spiderfoot.event import SpiderFootEvent
from spiderfoot.db import SpiderFootDb
from spiderfoot.logconfig import get_module_logger


class MispAttribute:
    """MISP attribute representation for SpiderFoot."""

    def __init__(
        self,
        type: str,
        value: str,
        category: str = None,
        to_ids: bool = False,
        comment: str = None,
        distribution: int = None,
        sharing_group_id: int = None,
        timestamp: int = None,
        **kwargs
    ):
        """Initialize a MISP attribute.

        Args:
            type: The type of attribute
            value: The value of the attribute
            category: The category of the attribute
            to_ids: Whether this attribute should be used for detection
            comment: Optional comment for the attribute
            distribution: Distribution level of the attribute
            sharing_group_id: ID of the sharing group
            timestamp: Unix timestamp of the attribute
            **kwargs: Additional attribute properties
        """
        self.log = get_module_logger('misp_integration')
        self.type = type
        self.value = value
        self.category = category
        self.to_ids = to_ids
        self.comment = comment
        self.distribution = distribution
        self.sharing_group_id = sharing_group_id
        self.timestamp = timestamp or int(time.time())
        self.uuid = kwargs.get('uuid', str(uuid.uuid4()))
        
        # Additional MISP properties
        self.additional_properties = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert the MISP attribute to a dictionary.

        Returns:
            Dict: Dictionary representation of the MISP attribute
        """
        attr_dict = {
            "type": self.type,
            "value": self.value,
            "uuid": self.uuid,
            "timestamp": self.timestamp
        }
        
        if self.category:
            attr_dict["category"] = self.category
        
        attr_dict["to_ids"] = self.to_ids
        
        if self.comment:
            attr_dict["comment"] = self.comment
            
        if self.distribution is not None:
            attr_dict["distribution"] = self.distribution
            
        if self.sharing_group_id:
            attr_dict["sharing_group_id"] = self.sharing_group_id
            
        # Add any additional properties
        for k, v in self.additional_properties.items():
            if k not in attr_dict and k != "uuid":
                attr_dict[k] = v
                
        return attr_dict


class MispObject:
    """MISP object representation for SpiderFoot."""

    def __init__(
        self,
        name: str,
        description: str = None,
        template_uuid: str = None,
        template_version: str = None,
        meta: Dict[str, Any] = None,
        distribution: int = None,
        sharing_group_id: int = None,
        timestamp: int = None,
        **kwargs
    ):
        """Initialize a MISP object.

        Args:
            name: The name/type of the object
            description: Description of the object
            template_uuid: UUID of the template
            template_version: Version of the template
            meta: Metadata for the object
            distribution: Distribution level
            sharing_group_id: Sharing group ID
            timestamp: Unix timestamp
            **kwargs: Additional object properties
        """
        self.log = get_module_logger('misp_integration')
        self.name = name
        self.description = description
        self.template_uuid = template_uuid
        self.template_version = template_version
        self.meta = meta or {}
        self.distribution = distribution
        self.sharing_group_id = sharing_group_id
        self.timestamp = timestamp or int(time.time())
        self.uuid = kwargs.get('uuid', str(uuid.uuid4()))
        self.attributes: List[MispAttribute] = []
        
        # Additional MISP properties
        self.additional_properties = kwargs

    def add_attribute(self, attribute: MispAttribute) -> None:
        """Add a MISP attribute to the object.

        Args:
            attribute: MISP attribute to add
        """
        self.attributes.append(attribute)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the MISP object to a dictionary.

        Returns:
            Dict: Dictionary representation of the MISP object
        """
        obj_dict = {
            "name": self.name,
            "uuid": self.uuid,
            "timestamp": self.timestamp,
            "Attribute": [attr.to_dict() for attr in self.attributes]
        }
        
        if self.description:
            obj_dict["description"] = self.description
            
        if self.template_uuid:
            obj_dict["template_uuid"] = self.template_uuid
            
        if self.template_version:
            obj_dict["template_version"] = self.template_version
            
        if self.meta:
            obj_dict["meta"] = self.meta
            
        if self.distribution is not None:
            obj_dict["distribution"] = self.distribution
            
        if self.sharing_group_id:
            obj_dict["sharing_group_id"] = self.sharing_group_id
            
        # Add any additional properties
        for k, v in self.additional_properties.items():
            if k not in obj_dict and k != "uuid":
                obj_dict[k] = v
                
        return obj_dict


class MispEvent:
    """MISP event representation for SpiderFoot."""

    def __init__(
        self,
        info: str,
        threat_level_id: int = 4,  # Default: Undefined
        analysis: int = 0,  # Default: Initial
        distribution: int = 0,  # Default: Your organization only
        sharing_group_id: int = None,
        published: bool = False,
        timestamp: int = None,
        **kwargs
    ):
        """Initialize a MISP event.

        Args:
            info: Information about the event
            threat_level_id: Threat level (1-4)
            analysis: Analysis level (0-2)
            distribution: Distribution level
            sharing_group_id: Sharing group ID
            published: Whether the event is published
            timestamp: Unix timestamp
            **kwargs: Additional event properties
        """
        self.log = get_module_logger('misp_integration')
        self.info = info
        self.threat_level_id = threat_level_id
        self.analysis = analysis
        self.distribution = distribution
        self.sharing_group_id = sharing_group_id
        self.published = published
        self.timestamp = timestamp or int(time.time())
        self.uuid = kwargs.get('uuid', str(uuid.uuid4()))
        self.attributes: List[MispAttribute] = []
        self.objects: List[MispObject] = []
        self.tags: List[str] = []
        
        # Additional MISP properties
        self.additional_properties = kwargs

    def add_attribute(self, attribute: MispAttribute) -> None:
        """Add a MISP attribute to the event.

        Args:
            attribute: MISP attribute to add
        """
        self.attributes.append(attribute)

    def add_object(self, obj: MispObject) -> None:
        """Add a MISP object to the event.

        Args:
            obj: MISP object to add
        """
        self.objects.append(obj)

    def add_tag(self, tag: str) -> None:
        """Add a tag to the event.

        Args:
            tag: Tag to add
        """
        if tag not in self.tags:
            self.tags.append(tag)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the MISP event to a dictionary.

        Returns:
            Dict: Dictionary representation of the MISP event
        """
        event_dict = {
            "info": self.info,
            "threat_level_id": self.threat_level_id,
            "analysis": self.analysis,
            "distribution": self.distribution,
            "uuid": self.uuid,
            "timestamp": self.timestamp,
            "published": self.published,
            "Attribute": [attr.to_dict() for attr in self.attributes],
            "Object": [obj.to_dict() for obj in self.objects],
            "Tag": self.tags
        }
        
        if self.sharing_group_id:
            event_dict["sharing_group_id"] = self.sharing_group_id
            
        # Add any additional properties
        for k, v in self.additional_properties.items():
            if k not in event_dict and k != "uuid":
                event_dict[k] = v
                
        return event_dict


class MispTaxonomy:
    """MISP taxonomy representation for SpiderFoot."""

    def __init__(self, namespace: str, description: str = None):
        """Initialize a MISP taxonomy.

        Args:
            namespace: The namespace of the taxonomy
            description: Description of the taxonomy
        """
        self.log = get_module_logger('misp_integration')
        self.namespace = namespace
        self.description = description
        self.predicates: Dict[str, Dict[str, Any]] = {}

    def add_predicate(self, predicate: str, description: str = None) -> None:
        """Add a predicate to the taxonomy.

        Args:
            predicate: The predicate name
            description: Description of the predicate
        """
        if predicate not in self.predicates:
            self.predicates[predicate] = {
                "description": description,
                "values": {}
            }

    def add_entry(self, predicate: str, value: str, description: str = None) -> None:
        """Add an entry to a predicate.

        Args:
            predicate: The predicate name
            value: The entry value
            description: Description of the entry
        """
        if predicate not in self.predicates:
            self.add_predicate(predicate)
            
        self.predicates[predicate]["values"][value] = {
            "description": description
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert the taxonomy to a dictionary.

        Returns:
            Dict: Dictionary representation of the taxonomy
        """
        return {
            "namespace": self.namespace,
            "description": self.description,
            "predicates": self.predicates
        }


class MispIntegration:
    """Main MISP integration class for SpiderFoot."""

    def __init__(self, db: SpiderFootDb):
        """Initialize MISP integration.

        Args:
            db: SpiderFoot database instance
        """
        self.log = get_module_logger('misp_integration')
        self.db = db
        self.taxonomies: Dict[str, MispTaxonomy] = {}
        self._load_default_taxonomies()

    def _load_default_taxonomies(self) -> None:
        """Load default MISP taxonomies."""
        # Load tlp taxonomy
        tlp = MispTaxonomy("tlp", "Traffic Light Protocol")
        tlp.add_predicate("marking", "TLP marking")
        tlp.add_entry("marking", "white", "TLP:WHITE")
        tlp.add_entry("marking", "green", "TLP:GREEN")
        tlp.add_entry("marking", "amber", "TLP:AMBER")
        tlp.add_entry("marking", "red", "TLP:RED")
        self.taxonomies["tlp"] = tlp

        # Load confidence taxonomy
        confidence = MispTaxonomy("confidence", "Confidence level")
        confidence.add_predicate("level", "Confidence level")
        confidence.add_entry("level", "low", "Low confidence")
        confidence.add_entry("level", "medium", "Medium confidence")
        confidence.add_entry("level", "high", "High confidence")
        self.taxonomies["confidence"] = confidence

        # Load threat actor taxonomy
        threat_actor = MispTaxonomy("threat-actor", "Threat Actor Classification")
        threat_actor.add_predicate("type", "Threat Actor Type")
        threat_actor.add_entry("type", "apt", "Advanced Persistent Threat")
        threat_actor.add_entry("type", "criminal", "Criminal")
        threat_actor.add_entry("type", "hacktivist", "Hacktivist")
        self.taxonomies["threat-actor"] = threat_actor

    def add_taxonomy(self, taxonomy: MispTaxonomy) -> None:
        """Add a taxonomy.

        Args:
            taxonomy: Taxonomy to add
        """
        self.taxonomies[taxonomy.namespace] = taxonomy

    def create_misp_event_from_scan(self, scan_id: str) -> MispEvent:
        """Create a MISP event from a SpiderFoot scan.

        Args:
            scan_id: Scan instance ID

        Returns:
            MispEvent: MISP event containing scan data
        """
        scan_info = self.db.scanInstanceGet(scan_id)
        
        if not scan_info:
            self.log.error(f"Scan {scan_id} not found")
            return None
            
        scan_name = scan_info[0]
        scan_target = scan_info[1]
        
        misp_event = MispEvent(
            info=f"SpiderFoot Scan: {scan_name}",
            timestamp=int(scan_info[2])  # created timestamp
        )
        
        # Add target as an attribute
        target_type = "domain" if "." in scan_target else "text"
        misp_event.add_attribute(
            MispAttribute(type=target_type, value=scan_target, category="Payload delivery")
        )
        
        # Get scan results and convert to MISP objects/attributes
        results = self.db.scanResultEvent(scan_id)
        
        # Group results by type for better organization
        results_by_type = {}
        for result in results:
            if result[4] not in results_by_type:
                results_by_type[result[4]] = []
            results_by_type[result[4]].append(result)
            
        # Process results by type
        for event_type, events in results_by_type.items():
            # Create a MISP object for each event type
            misp_obj = MispObject(
                name=f"sf-{event_type.lower().replace('_', '-')}",
                description=f"SpiderFoot {event_type} findings"
            )
            
            # Add events as attributes to the object
            for event in events:
                event_data = event[1]
                module = event[3]
                confidence = event[5]
                
                # Map SpiderFoot event types to MISP attribute types
                attr_type = self._map_sf_type_to_misp_type(event_type)
                attr_category = self._map_sf_type_to_misp_category(event_type)
                
                # Create attribute
                attr = MispAttribute(
                    type=attr_type,
                    value=event_data,
                    category=attr_category,
                    comment=f"Found by SpiderFoot module: {module}",
                    to_ids=confidence > 75  # Only high confidence items for IDS
                )
                
                misp_obj.add_attribute(attr)
                
            # Only add object if it has attributes
            if misp_obj.attributes:
                misp_event.add_object(misp_obj)
                
        return misp_event

    def _map_sf_type_to_misp_type(self, sf_type: str) -> str:
        """Map SpiderFoot event type to MISP attribute type.

        Args:
            sf_type: SpiderFoot event type

        Returns:
            str: MISP attribute type
        """
        mapping = {
            "IP_ADDRESS": "ip-src",
            "IPV6_ADDRESS": "ip-src",
            "INTERNET_NAME": "hostname",
            "AFFILIATE_INTERNET_NAME": "hostname",
            "DOMAIN_NAME": "domain",
            "DOMAIN_NAME_PARENT": "domain",
            "EMAILADDR": "email",
            "URL": "url",
            "PHONE_NUMBER": "phone-number",
            "WEBSERVER_BANNER": "text",
            "LEAKSITE_URL": "url",
            "HASH": "md5",  # Depends on the actual hash type
            "HASH_MD5": "md5",
            "HASH_SHA1": "sha1",
            "HASH_SHA256": "sha256",
            "HUMAN_NAME": "text",
            "BITCOIN_ADDRESS": "btc",
            "ETHEREUM_ADDRESS": "text",  # MISP doesn't have a specific type for this
            "BGP_AS_OWNER": "AS",
            "COMPANY_NAME": "text",
            "SSL_CERTIFICATE_RAW": "x509-fingerprint-sha1",
            "RAW_RIR_DATA": "text",
            "TARGET_WEB_CONTENT": "text",
            "WEBSERVER_HTTPHEADERS": "http-method",
            "SOFTWARE_USED": "filename",
            "PROVIDER_DNS": "hostname",
            "PROVIDER_MAIL": "email-dst",
            "PHYSICAL_ADDRESS": "text",
            "PHYSICAL_COORDINATES": "geolocation",
            "PGP_KEY": "pgp-public-key",
        }
        
        return mapping.get(sf_type, "text")

    def _map_sf_type_to_misp_category(self, sf_type: str) -> str:
        """Map SpiderFoot event type to MISP category.

        Args:
            sf_type: SpiderFoot event type

        Returns:
            str: MISP attribute category
        """
        mapping = {
            "IP_ADDRESS": "Network activity",
            "IPV6_ADDRESS": "Network activity",
            "INTERNET_NAME": "Network activity",
            "AFFILIATE_INTERNET_NAME": "Network activity",
            "DOMAIN_NAME": "Network activity",
            "DOMAIN_NAME_PARENT": "Network activity",
            "EMAILADDR": "Payload delivery",
            "URL": "Network activity",
            "PHONE_NUMBER": "Person",
            "WEBSERVER_BANNER": "Network activity",
            "LEAKSITE_URL": "Attribution",
            "HASH": "Payload installation",
            "HASH_MD5": "Payload installation",
            "HASH_SHA1": "Payload installation",
            "HASH_SHA256": "Payload installation",
            "HUMAN_NAME": "Person",
            "BITCOIN_ADDRESS": "Financial",
            "ETHEREUM_ADDRESS": "Financial",
            "BGP_AS_OWNER": "Network activity",
            "COMPANY_NAME": "Attribution",
            "MALICIOUS_IPADDR": "Attribution",
            "MALICIOUS_INTERNET_NAME": "Attribution",
            "VULNERABILITY_CVE_CRITICAL": "Artifacts dropped",
            "VULNERABILITY_CVE_HIGH": "Artifacts dropped",
            "SSL_CERTIFICATE_RAW": "Network activity",
            "SSL_CERTIFICATE_ISSUED": "Network activity",
            "SSL_CERTIFICATE_ISSUER": "Network activity",
            "TCP_PORT_OPEN": "Network activity",
            "UDP_PORT_OPEN": "Network activity",
            "PHYSICAL_ADDRESS": "Person",
            "PHYSICAL_COORDINATES": "Person",
            "PGP_KEY": "Person",
            "PROVIDER_DNS": "Support",
            "PROVIDER_MAIL": "Support",
        }
        
        return mapping.get(sf_type, "Other")

    def convert_sf_event_to_misp_attribute(self, sf_event: SpiderFootEvent) -> MispAttribute:
        """Convert a SpiderFoot event to a MISP attribute.

        Args:
            sf_event: SpiderFoot event

        Returns:
            MispAttribute: MISP attribute
        """
        attr_type = self._map_sf_type_to_misp_type(sf_event.eventType)
        attr_category = self._map_sf_type_to_misp_category(sf_event.eventType)
        
        # Add confidence as a tag if available
        tags = []
        if hasattr(sf_event, "tags") and sf_event.tags:
            tags = sf_event.tags
        
        attr = MispAttribute(
            type=attr_type,
            value=sf_event.data,
            category=attr_category,
            comment=f"Found by SpiderFoot module: {sf_event.module}",
            to_ids=sf_event.confidence > 75,  # Only high confidence items for IDS
            timestamp=int(sf_event.generated),
            tags=tags
        )
        
        # Add additional MISP attributes from event if available
        if hasattr(sf_event, "misp_attributes") and sf_event.misp_attributes:
            for k, v in sf_event.misp_attributes.items():
                if not hasattr(attr, k):
                    setattr(attr, k, v)
                
        return attr

    def export_misp_event(self, misp_event: MispEvent, format: str = "json") -> Union[str, Dict]:
        """Export MISP event to the specified format.

        Args:
            misp_event: MISP event to export
            format: Output format (json or dict)

        Returns:
            Union[str, Dict]: Exported event
        """
        event_dict = misp_event.to_dict()
        
        if format.lower() == "json":
            return json.dumps(event_dict, indent=2)
            
        return event_dict
        
    def save_misp_event(self, misp_event: MispEvent, scan_id: str) -> bool:
        """Save MISP event to the database.

        Args:
            misp_event: MISP event to save
            scan_id: Scan instance ID

        Returns:
            bool: Success
        """
        try:
            # First store objects
            for obj in misp_event.objects:
                obj_dict = obj.to_dict()
                obj_dict["scan_instance_id"] = scan_id
                self.db.storeObject(obj, True)
                
            # Store standalone attributes
            for attr in misp_event.attributes:
                attr_dict = attr.to_dict()
                attr_dict["scan_instance_id"] = scan_id
                self.db.storeAttribute(attr, scan_id)
                
            # Store event metadata
            event_dict = misp_event.to_dict()
            event_dict["scan_instance_id"] = scan_id
            
            # Store tags
            for tag in misp_event.tags:
                self.db.storeMispTag(tag, scan_id)
                
            return True
        except Exception as e:
            self.log.error(f"Error saving MISP event: {e}")
            return False

    @staticmethod
    def get_misp_type_mapping() -> Dict[str, str]:
        """Get mapping from SpiderFoot event types to MISP types.

        Returns:
            Dict: Mapping of SpiderFoot types to MISP types
        """
        return {
            "IP_ADDRESS": "ip-src",
            "IPV6_ADDRESS": "ip-src",
            "INTERNET_NAME": "hostname",
            "AFFILIATE_INTERNET_NAME": "hostname",
            "DOMAIN_NAME": "domain",
            "DOMAIN_NAME_PARENT": "domain",
            "EMAILADDR": "email",
            "URL_UNVERIFIED": "url",
            "URL": "url",
            "PHONE_NUMBER": "phone-number",
            "WEBSERVER_BANNER": "text",
            "LEAKSITE_URL": "url",
            "HASH_MD5": "md5",
            "HASH_SHA1": "sha1",
            "HASH_SHA256": "sha256",
            "HUMAN_NAME": "text",
            "BITCOIN_ADDRESS": "btc",
            "ETHEREUM_ADDRESS": "text",
            "BGP_AS_OWNER": "AS",
            "COMPANY_NAME": "text",
            "AFFILIATE_COMPANY_NAME": "text",
            "COUNTRY_NAME": "text",
            "RAW_RIR_DATA": "text",
            "SSL_CERTIFICATE_RAW": "x509-fingerprint-sha1",
        }
