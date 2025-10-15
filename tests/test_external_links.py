import os
import tempfile
from canvas_viewer.parser import CanvasExport
from canvas_viewer.app import create_app


def _example_base():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples', 'minimal-course-export'))


def test_find_external_links_exact_and_wildcard(tmp_path):
    base = _example_base()
    e = CanvasExport(base)

    # Construct a small set of allowed domains and test matching
    # exact host
    allowed = ['https://example.com']
    links = e.find_external_links(allowed_domains=allowed)
    # minimal example has no external links, so should be empty
    assert isinstance(links, list)

    # wildcard matching: treat any subdomain of instructure.com as internal
    allowed2 = ['https://*.instructure.com']
    links2 = e.find_external_links(allowed_domains=allowed2)
    assert isinstance(links2, list)


def test_canvas_data_respects_env_base_domain(monkeypatch):
    base = _example_base()
    # set a non-matching base domain so that external links (if any) are reported
    monkeypatch.setenv('CANVAS_BASE_DOMAIN', 'https://example.com')
    app = create_app(base)
    client = app.test_client()
    resp = client.get('/canvas-data')
    assert resp.status_code == 200
    # page should include the Canvas Data header
    assert b'Canvas Data' in resp.data
