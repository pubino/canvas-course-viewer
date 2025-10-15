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


def test_wiki_page_and_files():
    import os
    from canvas_viewer.app import create_app
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'courses', 'orf245-egr245-f2020-fundamentals-of-statistics-export'))
    app = create_app(base)
    client = app.test_client()
    # wiki page that contains an uploaded media image
    r = client.get('/page/wiki_content/welcome-to-orf-245-fall-2020.html')
    assert r.status_code == 200
    assert b'Canvas Viewer' in r.data  # navbar present via layout

    r2 = client.get('/files')
    assert r2.status_code == 200
    assert b'Files' in r2.data


def test_orf455_example_pages():
    """Smoke-test the ORF455 export: index, files and a known wiki page from the manifest."""
    import os
    from canvas_viewer.app import create_app

    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'courses', 'orf455-ene455-f2020-energy-and-commodities-markets-export'))
    app = create_app(base)
    client = app.test_client()

    for path in ['/', '/files', '/pages']:
        r = client.get(path)
        assert r.status_code == 200, f'{path} failed with {r.status_code}'

    # a manifest-listed wiki page
    r2 = client.get('/page/wiki_content/homepage.html')
    assert r2.status_code == 200, f'homepage.html returned {r2.status_code}'
    assert b'Canvas Viewer' in r2.data
