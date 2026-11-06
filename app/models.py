from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field

# Core Child & Round DTOs
class ChildBase(BaseModel):
    child_id: str
    name: str
    dob: date
    guardian_name: str
    settlement: str

class RoundModel(BaseModel):
    round_id: str
    name: str
    start_date: date
    end_date: date

# Encounter Ingestion & Record DTOs
class EncounterCreate(BaseModel):
    event_id: Optional[str] = None
    child_id: str
    round_id: str
    device_id: str = "DEV-PORTAL"
    recorded_at: Optional[datetime] = None
    type: str = "revisit"
    zero_dose_answer: Optional[bool] = None
    vaccinated_since_last: Optional[str] = None
    vaccinated_elsewhere: Optional[bool] = None
    comment: Optional[str] = None

class EncounterRecord(EncounterCreate):
    event_id: str
    recorded_at: datetime

# Status & History Representation
class StatusChangeItem(BaseModel):
    timestamp: datetime
    round_id: str
    event_id: str
    source_type: str
    previous_status: Optional[bool]
    new_status: bool
    details: str

class ChildDetailResponse(BaseModel):
    child_id: str
    name: str
    dob: date
    guardian_name: str
    settlement: str
    current_zero_dose_flag: Optional[bool]
    status_label: str
    history: List[StatusChangeItem]
    encounters: List[EncounterRecord]

# Supervisor Transition Models
class TransitionChildSummary(BaseModel):
    child_id: str
    name: str
    settlement: str
    guardian_name: str
    from_round: str
    to_round: str
    resolved_event_id: str
    resolved_at: datetime
    confirmation_method: str

class TransitionSupervisorResponse(BaseModel):
    from_round: str
    to_round: str
    total_transitioned_count: int
    children: List[TransitionChildSummary]