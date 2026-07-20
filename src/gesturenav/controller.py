"""Stateful gesture -> camera-control-delta controller.

Feed it up to two hands' worth of landmarks per frame; it tracks pose
smoothing (EMA), pose-hold arming, and swipe/pinch detection, and returns
a GestureState describing the pan/orbit/zoom delta for that frame.
"""
import math
import time
from collections import deque
from dataclasses import dataclass

from .poses import classify_hand


@dataclass
class GestureState:
    mode: str = "none"           # "none" | "pan" | "orbit" | "zoom"
    armed: bool = False
    current_pose: str = "none"   # "none" | "pan" | "orbit" | "zoom"
    delta_x: float = 0.0
    delta_y: float = 0.0
    zoom_delta: float = 0.0
    toggle_id: int = 0


class GestureController:
    """
    Recognized poses (from the first detected hand):
      - V-sign (index + middle extended)   -> arms "orbit"; swipe to rotate
      - open palm (flat aspect ratio)      -> arms "pan"; swipe to translate
      - pinch (thumb + index tips close)   -> drag vertically to zoom
      - shaka (thumb + pinky extended,
               other fingers curled) held
        for `toggle_hold_secs`             -> fires a toggle_id increment
                                               (e.g. switch camera mode)

    A pose must be held for `pose_lock_secs` before it "arms" — this
    prevents accidental pans/orbits while the hand is still moving into
    position. Once armed, a fast enough motion (`swipe_thresh`) triggers
    the delta for that frame.

    Call update() once per frame with the latest detected hand landmarks.
    Call reset() (or update() with an empty list) when hand tracking is lost.
    """

    def __init__(self, pose_lock_secs=0.5, swipe_thresh=0.022,
                 ema_alpha=0.6, toggle_hold_secs=0.6, toggle_cooldown=2.0,
                 history_len=10):
        self.pose_lock_secs   = pose_lock_secs
        self.swipe_thresh     = swipe_thresh
        self.ema_alpha        = ema_alpha
        self.toggle_hold_secs = toggle_hold_secs
        self.toggle_cooldown  = toggle_cooldown

        self._ema_hand     = [None, None]
        self._ema_pinch     = None
        self._hand_pos_hist = [deque(maxlen=history_len), deque(maxlen=history_len)]
        self._pinch_hist    = deque(maxlen=history_len)
        self._toggle_sm     = {"state": "idle", "shaka_since": 0.0, "last_toggle": 0.0}
        self._pose_timer    = {"pose": None, "since": 0.0}
        self._toggle_id     = 0

    def reset(self):
        """Clear motion-tracking state. Call when no hand is detected."""
        self._hand_pos_hist[0].clear()
        self._hand_pos_hist[1].clear()
        self._pinch_hist.clear()
        self._ema_hand[0] = None
        self._ema_hand[1] = None
        self._ema_pinch   = None
        return GestureState(toggle_id=self._toggle_id)

    def update(self, hands_landmarks, now=None):
        """
        hands_landmarks: list of 0-2 hands, each a sequence of 21 landmarks
                          with .x/.y/.z (e.g. MediaPipe HandLandmarker output).
        now: unix timestamp for this frame; defaults to time.time(). Pass an
             explicit value in tests to make motion/timing deterministic.

        Returns a GestureState describing this frame's gesture output.
        """
        if not hands_landmarks:
            return self.reset()

        now = time.time() if now is None else now
        n_h = min(len(hands_landmarks), 2)
        poses = [classify_hand(hands_landmarks[i]) for i in range(n_h)]

        for i in range(n_h):
            raw_c = poses[i].center
            if self._ema_hand[i] is None:
                self._ema_hand[i] = raw_c
            else:
                a = self.ema_alpha
                self._ema_hand[i] = (
                    self._ema_hand[i][0] * (1 - a) + raw_c[0] * a,
                    self._ema_hand[i][1] * (1 - a) + raw_c[1] * a,
                )
            self._hand_pos_hist[i].append(self._ema_hand[i])
        if n_h < 2:
            self._hand_pos_hist[1].clear()
            self._ema_hand[1] = None

        mode, dx, dy, zdelta = "none", 0.0, 0.0, 0.0

        c0 = poses[0]
        sm = self._toggle_sm
        if c0.shaka:
            if sm["state"] == "idle":
                sm["state"], sm["shaka_since"] = "shaka", now
            elif sm["state"] == "shaka":
                if (now - sm["shaka_since"]) >= self.toggle_hold_secs:
                    if (now - sm["last_toggle"]) > self.toggle_cooldown:
                        self._toggle_id += 1
                        sm["last_toggle"] = now
                    sm["state"] = "cooldown"
        else:
            sm["state"] = "idle"

        current_pose = None
        if c0.v_sign:
            current_pose = "orbit"
        elif c0.palm_open and not c0.shaka:
            current_pose = "pan"

        pt = self._pose_timer
        if current_pose != pt["pose"]:
            pt["pose"], pt["since"] = current_pose, now
        armed = (current_pose is not None) and \
                (now - pt["since"] >= self.pose_lock_secs)

        if c0.is_pinch:
            current_pose = "zoom"
            raw_pc = c0.pinch_center
            if self._ema_pinch is None:
                self._ema_pinch = raw_pc
            else:
                a = self.ema_alpha
                self._ema_pinch = (
                    self._ema_pinch[0] * (1 - a) + raw_pc[0] * a,
                    self._ema_pinch[1] * (1 - a) + raw_pc[1] * a,
                )
            self._pinch_hist.append(self._ema_pinch)
            if len(self._pinch_hist) >= 3:
                rdy = self._pinch_hist[-1][1] - self._pinch_hist[-3][1]
                if abs(rdy) > self.swipe_thresh * 0.5:
                    zdelta, mode = rdy, "zoom"
            armed = (mode == "none")
        else:
            self._pinch_hist.clear()
            self._ema_pinch = None
            if armed:
                hist = list(self._hand_pos_hist[0])
                if len(hist) >= 3:
                    rdx = hist[-1][0] - hist[-3][0]
                    rdy = hist[-1][1] - hist[-3][1]
                    spd = math.sqrt(rdx * rdx + rdy * rdy)
                    if spd > self.swipe_thresh:
                        mode, dx, dy = current_pose, rdx, rdy

        return GestureState(
            mode=mode, armed=armed and mode == "none",
            current_pose=current_pose or "none",
            delta_x=dx, delta_y=dy, zoom_delta=zdelta,
            toggle_id=self._toggle_id,
        )
