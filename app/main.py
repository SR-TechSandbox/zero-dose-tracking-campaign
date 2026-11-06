"""
FastAPI Main Application.
Provides REST API endpoints for rounds, children, flag history, supervisor aggregates,
and new revisit encounters, plus serves the lightweight frontend single-page UI.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime, timezone
import uuid
import os

from app.database import (
    init_db, get_all_rounds, get_all_children, get_child_by_id,
    get_encounters_for_child, insert_encounter
)
from app.engine import ZeroDoseEngine
from app.models import (
    EncounterCreate, EncounterRecord, ChildDetailResponse,
    TransitionSupervisorResponse, TransitionChildSummary, RoundModel
)

app = FastAPI(
    title="Zero-Dose Campaign Tracker API",
    version="0.1.0",
    description="Cross-round zero-dose child tracking, revisit persistence, and supervisor aggregates"
)

# Startup hook to initialize and auto-seed database
@app.on_event("startup")
def on_startup():
    init_db()

# Serve static UI files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
def get_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Zero-Dose Campaign Tracker API online. Visit /docs for OpenAPI documentation."}

@app.get("/api/rounds", response_model=list[RoundModel])
def list_rounds():
    """Retrieve all campaign rounds in chronological order."""
    rounds = get_all_rounds()
    return rounds

@app.get("/api/children")
def list_children(search: str = Query(None, description="Search by name, settlement, or child_id")):
    """List all registered children with their current zero-dose status."""
    children = get_all_children()
    results = []

    for ch in children:
        if search:
            q = search.lower()
            if q not in ch["child_id"].lower() and q not in ch["name"].lower() and q not in ch["settlement"].lower():
                continue
        encs = get_encounters_for_child(ch["child_id"])
        current_status, history = ZeroDoseEngine.compute_child_timeline(encs)
        results.append({
            "child_id": ch["child_id"],
            "name": ch["name"],
            "dob": ch["dob"],
            "guardian_name": ch["guardian_name"],
            "settlement": ch["settlement"],
            "current_zero_dose_flag": current_status,
            "status_label": "Zero-Dose" if current_status is True else ("Vaccinated" if current_status is False else "Unknown"),
            "encounter_count": len(encs)
        })
    return results

@app.get("/api/children/{child_id}", response_model=ChildDetailResponse)
def get_child_detail(child_id: str):
    """Retrieve child details, full encounter history, and zero-dose status change timeline."""
    child = get_child_by_id(child_id)
    if not child:
        raise HTTPException(status_code=404, detail=f"Child {child_id} not found")

    encs = get_encounters_for_child(child_id)
    current_status, history = ZeroDoseEngine.compute_child_timeline(encs)

    return {
        "child_id": child["child_id"],
        "name": child["name"],
        "dob": child["dob"],
        "guardian_name": child["guardian_name"],
        "settlement": child["settlement"],
        "current_zero_dose_flag": current_status,
        "status_label": "Zero-Dose" if current_status is True else ("Vaccinated" if current_status is False else "Unknown"),
        "history": history,
        "encounters": encs
    }

@app.get("/api/supervisor/transitions", response_model=TransitionSupervisorResponse)
def get_round_transitions(
    from_round: str = Query(..., description="Starting round (e.g., R1)"),
    to_round: str = Query(..., description="Consecutive comparison round (e.g., R2)")
):
    """
    Supervisor aggregate endpoint:
    Returns the count and list of children who moved from zero-dose (True) in from_round
    to vaccinated (False) in to_round.
    """
    rounds = get_all_rounds()
    round_ids = [r["round_id"] for r in rounds]

    if from_round not in round_ids or to_round not in round_ids:
        raise HTTPException(status_code=400, detail="Specified rounds must exist in campaign rounds")

    children = get_all_children()
    transitioned_children = []

    for ch in children:
        cid = ch["child_id"]
        encs = get_encounters_for_child(cid)
        round_map = ZeroDoseEngine.get_round_status_map(encs, round_ids)

        status_from = round_map.get(from_round)
        status_to = round_map.get(to_round)

        # A child moved if they were zero-dose (True) in from_round and vaccinated (False) in to_round
        if status_from is True and status_to is False:
            to_encs = [e for e in encs if e["round_id"] == to_round]
            resolved_event = to_encs[-1] if to_encs else encs[-1]
            method = "Campaign Revisit"
            if resolved_event.get("vaccinated_elsewhere") is True:
                method = "External (Vaccinated Elsewhere)"
            elif resolved_event.get("vaccinated_since_last") == "yes":
                method = "Vaccinated Since Last Campaign"

            transitioned_children.append(TransitionChildSummary(
                child_id=cid,
                name=ch["name"],
                settlement=ch["settlement"],
                guardian_name=ch["guardian_name"],
                from_round=from_round,
                to_round=to_round,
                resolved_event_id=resolved_event["event_id"],
                resolved_at=resolved_event["recorded_at"],
                confirmation_method=method
            ))

    return TransitionSupervisorResponse(
        from_round=from_round,
        to_round=to_round,
        total_transitioned_count=len(transitioned_children),
        children=transitioned_children
    )

@app.post("/api/encounters")
def record_encounter(payload: EncounterCreate):
    """
    Record a new field encounter (e.g. revisit).
    Persists encounter, updates the audit log, and recalculates the zero-dose flag.
    """
    child = get_child_by_id(payload.child_id)
    if not child:
        raise HTTPException(status_code=404, detail=f"Child {payload.child_id} not found")

    event_id = payload.event_id or f"E{uuid.uuid4().hex[:6].upper()}"
    rec_at = payload.recorded_at or datetime.now(timezone.utc).isoformat()
    if isinstance(rec_at, datetime):
        rec_at = rec_at.isoformat()

    enc_dict = {
        "event_id": event_id,
        "child_id": payload.child_id,
        "round_id": payload.round_id,
        "device_id": payload.device_id,
        "recorded_at": rec_at,
        "type": payload.type,
        "zero_dose_answer": payload.zero_dose_answer,
        "vaccinated_since_last": payload.vaccinated_since_last,
        "vaccinated_elsewhere": payload.vaccinated_elsewhere,
        "comment": payload.comment
    }

    insert_encounter(enc_dict)

    # Recompute updated status
    updated_encs = get_encounters_for_child(payload.child_id)
    new_status, history = ZeroDoseEngine.compute_child_timeline(updated_encs)

    return {
        "status": "success",
        "message": "Encounter recorded successfully",
        "event_id": event_id,
        "child_id": payload.child_id,
        "current_zero_dose_flag": new_status,
        "history_count": len(history)
    }