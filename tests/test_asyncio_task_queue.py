"""Tests for AsyncioTaskQueue adapter"""

import asyncio

import pytest

from app.adapters.tasks.asyncio_task_queue import AsyncioTaskQueue
from app.metaclasses import Singleton
from app.monitoring.metrics import (
    background_tasks_queue_size,
    background_tasks_total,
)


@pytest.fixture(autouse=True)
def _reset_task_queue():
    """Reset Singleton and pending jobs before each test for isolation."""
    Singleton._instances.pop(AsyncioTaskQueue, None)
    AsyncioTaskQueue._pending_jobs.clear()
    yield
    AsyncioTaskQueue._pending_jobs.clear()
    Singleton._instances.pop(AsyncioTaskQueue, None)


class TestSingleton:
    def test_same_instance_returned(self):
        q1 = AsyncioTaskQueue()
        q2 = AsyncioTaskQueue()
        assert q1 is q2

    def test_shared_pending_jobs_set(self):
        q1 = AsyncioTaskQueue()
        q2 = AsyncioTaskQueue()
        assert q1._pending_jobs is q2._pending_jobs


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_duplicate_job_skipped(self):
        queue = AsyncioTaskQueue()
        completed = []

        async def work():
            await asyncio.sleep(0.05)
            completed.append(1)

        await queue.enqueue("refresh", job_id="job-1", coro=work())
        await queue.enqueue("refresh", job_id="job-1")  # duplicate — no coro

        await asyncio.sleep(0.1)
        assert len(completed) == 1

    @pytest.mark.asyncio
    async def test_duplicate_coro_closed(self):
        """The second coroutine must be closed to prevent 'never awaited' warning."""
        queue = AsyncioTaskQueue()

        async def work():
            await asyncio.sleep(0.05)

        async def second():
            pass  # never should run

        await queue.enqueue("refresh", job_id="job-1", coro=work())

        # Enqueue with a coro while job-1 is still running
        coro = second()
        await queue.enqueue("refresh", job_id="job-1", coro=coro)

        # coro should be closed (not just pending)
        assert coro.cr_frame is None  # closed coroutine has no frame

        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_same_job_id_requeued_after_completion(self):
        """After a job finishes, the same job_id can be enqueued again."""
        queue = AsyncioTaskQueue()
        completed = []

        async def work():
            completed.append(1)

        await queue.enqueue("refresh", job_id="job-1", coro=work())
        await asyncio.sleep(0.05)
        assert len(completed) == 1

        await queue.enqueue("refresh", job_id="job-1", coro=work())
        await asyncio.sleep(0.05)
        assert len(completed) == 2  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_different_job_ids_both_run(self):
        queue = AsyncioTaskQueue()
        completed = []

        async def work(name: str):
            completed.append(name)

        await queue.enqueue("refresh", job_id="job-a", coro=work("a"))
        await queue.enqueue("refresh", job_id="job-b", coro=work("b"))
        await asyncio.sleep(0.05)

        assert sorted(completed) == ["a", "b"]


class TestCallbacks:
    @pytest.mark.asyncio
    async def test_on_complete_called_on_success(self):
        queue = AsyncioTaskQueue()
        completed_ids = []

        async def work():
            pass

        async def on_complete(job_id: str) -> None:
            completed_ids.append(job_id)

        await queue.enqueue(
            "refresh", job_id="job-1", coro=work(), on_complete=on_complete
        )
        await asyncio.sleep(0.05)

        assert completed_ids == ["job-1"]

    @pytest.mark.asyncio
    async def test_on_failure_called_on_error(self):
        queue = AsyncioTaskQueue()
        failures: list[tuple[str, Exception]] = []

        async def failing_work():
            msg = "boom"
            raise ValueError(msg)

        async def on_failure(job_id: str, exc: Exception) -> None:
            failures.append((job_id, exc))

        await queue.enqueue(
            "refresh", job_id="job-1", coro=failing_work(), on_failure=on_failure
        )
        await asyncio.sleep(0.05)

        assert len(failures) == 1
        assert failures[0][0] == "job-1"
        assert isinstance(failures[0][1], ValueError)

    @pytest.mark.asyncio
    async def test_on_complete_not_called_on_failure(self):
        queue = AsyncioTaskQueue()
        completed_ids = []

        async def failing_work():
            msg = "fail"
            raise RuntimeError(msg)

        async def on_complete(job_id: str) -> None:
            completed_ids.append(job_id)

        await queue.enqueue(
            "refresh", job_id="job-1", coro=failing_work(), on_complete=on_complete
        )
        await asyncio.sleep(0.05)

        assert completed_ids == []

    @pytest.mark.asyncio
    async def test_no_callbacks_no_error(self):
        """Enqueue without callbacks should run cleanly with no exception."""
        queue = AsyncioTaskQueue()

        async def work():
            pass

        await queue.enqueue("refresh", job_id="job-1", coro=work())
        await asyncio.sleep(0.05)


class TestMetrics:
    @pytest.mark.asyncio
    async def test_queue_size_increments_then_decrements(self):
        queue = AsyncioTaskQueue()
        sizes_during: list[float] = []

        async def work():
            val = background_tasks_queue_size.labels(task_type="refresh")._value.get()
            sizes_during.append(val)
            await asyncio.sleep(0.01)

        await queue.enqueue("refresh", job_id="job-1", coro=work())
        await asyncio.sleep(0.05)

        assert sizes_during[0] == 1.0
        after = background_tasks_queue_size.labels(task_type="refresh")._value.get()
        assert after == 0.0

    @pytest.mark.asyncio
    async def test_tasks_total_success(self):
        queue = AsyncioTaskQueue()

        async def work():
            pass

        before = background_tasks_total.labels(
            task_type="refresh", status="success"
        )._value.get()
        await queue.enqueue("refresh", job_id="job-1", coro=work())
        await asyncio.sleep(0.05)
        after = background_tasks_total.labels(
            task_type="refresh", status="success"
        )._value.get()

        assert after == before + 1

    @pytest.mark.asyncio
    async def test_tasks_total_failure(self):
        queue = AsyncioTaskQueue()

        async def failing_work():
            msg = "fail"
            raise ValueError(msg)

        before = background_tasks_total.labels(
            task_type="refresh", status="failure"
        )._value.get()
        await queue.enqueue("refresh", job_id="job-1", coro=failing_work())
        await asyncio.sleep(0.05)
        after = background_tasks_total.labels(
            task_type="refresh", status="failure"
        )._value.get()

        assert after == before + 1


class TestIsJobPendingOrRunning:
    @pytest.mark.asyncio
    async def test_pending_while_running(self):
        queue = AsyncioTaskQueue()
        is_pending_during: list[bool] = []

        async def work():
            is_pending_during.append(await queue.is_job_pending_or_running("job-1"))
            await asyncio.sleep(0.02)

        await queue.enqueue("refresh", job_id="job-1", coro=work())
        await asyncio.sleep(0.05)

        assert is_pending_during == [True]

    @pytest.mark.asyncio
    async def test_not_pending_after_completion(self):
        queue = AsyncioTaskQueue()

        async def work():
            pass

        await queue.enqueue("refresh", job_id="job-1", coro=work())
        await asyncio.sleep(0.05)

        assert not await queue.is_job_pending_or_running("job-1")

    @pytest.mark.asyncio
    async def test_not_pending_for_unknown_job(self):
        queue = AsyncioTaskQueue()
        assert not await queue.is_job_pending_or_running("unknown-job")
