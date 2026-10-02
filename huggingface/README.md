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

This is a small proof of concept. It ranks agriculture PDFs from the English FinePDFs training split. The scores are ranking values. They are not relevance probabilities. They are not manually judged labels.

## Files

- [`agriculture_bm25_p99_5000.csv`](agriculture_bm25_p99_5000.csv): the 50 records that the 99th-percentile filter keeps from the first 5,000 streamed records.
- [`agriculture_bm25_p99_5000.metrics.json`](agriculture_bm25_p99_5000.metrics.json): the score cutoff, the record counts, and the measured stage times for the 5,000-record run.

The CSV file contains `bm25_score`, `pdf_url`, and `text_preview`. A preview has a maximum of 300 characters. The rows are in descending order of score.

## Method

- Source: [`HuggingFaceFW/finepdfs`](https://huggingface.co/datasets/HuggingFaceFW/finepdfs), config `eng_Latn`, split `train`.
- Read only the requested prefix in Hugging Face `datasets` streaming mode. The system does not download the source dataset.
- Use the extracted `text` field. Keep `url` when it is available.
- Query: `agriculture crop wheat maize rice soil irrigation plant disease farming harvest`.
- Split the text into tokens with a lowercase regex word splitter. Score the tokens with `rank-bm25` BM25Okapi.
- For the 5,000-record run, calculate the linearly interpolated 99th percentile of all BM25 scores. Then keep the positive scores at or above the cutoff. Tied scores can keep more than one percent of the records.

The recorded p99 cutoff is `15.913687525759888`. The run kept 50 of 5,000 records.

## Observed timing

One run on 2026-09-29 took 11.054973 seconds in total. This is 452.285 documents per second. The times include the network streaming time. The times change with the runtime and the connection.

| Stage | Seconds |
| --- | ---: |
| Dataset initialization | 4.675616 |
| Streaming 5,000 records | 3.265685 |
| BM25 scoring and filtering | 3.112621 |
| CSV output | 0.001052 |
| Total | 11.054973 |

The total includes the CSV output. It excludes the console output and the write of the metrics JSON.

## Attribution and scope

The FinePDFs Hub metadata declares the license of the source dataset as ODC-By. The files keep the source URLs for attribution. The underlying PDFs can have their own terms. This is a small sample from the start of the English training split. It is not a relevance benchmark.
