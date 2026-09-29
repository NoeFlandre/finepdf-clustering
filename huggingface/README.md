---
pretty_name: Agriculture BM25 retrieval results
license: odc-by
language:
  - en
size_categories:
  - n<1K
tags:
  - agriculture
  - bm25
  - finepdfs
configs:
  - config_name: default
    data_files:
      - split: train
        path: agriculture_bm25_p99_5000.csv
---

# Agriculture BM25 retrieval results

A small proof of concept that ranks agriculture-related PDFs from the English FinePDFs training split. Scores are ranking values, not relevance probabilities or manually judged labels.

## Files

- [`agriculture_bm25_p99_5000.csv`](agriculture_bm25_p99_5000.csv): all 50 records retained by the 99th-percentile filter over the first 5,000 streamed records.
- [`agriculture_bm25_p99_5000.metrics.json`](agriculture_bm25_p99_5000.metrics.json): the score cutoff, record counts, and measured stage timings for the 5,000-record run.

The CSV contains `bm25_score`, `pdf_url`, and `text_preview`; previews are limited to 300 characters. Results are sorted by descending score.

## Method

- Source: [`HuggingFaceFW/finepdfs`](https://huggingface.co/datasets/HuggingFaceFW/finepdfs), config `eng_Latn`, split `train`.
- Read only the requested prefix in Hugging Face `datasets` streaming mode; the source dataset is not downloaded.
- Use the extracted `text` field and retain `url` when available.
- Query: `agriculture crop wheat maize rice soil irrigation plant disease farming harvest`.
- Tokenize with lowercase regex word splitting and score with `rank-bm25` BM25Okapi.
- For the 5,000-record run, compute the linearly interpolated 99th percentile from all BM25 scores, then keep positive scores at or above the cutoff. Ties can retain more than one percent of records.

The recorded p99 cutoff is `15.913687525759888`; 50 of 5,000 records were retained.

## Observed timing

One run on 2026-09-29 took 11.054973 seconds overall, or 452.285 documents per second. The times include network streaming and depend on the runtime and connection.

| Stage | Seconds |
| --- | ---: |
| Dataset initialization | 4.675616 |
| Streaming 5,000 records | 3.265685 |
| BM25 scoring and filtering | 3.112621 |
| CSV output | 0.001052 |
| Total | 11.054973 |

Total includes CSV output and excludes console output and writing the metrics JSON.

## Attribution and scope

The FinePDFs Hub metadata declares the source dataset license as ODC-By. Source URLs are retained for attribution; underlying PDFs may have their own terms. This is a small sample from the start of the English training split and is not a relevance benchmark.
