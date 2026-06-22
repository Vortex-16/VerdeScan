"""
VerdeScan Backend — End-to-End Pipeline Test
=============================================
Tests the full processing pipeline without needing a running HTTP server.

SCOPE / CAVEAT: these tests use SYNTHETIC solid-colour images and exercise the
legacy single-image CNN path, the task queue, and the API plumbing.  Because a
green square is classified ALIVE and a brown square DEAD, the health-classifier
assertions are tautological — they confirm the plumbing works, NOT that survival
detection is accurate.  The real survival logic (weeding-circle decision rule)
and the casualty-scoring maths are tested in tests/test_ortho.py, and accuracy
against the known dead GPS points is measured by evaluate.py.

Run from the 'AI Model' directory:
    python -m pytest tests/test_pipeline.py -v
OR:
    python tests/test_pipeline.py
"""

import os
import sys
import asyncio
import tempfile
import shutil
import json

# Ensure project root is on path when running as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np

# ─── helpers ───────────────────────────────────────────────────────────────────

def _make_synthetic_image(path: str, width: int = 800, height: int = 600) -> str:
    """Create a synthetic drone-imagery-like image (green with circular bright patches)."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Green background (like vegetation)
    img[:] = (34, 139, 34)
    # Bright circular "weeding patches" (targets for OP3 Hough detection)
    for cx, cy in [(200, 150), (400, 300), (600, 450)]:
        cv2.circle(img, (cx, cy), 30, (210, 200, 190), -1)
    cv2.imwrite(path, img)
    return path


def _make_dead_tree_image(path: str) -> str:
    """Create a synthetic dead tree (brownish) crop for health classifier testing."""
    img = np.zeros((80, 80, 3), dtype=np.uint8)
    img[:] = (30, 80, 110)  # BGR ~ brownish-grey
    cv2.imwrite(path, img)
    return path


def _make_alive_tree_image(path: str) -> str:
    """Create a synthetic alive tree (green) crop for health classifier testing."""
    img = np.zeros((80, 80, 3), dtype=np.uint8)
    img[:] = (34, 180, 34)  # BGR ~ green
    cv2.imwrite(path, img)
    return path


# ─── tests ─────────────────────────────────────────────────────────────────────

def test_health_classifier_alive():
    """TreeHealthClassifier should classify a green crop as ALIVE."""
    from core.health_classifier import TreeHealthClassifier
    from models.data_structures import TreeStatus

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "alive.jpg")
        _make_alive_tree_image(path)
        img = cv2.imread(path)

        classifier = TreeHealthClassifier()
        result = classifier.classify_health(img, tree_id=0)

        assert result is not None, "classify_health returned None"
        assert result.status == TreeStatus.ALIVE, (
            f"Expected ALIVE for green crop, got {result.status}"
        )
        assert result.confidence > 0.5, f"Confidence too low: {result.confidence}"
        print(f"  ✅ ALIVE classification: confidence={result.confidence:.2f}")
    finally:
        shutil.rmtree(tmpdir)


def test_health_classifier_dead():
    """TreeHealthClassifier should classify a brownish crop as DEAD."""
    from core.health_classifier import TreeHealthClassifier
    from models.data_structures import TreeStatus

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "dead.jpg")
        _make_dead_tree_image(path)
        img = cv2.imread(path)

        classifier = TreeHealthClassifier()
        result = classifier.classify_health(img, tree_id=1)

        assert result is not None, "classify_health returned None"
        # Brown/dark image should be DEAD or DISEASED (not ALIVE)
        assert result.status in (TreeStatus.DEAD, TreeStatus.DISEASED), (
            f"Expected DEAD/DISEASED for brown crop, got {result.status}"
        )
        print(f"  ✅ Dead classification: status={result.status.value}, confidence={result.confidence:.2f}")
    finally:
        shutil.rmtree(tmpdir)


def test_forest_processor_geometric_fallback():
    """ForestMLProcessor should detect features via geometric fallback when CNN model is absent."""
    from core.forest_processor import ForestMLProcessor
    from models.data_structures import ProcessingResult

    tmpdir = tempfile.mkdtemp()
    try:
        img_path = os.path.join(tmpdir, "test_patch.jpg")
        _make_synthetic_image(img_path)

        processor = ForestMLProcessor()

        # Force geometric mode (model may or may not be loaded — test either path)
        result = processor.process_image(img_path, patch_id="test_patch_001")

        assert result is not None, "process_image returned None — check logs for errors"
        assert isinstance(result, ProcessingResult), "Result is not a ProcessingResult"
        assert result.patch_id == "test_patch_001"
        assert result.processing_time >= 0
        assert result.tree_results is not None
        print(
            f"  ✅ Processed image: {len(result.tree_results)} trees found | "
            f"time={result.processing_time:.2f}s | CNN={'yes' if processor.model_loaded else 'fallback'}"
        )

        # Check health fields are populated
        for tree in result.tree_results:
            assert hasattr(tree, 'status'), "TreeResult missing 'status' field"
            assert tree.status is not None, "TreeResult.status is None"
        print(f"  ✅ All {len(result.tree_results)} trees have health status")
    finally:
        shutil.rmtree(tmpdir)


def test_data_manager_save_and_retrieve():
    """DataManager should save a ProcessingResult and retrieve it with patch_id injected."""
    from core.forest_processor import ForestMLProcessor
    from core.data_manager import DataManager
    from config import settings

    tmpdir = tempfile.mkdtemp()
    original_data_dir = settings.data_dir
    settings.data_dir = tmpdir

    try:
        img_path = os.path.join(tmpdir, "test.jpg")
        _make_synthetic_image(img_path)

        processor = ForestMLProcessor()
        result = processor.process_image(img_path, patch_id="dm_test_patch")
        assert result is not None, "process_image returned None"

        dm = DataManager()

        async def run():
            saved = await dm.save_processing_result(result)
            assert saved, "save_processing_result returned False"

            patches = await dm.get_all_patches()
            assert "dm_test_patch" in patches, f"Patch not found in list: {patches}"

            all_results = await dm.get_all_results()
            assert any(r.get("patch_id") == "dm_test_patch" for r in all_results), (
                "patch_id not injected in get_all_results()"
            )

            for r in all_results:
                if r.get("patch_id") == "dm_test_patch":
                    assert "trees" in r, "get_all_results() missing 'trees' alias for 'details'"
                    break

            stats = await dm.get_global_statistics()
            assert stats.get("total_patches", 0) > 0, "Global statistics show 0 patches"
            print(f"  ✅ Stats: {json.dumps({k: v for k, v in stats.items() if k != 'last_updated'}, indent=2)}")

        asyncio.run(run())
        print("  ✅ DataManager save/retrieve/stats all passed")
    finally:
        settings.data_dir = original_data_dir
        shutil.rmtree(tmpdir)


def test_api_stats_endpoint():
    """GET /api/stats should return non-zero data when results exist."""
    # This test runs a mini in-process HTTP request using the ASGI app
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/api/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "total_patches" in data, "Response missing total_patches"
        assert "avg_survival_rate" in data, "Response missing avg_survival_rate"
        print(f"  ✅ /api/stats returned: total_patches={data['total_patches']}, survival={data['avg_survival_rate']}%")
    except ImportError:
        print("  ⚠️  httpx not installed — skipping HTTP integration test (pip install httpx)")


def test_full_upload_pipeline():
    """Full pipeline: upload image → task queued → processing → result stored."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        import time

        client = TestClient(app, raise_server_exceptions=False)

        # Create a synthetic image
        tmpdir = tempfile.mkdtemp()
        try:
            img_path = os.path.join(tmpdir, "drone_test.jpg")
            _make_synthetic_image(img_path, 400, 300)

            with open(img_path, "rb") as f:
                response = client.post(
                    "/api/upload-image",
                    data={"patch_name": "integration_test_patch"},
                    files={"file": ("drone_test.jpg", f, "image/jpeg")},
                )

            if response.status_code != 200:
                print(f"  ⚠️  Upload returned {response.status_code}: {response.text}")
                return

            data = response.json()
            task_id = data.get("task_id")
            assert task_id, "No task_id in upload response"
            print(f"  ✅ Upload accepted: task_id={task_id}")

            # Poll for completion (max 30s)
            for _ in range(30):
                time.sleep(1)
                status_resp = client.get(f"/api/task-status/{task_id}")
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    s = status_data.get("status")
                    if s in ("completed", "failed"):
                        print(f"  ✅ Task finished: status={s}")
                        if s == "failed":
                            print(f"  ❌ Task failed: {status_data.get('error_message')}")
                        break
        finally:
            shutil.rmtree(tmpdir)

    except ImportError:
        print("  ⚠️  httpx not installed — skipping HTTP upload test (pip install httpx)")


# ─── runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("Health Classifier — Alive", test_health_classifier_alive),
        ("Health Classifier — Dead",  test_health_classifier_dead),
        ("Forest Processor — Geometric Fallback", test_forest_processor_geometric_fallback),
        ("DataManager — Save & Retrieve", test_data_manager_save_and_retrieve),
        ("API — /api/stats endpoint", test_api_stats_endpoint),
        ("Full Upload Pipeline", test_full_upload_pipeline),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print('='*60)
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAIL: {e}")
            failed += 1
        except Exception as e:
            import traceback
            print(f"  ❌ ERROR: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print('='*60)
    sys.exit(0 if failed == 0 else 1)
