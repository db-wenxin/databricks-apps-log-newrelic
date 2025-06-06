# Databricks Apps - Datadog Logs Integration Demo

A simple demonstration of how to send Python application logs from Databricks Apps to Datadog using the V2 Logs API.

## Features

- 📝 Sends Python application logs (`logger.info`, `logger.warning`, `logger.error`) to Datadog
- 🔒 Securely retrieves Datadog API key from Databricks Secret Scope
- 🖥️ Simple web interface to monitor application status and trigger test logs
- ⚡ Real-time log streaming with batching for optimal performance

## Quick Start

### 1. Setup Databricks Secret Scope

First, create a secret scope and store your Datadog API key:

```bash
# Create secret scope (if not exists)
databricks secrets create-scope --scope datadog_credentials

# Store your Datadog API key
databricks secrets put --scope datadog_credentials --key datadog_api_key
```

### 2. Configure Application

Update the environment variables in `app.yaml`:

```yaml
env:
  - name: "DD_SERVICE"
    value: "your-service-name"
  - name: "DD_ENV"
    value: "development"  # or production
  - name: "DD_SITE"
    value: "us5.datadoghq.com"  # your Datadog site
  - name: "DD_HOST"
    value: "your-host-name"
  - name: "DD_API_SECRET_SCOPE"
    value: "datadog_credentials"
  - name: "DD_API_SECRET_KEYNAME"
    value: "datadog_api_key"
```

### 3. Deploy to Databricks Apps

Deploy the application using Databricks CLI or Workspace UI.

## Configuration Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `DD_SERVICE` | Service name for log tagging | `databricks-logs-demo` | No |
| `DD_ENV` | Environment name (dev/prod) | `demo` | No |
| `DD_SITE` | Datadog site URL | `us5.datadoghq.com` | No |
| `DD_HOST` | Host name for log tagging | `databricks-app` | No |
| `DD_API_SECRET_SCOPE` | Databricks secret scope name | N/A | **Yes** |
| `DD_API_SECRET_KEYNAME` | Secret key name for API key | N/A | **Yes** |

## Security Best Practices

✅ **DO**: Use Databricks Secret Scope to store sensitive API keys
```python
# The app safely retrieves the API key like this:
api_key = WorkspaceClient().dbutils.secrets.get(
    scope=os.environ.get("DD_API_SECRET_SCOPE"),
    key=os.environ.get("DD_API_SECRET_KEYNAME")
)
```

❌ **DON'T**: Put API keys directly in environment variables or code
```yaml
# Don't do this:
env:
  - name: "DD_API_KEY"
    value: "your-actual-api-key"  # NEVER do this!
```

## Project Structure

```
apm_datadog/
├── app.py              # Main Flask application with Datadog integration
├── app.yaml            # Databricks Apps configuration
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Web interface for monitoring
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

## API Endpoints

- `GET /` - Web interface
- `GET /api/status` - Application status and metrics
- `POST /api/trigger-error` - Manually trigger test error logs
- `POST /api/test-app-logs` - Send test logs with different levels
- `GET /health` - Health check endpoint

## How It Works

1. **Log Capture**: The application uses a custom `DatadogHTTPHandler` to capture Python logs
2. **Batching**: Logs are batched (10 entries or 5-second intervals) for efficient transmission
3. **Secure API Access**: Datadog API key is retrieved from Databricks Secret Scope at runtime
4. **Dual Output**: Logs are sent to both Datadog and console for visibility

## Testing

Access the web interface at your app's URL and use the following features:
- View real-time application status
- Trigger manual test errors
- Monitor recent error logs
- Test different log levels


## Disclaimer

**This code is provided as-is for demonstration purposes.** 

While this demo follows security best practices for handling API keys, please review and test thoroughly before using in production environments. The authors make no warranties regarding the suitability, reliability, or security of this code for any particular use case.

---

*For more information about Datadog Logs API, visit: https://docs.datadoghq.com/api/latest/logs/* 