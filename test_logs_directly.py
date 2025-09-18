#!/usr/bin/env python3
"""
Direct test of the logging system to diagnose the /logs endpoint issue
"""

import sys
import os
sys.path.append('/Users/tomo/Development/skysolve-next')

from skysolve_next.core.logging_config import get_recent_logs, get_logger

def test_logging_directly():
    """Test the logging system directly"""
    print("Testing logging system directly...")
    
    # First, let's create some log entries
    logger = get_logger(__name__)
    logger.info("Test log entry 1")
    logger.warning("Test log entry 2")
    logger.error("Test log entry 3")
    
    print("Created 3 test log entries")
    
    # Now try to get recent logs
    try:
        print("Attempting to get recent logs...")
        logs = get_recent_logs(10)
        print(f"Successfully retrieved {len(logs)} log entries")
        
        for i, log in enumerate(logs[-3:]):  # Show last 3 entries
            print(f"Log {i+1}: {log}")
            
        return True
    except Exception as e:
        print(f"Error getting logs: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_logging_directly()
    print(f"Test {'PASSED' if success else 'FAILED'}")
