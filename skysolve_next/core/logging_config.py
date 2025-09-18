"""
Centralized logging configuration for SkySolve Next.

Provides consistent logging setup across all components with support for:
- Dynamic log level changes from settings
- Structured logging with JSON formatting
- Component-specific loggers
- Real-time log streaming capabilities
"""

import logging
import logging.handlers
import json
import sys
import threading
import os
import time
from typing import Dict, List, Optional, Any
from collections import deque
from datetime import datetime
from enum import Enum

# Shared log file for inter-process communication
SHARED_LOG_FILE = "skysolve_next/logs/shared_logs.jsonl"

class LogLevel(Enum):
    """Supported log levels"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def __init__(self, component: str = "skysolve"):
        super().__init__()
        self.component = component
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "component": self.component,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any extra fields that were included in the log record
        if hasattr(record, 'extra_fields') and record.extra_fields:
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)

class SimpleFormatter(logging.Formatter):
    """Simple text formatter for console output"""
    
    def __init__(self, component: str = "skysolve"):
        super().__init__()
        self.component = component
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as simple text"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] {self.component}.{record.name} {record.levelname}: {record.getMessage()}"

class LogCapture:
    """Captures logs for real-time streaming to web interface"""
    
    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self.entries = deque(maxlen=max_entries)
        self.listeners: List[callable] = []
        self._lock = threading.Lock()
    
    def add_entry(self, record: logging.LogRecord, formatted_message: str):
        """Add a log entry to the capture"""
        with self._lock:
            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "formatted": formatted_message
            }
            
            # Add extra fields if present
            if hasattr(record, 'extra_fields') and record.extra_fields:
                entry.update(record.extra_fields)
            
            self.entries.append(entry)
            
            # Notify listeners
            for listener in self.listeners.copy():  # Copy to avoid modification during iteration
                try:
                    listener(entry)
                except Exception:
                    # Don't let listener errors affect logging
                    pass
    
    def get_recent_entries(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent log entries"""
        with self._lock:
            if count is None:
                return list(self.entries)
            return list(self.entries)[-count:] if count > 0 else []
    
    def add_listener(self, callback: callable):
        """Add a listener for new log entries"""
        with self._lock:
            if callback not in self.listeners:
                self.listeners.append(callback)
    
    def remove_listener(self, callback: callable):
        """Remove a log listener"""
        with self._lock:
            if callback in self.listeners:
                self.listeners.remove(callback)

