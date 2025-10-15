import os
from canvas_viewer.parser import CanvasExport


def test_load_example():
    import os
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'courses'))
    # prefer a non-minimal export when available
    base = None
    for name in os.listdir(root):
        if name == 'minimal-course-export':
            continue
        p = os.path.join(root, name)
        if os.path.isdir(p) and os.path.exists(os.path.join(p, 'imsmanifest.xml')):
            base = p
            break
    if not base:
        # fallback to minimal example
        candidate = os.path.join(root, 'minimal-course-export')
        if os.path.isdir(candidate):
            base = candidate
    import pytest
    if not base or not os.path.exists(os.path.join(base, 'imsmanifest.xml')):
        pytest.skip('No usable course export found under courses/; skipping parser test')
    exp = CanvasExport(base)
    # title may be missing in some exports; ensure resources parsed and categorization returns expected keys
    assert isinstance(exp.resources, dict)

    # categorization should return a dict with common keys (may be empty lists)
    cats = exp.categorize_resources()
    assert isinstance(cats, dict)
    for key in ('announcements', 'modules', 'quizzes', 'discussions', 'people', 'files'):
        assert key in cats
