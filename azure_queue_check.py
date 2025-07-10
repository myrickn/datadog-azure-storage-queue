import sys

site_packages = "/opt/datadog-agent/embedded/lib/python3.12/site-packages"
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

from azure_queue_check_impl import AzureQueueCheck
