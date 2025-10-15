import os


def test_index_renders():
    """Start the Flask app via the factory and GET / using the test client."""
    from canvas_viewer.app import create_app

    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'courses', 'minimal-course-export'))

    app = create_app(base)
    client = app.test_client()
    resp = client.get('/')
    assert resp.status_code == 200
    # should at least include page title / brand
    assert b'Canvas Viewer' in resp.data or b'<title>' in resp.data


def _find_course_dir(prefer=None):
    import os
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'courses'))
    if prefer:
        candidate = os.path.join(root, prefer)
        if os.path.exists(os.path.join(candidate, 'imsmanifest.xml')):
            return candidate
    # prefer non-minimal exports
    for name in os.listdir(root):
        p = os.path.join(root, name)
        if name == 'minimal-course-export':
            continue
        if os.path.isdir(p) and os.path.exists(os.path.join(p, 'imsmanifest.xml')):
            return p
    # fallback to minimal export
    minimal = os.path.join(root, 'minimal-course-export')
    if os.path.isdir(minimal):
        return minimal
    return None


def test_wiki_page_and_files():
    import os
    import pytest
    from canvas_viewer.app import create_app
    base = _find_course_dir(prefer=None)
    if not base:
        pytest.skip('No course exports available under courses/; skipping integration test')
    app = create_app(base)
    client = app.test_client()
    # wiki page that contains an uploaded media image
    r = client.get('/page/wiki_content/welcome-to-orf-245-fall-2020.html')
    assert r.status_code == 200
    assert b'Canvas Viewer' in r.data  # navbar present via layout

    r2 = client.get('/files')
    assert r2.status_code == 200
    assert b'Files' in r2.data


def test_example_pages_smoke():
    """Smoke-test an available course export: index, files and a known wiki page from the manifest."""
    import os
    import pytest
    from canvas_viewer.app import create_app

    base = _find_course_dir()
    if not base:
        pytest.skip('No course exports available under courses/; skipping integration test')
    app = create_app(base)
    client = app.test_client()

    for path in ['/', '/files', '/pages']:
        r = client.get(path)
        assert r.status_code == 200, f'{path} failed with {r.status_code}'

    # a manifest-listed wiki page: pick the first wiki_content page the export knows about
    from canvas_viewer.parser import CanvasExport
    exp = CanvasExport(base)
    pages = exp.get_pages_by_folder('wiki_content')
    if pages:
        first = pages[0].get('href')
        # request via the page endpoint
        r2 = client.get('/page/' + first)
        assert r2.status_code == 200, f'{first} returned {r2.status_code}'
        assert b'Canvas Viewer' in r2.data
    else:
        # no wiki pages present in this export - skip page-specific assertions
        import pytest
        pytest.skip('No wiki_content pages in selected export; skipping page assertions')
