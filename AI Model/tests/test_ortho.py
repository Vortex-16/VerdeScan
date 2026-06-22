"""
VerdeScan — ortho-pipeline + evaluation unit tests.

Unlike test_pipeline.py (which feeds the legacy CNN solid-colour squares and so
only proves the colour heuristic relearns its own colours), these tests exercise
the ACTUAL survival-decision logic and the casualty-scoring maths that the
hackathon is judged on:

  • coordinate round-trip (pixel ↔ projected)
  • haversine distance against a known value
  • greedy_match recall against synthetic ground truth
  • classify_signals: the weeding-ring / localised-green decision rule, including
    the weed-overgrown-casualty case (challenge #2) that must NOT read as alive.

Run:  python -m pytest tests/test_ortho.py -v
"""

import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ortho_pipeline as op
import evaluate as ev


# ── coordinate maths ─────────────────────────────────────────────────────────

class _FakeMeta:
    """Minimal stand-in for RasterMeta with a known affine transform."""
    ox, oy = 500_000.0, 2_400_000.0      # UTM-ish origin
    sx, sy = 0.025, 0.025                 # 2.5 cm/px


def test_pixel_proj_roundtrip():
    m = _FakeMeta()
    for col, row in [(0, 0), (1234, 5678), (20000, 16000)]:
        px, py = op.RasterMeta.pixel_to_proj(m, col, row)
        c2, r2 = op.RasterMeta.proj_to_pixel(m, px, py)
        assert (c2, r2) == (col, row), f"round-trip failed: {(col,row)} → {(c2,r2)}"


def test_haversine_known_distance():
    # 0.001° of latitude ≈ 111.19 m
    d = ev.haversine_m(21.65, 83.82, 21.651, 83.82)
    assert 110.0 < d < 112.5, f"haversine off: {d:.2f} m"
    assert ev.haversine_m(21.65, 83.82, 21.65, 83.82) == 0.0


# ── casualty scoring ─────────────────────────────────────────────────────────

def test_greedy_match_recall():
    truth = [(21.6500, 83.8200), (21.6510, 83.8210)]
    # one prediction ~0.75 m from truth[0], one far away
    pred = [(21.650005, 83.820005), (21.7000, 83.9000)]
    matches, missed = ev.greedy_match(truth, pred, tol_m=1.5)
    assert len(matches) == 1
    assert missed == [1]


def test_greedy_match_no_double_count():
    truth = [(21.6500, 83.8200), (21.65001, 83.82001)]   # two truths, very close
    pred  = [(21.65000, 83.82000)]                         # only one prediction
    matches, missed = ev.greedy_match(truth, pred, tol_m=2.0)
    assert len(matches) == 1, "one prediction must not match two truths"
    assert len(missed) == 1


# ── survival decision rule ───────────────────────────────────────────────────

def test_live_sapling_localised_green_is_alive():
    # green concentrated at centre, bare surround → a real survivor
    sig = {"green_center": 0.40, "green_annulus": 0.05, "ring_contrast": 0.02}
    status, conf = op.classify_signals(sig, hough=False)
    assert status == "alive" and conf > 0.5


def test_weed_overgrown_casualty_is_dead():
    # uniformly green everywhere (weeds), no weeding ring → must be a casualty,
    # NOT alive — this is the brief's challenge #2.
    sig = {"green_center": 0.80, "green_annulus": 0.82, "ring_contrast": 0.0}
    status, _ = op.classify_signals(sig, hough=False)
    assert status == "dead", "weed-overgrown spot wrongly classified alive"


def test_weeding_ring_alone_is_alive():
    # bare centre but a strong cleared-ring contrast → a maintained sapling
    sig = {"green_center": 0.0, "green_annulus": 0.0, "ring_contrast": 0.25}
    status, _ = op.classify_signals(sig, hough=False)
    assert status == "alive"


def test_bare_soil_is_dead():
    sig = {"green_center": 0.0, "green_annulus": 0.0, "ring_contrast": 0.01}
    status, conf = op.classify_signals(sig, hough=False)
    assert status == "dead" and conf > 0.5


def test_hough_ring_rescues_bare_centre():
    sig = {"green_center": 0.0, "green_annulus": 0.0, "ring_contrast": 0.0}
    assert op.classify_signals(sig, hough=True)[0] == "alive"
    assert op.classify_signals(sig, hough=False)[0] == "dead"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn(); print(f"  ✅ {fn.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  ❌ {fn.__name__}: {e}")
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
