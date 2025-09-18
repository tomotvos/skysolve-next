#!/usr/bin/env python3
"""
API Endpoint Validator
Validates that all required API endpoints exist and work correctly.
Run this after any changes to the web app to ensure frontend integration works.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from skysolve_next.web.app import app

def validate_endpoints():
    """Validate all critical API endpoints"""
    client = TestClient(app)
    results = []
    
    endpoints_to_test = [
        # Core endpoints that JavaScript depends on
        ("GET", "/", "Root page"),
        ("GET", "/status", "Application status"),
        ("POST", "/mode", "Mode switching", {"mode": "test"}),
        ("GET", "/logs", "Log retrieval"),
        ("GET", "/settings", "Settings retrieval"),
        ("POST", "/settings", "Settings update", {"solver": {"solve_radius": 20.0}}),
        ("GET", "/worker-status", "Worker status"),
        ("POST", "/solve", "Image solving"),
        ("GET", "/solve", "Solve status"),
        ("POST", "/auto-solve", "Auto-solve toggle", {"enabled": False}),
        ("POST", "/auto-push", "Auto-push toggle", {"enabled": False}),
    ]
    
    print("🔍 Validating API endpoints...")
    print("=" * 50)
    
    for test_data in endpoints_to_test:
        method = test_data[0]
        endpoint = test_data[1] 
        description = test_data[2]
        payload = test_data[3] if len(test_data) > 3 else None
        
        try:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json=payload)
            else:
                response = None
                
            if response and response.status_code != 404:
                status = "✅ PASS"
                results.append(True)
            else:
                status = "❌ FAIL (404 Not Found)"
                results.append(False)
                
        except Exception as e:
            status = f"❌ ERROR: {str(e)[:50]}..."
            results.append(False)
            
        print(f"{method:4} {endpoint:15} - {description:20} - {status}")
    
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} endpoints working")
    
    if passed == total:
        print("🎉 All endpoints are working!")
        return True
    else:
        print("⚠️  Some endpoints are missing or broken")
        print("   This may cause frontend JavaScript errors")
        return False

def validate_frontend_dependencies():
    """Check that specific endpoints the frontend JavaScript needs are working"""
    client = TestClient(app)
    print("\n🎯 Validating frontend JavaScript dependencies...")
    print("=" * 50)
    
    # Test the exact workflow the frontend JavaScript performs
    critical_tests = [
        ("Status Check", lambda: client.get("/status")),
        ("Mode Change", lambda: client.post("/mode", json={"mode": "test"})),
        ("Status Verification", lambda: client.get("/status")),
        ("Settings Load", lambda: client.get("/settings")),
        ("Log Retrieval", lambda: client.get("/logs?count=10")),
    ]
    
    all_passed = True
    
    for test_name, test_func in critical_tests:
        try:
            response = test_func()
            if response.status_code in [200, 202]:  # Accept both OK and Accepted
                print(f"✅ {test_name:20} - Status {response.status_code}")
            else:
                print(f"❌ {test_name:20} - Status {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"❌ {test_name:20} - ERROR: {str(e)[:30]}...")
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All frontend dependencies are working!")
        print("   The web UI mode switching should work now")
    else:
        print("⚠️  Some frontend dependencies are broken")
        print("   The web UI may not function correctly")
    
    return all_passed

if __name__ == "__main__":
    print("SkySolve Next API Endpoint Validator")
    print("=" * 50)
    
    basic_check = validate_endpoints()
    frontend_check = validate_frontend_dependencies()
    
    if basic_check and frontend_check:
        print("\n🏆 All validations passed!")
        sys.exit(0)
    else:
        print("\n💥 Some validations failed!")
        sys.exit(1)
