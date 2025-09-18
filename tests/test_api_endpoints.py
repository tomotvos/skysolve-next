"""
Comprehensive tests for all API endpoints to ensure frontend-backend integration works.
These tests verify that all endpoints the JavaScript frontend depends on are available.
"""

import pytest
import json
import os
from fastapi.testclient import TestClient
from skysolve_next.web.app import app
from skysolve_next.core.config import settings

client = TestClient(app)

class TestCoreAPIEndpoints:
    """Test core API endpoints that the frontend JavaScript depends on"""
    
    def test_root_endpoint(self):
        """Test that the root endpoint returns HTML"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "SkySolve Next" in response.text
    
    def test_status_endpoint(self):
        """Test /status endpoint that JavaScript polls for current mode"""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert "status" in data
        assert data["mode"] in ["solve", "align", "test"]
        assert data["status"] == "running"
    
    def test_mode_endpoint_valid_modes(self):
        """Test /mode endpoint accepts valid modes"""
        valid_modes = ["solve", "align", "test"]
        
        for mode in valid_modes:
            response = client.post("/mode", json={"mode": mode})
            assert response.status_code == 200
            data = response.json()
            assert data["result"] == "success"
            assert data["mode"] == mode
            
            # Verify the mode was actually set
            status_response = client.get("/status")
            assert status_response.json()["mode"] == mode
    
    def test_mode_endpoint_invalid_mode(self):
        """Test /mode endpoint rejects invalid modes"""
        response = client.post("/mode", json={"mode": "invalid"})
        assert response.status_code == 400
        assert "Invalid mode" in response.json()["detail"]
    
    def test_mode_endpoint_missing_mode(self):
        """Test /mode endpoint handles missing mode parameter"""
        response = client.post("/mode", json={})
        assert response.status_code == 400
    
    def test_logs_endpoint(self):
        """Test /logs endpoint returns proper structure"""
        response = client.get("/logs")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)
    
    def test_logs_endpoint_with_count(self):
        """Test /logs endpoint respects count parameter"""
        response = client.get("/logs?count=5")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert len(data["logs"]) <= 5

class TestSettingsEndpoints:
    """Test settings-related endpoints"""
    
    def test_get_settings(self):
        """Test GET /settings endpoint"""
        response = client.get("/settings")
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected settings structure
        assert "mode" in data
        assert "web_port" in data
        assert "lx200_port" in data
        assert "log_level" in data
        assert "solver" in data
        assert "camera" in data
        assert "onstep" in data
        assert "logging" in data
    
    def test_post_settings(self):
        """Test POST /settings endpoint"""
        # Get current settings first
        current_response = client.get("/settings")
        current_settings = current_response.json()
        
        # Update a setting
        new_settings = {
            "solver": {
                "solve_radius": 25.0
            }
        }
        
        response = client.post("/settings", json=new_settings)
        assert response.status_code == 200
        
        # Verify the setting was updated
        updated_response = client.get("/settings")
        updated_settings = updated_response.json()
        assert updated_settings["solver"]["solve_radius"] == 25.0

class TestSolveEndpoints:
    """Test solve-related endpoints"""
    
    def test_solve_endpoint_exists(self):
        """Test that POST /solve endpoint exists (may fail without proper setup)"""
        response = client.post("/solve")
        # We don't test for success since it requires camera setup
        # Just verify the endpoint exists and doesn't return 404
        assert response.status_code != 404
    
    def test_get_solve_endpoint(self):
        """Test GET /solve endpoint exists"""
        response = client.get("/solve")
        assert response.status_code != 404

class TestWorkerEndpoints:
    """Test worker-related endpoints"""
    
    def test_worker_status_endpoint(self):
        """Test /worker-status endpoint"""
        response = client.get("/worker-status")
        assert response.status_code == 200
        data = response.json()
        # Should return worker status information
        assert isinstance(data, dict)

class TestSystemEndpoints:
    """Test system control endpoints"""
    
    def test_auto_solve_endpoint(self):
        """Test /auto-solve endpoint exists"""
        response = client.post("/auto-solve", json={"enabled": False})
        assert response.status_code != 404
    
    def test_auto_push_endpoint(self):
        """Test /auto-push endpoint exists"""  
        response = client.post("/auto-push", json={"enabled": False})
        assert response.status_code != 404

class TestWebSocketEndpoints:
    """Test WebSocket endpoints (connection only, not full functionality)"""
    
    def test_websocket_logs_endpoint_exists(self):
        """Test that WebSocket /ws/logs endpoint exists and can connect"""
        # Test that we can successfully connect to the WebSocket endpoint
        try:
            with client.websocket_connect("/ws/logs") as websocket:
                # If we get here, the endpoint exists and accepts connections
                # We don't need to test full functionality, just that it exists
                assert websocket is not None
                # Optionally send a close message to cleanly disconnect
                pass
        except Exception as e:
            # If there's an exception, it should not be a 404 or route not found
            error_msg = str(e).lower()
            assert "404" not in error_msg, f"WebSocket endpoint not found: {e}"
            assert "not found" not in error_msg, f"WebSocket endpoint not found: {e}"
            # Other exceptions are acceptable (like connection issues)

class TestEndpointIntegration:
    """Test that endpoints work together as the frontend expects"""
    
    def test_mode_change_workflow(self):
        """Test the complete mode change workflow that JavaScript performs"""
        # 1. Get current status
        status_response = client.get("/status")
        assert status_response.status_code == 200
        original_mode = status_response.json()["mode"]
        
        # 2. Change to a different mode
        new_mode = "test" if original_mode != "test" else "solve"
        mode_response = client.post("/mode", json={"mode": new_mode})
        assert mode_response.status_code == 200
        
        # 3. Verify status reflects the change
        new_status_response = client.get("/status")
        assert new_status_response.status_code == 200
        assert new_status_response.json()["mode"] == new_mode
        
        # 4. Restore original mode
        restore_response = client.post("/mode", json={"mode": original_mode})
        assert restore_response.status_code == 200
    
    def test_settings_persistence(self):
        """Test that settings changes persist through the API"""
        # Get original settings
        original_response = client.get("/settings")
        original_settings = original_response.json()
        original_radius = original_settings["solver"]["solve_radius"]
        
        # Change a setting
        new_radius = original_radius + 5.0
        client.post("/settings", json={
            "solver": {"solve_radius": new_radius}
        })
        
        # Verify change persisted
        updated_response = client.get("/settings")
        updated_settings = updated_response.json()
        assert updated_settings["solver"]["solve_radius"] == new_radius
        
        # Restore original setting
        client.post("/settings", json={
            "solver": {"solve_radius": original_radius}
        })

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
