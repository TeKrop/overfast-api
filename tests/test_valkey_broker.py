"""Tests for ValkeyListBroker — startup, shutdown, _get_client, kick, listen"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.tasks.valkey_broker import ValkeyListBroker

_MODULE = "app.adapters.tasks.valkey_broker"


@pytest.fixture
def broker() -> ValkeyListBroker:
    return ValkeyListBroker(url="valkey://localhost:6379", queue_name="test:queue")


class TestGetClient:
    def test_raises_runtime_error_before_startup(self, broker: ValkeyListBroker):
        """_get_client() raises RuntimeError if startup() was never called."""
        with pytest.raises(RuntimeError, match="startup"):
            broker._get_client()

    def test_returns_client_after_pool_set(self, broker: ValkeyListBroker):
        """_get_client() returns a Valkey client when pool is available."""
        mock_pool = MagicMock()
        broker._pool = mock_pool

        with patch(
            "app.adapters.tasks.valkey_broker.aiovalkey.Valkey",
            return_value=MagicMock(),
        ) as mock_valkey_cls:
            client = broker._get_client()

        mock_valkey_cls.assert_called_once_with(connection_pool=mock_pool)
        assert client is not None


class TestStartup:
    @pytest.mark.asyncio
    async def test_startup_creates_pool(self, broker: ValkeyListBroker):
        """startup() creates a BlockingConnectionPool."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.llen = AsyncMock(return_value=0)

        with (
            patch(
                f"{_MODULE}.aiovalkey.BlockingConnectionPool.from_url",
                return_value=mock_pool,
            ) as mock_from_url,
            patch.object(broker, "_get_client", return_value=mock_conn),
        ):
            await broker.startup()

        mock_from_url.assert_called_once_with(
            broker._url,
            max_connections=broker._max_pool_size,
        )
        assert broker._pool is mock_pool

    @pytest.mark.asyncio
    async def test_startup_sets_pool(self, broker: ValkeyListBroker):
        """After startup(), _pool is not None."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.llen = AsyncMock(return_value=0)

        with (
            patch(
                f"{_MODULE}.aiovalkey.BlockingConnectionPool.from_url",
                return_value=mock_pool,
            ),
            patch.object(broker, "_get_client", return_value=mock_conn),
        ):
            await broker.startup()

        assert broker._pool is not None


class TestShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_disconnects_pool(self, broker: ValkeyListBroker):
        """shutdown() calls pool.disconnect() and sets _pool to None."""
        mock_pool = AsyncMock()
        broker._pool = mock_pool

        await broker.shutdown()

        mock_pool.disconnect.assert_awaited_once()
        assert broker._pool is None

    @pytest.mark.asyncio
    async def test_shutdown_with_no_pool_does_not_raise(self, broker: ValkeyListBroker):
        """shutdown() is safe to call when _pool is already None."""
        broker._pool = None
        await broker.shutdown()  # Should not raise


class TestKick:
    @pytest.mark.asyncio
    async def test_kick_calls_lpush(self, broker: ValkeyListBroker):
        """kick() LPUSH the serialised message onto the queue."""
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        mock_message = MagicMock()
        mock_message.message = b"serialised-task"

        broker._pool = MagicMock()  # non-None so _get_client won't raise

        with patch.object(broker, "_get_client", return_value=mock_conn):
            await broker.kick(mock_message)

        mock_conn.lpush.assert_awaited_once_with("test:queue", b"serialised-task")


class TestListen:
    @pytest.mark.asyncio
    async def test_listen_yields_data_from_brpop(self, broker: ValkeyListBroker):
        """listen() yields the data part of BRPOP result."""
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        # First call returns a result; second returns None (no more items);
        # third returns None again — we'll stop iteration via StopAsyncIteration
        mock_conn.brpop = AsyncMock(
            side_effect=[
                ("test:queue", b"task-data-1"),
                ("test:queue", b"task-data-2"),
                None,
                None,
                None,
            ]
        )

        broker._pool = MagicMock()

        with patch.object(broker, "_get_client", return_value=mock_conn):
            results = []
            async for item in broker.listen():
                results.append(item)
                if len(results) >= 2:  # noqa: PLR2004
                    break

        assert results == [b"task-data-1", b"task-data-2"]

    @pytest.mark.asyncio
    async def test_listen_skips_none_brpop(self, broker: ValkeyListBroker):
        """listen() skips None results from BRPOP (timeout with no message)."""
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        call_count = 0

        async def brpop_side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # timeout, no message
            return ("test:queue", b"real-task")

        mock_conn.brpop = brpop_side_effect
        broker._pool = MagicMock()

        with patch.object(broker, "_get_client", return_value=mock_conn):
            results = []
            async for item in broker.listen():
                results.append(item)
                break  # take the first real item

        assert results == [b"real-task"]
