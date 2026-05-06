"""Unit tests for the token resolver.

Run inside Blender:
    blender --background myfile.blend --python tests/test_tokens.py

Run standalone (no Blender needed):
    python tests/test_tokens.py
"""

import sys
import os
import datetime

# ---------------------------------------------------------------------------
# Path setup — allow standalone execution from inside the tests/ folder.
# ---------------------------------------------------------------------------
_ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ADDON_ROOT not in sys.path:
    sys.path.insert(0, _ADDON_ROOT)


# ---------------------------------------------------------------------------
# Minimal mocks so the resolver works without a live Blender session.
# ---------------------------------------------------------------------------

class _ImageSettings:
    file_format = "PNG"


class _Render:
    image_settings = _ImageSettings()


class _ViewLayer:
    name = "ViewLayer"


class _Camera:
    def __init__(self, name):
        self.name = name


class _MockScene:
    def __init__(self, camera_name=None, frame=1, fmt="PNG"):
        self.camera = _Camera(camera_name) if camera_name else None
        self.frame_current = frame
        self.render = _Render()
        self.render.image_settings.file_format = fmt
        self.view_layers = [_ViewLayer()]


class _MockSetup:
    def __init__(self, name):
        self.name = name


# ---------------------------------------------------------------------------
# Attempt to import the real tokens module (works both ways).
# ---------------------------------------------------------------------------

try:
    # Inside Blender with the add-on installed.
    from scene_manager.core import tokens as tok
except ImportError:
    # Standalone: add-on root is already on sys.path.
    from core import tokens as tok  # type: ignore


# Patch bpy inside the tokens module for standalone runs.
try:
    import bpy  # noqa: F401
    _STANDALONE = False
except ImportError:
    _STANDALONE = True

    class _FakeBpy:
        class data:
            filepath = ""

        class path:
            @staticmethod
            def abspath(p):
                return p.replace("//", "/tmp/")

    tok.bpy = _FakeBpy  # type: ignore


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

_FIXED_TIME = datetime.datetime(2024, 6, 15, 10, 30, 0)
_FIXED_BLEND = "/project/scene/myfile.blend"

_failures = 0


def _assert(label: str, got, expected) -> None:
    global _failures
    if got != expected:
        print(f"  FAIL  [{label}]\n        expected: {expected!r}\n        got:      {got!r}")
        _failures += 1
    else:
        print(f"  PASS  [{label}]")


def test_sanitize_name():
    _assert("plain name unchanged", tok.sanitize_name("Shot_01"), "Shot_01")
    _assert("forward slash replaced", tok.sanitize_name("a/b"), "a_b")
    _assert("colon replaced", tok.sanitize_name("name:val"), "name_val")
    _assert("angle brackets replaced", tok.sanitize_name("<hero>"), "_hero_")
    _assert("null byte replaced", tok.sanitize_name("bad\x00char"), "bad_char")
    _assert("control char replaced", tok.sanitize_name("x\x1fy"), "x_y")


def test_basic_tokens():
    scene = _MockScene(camera_name="Cam_Hero", frame=42, fmt="PNG")
    setup = _MockSetup("Shot_01")
    result = tok.resolve(
        "//{setup}/{camera}_{frame}.{ext}",
        scene, setup,
        render_time=_FIXED_TIME,
        blend_path=_FIXED_BLEND,
    )
    _assert("basic token expansion", result, "//Shot_01/Cam_Hero_0042.png")


def test_no_camera_fallback():
    scene = _MockScene(camera_name=None, frame=1)
    setup = _MockSetup("NoCamera")
    result = tok.resolve("{camera}", scene, setup, _FIXED_TIME, _FIXED_BLEND)
    _assert("no camera -> no_camera", result, "no_camera")


def test_date_time_tokens():
    scene = _MockScene(camera_name="C", frame=1)
    setup = _MockSetup("S")
    result = tok.resolve("{date}_{time}", scene, setup, _FIXED_TIME, _FIXED_BLEND)
    _assert("date/time tokens", result, "20240615_103000")


def test_blend_token():
    scene = _MockScene(camera_name="C", frame=1)
    setup = _MockSetup("S")
    result = tok.resolve("{blend}", scene, setup, _FIXED_TIME, _FIXED_BLEND)
    _assert("blend token is stem only", result, "myfile")


def test_blend_token_unsaved():
    scene = _MockScene(camera_name="C", frame=1)
    setup = _MockSetup("S")
    result = tok.resolve("{blend}", scene, setup, _FIXED_TIME, blend_path="")
    _assert("unsaved blend -> 'unsaved'", result, "unsaved")


def test_forbidden_chars_in_setup_name():
    scene = _MockScene(camera_name="C", frame=1)
    setup = _MockSetup('Shot: <Hero>"')
    result = tok.resolve("{setup}", scene, setup, _FIXED_TIME, _FIXED_BLEND)
    _assert("forbidden chars sanitized in setup name", result, "Shot_ _Hero__")


def test_frame_zero_padding():
    scene = _MockScene(camera_name="C", frame=7)
    setup = _MockSetup("S")
    result = tok.resolve("{frame}", scene, setup, _FIXED_TIME, _FIXED_BLEND)
    _assert("frame zero-padded to 4 digits", result, "0007")


def test_ext_mapping():
    for fmt, expected in [("JPEG", "jpg"), ("OPEN_EXR", "exr"), ("TIFF", "tif")]:
        scene = _MockScene(camera_name="C", frame=1, fmt=fmt)
        setup = _MockSetup("S")
        result = tok.resolve("{ext}", scene, setup, _FIXED_TIME, _FIXED_BLEND)
        _assert(f"ext for {fmt}", result, expected)


def test_unknown_token_left_intact():
    scene = _MockScene(camera_name="C", frame=1)
    setup = _MockSetup("S")
    result = tok.resolve("{unknown}", scene, setup, _FIXED_TIME, _FIXED_BLEND)
    _assert("unknown token left as-is", result, "{unknown}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== Scene Manager — Token Resolver Tests ===\n")
    test_sanitize_name()
    test_basic_tokens()
    test_no_camera_fallback()
    test_date_time_tokens()
    test_blend_token()
    test_blend_token_unsaved()
    test_forbidden_chars_in_setup_name()
    test_frame_zero_padding()
    test_ext_mapping()
    test_unknown_token_left_intact()
    print(f"\n{'All tests passed.' if _failures == 0 else f'{_failures} test(s) FAILED.'}")
    sys.exit(0 if _failures == 0 else 1)
