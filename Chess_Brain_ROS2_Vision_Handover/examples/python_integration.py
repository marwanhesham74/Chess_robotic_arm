"""WORKING CORE DEMO with simulated ack/vision only. Not a robot interface."""
from chess_brain_handover import GameController
from chess_brain_handover.selfplay import fake_vision

with GameController(white="strong", black="medium") as game:
    print("Initial sync:", game.sync_initial_board(fake_vision(game.board.board_fen())))
    plan = game.next_plan()
    print("PLAN FOR ROBOT:", plan.to_dict())
    print("Robot (SIMULATED) ack:", game.robot_ack(plan.plan_id, success=True,
                                                 arm_parked=True, gripper_released=True))
    print("Camera (SIMULATED) verify:", game.confirm_vision(fake_vision(plan.expected_fen.split()[0])))
    print("Current state:", game.state())
