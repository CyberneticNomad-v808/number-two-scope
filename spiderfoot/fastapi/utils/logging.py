import logging
import atexit
import socket
import sys
import time
from contextlib import suppress
from logging.handlers import (
    QueueHandler,
    QueueListener,
    TimedRotatingFileHandler,
)
import multiprocessing
from typing import Dict, Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from spiderfoot import SpiderFootDb, SpiderFootHelpers


class JSONLogFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Add extra attributes from record
        for key, value in record.__dict__.items():
            if key not in ["args", "exc_info", "exc_text", "msg", "message",
                           "levelname", "levelno", "pathname", "filename",
                           "module", "name", "lineno", "funcName", "created",
                           "asctime", "msecs", "relativeCreated", "thread",
                           "threadName", "processName", "process"]:
                log_record[key] = value

        import json
        return json.dumps(log_record)


class SafeQueueListener(QueueListener):
    """Thread-safe implementation of QueueListener for handling logs from
    multiple threads.

    This class extends QueueListener to provide thread-safety when
    processing log records from multiple threads through a queue.
    """

    def dequeue(self, block):
        """Get a record from the queue.

        Args:
            block (bool): Whether to block if queue is empty

        Returns:
            LogRecord: A log record from the queue or None
        """
        if self.queue is not None:
            return self.queue.get(block)
        return None

    def _monitor(self):
        """Monitor the queue for records and process them."""
        try:
            while True:
                if self.queue is not None:
                    record = self.dequeue(True)
                    if record is not None:
                        self.handle(record)
                else:
                    break
        except Exception:
            self.handleError(None)

    def enqueue(self, record):
        """Put a record into the queue.

        Args:
            record (LogRecord): The log record to queue
        """
        if self.queue is not None:
            self.queue.put_nowait(record)


class SpiderFootSqliteLogHandler(logging.Handler):
    """Handler for logging to SQLite database.

    This ensures all SQLite logging is done from a single process and a
    single database handle to avoid concurrency issues.
    """

    def __init__(self, opts: dict) -> None:
        """Initialize the SQLite log handler.

        Args:
            opts (dict): Configuration options
        """
        self.opts = opts
        self.dbh = None
        self.batch = []
        if self.opts.get("_debug", False):
            self.batch_size = 100
        else:
            self.batch_size = 5
        self.shutdown_hook = False
        super().__init__()

    def emit(self, record: "logging.LogRecord") -> None:
        """Emit a log record.

        Args:
            record (logging.LogRecord): Log event record
        """
        if not self.shutdown_hook:
            atexit.register(self.logBatch)
            self.shutdown_hook = True
        scanId = getattr(record, "scanId", None)
        component = getattr(record, "module", None)
        if scanId:
            level = "STATUS" if record.levelname == "INFO" else record.levelname
            self.batch.append(
                (scanId, level, record.getMessage(), component, time.time())
            )
            if len(self.batch) >= self.batch_size:
                self.logBatch()

    def logBatch(self) -> None:
        """Log a batch of records to the database."""
        batch = self.batch
        self.batch = []
        if self.dbh is None:
            # Create a new database handle when the first log batch is processed
            self.makeDbh()
        logResult = self.dbh.scanLogEvents(batch)
        if logResult is False:
            # Try to recreate database handle if insert failed
            self.makeDbh()
            self.dbh.scanLogEvents(batch)

    def makeDbh(self) -> None:
        """Create a new database handle."""
        self.dbh = SpiderFootDb(self.opts)


