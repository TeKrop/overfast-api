"""Custom Valkey List broker for taskiq.

Uses LPUSH for enqueuing (``kick``) and BRPOP for consuming (``listen``).
A :class:`~valkey.asyncio.BlockingConnectionPool` is shared across all
operations to avoid connection exhaustion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import valkey.asyncio as aiovalkey
from taskiq.abc.broker import AsyncBroker

from app.infrastructure.logger import logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from taskiq.message import BrokerMessage

_QUEUE_DEFAULT = "taskiq:queue"
_BRPOP_TIMEOUT = 2  # seconds; controls shutdown responsiveness


class ValkeyListBroker(AsyncBroker):
    """Taskiq broker backed by a Valkey List (LPUSH / BRPOP).

    The broker is intentionally simple:

    * ``kick`` pushes the serialised task bytes to the **left** of the list.
    * ``listen`` pops from the **right**, maintaining FIFO order.
    * A :class:`~valkey.asyncio.BlockingConnectionPool` is created once on
      ``startup`` and disconnected on ``shutdown``.

    Deduplication is the responsibility of the caller (e.g.
    :class:`~app.adapters.tasks.valkey_task_queue.ValkeyTaskQueue`).
    """

    def __init__(
        self,
        url: str,
        queue_name: str = _QUEUE_DEFAULT,
        max_pool_size: int = 10,
        **connection_kwargs: Any,
    ) -> None:
        super().__init__()
        self._url = url
        self.queue_name = queue_name
        self._max_pool_size = max_pool_size
        self._connection_kwargs = connection_kwargs
        self._pool: aiovalkey.BlockingConnectionPool | None = None

    def _get_client(self) -> aiovalkey.Valkey:
        """Return a client backed by the shared pool."""
        if self._pool is None:
            msg = "Broker not started — call startup() first"
            raise RuntimeError(msg)
        return aiovalkey.Valkey(connection_pool=self._pool)

    async def startup(self) -> None:
        """Create the connection pool and run taskiq startup hooks."""
        await super().startup()
        self._pool = aiovalkey.BlockingConnectionPool.from_url(
            self._url,
            max_connections=self._max_pool_size,
            **self._connection_kwargs,
        )
        logger.info(
            "ValkeyListBroker started (url=%s, queue=%s)", self._url, self.queue_name
        )

    async def shutdown(self) -> None:
        """Disconnect the pool and run taskiq shutdown hooks."""
        await super().shutdown()
        if self._pool is not None:
            await self._pool.disconnect()
            self._pool = None
        logger.info("ValkeyListBroker stopped.")

    async def kick(self, message: BrokerMessage) -> None:
        """Push a serialised task message to the left of the queue list."""
        async with self._get_client() as conn:
            await conn.lpush(self.queue_name, message.message)  # type: ignore[misc]

    async def listen(self) -> AsyncGenerator[bytes]:
        """Block-pop messages from the right of the queue and yield raw bytes.

        Keeps a single long-lived connection open for the worker lifetime.
        The short ``BRPOP`` timeout ensures shutdown is responsive.
        """
        async with self._get_client() as conn:
            while True:
                result = await conn.brpop(self.queue_name, timeout=_BRPOP_TIMEOUT)  # type: ignore[misc, arg-type]
                if result is not None:
                    _, data = result
                    yield data
