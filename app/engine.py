"""
Reusable Zero-Dose Domain Engine.
Design Principle: Isolated, framework-independent domain service for zero-dose tracking,
evaluation, status reconstruction, and transition audits.
"""
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

class ZeroDoseEngine:
    """
    Domain service evaluating zero-dose statuses, state histories, and cross-round transitions.
    Fully isolated from storage engines or web frameworks.
    """

    @staticmethod
    def evaluate_encounter(
        current_zero_dose: Optional[bool],
        enc: Dict[str, Any]
    ) -> Tuple[Optional[bool], Optional[Dict[str, Any]]]:
        """
        Evaluates a single encounter against the child's running status.
        Returns: (new_zero_dose_status, audit_event_dict_if_status_changed)
        """
        enc_type = enc.get("type")
        event_id = enc.get("event_id")
        round_id = enc.get("round_id")
        rec_at = enc.get("recorded_at")
        comment = enc.get("comment") or ""

        # Enumeration round handling
        if enc_type == "enumeration":
            z_ans = enc.get("zero_dose_answer")
            if z_ans is not None:
                new_status = bool(z_ans)
                audit = {
                    "timestamp": rec_at,
                    "round_id": round_id,
                    "event_id": event_id,
                    "source_type": "enumeration",
                    "previous_status": current_zero_dose,
                    "new_status": new_status,
                    "details": f"Initial enumeration: zero-dose = {new_status}"
                }
                return new_status, audit
            return current_zero_dose, None

        # Revisit encounter handling
        v_since = enc.get("vaccinated_since_last")
        v_elsewhere = enc.get("vaccinated_elsewhere")

        # Check for confirmed vaccination (either via campaign or outside campaign)
        vaccinated_confirmed = (v_since == "yes") or (v_elsewhere is True)

        # Check for explicit correction (revisit answering 'no' or card correction)
        not_vaccinated_answered = (v_since == "no")

        if vaccinated_confirmed:
            if current_zero_dose is not False:
                details = "Guardian confirmed vaccination"
                if v_elsewhere is True:
                    details += " outside campaign (elsewhere)"
                elif v_since == "yes":
                    details += " since last campaign round"
                if comment:
                    details += f" ({comment})"

                audit = {
                    "timestamp": rec_at,
                    "round_id": round_id,
                    "event_id": event_id,
                    "source_type": "revisit_vaccinated",
                    "previous_status": current_zero_dose,
                    "new_status": False,
                    "details": details
                }
                return False, audit

        elif not_vaccinated_answered:
            # Check if this is an explicit correction (e.g. C043 where sibling card was shown)
            if "correcting" in comment.lower() or current_zero_dose is None:
                new_status = True
                if current_zero_dose != new_status:
                    audit = {
                        "timestamp": rec_at,
                        "round_id": round_id,
                        "event_id": event_id,
                        "source_type": "revisit_correction",
                        "previous_status": current_zero_dose,
                        "new_status": True,
                        "details": f"Status revised to zero-dose: {comment or 'no vaccination recorded'}"
                    }
                    return True, audit

        # Null or non-transitioning answers preserve status
        return current_zero_dose, None

    @classmethod
    def compute_child_timeline(
        cls,
        encounters: List[Dict[str, Any]]
    ) -> Tuple[Optional[bool], List[Dict[str, Any]]]:
        """
        Sorts encounters deterministically by timestamp and replays state to build
        an audit trail of state changes and final current status.
        """
        sorted_encs = sorted(
            encounters,
            key=lambda e: (str(e.get("recorded_at") or ""), str(e.get("event_id") or ""))
        )
        current_status: Optional[bool] = None
        history: List[Dict[str, Any]] = []

        for enc in sorted_encs:
            new_status, audit = cls.evaluate_encounter(current_status, enc)
            if audit:
                history.append(audit)
            current_status = new_status

        return current_status, history

    @classmethod
    def get_round_status_map(
        cls,
        encounters: List[Dict[str, Any]],
        ordered_rounds: List[str]
    ) -> Dict[str, Optional[bool]]:
        """
        Returns a dict mapping round_id -> effective_zero_dose_status at the end of that round.
        """
        sorted_encs = sorted(
            encounters,
            key=lambda e: (str(e.get("recorded_at") or ""), str(e.get("event_id") or ""))
        )
        round_map: Dict[str, Optional[bool]] = {r: None for r in ordered_rounds}
        running_status: Optional[bool] = None

        enc_by_round: Dict[str, List[Dict[str, Any]]] = {r: [] for r in ordered_rounds}
        for enc in sorted_encs:
            rid = enc.get("round_id")
            if rid in enc_by_round:
                enc_by_round[rid].append(enc)

        for rid in ordered_rounds:
            for enc in enc_by_round[rid]:
                running_status, _ = cls.evaluate_encounter(running_status, enc)
            round_map[rid] = running_status

        return round_map