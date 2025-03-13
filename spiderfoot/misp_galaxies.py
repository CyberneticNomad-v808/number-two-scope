"""MISP Galaxy support for SpiderFoot.

This module provides integration with MISP Galaxies to enhance threat
intelligence.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from spiderfoot.logconfig import get_module_logger


class MispGalaxy:
    """MISP Galaxy representation for SpiderFoot."""

    def __init__(self, name: str, description: str = None, uuid: str = None):
        """Initialize a MISP Galaxy.

        Args:
            name: Galaxy name
            description: Galaxy description
            uuid: Galaxy UUID
        """
        self.log = get_module_logger('misp_galaxies')
        self.name = name
        self.description = description
        self.uuid = uuid
        self.clusters: List[Dict[str, Any]] = []
        
    def add_cluster(self, cluster: Dict[str, Any]) -> None:
        """Add a cluster to the galaxy.

        Args:
            cluster: Cluster data
        """
        self.clusters.append(cluster)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the galaxy to a dictionary.

        Returns:
            Dict: Galaxy dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "uuid": self.uuid,
            "clusters": self.clusters
        }


class MispGalaxyManager:
    """Manager class for MISP Galaxies."""

    def __init__(self):
        """Initialize the MISP Galaxy Manager."""
        self.log = get_module_logger('misp_galaxies')
        self.galaxies: Dict[str, MispGalaxy] = {}
        self.load_predefined_galaxies()
        
    def load_predefined_galaxies(self) -> None:
        """Load predefined MISP galaxies."""
        # Threat Actor Galaxy
        threat_actor = MispGalaxy(
            "threat-actor",
            "Threat Actor Galaxy",
            "698774c7-8022-42c4-917f-8d6e4f06ada3"
        )
        
        # Add APT groups
        threat_actor.add_cluster({
            "value": "APT1",
            "description": "APT1 is a Chinese threat group that has been attributed to the 2nd Bureau of the People's Liberation Army (PLA) General Staff Department's (GSD) 3rd Department, commonly known by its Military Unit Cover Designator (MUCD) as Unit 61398.",
            "meta": {
                "synonyms": ["Comment Crew", "Comment Group", "Unit 61398"],
                "country": "China",
                "refs": ["https://www.fireeye.com/content/dam/fireeye-www/services/pdfs/mandiant-apt1-report.pdf"]
            }
        })
        
        threat_actor.add_cluster({
            "value": "APT28",
            "description": "APT28 is a threat group that has been attributed to Russia's General Staff Main Intelligence Directorate (GRU) 85th Main Special Service Center (GTsSS) military unit 26165.",
            "meta": {
                "synonyms": ["Fancy Bear", "Sofacy", "Sednit", "STRONTIUM", "Pawn Storm"],
                "country": "Russia",
                "refs": ["https://www.fireeye.com/blog/threat-research/2014/10/apt28-a-window-into-russias-cyber-espionage-operations.html"]
            }
        })
        
        self.galaxies["threat-actor"] = threat_actor
        
        # Attack Pattern Galaxy
        attack_pattern = MispGalaxy(
            "attack-pattern",
            "Attack Pattern Galaxy",
            "b5a533ef-e030-4e3d-9671-89f5c8c31415"
        )
        
        attack_pattern.add_cluster({
            "value": "Spearphishing Attachment",
            "description": "Spearphishing attachment is a specific variant of spearphishing. Spearphishing attachment is different from other forms of spearphishing in that it employs the use of malware attached to an email. All forms of spearphishing are electronically delivered social engineering targeted at a specific individual, company, or industry.",
            "meta": {
                "external_id": "T1193",
                "refs": ["https://attack.mitre.org/techniques/T1193/"]
            }
        })
        
        self.galaxies["attack-pattern"] = attack_pattern
        
        # Tool Galaxy
        tool_galaxy = MispGalaxy(
            "tool",
            "Tool Galaxy",
            "d5cbd1a2-78f6-4c89-acb0-d46f9ca827a2"
        )
        
        tool_galaxy.add_cluster({
            "value": "Mimikatz",
            "description": "Mimikatz is a credential dumper capable of obtaining plaintext Windows account logins and passwords, along with many other features that make it useful for testing the security of networks.",
            "meta": {
                "refs": ["https://github.com/gentilkiwi/mimikatz"]
            }
        })
        
        self.galaxies["tool"] = tool_galaxy
        
    def get_galaxy(self, name: str) -> Optional[MispGalaxy]:
        """Get a galaxy by name.

        Args:
            name: Galaxy name

        Returns:
            MispGalaxy: Galaxy object or None if not found
        """
        return self.galaxies.get(name)
        
    def add_galaxy(self, galaxy: MispGalaxy) -> None:
        """Add a galaxy.

        Args:
            galaxy: Galaxy to add
        """
        self.galaxies[galaxy.name] = galaxy
