# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# Name:         sfwebui_fastapi
# Purpose:      FastAPI implementation of SpiderFoot web interface
#
# Author:   Agostino Panico <van1sh@van1shland.io>
#
# Created:  01/03/2025
# Copyright:  (c) poppopjmp
# License:      MIT
# -----------------------------------------------------------------
import csv
import html
import json
import logging
import multiprocessing as mp
import random
import string
import time
from copy import deepcopy
from io import BytesIO, StringIO
from operator import itemgetter
from typing import Dict, List, Optional, Union, Any

from fastapi import FastAPI, Request, File, Form, UploadFile, HTTPException, Depends, BackgroundTasks, Security
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware

import openpyxl
import secure

from sflib import SpiderFoot
from sfscan import startSpiderFootScanner
from spiderfoot import SpiderFootDb
from spiderfoot import SpiderFootHelpers
from spiderfoot import __version__
from spiderfoot.logger import logListenerSetup, logWorkerSetup

from mako.lookup import TemplateLookup
from mako.template import Template
from fastapi.responses import StreamingResponse, HTMLResponse

# Import our new utilities
from spiderfoot.fastapi_logger import setup_logging, get_logger
from spiderfoot.fastapi_error_handlers import setup_error_handlers
from spiderfoot.fastapi_utils import setup_cors, APIKeyAuth, generate_api_key

mp.set_start_method("spawn", force=True)

