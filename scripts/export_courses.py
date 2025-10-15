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

    # build a simple index.html for the course
    pages = exp.list_pages()
    files = exp.get_files()
    modules = exp.get_modules()

    idx_lines = [
        '<!doctype html>',
        '<html><head><meta charset="utf-8"><title>%s</title></head><body>' % (name,),
        f'<h1>{name}</h1>',
        '<h2>Pages</h2>',
        '<ul>'
    ]
    for p in pages:
        href = p.get('href')
        # link relative to course root
        idx_lines.append(f'<li><a href="./{href}">{p.get("title") or href}</a></li>')
    idx_lines.append('</ul>')

    idx_lines.append('<h2>Files</h2><ul>')
    for f in files:
        href = f.get('href')
        idx_lines.append(f'<li><a href="./{href}">{f.get("title")}</a> ({f.get("date") or "—"})</li>')
    idx_lines.append('</ul>')

    if modules:
        idx_lines.append('<h2>Modules</h2>')
        for m in modules:
            idx_lines.append(f'<h3>{m.get("title")}</h3><ul>')
            for it in m.get('items'):
                href = it.get('href') or '#'
                idx_lines.append(f'<li><a href="./{href}">{it.get("title")}</a></li>')
            idx_lines.append('</ul>')

    idx_lines.append('<p><a href="../index.html">Back to courses index</a></p>')
    idx_lines.append('</body></html>')

    with open(course_out / 'index.html', 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(idx_lines))

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

                    # Prefer relative path from the HTML file to _static (use './_static/...')
                    existing = head.xpath("link[contains(@href, 'canvas_viewer.css')]")
                    if not existing:
                        link = lh.Element('link', rel='stylesheet', href='./_static/canvas_viewer.css')
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


def build_site(courses_dir: Path, out_dir: Path):
    # ensure out_dir is clean
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # first unzip any archives
    unzip_archives(courses_dir)

    course_names = []
    for p in sorted(courses_dir.iterdir()):
        if p.is_dir() and (p / 'imsmanifest.xml').exists():
            build_course(p, out_dir)
            course_names.append((p.name, p))

    # write root index.html
    lines = ['<!doctype html>', '<html><head><meta charset="utf-8"><title>Courses</title></head><body>', '<h1>Courses</h1>', '<ul>']
    for name, p in course_names:
        lines.append(f'<li><a href="./{name}/index.html">{name}</a></li>')
    lines.append('</ul>')
    lines.append('</body></html>')

    with open(out_dir / 'index.html', 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))


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
