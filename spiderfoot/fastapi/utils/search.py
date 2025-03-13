"""
SpiderFoot FastAPI Search Utilities

This module provides utilities for search operations in the SpiderFoot API.
"""

import html
import time
from typing import List, Dict, Any, Optional, Union

from spiderfoot import SpiderFootDb
from spiderfoot.fastapi.utils.logging import get_logger

logger = get_logger("spiderfoot.api.search")


class SearchHelper:
    """Helper class for search operations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize search helper.
        
        Args:
            config: SpiderFoot configuration
        """
        self.config = config
        self.dbh = SpiderFootDb(config)
    
    def search_by_criteria(
        self,
        scan_id: Optional[str] = None,
        event_type: Optional[str] = None,
        value: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for data based on criteria.
        
        Args:
            scan_id: Optional scan ID to filter by
            event_type: Optional event type to filter by
            value: Optional value to filter by
            
        Returns:
            List of search results
        """
        retdata = []

        if not scan_id and not event_type and not value:
            return retdata

        value = value or ""

        # Handle regex search
        regex = ""
        if value.startswith("/") and value.endswith("/"):
            regex = value[1: len(value) - 1]
            value = ""

        value = value.replace("*", "%")
        if value in [None, ""] and regex in [None, ""]:
            value = "%"
            regex = ""

        criteria = {
            "scan_id": scan_id or "",
            "type": event_type or "",
            "value": value or "",
            "regex": regex or "",
        }

        try:
            data = self.dbh.search(criteria)
        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            return retdata

        for row in data:
            lastseen = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
            escapeddata = html.escape(row[1])
            escapedsrc = html.escape(row[2])
            retdata.append(
                {
                    "lastSeen": lastseen,
                    "data": escapeddata,
                    "source": escapedsrc,
                    "type": row[3],
                    "module": row[5],
                    "scanId": row[6],
                    "scanName": row[7],
                    "scanTarget": row[8],
                    "falsePositive": row[10],
                    "risk": row[11],
                    "eventId": row[4],
                    "correlationId": row[13],
                    "correlationRuleId": row[14],
                }
            )

        return retdata
    
    def get_scan_history(self, scan_id: str) -> List[Dict[str, Any]]:
        """Get historical data for a scan.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            List of historical data points
        """
        try:
            data = self.dbh.scanResultHistory(scan_id)
            return [
                {
                    "timestamp": row[0],
                    "count": row[1]
                } 
                for row in data
            ]
        except Exception as e:
            logger.error(f"Error getting scan history: {str(e)}", exc_info=True)
            return []
