#!/usr/bin/env python3
"""
HTTP test script to test the web app endpoints
"""

import urllib.request
import urllib.error
import json
import socket

def test_web_app():
    """Test the web app endpoints"""
    base_url = "http://localhost:5001"
    
    print("Testing web app endpoints...")
    
    # Test root endpoint first
    try:
        print("Testing root endpoint...")
        with urllib.request.urlopen(f"{base_url}/", timeout=5) as response:
            status = response.getcode()
            print(f"Root endpoint: Status {status}")
            if status == 200:
                print("Root endpoint is working!")
                return True
            else:
                content = response.read().decode()
                print(f"Root endpoint returned: {content[:200]}")
                return False
    except Exception as e:
        print(f"Error testing root endpoint: {e}")
        return False

def test_logs_endpoint():
    """Test just the logs endpoint with proper timeout handling"""
    try:
        print("Testing /logs endpoint with 5 second timeout...")
        
        # Set a socket timeout for the entire operation
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(5.0)
        
        try:
            with urllib.request.urlopen("http://localhost:5001/logs?count=5") as response:
                status = response.getcode()
                print(f"Logs endpoint: Status {status}")
                
                if status == 200:
                    content = response.read().decode()
                    data = json.loads(content)
                    logs = data.get('logs', [])
                    print(f"Successfully got {len(logs)} log entries")
                    
                    # Show a few log entries
                    for i, log in enumerate(logs[:3]):
                        print(f"Log {i+1}: {log}")
                        
                    return True
                else:
                    print(f"Logs endpoint returned status: {status}")
                    return False
                    
        finally:
            socket.setdefaulttimeout(old_timeout)
            
    except socket.timeout:
        print("Logs endpoint timed out after 5 seconds - this confirms the hanging issue!")
        return False
    except Exception as e:
        print(f"Error testing logs endpoint: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Testing web app...")
    
    if test_web_app():
        print("\nRoot endpoint works, now testing logs endpoint...")
        success = test_logs_endpoint()
        print(f"\nLogs endpoint test {'PASSED' if success else 'FAILED'}")
    else:
        print("\nRoot endpoint failed, skipping logs test")
        
    print("=" * 50)
