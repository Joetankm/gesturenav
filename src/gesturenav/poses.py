"""Pure hand-pose classification from 21-point hand landmarks.

Works with any landmark objects exposing .x, .y, .z in normalized [0, 1]
image coordinates - e.g. MediaPipe's HandLandmarker output, or a plain
namedtuple for testing. No dependency on MediaPipe itself.
"""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class HandPose:
    is_fist: bool
    is_open: bool
    is_pinch: bool
    v_sign: bool
    palm_open: bool
    shaka: bool
    center: tuple
    pinch_center: tuple


def _dist2(lm, a, b):
    return math.sqrt((lm[a].x - lm[b].x) ** 2 + (lm[a].y - lm[b].y) ** 2)


def _dist3(lm, a, b):
    return math.sqrt((lm[a].x - lm[b].x) ** 2 + (lm[a].y - lm[b].y) ** 2
                      + (lm[a].z - lm[b].z) ** 2)


def classify_hand(landmarks) -> HandPose:
    """Classify one hand's 21 MediaPipe-style landmarks into a HandPose.

    landmarks: a sequence of 21 objects, each with .x, .y, .z attributes
    (normalized image coordinates), indexed per the MediaPipe hand model
    (0=wrist, 4=thumb tip, 8=index tip, 12=middle tip, 16=ring tip,
    20=pinky tip, ...).
    """
    lm = landmarks
    curled = [
        _dist3(lm, 8, 0)  < _dist3(lm, 5, 0),
        _dist3(lm, 12, 0) < _dist3(lm, 9, 0),
        _dist3(lm, 16, 0) < _dist3(lm, 13, 0),
        _dist3(lm, 20, 0) < _dist3(lm, 17, 0),
    ]
    n_curled = sum(curled)
    is_fist  = n_curled >= 3
    is_open  = n_curled == 0

    is_pinch = (_dist2(lm, 4, 8) < 0.07) and not is_fist

    width_2d  = _dist2(lm, 5, 17)
    length_2d = _dist2(lm, 0, 9)
    aspect    = width_2d / (length_2d + 1e-6)

    v_sign = (not curled[0]) and (not curled[1]) and curled[2] and curled[3] \
             and not is_fist
    palm_open = is_open and (aspect > 0.55)

    thumb_ext = _dist2(lm, 4, 5) > _dist2(lm, 2, 5) * 1.1
    shaka = thumb_ext and curled[0] and curled[1] and curled[2] and (not curled[3])

    cx  = (lm[0].x + lm[9].x) * 0.5
    cy  = (lm[0].y + lm[9].y) * 0.5
    pcx = (lm[4].x + lm[8].x) * 0.5
    pcy = (lm[4].y + lm[8].y) * 0.5

    return HandPose(
        is_fist=is_fist, is_open=is_open, is_pinch=is_pinch,
        v_sign=v_sign, palm_open=palm_open, shaka=shaka,
        center=(cx, cy), pinch_center=(pcx, pcy),
    )
