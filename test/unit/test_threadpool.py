"""Unit tests for spiderfoot.threadpool module."""

import unittest
from unittest import mock
import concurrent.futures
import threading
import time

from spiderfoot.threadpool import SpiderFootThreadPool


class TestSpiderFootThreadPool(unittest.TestCase):
    """Test cases for SpiderFootThreadPool class."""

    def setUp(self):
        """Set up test case."""
        self.pool = SpiderFootThreadPool(max_workers=2, name="TestPool")
        
    def tearDown(self):
        """Clean up after test case."""
        self.pool.shutdown(wait=True)
        
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.pool.name, "TestPool")
        self.assertIsInstance(self.pool.executor, concurrent.futures.ThreadPoolExecutor)
        self.assertIsInstance(self.pool.lock, threading.RLock)
        self.assertEqual(self.pool.futures, {})
        
    def test_submit(self):
        """Test submit method."""
        def test_function():
            return "success"
            
        # Submit a task
        future = self.pool.submit(test_function, taskName="test_task")
        
        # Verify task was submitted
        self.assertIsInstance(future, concurrent.futures.Future)
        self.assertIn("test_task", self.pool.futures)
        self.assertEqual(len(self.pool.futures["test_task"]), 1)
        
        # Wait for task to complete
        result = future.result(timeout=5)
        
        # Verify task result
        self.assertEqual(result, "success")
        
    def test_submit_with_args(self):
        """Test submit method with arguments."""
        def test_function(arg1, arg2, kwarg=None):
            return f"{arg1}-{arg2}-{kwarg}"
            
        # Submit a task with arguments
        future = self.pool.submit(test_function, "value1", "value2", taskName="test_task", kwarg="value3")
        
        # Wait for task to complete
        result = future.result(timeout=5)
        
        # Verify task result
        self.assertEqual(result, "value1-value2-value3")
        
    def test_submit_max_threads(self):
        """Test submit method with max threads."""
        completed = []
        
        def slow_function(idx):
            time.sleep(0.5)
            completed.append(idx)
            return idx
        
        # Submit tasks to fill the pool (max 2 threads per task name)
        futures = []
        for i in range(4):
            futures.append(self.pool.submit(slow_function, i, taskName="limited_task", maxThreads=2))
        
        # Wait for tasks to complete
        concurrent.futures.wait(futures)
        
        # Verify all tasks completed
        self.assertEqual(len(completed), 4)
        
    def test_count_queued_tasks(self):
        """Test countQueuedTasks method."""
        def test_function():
            time.sleep(0.2)
            return "success"
            
        # Submit tasks
        self.pool.submit(test_function, taskName="task_type_1")
        self.pool.submit(test_function, taskName="task_type_1")
        self.pool.submit(test_function, taskName="task_type_2")
        
        # Count tasks
        self.assertEqual(self.pool.countQueuedTasks("task_type_1"), 2)
        self.assertEqual(self.pool.countQueuedTasks("task_type_2"), 1)
        self.assertEqual(self.pool.countQueuedTasks("nonexistent_task"), 0)
        
        # Wait for tasks to complete
        self.pool.waitForCompletion()
        
    def test_wait_for_completion(self):
        """Test waitForCompletion method."""
        completed = []
        
        def test_function(idx):
            time.sleep(0.2)
            completed.append(idx)
            
        # Submit tasks
        for i in range(3):
            self.pool.submit(test_function, i, taskName="wait_task")
            
        # Wait for completion
        self.pool.waitForCompletion("wait_task")
        
        # Verify all tasks completed
        self.assertEqual(len(completed), 3)
        self.assertIn(0, completed)
        self.assertIn(1, completed)
        self.assertIn(2, completed)
        
    def test_wait_for_all_completion(self):
        """Test waitForCompletion method for all tasks."""
        completed_a = []
        completed_b = []
        
        def test_function_a(idx):
            time.sleep(0.2)
            completed_a.append(idx)
            
        def test_function_b(idx):
            time.sleep(0.2)
            completed_b.append(idx)
            
        # Submit tasks of different types
        for i in range(2):
            self.pool.submit(test_function_a, i, taskName="task_type_a")
        for i in range(3):
            self.pool.submit(test_function_b, i, taskName="task_type_b")
            
        # Wait for all tasks to complete
        self.pool.waitForCompletion()
        
        # Verify all tasks completed
        self.assertEqual(len(completed_a), 2)
        self.assertEqual(len(completed_b), 3)
        
    def test_shutdown(self):
        """Test shutdown method."""
        with mock.patch.object(self.pool.executor, 'shutdown') as mock_shutdown:
            # Call shutdown
            self.pool.shutdown(wait=True)
            
            # Verify executor shutdown was called
            mock_shutdown.assert_called_once_with(wait=True)
            
    def test_context_manager(self):
        """Test context manager interface."""
        with SpiderFootThreadPool(max_workers=1) as pool:
            def test_function():
                return "success"
                
            # Submit a task
            future = pool.submit(test_function)
            
            # Wait for task to complete
            result = future.result(timeout=5)
            
            # Verify task result
            self.assertEqual(result, "success")
            
        # Pool should be shut down after context
        
    def test_error_handling(self):
        """Test error handling in submitted tasks."""
        def failing_function():
            raise ValueError("Test error")
            
        # Submit a task that will fail
        future = self.pool.submit(failing_function)
        
        # Wait for task to complete and check exception
        with self.assertRaises(ValueError):
            future.result()
            
        # Pool should still be usable after task failure
        def success_function():
            return "recovered"
            
        future = self.pool.submit(success_function)
        self.assertEqual(future.result(timeout=5), "recovered")


if __name__ == '__main__':
    unittest.main()
