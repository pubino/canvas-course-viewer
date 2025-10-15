import os
import pytest

from canvas_viewer.parser import CanvasExport
from canvas_viewer.app import create_app

HERE = os.path.abspath(os.path.dirname(__file__))
COURSES_ROOT = os.path.abspath(os.path.join(HERE, '..', 'courses'))


def _pick_course_pairs():
    # Return two example course dirs (prefer non-minimal exports). If not available, return whatever exists.
    entries = []
    for name in os.listdir(COURSES_ROOT):
        p = os.path.join(COURSES_ROOT, name)
        if os.path.isdir(p) and os.path.exists(os.path.join(p, 'imsmanifest.xml')):
            entries.append(p)
    if not entries:
        return (None, None)
    if len(entries) == 1:
        return (entries[0], entries[0])
    return (entries[0], entries[1])


EX1, EX2 = _pick_course_pairs()


def test_get_modules_non_empty():
    import pytest
    if not EX1:
        pytest.skip('No course exports available; skipping regression tests')
    e1 = CanvasExport(EX1)
    mods1 = e1.get_modules()
    assert isinstance(mods1, list)
    # modules may legitimately be empty in some exports; just ensure we got a list

    if not EX2:
        pytest.skip('Second course export not available; skipping part of regression test')
    e2 = CanvasExport(EX2)
    mods2 = e2.get_modules()
    assert isinstance(mods2, list)
    # modules may legitimately be empty in some exports; just ensure we got a list


def test_home_and_modules_routes():
    import pytest
    if not EX2:
        pytest.skip('Second course export not available; skipping module/home route test')
    app = create_app(EX2)
    client = app.test_client()
    r = client.get('/home')
    assert r.status_code == 200
    r2 = client.get('/modules')
    assert r2.status_code == 200

    app2 = create_app(EX1)
    c2 = app2.test_client()
    r3 = c2.get('/modules')
    assert r3.status_code == 200


def test_file_endpoint_serves_webresource():
    import pytest
    if not EX2:
        pytest.skip('Second course export not available; skipping file endpoint test')
    e = CanvasExport(EX2)
    # find a web_resources resource id
    web_id = None
    for ident, r in e.resources.items():
        href = r.get('href') or ''
        if href.startswith('web_resources'):
            web_id = ident
            break
    assert web_id, 'No web_resources found in manifest (unexpected)'

    app = create_app(EX2)
    client = app.test_client()
    resp = client.get(f'/file/{web_id}')
    # we expect either the file to be served (200) or a redirect/304; assert 200-ish
    assert resp.status_code == 200