class SpiderFootLogger:
    """SpiderFoot logger class."""

    def __init__(self, logname, refresh_rate=1):
        """Initialize SpiderFoot logger.

        Args:
            logname (str): name of the log
            refresh_rate (int): how quickly to refresh the log
        """
        self.logname = logname
        self.refresh_rate = refresh_rate
        self._logger = logging.getLogger(f"spiderfoot.{logname}")

    @property
    def log(self):
        return self._logger

    @log.setter
    def log(self, value):
        self._logger = value

    def debug(self, message):
        """Log debug message.

        Args:
            message (str): message to log
        """
        self._logger.debug(message)

    def info(self, message):
        """Log info message.

        Args:
            message (str): message to log
        """
        self._logger.info(message)

    def warning(self, message):
        """Log warning message.

        Args:
            message (str): message to log
        """
        self._logger.warning(message)

    def error(self, message):
        """Log error message.

        Args:
            message (str): message to log
        """
        self._logger.error(message)

    def critical(self, message):
        """Log critical message.

        Args:
            message (str): message to log
        """
        self._logger.critical(message)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests processed by the application."""

    def __init__(self, app, logger=None):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate request processing time
        process_time = (time.time() - start_time) * 1000

        # Log request details
        if self.logger:
            self.logger.info(
                f"{request.method} {request.url.path} "
                f"completed in {process_time:.2f}ms - Status: {response.status_code}"
            )

        return response


def setup_logging(config: Dict[str, Any] = None) -> None:
    """Configure logging for the FastAPI application.

    Args:
        config: Dictionary containing logging configuration
    """
    if config is None:
        config = {}

    log_level = config.get("log_level", "INFO")

    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Name for the logger

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


def logListenerSetup(loggingQueue, opts: dict = None) -> "QueueListener":
    """Create and start a SpiderFoot log listener in its own thread.

    This function sets up a centralized logging system that safely handles logs
    from multiple threads by using a queue-based approach. All log handlers are
    managed by a single listener thread to avoid file access conflicts.

    Args:
        loggingQueue (Queue): Queue (accepts both normal and multiprocessing queue types)
                              Must be instantiated in the main process.
        opts (dict): SpiderFoot config

    Returns:
        logging.handlers.QueueListener: Log listener
    """
    if opts is None:
        opts = dict()
    doLogging = opts.get("__logging", True)
    debug = opts.get("_debug", False)
    logLevel = logging.DEBUG if debug else logging.INFO

    # Log to terminal
    console_handler = logging.StreamHandler(sys.stderr)

    # Log debug messages to file
    log_dir = SpiderFootHelpers.logPath()
    debug_handler = TimedRotatingFileHandler(
        f"{log_dir}/spiderfoot.debug.log", when="d", interval=1, backupCount=30
    )

    # Log error messages to file
    error_handler = TimedRotatingFileHandler(
        f"{log_dir}/spiderfoot.error.log", when="d", interval=1, backupCount=30
    )

    # Get hostname for syslog format
    hostname = socket.gethostname()

    # Log to syslog format file
    syslog_handler = logging.FileHandler(f"{log_dir}/spiderfoot.syslog.log")
    syslog_format = logging.Formatter(
        f"%(asctime)s {hostname} %(name)s: %(message)s")
    syslog_handler.setFormatter(syslog_format)

    # Filter by log level
    console_handler.addFilter(lambda x: x.levelno >= logLevel)
    debug_handler.addFilter(lambda x: x.levelno >= logging.DEBUG)
    error_handler.addFilter(lambda x: x.levelno >= logging.WARN)
    syslog_handler.addFilter(lambda x: x.levelno >= logLevel)

    # Set log format
    log_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(module)s : %(message)s"
    )
    debug_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)s : %(message)s"
    )
    console_handler.setFormatter(log_format)
    debug_handler.setFormatter(debug_format)
    error_handler.setFormatter(debug_format)

    if doLogging:
        handlers = [console_handler, debug_handler,
                    error_handler, syslog_handler]
    else:
        handlers = []

    if doLogging and opts is not None:
        sqlite_handler = SpiderFootSqliteLogHandler(opts)
        sqlite_handler.setLevel(logLevel)
        sqlite_handler.setFormatter(log_format)
        handlers.append(sqlite_handler)

    spiderFootLogListener = SafeQueueListener(loggingQueue, *handlers)
    spiderFootLogListener.start()
    atexit.register(stop_listener, spiderFootLogListener)
    return spiderFootLogListener


def logWorkerSetup(loggingQueue) -> "logging.Logger":
    """Create a thread-safe root SpiderFoot logger.

    Creates a thread-safe logger that sends all log records to a queue,
    which is then processed by a single listener thread. This approach ensures
    thread-safety by centralizing all I/O operations to a single thread.

    Args:
        loggingQueue (Queue): Queue for logging events

    Returns:
        logging.Logger: Thread-safe logger
    """
    log = logging.getLogger("spiderfoot")
    # Don't do this more than once
    if len(log.handlers) == 0:
        log.setLevel(logging.DEBUG)
        queue_handler = QueueHandler(loggingQueue)
        log.addHandler(queue_handler)
    return log


def stop_listener(listener: "QueueListener") -> None:
    """Stop the log listener.

    Args:
        listener (logging.handlers.QueueListener): Log listener
    """
    with suppress(Exception):
        listener.stop()


def logEvent(
    instance_id: str, classification: str, message: str, module: str = None
) -> None:
    """Log an event to the appropriate logger.

    Args:
        instance_id (str): Scan instance ID
        classification (str): Log level (INFO, WARNING, ERROR, etc.)
        message (str): Log message
        module (str): Module name
    """
    if not module:
        module = "spiderfoot"

    logger = get_logger(module)

    log_level = getattr(logging, classification.upper(), None)
    if not isinstance(log_level, int):
        log_level = logging.INFO

    logger.log(log_level, f"[{instance_id}] {message}")
