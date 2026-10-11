# Chess Brain integration contract — v1.0

## A. Coordinate conventions — MUST be agreed upon before implementation

- 8 × 8 board, standard chess (not Chess960).
- Camera's **calibrated, reoriented** board matrix has `row=0` at the TOP (rank 8) and `col=0` at the LEFT (file a), with WHITE pieces starting at the BOTTOM.
- `row, col` are integers **0..7**, not 1..8. `a8=(0,0)`, `h8=(0,7)`, `a1=(7,0)`, `h1=(7,7)`, `e4=(4,4)`, `e2=(6,4)`.
- Each cell is one of 13 classes: `.` empty, `PNBRQK` white, `pnbrqk` black. Case is important.
- Squares do NOT encode world XYZ. Vision/robotics calibrate `board_frame` into each arm's base frame via TF2 / extrinsics. Do NOT reuse the raw camera pixel position as an arm target.

## B. Vision input: `/chess/vision/board` (`std_msgs/msg/String` as JSON)

Vision is responsible for producing a FULL 64-cell board, not a piece-only bounding-box list. Each frame should be stabilized over an appropriate frame window, with unique `capture_id`, trustworthy `captured_at` (Unix seconds), `stable`, `calibrated`, `confidence`, and `orientation`.

```json
{
  "schema_version":"1.0",
  "capture_id":"camera-frame-001",
  "source":"overhead_camera",
  "captured_at":1791750000.123,
  "orientation":"a8_top_left",
  "stable":true,
  "calibrated":true,
  "confidence":0.99,
  "cells":[
    {"row":0,"col":0,"piece":"r","confidence":0.99},
    {"row":0,"col":1,"piece":"n","confidence":0.99}
  ]
}
```

**The cells array above is abbreviated for illustration; the REAL message must contain all 64 unique `(row,col)` pairs, including empty squares.** Generate a full example with `python examples/make_vision_json.py`. Set `piece` to `.` when empty.

For Python-only testing, the `GameController` also accepts `piece_placement` instead of `cells` using a valid FEN placement field, but **ROS 2 bridge defaults to requiring 64 `cells`** so that there is an explicit reading for every square and per-cell confidence can be evaluated. This is a data contract; physical trust still depends on calibration and camera quality.

`captured_at` must be capture time, not time of ROS receipt. Synced clock required. `max_vision_age_s` defaults 5s. Confidence board >= 0.95 and cell >= 0.90 by default. A stable frame must have both hands away from the board; absence of hands must be verified by Vision.

**Never set `stable:true`, `calibrated:true` or `confidence:1.0` without actually measuring/guaranteeing those conditions.**

## C. Robot motion plan: `/chess/move_plan` (`std_msgs/msg/String` as JSON)

Example of one normal move:

```json
{
  "schema_version":"1.0",
  "plan_id":"unique-32-char-uuid-hex",
  "uci":"e2e4",
  "san":"e4",
  "side":"white",
  "piece":"P",
  "from_sq":"e2",
  "to_sq":"e4",
  "from_cell":{"row":6,"col":4},
  "to_cell":{"row":4,"col":4},
  "before_fen":"...",
  "expected_fen":"...",
  "created_at":1791750000.0,
  "actions":[{"kind":"move","source":"e2","target":"e4","piece":null,"source_cell":{"row":6,"col":4},"target_cell":{"row":4,"col":4}}],
  "captured":null,
  "capture_sq":null,
  "is_castling":false,
  "promotion":null,
  "gives_check":false,
  "eval_cp":null,
  "think_ms":1000.0
}
```

`before_fen` and `expected_fen` are FULL FEN strings, not just piece placement. They can be used by the integration team to display/verify state but **must not be copied as camera output for real operation**.

The robot must understand actions in order:

- `remove`: move victim piece from `source` into a configured captured-pieces area; the Brain does NOT have physical coordinates for the bin.
- `move`: move the source piece to target. Robotics resolves board cell -> board pose -> arm base pose -> IK/trajectory.
- `promote`: replace the pawn at the target with the specified spare piece. Handling inventory, routing, and gripper is Robotics' responsibility.

