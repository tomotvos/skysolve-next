"""
Integration test that validates all API endpoints work correctly.
This prevents the issue where endpoints disappear but unit tests continue to pass.
"""

import pytest
from fastapi.testclient import TestClient
from skysolve_next.web.app import app

class TestAPIEndpointAvailability:
    """Comprehensive test to ensure ALL API endpoints exist and respond correctly"""
    
    client = TestClient(app)
    
    def test_all_critical_endpoints_exist(self):
        """Test that all endpoints the frontend depends on exist and return non-404 status"""
        
        critical_endpoints = [
            # Frontend JavaScript dependencies - these MUST work
            ("GET", "/", "Root HTML page"),
            ("GET", "/status", "Application status for mode detection"),  
            ("POST", "/mode", "Mode switching functionality", {"mode": "test"}),
            ("GET", "/logs", "Log retrieval for display"),
            ("GET", "/settings", "Settings retrieval"),
            ("POST", "/settings", "Settings updates", {"solver": {"solve_radius": 20.0}}),
            
            # Core functionality endpoints  
            ("GET", "/worker-status", "Worker status monitoring"),
            ("POST", "/solve", "Image solving"),
            ("GET", "/solve", "Solve status check"),
            
            # System control endpoints
            ("POST", "/auto-solve", "Auto-solve control", {"enabled": False}),
            ("POST", "/auto-push", "Auto-push control", {"enabled": False}),
        ]
        
        failed_endpoints = []
        
        for endpoint_data in critical_endpoints:
            method = endpoint_data[0]
            endpoint = endpoint_data[1]
            description = endpoint_data[2]
            payload = endpoint_data[3] if len(endpoint_data) > 3 else None
            
            try:
                if method == "GET":
                    response = self.client.get(endpoint)
                elif method == "POST":
                    response = self.client.post(endpoint, json=payload)
                else:
                    continue
                    
                # Endpoint must exist (not 404) and not return method not allowed (405)
                if response.status_code in [404, 405]:
                    failed_endpoints.append(f"{method} {endpoint} - {description}")
                    
            except Exception as e:
                failed_endpoints.append(f"{method} {endpoint} - ERROR: {str(e)}")
        
        # Assert all endpoints are available
        if failed_endpoints:
            error_msg = "The following critical API endpoints are missing or broken:\n"
            error_msg += "\n".join([f"  - {endpoint}" for endpoint in failed_endpoints])
            error_msg += "\n\nThis will cause frontend JavaScript errors!"
            pytest.fail(error_msg)
    
    def test_frontend_javascript_workflow(self):
        """Test the exact workflow that frontend JavaScript performs"""
        
        # 1. Page load - get current status
        status_response = self.client.get("/status")
        assert status_response.status_code == 200, "Status endpoint must work for page load"
        
        status_data = status_response.json()
        assert "mode" in status_data, "Status must include current mode"
        assert "status" in status_data, "Status must include application status"
        
        original_mode = status_data["mode"]
        assert original_mode in ["solve", "align", "test"], f"Invalid mode: {original_mode}"
        
        # 2. Mode change - switch to test mode
        mode_response = self.client.post("/mode", json={"mode": "test"})
        assert mode_response.status_code == 200, "Mode change must succeed"
        
        mode_data = mode_response.json()
        assert mode_data["result"] == "success", "Mode change must return success"
        assert mode_data["mode"] == "test", "Mode change must confirm new mode"
        
        # 3. Verify mode change persisted  
        verify_response = self.client.get("/status")
        assert verify_response.status_code == 200, "Status check after mode change must work"
        
        verify_data = verify_response.json()
        assert verify_data["mode"] == "test", "Mode change must persist"
        
        # 4. Load settings (for UI state)
        settings_response = self.client.get("/settings")
        assert settings_response.status_code == 200, "Settings load must work"
        
        settings_data = settings_response.json()
        assert "mode" in settings_data, "Settings must include mode"
        
        # 5. Get logs (for display)
        logs_response = self.client.get("/logs?count=5")
        assert logs_response.status_code == 200, "Logs retrieval must work"
        
        logs_data = logs_response.json()
        assert "logs" in logs_data, "Logs response must include logs array"
        assert isinstance(logs_data["logs"], list), "Logs must be an array"
        
        # 6. Restore original mode
        restore_response = self.client.post("/mode", json={"mode": original_mode})
        assert restore_response.status_code == 200, "Mode restoration must work"
    
    def test_mode_switching_all_modes(self):
        """Test switching between all supported modes"""
        
        modes = ["solve", "align", "test"]
        
        for target_mode in modes:
            # Switch to mode
            response = self.client.post("/mode", json={"mode": target_mode})
            assert response.status_code == 200, f"Failed to switch to {target_mode} mode"
            
            # Verify mode was set
            status_response = self.client.get("/status")
            status_data = status_response.json()
            assert status_data["mode"] == target_mode, f"Mode {target_mode} was not persisted"
    
    def test_invalid_mode_rejection(self):
        """Test that invalid modes are properly rejected"""
        
        invalid_modes = ["invalid", "debug", "admin", "", None]
        
        for invalid_mode in invalid_modes:
            response = self.client.post("/mode", json={"mode": invalid_mode})
            assert response.status_code == 400, f"Invalid mode '{invalid_mode}' should be rejected"
    
    def test_logs_endpoint_functionality(self):
        """Test logs endpoint returns proper structure and respects parameters"""
        
        # Test basic logs retrieval
        response = self.client.get("/logs")
        assert response.status_code == 200
        
        data = response.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)
        
        # Test count parameter
        response = self.client.get("/logs?count=3")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["logs"]) <= 3
        
        # Test that log entries have proper structure (if any exist)
        if data["logs"]:
            log_entry = data["logs"][0]
            assert isinstance(log_entry, dict)
            # Verify log entries have expected fields
            expected_fields = ["timestamp", "level", "message"]
            for field in expected_fields:
                assert field in log_entry, f"Log entry missing field: {field}"
