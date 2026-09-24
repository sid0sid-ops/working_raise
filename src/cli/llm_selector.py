"""
RAISE — Interactive LLM Inference Selector
Enables users to choose between local GPU inference (vLLM) and Cloud LLM APIs (Groq, Gemini, DeepSeek)
with graceful auto-fallback when running on machines without local GPU/vLLM.
"""

from __future__ import annotations

import os
import sys
import logging
from typing import Optional, Tuple, Dict, Any

from src.cli.renderer import C
from src.infrastructure.providers.diagnostics import ProviderDiagnostics
from src.infrastructure.providers.router import get_provider_router, ExecutionMode, InferenceTask

logger = logging.getLogger("raise.cli.llm_selector")


def prompt_llm_backend(headless: bool = False, default_provider: Optional[str] = None) -> str:
    """
    Prompts the user to select an LLM backend (Local vLLM vs Cloud APIs).
    If headless or non-interactive, uses environment or healthy cloud fallback.
    """
    router = get_provider_router()
    env_backend = (os.getenv("LLM_BACKEND") or "").lower().strip()

    # Check CLI arguments first
    for i, arg in enumerate(sys.argv):
        if arg in ("--llm", "--provider", "-p") and i + 1 < len(sys.argv):
            selected = sys.argv[i + 1].lower().strip()
            _apply_provider_choice(selected, router)
            return selected

    # Check environment variable
    if env_backend in ("groq", "gemini", "deepseek", "vllm", "nvidia", "cohere"):
        _apply_provider_choice(env_backend, router)
        return env_backend

    if default_provider:
        _apply_provider_choice(default_provider, router)
        return default_provider

    # Quick diagnostic probe
    diag = ProviderDiagnostics()
    health_map = diag.run_all(timeout=3.0)

    vllm_ready = bool(health_map.get("Local vLLM") and health_map["Local vLLM"].endpoint_reachable)
    groq_ready = bool(health_map.get("Groq") and health_map["Groq"].credential_valid)
    gemini_ready = bool(health_map.get("Google Gemini") and health_map["Google Gemini"].credential_valid)
    deepseek_ready = bool(health_map.get("DeepSeek") and health_map["DeepSeek"].credential_valid)
    nvidia_ready = bool(health_map.get("NVIDIA NIM") and health_map["NVIDIA NIM"].credential_valid)
    cohere_ready = bool(health_map.get("Cohere") and health_map["Cohere"].credential_valid)
    openrouter_ready = bool(health_map.get("OpenRouter") and health_map["OpenRouter"].credential_valid)

    if headless or not sys.stdin.isatty():
        # Non-interactive / headless environment
        choice = (
            "groq" if groq_ready
            else ("gemini" if gemini_ready
            else ("nvidia" if nvidia_ready
            else ("openrouter" if openrouter_ready
            else ("cohere" if cohere_ready
            else ("deepseek" if deepseek_ready
            else ("vllm" if vllm_ready else "groq"))))))
        )
        _apply_provider_choice(choice, router)
        return choice

    # Interactive Terminal Menu
    print("\n" + C.BANNER + "╔" + "═" * 74 + "╗" + C.RESET)
    print(f"{C.BANNER}║{C.RESET} {C.TITLE}🤖  RAISE MULTI-BACKEND AI INFERENCE SELECTOR{C.RESET}{' ' * 27}{C.BANNER}║{C.RESET}")
    print(f"{C.BANNER}║{C.RESET} {C.MUTED}Select your LLM engine. Works offline on GPU or via free Cloud APIs.{C.RESET}{' ' * 4}{C.BANNER}║{C.RESET}")
    print(C.BANNER + "╠" + "═" * 74 + "╣" + C.RESET)

    vllm_badge = f"{C.SUCCESS}[ONLINE]{C.RESET}" if vllm_ready else f"{C.WARN}[OFFLINE / GPU REQUIRED]{C.RESET}"
    groq_badge = f"{C.SUCCESS}[READY - RECOMMENDED]{C.RESET}" if groq_ready else f"{C.MUTED}[KEY NEEDED]{C.RESET}"
    gemini_badge = f"{C.SUCCESS}[READY]{C.RESET}" if gemini_ready else f"{C.MUTED}[KEY NEEDED]{C.RESET}"
    deepseek_badge = f"{C.SUCCESS}[READY]{C.RESET}" if deepseek_ready else f"{C.MUTED}[KEY NEEDED]{C.RESET}"
    nvidia_badge = f"{C.SUCCESS}[READY]{C.RESET}" if nvidia_ready else f"{C.MUTED}[KEY NEEDED]{C.RESET}"
    cohere_badge = f"{C.SUCCESS}[READY]{C.RESET}" if cohere_ready else f"{C.MUTED}[KEY NEEDED]{C.RESET}"
    openrouter_badge = f"{C.SUCCESS}[READY]{C.RESET}" if openrouter_ready else f"{C.MUTED}[KEY NEEDED]{C.RESET}"

    print(f"{C.BANNER}║{C.RESET}  {C.NUM}1.{C.RESET} {C.BOLD}Local vLLM Engine{C.RESET} (Qwen 2.5 14B)   — {vllm_badge}")
    print(f"{C.BANNER}║{C.RESET}  {C.NUM}2.{C.RESET} {C.BOLD}Groq Cloud API{C.RESET}    (Ultra-fast LPU)   — {groq_badge}")
    print(f"{C.BANNER}║{C.RESET}  {C.NUM}3.{C.RESET} {C.BOLD}Google Gemini API{C.RESET} (Gemini 3.8 Flash) — {gemini_badge}")
    print(f"{C.BANNER}║{C.RESET}  {C.NUM}4.{C.RESET} {C.BOLD}DeepSeek API{C.RESET}      (DeepSeek-V3/R1)   — {deepseek_badge}")
    print(f"{C.BANNER}║{C.RESET}  {C.NUM}5.{C.RESET} {C.BOLD}NVIDIA NIM API{C.RESET}    (Llama/GLM)        — {nvidia_badge}")
    print(f"{C.BANNER}║{C.RESET}  {C.NUM}6.{C.RESET} {C.BOLD}Cohere API{C.RESET}        (Command R+)       — {cohere_badge}")
    print(f"{C.BANNER}║{C.RESET}  {C.NUM}7.{C.RESET} {C.BOLD}OpenRouter API{C.RESET}    (GPT-4o/Omni)      — {openrouter_badge}")
    print(C.BANNER + "╚" + "═" * 74 + "╝" + C.RESET)

    default_choice = (
        "2" if groq_ready
        else ("3" if gemini_ready
        else ("1" if vllm_ready
        else ("5" if nvidia_ready
        else ("7" if openrouter_ready
        else ("6" if cohere_ready else "2")))))
    )
    prompt = f"\n👉 Choose backend [1-7] (default: {default_choice}): "

    try:
        user_input = input(prompt).strip() or default_choice
    except (EOFError, KeyboardInterrupt):
        user_input = default_choice

    mapping = {
        "1": "vllm", "vllm": "vllm",
        "2": "groq", "groq": "groq",
        "3": "gemini", "gemini": "gemini",
        "4": "deepseek", "deepseek": "deepseek",
        "5": "nvidia", "nvidia": "nvidia", "nim": "nvidia",
        "6": "cohere", "cohere": "cohere",
        "7": "openrouter", "openrouter": "openrouter",
    }
    chosen = mapping.get(user_input.lower(), "groq")
    _apply_provider_choice(chosen, router)
    print(f"{C.SUCCESS}✨ Configured Inference Backend:{C.RESET} {C.ACCENT}{chosen.upper()}{C.RESET}\n")
    return chosen


