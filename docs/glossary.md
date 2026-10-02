# Glossary

This page defines the project terms. Each term has one meaning in all the documents.

| Term | Meaning |
| --- | --- |
| FinePDFs | The source dataset on Hugging Face. It contains text that comes from PDF files. |
| Record | One row of the dataset. |
| Split | A named part of the dataset. This project uses the `train` split. |
| Streaming mode | A way to read records one by one. The system does not download the full dataset. |
| BM25 | A method that gives a score to each document for a query. |
| Query | The fixed list of words that the system uses to find documents. |
| Score | The number that BM25 gives to a document. A high score shows a close match. |
| Percentile cutoff | The score limit that the system calculates from all scores. The system keeps the records at or above this limit. |
| p99 | The 99th percentile. |
| Proof of concept | A small first version that shows that the method works. |
| Quality gate | The set of checks that the code must pass. |
| Coverage | The part of the code that the tests run. |
| CRAP score | A number that combines the complexity of a function and the test coverage of the function. |
| Mutant | A small change that the tool puts in the code to test the tests. |
| Killed mutant | A mutant that makes at least one test fail. |
| Lockfile | The file `uv.lock`. It records the exact versions of the dependencies. |
