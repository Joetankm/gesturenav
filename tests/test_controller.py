from gesturenav import GestureController
from helpers import open_palm, shaka


def test_reset_on_no_hands():
    ctrl = GestureController()
    state = ctrl.update([])
    assert state.mode == "none"
    assert state.current_pose == "none"


def test_pan_swipe_after_arming():
    ctrl = GestureController(pose_lock_secs=0.1, swipe_thresh=0.01)
    t = 0.0

    # hold an open palm still long enough for "pan" to arm
    state = None
    for _ in range(6):
        state = ctrl.update([open_palm()], now=t)
        t += 0.05
    assert state.current_pose == "pan"

    # then move the hand steadily -> should trigger a pan swipe
    triggered = False
    for i in range(5):
        t += 0.05
        state = ctrl.update([open_palm(ox=0.05 * (i + 1))], now=t)
        if state.mode == "pan":
            triggered = True
            break
    assert triggered
    assert state.delta_x > 0


def test_shaka_toggle_fires_once_per_hold():
    ctrl = GestureController(toggle_hold_secs=0.1, toggle_cooldown=1.0)
    t = 100.0  # realistic epoch-like timestamp; avoids the cooldown-at-zero edge case
    ids = []
    for _ in range(6):
        state = ctrl.update([shaka()], now=t)
        ids.append(state.toggle_id)
        t += 0.05
    assert ids[0] == 0
    assert ids[-1] == 1