def _apply_provider_choice(provider_name: str, router: Any) -> None:
    """Configures the singleton provider router with chosen backend."""
    prov = provider_name.lower().strip()
    os.environ["LLM_BACKEND"] = prov

    if prov == "vllm":
        router.set_execution_mode(ExecutionMode.LOCAL)
        router.set_task_provider(InferenceTask.RAG_GENERATION, "vllm")
        router.set_task_provider(InferenceTask.CHAT, "vllm")
    else:
        router.set_execution_mode(ExecutionMode.CLOUD)
        router.set_cloud_allowed(True)
        router.set_task_provider(InferenceTask.RAG_GENERATION, prov)
        router.set_task_provider(InferenceTask.CHAT, prov)
        all_cloud = [prov, "groq", "gemini", "nvidia", "openrouter", "cohere", "deepseek", "vllm"]
        seen = set()
        deduped = [x for x in all_cloud if not (x in seen or seen.add(x))]
        router.fallback_chain = deduped


def show_simple_gui_prompt() -> Optional[str]:
    """Displays a lightweight tkinter dialog for selecting inference backend."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.title("RAISE — Inference Engine Selector")
        root.geometry("500x400")
        root.resizable(False, False)

        selected = tk.StringVar(value="groq")

        tk.Label(root, text="Select RAISE Inference Backend", font=("Arial", 14, "bold")).pack(pady=10)
        tk.Label(root, text="Run fully offline with a local GPU, or use free Cloud API keys:", font=("Arial", 9)).pack(pady=5)

        frame = tk.Frame(root)
        frame.pack(pady=10, padx=20, fill="both")

        tk.Radiobutton(frame, text="1. Local vLLM (Offline - RTX GPU required)", variable=selected, value="vllm", font=("Arial", 10)).pack(anchor="w", pady=3)
        tk.Radiobutton(frame, text="2. Groq Cloud API (Free & Fast LPU) [Recommended]", variable=selected, value="groq", font=("Arial", 10, "bold")).pack(anchor="w", pady=3)
        tk.Radiobutton(frame, text="3. Google Gemini API (Gemini 3.8 Flash)", variable=selected, value="gemini", font=("Arial", 10)).pack(anchor="w", pady=3)
        tk.Radiobutton(frame, text="4. DeepSeek API (Cloud)", variable=selected, value="deepseek", font=("Arial", 10)).pack(anchor="w", pady=3)
        tk.Radiobutton(frame, text="5. NVIDIA NIM API (Llama/GLM Cloud)", variable=selected, value="nvidia", font=("Arial", 10)).pack(anchor="w", pady=3)
        tk.Radiobutton(frame, text="6. Cohere API (Command R+)", variable=selected, value="cohere", font=("Arial", 10)).pack(anchor="w", pady=3)
        tk.Radiobutton(frame, text="7. OpenRouter API (GPT-4o / Multi-Model)", variable=selected, value="openrouter", font=("Arial", 10)).pack(anchor="w", pady=3)

        def on_confirm():
            root.destroy()

        tk.Button(root, text="Confirm & Launch", command=on_confirm, bg="#2563EB", fg="white", font=("Arial", 10, "bold"), padx=15, pady=5).pack(pady=10)

        root.mainloop()
        choice = selected.get()
        _apply_provider_choice(choice, get_provider_router())
        return choice
    except Exception as e:
        logger.debug(f"GUI selector unavailable: {e}. Falling back to CLI prompt.")
        return prompt_llm_backend()
