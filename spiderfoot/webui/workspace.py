import cherrypy
import json
from mako.template import Template
from spiderfoot.workspace import SpiderFootWorkspace
from spiderfoot import __version__

class WorkspaceEndpoints:
    @cherrypy.expose
    def workspaces(self):
        """Show workspace management page.

        Returns:
            str: Workspace management page HTML
        """
        # Generate CSRF token for the session
        csrf_token = None
        try:
            # Try to get CSRF token from security middleware
            if hasattr(cherrypy, 'session') and hasattr(cherrypy.tools, 'csrf'):
                from spiderfoot.csrf_protection import csrf_token as get_csrf_token
                csrf_token = get_csrf_token()
        except Exception as e:
            self.log.warning(f"Could not generate CSRF token: {e}")
            csrf_token = "disabled"

        templ = Template(filename='spiderfoot/templates/workspaces.tmpl', lookup=self.lookup)
        return templ.render(
            pageid='WORKSPACES',
            docroot=self.docroot,
            version=__version__,
            csrf_token=csrf_token
        )

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspacelist(self):
        try:
            workspaces = SpiderFootWorkspace.list_workspaces(self.config)
            return workspaces
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspacecreate(self, name, description=''):
        try:
            ws = SpiderFootWorkspace(self.config, name=name)
            ws.description = description
            ws.save_workspace()
            return {"success": True, "workspace_id": ws.workspace_id}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspaceget(self, workspace_id):
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            return {
                "workspace_id": ws.workspace_id,
                "name": ws.name,
                "description": ws.description,
                "created_time": ws.created_time,
                "modified_time": ws.modified_time,
                "targets": ws.get_targets(),
                "scans": ws.get_scans(),
                "metadata": ws.metadata
            }
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspaceupdate(self, workspace_id, name=None, description=None):
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            if name:
                ws.name = name
            if description:
                ws.description = description
            ws.save_workspace()
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspacedelete(self, workspace_id):
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            ws.delete_workspace()
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspacesummary(self, workspace_id):
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            return ws.get_workspace_summary()
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspaceaddtarget(self, workspace_id, target, target_type=None):
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            target_id = ws.add_target(target, target_type)
            return {"success": True, "target_id": target_id}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspaceremovetarget(self, workspace_id, target_id):
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            ok = ws.remove_target(target_id)
            return {"success": ok}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspaceimportscans(self, workspace_id, scan_ids):
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            scan_id_list = [s.strip() for s in scan_ids.split(',') if s.strip()]
            results = ws.bulk_import_scans(scan_id_list)
            return {"success": True, "results": results}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspacemultiscan(self, workspace_id, targets, modules, scan_name_prefix, enable_correlation='false'):
        self.log.info(f"[MULTISCAN] Starting multi-target scan for workspace: {workspace_id}")
        self.log.debug(f"[MULTISCAN] Input parameters - targets: {targets}, modules: {modules}, prefix: {scan_name_prefix}")
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            # Parse targets and modules as JSON (they could be JSON strings or already parsed)
            if isinstance(targets, str):
                target_list = json.loads(targets)
            else:
                target_list = targets

            if isinstance(modules, str):
                module_list = json.loads(modules)
            else:
                module_list = modules
            # Get logging queue from the parent WebUiRoutes class
            logging_queue = getattr(self, 'loggingQueue', None)
            results = ws.start_multiscan(target_list, module_list, scan_name_prefix, enable_correlation, logging_queue)
            return {"success": True, "results": results}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspacemcpreport(self, workspace_id, report_type, format='json', include_correlations='true', include_threat_intel='true', include_recommendations='true', tlp_level='amber'):
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            report = ws.generate_mcp_report(report_type, format, include_correlations, include_threat_intel, include_recommendations, tlp_level)
            return {"success": True, "download_url": report.get('download_url', ''), "error": report.get('error', '')}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspacetiming(self, workspace_id, timezone=None, default_start_time=None, retention_period=None, auto_scheduling=None, business_hours_only=None, enable_throttling=None, business_start=None, business_end=None):
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            timing = ws.update_timing_config(timezone, default_start_time, retention_period, auto_scheduling, business_hours_only, enable_throttling, business_start, business_end)
            return {"success": True, "timing": timing}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspacescanresults(self, workspace_id, scan_id=None, event_type=None, limit=100):
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            results = ws.get_scan_results(scan_id=scan_id, event_type=event_type, limit=limit)
            return {"results": results}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspacescancorrelations(self, workspace_id):
        # Bugs fixed here: the response never included a 'success' key in
        # either branch, so workspace_details.tmpl's loadCorrelations()
        # (which checks `if (data.success)`) always took the error path --
        # even when this call succeeded and found real correlations,
        # reading the also-undefined data.error, producing exactly "Error
        # loading correlations: undefined" regardless of actual data.
        # Separately, the shape didn't match what the frontend reads at
        # all: it expects correlation_groups (grouped by rule name, not a
        # flat list), total_correlations/cross_scan_patterns/
        # finished_scans/total_scans summary counts, and per-item fields
        # named rule_risk/rule_description (get_cross_scan_correlations()
        # returns risk/description).
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            scan_details = ws.get_scan_details()
            total_scans = len(scan_details)
            finished_scans = sum(
                1 for s in scan_details if s.get('status') == 'FINISHED'
            )

            correlations = ws.get_cross_scan_correlations()

            correlation_groups = {}
            for corr in correlations:
                rule_name = corr.get('rule_name') or corr.get('title') or 'Unknown'
                correlation_groups.setdefault(rule_name, []).append({
                    'scan_id': corr.get('scan_id'),
                    'rule_risk': corr.get('risk'),
                    'rule_description': corr.get('description'),
                })

            response = {
                'success': True,
                'correlations': correlations,
                'correlation_groups': correlation_groups,
                'total_correlations': len(correlations),
                'cross_scan_patterns': len(correlation_groups),
                'finished_scans': finished_scans,
                'total_scans': total_scans,
            }
            if not correlations:
                response['message'] = (
                    "Need at least 2 completed scans for cross-correlation "
                    "analysis." if finished_scans < 2 else
                    "No correlations found across this workspace's "
                    "finished scans."
                )
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspaceruncorrelations(self, workspace_id):
        # This endpoint didn't exist at all -- confirmed live, a 404 --
        # which is why workspace_details.tmpl's "Run Correlation
        # Analysis" button always failed with "Failed to start
        # correlation analysis: Server error" (jQuery's .fail() callback,
        # triggered by any non-2xx response). See
        # SpiderFootWorkspace.run_cross_scan_correlations() for why this
        # needed a real cross-scan implementation, not just a stub: the
        # existing per-scan correlation (scan_service/scanner.py) never
        # ran with more than one scan's own ID.
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            correlated_count = ws.run_cross_scan_correlations()
            return {"success": True, "correlations_created": correlated_count}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @cherrypy.expose
    def workspacedetails(self, workspace_id):
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)

            # Ensure workspace has required attributes
            if not hasattr(ws, 'name') or not ws.name:
                return f"Error: Workspace {workspace_id} not found or has no name"

            # Generate CSRF token for the session
            csrf_token = None
            try:
                # Try to get CSRF token from security middleware
                if hasattr(cherrypy, 'session') and hasattr(cherrypy.tools, 'csrf'):
                    from spiderfoot.csrf_protection import csrf_token as get_csrf_token
                    csrf_token = get_csrf_token()
            except Exception as e:
                self.log.warning(f"Could not generate CSRF token: {e}")
                csrf_token = "disabled"

            # Load scans for the workspace
            scan_details = []
            try:
                scan_details = ws.get_scan_details()
            except Exception as e:
                self.log.warning(f"Could not load scans for workspace {workspace_id}: {e}")

            # Use the template
            templ = Template(filename='spiderfoot/templates/workspace_details.tmpl', lookup=self.lookup)
            return templ.render(
                workspace=ws,
                scan_details=scan_details,
                docroot=self.docroot,
                version=__version__,
                csrf_token=csrf_token
            )
        except Exception as e:
            self.log.error(f"Error loading workspace details for {workspace_id}: {e}", exc_info=True)
            return f"Error loading workspace details: {str(e)}"

    @cherrypy.expose
    def workspacereportdownload(self, report_id, workspace_id, format='json'):
        try:
            # Placeholder: implement report download logic
            cherrypy.response.headers['Content-Disposition'] = f"attachment; filename=workspace-{workspace_id}-report.{format}"
            cherrypy.response.headers['Content-Type'] = f"application/{format}"
            cherrypy.response.headers['Pragma'] = 'no-cache'
            return "{}"
        except Exception as e:
            return str(e)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def workspaceperiodicscans(self, workspace_id):
        """Get periodic scan schedules for workspace.

        Stub implementation - returns empty schedules array.
        Full periodic scan scheduling feature is not yet implemented.
        See /stuff/PROJECTS.md for future enhancement plans.

        Args:
            workspace_id: The workspace ID to get schedules for

        Returns:
            dict: JSON response with success status and empty schedules array
        """
        try:
            # TODO: Implement full periodic scan scheduling feature
            # - Database table: tbl_workspace_schedules
            # - CRUD endpoints for schedule management
            # - Background scheduler service
            # - UI forms for creating/editing schedules
            return {
                "success": True,
                "schedules": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "schedules": []
            }
