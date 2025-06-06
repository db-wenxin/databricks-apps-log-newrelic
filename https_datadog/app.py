"""
Databricks Apps - Datadog Application Logs Demo
Sends Python application logs (from the `logging` module) to Datadog.

Features:
- Python application logs (logger.info/warning/error) are sent to Datadog.
- Logs are also written to the standard console output.

NOTE: Standard output/error (e.g., `print` statements) are NOT captured by this integration.
      This is to avoid instability from redirecting system streams in some environments.

Uses Datadog V2 API: https://api.{site}/api/v2/logs
Required secret: The Datadog API key must be stored in a Databricks secret.
                 The scope and key name must be set as environment variables.
"""
import os
import logging
import requests
import threading
import time
import random
from datetime import datetime
from collections import deque
from flask import Flask, jsonify, render_template
from databricks.sdk import WorkspaceClient

# --- Datadog Configuration ---

def get_datadog_api_key_from_secret():
    """
    Securely fetches the Datadog API key from Databricks secrets.
    The scope and key name are read from environment variables.
    """
    scope = os.environ.get("DD_API_SECRET_SCOPE")
    key = os.environ.get("DD_API_SECRET_KEYNAME")
    
    if not scope or not key:
        print("Warning: DD_API_SECRET_SCOPE or DD_API_SECRET_KEYNAME not set. Cannot fetch Datadog API key.")
        return None
        
    print(f"Fetching Datadog API key from secret. Scope: '{scope}', Key: '{key}'")
    try:
        api_key = WorkspaceClient().dbutils.secrets.get(scope=scope, key=key)
        print("Successfully fetched Datadog API key from secret.")
        return api_key
    except Exception as e:
        print(f"Error fetching Datadog API key from secret: {e}")
        return None

# Fetch the API key securely
DD_API_KEY = get_datadog_api_key_from_secret()

# Other Datadog configurations
DD_SITE = os.environ.get('DD_SITE', 'us5.datadoghq.com')
DD_SERVICE = os.environ.get('DD_SERVICE', 'databricks-logs-demo')
DD_ENV = os.environ.get('DD_ENV', 'demo')
DD_HOST = os.environ.get('DD_HOST', 'databricks-app')

# The StreamCapture class is removed to avoid redirecting stdout/stderr,
# which can cause instability in some environments. We will only capture
# logs from the Python logging module.
#
# class StreamCapture:
#    ...

