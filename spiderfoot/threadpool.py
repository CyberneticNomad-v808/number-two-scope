"""
SpiderFoot thread pool module.

This module provides thread pooling capabilities for SpiderFoot modules
to enable efficient parallel processing while maintaining control over
resource usage.
"""

import concurrent.futures
import threading
import traceback
from typing import Any, Callable, Dict, Optional, List, Set

from spiderfoot.logconfig import get_module_logger


class SpiderFootThreadPool:
    """Thread pool for SpiderFoot.

    Manages a pool of worker threads to handle tasks efficiently
    with better control over resource usage and error handling.
    """

    def __init__(self, max_workers: Optional[int] = None, name: str = "SpiderFoot"):
        """Initialize the thread pool.

        Args:
            max_workers: Maximum number of worker threads. If None, uses default based on system.
            name: Name for the thread pool for identification in logs
        """
        self.log = get_module_logger("threadpool")
        self.name = name
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix=f"sf-{name}"
        )
        self.futures: Dict[str,
                           Dict[concurrent.futures.Future, Dict[str, Any]]] = {}
        self.lock = threading.RLock()
        self.log.debug(
            f"Thread pool '{name}' initialized with max_workers={max_workers}"
        )

    def submit(
        self,
        fn: Callable,
        *args,
        taskName: str = "default",
        maxThreads: int = 5,
        **kwargs,
    ) -> concurrent.futures.Future:
        """Submit a task to the thread pool.

        Args:
            fn: Function to execute
            args: Positional arguments for the function
            taskName: Name for grouping related tasks
            maxThreads: Maximum number of concurrent tasks for this task name
            kwargs: Keyword arguments for the function

        Returns:
            Future object representing the execution of the callable
        """
        with self.lock:
            if taskName not in self.futures:
                self.futures[taskName] = {}

            # Clean up completed tasks
            completed = [
                future for future in self.futures[taskName] if future.done()]
            for future in completed:
                self.futures[taskName].pop(future, None)

            # Check if we're at the maximum thread count for this task name
            if len(self.futures[taskName]) >= maxThreads:
                self.log.debug(
                    f"Max threads {maxThreads} reached for task {taskName}. Waiting..."
                )
                # Wait for a task to complete
                if self.futures[taskName]:
                    done, _ = concurrent.futures.wait(
                        self.futures[taskName],
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    for future in done:
                        self.futures[taskName].pop(future, None)

            # Submit new task
            future = self.executor.submit(
                self._wrap_fn, fn, args, kwargs, taskName)
            self.futures[taskName][future] = {
                "name": taskName, "function": fn.__name__}

            return future

    def _wrap_fn(self, fn: Callable, args: tuple, kwargs: dict, task_name: str) -> Any:
        """Wrap the function call to handle exceptions and logging.

        Args:
            fn: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            task_name: Name of the task

        Returns:
            Result of the function call
        """
        try:
            self.log.debug(f"Starting task {task_name}: {fn.__name__}")
            result = fn(*args, **kwargs)
            self.log.debug(f"Completed task {task_name}: {fn.__name__}")
            return result
        except Exception as e:
            self.log.error(f"Error in task {task_name}: {fn.__name__} - {e}")
            self.log.debug(f"Error details: {traceback.format_exc()}")
            raise

    def countQueuedTasks(self, taskName: str) -> int:
        """Count the number of queued tasks for a specific task name.

        Args:
            taskName: Name of the task group

        Returns:
            int: Number of queued tasks
        """
        with self.lock:
            if taskName not in self.futures:
                return 0
            return len(self.futures[taskName])

    def waitForCompletion(self, taskName: Optional[str] = None) -> None:
        """Wait for all tasks to complete.

        Args:
            taskName: If specified, only wait for tasks with this name
        """
        with self.lock:
            if taskName:
                if taskName in self.futures and self.futures[taskName]:
                    self.log.debug(
                        f"Waiting for {len(self.futures[taskName])} tasks to complete for {taskName}"
                    )
                    concurrent.futures.wait(self.futures[taskName])
            else:
                for name, futures_dict in self.futures.items():
                    if futures_dict:
                        self.log.debug(
                            f"Waiting for {len(futures_dict)} tasks to complete for {name}"
                        )
                        concurrent.futures.wait(futures_dict)

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the thread pool.

        Args:
            wait: If True, wait for pending tasks to complete
        """
        self.log.debug(f"Shutting down thread pool '{self.name}'")
        self.executor.shutdown(wait=wait)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown(wait=True)
