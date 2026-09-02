"""
RAISE Academic GraphRAG Studio — Workspace Root Forwarder
Allows running 'python main.py' directly from either root (raise/) or RAG/
"""

import sys
from pathlib import Path

# Add RAG directory to path and invoke main
RAG_DIR = Path(__file__).resolve().parent / "RAG"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

if __name__ == "__main__":
    from main import main
    main()
