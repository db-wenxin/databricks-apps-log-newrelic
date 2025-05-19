# databricks-apps-log-newrelic

A simple guide to send Databricks Apps logs to New Relic APM for centralized monitoring.

## Quick Setup
1. **Add New Relic to your app dependencies**

2. **Create or download `newrelic.ini`**
- Set your license key and app name
- Place this file in your app's root directory

3. **Update `app.yaml` to use New Relic admin**
```yaml
command: [
  "newrelic-admin",
  "run-program",
  "flask",  # Or your framework: uvicorn, streamlit, etc.
  "--app",
  "app.py",
  "run"
]
env:
  - name: "NEW_RELIC_CONFIG_FILE"
    value: "./newrelic.ini"

```
4. **Deploy your app and verify**

Check logs at your-app-url/logz
Verify data appears in New Relic dashboard

## Note
This setup focuses on application logs only, not infrastructure metrics. For advanced configurations, refer to the New Relic Python Agent documentation.