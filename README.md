# Zero-Dose Campaign Tracker (v0.1)

A cross-round zero-dose child tracking system with audit trail retention, transition analytics for supervisors, and field encounter updates.

## Key Design Principle Alignment

> *"While building a capability for one business application, identifying opportunities to isolate and expose reusable components, APIs, templates, and services so that they can support future applications without compromising the immediate business outcome."*

- **Headless Domain Service (`app/engine.py`):** Core zero-dose business logic, state replay, and transition analytics are decoupled into a standalone Python service free from web framework or database dependencies, allowing immediate reuse across routine immunization or campaign platforms.
- **Event-Sourced Flag History:** Encounters are modeled as immutable historical events. State changes are deterministically derived rather than relying on mutable booleans.
- **Contract-First REST API:** Standardized schemas cleanly isolate storage from web UI clients and downstream consumers.

---

## Quickstart (Single Command)

From the project root directory, run:

```bash
docker compose up --build
```

- **Application Web UI:** http://localhost:8000
- **Interactive API Documentation:** http://localhost:8000/docs

All three data files (`children.csv`, `rounds.json`, `encounters.jsonl`) are automatically ingested and seeded into the SQLite persistence layer at container startup.

---

## Running Tests

To run the full automated verification test suite:

**Inside Docker:**
```bash
docker compose exec zero-dose-tracker pytest
```

**Locally (if Python environment is available):**
```bash
pytest tests/
```

---

## Repository Structure

```text
.
├── Dockerfile
├── docker-compose.yml
├── README.md
├── spec.md
├── plan.md
├── ai-log.md
├── requirements.txt
├── data/
│   ├── children.csv
│   ├── rounds.json
│   └── encounters.jsonl
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI endpoints & static UI mount
│   ├── models.py            # Pydantic schemas & DTOs
│   ├── engine.py            # Headless domain engine (zero-dose state rules)
│   ├── database.py          # SQLite persistence & auto-loader
│   └── static/
│       └── index.html       # Supervisor dashboard & child inspection UI
└── tests/
    ├── __init__.py
    └── test_zero_dose_engine.py
```