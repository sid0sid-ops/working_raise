"""
Repair OCR Artifacts in Scanned Academic Report Chunks
=====================================================
Fixes noisy OCR tokens in financial schedules (ISM Dhanbad Schedule 12)
and updates ChromaDB vector store so BM25 and vector retrieval match cleanly.
"""

import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.infrastructure.vector.chroma import ChromaDBEngine


REPLACEMENTS = [
    (r"Penalbrom\s+Contieclon\s+Supplers", "Penalty from Contractors/Suppliers"),
    (r"Petalb[_\s]+lro\s+Con\s*raclor\s+SupeLers", "Penalty from Contractors/Suppliers"),
    (r"Schod\s+suppodlrom\s+ConsullancyPiokdls", "School support from Consultancy / Projects"),
    (r"\[ch\s*42:OTHERINcOME", "Schedule 12: Other Income"),
    (r"\[62,06,35100", "Rs. 62,06,351.00"),
    (r"4153306\s*g\[", "Rs. 14,53,306.00"),
    (r"1453,30\.00", "Rs. 14,53,306.00"),
]

def repair_text(text: str) -> str:
    if not text:
        return ""
    res = text
    for pat, repl in REPLACEMENTS:
        res = re.sub(pat, repl, res, flags=re.IGNORECASE)
    return res

def main():
    chunks_dir = Path("data/processed/chunks")
    for f in chunks_dir.glob("AR_2024_25_Combined_English_Mail*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            modified = False
            for item in data:
                if isinstance(item, dict):
                    for k in ["plain_text", "text", "contextualized_content", "enriched_text"]:
                        if k in item and item[k]:
                            new_val = repair_text(item[k])
                            if new_val != item[k]:
                                item[k] = new_val
                                modified = True
            if modified:
                f.write_text(json.dumps(data, indent=2), encoding="utf-8")
                print(f"Repaired OCR artifacts in: {f.name}")
        except Exception as e:
            print(f"Error repairing {f.name}: {e}")

    # Sync repaired chunks to ChromaDB
    chroma = ChromaDBEngine()
    c_file = chunks_dir / "AR_2024_25_Combined_English_Mail_chunks.json"
    if c_file.exists():
        chunks = json.loads(c_file.read_text(encoding="utf-8"))
        # Delete old chunks for this doc and re-ingest
        chroma.delete_document("AR_2024-25_Combined_English_Mail.pdf")
        count = chroma.ingest_chunks(chunks, doc_id="AR_2024_25_Combined_English_Mail")
        print(f"Re-indexed {count} repaired chunks in ChromaDB.")

if __name__ == "__main__":
    main()
