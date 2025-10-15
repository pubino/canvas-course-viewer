#!/usr/bin/env python3
"""Export courses into a static site suitable for GitHub Pages.

This script will:
- Unzip any .zip or .imscc files found in the courses directory (into sibling folders)
- For each extracted course folder containing imsmanifest.xml, build a minimal
  static export: copy wiki_content and web_resources into the output and write
  a simple index.html listing pages, files and modules.

The output directory will contain one subfolder per course and a root index.html.
"""
import argparse
import os
import shutil
import zipfile
from pathlib import Path

from canvas_viewer.parser import CanvasExport
from lxml import html as lh
import jinja2


def unzip_archives(courses_dir: Path):
    for p in courses_dir.iterdir():
        if p.is_file() and p.suffix.lower() in ('.zip', '.imscc'):
            dest = courses_dir / p.stem
            if dest.exists():
                print(f"Skipping unzip; destination exists: {dest}")
                continue
            print(f"Unzipping {p} -> {dest}")
            dest.mkdir(parents=True, exist_ok=True)
            try:
                with zipfile.ZipFile(p, 'r') as z:
                    z.extractall(dest)
            except zipfile.BadZipFile:
                print(f"Warning: {p} is not a valid zip; skipping")


def build_course(export_path: Path, out_path: Path):
    try:
        exp = CanvasExport(str(export_path))
    except Exception as e:
        print(f"Skipping {export_path}: failed to parse manifest: {e}")
        return

    name = exp.title or export_path.name
    print(f"Building course '{name}' from {export_path}")
    course_out = out_path / export_path.name
    course_out.mkdir(parents=True, exist_ok=True)

    # copy wiki_content and web_resources if present
    for sub in ('wiki_content', 'web_resources', 'course_settings'):
        src = export_path / sub
        if src.exists():
            dst = course_out / sub
            if dst.exists():
                shutil.rmtree(dst)
            print(f"Copying {src} -> {dst}")
            shutil.copytree(src, dst)

    # gather pages/files/modules for rendering the richer template below
    pages = exp.list_pages()
    files = exp.get_files()
    modules = exp.get_modules()

    # gather metadata for use in templates and return value
    metadata = exp.get_course_metadata() or {}

    # Render a richer static index using a small Jinja2 template that mimics
    # the interactive viewer but uses local paths for static assets and pages.
    try:
        assets = []
        # combine pages and files for a simplified asset listing
        for p in exp.list_pages():
            assets.append({'title': p.get('title') or p.get('href'), 'href': p.get('href'), 'type': 'page'})
        for f in exp.get_files():
            assets.append({'title': f.get('title') or f.get('href'), 'href': f.get('href'), 'type': 'file'})

        external_tools = exp.detect_external_tools() or []
        has_external_tools = bool(external_tools)

        modules = exp.get_modules() or []

        nav = {
            'home': True,
            'syllabus': bool(exp.get_syllabus()),
            'announcements': False,
            'modules': bool(modules),
            'pages': bool(exp.list_pages()),
            'files': bool(exp.get_files()),
            'quizzes': False,
            'discussions': False,
            'people': False,
        }

        tmpl = jinja2.Template(r"""<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{{ title }}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="./_static/canvas_viewer.css" />
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-light bg-light mb-3">
            <div class="container-fluid">
                <a class="navbar-brand" href="../index.html">Canvas Viewer</a>
                <div class="collapse navbar-collapse">
                    <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                        {% if nav.home %}<li class="nav-item"><a class="nav-link" href="./index.html">Home</a></li>{% endif %}
                        {% if nav.syllabus %}<li class="nav-item"><a class="nav-link" href="./course_settings/syllabus.html">Syllabus</a></li>{% endif %}
                        {% if nav.modules %}<li class="nav-item"><a class="nav-link" href="./index.html#modules">Modules</a></li>{% endif %}
                        {% if nav.pages %}<li class="nav-item"><a class="nav-link" href="./wiki_content/homepage.html">Pages</a></li>{% endif %}
                        {% if nav.files %}<li class="nav-item"><a class="nav-link" href="./index.html#files">Files</a></li>{% endif %}
                    </ul>
                </div>
            </div>
        </nav>

        <main class="container">
            <div class="row">
                <section class="col-12">
                    <div class="card mb-3">
                        <div class="card-body d-flex">
                            <div class="me-3">
                                {% if metadata.image_href %}
                                    <img src="./{{ metadata.image_href }}" alt="Course image" style="max-width:150px; height:auto;"/>
                                {% endif %}
                            </div>
                            <div>
                                <h2 class="h5">{{ metadata.title or title }}</h2>
                                <p class="mb-1"><strong>Course code:</strong> {{ metadata.course_code or '—' }}</p>
                                <p class="mb-1"><strong>Start:</strong> {{ metadata.start_at or '—' }} <strong>End:</strong> {{ metadata.conclude_at or '—' }}</p>
                                <p class="mb-0"><strong>License:</strong> {{ metadata.license or '—' }} <strong>Storage:</strong> {{ metadata.storage_quota or '—' }}</p>
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-header">All Assets</div>
                        {% if has_external_tools %}
                            <div class="card-body">
                                <div class="alert alert-warning mb-0">
                                    <strong>Warning:</strong> This export references external tool integrations that may host course content outside the export. Detected: {{ external_tools | join(', ') }}
                                </div>
                            </div>
                        {% endif %}
                        <div class="table-responsive">
                            <table class="table table-striped table-hover mb-0">
                                <thead><tr><th>Name</th><th>Path</th></tr></thead>
                                <tbody>
                                    {% for a in assets %}
                                        <tr>
                                            <td>{{ a.title or a.href }}</td>
                                            <td>
                                                {% if a.type == 'page' %}
                                                    <a href="./{{ a.href }}">{{ a.href }}</a>
                                                {% else %}
                                                    <a href="./{{ a.href }}">{{ a.href }}</a>
                                                {% endif %}
                                            </td>
                                        </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>
            </div>
        </main>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
</html>""")

        rendered = tmpl.render(title=name, metadata=metadata, assets=assets, external_tools=external_tools, has_external_tools=has_external_tools, nav=nav, modules=modules)
        with open(course_out / 'index.html', 'w', encoding='utf-8') as fh:
            fh.write(rendered)
    except Exception as e:
        print(f"Warning: failed to render rich index for {course_out}: {e}")

    # Copy the viewer's CSS into the course output so the static site can use
    # the same styling as the interactive viewer. We place it in a _static
    # folder inside the course output and inject a link tag into each HTML
    # file under the course (wiki pages, index, etc.) so the pages pick up
    # the styling when served from GitHub Pages.
    try:
        static_src_dir = Path(__file__).resolve().parents[1] / 'canvas_viewer' / 'static'
        if static_src_dir.exists() and static_src_dir.is_dir():
            static_dst = course_out / '_static'
            # Remove old static if present
            if static_dst.exists():
                shutil.rmtree(static_dst)
            shutil.copytree(static_src_dir, static_dst)

            # Inject link tag into all HTML files under the course_out if missing
            for html_file in course_out.rglob('*.html'):
                try:
                    doc = lh.parse(str(html_file))
                    head = doc.find('.//head')
                    if head is None:
                        root = doc.getroot()
                        head = lh.Element('head')
                        root.insert(0, head)
                    # Compute a relative path from the HTML file to the course _static directory
                    # so nested pages correctly resolve the CSS file.
                    relpath = os.path.relpath(static_dst, start=html_file.parent)
                    css_href = os.path.join(relpath, 'canvas_viewer.css').replace(os.path.sep, '/')
                    existing = head.xpath("link[contains(@href, 'canvas_viewer.css')]")
                    if not existing:
                        link = lh.Element('link', rel='stylesheet', href=css_href)
                        if len(head):
                            head.insert(0, link)
                        else:
                            head.append(link)

                        with open(html_file, 'wb') as fh:
                            fh.write(lh.tostring(doc, encoding='utf-8', pretty_print=True, doctype='<!DOCTYPE html>'))
                except Exception:
                    print(f"Warning: failed to inject CSS into {html_file}; skipping")
    except Exception as e:
        print(f"Warning: failed to copy/inject viewer static assets: {e}")

    # Generate static section pages: pages.html (wiki pages), files.html, modules.html
    try:
        # pages.html
        pages_list = exp.get_pages_by_folder('wiki_content')
        pages_tmpl = jinja2.Template(r"""<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{{ title }} - Pages</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="{{ css_href }}" />
    </head>
    <body>
        <main class="container mt-3">
            <h1>Pages</h1>
            <ul>
            {% for p in pages %}
                <li><a href="./{{ p.href }}">{{ p.title or p.href }}</a></li>
            {% endfor %}
            </ul>
            <p><a href="./index.html">Back to course</a></p>
        </main>
    </body>
</html>""")
        # compute css href relative to course root (index is in course root)
        css_href_root = './_static/canvas_viewer.css'
        with open(course_out / 'pages.html', 'w', encoding='utf-8') as fh:
            fh.write(pages_tmpl.render(title=name, pages=pages_list, css_href=css_href_root))

        # files.html
        files_list = exp.get_files()
        files_tmpl = jinja2.Template(r"""<!doctype html>
<html><head>
<meta charset="utf-8"><title>{{ title }} - Files</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="{{ css_href }}" />
</head><body>
<main class="container mt-3">
<h1>Files</h1>
<ul>
{% for f in files %}
    <li><a href="./{{ f.href }}">{{ f.title }}</a> {% if f.date %}({{ f.date }}){% endif %}</li>
{% endfor %}
</ul>
<p><a href="./index.html">Back to course</a></p>
</main></body></html>""")
        with open(course_out / 'files.html', 'w', encoding='utf-8') as fh:
            fh.write(files_tmpl.render(title=name, files=files_list, css_href=css_href_root))

        # modules.html
        modules_list = exp.get_modules()
        modules_tmpl = jinja2.Template(r"""<!doctype html>
<html><head>
<meta charset="utf-8"><title>{{ title }} - Modules</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="{{ css_href }}" />
</head><body>
<main class="container mt-3">
<h1>Modules</h1>
{% for m in modules %}
    <h2>{{ m.title }}</h2>
    <ul>
    {% for it in m.items %}
        <li><a href="./{{ it.href }}">{{ it.title }}</a></li>
    {% endfor %}
    </ul>
{% endfor %}
<p><a href="./index.html">Back to course</a></p>
</main></body></html>""")
        with open(course_out / 'modules.html', 'w', encoding='utf-8') as fh:
            fh.write(modules_tmpl.render(title=name, modules=modules_list, css_href=css_href_root))
    except Exception as e:
        print(f"Warning: failed to render static section pages for {course_out}: {e}")

    # Return course metadata for use by build_site when rendering root index
    return {'name': export_path.name, 'title': name, 'metadata': metadata}


