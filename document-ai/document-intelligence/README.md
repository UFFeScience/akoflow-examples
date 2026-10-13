# Document Intelligence

An offline document-processing workload over a small synthetic procurement
dataset. It ingests semi-structured text invoices, classifies them, extracts
fields, reconciles totals, detects duplicate invoice numbers, and emits an
auditable JSONL/CSV report. It uses only Python's standard library.

Run `./run.sh`. The files in `data/documents/` are the versioned test dataset.
Replace that directory with a larger local corpus to create a long-running run.

