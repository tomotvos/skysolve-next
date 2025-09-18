#!/usr/bin/env python3
"""
Test script to verify logging configuration works correctly.
"""

import sys
import time
from skysolve_next.core.logging_config import get_logger, set_log_level, get_recent_logs
from skysolve_next.core.config import settings

def test_logging():
    """Test the centralized logging configuration"""
    
    print("Testing centralized logging configuration...")
    
    # Test different loggers
    logger1 = get_logger("test_component1", "test")
    logger2 = get_logger("test_component2", "solver")
    logger3 = get_logger("test_component3", "web")
    
    # Test different log levels
    print("\n1. Testing different log levels:")
    set_log_level("DEBUG")
    logger1.debug("This is a debug message")
    logger1.info("This is an info message")
    logger1.warning("This is a warning message")
    logger1.error("This is an error message")
    
    print("\n2. Testing log level changes:")
    set_log_level("WARNING")
    logger1.info("This INFO message should NOT appear")
    logger1.warning("This WARNING message should appear")
    
    print("\n3. Testing different components:")
    set_log_level("INFO")
    logger2.info("Solver component log")
    logger3.info("Web component log")
    
    print("\n4. Testing log capture:")
    recent_logs = get_recent_logs(5)
    print(f"Captured {len(recent_logs)} recent log entries")
    for log_entry in recent_logs[-3:]:  # Show last 3
        print(f"  - {log_entry['timestamp'][:19]} [{log_entry['level']}] {log_entry['message']}")
    
    print("\n5. Testing settings integration:")
    # Update log level through settings
    settings.logging.level = "ERROR"
    settings.reload_if_changed()
    logger1.info("This should not appear (level = ERROR)")
    logger1.error("This error should appear")
    
    # Reset to INFO
    settings.logging.level = "INFO"
    set_log_level("INFO")
    
    print("\nLogging configuration test completed successfully!")

if __name__ == "__main__":
    test_logging()
