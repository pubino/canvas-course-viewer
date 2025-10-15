import os
import pytest

from canvas_viewer.parser import CanvasExport
from canvas_viewer.app import create_app

HERE = os.path.abspath(os.path.dirname(__file__))
EX1 = os.path.join(HERE, '..', 'examples', 'orf245-egr245-f2020-fundamentals-of-statistics-export')
EX2 = os.path.join(HERE, '..', 'examples', 'orf455-ene455-f2020-energy-and-commodities-markets-export')


def test_get_modules_non_empty():
    e1 = CanvasExport(EX1)
    mods1 = e1.get_modules()
    assert isinstance(mods1, list)
    assert len(mods1) >= 1

    e2 = CanvasExport(EX2)
    mods2 = e2.get_modules()
    assert isinstance(mods2, list)
    assert len(mods2) >= 1


def test_home_and_modules_routes():
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