app = FastAPI(
    title="SpiderFoot API", 
    description="SpiderFoot OSINT Automation Tool API",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Create API key auth instance
api_key_auth = None

# We'll create a class similar to SpiderFootWebUi but adapted for FastAPI
class SpiderFootFastApi:
    """SpiderFoot FastAPI web interface."""
    
    def __init__(
        self,
        web_config: dict,
        config: dict,
        loggingQueue: "logging.handlers.QueueListener" = None,
    ) -> None:
        """Initialize web server.

        Args:
            web_config (dict): config settings for web interface (interface, port, root path)
            config (dict): SpiderFoot config
            loggingQueue: TBD

        Raises:
            TypeError: arg type is invalid
            ValueError: arg value is invalid
        """
        if not isinstance(config, dict):
            raise TypeError(f"config is {type(config)}; expected dict()")
        if not config:
            raise ValueError("config is empty")

        if not isinstance(web_config, dict):
            raise TypeError(
                f"web_config is {type(web_config)}; expected dict()")
        if not config:
            raise ValueError("web_config is empty")

        self.docroot = web_config.get("root", "/").rstrip("/")
        
        # 'config' supplied will be the defaults, let's supplement them
        # now with any configuration which may have previously been saved.
        self.defaultConfig = deepcopy(config)
        dbh = SpiderFootDb(self.defaultConfig, init=True)
        sf = SpiderFoot(self.defaultConfig)
        self.config = sf.configUnserialize(dbh.configGet(), self.defaultConfig)
        
        # Initialize templates - both Jinja2 for FastAPI and Mako for legacy templates
        self.templates = Jinja2Templates(directory="spiderfoot/templates")
        self.lookup = TemplateLookup(directories=[""])
        
        # Set up logging
        if loggingQueue is None:
            self.loggingQueue = mp.Queue()
            logListenerSetup(self.loggingQueue, self.config)
        else:
            self.loggingQueue = loggingQueue
        logWorkerSetup(self.loggingQueue)
        self.log = logging.getLogger(f"spiderfoot.{__name__}")
        
        # Security setup
        self.csp = (
            secure.ContentSecurityPolicy()
            .default_src("'self'")
            .script_src("'self'", "'unsafe-inline'", "blob:")
            .style_src("'self'", "'unsafe-inline'")
            .base_uri("'self'")
            .connect_src("'self'", "data:")
            .frame_src("'self'", "data:")
            .img_src("'self'", "data:")
        )
        
        # Generate a token for CSRF protection
        self.token = None

        # Set up logger
        self.log = get_logger(f"spiderfoot.{__name__}")
        
        # Initialize API key auth if enabled
        global api_key_auth
        if web_config.get("enable_api_key_auth", False):
            api_key = web_config.get("api_key", generate_api_key())
            api_key_auth = APIKeyAuth(api_key_name="X-API-Key", api_key=api_key)
            self.log.info(f"API key authentication enabled. Key: {api_key}")
    
    # Utility methods for error handling, response formatting, etc.
    def error_response(self, message: str, status_code: int = 500) -> JSONResponse:
        """Return JSON error response.
        
        Args:
            message (str): Error message
            status_code (int): HTTP status code
            
        Returns:
            JSONResponse: JSON error response
        """
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "http_status": status_code,
                    "message": message,
                }
            }
        )
    
    def cleanUserInput(self, inputList: list) -> list:
        """Convert data to HTML entities; except quotes and ampersands.

        Args:
            inputList (list): list of strings to sanitize

        Returns:
            list: sanitized input

        Raises:
            TypeError: inputList type was invalid
        """
        if not isinstance(inputList, list):
            raise TypeError(f"inputList is {type(inputList)}; expected list()")

        ret = list()

        for item in inputList:
            if not item:
                ret.append("")
                continue
            c = html.escape(item, True)

            # Decode '&' and '"' HTML entities
            c = c.replace("&amp;", "&").replace("&quot;", '"')
            ret.append(c)

        return ret
    
    # Endpoints matching the CherryPy routes in sfwebui.py
    async def get_eventtypes(self) -> List[List[str]]:
        """List all event types.

        Returns:
            list: list of event types
        """
        dbh = SpiderFootDb(self.config)
        types = dbh.eventTypes()
        ret = list()

        for r in types:
            ret.append([r[1], r[0]])

        return sorted(ret, key=itemgetter(0))
    
    async def get_modules(self) -> List[Dict[str, str]]:
        """List all modules.

        Returns:
            list: list of modules
        """
        ret = list()

        modinfo = list(self.config["__modules__"].keys())
        if not modinfo:
            return ret

        modinfo.sort()

        for m in modinfo:
            if "__" in m:
                continue
            ret.append(
                {"name": m, "descr": self.config["__modules__"][m]["descr"]}
            )

        return ret

    async def get_correlationrules(self) -> List[Dict[str, Any]]:
        """List all correlation rules.

        Returns:
            list: list of correlation rules
        """
        ret = list()

        rules = self.config["__correlationrules__"]
        if not rules:
            return ret

        for r in rules:
            ret.append(
                {
                    "id": r["id"],
                    "name": r["meta"]["name"],
                    "descr": r["meta"]["description"],
                    "risk": r["meta"]["risk"],
                }
            )

        return ret
        
    async def do_ping(self) -> List[str]:
        """For the CLI to test connectivity to this server.

        Returns:
            list: SpiderFoot version as JSON
        """
        return ["SUCCESS", __version__]
    
    async def do_query(self, query: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """For the CLI to run queries against the database.

        Args:
            query (str): SQL query

        Returns:
            Union[List[Dict[str, Any]], Dict[str, Any]]: query results or error message
        """
        dbh = SpiderFootDb(self.config)

        if not query:
            return {"error": {"http_status": "400", "message": "Invalid query."}}

        if not query.lower().startswith("select"):
            return {"error": {
                "http_status": "400", 
                "message": "Non-SELECTs are unpredictable and not recommended."
            }}

        try:
            ret = dbh.dbh.execute(query)
            data = ret.fetchall()
            columnNames = [c[0] for c in dbh.dbh.description]
            return [dict(zip(columnNames, row)) for row in data]
        except Exception as e:
            return {"error": {"http_status": "500", "message": str(e)}}
    
    async def search_data(
        self, 
        id: Optional[str] = None, 
        eventType: Optional[str] = None, 
        value: Optional[str] = None
    ) -> List[List[Any]]:
        """Search scans.

        Args:
            id (str): filter search results by scan ID
            eventType (str): filter search results by event type
            value (str): filter search results by event value

        Returns:
            List[List[Any]]: search results
        """
        try:
            return self.searchBase(id, eventType, value)
        except Exception:
            return []
    
    async def get_scanhistory(self, id: str) -> List[Any]:
        """Historical data for a scan.

        Args:
            id (str): scan ID

        Returns:
            List[Any]: scan history
        """
        if not id:
            raise HTTPException(status_code=404, detail="No scan specified")

        dbh = SpiderFootDb(self.config)

        try:
            return dbh.scanResultHistory(id)
        except Exception:
            return []
    
    async def get_scanlist(self) -> List[List[Any]]:
        """Produce a list of scans.

        Returns:
            List[List[Any]]: scan list
        """
        dbh = SpiderFootDb(self.config)
        data = dbh.scanInstanceList()
        retdata = []

        for row in data:
            created = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(row[3]))
            riskmatrix = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
            correlations = dbh.scanCorrelationSummary(row[0], by="risk")
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
                [
                    row[0],
                    row[1],
                    row[2],
                    created,
                    started,
                    finished,
                    row[6],
                    row[7],
                    riskmatrix,
                ]
            )

        return retdata
    
    async def get_scanstatus(self, id: str) -> List[Any]:
        """Show basic information about a scan, including status and number of each event type.

        Args:
            id (str): scan ID

        Returns:
            List[Any]: scan status
        """
        dbh = SpiderFootDb(self.config)
        data = dbh.scanInstanceGet(id)

        if not data:
            return []

        created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[2]))
        started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[3]))
        ended = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[4]))
        riskmatrix = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        correlations = dbh.scanCorrelationSummary(id, by="risk")
        if correlations:
            for c in correlations:
                riskmatrix[c[0]] = c[1]

        return [data[0], data[1], created, started, ended, data[5], riskmatrix]
    
    async def delete_scan(self, id: str) -> Dict[str, Any]:
        """Delete scan(s).

        Args:
            id (str): comma separated list of scan IDs

        Returns:
            Dict[str, Any]: Status message
        """
        if not id:
            raise HTTPException(status_code=404, detail="No scan specified")

        dbh = SpiderFootDb(self.config)
        ids = id.split(",")

        for scan_id in ids:
            res = dbh.scanInstanceGet(scan_id)
            if not res:
                raise HTTPException(status_code=404, detail=f"Scan {scan_id} does not exist")

            if res[5] in ["RUNNING", "STARTING", "STARTED"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Scan {scan_id} is {res[5]}. You cannot delete running scans."
                )

        for scan_id in ids:
            dbh.scanInstanceDelete(scan_id)

        return {"status": "success", "message": f"Successfully deleted {len(ids)} scan(s)"}
    
    async def stop_scan(self, id: str) -> Dict[str, Any]:
        """Stop a scan.

        Args:
            id (str): comma separated list of scan IDs

        Returns:
            Dict[str, Any]: Status message
        """
        if not id:
            raise HTTPException(status_code=404, detail="No scan specified")

        dbh = SpiderFootDb(self.config)
        ids = id.split(",")

        for scan_id in ids:
            res = dbh.scanInstanceGet(scan_id)
            if not res:
                raise HTTPException(status_code=404, detail=f"Scan {scan_id} does not exist")

            scan_status = res[5]

            if scan_status == "FINISHED":
                raise HTTPException(
                    status_code=400,
                    detail=f"Scan {scan_id} has already finished."
                )

            if scan_status == "ABORTED":
                raise HTTPException(
                    status_code=400,
                    detail=f"Scan {scan_id} has already aborted."
                )

            if scan_status != "RUNNING" and scan_status != "STARTING":
                raise HTTPException(
                    status_code=400,
                    detail=f"The running scan is currently in the state '{scan_status}', please try again later or restart SpiderFoot."
                )

        for scan_id in ids:
            dbh.scanInstanceSet(scan_id, status="ABORT-REQUESTED")

        return {"status": "success", "message": f"Successfully requested stop for {len(ids)} scan(s)"}

    async def start_scan(
        self,
        scanname: str,
        scantarget: str,
        modulelist: Optional[str] = None,
        typelist: Optional[str] = None,
        usecase: Optional[str] = None
    ) -> Union[Dict[str, Any], str]:
        """Initiate a scan.

        Args:
            scanname (str): scan name
            scantarget (str): scan target
            modulelist (str): comma separated list of modules to use
            typelist (str): selected modules based on produced event data types
            usecase (str): selected module group (passive, investigate, footprint, all)

        Returns:
            Union[Dict[str, Any], str]: scan ID or error message
        """
        scanname = self.cleanUserInput([scanname])[0]
        scantarget = self.cleanUserInput([scantarget])[0]

        if not scanname:
            raise HTTPException(
                status_code=400,
                detail="Incorrect usage: scan name was not specified."
            )

        if not scantarget:
            raise HTTPException(
                status_code=400,
                detail="Incorrect usage: scan target was not specified."
            )

        if not typelist and not modulelist and not usecase:
            raise HTTPException(
                status_code=400,
                detail="Incorrect usage: no modules specified for scan."
            )

        targetType = SpiderFootHelpers.targetTypeFromString(scantarget)
        if targetType is None:
            raise HTTPException(
                status_code=400,
                detail="Unrecognised target type."
            )

        # Swap the globalscantable for the database handler
        dbh = SpiderFootDb(self.config)

        # Snapshot the current configuration to be used by the scan
        cfg = deepcopy(self.config)
        sf = SpiderFoot(cfg)

        modlist = list()

        # User selected modules
        if modulelist:
            modlist = modulelist.replace("module_", "").split(",")

        # User selected types
        if len(modlist) == 0 and typelist:
            typesx = typelist.replace("type_", "").split(",")

            # 1. Find all modules that produce the requested types
            modlist = sf.modulesProducing(typesx)
            newmods = deepcopy(modlist)
            newmodcpy = deepcopy(newmods)

            # 2. For each type those modules consume, get modules producing
            while len(newmodcpy) > 0:
                for etype in sf.eventsToModules(newmodcpy):
                    xmods = sf.modulesProducing([etype])
                    for mod in xmods:
                        if mod not in modlist:
                            modlist.append(mod)
                            newmods.append(mod)
                newmodcpy = deepcopy(newmods)
                newmods = list()

        # User selected a use case
        if len(modlist) == 0 and usecase:
            for mod in self.config["__modules__"]:
                if (
                    usecase == "all" or
                    usecase in self.config["__modules__"][mod]["group"]
                ):
                    modlist.append(mod)

        # If we somehow got all the way through to here and still don't have any modules selected
        if not modlist:
            raise HTTPException(
                status_code=400,
                detail="Incorrect usage: no modules specified for scan."
            )

        # Add our mandatory storage module
        if "sfp__stor_db" not in modlist:
            modlist.append("sfp__stor_db")
        modlist.sort()

        # Delete the stdout module in case it crept in
        if "sfp__stor_stdout" in modlist:
            modlist.remove("sfp__stor_stdout")

        # Start running a new scan
        if targetType in ["HUMAN_NAME", "USERNAME", "BITCOIN_ADDRESS"]:
            scantarget = scantarget.replace('"', "")
        else:
            scantarget = scantarget.lower()

        # Start running a new scan
        scanId = SpiderFootHelpers.genScanInstanceId()
        try:
            p = mp.Process(
                target=startSpiderFootScanner,
                args=(
                    self.loggingQueue,
                    scanname,
                    scanId,
                    scantarget,
                    targetType,
                    modlist,
                    cfg,
                ),
            )
            p.daemon = True
            p.start()
        except Exception as e:
            self.log.error(f"[-] Scan [{scanId}] failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"[-] Scan [{scanId}] failed: {e}")

        # Wait until the scan has initialized
        # Check the database for the scan status results
        while dbh.scanInstanceGet(scanId) is None:
            self.log.info("Waiting for the scan to initialize...")
            time.sleep(1)

        return {"scan_id": scanId}
    
    # HTML page rendering methods
    async def render_index(self, request: Request) -> HTMLResponse:
        """Show scan list page.

        Returns:
            str: Scan list page HTML
        """
        templ = Template(
            filename="spiderfoot/templates/scanlist.tmpl", lookup=self.lookup
        )
        content = templ.render(
            pageid="SCANLIST", docroot=self.docroot, version=__version__
        )
        return HTMLResponse(content=content)
    
    async def render_scaninfo(self, request: Request, id: str) -> HTMLResponse:
        """Information about a selected scan.

        Args:
            id (str): scan id

        Returns:
            str: scan info page HTML
        """
        dbh = SpiderFootDb(self.config)
        res = dbh.scanInstanceGet(id)
        if res is None:
            return HTMLResponse(
                content=self.error_html("Scan ID not found.").body.decode('utf-8')
            )

        templ = Template(
            filename="spiderfoot/templates/scaninfo.tmpl",
            lookup=self.lookup,
            input_encoding="utf-8",
        )
        content = templ.render(
            id=id,
            name=html.escape(res[0]),
            status=res[5],
            docroot=self.docroot,
            version=__version__,
            pageid="SCANLIST",
        )
        return HTMLResponse(content=content)
    
    async def render_newscan(self, request: Request) -> HTMLResponse:
        """Configure a new scan.

        Returns:
            str: New scan page HTML
        """
        dbh = SpiderFootDb(self.config)
        types = dbh.eventTypes()
        templ = Template(
            filename="spiderfoot/templates/newscan.tmpl", lookup=self.lookup
        )
        content = templ.render(
            pageid="NEWSCAN",
            types=types,
            docroot=self.docroot,
            modules=self.config["__modules__"],
            scanname="",
            selectedmods="",
            scantarget="",
            version=__version__,
        )
        return HTMLResponse(content=content)
    
    async def render_clonescan(self, request: Request, id: str) -> HTMLResponse:
        """Clone an existing scan (pre-selected options in the newscan page).

        Args:
            id (str): scan ID to clone

        Returns:
            str: New scan page HTML pre-populated with options from cloned scan.
        """
        dbh = SpiderFootDb(self.config)
        types = dbh.eventTypes()
        info = dbh.scanInstanceGet(id)

        if not info:
            return HTMLResponse(
                content=self.error_html("Invalid scan ID.").body.decode('utf-8')
            )

        scanconfig = dbh.scanConfigGet(id)
        scanname = info[0]
        scantarget = info[1]

        if scanname == "" or scantarget == "" or len(scanconfig) == 0:
            return HTMLResponse(
                content=self.error_html("Something went wrong internally.").body.decode('utf-8')
            )

        targetType = SpiderFootHelpers.targetTypeFromString(scantarget)
        if targetType is None:
            # It must be a name, so wrap quotes around it
            scantarget = "&quot;" + scantarget + "&quot;"

        modlist = scanconfig["_modulesenabled"].split(",")

        templ = Template(
            filename="spiderfoot/templates/newscan.tmpl", lookup=self.lookup
        )
        content = templ.render(
            pageid="NEWSCAN",
            types=types,
            docroot=self.docroot,
            modules=self.config["__modules__"],
            selectedmods=modlist,
            scanname=str(scanname),
            scantarget=str(scantarget),
            version=__version__,
        )
        return HTMLResponse(content=content)
    
    async def render_opts(self, request: Request, updated: Optional[str] = None) -> HTMLResponse:
        """Show module and global settings page.

        Args:
            updated (str): scan options were updated successfully

        Returns:
            str: scan options page HTML
        """
        templ = Template(
            filename="spiderfoot/templates/opts.tmpl", lookup=self.lookup)
        self.token = random.SystemRandom().randint(0, 99999999)
        content = templ.render(
            opts=self.config,
            pageid="SETTINGS",
            token=self.token,
            version=__version__,
            updated=updated,
            docroot=self.docroot,
        )
        return HTMLResponse(content=content)
    
    # File export methods
    async def export_scanexportlogs(self, id: str, dialect: str = "excel") -> Response:
        """Get scan log

        Args:
            id (str): scan ID
            dialect (str): CSV dialect (default: excel)

        Returns:
            bytes: scan logs in CSV format
        """
        dbh = SpiderFootDb(self.config)

        try:
            data = dbh.scanLogs(id, None, None, True)
        except Exception:
            return HTMLResponse(
                content=self.error_html("Scan ID not found.").body.decode('utf-8')
            )

        if not data:
            return HTMLResponse(
                content=self.error_html("Scan ID not found.").body.decode('utf-8')
            )

        fileobj = StringIO()
        parser = csv.writer(fileobj, dialect=dialect)
        parser.writerow(["Date", "Component", "Type", "Event", "Event ID"])
        for row in data:
            parser.writerow(
                [
                    time.strftime("%Y-%m-%d %H:%M:%S",
                                  time.localtime(row[0] / 1000)),
                    str(row[1]),
                    str(row[2]),
                    str(row[3]),
                    row[4],
                ]
            )

        headers = {
            "Content-Disposition": f"attachment; filename=SpiderFoot-{id}.log.csv",
            "Content-Type": "application/csv",
            "Pragma": "no-cache"
        }
        
        return Response(
            content=fileobj.getvalue().encode("utf-8"), 
            headers=headers
        )
    
    async def export_scaneventresult(
        self,
        id: str,
        type: str,
        filetype: str = "csv",
        dialect: str = "excel",
    ) -> Response:
        """Get scan event result data in CSV or Excel format

        Args:
            id (str): scan ID
            type (str): event type
            filetype (str): type of file ("xlsx|excel" or "csv")
            dialect (str): CSV dialect (default: excel)

        Returns:
            Response: results in CSV or Excel format
        """
        dbh = SpiderFootDb(self.config)
        data = dbh.scanResultEvent(id, type)

        if filetype.lower() in ["xlsx", "excel"]:
            rows = []
            for row in data:
                if row[4] == "ROOT":
                    continue
                lastseen = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
                datafield = str(row[1]).replace(
                    "<SFURL>", "").replace("</SFURL>", "")
                rows.append(
                    [
                        lastseen,
                        str(row[4]),
                        str(row[3]),
                        str(row[2]),
                        row[13],
                        datafield,
                    ]
                )

            headers = {
                "Content-Disposition": "attachment; filename=SpiderFoot.xlsx",
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Pragma": "no-cache"
            }
            
            return Response(
                content=self.buildExcel(
                    rows,
                    ["Updated", "Type", "Module", "Source", "F/P", "Data"],
                    sheetNameIndex=1,
                ),
                headers=headers
            )

        if filetype.lower() == "csv":
            fileobj = StringIO()
            parser = csv.writer(fileobj, dialect=dialect)
            parser.writerow(
                ["Updated", "Type", "Module", "Source", "F/P", "Data"])
            for row in data:
                if row[4] == "ROOT":
                    continue
                lastseen = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
                datafield = str(row[1]).replace(
                    "<SFURL>", "").replace("</SFURL>", "")
                parser.writerow(
                    [
                        lastseen,
                        str(row[4]),
                        str(row[3]),
                        str(row[2]),
                        row[13],
                        datafield,
                    ]
                )

            headers = {
                "Content-Disposition": "attachment; filename=SpiderFoot.csv",
                "Content-Type": "application/csv",
                "Pragma": "no-cache"
            }
            
            return Response(
                content=fileobj.getvalue().encode("utf-8"),
                headers=headers
            )

        return HTMLResponse(
            content=self.error_html("Invalid export filetype.").body.decode('utf-8')
        )
    
    async def export_scanviz(self, id: str, gexf: str = "0") -> Response:
        """Export entities from scan results for visualising.

        Args:
            id (str): scan ID
            gexf (str): Format flag (0=JSON, 1=GEXF)

        Returns:
            Response: Visualization data
        """
        if not id:
            return JSONResponse(content=None)

        dbh = SpiderFootDb(self.config)
        data = dbh.scanResultEvent(id, filterFp=True)
        scan = dbh.scanInstanceGet(id)

        if not scan:
            return JSONResponse(content=None)

        scan_name = scan[0]
        root = scan[1]

        if gexf == "0":
            return JSONResponse(content=SpiderFootHelpers.buildGraphJson([root], data))

        if not scan_name:
            fname = "SpiderFoot.gexf"
        else:
            fname = scan_name + "SpiderFoot.gexf"

        headers = {
            "Content-Disposition": f"attachment; filename={fname}",
            "Content-Type": "application/gexf",
            "Pragma": "no-cache"
        }
        
        return Response(
            content=SpiderFootHelpers.buildGraphGexf([root], "SpiderFoot Export", data),
            headers=headers
        )
    
    async def export_scanvizmulti(self, ids: str, gexf: str = "1") -> Response:
        """Export entities results from multiple scans in GEXF format.

        Args:
            ids (str): comma-separated scan IDs
            gexf (str): Format flag (0=JSON, 1=GEXF)

        Returns:
            Response: Visualization data
        """
        dbh = SpiderFootDb(self.config)
        data = list()
        roots = list()
        scan_name = ""

        if not ids:
            return JSONResponse(content=None)

        for id in ids.split(","):
            scan = dbh.scanInstanceGet(id)
            if not scan:
                continue
            data = data + dbh.scanResultEvent(id, filterFp=True)
            roots.append(scan[1])
            scan_name = scan[0]

        if not data:
            return JSONResponse(content=None)

        if gexf == "0":
            # Not implemented yet
            return JSONResponse(content=None)

        if len(ids.split(",")) > 1 or scan_name == "":
            fname = "SpiderFoot.gexf"
        else:
            fname = scan_name + "-SpiderFoot.gexf"

        headers = {
            "Content-Disposition": f"attachment; filename={fname}",
            "Content-Type": "application/gexf",
            "Pragma": "no-cache"
        }
        
        return Response(
            content=SpiderFootHelpers.buildGraphGexf(roots, "SpiderFoot Export", data),
            headers=headers
        )
    
    # Settings management
    async def save_settings(
        self,
        allopts: str,
        token: str,
        configFile: Optional[UploadFile] = None,
    ) -> Union[RedirectResponse, HTMLResponse]:
        """Save settings, also used to completely reset them to default.

        Args:
            allopts: JSON string of all options
            token (str): CSRF token
            configFile: Optional uploaded config file

        Returns:
            Union[RedirectResponse, HTMLResponse]: Redirect to settings page or error
        """
        if str(token) != str(self.token):
            return HTMLResponse(
                content=self.error_html(f"Invalid token ({token})").body.decode('utf-8')
            )

        # configFile seems to get set even if a file isn't uploaded
        if configFile and configFile.file:
            try:
                contents = configFile.file.read()

                if isinstance(contents, bytes):
                    contents = contents.decode("utf-8")

                tmp = dict()
                for line in contents.split("\n"):
                    if "=" not in line:
                        continue

                    opt_array = line.strip().split("=")
                    if len(opt_array) == 1:
                        opt_array[1] = ""

                    tmp[opt_array[0]] = "=".join(opt_array[1:])

                allopts = json.dumps(tmp)
            except Exception as e:
                return HTMLResponse(
                    content=self.error_html(
                        f"Failed to parse input file. Was it generated from SpiderFoot? ({e})"
                    ).body.decode('utf-8')
                )

        # Reset config to default
        if allopts == "RESET":
            if self.reset_settings():
                return RedirectResponse(f"{self.docroot}/opts?updated=1", status_code=303)
            return HTMLResponse(
                content=self.error_html("Failed to reset settings").body.decode('utf-8')
            )

        # Save settings
        try:
            dbh = SpiderFootDb(self.config)
            useropts = json.loads(allopts)
            cleanopts = dict()
            for opt in list(useropts.keys()):
                cleanopts[opt] = self.cleanUserInput([useropts[opt]])[0]

            currentopts = deepcopy(self.config)

            # Make a new config where the user options override
            # the current system config.
            sf = SpiderFoot(self.config)
            self.config = sf.configUnserialize(cleanopts, currentopts)
            dbh.configSet(sf.configSerialize(self.config))
        except Exception as e:
            return HTMLResponse(
                content=self.error_html(f"Processing one or more of your inputs failed: {e}").body.decode('utf-8')
            )

        return RedirectResponse(f"{self.docroot}/opts?updated=1", status_code=303)
    
    def reset_settings(self) -> bool:
        """Reset settings to default.

        Returns:
            bool: success
        """
        try:
            dbh = SpiderFootDb(self.config)
            dbh.configClear()  # Clear it in the DB
            self.config = deepcopy(self.defaultConfig)  # Clear in memory
        except Exception:
            return False

        return True

    def error_html(self, message: str) -> HTMLResponse:
        """Show generic error page with error message.

        Args:
            message (str): error message

        Returns:
            HTMLResponse: HTML error response
        """
        templ = Template(
            filename="spiderfoot/templates/error.tmpl", lookup=self.lookup)
        return HTMLResponse(
            content=templ.render(
                message=message, 
                docroot=self.docroot, 
                version=__version__
            )
        )

# Global instance initialization
sf_api_instance = None

def initialize_sf_api(web_config: dict, config: dict):
    """Initialize the global SpiderFootFastApi instance
    
    Args:
        web_config (dict): Web interface configuration
        config (dict): SpiderFoot configuration
    """
    global sf_api_instance
    sf_api_instance = SpiderFootFastApi(web_config, config)
    
    # Set up utilities
    setup_logging(app, log_level=logging.DEBUG if config.get("_debug") else logging.INFO)
    setup_error_handlers(app, html_error_template=sf_api_instance.error_html)
    setup_cors(
        app, 
        allowed_origins=web_config.get("cors", ["http://127.0.0.1", "http://localhost"])
    )
    
    return sf_api_instance

def get_sf_api():
    """FastAPI dependency to get the SpiderFootFastApi instance
    
    Returns:
        SpiderFootFastApi: The global SpiderFootFastApi instance
    """
    if sf_api_instance is None:
        raise HTTPException(status_code=500, detail="SpiderFoot API not initialized")
    return sf_api_instance

# API Key dependency
def get_api_auth(api_key: str = Security(APIKeyHeader(name="X-API-Key"))):
    """FastAPI dependency to check API key authentication
    
    Args:
        api_key (str): API key from header
        
    Returns:
        bool: True if authentication successful
    """
    global api_key_auth
    if api_key_auth:
        return api_key_auth.verify_api_key(api_key)
    return True

# FastAPI route definitions
@app.get("/eventtypes", response_model=List[List[str]])
async def eventtypes(
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """List all event types.

    Returns:
        list: list of event types
    """
    return await sf_api.get_eventtypes()

@app.get("/modules", response_model=List[Dict[str, str]])
async def modules(
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """List all modules.

    Returns:
        list: list of modules
    """
    return await sf_api.get_modules()

@app.get("/correlationrules", response_model=List[Dict[str, Any]])
async def correlationrules(
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """List all correlation rules.

    Returns:
        list: list of correlation rules
    """
    return await sf_api.get_correlationrules()

@app.get("/ping", response_model=List[str])
async def ping(
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Test connectivity to this server.

    Returns:
        List[str]: Success status and version
    """
    return await sf_api.do_ping()

@app.get("/query")
async def query(
    query: str, 
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Run SQL queries against the database.
    
    Args:
        query (str): SQL query string
    
    Returns:
        Union[List[Dict], Dict]: Query results or error message
    """
    return await sf_api.do_query(query)

@app.get("/search")
async def search(
    id: Optional[str] = None, 
    eventType: Optional[str] = None,
    value: Optional[str] = None,
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Search scans.
    
    Args:
        id (str): Filter by scan ID
        eventType (str): Filter by event type
        value (str): Filter by value
    
    Returns:
        List[List]: Search results
    """
    return await sf_api.search_data(id, eventType, value)

@app.get("/scanhistory")
async def scanhistory(
    id: str, 
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Get scan history.
    
    Args:
        id (str): Scan ID
    
    Returns:
        List: Scan history data
    """
    return await sf_api.get_scanhistory(id)

@app.get("/scanlist", response_model=List[List[Any]])
async def scanlist(
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Get a list of all scans.
    
    Returns:
        List[List]: List of scans with details
    """
    return await sf_api.get_scanlist()

@app.get("/scanstatus")
async def scanstatus(
    id: str,
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Get scan status.
    
    Args:
        id (str): Scan ID
    
    Returns:
        List: Scan status information
    """
    return await sf_api.get_scanstatus(id)

@app.delete("/scandelete")
async def scandelete(
    id: str,
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Delete one or more scans.
    
    Args:
        id (str): Comma-separated list of scan IDs
    
    Returns:
        Dict: Status message
    """
    return await sf_api.delete_scan(id)

@app.post("/stopscan")
async def stopscan(
    id: str,
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Stop one or more running scans.
    
    Args:
        id (str): Comma-separated list of scan IDs
    
    Returns:
        Dict: Status message
    """
    return await sf_api.stop_scan(id)

@app.post("/startscan")
async def startscan(
    scanname: str,
    scantarget: str,
    modulelist: Optional[str] = None,
    typelist: Optional[str] = None,
    usecase: Optional[str] = None,
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Start a new scan.

    Args:
        scanname (str): Scan name
        scantarget (str): Target for scanning
        modulelist (str, optional): Comma-separated list of modules
        typelist (str, optional): Comma-separated list of types
        usecase (str, optional): Use case (all, passive, investigate, footprint)
    
    Returns:
        Dict: Status message with scan ID
    """
    return await sf_api.start_scan(scanname, scantarget, modulelist, typelist, usecase)

@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request, 
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Show scan list page.

    Returns:
        HTMLResponse: Scan list page HTML
    """
    return await sf_api.render_index(request)

@app.get("/scaninfo", response_class=HTMLResponse)
async def scaninfo(
    request: Request, 
    id: str, 
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Information about a selected scan.

    Args:
        id (str): scan id

    Returns:
        HTMLResponse: scan info page HTML
    """
    return await sf_api.render_scaninfo(request, id)

@app.get("/newscan", response_class=HTMLResponse)
async def newscan(
    request: Request, 
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Configure a new scan.

    Returns:
        HTMLResponse: New scan page HTML
    """
    return await sf_api.render_newscan(request)

@app.get("/clonescan", response_class=HTMLResponse)
async def clonescan(
    request: Request, 
    id: str, 
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Clone an existing scan (pre-selected options in the newscan page).

    Args:
        id (str): scan ID to clone

    Returns:
        HTMLResponse: New scan page HTML pre-populated with options from cloned scan.
    """
    return await sf_api.render_clonescan(request, id)

@app.get("/opts", response_class=HTMLResponse)
async def opts(
    request: Request, 
    updated: Optional[str] = None, 
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Show module and global settings page.

    Args:
        updated (str): scan options were updated successfully

    Returns:
        HTMLResponse: scan options page HTML
    """
    return await sf_api.render_opts(request, updated)

@app.get("/scanexportlogs")
async def scanexportlogs(
    id: str, 
    dialect: str = "excel", 
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Get scan log

    Args:
        id (str): scan ID
        dialect (str): CSV dialect (default: excel)

    Returns:
        Response: scan logs in CSV format
    """
    return await sf_api.export_scanexportlogs(id, dialect)

@app.get("/scaneventresultexport")
async def scaneventresultexport(
    id: str,
    type: str,
    filetype: str = "csv",
    dialect: str = "excel",
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Get scan event result data in CSV or Excel format

    Args:
        id (str): scan ID
        type (str): event type
        filetype (str): type of file ("xlsx|excel" or "csv")
        dialect (str): CSV dialect (default: excel)

    Returns:
        Response: results in CSV or Excel format
    """
    return await sf_api.export_scaneventresult(id, type, filetype, dialect)

@app.get("/scanviz")
async def scanviz(
    id: str, 
    gexf: str = "0", 
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Export entities from scan results for visualising.

    Args:
        id (str): scan ID
        gexf (str): Format flag (0=JSON, 1=GEXF)

    Returns:
        Response: Visualization data
    """
    return await sf_api.export_scanviz(id, gexf)

@app.get("/scanvizmulti")
async def scanvizmulti(
    ids: str, 
    gexf: str = "1", 
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Export entities results from multiple scans in GEXF format.

    Args:
        ids (str): comma-separated scan IDs
        gexf (str): Format flag (0=JSON, 1=GEXF)

    Returns:
        Response: Visualization data
    """
    return await sf_api.export_scanvizmulti(ids, gexf)

@app.post("/savesettings")
async def savesettings(
    request: Request,
    allopts: str = Form(...),
    token: str = Form(...),
    configFile: Optional[UploadFile] = None,
    sf_api: SpiderFootFastApi = Depends(get_sf_api),
    _: bool = Depends(get_api_auth)
):
    """Save settings, also used to completely reset them to default.

    Args:
        allopts: JSON string of all options
        token (str): CSRF token
        configFile: Optional uploaded config file

    Returns:
        Union[RedirectResponse, HTMLResponse]: Redirect to settings page or error
    """
    return await sf_api.save_settings(allopts, token, configFile)

# Add a main function to set up the app with SpiderFoot config
def setup_app(web_config: dict, config: dict):
    """Set up the FastAPI application with SpiderFoot config
    
    Args:
        web_config (dict): Web interface configuration
        config (dict): SpiderFoot configuration
    """
    initialize_sf_api(web_config, config)
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="spiderfoot/static"), name="static")
    
    # Add application startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        logger = get_logger("spiderfoot.app")
        logger.info(f"Starting SpiderFoot FastAPI server version {__version__}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger = get_logger("spiderfoot.app")
        logger.info("Shutting down SpiderFoot FastAPI server")
    
    return app
