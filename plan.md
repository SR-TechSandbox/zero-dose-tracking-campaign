# Architectural Plan & Delivery Roadmap

## 1. Key Design Principle Alignment

> *"While building a capability for one business application, identifying opportunities to isolate and expose reusable components, APIs, templates, and services so that they can support future applications without compromising the immediate business outcome."*

To satisfy this directly without unnecessary bloat:
* **Decoupled Domain Service (`app/engine.py`):** The zero-dose status transition engine, chronological event replay logic, and transition aggregations are encapsulated in a pure Python domain class with zero dependencies on web frameworks or SQLite drivers. This component can be extracted and reused in routine immunization services, child health registries, or national health information systems.
* **Event-Sourced Historical Integrity:** Status flags are not mutated in place. All changes are derived deterministically from an append-only encounter log, guaranteeing full auditability across campaign rounds.
* **OpenAPI Contract-First Design:** Clean REST contracts decouple the supervisor dashboard, tablet clients, and potential third-party analytics pipelines from internal persistence models.

---

## 2. Solution Architecture & Data Model

```text
+-------------------------------------------------------------+
|                  Client Layer (Thin Web UI)                 |
|   - Supervisor Round Transition Selector & Metrics Table    |
|   - Child Registry, Status Timeline & Encounter Form        |
+------------------------------+------------------------------+
                               | HTTP / JSON
+------------------------------v------------------------------+
|             Application Layer (FastAPI Controllers)         |
|   - GET  /api/rounds                                        |
|   - GET  /api/children                                      |
|   - GET  /api/children/{child_id}                           |
|   - GET  /api/supervisor/transitions?from_round=&to_round=  |
|   - POST /api/encounters                                    |
+------------------------------+------------------------------+
                               | Calls domain logic
+------------------------------v------------------------------+
|            Reusable Domain Engine (zero_dose_engine)        |
|   - evaluate_encounter()                                    |
|   - compute_child_timeline()                                |
|   - get_round_status_map()                                  |
+------------------------------+------------------------------+
                               | Reads / Writes
+------------------------------v------------------------------+
|            Persistence Layer (SQLite Database)              |
|   - children   (child_id, name, dob, guardian, settlement)  |
|   - rounds     (round_id, name, start_date, end_date)       |
|   - encounters (event_id, child_id, round_id, answers...)   |
+-------------------------------------------------------------+
```

### Relational Schema (SQLite)

* `children`: `child_id` (PK, string), `name` (string), `dob` (date), `guardian_name` (string), `settlement` (string)
* `rounds`: `round_id` (PK, string), `name` (string), `start_date` (date), `end_date` (date)
* `encounters`: `event_id` (PK, string), `child_id` (FK, string), `round_id` (FK, string), `device_id` (string), `recorded_at` (ISO timestamp), `type` (enumeration/revisit), `zero_dose_answer` (boolean/null), `vaccinated_since_last` (string/null), `vaccinated_elsewhere` (boolean/null), `comment` (text/null)

---

## 3. Milestones & Delivery Status

- [x] **Milestone 1: Data Ingestion & Auto-Seeding:** Automated parsing and database loading of `children.csv`, `rounds.json`, and `encounters.jsonl` upon startup.
- [x] **Milestone 2: Reusable Domain Engine:** Implementation of `ZeroDoseEngine` handling timestamp ordering, guardian confirmation, and supervisor correction overrides.
- [x] **Milestone 3: REST API & Aggregations:** Creation of child detail, history audit, and cross-round supervisor transition endpoints.
- [x] **Milestone 4: Thin Web Interface:** Responsive supervisor dashboard and child detail inspector built with Tailwind CSS.
- [x] **Milestone 5: Automated Verification Suite:** Integration and unit tests covering edge cases (`C043`, `C027`, null revisits, transition logic).
- [x] **Milestone 6: Single-Command Docker Containerization:** Multi-stage container setup verifying `docker compose up` readiness.

---

## 4. Test Strategy

1. **Ingestion Verification:** Validates that all 60 child records, 3 campaign rounds, and 130 sample encounters load accurately into the SQLite store.
2. **Correction Reversal Test (Child C043):** Tests that an intra-round revisit with a corrective comment supersedes an earlier erroneous vaccination answer, leaving the child flagged as zero-dose.
3. **External Vaccination Transition (Child C016):** Verifies that `vaccinated_elsewhere = true` transitions a child from zero-dose to vaccinated.
4. **Idempotence & Null Resilience (Child C049):** Ensures null revisit answers preserve previous states without generating spurious audit entries.
5. **Supervisor Aggregate Query:** Asserts that transition calculations between R1 and R2 accurately report transitioned children while omitting corrected or non-transitioned records.
6. **Encounter Write Path:** Confirms that recording a new encounter immediately updates the flag and appends an audit event to the child's timeline.

---

## 5. What We'd Do With One More Day

1. **Offline-First Synchronization:** Implement an IndexedDB client cache with a Service Worker to allow field recorders to capture revisits in zero-connectivity environments and sync when a signal is acquired.
2. **Geospatial Settlement Analytics:** Integrate Leaflet/MapLibre to visualize geographic clusters of remaining zero-dose children across settlements to guide supervisor team allocations.
3. **Batch Encounter Ingestion:** Provide a bulk `/api/encounters/batch` endpoint supporting atomic batch inserts and conflict resolution for field devices returning from remote campaign sectors.