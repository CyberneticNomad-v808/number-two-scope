# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         Modular SpiderFoot Database Module
# Purpose:      Common functions for working with the database back-end.
#
# Author:      Agostino Panico @poppopjmp
#
# Created:     30/06/2025
# Copyright:   (c) Agostino Panico 2025
# Licence:     MIT
# -------------------------------------------------------------------------------
"""
Event storage, retrieval, search, and event tree navigation for SpiderFootDb.
"""
from threading import RLock
import time
import psycopg2
from ..event import SpiderFootEvent
from .db_utils import get_placeholder, is_transient_error

class EventManager:
    def __init__(self, dbh, conn, dbhLock, db_type):
        self.dbh = dbh
        self.conn = conn
        self.dbhLock = dbhLock
        self.db_type = db_type

    def _log_db_error(self, msg, exc):
        print(f"[DB ERROR] {msg}: {exc}")

    def _is_transient_error(self, exc):
        return is_transient_error(exc)

    def scanLogEvents(self, batch: list) -> bool:
        inserts = []
        for item in batch:
            if len(item) != 5:
                continue
            instanceId, classification, message, component, logTime = item
            if not isinstance(instanceId, str):
                continue
            if not isinstance(classification, str):
                continue
            if not isinstance(message, str):
                continue
            if not component:
                component = "SpiderFoot"
            if isinstance(logTime, float):
                logTime = int(logTime * 1000)
            elif isinstance(logTime, int) and logTime < 1000000000000:
                logTime = logTime * 1000
            inserts.append(
                (instanceId, logTime, component, classification, message)
            )
        if not inserts:
            return True
        if self.db_type == 'sqlite':
            qry = "INSERT INTO tbl_scan_log \
                (scan_instance_id, generated, component, type, message) \
                VALUES (?, ?, ?, ?, ?)"
        else:
            qry = "INSERT INTO tbl_scan_log \
                (scan_instance_id, generated, component, type, message) \
                VALUES (%s, %s, %s, %s, %s)"
        with self.dbhLock:
            for attempt in range(3):
                try:
                    if not self.conn:
                        return False
                    self.dbh.executemany(qry, inserts)
                    self.conn.commit()
                    return True
                except (psycopg2.Error) as e:
                    self._log_db_error("Error in scanLogEvents", e)
                    if self._is_transient_error(e) and attempt < 2:
                        time.sleep(0.2 * (attempt + 1))
                        continue
                    try:
                        self.conn.rollback()
                    except Exception as e2:
                        self._log_db_error(
                            "Rollback failed in scanLogEvents", e2
                        )
                    return False
                except Exception as e:
                    self._log_db_error("Unknown error in scanLogEvents", e)
                    return False

    def scanLogEvent(
        self,
        instanceId: str,
        classification: str,
        message: str,
        component: str = None
    ) -> None:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        if not isinstance(classification, str):
            raise TypeError(
                f"classification is {type(classification)}; expected str()"
            )
        if not isinstance(message, str):
            raise TypeError(f"message is {type(message)}; expected str()")
        if not component:
            component = "SpiderFoot"
        ph = get_placeholder(self.db_type)
        qry = (
            f"INSERT INTO tbl_scan_log "
            f"(scan_instance_id, generated, component, type, message) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph})"
        )
        with self.dbhLock:
            for attempt in range(3):
                try:
                    self.dbh.execute(qry, (
                        instanceId, time.time() * 1000, component,
                        classification, message
                    ))
                    self.conn.commit()
                    return
                except (psycopg2.Error) as e:
                    self._log_db_error("Error in scanLogEvent", e)
                    if self._is_transient_error(e) and attempt < 2:
                        time.sleep(0.2 * (attempt + 1))
                        continue
                    raise IOError("Error in scanLogEvent") from e

    def scanLogs(
        self,
        instanceId: str,
        limit: int = None,
        fromRowId: int = 0,
        reverse: bool = False
    ) -> list:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        ph = get_placeholder(self.db_type)
        qry = (
            f"SELECT generated AS generated, component, type, message, id AS rowid "
            f"FROM tbl_scan_log WHERE scan_instance_id = {ph}"
        )
        if fromRowId:
            qry += f" and id > {ph}"
        qry += " ORDER BY generated "
        if reverse:
            qry += "ASC"
        else:
            qry += "DESC"
        qvars = [instanceId]
        if fromRowId:
            qvars.append(str(fromRowId))
        if limit is not None:
            qry += f" LIMIT {ph}"
            qvars.append(str(limit))
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when fetching scan logs"
                ) from e

    def scanErrors(self, instanceId: str, limit: int = 0) -> list:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        if not isinstance(limit, int):
            raise TypeError(f"limit is {type(limit)}; expected int()")
        ph = get_placeholder(self.db_type)
        qry = (
            f"SELECT generated AS generated, component, message "
            f"FROM tbl_scan_log WHERE scan_instance_id = {ph} "
            f"AND type = 'ERROR' ORDER BY generated DESC"
        )
        qvars = [instanceId]
        if limit:
            qry += f" LIMIT {ph}"
            qvars.append(str(limit))
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when fetching scan errors"
                ) from e

    def scanResultEvent(
        self,
        instanceId: str,
        eventType: str = 'ALL',
        srcModule: str = None,
        data: list = None,
        sourceId: list = None,
        correlationId: str = None,
        filterFp: bool = False
    ) -> list:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        if not isinstance(eventType, str) and not isinstance(eventType, list):
            raise TypeError(
                f"eventType is {type(eventType)}; expected str() or list()"
            )
        # Fix: Use LEFT JOIN for parent event, and allow source_event_hash
        # = 'ROOT' to include root events
        # Legacy tuple order: generated, data, module, hash, type,
        # source_event_hash, confidence, visibility, risk
        ph = get_placeholder(self.db_type)
        qry = (
            f"SELECT ROUND(c.generated) AS generated, c.data, c.module, "
            f"c.hash, c.type, c.source_event_hash, c.confidence, c.visibility, "
            f"c.risk FROM tbl_scan_results c "
            f"WHERE c.scan_instance_id = {ph} "
        )
        qvars = [instanceId]
        if eventType != "ALL":
            if isinstance(eventType, list):
                qry += (
                    " AND c.type in (" +
                    ','.join([ph] * len(eventType)) + ")"
                )
                qvars.extend(eventType)
            else:
                qry += f" AND c.type = {ph}"
                qvars.append(eventType)
        if filterFp:
            qry += " AND c.false_positive <> 1"
        if srcModule:
            if isinstance(srcModule, list):
                qry += (
                    " AND c.module in (" +
                    ','.join([ph] * len(srcModule)) + ")"
                )
                qvars.extend(srcModule)
            else:
                qry += f" AND c.module = {ph}"
                qvars.append(srcModule)
        if data:
            if isinstance(data, list):
                qry += (
                    " AND c.data in (" +
                    ','.join([ph] * len(data)) + ")"
                )
                qvars.extend(data)
            else:
                qry += f" AND c.data = {ph}"
                qvars.append(data)
        if sourceId:
            if isinstance(sourceId, list):
                qry += (
                    " AND c.source_event_hash in (" +
                    ','.join([ph] * len(sourceId)) + ")"
                )
                qvars.extend(sourceId)
            else:
                qry += f" AND c.source_event_hash = {ph}"
                qvars.append(sourceId)
        # Special case: include events where c.source_event_hash = 'ROOT'
        qry += " AND (c.source_event_hash = 'ROOT' OR "
        qry += "c.source_event_hash != 'ROOT')"
        qry += " ORDER BY c.data"
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when fetching result events"
                ) from e

    def scanResultEventForGraph(self, instanceId: str, filterFp: bool = False) -> list:
        """Return scan result rows shaped for graph building
        (SpiderFootHelpers.buildGraphData/buildGraphJson/buildGraphGexf).

        Each row is (data, parent_data, type, event_type_category, hash):
        parent_data is the source event's own data value (resolved via a
        self-join on source_event_hash), not just the hash reference that
        scanResultEvent() returns -- buildGraphData needs the actual parent
        label to draw an edge. 'ROOT' parents (or missing source events, e.g.
        due to false-positive filtering) fall back to the literal 'ROOT'
        label, which callers already special-case and skip.
        """
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        ph = get_placeholder(self.db_type)
        qry = (
            f"SELECT c.data, COALESCE(p.data, 'ROOT') AS parent_data, "
            f"c.type, e.event_type, c.hash "
            f"FROM tbl_scan_results c "
            f"JOIN tbl_event_types e ON e.event = c.type "
            f"LEFT JOIN tbl_scan_results p ON p.hash = c.source_event_hash "
            f"AND p.scan_instance_id = c.scan_instance_id "
            f"WHERE c.scan_instance_id = {ph}"
        )
        if filterFp:
            qry += " AND c.false_positive <> 1"
        qvars = [instanceId]
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when fetching graph data"
                ) from e

    def scanResultEventUnique(
        self,
        instanceId: str,
        eventType: str = 'ALL',
        filterFp: bool = False
    ) -> list:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        if not isinstance(eventType, str):
            raise TypeError(f"eventType is {type(eventType)}; expected str()")
        ph = get_placeholder(self.db_type)
        qry = (
            f"SELECT DISTINCT data, type, COUNT(*) "
            f"FROM tbl_scan_results WHERE scan_instance_id = {ph}"
        )
        qvars = [instanceId]
        if eventType != "ALL":
            qry += f" AND type = {ph}"
            qvars.append(eventType)
        if filterFp:
            qry += " AND false_positive <> 1"
        qry += " GROUP BY type, data ORDER BY COUNT(*)"
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when fetching unique result events"
                ) from e

    def scanResultSummary(self, instanceId: str, by: str = "type") -> list:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        if not isinstance(by, str):
            raise TypeError(f"by is {type(by)}; expected str()")
        if by not in ["type", "module", "entity"]:
            raise ValueError(f"Invalid filter by value: {by}")
        ph = get_placeholder(self.db_type)
        if by == "type":
            qry = (
                f"SELECT r.type, e.event_descr, "
                f"MAX(ROUND(generated)) AS last_in, count(*) AS total, "
                f"count(DISTINCT r.data) as utotal "
                f"FROM tbl_scan_results r, tbl_event_types e "
                f"WHERE e.event = r.type AND r.scan_instance_id = {ph} "
                f"GROUP BY r.type, e.event_descr ORDER BY e.event_descr"
            )
        if by == "module":
            qry = (
                f"SELECT r.module, '', MAX(ROUND(generated)) AS last_in, "
                f"count(*) AS total, count(DISTINCT r.data) as utotal "
                f"FROM tbl_scan_results r, tbl_event_types e "
                f"WHERE e.event = r.type AND r.scan_instance_id = {ph} "
                f"GROUP BY r.module ORDER BY r.module DESC"
            )
        if by == "entity":
            qry = (
                f"SELECT r.data, e.event_descr, "
                f"MAX(ROUND(generated)) AS last_in, count(*) AS total, "
                f"count(DISTINCT r.data) as utotal "
                f"FROM tbl_scan_results r, tbl_event_types e "
                f"WHERE e.event = r.type AND r.scan_instance_id = {ph} "
                f"AND e.event_type in ('ENTITY') GROUP BY r.data, "
                f"e.event_descr ORDER BY total DESC limit 50"
            )
        qvars = [instanceId]
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when fetching result summary"
                ) from e

    def scanResultHistory(self, instanceId: str) -> list:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        ph = get_placeholder(self.db_type)
        qry = (
            f"SELECT TO_CHAR(TO_TIMESTAMP(generated), 'HH24:MI D') AS hourmin, "
            f"type, COUNT(*) FROM tbl_scan_results "
            f"WHERE scan_instance_id = {ph} "
            f"GROUP BY TO_CHAR(TO_TIMESTAMP(generated), 'HH24:MI D'), type"
        )
        qvars = [instanceId]
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (psycopg2.Error) as e:
                raise IOError(
                    f"SQL error encountered when fetching history "
                    f"for scan {instanceId}"
                ) from e

    def scanResultsUpdateFP(
        self,
        instanceId: str,
        resultHashes: list,
        fpFlag: int
    ) -> bool:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        if not isinstance(resultHashes, list):
            raise TypeError(
                f"resultHashes is {type(resultHashes)}; expected list()"
            )
        ph = get_placeholder(self.db_type)
        with self.dbhLock:
            for resultHash in resultHashes:
                qry = (
                    f"UPDATE tbl_scan_results SET false_positive = {ph} "
                    f"WHERE scan_instance_id = {ph} AND hash = {ph}"
                )
                qvars = [fpFlag, instanceId, resultHash]
                try:
                    self.dbh.execute(qry, qvars)
                except (psycopg2.Error) as e:
                    raise IOError(
                        "SQL error encountered when updating false-positive"
                    ) from e
            try:
                self.conn.commit()
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when updating false-positive"
                ) from e
        return True

    def scanEventStore(
        self,
        instanceId: str,
        sfEvent,
        truncateSize: int = 0
    ) -> None:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        if not instanceId:
            raise ValueError("instanceId is empty")
        if not isinstance(sfEvent, SpiderFootEvent):
            raise TypeError(
                f"sfEvent is {type(sfEvent)}; expected SpiderFootEvent()"
            )
        if not isinstance(sfEvent.generated, (int, float)):
            raise TypeError(
                f"sfEvent.generated is {type(sfEvent.generated)}; "
                f"expected int() or float()"
            )
        if not sfEvent.generated:
            raise ValueError("sfEvent.generated is empty")
        if not isinstance(sfEvent.eventType, str):
            raise TypeError(
                f"sfEvent.eventType is {type(sfEvent.eventType,)}; "
                f"expected str()"
            )
        if not sfEvent.eventType:
            raise ValueError("sfEvent.eventType is empty")
        if not isinstance(sfEvent.data, str):
            raise TypeError(f"sfEvent.data is {type(sfEvent.data)}; "
                           f"expected str()")
        if not sfEvent.data:
            raise ValueError("sfEvent.data is empty")
        if not isinstance(sfEvent.module, str):
            raise TypeError(f"sfEvent.module is {type(sfEvent.module)}; "
                           f"expected str()")
        if not sfEvent.module and sfEvent.eventType != "ROOT":
            raise ValueError("sfEvent.module is empty")
        if not isinstance(sfEvent.confidence, int):
            raise TypeError(
                f"sfEvent.confidence is {type(sfEvent.confidence)}; "
                f"expected int()"
            )
        if not 0 <= sfEvent.confidence <= 100:
            raise ValueError(
                f"sfEvent.confidence value is {type(sfEvent.confidence)}; "
                f"expected 0 - 100"
            )
        if not isinstance(sfEvent.visibility, int):
            raise TypeError(
                f"sfEvent.visibility is {type(sfEvent.visibility)}; "
                f"expected int()"
            )
        if not 0 <= sfEvent.visibility <= 100:
            raise ValueError(
                f"sfEvent.visibility value is {type(sfEvent.visibility)}; "
                f"expected 0 - 100"
            )
        if not isinstance(sfEvent.risk, int):
            raise TypeError(
                f"sfEvent.risk is {type(sfEvent.risk)}; "
                f"expected int()"
            )
        if not 0 <= sfEvent.risk <= 100:
            raise ValueError(
                f"sfEvent.risk value is {type(sfEvent.risk)}; "
                f"expected 0 - 100"
            )
        # Note: no separate check on sfEvent.sourceEvent itself here (there
        # used to be one requiring it to be a real SpiderFootEvent for any
        # non-ROOT eventType). SpiderFootEvent's own sourceEvent setter
        # explicitly documents and supports sourceEvent=None for "testing
        # or special cases", defaulting sourceEventHash to "ROOT" -- a
        # legitimate, storable value used by e.g. sfp_advanced_correlation's
        # scanFinished()-emitted aggregate events, which have no single
        # parent event. That check rejected exactly this case with a
        # TypeError whose own message didn't even match what it was
        # checking ("expected str()" while testing isinstance(...,
        # SpiderFootEvent)). What actually needs validating -- and gets
        # stored -- is sourceEventHash, checked just below.
        if not isinstance(sfEvent.sourceEventHash, str):
            raise TypeError(
                f"sfEvent.sourceEventHash is {type(sfEvent.sourceEventHash)}; "
                f"expected str()"
            )
        if not sfEvent.sourceEventHash:
            raise ValueError("sfEvent.sourceEventHash is empty")
        storeData = sfEvent.data
        if isinstance(truncateSize, int) and truncateSize > 0:
            storeData = storeData[0:truncateSize]
        # generated is stored as whole seconds since epoch -- every reader
        # of this column (ROUND(c.generated), TO_TIMESTAMP(generated),
        # time.localtime() in search results) treats it as seconds, not ms.
        generated_seconds = int(sfEvent.generated)
        ph = get_placeholder(self.db_type)
        qry = (
            f"INSERT INTO tbl_scan_results "
            f"(scan_instance_id, hash, type, generated, confidence, "
            f"visibility, risk, module, data, source_event_hash) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, "
            f"{ph}, {ph})"
        )
        qvals = [
            instanceId, sfEvent.hash, sfEvent.eventType, generated_seconds,
            sfEvent.confidence, sfEvent.visibility, sfEvent.risk,
            sfEvent.module, storeData, sfEvent.sourceEventHash
        ]
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvals)
                self.conn.commit()
            except (psycopg2.Error) as e:
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                raise IOError(
                    f"SQL error encountered when storing event data: {e}"
                ) from e

    def scanElementSourcesDirect(
        self,
        instanceId: str,
        elementIdList: list
    ) -> list:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        if not isinstance(elementIdList, list):
            raise TypeError(
                f"elementIdList is {type(elementIdList)}; expected list()"
            )
        hashIds = []
        for hashId in elementIdList:
            if not hashId:
                continue
            if not hashId.isalnum():
                continue
            hashIds.append(hashId)
        ph = get_placeholder(self.db_type)
        qry = (
            f"SELECT ROUND(c.generated) AS generated, c.data, "
            f"s.data as source_data, c.module, c.type, c.confidence, "
            f"c.visibility, c.risk, c.hash, c.source_event_hash, "
            f"t.event_descr, t.event_type, s.scan_instance_id, "
            f"c.false_positive as fp, s.false_positive as parent_fp, "
            f"s.type, s.module, st.event_type as source_entity_type "
            f"FROM tbl_scan_results c, tbl_scan_results s, tbl_event_types t, "
            f"tbl_event_types st WHERE c.scan_instance_id = {ph} AND "
            f"c.source_event_hash = s.hash AND "
            f"s.scan_instance_id = c.scan_instance_id AND "
            f"st.event = s.type AND t.event = c.type AND c.hash in ('" +
            "','".join(hashIds) + "')"
        )
        qvars = [instanceId]
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when getting source element IDs"
                ) from e

    def scanElementChildrenDirect(
        self,
        instanceId: str,
        elementIdList: list
    ) -> list:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        if not isinstance(elementIdList, list):
            raise TypeError(
                f"elementIdList is {type(elementIdList)}; expected list()"
            )
        hashIds = []
        for hashId in elementIdList:
            if not hashId:
                continue
            if not hashId.isalnum():
                continue
            hashIds.append(hashId)
        ph = get_placeholder(self.db_type)
        qry = (
            f"SELECT ROUND(c.generated) AS generated, c.data, "
            f"s.data as source_data, c.module, c.type, c.confidence, "
            f"c.visibility, c.risk, c.hash, c.source_event_hash, "
            f"t.event_descr, t.event_type, s.scan_instance_id, "
            f"c.false_positive as fp, s.false_positive as parent_fp "
            f"FROM tbl_scan_results c, tbl_scan_results s, tbl_event_types t "
            f"WHERE c.scan_instance_id = {ph} AND "
            f"c.source_event_hash = s.hash AND "
            f"s.scan_instance_id = c.scan_instance_id AND "
            f"t.event = c.type AND s.hash in ('" +
            "','".join(hashIds) + "')"
        )
        qvars = [instanceId]
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when getting child element IDs"
                ) from e

    def scanElementSourcesAll(
        self,
        instanceId: str,
        childData: list
    ) -> list:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        if not isinstance(childData, list):
            raise TypeError(
                f"childData is {type(childData)}; expected list()"
            )
        if not childData:
            raise ValueError("childData is empty")
        keepGoing = True
        nextIds = list()
        datamap = dict()
        pc = dict()
        for row in childData:
            parentId = row[9]
            childId = row[8]
            datamap[childId] = row
            if parentId in pc:
                if childId not in pc[parentId]:
                    pc[parentId].append(childId)
            else:
                pc[parentId] = [childId]
            if parentId not in nextIds:
                nextIds.append(parentId)
        while keepGoing:
            parentSet = self.scanElementSourcesDirect(instanceId, nextIds)
            nextIds = list()
            keepGoing = False
            for row in parentSet:
                parentId = row[9]
                childId = row[8]
                datamap[childId] = row
                if parentId in pc:
                    if childId not in pc[parentId]:
                        pc[parentId].append(childId)
                else:
                    pc[parentId] = [childId]
                if parentId not in nextIds:
                    nextIds.append(parentId)
                if parentId != "ROOT":
                    keepGoing = True
        datamap[parentId] = row
        return [datamap, pc]

    def scanElementChildrenAll(
        self,
        instanceId: str,
        parentIds: list
    ) -> list:
        if not isinstance(instanceId, str):
            raise TypeError(f"instanceId is {type(instanceId)}; expected str()")
        if not isinstance(parentIds, list):
            raise TypeError(
                f"parentIds is {type(parentIds)}; expected list()"
            )
        datamap = list()
        keepGoing = True
        nextIds = list()
        nextSet = self.scanElementChildrenDirect(instanceId, parentIds)
        for row in nextSet:
            datamap.append(row[8])
        for row in nextSet:
            if row[8] not in nextIds:
                nextIds.append(row[8])
        while keepGoing:
            nextSet = self.scanElementChildrenDirect(instanceId, nextIds)
            if nextSet is None or len(nextSet) == 0:
                keepGoing = False
                break
            for row in nextSet:
                datamap.append(row[8])
                nextIds = list()
                nextIds.append(row[8])
        return datamap

    def get_sources(self, scan_id: str, event_hash: str) -> list:
        ph = get_placeholder(self.db_type)
        qry = f"""
            SELECT s.hash, s.type, s.data, s.module, s.generated,
                   s.source_event_hash
            FROM tbl_scan_results c
            JOIN tbl_scan_results s
              ON c.source_event_hash = s.hash
            WHERE c.scan_instance_id = {ph}
              AND c.hash = {ph}
              AND c.source_event_hash != 'ROOT'
        """
        qvars = [scan_id, event_hash]
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                rows = self.dbh.fetchall()
                sources = []
                for row in rows:
                    sources.append({
                        'hash': row[0],
                        'type': row[1],
                        'data': row[2],
                        'module': row[3],
                        'generated': row[4],
                        'source_event_hash': row[5]
                    })
                return sources
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when fetching event sources"
                ) from e

    def get_entities(self, scan_id: str, event_hash: str) -> list:
        ph = get_placeholder(self.db_type)
        qry = f"""
            SELECT c.hash, c.type, c.data, c.module, c.generated,
                   c.source_event_hash
            FROM tbl_scan_results c
            WHERE c.scan_instance_id = {ph}
              AND c.source_event_hash = {ph}
              AND c.type IN (
                SELECT event FROM tbl_event_types
                WHERE event_type = 'ENTITY'
              )
        """
        qvars = [scan_id, event_hash]
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                rows = self.dbh.fetchall()
                entities = []
                for row in rows:
                    entities.append({
                        'hash': row[0],
                        'type': row[1],
                        'data': row[2],
                        'module': row[3],
                        'generated': row[4],
                        'source_event_hash': row[5]
                    })
                return entities
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when fetching entity events"
                ) from e

    def search(self, criteria: dict, filterFp: bool = False) -> list:
        """
        Search for events in the scan results matching the given criteria.

        Supported keys: scan_id (required), type, data, module, value,
        regex, start_date, end_date.

        Returns rows shaped (generated, data, source_data, module, type,
        confidence, visibility, risk, hash, source_event_hash, event_descr,
        event_type, scan_instance_id, false_positive, parent_false_positive)
        -- restored from this project's own pre-refactor db.py.backup, which
        every caller of this method (webui searchBase() in both
        webui/helpers.py and webui/routes.py, and the FastAPI search-export
        endpoint) still indexes into. The previous 9-column version silently
        broke all three: they either raised IndexError past column 8 (caught
        by a bare except and returned as empty results) or read the wrong
        field entirely.
        """
        if not isinstance(criteria, dict):
            raise TypeError("criteria must be a dict")
        if not criteria:
            raise ValueError("criteria must not be empty")
        scan_id = criteria.get('scan_id')
        if not scan_id or not isinstance(scan_id, str):
            raise ValueError(
                "criteria must include a valid 'scan_id' string"
            )
        ph = get_placeholder(self.db_type)
        qry = (
            f"SELECT ROUND(c.generated) AS generated, c.data, "
            f"COALESCE(s.data, 'ROOT') AS source_data, c.module, c.type, "
            f"c.confidence, c.visibility, c.risk, c.hash, "
            f"c.source_event_hash, t.event_descr, t.event_type, "
            f"c.scan_instance_id, c.false_positive AS fp, "
            f"COALESCE(s.false_positive, 0) AS parent_fp "
            f"FROM tbl_scan_results c "
            f"JOIN tbl_event_types t ON t.event = c.type "
            f"LEFT JOIN tbl_scan_results s ON s.hash = c.source_event_hash "
            f"AND s.scan_instance_id = c.scan_instance_id "
            f"WHERE c.scan_instance_id = {ph}"
        )
        qvars = [scan_id]
        if 'type' in criteria and criteria['type']:
            qry += f" AND c.type = {ph}"
            qvars.append(criteria['type'])
        if 'data' in criteria and criteria['data']:
            qry += f" AND c.data = {ph}"
            qvars.append(criteria['data'])
        if 'module' in criteria and criteria['module']:
            qry += f" AND c.module = {ph}"
            qvars.append(criteria['module'])
        if 'value' in criteria and criteria['value']:
            qry += f" AND (c.data LIKE {ph} OR s.data LIKE {ph})"
            qvars.append(criteria['value'])
            qvars.append(criteria['value'])
        if 'regex' in criteria and criteria['regex']:
            qry += f" AND (c.data ~ {ph} OR s.data ~ {ph})"
            qvars.append(criteria['regex'])
            qvars.append(criteria['regex'])
        if 'start_date' in criteria and criteria['start_date']:
            qry += f" AND c.generated >= {ph}"
            start = criteria['start_date']
            # c.generated is stored in whole seconds; accept a ms-scale
            # value from a caller too, same as end_date below.
            if start > 1000000000000:
                qvars.append(int(start / 1000))
            else:
                qvars.append(int(start))
        if 'end_date' in criteria and criteria['end_date']:
            qry += f" AND c.generated <= {ph}"
            end = criteria['end_date']
            if end > 1000000000000:
                qvars.append(int(end / 1000))
            else:
                qvars.append(int(end))
        if filterFp:
            qry += " AND c.false_positive <> 1"
        qry += " ORDER BY c.data"
        with self.dbhLock:
            try:
                self.dbh.execute(qry, qvars)
                return self.dbh.fetchall()
            except (psycopg2.Error) as e:
                raise IOError(
                    "SQL error encountered when searching events"
                ) from e

    def close(self):
        if hasattr(self, 'dbh') and self.dbh:
            try:
                self.dbh.close()
            except Exception:
                pass
            self.dbh = None
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
