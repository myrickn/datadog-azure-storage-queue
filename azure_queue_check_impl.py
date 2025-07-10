from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import time
import logging

import requests
from azure.storage.queue import QueueServiceClient
from azure.core.pipeline.transport import RequestsTransport
from datadog_checks.base import AgentCheck


class AzureQueueCheck(AgentCheck):
    """Datadog custom check for Azure Storage Queue metrics."""

    def __init__(self, name, init_config, instances=None):
        super().__init__(name, init_config, instances)
        logging.getLogger("azure").setLevel(logging.WARNING)
        self._queue_service: Optional[QueueServiceClient] = None
        self._connection_string: Optional[str] = None

    def _ensure_client(self, connection_string: str, proxy_url: Optional[str] = None) -> None:
        if self._queue_service is None or connection_string != self._connection_string:
            self.log.info("Initializing QueueServiceClient...")
            proxies = None
            if proxy_url:
                proxies = {"http": proxy_url, "https": proxy_url}
                self.log.info(f"Using proxy: {proxy_url}")

            session = requests.Session()
            if proxies:
                session.proxies.update(proxies)

            transport = RequestsTransport(session=session, connection_timeout=3, read_timeout=2)

            self._queue_service = QueueServiceClient.from_connection_string(
                connection_string, transport=transport
            )
            self._connection_string = connection_string

    def _get_oldest_message_age(self, queue_name: str) -> float:
        qc = self._queue_service.get_queue_client(queue_name)
        peeked = qc.peek_messages(max_messages=1)
        messages = list(peeked)
        if not messages:
            self.log.debug(f"Queue {queue_name} is empty. Posting age as 0.")
            return 0.0
        insert_time = messages[0].insertion_time
        now_utc = datetime.now(timezone.utc)
        return (now_utc - insert_time).total_seconds()

    def _get_queue_depth(self, queue_name: str) -> int:
        qc = self._queue_service.get_queue_client(queue_name)
        props = qc.get_queue_properties()
        return props.approximate_message_count or 0

    def _process_queue(self, queue_name: str, tags: List[str]) -> Optional[Tuple[str, float, int, List[str]]]:
        try:
            self.log.info(f"AzureQueueCheck: processing {queue_name}")
            age = self._get_oldest_message_age(queue_name)
            depth = self._get_queue_depth(queue_name)
            return (queue_name, age, depth, tags)
        except Exception as e:
            self.log.error(f"AzureQueueCheck: Error processing queue {queue_name}: {e}", exc_info=True)
            return None

    def check(self, instance: Dict):
        self.log.info("AzureQueueCheck: starting check()")

        connection_string = instance.get("connection_string")
        proxy_url = instance.get("proxy_url")
        if not connection_string:
            raise Exception("connection_string is required")

        self._ensure_client(connection_string, proxy_url=proxy_url)

        default_tags = instance.get("tags", [])
        queues: List = instance.get("queues", [])
        work_items = []

        for queue_cfg in queues:
            if isinstance(queue_cfg, dict):
                queue_name = queue_cfg.get("name")
                queue_tags = queue_cfg.get("tags", [])
            else:
                queue_name = str(queue_cfg)
                queue_tags = []

            if not queue_name:
                continue

            tags = list(default_tags) + list(queue_tags) + [f"queue:{queue_name}"]
            work_items.append((queue_name, tags))

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(self._process_queue, queue_name, tags)
                for queue_name, tags in work_items
            ]

            for future in futures:
                result = future.result()
                if result:
                    queue_name, age, depth, tags = result
                    self.log.info(f"AzureQueueCheck: sending age={age}, depth={depth} for {queue_name}")
                    self.gauge("custom.azure_queue.oldest_message_age", age, tags=tags)
                    self.gauge("custom.azure_queue.depth", depth, tags=tags)

        self.log.info(f"AzureQueueCheck finished in {time.time() - start_time:.2f}s")
