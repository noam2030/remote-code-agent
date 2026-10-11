"""Service managing asynchronous background code generation runs and multi-client streaming."""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncGenerator, Callable

from remote_code_agent.services.code_creation import generate_code_stream


class RunAlreadyInProgressError(Exception):
    """Raised when a run is already active and cannot start a new conflicting run."""
    pass


@dataclass
class ActiveRun:
    run_id: str
    project_name: str | None
    prompt: str
    status: str  # "running", "completed", "error", "cancelled"
    started_at: float
    completed_at: float | None = None
    logs: list[str] = field(default_factory=list)
    subscribers: set[asyncio.Queue] = field(default_factory=set)
    task: asyncio.Task | None = None
    error: str | None = None


class RunManager:
    """Manages server-side code generation runs decoupled from HTTP connection lifetimes."""

    def __init__(self):
        self.current_run: ActiveRun | None = None

    def get_active_run(self) -> dict:
        """Returns the current active or most recent run details."""
        if not self.current_run:
            return {
                "active": False,
                "run_id": None,
                "project_name": None,
                "prompt": None,
                "status": "idle",
                "logs": "",
                "started_at": None,
                "completed_at": None,
            }

        return {
            "active": self.current_run.status == "running",
            "run_id": self.current_run.run_id,
            "project_name": self.current_run.project_name,
            "prompt": self.current_run.prompt,
            "status": self.current_run.status,
            "logs": "".join(self.current_run.logs),
            "started_at": self.current_run.started_at,
            "completed_at": self.current_run.completed_at,
        }

    def start_run(
        self,
        prompt: str,
        project_name: str | None = None,
        generator_fn: Callable[..., AsyncGenerator[str, None]] | None = None,
    ) -> ActiveRun:
        """Starts a background execution run or attaches if the same run is already active."""
        if self.current_run and self.current_run.status == "running":
            curr_proj = (self.current_run.project_name or "").strip().lower()
            req_proj = (project_name or "").strip().lower()
            if curr_proj == req_proj and self.current_run.prompt.strip() == prompt.strip():
                return self.current_run

            raise RunAlreadyInProgressError(
                f"A generation task is already in progress for project '{self.current_run.project_name or 'current'}'. "
                "Please wait for it to complete."
            )

        run_id = str(uuid.uuid4())
        run = ActiveRun(
            run_id=run_id,
            project_name=project_name,
            prompt=prompt,
            status="running",
            started_at=time.time(),
        )
        self.current_run = run

        gen = (generator_fn or generate_code_stream)(prompt, project_name=project_name)
        task = asyncio.create_task(self._execute_run(run, gen))
        run.task = task
        return run

    async def _execute_run(self, run: ActiveRun, gen: AsyncGenerator[str, None]):
        """Executes the generator asynchronously and broadcasts chunks to subscribers."""
        try:
            async for chunk in gen:
                run.logs.append(chunk)
                for q in list(run.subscribers):
                    try:
                        q.put_nowait(chunk)
                    except Exception:
                        pass
            run.status = "completed"
        except asyncio.CancelledError:
            run.status = "cancelled"
            cancelled_msg = "\n⏹️ [Run Cancelled] Generation was cancelled.\n"
            run.logs.append(cancelled_msg)
            for q in list(run.subscribers):
                try:
                    q.put_nowait(cancelled_msg)
                except Exception:
                    pass
            raise
        except Exception as e:
            run.status = "error"
            run.error = str(e)
            err_msg = f"\n❌ [Run Error] Execution error: {e}\n"
            run.logs.append(err_msg)
            for q in list(run.subscribers):
                try:
                    q.put_nowait(err_msg)
                except Exception:
                    pass
        finally:
            run.completed_at = time.time()
            for q in list(run.subscribers):
                try:
                    q.put_nowait(None)  # EOF sentinel
                except Exception:
                    pass

    async def stream_run(
        self,
        run_id: str | None = None,
        offset: int = 0,
    ) -> AsyncGenerator[str, None]:
        """Streams run output. Replays past logs from offset, then streams live chunks."""
        run = self.current_run
        if not run or (run_id and run.run_id != run_id):
            return

        # If run is already finished (completed / error / cancelled):
        if run.status in ("completed", "error", "cancelled"):
            full_logs = "".join(run.logs)
            if offset < len(full_logs):
                yield full_logs[offset:]
            return

        # Run is currently running:
        q: asyncio.Queue[str | None] = asyncio.Queue()
        run.subscribers.add(q)
        try:
            current_logs = "".join(run.logs)
            snapshot_len = len(current_logs)
            if offset < snapshot_len:
                yield current_logs[offset:]

            while True:
                chunk = await q.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            run.subscribers.discard(q)


# Global singleton instance
run_manager = RunManager()