class CaptureHandler(logging.Handler):
    """Handler that captures logs for real-time streaming"""
    
    def __init__(self, capture: LogCapture, formatter: logging.Formatter):
        super().__init__()
        self.capture = capture
        self.setFormatter(formatter)
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record"""
        try:
            formatted = self.format(record)
            self.capture.add_entry(record, formatted)
        except Exception:
            # Don't let capture errors affect logging
            pass

class SkySolveLogger:
    """Centralized logger management for SkySolve Next"""
    
    def __init__(self):
        self.loggers: Dict[str, logging.Logger] = {}
        self.capture = LogCapture()
        self._current_level = logging.INFO
        self._lock = threading.Lock()
        
        # Configure root logger
        self._setup_root_logger()
        
        # Start monitoring shared log file for inter-process logs
        self.start_log_file_monitor()
    
    def _setup_root_logger(self):
        """Setup the root logger configuration"""
        root_logger = logging.getLogger()
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Set root logger level
        root_logger.setLevel(self._current_level)
        
        # Add console handler with simple formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._current_level)
        console_handler.setFormatter(SimpleFormatter())
        root_logger.addHandler(console_handler)
        
        # Add capture handler for web interface
        capture_handler = CaptureHandler(self.capture, SimpleFormatter())
        capture_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(capture_handler)
        
        # Setup shared file handler for inter-process communication
        self._setup_shared_file_handler(root_logger)
    
    def _setup_shared_file_handler(self, root_logger):
        """Setup shared file handler for inter-process log sharing"""
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(SHARED_LOG_FILE)
            os.makedirs(log_dir, exist_ok=True)
            
            # Add file handler with JSON formatting for structured logs
            file_handler = logging.FileHandler(SHARED_LOG_FILE, mode='a')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(StructuredFormatter())
            root_logger.addHandler(file_handler)
        except Exception as e:
            # Don't let shared file setup errors break logging
            print(f"Warning: Could not setup shared log file: {e}")
    
    def start_log_file_monitor(self):
        """Start monitoring the shared log file for entries from other processes"""
        def monitor_file():
            """Monitor shared log file for new entries from other processes"""
            last_position = 0
            
            while True:
                try:
                    if os.path.exists(SHARED_LOG_FILE):
                        with open(SHARED_LOG_FILE, 'r') as f:
                            # Seek to last known position
                            f.seek(last_position)
                            
                            # Read new lines
                            for line in f:
                                line = line.strip()
                                if line:
                                    try:
                                        log_entry = json.loads(line)
                                        # Add to capture for web interface
                                        # Create a mock record for the capture
                                        record = logging.LogRecord(
                                            name=log_entry.get('logger', 'unknown'),
                                            level=getattr(logging, log_entry.get('level', 'INFO')),
                                            pathname="",
                                            lineno=log_entry.get('line', 0),
                                            msg=log_entry.get('message', ''),
                                            args=(),
                                            exc_info=None
                                        )
                                        
                                        # Add extra fields if present
                                        extra_fields = {k: v for k, v in log_entry.items() 
                                                      if k not in ['logger', 'level', 'line', 'message', 'timestamp', 'component', 'module', 'function']}
                                        if extra_fields:
                                            record.extra_fields = extra_fields
                                        
                                        formatted = f"[{log_entry.get('timestamp', '')}] {log_entry.get('component', 'unknown')}.{log_entry.get('logger', 'unknown')} {log_entry.get('level', 'INFO')}: {log_entry.get('message', '')}"
                                        self.capture.add_entry(record, formatted)
                                    except (json.JSONDecodeError, KeyError):
                                        # Skip malformed log entries
                                        continue
                            
                            # Update position
                            last_position = f.tell()
                    
                    # Check every 100ms for new log entries
                    time.sleep(0.1)
                    
                except Exception:
                    # Don't let file monitoring errors break the application
                    time.sleep(1.0)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_file, daemon=True)
        monitor_thread.start()
    
    def get_logger(self, name: str, component: str = "skysolve") -> logging.Logger:
        """Get a logger with the specified name and component"""
        with self._lock:
            full_name = f"{component}.{name}"
            
            if full_name not in self.loggers:
                logger = logging.getLogger(full_name)
                logger.setLevel(self._current_level)
                # Logger inherits handlers from root logger
                self.loggers[full_name] = logger
            
            return self.loggers[full_name]
    
    def set_log_level(self, level: str):
        """Set the log level for all loggers"""
        with self._lock:
            try:
                if hasattr(LogLevel, level):
                    log_level = getattr(LogLevel, level).value
                else:
                    # Try to get by name
                    log_level = getattr(logging, level.upper(), logging.INFO)
                
                self._current_level = log_level
                
                # Update root logger
                root_logger = logging.getLogger()
                root_logger.setLevel(log_level)
                
                # Update all handlers
                for handler in root_logger.handlers:
                    if isinstance(handler, logging.StreamHandler):
                        handler.setLevel(log_level)
                
                # Update all managed loggers
                for logger in self.loggers.values():
                    logger.setLevel(log_level)
                    
            except (AttributeError, ValueError):
                # Default to INFO if invalid level
                self._current_level = logging.INFO
    
    def get_log_level(self) -> str:
        """Get current log level as string"""
        return logging.getLevelName(self._current_level)
    
    def get_recent_logs(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent log entries for web interface"""
        return self.capture.get_recent_entries(count)
    
    def add_log_listener(self, callback: callable):
        """Add a listener for new log entries"""
        self.capture.add_listener(callback)
    
    def remove_log_listener(self, callback: callable):
        """Remove a log listener"""
        self.capture.remove_listener(callback)

# Global logger manager instance
_logger_manager: Optional[SkySolveLogger] = None

def get_logger_manager() -> SkySolveLogger:
    """Get the global logger manager instance"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = SkySolveLogger()
    return _logger_manager

def get_logger(name: str, component: str = "skysolve") -> logging.Logger:
    """Get a logger with consistent configuration"""
    return get_logger_manager().get_logger(name, component)

def set_log_level(level: str):
    """Set the log level for all loggers"""
    return get_logger_manager().set_log_level(level)

def get_log_level() -> str:
    """Get current log level"""
    return get_logger_manager().get_log_level()

def get_recent_logs(count: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get recent log entries for web interface"""
    return get_logger_manager().get_recent_logs(count)

def add_log_listener(callback: callable):
    """Add a listener for new log entries"""
    return get_logger_manager().add_log_listener(callback)

def remove_log_listener(callback: callable):
    """Remove a log listener"""
    return get_logger_manager().remove_log_listener(callback)