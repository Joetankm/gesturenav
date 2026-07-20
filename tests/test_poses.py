from gesturenav import classify_hand
from helpers import open_palm, fist, v_sign, shaka, pinch


def test_open_palm():
    pose = classify_hand(open_palm())
    assert pose.is_open
    assert pose.palm_open
    assert not pose.is_fist
    assert not pose.v_sign


def test_fist():
    pose = classify_hand(fist())
    assert pose.is_fist
    assert not pose.is_open
    assert not pose.palm_open


def test_v_sign():
    pose = classify_hand(v_sign())
    assert pose.v_sign
    assert not pose.is_fist
    assert not pose.palm_open


def test_shaka():
    pose = classify_hand(shaka())
    assert pose.shaka
    # shaka has 3 curled fingers, same as the is_fist threshold - they
    # legitimately overlap; the controller checks shaka independently.
    assert pose.is_fist


def test_pinch():
    pose = classify_hand(pinch())
    assert pose.is_pinch
    assert not pose.is_fist