class DatadogHTTPHandler(logging.Handler):
    """Custom log handler that sends logs directly to Datadog HTTP API"""
    
    def __init__(self, api_key, site=DD_SITE):
        super().__init__()
        self.api_key = api_key
        
        # The V2 logs intake endpoint is http-intake.logs.{site}, not api.{site}.
        # This was causing the 404 "Not found" error.
        # See: https://docs.datadoghq.com/api/latest/logs/#send-logs
        self.url = f"https://http-intake.logs.{site}/api/v2/logs"
            
        self.headers = {
            "DD-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        print(f"Datadog V2 Log API URL: {self.url}")
        self.batch = []
        self.batch_size = 10
        self.flush_interval = 5
        self._start_flusher()
    
    def _start_flusher(self):
        """Start background thread to flush logs periodically"""
        def flush_periodically():
            while True:
                time.sleep(self.flush_interval)
                self.flush()
        threading.Thread(target=flush_periodically, daemon=True).start()
    
    def emit(self, record):
        """Add log record to batch for sending to Datadog V2 API"""
        # Use "status" for log level, and format tags as a comma-separated string,
        # adhering to Datadog's standard attributes for proper parsing.
        # See: https://docs.datadoghq.com/logs/log_configuration/attributes_naming_convention/
        tags = [
            f"env:{DD_ENV}",
            f"service:{DD_SERVICE}",
            f"logger:{record.name}",
            f"status:{record.levelname.lower()}"
        ]

        log_entry = {
            "ddsource": "python",
            "ddtags": ",".join(tags),
            "hostname": DD_HOST,
            "message": self.format(record),
            "service": DD_SERVICE,
            "Status": record.levelname.lower(),
            # Add other structured attributes for better context in Datadog
            "logger": {
                "name": record.name,
                "thread_name": record.threadName,
            },
            "code": {
                 "function": record.funcName,
                 "line": record.lineno,
                 "module": record.module,
            }
        }
        
        self.batch.append(log_entry)
        if len(self.batch) >= self.batch_size:
            self.flush()
    
    def flush(self):
        """Send batched logs to Datadog V2 API"""
        if not self.batch:
            return
        
        batch_size = len(self.batch)
        
        # The V2 API expects a JSON array of log objects as the payload,
        # not a dictionary wrapping the logs. Sending `self.batch` directly.
        try:
            response = requests.post(self.url, headers=self.headers, json=self.batch, timeout=10)
            if response.status_code in [200, 202]:
                print(f"- Successfully sent {batch_size} log entries to Datadog")
                self.batch = []
            else:
                print(f"Failed to send logs. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            print(f"Exception sending logs: {e}")

# Flask application
app = Flask(__name__)

# Application state
heartbeat_status = {"last_heartbeat": None, "count": 0}
error_count = 0
recent_errors = deque(maxlen=10)

# Setup logging
# We always log to the console via StreamHandler.
# If a DD_API_KEY is present, we add the DatadogHTTPHandler to also send logs to Datadog.
handlers = [logging.StreamHandler()] 
if DD_API_KEY:
    print("Datadog integration enabled. Creating Datadog handler.")
    datadog_handler = DatadogHTTPHandler(DD_API_KEY, DD_SITE)
    handlers.append(datadog_handler)
else:
    print("Datadog integration disabled (DD_API_KEY not set). Logging to console only.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger(__name__)

def heartbeat_logger():
    """Background heartbeat log generator"""
    global heartbeat_status
    count = 0
    while True:
        count += 1
        heartbeat_status = {"last_heartbeat": time.time(), "count": count}
        logger.info(f"Heartbeat #{count} - Application running normally")
        time.sleep(30)

def mock_error_generator():
    """Mock error generator"""
    global error_count, recent_errors
    error_types = ["DatabaseTimeout", "NetworkError", "ValidationError", "ProcessingError"]
    
    while True:
        time.sleep(random.randint(45, 90))
        error_type = random.choice(error_types)
        error_id = f"ERR-{error_type[:3].upper()}-{random.randint(1000, 9999)}"
        mock_error = f"[{error_type}] Simulated error for testing (ID: {error_id})"
        
        logger.error(mock_error)
        error_count += 1
        recent_errors.append({
            'timestamp': time.time(),
            'message': mock_error,
            'type': error_type,
            'id': error_id
        })

# Start background threads
threading.Thread(target=heartbeat_logger, daemon=True).start()
threading.Thread(target=mock_error_generator, daemon=True).start()

@app.route('/')
def home():
    """Home page"""
    logger.info("Home page accessed")
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """Application status API"""
    return jsonify({
        "heartbeat": heartbeat_status,
        "error_count": error_count,
        "recent_errors": list(recent_errors),
        "datadog": {
            "logs_enabled": bool(DD_API_KEY),
            "service": DD_SERVICE,
            "env": DD_ENV,
            "site": DD_SITE
        }
    })

@app.route('/api/trigger-error', methods=['POST'])
def trigger_error():
    """Manually trigger error for testing"""
    global error_count
    error_id = f"ERR-MANUAL-{random.randint(10000, 99999)}"
    error_message = f"[MANUAL ERROR] User triggered test error (ID: {error_id})"
    
    logger.error(error_message)
    error_count += 1
    recent_errors.append({
        'timestamp': time.time(),
        'message': error_message,
        'type': 'ManualError',
        'id': error_id
    })
    
    return jsonify({"status": "error_triggered", "error": error_message})

@app.route('/health')
def health_check():
    """Health check"""
    return jsonify({"status": "ok"})

@app.route('/api/test-app-logs', methods=['POST'])
def test_app_logs():
    """Tests the application-level logging to Datadog."""
    
    logger.info("--- Starting Application Log Test ---")
    logger.info("This is a test INFO message from the application logger.")
    logger.warning("This is a test WARNING message from the application logger.")
    logger.error("This is a test ERROR message from the application logger.")
    
    try:
        # Deliberately trigger a division by zero error for testing
        1 / 0
    except Exception:
        # `exc_info=True` adds exception info to the log record,
        # including the traceback, without printing to stderr.
        logger.error("This is a test EXCEPTION log.", exc_info=True)
        
    logger.info("--- Application Log Test Complete ---")
    
    return jsonify({
        "status": "test_completed",
        "message": "Check your console and Datadog for the test log messages.",
        "tested_types": [
            "logger.info",
            "logger.warning",
            "logger.error",
            "logger.error with exception info"
        ]
    })

if __name__ == '__main__':
    logger.info("Starting Flask application for Datadog logs demo")
    if DD_API_KEY:
        logger.info(f"Datadog integration enabled - Service: {DD_SERVICE}, Env: {DD_ENV}, Site: {DD_SITE}")
    else:
        logger.warning("Datadog integration disabled - DD_API_KEY not found")
    
    app.run(debug=True, host='0.0.0.0', port=8000)