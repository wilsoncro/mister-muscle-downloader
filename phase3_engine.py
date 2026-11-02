"""LOCAL BETA Phase 3: opt-in download queue engine (not wired into Qt UI)."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
import json, os, subprocess, tempfile, time
from typing import Callable

STATES = {'pending', 'running', 'completed', 'failed', 'paused', 'canceled'}

@dataclass
class Job:
    url: str
    mode: str = 'video'
    format_id: str = 'best'
    status: str = 'pending'
    attempts: int = 0
    error: str = ''


def fallback_formats(preferred: str, mode: str = 'video') -> list[str]:
    """Conservative yt-dlp selectors; never silently switch audio-only to video."""
    if mode == 'audio':
        candidates = [preferred, 'bestaudio/best']
    elif mode == 'video-only':
        candidates = [preferred, 'bestvideo', 'best']
    else:
        candidates = [preferred, 'bv*+ba/b', 'best']
    return list(dict.fromkeys(x for x in candidates if x))


def load_jobs(path: Path) -> list[Job]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or payload.get('schema') != 1:
        raise ValueError('Unsupported queue state')
    result = []
    for item in payload['jobs']:
        job = Job(**{k: item[k] for k in Job.__dataclass_fields__ if k in item})
        if job.status not in STATES:
            raise ValueError('Invalid job status')
        if job.status == 'running':
            job.status = 'pending'  # interrupted processes are eligible for recovery
        result.append(job)
    return result


def save_jobs(path: Path, jobs: list[Job]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix='.queue-', suffix='.json', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump({'schema': 1, 'jobs': [asdict(j) for j in jobs]}, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


class QueueEngine:
    """Runs a bounded number of workers. Runner receives Job and format selector.

    A runner should raise on failure. State file contains URLs: keep it local and
    never attach it to telemetry or bug reports.
    """
    def __init__(self, jobs: list[Job], state_path: Path, concurrency: int = 2,
                 retries: int = 2, delay: float = 0, runner: Callable | None = None):
        if not 1 <= concurrency <= 3:
            raise ValueError('Concurrency must be 1..3')
        if not 0 <= retries <= 5:
            raise ValueError('Retries must be 0..5')
        self.jobs, self.state_path = jobs, Path(state_path)
        self.concurrency, self.retries, self.delay = concurrency, retries, delay
        self.runner = runner or self._download
        import threading
        self.lock = threading.Lock()

    @staticmethod
    def _download(job: Job, selector: str):
        # No shell. yt-dlp continues supported .part downloads. Use local module.
        args = [os.sys.executable, '-m', 'yt_dlp', '--continue', '--no-playlist',
                '--format', selector, '--', job.url]
        proc = subprocess.run(args, capture_output=True, text=True, timeout=3600)
        if proc.returncode:
            # Avoid persisting stderr because it may contain private URLs/paths.
            raise RuntimeError('yt-dlp returned nonzero exit status')

    def _persist(self):
        with self.lock:
            save_jobs(self.state_path, self.jobs)

    def _run_one(self, job: Job):
        with self.lock:
            if job.status != 'pending':
                return
            job.status = 'running'
            save_jobs(self.state_path, self.jobs)
        selectors = fallback_formats(job.format_id, job.mode)
        for selector in selectors:
            for attempt in range(self.retries + 1):
                with self.lock:
                    if job.status != 'running':
                        save_jobs(self.state_path, self.jobs)
                        return
                    job.attempts += 1
                    save_jobs(self.state_path, self.jobs)
                try:
                    self.runner(job, selector)
                except Exception as exc:
                    with self.lock:
                        if job.status in ('paused', 'canceled'):
                            save_jobs(self.state_path, self.jobs)
                            return
                        job.error = type(exc).__name__  # no sensitive raw error text
                        save_jobs(self.state_path, self.jobs)
                    if attempt < self.retries and self.delay:
                        time.sleep(self.delay * (2 ** attempt))
                else:
                    with self.lock:
                        if job.status in ('paused', 'canceled'):
                            save_jobs(self.state_path, self.jobs)
                            return
                        job.status, job.error = 'completed', ''
                        save_jobs(self.state_path, self.jobs)
                    return
        with self.lock:
            if job.status in ('paused', 'canceled'):
                save_jobs(self.state_path, self.jobs)
                return
            job.status = 'failed'
            save_jobs(self.state_path, self.jobs)

    def run(self):
        self._persist()
        pending = [j for j in self.jobs if j.status == 'pending']
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = [pool.submit(self._run_one, j) for j in pending]
            for f in as_completed(futures):
                f.result()
        return {'completed': sum(j.status == 'completed' for j in self.jobs),
                'failed': sum(j.status == 'failed' for j in self.jobs)}
