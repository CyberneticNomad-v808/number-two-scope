import cherrypy
import csv
import json
import time
from io import StringIO
from xml.etree import ElementTree as ET
from xml.dom import minidom
from mako.template import Template
from spiderfoot.workspace import SpiderFootWorkspace
from spiderfoot import __version__, SpiderFootDb

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
                # Required by the Generate Report modal's JS
                # (templates/workspace_details.tmpl), which gates report
                # generation on `data.success && data.scans && ...`. This
                # key was missing entirely on the success path, so that
                # check could never pass and the "No Scans Available"
                # dialog fired unconditionally regardless of how many
                # scans existed or whether they'd finished.
                "success": True,
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
        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
            correlations = ws.get_cross_scan_correlations()
            return {"correlations": correlations}
        except Exception as e:
            return {"error": str(e)}

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
    def workspacereportexport(self, workspace_id, format='json'):
        """Export all events from every scan in a workspace as a single
        JSON, CSV, or XML file.

        This is the actual working replacement for the "Generate Report"
        button in workspace_details.tmpl, which previously pointed at a
        route (/scanexport) that never existed, and at workspacemcpreport /
        workspacereportdownload, which called an undefined method
        (SpiderFootWorkspace.generate_mcp_report) and returned an empty
        placeholder respectively. No LLM/AI dependency, no external
        service -- straight scan_instance_id + tbl_scan_results dump,
        same DB access pattern as the already-working
        scanexportjsonmulti/scaneventresultexportmulti in webui/export.py.
        """
        fmt = (format or 'json').lower()
        if fmt not in ('json', 'csv', 'xml'):
            cherrypy.response.status = 400
            return json.dumps({"error": f"Unsupported format: {format}. Use json, csv, or xml."}).encode('utf-8')

        try:
            ws = SpiderFootWorkspace(self.config, workspace_id=workspace_id)
        except Exception as e:
            cherrypy.response.status = 404
            return json.dumps({"error": f"Workspace not found: {e}"}).encode('utf-8')

        dbh = SpiderFootDb(self.config)
        rows = []
        for scan_id in ws.get_scan_ids():
            scan_info = dbh.scanInstanceGet(scan_id)
            scan_name = scan_info[0] if scan_info else scan_id
            scan_status = scan_info[5] if scan_info and len(scan_info) > 5 else ""
            try:
                events = dbh.scanResultEvent(scan_id)
            except Exception:
                continue
            for event in events:
                # scanResultEvent() column order: generated, data, module,
                # hash, type, source_event_hash, confidence, visibility, risk
                generated, data, module, event_hash, event_type, source_hash, confidence, visibility, risk = event[:9]
                if event_type == "ROOT":
                    continue
                rows.append({
                    "scan_id": scan_id,
                    "scan_name": scan_name,
                    "scan_status": scan_status,
                    "generated": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(generated)) if generated else "",
                    "event_type": event_type,
                    "module": module,
                    "data": str(data).replace("<SFURL>", "").replace("</SFURL>", ""),
                    "confidence": confidence,
                    "visibility": visibility,
                    "risk": risk,
                    "event_hash": event_hash,
                    "source_event_hash": source_hash,
                })

        fname = f"workspace-{workspace_id}-report.{fmt}"
        cherrypy.response.headers['Content-Disposition'] = f"attachment; filename={fname}"
        cherrypy.response.headers['Pragma'] = 'no-cache'

        if fmt == 'json':
            cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
            return json.dumps({
                "workspace_id": workspace_id,
                "workspace_name": ws.name,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "event_count": len(rows),
                "events": rows,
            }, indent=2).encode('utf-8')

        if fmt == 'csv':
            cherrypy.response.headers['Content-Type'] = "text/csv; charset=utf-8"
            fileobj = StringIO()
            fieldnames = ["scan_id", "scan_name", "scan_status", "generated", "event_type",
                          "module", "data", "confidence", "visibility", "risk",
                          "event_hash", "source_event_hash"]
            writer = csv.DictWriter(fileobj, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            return fileobj.getvalue().encode('utf-8')

        # fmt == 'xml'
        cherrypy.response.headers['Content-Type'] = "application/xml; charset=utf-8"
        root = ET.Element("workspaceReport", {
            "workspaceId": workspace_id,
            "workspaceName": ws.name or "",
            "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
            "eventCount": str(len(rows)),
        })
        for row in rows:
            event_el = ET.SubElement(root, "event")
            for key, value in row.items():
                child = ET.SubElement(event_el, key)
                child.text = "" if value is None else str(value)
        raw_xml = ET.tostring(root, encoding="unicode")
        pretty_xml = minidom.parseString(raw_xml).toprettyxml(indent="  ")
        return pretty_xml.encode('utf-8')

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
