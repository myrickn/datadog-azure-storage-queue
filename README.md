# Azure Queue Check for Datadog

This custom Datadog Agent check collects metrics from Azure Storage Queues, specifically:

- The age (in seconds) of the oldest message
- The approximate message count (queue depth)

---

## Files

- `azure_queue_check.py`: Entry point for the Datadog Agent.
- `azure_queue_check_impl.py`: Contains the check implementation logic.

---

## Prerequisites

Ensure that your Datadog Agent is installed and Python 3.12 is available via the embedded path:

```
/opt/datadog-agent/embedded/
```

You will also need the following Python packages installed in the Agent’s embedded environment:

```bash
sudo -u dd-agent /opt/datadog-agent/embedded/bin/pip install azure-storage-queue azure-core requests
```

---

## File Installation and Permissions

Place the Python files in the custom checks directory:

```bash
sudo -u dd-agent cp azure_queue_check.py azure_queue_check_impl.py /etc/datadog-agent/checks.d/
```

Set ownership and permissions:

```bash
sudo -u dd-agent chown dd-agent:dd-agent /etc/datadog-agent/checks.d/azure_queue_check*.py
sudo -u dd-agent chmod 644 /etc/datadog-agent/checks.d/azure_queue_check*.py
```

---

## Configuration

Create the configuration file at `/etc/datadog-agent/conf.d/azure_queue_check.d/conf.yaml` with the following content:

```yaml
init_config: {}

instances:
  - connection_string: "<YOUR_AZURE_QUEUE_CONNECTION_STRING>"
    proxy_url: "http://proxy.com:8080"  # Optional
    tags:
      - env:prod
      - region:us-east
    queues:
      - name: my-queue-1
        tags:
          - app:orders
      - name: my-queue-2
        tags:
          - app:billing
```

Replace `<YOUR_AZURE_QUEUE_CONNECTION_STRING>` with your actual Azure Storage Queue connection string.

---

## Restart Agent and Verify

After installation and configuration:

```bash
sudo systemctl restart datadog-agent
```

To verify the check is running:

```bash
sudo -u dd-agent tail -f /var/log/datadog/agent.log | grep azure_queue_check
```

---

## Metrics Collected

| Metric Name                               | Type  | Description                                 |
|------------------------------------------|-------|---------------------------------------------|
| `custom.azure_queue.oldest_message_age`   | Gauge | Age in seconds of the oldest queue message  |
| `custom.azure_queue.depth`                | Gauge | Approximate number of messages in the queue |

---

## Troubleshooting

- Make sure the Datadog Agent is restarted after copying files or editing configuration.
- Check that the Azure connection string has access to the relevant queues.
- Confirm Python dependencies are installed in the embedded environment.
- Check the agent log file at `/var/log/datadog/agent.log` for errors.

---
