# Local RAG Factory

A network-free retrieval-augmented generation pipeline. It normalizes a local
Markdown knowledge base, chunks documents, builds a hashed TF-IDF vector index,
retrieves evidence for a benchmark question set, and produces grounded answers
with citations. The deterministic extractive generator is useful for CI; an
Ollama adapter can be added without changing the workflow boundaries.

Run `./run.sh`. The corpus and evaluation questions are versioned under `data/`.

