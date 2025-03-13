"""SpiderFoot FastAPI Visualization Utilities.

This module provides utilities for data visualization in the SpiderFoot
API.
"""

from typing import List, Dict, Any, Optional

from spiderfoot import SpiderFootDb, SpiderFootHelpers
from spiderfoot.fastapi.utils.logging import get_logger

logger = get_logger("spiderfoot.api.visualization")


class VisualizationHelper:
    """Helper class for data visualization."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize visualization helper.

        Args:
            config: SpiderFoot configuration
        """
        self.config = config
        self.dbh = SpiderFootDb(config)
    
    def get_scan_visualization_data(
        self, 
        scan_id: str, 
        as_gexf: bool = False
    ) -> Optional[Any]:
        """Get visualization data for a scan.

        Args:
            scan_id: Scan ID
            as_gexf: Whether to return data in GEXF format

        Returns:
            Visualization data in JSON or GEXF format
        """
        if not scan_id:
            return None

        try:
            data = self.dbh.scanResultEvent(scan_id, filterFp=True)
            scan = self.dbh.scanInstanceGet(scan_id)

            if not scan:
                return None

            root = scan[1]

            if as_gexf:
                return SpiderFootHelpers.buildGraphGexf([root], "SpiderFoot Export", data)
            else:
                return SpiderFootHelpers.buildGraphJson([root], data)
        except Exception as e:
            logger.error(f"Error generating visualization data: {str(e)}", exc_info=True)
            return None
    
    def get_multi_scan_visualization_data(
        self, 
        scan_ids: List[str], 
        as_gexf: bool = False
    ) -> Optional[Any]:
        """Get visualization data for multiple scans.

        Args:
            scan_ids: List of scan IDs
            as_gexf: Whether to return data in GEXF format

        Returns:
            Visualization data in JSON or GEXF format
        """
        if not scan_ids:
            return None

        all_data = []
        roots = []
        scan_name = ""

        try:
            for scan_id in scan_ids:
                scan = self.dbh.scanInstanceGet(scan_id)
                if not scan:
                    continue
                
                scan_data = self.dbh.scanResultEvent(scan_id, filterFp=True)
                all_data.extend(scan_data)
                roots.append(scan[1])
                scan_name = scan[0]  # Use the last scan name

            if not all_data:
                return None

            if as_gexf:
                return SpiderFootHelpers.buildGraphGexf(roots, "SpiderFoot Multi-Scan Export", all_data)
            else:
                return SpiderFootHelpers.buildGraphJson(roots, all_data)
        except Exception as e:
            logger.error(f"Error generating multi-scan visualization: {str(e)}", exc_info=True)
            return None
