"""SpiderFoot event module.

This module defines the SpiderFootEvent class used throughout the
application to represent different types of data discovered during a
scan.
"""

import hashlib
import time
from typing import Any, Dict, Optional, Union, List

from spiderfoot.logconfig import get_module_logger


class SpiderFootEvent:
    """SpiderFootEvent object representing events of data found for a scan
    target.

    Attributes:
        eventType (str): Event type, e.g. URL_FORM, DOMAIN_NAME, etc.
        data (str): Event data, e.g. a URL, hostname, IP address
        module (str): Module from which the event originated
        sourceEvent (SpiderFootEvent): Source event that led to this event
        confidence (int): How sure are we of this data's validity (0-100)
        visibility (int): How 'visible' is this data (0-100)
        risk (int): How much risk does this data represent (0-100)
        sourceEventHash (str): Hash of the source event
        actualSource (str): Source module of the source event
        hash (str): Unique SHA256 hash of the event
        generated (float): UNIX timestamp when the event was generated
        tags (List[str]): MISP-compatible taxonomic tags
        misp_attributes (Dict[str, Any]): Additional MISP attribute values
        misp_category (str): MISP category for this event
    """

    def __init__(
        self,
        eventType: str,
        data: str,
        module: str,
        sourceEvent: Optional["SpiderFootEvent"] = None,
        confidence: int = 100,
        visibility: int = 100,
        risk: int = 0,
        sourceEventHash: Optional[str] = None,
    ) -> None:
        """Initialize a SpiderFoot event.

        Args:
            eventType: Event type, e.g. URL_FORM, DOMAIN_NAME, etc.
            data: Event data, e.g. a URL, hostname, IP address
            module: Module from which the event originated
            sourceEvent: Source event that led to this event
            confidence: How sure are we of this data's validity (0-100)
            visibility: How 'visible' is this data (0-100)
            risk: How much risk does this data represent (0-100)
            sourceEventHash: Hash of the source event

        Raises:
            TypeError: Argument type was invalid
            ValueError: Argument value was invalid
        """
        self.log = get_module_logger("event")

        # Validate eventType
        if not isinstance(eventType, str):
            raise TypeError(f"eventType is {type(eventType)}; expected str()")
        if not eventType:
            raise ValueError("eventType is empty")

        # Validate data
        if not isinstance(data, str):
            raise TypeError(f"data is {type(data)}; expected str()")
        if not data:
            raise ValueError("data is empty")

        # Validate module
        if not isinstance(module, str):
            raise TypeError(f"module is {type(module)}; expected str()")
        if not module:
            raise ValueError("module is empty")

        # Validate sourceEvent
        if sourceEvent and not isinstance(sourceEvent, SpiderFootEvent):
            raise TypeError(
                f"sourceEvent is {type(sourceEvent)}; expected SpiderFootEvent()"
            )

        # Validate confidence
        if not isinstance(confidence, int):
            raise TypeError(
                f"confidence is {type(confidence)}; expected int()")
        if not 0 <= confidence <= 100:
            raise ValueError(
                f"confidence value is {confidence}; expected 0-100")

        # Validate visibility
        if not isinstance(visibility, int):
            raise TypeError(
                f"visibility is {type(visibility)}; expected int()")
        if not 0 <= visibility <= 100:
            raise ValueError(
                f"visibility value is {visibility}; expected 0-100")

        # Validate risk
        if not isinstance(risk, int):
            raise TypeError(f"risk is {type(risk)}; expected int()")
        if not 0 <= risk <= 100:
            raise ValueError(f"risk value is {risk}; expected 0-100")

        # For deep event trees we don't need to track back the entire chain
        self.sourceEvent = sourceEvent
        self.eventType = eventType
        self.data = data
        self.module = module
        self.confidence = confidence
        self.visibility = visibility
        self.risk = risk
        self.generated = time.time()

        # MISP compatibility attributes
        self.tags: List[str] = []
        self.misp_attributes: Dict[str, Any] = {}
        self.misp_category: Optional[str] = None

        # Get the hash of the source event
        if sourceEvent:
            self.sourceEventHash = sourceEvent.hash
            # Keep track of the source module by combining the event's module and source_module values
            self.actualSource = f"{sourceEvent.module}"

            # Inherit tags from source event
            if hasattr(sourceEvent, 'tags'):
                self.tags = sourceEvent.tags.copy()
        else:
            self.sourceEventHash = sourceEventHash or "ROOT"
            self.actualSource = module

        # Create a unique hash of the event to avoid reporting the same data multiple times
        self.hash = self._generateHash()

        # Automatically add confidence tag based on confidence score
        self._add_confidence_tag()

        self.log.debug(
            f"Created event {eventType}: {data[:30]}... from {module}")

    def _generateHash(self) -> str:
        """Generate a unique hash for this event.

        Returns:
            str: SHA256 hash of the event data
        """
        sha256 = hashlib.sha256()

        # Different event types and modules may have the same data, so include those
        # fields in the hash calculation
        hash_components = (
            f"{self.eventType}{self.data}{self.module}{self.sourceEventHash}"
        ).encode("utf-8", errors="replace")

        sha256.update(hash_components)
        return sha256.hexdigest()

    def _add_confidence_tag(self) -> None:
        """Add a confidence tag based on the confidence score."""
        if self.confidence >= 75:
            self.add_tag("confidence:high")
        elif self.confidence >= 40:
            self.add_tag("confidence:medium")
        else:
            self.add_tag("confidence:low")

    def add_tag(self, tag: str) -> None:
        """Add a MISP-compatible taxonomic tag.

        Args:
            tag: Tag to add (e.g., 'tlp:amber', 'confidence:high')
        """
        if tag not in self.tags:
            self.tags.append(tag)

    def set_misp_category(self, category: str) -> None:
        """Set the MISP category for this event.

        Args:
            category: MISP category (e.g., 'Network activity', 'Person')
        """
        self.misp_category = category

    def set_misp_attribute(self, key: str, value: Any) -> None:
        """Set a MISP attribute for this event.

        Args:
            key: Attribute name
            value: Attribute value
        """
        self.misp_attributes[key] = value

    def get_misp_type(self) -> str:
        """Get the appropriate MISP attribute type for this event.

        Returns:
            str: MISP attribute type
        """
        from spiderfoot.misp_integration import MispIntegration

        mapping = MispIntegration.get_misp_type_mapping()
        return mapping.get(self.eventType, "text")

    def asDict(self) -> Dict[str, Any]:
        """Get event as dictionary.

        Returns:
            dict: Event as a dictionary
        """
        event_dict = {
            "type": self.eventType,
            "data": self.data,
            "module": self.module,
            "confidence": self.confidence,
            "visibility": self.visibility,
            "risk": self.risk,
            "hash": self.hash,
            "sourceEventHash": self.sourceEventHash,
            "actualSource": self.actualSource,
            "generated": self.generated,
        }

        # Add MISP attributes if present
        if hasattr(self, 'tags') and self.tags:
            event_dict["tags"] = self.tags

        if hasattr(self, 'misp_category') and self.misp_category:
            event_dict["misp_category"] = self.misp_category

        if hasattr(self, 'misp_attributes') and self.misp_attributes:
            event_dict["misp_attributes"] = self.misp_attributes

        return event_dict

    def __str__(self) -> str:
        """Get a string representation of the event.

        Returns:
            str: String representation
        """
        return (
            f"<{self.__class__.__name__}(eventType='{self.eventType}', "
            f"data='{self.data[:30]}{'...' if len(self.data) > 30 else ''}', "
            f"module='{self.module}')>"
        )

    def __eq__(self, other: Any) -> bool:
        """Compare events.

        Args:
            other: Another event to compare with

        Returns:
            bool: True if events are equal
        """
        if not isinstance(other, SpiderFootEvent):
            return False

        return self.hash == other.hash

    def __hash__(self) -> int:
        """Get hash of event.

        Returns:
            int: Hash value
        """
        return hash(self.hash)
