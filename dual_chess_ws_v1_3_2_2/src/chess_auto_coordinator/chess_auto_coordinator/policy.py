"""Pure, ROS-independent guard rules for coordinating the chess brain.

The policy never controls the robot; it decides only if a high-level
request to the chess brain is permissible. The brain revalidates inputs.
"""
from __future__ import annotations


def can_request_sync(*, enabled: bool, state: dict | None,
                     vision_seen: bool, vision_age_s: float,
                     state_age_s: float, in_flight: bool,
                     max_age_s: float) -> bool:
    return bool(
        enabled and isinstance(state, dict) and
        vision_seen and vision_age_s <= max_age_s and
        state_age_s <= max_age_s and not in_flight and
        not state.get("synchronized") and not state.get("blocked") and
        state.get("pending_plan_id") is None
    )


def can_request_next(*, enabled: bool, state: dict | None,
                     state_age_s: float, max_age_s: float,
                     safety_for_ply: int | None, last_requested_ply: int | None,
                     in_flight: bool) -> bool:
    if (not enabled or not isinstance(state, dict) or
            state_age_s > max_age_s or in_flight):
        return False
    ply = state.get("committed_plies")
    if type(ply) is not int or type(safety_for_ply) is not int:
        return False
    return bool(
        state.get("synchronized") is True and
        state.get("blocked") is False and
        state.get("result") is None and
        state.get("pending_plan_id") is None and
        state.get("robot_ack_received") is False and
        safety_for_ply == ply and
        last_requested_ply != ply
    )


def can_arm_safety(state: dict | None) -> bool:
    """Accept a *new* safety assertion only while idle and synchronized."""
    return bool(
        isinstance(state, dict) and
        state.get("synchronized") is True and
        state.get("blocked") is False and
        state.get("result") is None and
        state.get("pending_plan_id") is None and
        type(state.get("committed_plies")) is int
    )
