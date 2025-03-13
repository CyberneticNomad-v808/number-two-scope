"""
SpiderFoot FastAPI Database Utilities

This module provides utilities for working with the SpiderFoot database.
It abstracts common database operations used across the API.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Union, Tuple

from spiderfoot import SpiderFootDb
from spiderfoot.fastapi.models.scan import ScanListItem
from spiderfoot.fastapi.utils.logging import get_logger

logger = get_logger("spiderfoot.api.database")


class DatabaseHelper:
    """Helper class for database operations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize database helper.
        
        Args:
            config: SpiderFoot configuration
        """
        self.config = config
        self.dbh = SpiderFootDb(config)
    
    def get_scan_list(self) -> List[Dict[str, Any]]:
        """Get list of all scans.
        
        Returns:
            List of scan details
        """
        data = self.dbh.scanInstanceList()
        retdata = []

        for row in data:
            created = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(row[3]))
            riskmatrix = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
            correlations = self.dbh.scanCorrelationSummary(row[0], by="risk")
            if correlations:
                for c in correlations:
                    riskmatrix[c[0]] = c[1]

            if row[4] == 0:
                started = "Not yet"
            else:
                started = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(row[4]))

            if row[5] == 0:
                finished = "Not yet"
            else:
                finished = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(row[5]))

            retdata.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "target": row[2],
                    "created": created,
                    "started": started,
                    "finished": finished,
                    "status": row[6],
                    "total_events": row[7],
                    "risk_matrix": riskmatrix,
                }
            )

        return retdata
    
    def get_scan_status(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a scan.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            Scan status details or None if scan not found
        """
        data = self.dbh.scanInstanceGet(scan_id)
        
        if not data:
            return None
            
        created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[2]))
        started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[3]))
        ended = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[4]))
        
        riskmatrix = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        correlations = self.dbh.scanCorrelationSummary(scan_id, by="risk")
        if correlations:
            for c in correlations:
                riskmatrix[c[0]] = c[1]
                
        return {
            "id": data[0],
            "name": data[1],
            "created": created,
            "started": started,
            "ended": ended,
            "status": data[5],
            "risk_matrix": riskmatrix
        }
    
    def delete_scan(self, scan_id: str) -> bool:
        """Delete a scan.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.dbh.scanInstanceDelete(scan_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete scan {scan_id}: {str(e)}", exc_info=True)
            return False
    
    def stop_scan(self, scan_id: str) -> bool:
        """Stop a running scan.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.dbh.scanInstanceSet(scan_id, status="ABORT-REQUESTED")
            return True
        except Exception as e:
            logger.error(f"Failed to stop scan {scan_id}: {str(e)}", exc_info=True)
            return False
    
    def get_scan_config(self, scan_id: str) -> Dict[str, str]:
        """Get configuration for a scan.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            Scan configuration
        """
        return self.dbh.scanConfigGet(scan_id)
    
    def get_event_types(self) -> List[Tuple[str, str]]:
        """Get all event types.
        
        Returns:
            List of event types (description, type)
        """
        return self.dbh.eventTypes()
    
    def get_scan_logs(self, scan_id: str) -> List[List[Any]]:
        """Get logs for a scan.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            List of log entries
        """
        return self.dbh.scanLogs(scan_id)
    
    def get_scan_results(
        self, 
        scan_id: str, 
        event_type: Optional[str] = None, 
        filter_fp: bool = False
    ) -> List[List[Any]]:
        """Get results for a scan.
        
        Args:
            scan_id: Scan ID
            event_type: Optional event type to filter by
            filter_fp: Whether to filter out false positives
            
        Returns:
            List of scan results
        """
        return self.dbh.scanResultEvent(scan_id, event_type, filter_fp)
