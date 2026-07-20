# gesturenav

Touchless pan / orbit / zoom camera control from hand-landmark gestures.

Turns a stream of hand landmarks (e.g. from [MediaPipe](https://developers.google.com/mediapipe)'s
HandLandmarker) into camera-control deltas your app can apply to a 3D viewer,
using held poses instead of clicks and drags:

| Pose | Action |
|---|---|
| ✌️ V-sign, then swipe | Orbit |
| ✋ Open palm, then swipe | Pan |
| 🤏 Pinch, drag vertically | Zoom |
| 🤙 Shaka, held | Toggle (e.g. switch camera mode) |

Built for touchless / hands-free 3D navigation — useful for kiosks, AR/VR
interfaces, and as an alternative input method for people who can't
reliably use a mouse or trackpad.

Zero required dependencies — pure Python, `math` and `dataclasses` only.
Bring your own hand-tracking source (MediaPipe, or anything else that
produces 21 landmarks per hand).

## Install

```bash
pip install gesturenav
```

## Usage

```python
from gesturenav import GestureController

controller = GestureController()

# hands: a list of 0-2 hands, each a sequence of 21 landmark objects
# with .x, .y, .z attributes in normalized [0, 1] image coordinates
# (this is exactly what MediaPipe's HandLandmarker.detect() returns
# via result.hand_landmarks).
state = controller.update(hands)

if state.mode == "pan":
    camera.pan(state.delta_x, state.delta_y)
elif state.mode == "orbit":
    camera.orbit(state.delta_x, state.delta_y)
elif state.mode == "zoom":
    camera.zoom(state.zoom_delta)

if state.toggle_id != last_toggle_id:
    camera.switch_mode()
    last_toggle_id = state.toggle_id
```

Call `controller.update([])` (or just let an empty/no-hand frame through)
when tracking is lost — it clears motion history so the next gesture
doesn't inherit stale momentum.

### Tuning

```python
GestureController(
    pose_lock_secs=0.5,    # how long a pose must be held before it "arms"
    swipe_thresh=0.022,    # min normalized motion per frame to trigger a swipe
    ema_alpha=0.6,         # smoothing factor for hand position (higher = snappier)
    toggle_hold_secs=0.6,  # how long a shaka must be held to fire a toggle
    toggle_cooldown=2.0,   # min seconds between toggle fires
)
```

### Pose classification only

If you just want the raw pose classification without the stateful
swipe/toggle tracking:

```python
from gesturenav import classify_hand

pose = classify_hand(one_hand_landmarks)
pose.is_fist, pose.is_open, pose.is_pinch, pose.v_sign, pose.palm_open, pose.shaka
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
