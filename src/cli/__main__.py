"""
RAISE Command Line Interface — Runtime & Diagnostics Subcommands
Entry point for:
  python -m src.cli runtime diagnostics
  python -m src.cli runtime credentials [list|set|delete]
  python -m src.cli runtime gui
"""

from __future__ import annotations

import sys
import getpass
from src.infrastructure.credentials.manager import get_credential_manager
from src.infrastructure.providers.diagnostics import run_provider_diagnostics, ProviderDiagnostics


def print_usage():
    print("RAISE Multi-Backend Runtime CLI")
    print("Usage:")
    print("  python -m src.cli runtime diagnostics              Run connectivity & health checks")
    print("  python -m src.cli runtime credentials list         View masked credential statuses")
    print("  python -m src.cli runtime credentials set <name>   Store API key in Windows Locker")
    print("  python -m src.cli runtime credentials delete <name> Remove API key from Windows Locker")
    print("  python -m src.cli runtime control-center           Launch Neural Model Control Center (OLED Black)")
    print("  python -m src.cli runtime gui                      Alias for control-center")


def handle_credentials(args: list[str]):
    mgr = get_credential_manager()
    if not args or args[0] == "list":
        print("\n================ SECURE CREDENTIAL STATUS ================")
        statuses = mgr.list_all_statuses()
        for prov, info in sorted(statuses.items()):
            print(f"  {prov:<12} : {info['status'].upper():<12} (Source: {info['source']})")
        print("==========================================================\n")
        print("Note: Raw keys are never displayed or stored in plaintext.")
    elif args[0] == "set":
        if len(args) < 2:
            print("Error: Specify provider name (e.g. gemini, groq, deepseek, nvidia, cohere)")
            return
        prov = args[1].lower().strip()
        secret = getpass.getpass(f"Enter API key for {prov} (input hidden): ")
        if not secret or not secret.strip():
            print("Cancelled: Empty input provided.")
            return
        if mgr.set_credential(prov, secret):
            print(f"Success: Credential for '{prov}' securely stored in Windows Credential Locker.")
        else:
            print(f"Error: Failed to store credential for '{prov}'.")
    elif args[0] == "delete":
        if len(args) < 2:
            print("Error: Specify provider name (e.g. gemini, groq, deepseek, nvidia, cohere)")
            return
        prov = args[1].lower().strip()
        if mgr.delete_credential(prov):
            print(f"Success: Credential for '{prov}' deleted from Windows Credential Locker.")
        else:
            print(f"Notice: No stored credential found for '{prov}'.")
    else:
        print(f"Unknown credential action: {args[0]}")


def handle_gui():
    try:
        from src.gui.control_panel import launch_operator_gui
        launch_operator_gui()
    except Exception as e:
        print(f"Error launching GUI: {e}")


def main():
    args = sys.argv[1:]
    if not args:
        print_usage()
        return

    if args[0] == "runtime":
        sub = args[1:]
        if not sub:
            print_usage()
            return
        if sub[0] == "diagnostics":
            print("\nRunning provider diagnostics (probing local and cloud endpoints)...")
            table = run_provider_diagnostics(timeout=4.0)
            print(table)
            print()
        elif sub[0] == "credentials":
            handle_credentials(sub[1:])
        elif sub[0] in ("control-center", "ops", "gui"):
            handle_gui()
        else:
            print(f"Unknown runtime command: {sub[0]}")
            print_usage()
    else:
        print_usage()


if __name__ == "__main__":
    main()
