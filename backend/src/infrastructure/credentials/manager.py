"""
RAISE Infrastructure — Secure Credential Manager
Implements layered credential management using:
1. Process OS Environment Variables
2. Local Secure OS Store (Windows Credential Locker / DPAPI via keyring)
3. Untracked .env file fallback

Strictly enforces zero plaintext secret leakage across logs, exceptions, and serialization.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("raise.infrastructure.credentials")

# Secure keyring service identifier
KEYRING_SERVICE_NAME = "raise.ai.runtime"

# Known supported provider identifier mapping to primary env var names
PROVIDER_ENV_MAPPING: Dict[str, List[str]] = {
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "nvidia": ["NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY"],
    "cohere": ["COHERE_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "vllm": ["VLLM_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"],
}


class CredentialManager:
    """
    Secure OS-backed credential manager for multi-backend AI inference.
    Prevents secret leakage and ensures credentials persist safely in Windows Credential Locker.
    """

    def __init__(self, service_name: str = KEYRING_SERVICE_NAME, env_file_path: Optional[Path] = None):
        self.service_name = service_name
        self.env_file_path = env_file_path or (Path(__file__).resolve().parents[3] / ".env")
        self._keyring = None
        self._init_keyring()

    def _init_keyring(self) -> None:
        """Initialize the OS keyring backend safely."""
        try:
            import keyring
            self._keyring = keyring
        except Exception as e:
            logger.debug(f"Keyring initialization notice: {e}. Falling back to environment variables.")
            self._keyring = None

    def get_credential(self, provider: str) -> Optional[str]:
        """
        Retrieve credential for a provider following strict resolution precedence:
        1. Process OS Environment Variables
        2. Windows Credential Locker (DPAPI via keyring)
        3. Untracked .env file fallback
        Returns raw secret in-memory only. Never logs or prints the secret.
        """
        prov = provider.lower().strip()
        env_vars = PROVIDER_ENV_MAPPING.get(prov, [f"{prov.upper()}_API_KEY"])

        # 1. Check OS Environment Variables
        for var in env_vars:
            val = os.environ.get(var)
            if val and val.strip() and not val.strip().startswith("your_") and val.strip() != "placeholder":
                return val.strip()

        # 2. Check Windows Credential Locker
        if self._keyring:
            try:
                secret = self._keyring.get_password(self.service_name, prov)
                if secret and secret.strip():
                    return secret.strip()
            except Exception as e:
                logger.debug(f"Secure store query failed for provider {prov}: {e}")

        # 3. Check Untracked .env file fallback
        if self.env_file_path and self.env_file_path.exists():
            try:
                from dotenv import dotenv_values
                vals = dotenv_values(self.env_file_path)
                for var in env_vars:
                    val = vals.get(var)
                    if val and val.strip() and not val.strip().startswith("your_") and val.strip() != "placeholder":
                        return val.strip()
            except Exception as e:
                logger.debug(f"Failed to read local .env fallback: {e}")

        return None

    def set_credential(self, provider: str, secret: str) -> bool:
        """
        Store credential in the Windows Credential Locker.
        Also sets process environment variable for the current runtime session.
        Returns True on success.
        """
        prov = provider.lower().strip()
        if not secret or not secret.strip():
            return False

        clean_secret = secret.strip()

        # Update current process environment
        primary_var = PROVIDER_ENV_MAPPING.get(prov, [f"{prov.upper()}_API_KEY"])[0]
        os.environ[primary_var] = clean_secret

        # Store into Windows Credential Locker
        if self._keyring:
            try:
                self._keyring.set_password(self.service_name, prov, clean_secret)
                logger.info(f"Credential securely persisted in Windows Credential Locker for provider: {prov}")
                return True
            except Exception as e:
                logger.error(f"Failed to persist credential to Windows Credential Locker for {prov}: {e}")
                return False
        return True

    def delete_credential(self, provider: str) -> bool:
        """
        Remove credential from Windows Credential Locker and current process environment.
        """
        prov = provider.lower().strip()

        # Clear process environment
        for var in PROVIDER_ENV_MAPPING.get(prov, [f"{prov.upper()}_API_KEY"]):
            if var in os.environ:
                del os.environ[var]

        # Delete from Windows Credential Locker
        if self._keyring:
            try:
                self._keyring.delete_password(self.service_name, prov)
                logger.info(f"Credential removed from Windows Credential Locker for provider: {prov}")
                return True
            except Exception as e:
                logger.debug(f"Credential deletion notice for {prov}: {e}")
                return False
        return True

    def get_credential_status(self, provider: str) -> str:
        """
        Safe status inspection. Returns 'configured' or 'missing'.
        NEVER returns partial tokens, lengths, or hints.
        """
        val = self.get_credential(provider)
        if val is None or not val.strip():
            return "missing"
        if val.strip().startswith("your_") or val.strip().lower() == "placeholder":
            return "placeholder"
        return "configured"

    def get_credential_source(self, provider: str) -> str:
        """
        Returns source of credential ('environment', 'keyring', '.env', or 'none').
        Useful for operator inspection without revealing secrets.
        """
        prov = provider.lower().strip()
        env_vars = PROVIDER_ENV_MAPPING.get(prov, [f"{prov.upper()}_API_KEY"])

        for var in env_vars:
            val = os.environ.get(var)
            if val and val.strip() and not val.strip().startswith("your_"):
                return "environment"

        if self._keyring:
            try:
                secret = self._keyring.get_password(self.service_name, prov)
                if secret and secret.strip():
                    return "keyring (DPAPI)"
            except Exception:
                pass

        if self.env_file_path and self.env_file_path.exists():
            try:
                from dotenv import dotenv_values
                vals = dotenv_values(self.env_file_path)
                for var in env_vars:
                    val = vals.get(var)
                    if val and val.strip() and not val.strip().startswith("your_"):
                        return ".env file"
            except Exception:
                pass

        return "none"

    def list_all_statuses(self) -> Dict[str, Dict[str, str]]:
        """
        Enumerate all supported providers and their masked status & source.
        Zero secret leakage guarantee.
        """
        result = {}
        for prov in PROVIDER_ENV_MAPPING.keys():
            result[prov] = {
                "status": self.get_credential_status(prov),
                "source": self.get_credential_source(prov),
            }
        return result


# Module singleton
_manager_instance: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    """Return singleton CredentialManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = CredentialManager()
    return _manager_instance
