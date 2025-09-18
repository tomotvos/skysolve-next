"""
Tests for log rotation functionality.
"""

import pytest
import os
import tempfile
import logging.handlers
from skysolve_next.core.logging_config import SkySolveLogger, StructuredFormatter

class TestLogRotation:
    """Test log rotation functionality"""
    
    def test_rotation_settings_loading(self):
        """Test that rotation settings are loaded correctly from config"""
        config = {
            'logging': {
                'rotation': {
                    'max_file_size_mb': 5,
                    'backup_count': 3
                }
            }
        }
        
        logger_manager = SkySolveLogger(config)
        max_bytes, backup_count = logger_manager._get_rotation_settings()
        
        assert max_bytes == 5 * 1024 * 1024  # 5MB in bytes
        assert backup_count == 3
    
    def test_rotation_settings_defaults(self):
        """Test that default rotation settings are used when config is missing"""
        logger_manager = SkySolveLogger({})
        max_bytes, backup_count = logger_manager._get_rotation_settings()
        
        assert max_bytes == 10 * 1024 * 1024  # 10MB default
        assert backup_count == 5  # 5 backups default
    
    def test_rotating_file_handler_creation(self):
        """Test that RotatingFileHandler is created with correct settings"""
        import tempfile
        import shutil
        
        # Create a temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        temp_log_file = os.path.join(temp_dir, "test_rotation.jsonl")
        
        try:
            # Create a handler directly to test rotation
            max_bytes = 1024  # 1KB for easy testing
            backup_count = 2
            
            handler = logging.handlers.RotatingFileHandler(
                temp_log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            handler.setFormatter(StructuredFormatter("test"))
            
            # Create test logger
            test_logger = logging.getLogger("test_rotation_handler")
            test_logger.setLevel(logging.INFO)
            test_logger.handlers.clear()
            test_logger.addHandler(handler)
            
            # Generate enough logs to trigger rotation
            for i in range(20):
                test_logger.info(f"Test rotation message {i} with some extra content to reach the size limit")
            
            handler.close()
            
            # Check that backup files were created
            backup_files = []
            for filename in os.listdir(temp_dir):
                if filename.startswith("test_rotation.jsonl."):
                    backup_files.append(filename)
            
            assert len(backup_files) > 0, "No backup files were created during rotation"
            assert len(backup_files) <= backup_count, f"Too many backup files: {len(backup_files)} > {backup_count}"
            
            # Check main file exists and is reasonably sized
            assert os.path.exists(temp_log_file)
            main_file_size = os.path.getsize(temp_log_file)
            assert main_file_size > 0, "Main log file is empty"
            
        finally:
            # Clean up
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_config_integration_with_settings(self):
        """Test that settings.json rotation config is properly loaded"""
        from skysolve_next.core.config import Settings
        
        # This tests that our settings model includes rotation settings
        settings = Settings()
        assert hasattr(settings.logging, 'rotation')
        assert hasattr(settings.logging.rotation, 'max_file_size_mb')
        assert hasattr(settings.logging.rotation, 'backup_count')
        
        # Test default values
        assert settings.logging.rotation.max_file_size_mb == 10
        assert settings.logging.rotation.backup_count == 5

if __name__ == "__main__":
    pytest.main([__file__])
