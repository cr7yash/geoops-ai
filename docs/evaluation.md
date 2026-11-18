# Agent evaluation

Run `make eval` to execute the labeled suite with local providers. The command exits with code 1 when a configured gate fails. Dataset labels live in `data/evaluation/cases.json`, and minimum metric values live in `data/evaluation/thresholds.json`.

Each case starts with isolated operational state. An evaluation can request an approval without changing the operator's queue. The runner records the dataset SHA-256, provider, model, thresholds, case results, and measured latency. Saved runs appear at `/evaluations` and can be compared against a baseline.

Tool selection uses the intersection over union of expected and observed tool names. Argument accuracy compares the labeled argument subset with validated inputs. Retrieval recall measures the expected document IDs found in the returned sources. Citation correctness measures citation metadata integrity, not semantic truth. Task success also requires expected answer facts, correct approval behavior, and no forbidden tool calls.

Latency percentiles use observed end-to-end case durations with the nearest-rank method. These are local regression measurements, not hosted-service benchmarks. Tokens and estimated cost are null when the provider does not report usage or pricing is not configured. The dashboard displays unavailable measurements as `Not reported`.

`POST /api/evaluations/run` evaluates the configured model provider. The CLI `--local` option selects the deterministic runtime and mock maps for CI. External model evaluations require credentials and have provider-dependent latency and cost.

Firestore or SQLite stores the interactive run records. The analytical relay exports evaluations, agent runs, and dispatch history to BigQuery `audit_records` when `ANALYTICS_PROVIDER=bigquery`. Exports use stable record IDs and MERGE operations so a retry after a crash converges on the same record.
