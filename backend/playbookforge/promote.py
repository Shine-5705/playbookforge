from __future__ import annotations

from .models import PlaybookRule
from .replay import ReplayReport, report_to_dict
from .store import PlaybookStore, _utc_now


class PromotionGateError(Exception):
    pass


def can_promote(report: ReplayReport) -> tuple[bool, str]:
    if report.pass_rate_after <= report.pass_rate_before:
        return False, "Rule must strictly increase pass rate."
    if any(report.per_task_regressed.values()):
        regressed = [k for k, v in report.per_task_regressed.items() if v]
        return False, f"Regression on tasks: {', '.join(regressed)}"
    return True, "Eligible for promotion."


def apply_replay_to_candidate(store: PlaybookStore, rule: PlaybookRule, report: ReplayReport) -> PlaybookRule:
    updated = PlaybookRule(
        id=rule.id,
        text=rule.text,
        version=rule.version + 1,
        status=rule.status,
        pass_rate_before=report.pass_rate_before,
        pass_rate_after=report.pass_rate_after,
        simulated=report.simulated,
        created_at=_utc_now(),
        parent_version=rule.version,
    )
    store.insert_rule(updated, replay_payload=report_to_dict(report))
    store.save_replay(report_to_dict(report), rule_id=rule.id, rule_version=updated.version)
    return updated


def promote_rule(store: PlaybookStore, rule_id: str, version: int) -> PlaybookRule:
    rule = store.get_rule(rule_id, version)
    if not rule:
        raise PromotionGateError(f"Unknown rule {rule_id} v{version}")
    if rule.pass_rate_after is None or rule.pass_rate_before is None:
        raise PromotionGateError("Run replay before promotion.")
    if rule.pass_rate_after <= rule.pass_rate_before:
        raise PromotionGateError("Pass rate did not improve.")
    payload = store.get_replay_json(rule_id, version)
    if payload:
        regress = payload.get("per_task_regressed") or {}
        if any(regress.values()):
            raise PromotionGateError("Per-task regression detected.")
    return store.promote(rule_id, version)