Castling returns 2 `move` actions, and en passant removes the pawn at `capture_sq`, which differs from attacker's destination.

## D. Ack `/chess/robot_ack` (`std_msgs/msg/String` as JSON)

```json
{
  "plan_id":"unique-32-char-uuid-hex",
  "success":true,
  "arm_parked":true,
  "gripper_released":true
}
```

**Publish this only after all required physical actions are completed and the robot is safe to observe.** Use identical `plan_id` in the motion executor. Deduplicate it in the robot executor too: ROS topic QoS alone is not exactly-once execution. If failure occurs, send `success:false`: controller blocks, never retries automatically.

## E. Safety readiness `/chess/safety_ready` (`std_msgs/msg/Bool`)

This signal MUST originate from the independent robotics/safety coordinator only when the physical system is ready to accept another chess plan: arm-to-arm collision risk handled, all active trajectories stopped and guards satisfied.

The brain initializes with `False` and resets this gate to `False` when it publishes a plan. New plans require a new safety assertion. **This Boolean is not an emergency stop nor a physical safety proof.**

## F. Operator command `/chess/command` (`std_msgs/msg/String` as JSON)

- `{"action":"sync"}` — after receiving vision of physically arranged board; successful initial sync required to plan.
- `{"action":"next"}` — ask Stockfish for a new move; requires synced board, no pending, and safety ready.
- `{"action":"manual", "from_sq":"e2", "to_sq":"e4"}` — manual command for test/control; legal moves only; optional `promotion: "q"`.
- `{"action":"state"}` — publish current state.
- `{"action":"reset","physical_reset_confirmed":true}` — operator/robot coordinator confirms physical reset; clears pending and requires vision sync again. Optionally supply `fen` to describe an intentionally set legal test board. This is a privileged operation; restrict who can publish to `/chess/command`.

## G. State / events outputs

- `/chess/state` JSON: `fen`, `turn`, `result`, `synchronized`, `blocked`, `block_reason`, `pending_plan_id`, `robot_ack_received`, `committed_plies`, `legal_moves`.
- `/chess/events` JSON: `command_response`, `robot_ack_response`, `vision_confirmation`, and errors.

Recommended operation **one at a time**:

```text
1) Vision publishes a trusted 64-cell board
2) Operator sends {"action":"sync"} (must match starting logical board)
3) Robot safety coordinator publishes /chess/safety_ready = true
4) Operator/controller sends {"action":"next"}
5) Brain publishes /chess/move_plan (unique plan_id)
6) Robot executes pick/place, checks manipulator safety, publishes robot_ack
7) Vision publishes a NEW frame taken AFTER Ack, stable, complete, calibrated
8) Brain compares placement with the expected board and commits on match
9) Safety coordinator reasserts readiness, then go to step 4
```

The Brain only updates chess state after **both** independent ack and post-ack vision confirmation. It does not autonomously issue the next move, and it does not infer/repair ambiguous physical changes.

## H. Failure policy

- Wrong orientation, incomplete observation, low confidence, stale capture, camera not calibrated: REJECT without state mutation.
- Wrong plan ID: REJECT robot ack.
- Duplicate capture ID: IGNORE; no repeated mismatch count.
- 3 **different** stable mismatching frames: BLOCK until explicit operator reset after physical inspection.
- Robot ack failure or arm not parked / gripper not released: BLOCK.
- No motion ack, no image: remains PENDING; external watchdog must alert operator on timeout.
- Stockfish crashes: fail closed; ROS node reports command error, no plan published. Operator must inspect and restart appropriately.
- Clock sync: external source should use system clock synchronized (e.g. NTP/PTP). Message timestamps are not authenticated.
- Security: use controlled ROS graph/domain, optionally SROS2. A forged ack, reset, or safety boolean cannot be ruled out by this JSON proof-of-concept.

## I. What is NOT included

No trained CV weights, no camera drivers, no TF2 transform, no robot IK, no motor commands, no MoveIt execution, no emergency-stop hardware, no captured-bin coordinates, no spare-promotion inventory, no automatic power-loss recovery, no claimed physical system safety. Hand these tasks to the respective owners explicitly.
