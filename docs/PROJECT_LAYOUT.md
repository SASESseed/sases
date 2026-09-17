\# SASES Project Layout



\## Rule: Root Directory is Frozen



The root directory only contains:



\- `app\_full.py` — the single entry point

\- `config.py` — config forwarder

\- `README.md`, `LICENSE`, `requirements.txt`

\- `.env`, `.env.example`, `.gitignore`

\- `RELEASE\_NOTES\_\*.md`



\*\*No new `.py` files may be added to the root directory.\*\*



\## Where New Scripts Go



| Script purpose | Location |

|---------------|----------|

| Data preparation / training data | `scripts/data/` |

| Model training / fine-tuning / upload | `scripts/model/` |

| Evaluation / benchmarks | `scripts/eval/` |

| One-off debug tools | `tools/` |

| Ops / deployment | `scripts/ops/` |

| Documentation | `docs/` |

| Archived old scripts | `archive\_v1/` |



\## How to Run Scripts



Always run from the project root:



&#x20;   cd C:\\Users\\xiaomai\\sases

&#x20;   python scripts\\data\\build\_benchmark.py

&#x20;   python tools\\test\_swarm.py



Do NOT `cd` into subdirectories — scripts use paths relative to the project root.



\## Directory Overview



&#x20;   sases/

&#x20;   ├── app\_full.py                 # Entry point

&#x20;   ├── config.py                   # Config forwarder

&#x20;   ├── core/                       # Backend logic

&#x20;   ├── static/                     # Frontend

&#x20;   ├── harness\_modules/            # Hand-written Harness tools

&#x20;   ├── scripts/                    # Ops \& data scripts

&#x20;   │   ├── data/                   # Data preparation

&#x20;   │   ├── model/                  # Model training

&#x20;   │   ├── eval/                   # Evaluation

&#x20;   │   └── ops/                    # Deployment

&#x20;   ├── tools/                      # Debug tools

&#x20;   ├── evaluation/                 # Eval reports

&#x20;   ├── docs/                       # Documentation

&#x20;   └── archive\_v1/                 # Historic archive

