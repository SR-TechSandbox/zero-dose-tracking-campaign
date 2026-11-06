# Specification & Ambiguity Resolution: Zero-Dose Cross-Round Tracking

## 1. Problem Restatement
In field vaccination campaigns, a "zero-dose child" is defined as a child who has never received any routine vaccine dose. Identifying these children and ensuring they receive vaccinations across consecutive campaign rounds represents the campaign's highest-value intervention.

Supervisors and campaign coordinators require:
1. Cross-round persistence of a child's zero-dose flag.
2. Complete audit history of every status evaluation and change with source provenance and timestamps.
3. Field encounter ingestion supporting "vaccinated since last campaign?" updates (including external guardian confirmations).
4. An aggregate supervisor metric showing how many children moved from zero-dose to vaccinated between any selectable pair of consecutive rounds.

---

## 2. Identified Ambiguities, Sample Data Inconsistencies & Resolutions

### 2.1 Intra-Round Corrections & Contradictions (e.g., Child C043)
* **Observed Data:** In Round 2 (R2), child `C043` has encounter `E0070` answering `vaccinated_since_last = "yes"`. Later in the same round, encounter `E0094` records `vaccinated_since_last = "no"` with comment: *"correcting earlier entry - vaccination card shown was sibling's"*.
* **Ambiguity:** Should vaccination status be strictly monotonic (once vaccinated, never zero-dose), or can human/clerical errors be corrected in field operations?
* **Resolution:** Field operations require correction capabilities. Encounters are sorted chronologically by `recorded_at`. An explicit negative answer with a correction comment resets the child's status back to Zero-Dose (`true`) for that round. Both events remain preserved in the immutable audit trail. Child `C043` finishes R2 as Zero-Dose and is not counted as transitioned.

### 2.2 Intra-Round Duplicate Revisit Encounters (e.g., Child C027)
* **Observed Data:** In R2, child `C027` has two encounters: `E0078` ("yes") at 09:40 and `E0081` ("no") at 13:55.
* **Ambiguity:** Which encounter reflects round-level ground truth?
* **Resolution:** The deterministic event-replay engine evaluates encounters chronologically. The last recorded encounter before the round cut-off represents the child's effective status for that round.

### 2.3 Unanswered / Null Revisit Records
* **Observed Data:** 37 revisit encounters across R2 and R3 have `vaccinated_since_last = null`.
* **Ambiguity:** Does an encounter with no vaccination response imply unvaccinated, missing data, or an absent child?
* **Resolution:** Revisit encounters without a definitive "yes" or confirmed external vaccination preserve the child's prior zero-dose flag. The encounter is persisted to record field presence, but no state change event is emitted to prevent false transitions.

### 2.4 External Vaccination Confirmation (`vaccinated_elsewhere`)
* **Observed Data:** Encounters like `E0061` (child `C016`) have `vaccinated_since_last = "yes"` and `vaccinated_elsewhere = true`.
* **Ambiguity:** How should vaccinations administered outside the official campaign be classified?
* **Resolution:** Guardian-confirmed external vaccination satisfies immunization. The child transitions from Zero-Dose (`true`) to Vaccinated (`false`), tagged with `confirmation_method = "External (Vaccinated Elsewhere)"`.

### 2.5 Round-to-Round Transition Definition
* **Ambiguity:** What qualifies a child as having "moved from zero-dose to vaccinated between rounds"?
* **Resolution:** A child is counted in the supervisor transition aggregate from Round A to Round B if and only if:
  1. The child's effective status at the end of Round A was Zero-Dose (`true`).
  2. The child's effective status at the end of Round B was Vaccinated (`false`).

---

## 3. Explicit Out-of-Scope List
1. Multi-tenant authentication, authorization, and RBAC roles.
2. Direct hardware barcode/QR scanning integration.
3. Offline peer-to-peer mesh synchronization between field tablets without server connectivity.
4. Vaccine vial inventory tracking, cold-chain temperature telemetry, and batch wastage logs.