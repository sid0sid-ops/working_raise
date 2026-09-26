"""
Self-Contained Okapi BM25 Document Ranking Algorithm
===================================================
An independent, zero-dependency implementation of the Okapi BM25
document ranking algorithm. Completely offline-compatible with active drawer isolation.
"""

from __future__ import annotations

import re
import math
from pathlib import Path
from collections import Counter
from typing import Any, Dict, List, Optional


class SelfContainedBM25:
    """
    An independent, zero-dependency implementation of the Okapi BM25 
    document ranking algorithm. Completely offline-compatible.
    """
    def __init__(self, corpus_chunks: list, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks = corpus_chunks
        self.corpus_size = len(corpus_chunks)
        
        # Tokenize corpus
        self.tokenized_corpus = [self._tokenize(c.get("plain_text") or c.get("text") or "") for c in corpus_chunks]
        self.avg_doc_len = (
            sum(len(doc) for doc in self.tokenized_corpus) / self.corpus_size 
            if self.corpus_size > 0 else 1.0
        )
        
        # Calculate document frequencies
        self.doc_freqs = []
        self.doc_lens = []
        self.df = Counter()
        
        for doc in self.tokenized_corpus:
            self.doc_lens.append(len(doc))
            freqs = Counter(doc)
            self.doc_freqs.append(freqs)
            for word in freqs.keys():
                self.df[word] += 1
                
        # Precompute IDF scores
        self.idf = {}
        for word, freq in self.df.items():
            self.idf[word] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)
            
    def _tokenize(self, text: str) -> list:
        return re.findall(r'\b\w+\b', text.lower())
        
    def search(self, query: str, top_k: int = 6, active_docs: Optional[List[str]] = None) -> list:
        # Strict drawer isolation: If active_docs is explicitly empty, return zero hits
        if active_docs is not None and len(active_docs) == 0:
            return []
        query_tokens = [t for t in self._tokenize(query) if len(t) > 2]
        if not query_tokens:
            return []
            
        scores = []
        for i in range(self.corpus_size):
            chunk = self.chunks[i]
            if active_docs:
                doc_name = str(chunk.get("pdf_filename") or (chunk.get("metadata") or {}).get("pdf_filename") or chunk.get("document_id") or (chunk.get("metadata") or {}).get("doc_id") or "")
                clean_doc = re.sub(r"[^a-zA-Z0-9]", "", doc_name.lower())
                matched_doc = False
                for ad in active_docs:
                    clean_ad = re.sub(r"[^a-zA-Z0-9]", "", str(ad).lower())
                    clean_stem = re.sub(r"[^a-zA-Z0-9]", "", Path(ad).stem.lower())
                    if clean_ad in clean_doc or clean_doc in clean_ad or clean_stem in clean_doc or clean_doc in clean_stem:
                        matched_doc = True
                        break
                if not matched_doc:
                    continue

            score = 0.0
            doc_len = self.doc_lens[i]
            freqs = self.doc_freqs[i]
            
            for token in query_tokens:
                if token in freqs:
                    tf = freqs[token]
                    idf = self.idf.get(token, 0.0)
                    
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                    score += idf * (numerator / denominator)
                    
            if score > 0.0:
                item = dict(chunk)
                item["bm25_score"] = float(score)
                scores.append((score, item))
            
        # Sort descending by BM25 score
        scores.sort(key=lambda x: x[0], reverse=True)
        return [chunk for score, chunk in scores[:top_k]]
