import subprocess
import tempfile
import tracemalloc
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse, JSONResponse

# Profiling packages aren't installed on production environment
with suppress(ModuleNotFoundError):
    import memray
    import objgraph
    import pyinstrument


class OverFastMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> HTMLResponse | JSONResponse:
        # Don't make any profiling if query param is not here
        if not request.query_params.get("profile", False):
            return await call_next(request)

        # Proceed if requested
        return await self._dispatch(request, call_next)


class MemrayInMemoryMiddleware(OverFastMiddleware):
    async def _dispatch(self, request: Request, call_next: Callable) -> HTMLResponse:
        # Create an temporary file
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp_bin_file:
            tmp_bin_path = Path(tmp_bin_file.name)

        # Start Memray Tracker with the in-memory buffer
        destination = memray.FileDestination(path=tmp_bin_path, overwrite=True)
        with memray.Tracker(destination=destination):
            await call_next(request)

        # Convert the binary profiling data to an HTML report
        html_report = self.generate_html_report(tmp_bin_path)

        # Return the HTML report to the user directly
        return HTMLResponse(content=html_report, media_type="text/html")

    def generate_html_report(self, tmp_bin_path: Path) -> str:
        """
        Converts the binary tracking data in `buffer` to an HTML report.
        """
        # Create a temporary file for the HTML output
        with tempfile.NamedTemporaryFile(
            suffix=".html", delete_on_close=True
        ) as tmp_html_file:
            tmp_html_path = Path(tmp_html_file.name)

        # Use subprocess to call memray CLI to generate HTML flamegraph
        try:
            subprocess.run(  # noqa: S603
                [
                    "/bin/uv",
                    "run",
                    "memray",
                    "flamegraph",
                    "-o",
                    str(tmp_html_path),
                    str(tmp_bin_path),
                ],
                check=True,
            )
            # Read the generated HTML content
            html_content = tmp_html_path.read_text()
        finally:
            pass

        return html_content


class PyInstrumentMiddleware(OverFastMiddleware):
    async def _dispatch(self, request: Request, call_next: Callable) -> HTMLResponse:
        with pyinstrument.Profiler(interval=0.001, async_mode="enabled") as profiler:
            await call_next(request)

        return HTMLResponse(profiler.output_html())


class TraceMallocMiddleware(OverFastMiddleware):
    def __init__(self, app: FastAPI):
        super().__init__(app)
        tracemalloc.start()

    async def _dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        # Take a snapshot before the request
        snapshot_before = tracemalloc.take_snapshot()

        # Process the request
        await call_next(request)

        # Take a snapshot after the request
        snapshot_after = tracemalloc.take_snapshot()

        # Compute the difference
        top_stats = snapshot_after.compare_to(snapshot_before, "lineno")

        # Log the top memory usage changes
        memory_report = [
            {
                "file": stat.traceback[0].filename,
                "line": stat.traceback[0].lineno,
                "size_diff": stat.size_diff,
                "size": stat.size,
                "count": stat.count_diff,
            }
            for stat in top_stats[:10]  # Top 10 memory diffs
        ]

        return JSONResponse(content=memory_report)


class ObjGraphMiddleware(OverFastMiddleware):
    async def _dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        # Capture common object types before processing
        objects_before = objgraph.most_common_types(limit=10)
        objgraph_count_before = {obj[0]: obj[1] for obj in objects_before}

        # Process the request
        await call_next(request)

        # Capture common object types after processing
        objects_after = objgraph.most_common_types(limit=10)
        objgraph_count_after = {obj[0]: obj[1] for obj in objects_after}

        # Calculate new objects
        new_objects = {
            obj: count - objgraph_count_before.get(obj, 0)
            for obj, count in objgraph_count_after.items()
            if count > objgraph_count_before.get(obj, 0)
        }

        # Compare and create a report of differences in object types
        memory_report = {
            "before": objgraph_count_before,
            "after": objgraph_count_after,
            "new_objects": new_objects,
        }

        return JSONResponse(content=memory_report)
