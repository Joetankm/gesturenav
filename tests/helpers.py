"""Synthetic MediaPipe-shaped landmark builders for tests.

Only the landmark indices actually read by gesturenav.poses.classify_hand
are given meaningful positions (0, 2, 4, 5, 8, 9, 12, 13, 16, 17, 20);
everything else is filled with the wrist position as a harmless placeholder.
"""
from collections import namedtuple

Landmark = namedtuple("Landmark", "x y z")

_MCP_Y     = 0.6
_TIP_CURL  = 0.65   # tip near wrist => curled
_TIP_EXT   = 0.15   # tip far from wrist => extended
_FINGERS   = {  # name -> (mcp_index, tip_index, x)
    "index":  (5, 8, 0.42),
    "middle": (9, 12, 0.50),
    "ring":   (13, 16, 0.58),
    "pinky":  (17, 20, 0.66),
}


def make_landmarks(extended=(), thumb_ext=False, thumb_at=None, ox=0.0, oy=0.0):
    """
    extended: iterable of finger names ("index", "middle", "ring", "pinky")
              that should be classified as extended; the rest are curled.
    thumb_ext: whether the thumb should read as extended (for shaka).
    thumb_at: explicit (x, y) for the thumb tip (landmark 4), e.g. to place
              it on top of the index tip for a pinch.
    ox, oy: offset applied to every landmark, to move the whole hand.
    """
    wrist = (0.5 + ox, 0.9 + oy)
    lm = [Landmark(wrist[0], wrist[1], 0.0)] * 21
    lm = list(lm)
    lm[0] = Landmark(wrist[0], wrist[1], 0.0)

    for name, (mcp_i, tip_i, x) in _FINGERS.items():
        lm[mcp_i] = Landmark(x + ox, _MCP_Y + oy, 0.0)
        tip_y = _TIP_EXT if name in extended else _TIP_CURL
        lm[tip_i] = Landmark(x + ox, tip_y + oy, 0.0)

    lm[2] = Landmark(0.46 + ox, 0.75 + oy, 0.0)
    if thumb_at is not None:
        lm[4] = Landmark(thumb_at[0] + ox, thumb_at[1] + oy, 0.0)
    elif thumb_ext:
        lm[4] = Landmark(0.15 + ox, 0.50 + oy, 0.0)
    else:
        lm[4] = Landmark(0.44 + ox, 0.65 + oy, 0.0)

    return lm


def open_palm(ox=0.0, oy=0.0):
    return make_landmarks(extended=("index", "middle", "ring", "pinky"), ox=ox, oy=oy)


def fist(ox=0.0, oy=0.0):
    return make_landmarks(extended=(), ox=ox, oy=oy)


def v_sign(ox=0.0, oy=0.0):
    return make_landmarks(extended=("index", "middle"), ox=ox, oy=oy)


def shaka(ox=0.0, oy=0.0):
    return make_landmarks(extended=("pinky",), thumb_ext=True, ox=ox, oy=oy)


def pinch(ox=0.0, oy=0.0):
    # extend index + middle so n_curled stays below the is_fist threshold (3)
    lm = make_landmarks(extended=("index", "middle"), ox=ox, oy=oy)
    lm = list(lm)
    ix, iy, _ = lm[8]
    lm[4] = Landmark(ix + 0.01, iy + 0.01, 0.0)  # thumb tip on top of index tip
    return lm
