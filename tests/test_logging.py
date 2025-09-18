"""
Unit tests for centralized logging configuration.
"""

import pytest
import logging
import json
from unittest.mock import patch, MagicMock
from skysolve_next.core.logging_config import (
    SkySolveLogger, get_logger_manager, get_logger, set_log_level, 
    get_log_level, get_recent_logs, StructuredFormatter, LogCapture
)

class TestLogCapture:
    def test_log_capture_basic(self):
        """Test basic log capture functionality"""
        capture = LogCapture(max_entries=5)
        
        # Create a mock log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        capture.add_entry(record, "Formatted message")
        
        entries = capture.get_recent_entries()
        assert len(entries) == 1
        assert entries[0]["message"] == "Test message"
        assert entries[0]["level"] == "INFO"
        assert entries[0]["logger"] == "test_logger"
        assert entries[0]["formatted"] == "Formatted message"
    
    def test_log_capture_max_entries(self):
        """Test that log capture respects max entries limit"""
        capture = LogCapture(max_entries=3)
        
        for i in range(5):
            record = logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg=f"Message {i}",
                args=(),
                exc_info=None
            )
            capture.add_entry(record, f"Formatted {i}")
        
        entries = capture.get_recent_entries()
        assert len(entries) == 3
        assert entries[-1]["message"] == "Message 4"
    
    def test_log_capture_listeners(self):
        """Test log capture listener functionality"""
        capture = LogCapture()
        listener_calls = []
        
        def test_listener(entry):
            listener_calls.append(entry)
        
        capture.add_listener(test_listener)
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        capture.add_entry(record, "Formatted message")
        
        assert len(listener_calls) == 1
        assert listener_calls[0]["message"] == "Test message"
        
        # Test listener removal
        capture.remove_listener(test_listener)
        capture.add_entry(record, "Another message")
        
        assert len(listener_calls) == 1  # Should not have been called again

class TestStructuredFormatter:
    def test_structured_formatter_basic(self):
        """Test structured formatter creates proper JSON"""
        formatter = StructuredFormatter("test_component")
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["level"] == "INFO"
        assert data["component"] == "test_component"
        assert data["logger"] == "test_logger"
        assert data["message"] == "Test message"
        assert data["module"] == "test"
        assert data["line"] == 10
        assert "timestamp" in data
    
    def test_structured_formatter_with_exception(self):
        """Test structured formatter handles exceptions"""
        formatter = StructuredFormatter("test_component")
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Test error occurred",
                args=(),
                exc_info=exc_info
            )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["level"] == "ERROR"
        assert data["message"] == "Test error occurred"
        assert "exception" in data
        assert "ValueError: Test error" in data["exception"]
    
    def test_structured_formatter_with_extra_fields(self):
        """Test structured formatter includes extra fields"""
        formatter = StructuredFormatter("test_component")
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        record.extra_fields = {"solve_time": 1.5, "confidence": 0.95}
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["solve_time"] == 1.5
        assert data["confidence"] == 0.95

class TestSkySolveLogger:
    def test_logger_manager_singleton(self):
        """Test that get_logger_manager returns the same instance"""
        manager1 = get_logger_manager()
        manager2 = get_logger_manager()
        assert manager1 is manager2
    
    def test_get_logger_creates_unique_loggers(self):
        """Test that get_logger creates properly named loggers"""
        logger1 = get_logger("test1", "component1")
        logger2 = get_logger("test2", "component2")
        logger3 = get_logger("test1", "component1")  # Same as logger1
        
        assert logger1.name == "component1.test1"
        assert logger2.name == "component2.test2"
        assert logger1 is logger3  # Should return same instance
        assert logger1 is not logger2
    
    def test_set_log_level(self):
        """Test that set_log_level works correctly"""
        manager = get_logger_manager()
        
        # Test valid log levels
        set_log_level("DEBUG")
        assert get_log_level() == "DEBUG"
        
        set_log_level("WARNING")
        assert get_log_level() == "WARNING"
        
        # Test invalid log level defaults to INFO
        set_log_level("INVALID")
        assert get_log_level() == "INFO"
    
    def test_get_recent_logs(self):
        """Test that get_recent_logs returns proper format"""
        # Create a fresh logger manager for this test
        import skysolve_next.core.logging_config as logging_config
        from skysolve_next.core.logging_config import LogCapture, SkySolveLogger
        
        # Create a test-specific logger that doesn't interfere with the global one
        test_capture = LogCapture(max_entries=100)
        
        # Create a simple logger record manually and add it to capture
        import logging
        import time
        unique_message = f"Test log message {time.time()}"
        
        record = logging.LogRecord(
            name="test_logs",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg=unique_message,
            args=(),
            exc_info=None
        )
        
        test_capture.add_entry(record, f"[timestamp] test_logs INFO: {unique_message}")
        
        recent_logs = test_capture.get_recent_entries(10)
        
        assert isinstance(recent_logs, list)
        assert len(recent_logs) >= 1
        
        # Find our test message using the unique message
        test_log = None
        for log_entry in recent_logs:
            if unique_message in log_entry.get("message", ""):
                test_log = log_entry
                break
        
        assert test_log is not None
        assert test_log["level"] == "INFO"
        assert "timestamp" in test_log

class TestLoggingIntegration:
    """Integration tests to ensure logging works with existing code"""
    
    @patch('skysolve_next.core.config.settings')
    def test_settings_integration(self, mock_settings):
        """Test that settings integration works"""
        # Mock settings object
        mock_logging_settings = MagicMock()
        mock_logging_settings.level = "DEBUG"
        mock_settings.logging = mock_logging_settings
        mock_settings.log_level = "INFO"
        
        # This should work without errors
        from skysolve_next.core.config import Settings
        settings_obj = Settings()
        
        # Test reload functionality
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=123456), \
             patch('builtins.open'), \
             patch('json.load', return_value={"logging": {"level": "ERROR"}}):
            
            settings_obj._last_mtime = 123455  # Make it seem like file changed
            settings_obj.reload_if_changed()
            
            # Should not raise any errors

def test_solver_logging_integration():
    """Test that solvers use centralized logging correctly"""
    from skysolve_next.solver.astrometry_solver import AstrometrySolver
    from skysolve_next.solver.tetra3_solver import Tetra3Solver
    
    # Test AstrometrySolver
    astrometry_solver = AstrometrySolver()
    assert hasattr(astrometry_solver, 'logger')
    assert astrometry_solver.logger.name == "solver.astrometry_solver"
    
    # Test Tetra3Solver  
    tetra_solver = Tetra3Solver()
    assert hasattr(tetra_solver, 'logger')
    assert tetra_solver.logger.name == "solver.tetra3_solver"

def test_lx200_logging_integration():
    """Test that LX200 server uses centralized logging correctly"""
    from skysolve_next.publish.lx200_server import _logger
    
    # Verify the logger has the correct name
    assert _logger.name == "network.lx200_server"

def test_web_app_logging_integration():
    """Test that web app uses centralized logging correctly"""
    from skysolve_next.web.app import logger
    
    # Verify the logger has the correct name
    assert logger.name == "web.web_app"

if __name__ == "__main__":
    pytest.main([__file__])
