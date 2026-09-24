"""
RAISE (Research Assessment Intelligence & Semantic Extraction)
Security Subsystem — Subprocess Tunnel Watchdog
Manages cloudflared background processes with cross-platform group isolation:
- Windows: CREATE_NEW_PROCESS_GROUP, CTRL_BREAK_EVENT, taskkill /F /T /PID
- POSIX: start_new_session, os.killpg SIGTERM, os.killpg SIGKILL
"""

import os
import re
import sys
import signal
import asyncio
import logging
import subprocess
from typing import Optional, List

logger = logging.getLogger("RAISE.TunnelWatchdog")


class SubprocessTunnelManager:
    """
    Subprocess controller for Cloudflare Tunnels (cloudflared).
    Guarantees clean process tree teardown and prevents zombie port locks.
    """

    def __init__(self, port: int = 8000, binary_path: Optional[str] = None):
        self.port = port
        self.binary_path = binary_path or self._find_cloudflared_binary()
        self.process: Optional[asyncio.subprocess.Process] = None
        self.public_url: Optional[str] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._url_event = asyncio.Event()

    @staticmethod
    def _find_cloudflared_binary() -> str:
        """Locates cloudflared executable in project bin or system PATH."""
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent  # RAG
        local_bin = project_root / "bin" / ("cloudflared.exe" if sys.platform == "win32" else "cloudflared")
        if local_bin.exists():
            return str(local_bin)
        workspace_bin = project_root.parent / "bin" / ("cloudflared.exe" if sys.platform == "win32" else "cloudflared")
        if workspace_bin.exists():
            return str(workspace_bin)
        import shutil
        found = shutil.which("cloudflared")
        return found or ("cloudflared.exe" if sys.platform == "win32" else "cloudflared")

    async def start(self) -> Optional[str]:
        """
        Launches cloudflared tunnel as an isolated process group.
        Monitors stdout/stderr to extract the public https://*.trycloudflare.com URL.
        """
        cmd = [self.binary_path, "tunnel", "--url", f"http://127.0.0.1:{self.port}"]

        subprocess_kwargs: dict = {
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
        }

        if sys.platform != "win32":
            subprocess_kwargs["start_new_session"] = True
        else:
            # CREATE_NEW_PROCESS_GROUP = 0x00000200
            subprocess_kwargs["creationflags"] = 0x00000200

        try:
            self.process = await asyncio.create_subprocess_exec(*cmd, **subprocess_kwargs)
            logger.info(f"Spawned cloudflared (PID={self.process.pid}) for port {self.port}")
            self._monitor_task = asyncio.create_task(self._monitor_streams())
            
            # Wait up to 12 seconds for the public URL to be emitted
            try:
                await asyncio.wait_for(self._url_event.wait(), timeout=12.0)
            except asyncio.TimeoutError:
                logger.warning("Tunnel URL extraction timed out; tunnel may still be initializing.")
            return self.public_url
        except FileNotFoundError:
            logger.error(f"cloudflared binary not found at '{self.binary_path}'.")
            return None
        except Exception as e:
            logger.error(f"Failed to start tunnel subprocess: {e}")
            return None

    async def _monitor_streams(self) -> None:
        """Reads stdout/stderr asynchronously to capture the tunnel URL."""
        if not self.process:
            return

        url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

        async def read_stream(stream):
            while stream and not stream.at_eof():
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                match = url_regex.search(text)
                if match:
                    found_url = match.group(0)
                    if self.public_url != found_url:
                        self.public_url = found_url
                        self._url_event.set()
                        logger.info(f"Cloudflare Public Tunnel URL established: {self.public_url}")

        await asyncio.gather(
            read_stream(self.process.stdout),
            read_stream(self.process.stderr),
            return_exceptions=True
        )

    async def stop(self) -> None:
        """
        Executes a 2-stage teardown protocol:
        1. Graceful signal (CTRL_BREAK_EVENT on Windows / SIGTERM on POSIX)
        2. Waits up to 3.0s non-blocking grace window
        3. Escalates to forced process tree kill (taskkill /F /T /PID on Windows / SIGKILL on POSIX)
        """
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()

        if not self.process:
            return

        pid = self.process.pid
        logger.info(f"Initiating teardown of tunnel process (PID={pid})...")

        # 1. Polite signal
        try:
            if sys.platform != "win32":
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGTERM)
            else:
                # Sends break to process group
                os.kill(pid, signal.CTRL_BREAK_EVENT)
        except Exception as err:
            logger.debug(f"Graceful signal rejected or PID already gone: {err}")

        # 2. Wait up to 3 seconds for exit
        try:
            await asyncio.wait_for(self.process.wait(), timeout=3.0)
            logger.info(f"Subprocess PID={pid} exited gracefully.")
            return
        except asyncio.TimeoutError:
            logger.warning(f"Subprocess PID={pid} did not exit in 3.0s. Escalating to forced tree kill...")

        # 3. Forced escalation
        try:
            if sys.platform != "win32":
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGKILL)
            else:
                # taskkill /F /T /PID <pid>
                kill_proc = await asyncio.create_subprocess_exec(
                    "taskkill", "/F", "/T", "/PID", str(pid),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await kill_proc.wait()
            await asyncio.wait_for(self.process.wait(), timeout=2.0)
            logger.info(f"Subprocess PID={pid} forcibly terminated.")
        except Exception as err:
            logger.error(f"Forced termination error for PID={pid}: {err}")
