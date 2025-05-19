import pandas as pd
from flask import Flask, jsonify
import logging
import threading
import time
import sys
import random
import newrelic
import os

try:
    import newrelic.agent
    print("newrelic.agent imported")
    HAS_NEWRELIC = True
except Exception:
    HAS_NEWRELIC = False
    print("newrelic.agent NOT imported")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
flask_app = Flask(__name__)

# Heartbeat status dictionary
heartbeat_status = {
    "status": "healthy",
    "last_beat": time.time(),
    "uptime_seconds": 0,
    "start_time": time.time()
}

# Heartbeat logger function
def heartbeat_logger():
    """Background task that logs a heartbeat message every 30 seconds"""
    while True:
        current_time = time.time()
        heartbeat_status["last_beat"] = current_time
        heartbeat_status["uptime_seconds"] = current_time - heartbeat_status["start_time"]
        
        heartbeat_message = f"Heartbeat check - System running normally - Uptime: {int(heartbeat_status['uptime_seconds'])}s"
        logger.info(heartbeat_message)
        print(heartbeat_message, flush=True)  # Output to standard output
        time.sleep(30)  # Send every 30 seconds

# Mock error generator function
def mock_error_generator():
    """Background task that generates a mock error every 60 seconds"""
    error_types = [
        "DatabaseConnectionError",
        "TimeoutError",
        "MemoryLimitExceeded",
        "APIRateLimitExceeded",
        "AuthenticationFailure"
    ]
    error_messages = [
        "Failed to connect to database",
        "Operation timed out after 30 seconds",
        "Process exceeded memory allocation",
        "Too many requests, API rate limit reached",
        "Invalid credentials provided"
    ]
    
    while True:
        # Wait for 60 seconds before generating error
        time.sleep(60)
        
        # Create random mock error
        error_type = random.choice(error_types)
        error_message = random.choice(error_messages)
        error_id = f"ERR-{random.randint(10000, 99999)}"
        
        # Create detailed error message
        mock_error = f"[MOCK ERROR] {error_type}: {error_message} (ID: {error_id})"
        
        # Log the error
        logger.error(mock_error)
        print(f"Generated mock error: {mock_error}", file=sys.stderr, flush=True)

# Start heartbeat logger in background thread
threading.Thread(target=heartbeat_logger, daemon=True).start()
threading.Thread(target=mock_error_generator, daemon=True).start()

@flask_app.route('/')
def hello_world():
    return f'<h1>Hello, World!</h1>'

@flask_app.route('/heartbeat')
def get_heartbeat():
    """Endpoint that returns current heartbeat status"""
    return jsonify(heartbeat_status)

@flask_app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "ok"})

@flask_app.route('/newrelic-status')
def newrelic_status():
    """check newrelic status"""
    status = {
        "imported": "newrelic" in sys.modules,
        "initialized": False,
        "config_file": os.environ.get('NEW_RELIC_CONFIG_FILE', 'unknown')
    }
    
    if "newrelic" in sys.modules:
        import newrelic.agent
        if hasattr(newrelic.agent, 'application'):
            app = newrelic.agent.application()
            if app:
                status["initialized"] = True
                status["app_name"] = app.name
    
    return jsonify(status)


if __name__ == '__main__':
    logger.info("Starting Flask application with heartbeat and mock errors")
    flask_app.run(debug=True)
