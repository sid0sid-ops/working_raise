"""
RAISE (Research Assessment Intelligence & Semantic Extraction)
Security Subsystem — Pre-Flight Port Sweep & Zombie Process Cleaner
Detects port binding locks (default port 8000) and terminates orphaned processes.
"""

import sys
import socket
import logging
import subprocess
from typing import Optional, List

logger = logging.getLogger("RAISE.PortSweep")


class PortSweep:
    """Probes ports for binding conflicts and safely terminates zombie processes."""

    @staticmethod
    def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
        """Returns True if the port is actively accepting connections."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0

    @classmethod
    def sweep_and_clean(cls, port: int, max_retries: int = 3) -> bool:
        """
        Verifies if port is open. If occupied, identifies and terminates the holding PID.
        Returns True if the port is free or was successfully cleared; False if still blocked.
        """
        if not cls.is_port_in_use(port):
            return True

        logger.warning(f"Port {port} is occupied by an existing process. Initiating sweep...")
        pids = cls.find_pids_on_port(port)
        if not pids:
            logger.info(f"Port {port} occupied but PID not discoverable via netstat/lsof.")
            return False

        for pid in pids:
            cls.kill_pid(pid)

        # Confirm port is now free
        for _ in range(max_retries):
            if not cls.is_port_in_use(port):
                logger.info(f"Port {port} successfully freed.")
                return True
        return not cls.is_port_in_use(port)

    @staticmethod
    def find_pids_on_port(port: int) -> List[int]:
        """Finds PIDs listening on the specified port in a cross-platform manner."""
        pids: List[int] = []
        try:
            if sys.platform == "win32":
                # netstat -ano | findstr :<port>
                output = subprocess.check_output(
                    ["netstat", "-ano"], stderr=subprocess.DEVNULL, text=True
                )
                for line in output.splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 5 and "LISTENING" in parts:
                        local_addr = parts[1]
                        if local_addr.endswith(f":{port}"):
                            try:
                                pid = int(parts[-1])
                                if pid > 0 and pid not in pids:
                                    pids.append(pid)
                            except ValueError:
                                pass
            else:
                # POSIX: lsof -ti :<port>
                output = subprocess.check_output(
                    ["lsof", "-ti", f":{port}"], stderr=subprocess.DEVNULL, text=True
                )
                for line in output.splitlines():
                    line = line.strip()
                    if line.isdigit():
                        pids.append(int(line))
        except Exception as err:
            logger.debug(f"PID discovery error on port {port}: {err}")
        return pids

    @staticmethod
    def kill_pid(pid: int) -> bool:
        """Force terminates a PID using platform-specific commands."""
        try:
            if sys.platform == "win32":
                # taskkill /F /PID <pid>
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    check=False
                )
            else:
                import os
                import signal
                os.kill(pid, signal.SIGKILL)
            return True
        except Exception as err:
            logger.warning(f"Failed to kill PID {pid}: {err}")
            return False
