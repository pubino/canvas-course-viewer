import os
from canvas_viewer.parser import CanvasExport


def test_load_example():
    base = os.path.join(os.path.dirname(__file__), '..', 'courses', 'orf245-egr245-f2020-fundamentals-of-statistics-export')
    base = os.path.abspath(base)
    exp = CanvasExport(base)
    assert exp.title is not None
    assert isinstance(exp.resources, dict)

    # categorization should return a dict with common keys (may be empty lists)
    cats = exp.categorize_resources()
    assert isinstance(cats, dict)
    for key in ('announcements', 'modules', 'quizzes', 'discussions', 'people', 'files'):
        assert key in cats
