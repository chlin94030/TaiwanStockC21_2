# V21 Universe Lab - engineering test scope

## Status

The delivered program implements the finite research procedure. NO real full-market Top100/200/300/500 financial-performance result, optimal factor weight, or production-trading certification was obtained in this environment.

## Unit and integration suite

46 tests passed (latest pre-packaging run:5.46 seconds). Tests include deterministic sparse registries;252-session actual-amount logic; nested pool membership; future amount/feature/PIT mutations; future-outcome selection invariance; missing exits; suspended benchmark handling; capacity and no-fill cash slots; no price-times-volume substitution; imported scope/ZIP guards; label-maturity purge; held-out outcome mutation not changing training choice; global non-overlap; scalar/batch parity; small end-to-end synthetic output; validated resume; and ZIP CRC checks. The final packaging run is recorded in QA_TEST_LOG.txt and QA_JUNIT.xml.

## Completed default-size synthetic scale test

- 520 synthetic stocks plus0050;2,200 synthetic market sessions.
- 1,146,200 normalized input rows.
- Pools100/200/300/500,64profiles and5/20/60 horizons.
- 24-month training minimum,6-month outer blocks,24-month final tail.
- Outer blocks evaluated:7/5/5 for5/20/60 respectively.
- Completed final measured pass:34.79 seconds, peak process RSS291.7MB.
- This is a WARM INPUT-CACHE computation: the1.15m-row CSV had already been imported into SQLite by an earlier interrupted attempt. Feature/outcome preparation, grid evaluation, nested search and report export completed in the measured pass. No network was used and the CSV-generation/import time is NOT included.
- Bootstrap repetitions were200 for this scale test, versus2,000 in the default real protocol. Do not extrapolate the34.79s to a cold import, a2,000-repetition run, whole-market collection or Cloud performance.
- Earlier scale attempts encountered execution timeouts while the implementation was being optimized; only the final completed pass is reported as passed.
- Every synthetic horizon verdict is explicitly SYNTHETIC_ENGINE_TEST_NOT_PERFORMANCE. Synthetic winners or returns are not investment evidence.

## Tested environment

Core tests executed with NumPy2.3.5, pandas2.2.3, requests2.32.5 and pytest9.0.2. Python version and final package manifests are recorded separately. Streamlit1.50.0 and yfinance0.2.66 are declared deployment dependencies; they were NOT installed/exercised in a real Cloud browser in this environment. Their call contracts were checked against documentation and pure parsing fixtures.

## Not completed / limits

Live container API access failed at network/DNS level. The code's official TWSE/TPEx, FinMind and Yahoo fetching sequence has NOT completed a real-provider end-to-end smoke test here. API schemas, quota behavior and permissions can change. The user must inspect actual SOURCE/BLOCKED status, not assume engineering tests certify current endpoint availability.

The default automatic source uses the whole CURRENT official roster, not complete historical membership. Historical delistings, listing-board transfers, corporate-action revision vintages and PIT fundamental provenance are not reconstructed. Optional cap/fundamental tests require supplied timestamped data. Default price-only results do not verify those factors.

No selected new model has been shown to beat0050, no claim of a best live universe is made, and no code automatically authorizes orders. The prior150-stock report is not used as a substitute for all-market input.
