import shutil
import tempfile
from pathlib import Path

from scripts.export_courses import build_site


def test_export_includes_viewer_css(tmp_path):
    # Build site into tmp_path/public using the repository's courses folder
    out_dir = tmp_path / "public"
    courses_dir = Path("courses")
    # Ensure courses directory exists for the test; if not, skip
    if not courses_dir.exists():
        import pytest

        pytest.skip("No courses directory present for smoke test")

    build_site(courses_dir, out_dir)

    # Find at least one course output and assert _static/canvas_viewer.css exists
    found = False
    for course in out_dir.iterdir():
        if course.is_dir():
            css = course / "_static" / "canvas_viewer.css"
            if css.exists():
                found = True
                break

    assert found, "Expected at least one course to contain _static/canvas_viewer.css"