def build_site(courses_dir: Path, out_dir: Path):
    # ensure out_dir is clean
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # first unzip any archives
    unzip_archives(courses_dir)

    course_meta = []
    for p in sorted(courses_dir.iterdir()):
        if p.is_dir() and (p / 'imsmanifest.xml').exists():
            cm = build_course(p, out_dir)
            if cm:
                course_meta.append(cm)

    # write root index.html
        # Render a styled root index.html that lists courses
        try:
                root_tmpl = jinja2.Template(r"""<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Courses</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="./_static/canvas_viewer.css" />
    </head>
    <body>
        <main class="container mt-3">
            <h1>Courses</h1>
            <div class="list-group">
                {% for c in courses %}
                    <a class="list-group-item list-group-item-action" href="./{{ c.name }}/index.html">{{ c.title or c.name }}</a>
                {% endfor %}
            </div>
        </main>
    </body>
</html>""")
                # ensure top-level _static exists and contains viewer assets
                static_src_dir = Path(__file__).resolve().parents[1] / 'canvas_viewer' / 'static'
                if static_src_dir.exists() and static_src_dir.is_dir():
                        top_static = out_dir / '_static'
                        if top_static.exists():
                                shutil.rmtree(top_static)
                        shutil.copytree(static_src_dir, top_static)

                with open(out_dir / 'index.html', 'w', encoding='utf-8') as fh:
                        fh.write(root_tmpl.render(courses=course_meta))
        except Exception as e:
                print(f"Warning: failed to render root index: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--courses-dir', default='courses', help='Directory containing course exports')
    ap.add_argument('--output-dir', default='public', help='Directory to write the static site')
    args = ap.parse_args()

    courses_dir = Path(args.courses_dir)
    out_dir = Path(args.output_dir)

    if not courses_dir.exists():
        print(f"Courses directory not found: {courses_dir}")
        return

    build_site(courses_dir, out_dir)


if __name__ == '__main__':
    main()
