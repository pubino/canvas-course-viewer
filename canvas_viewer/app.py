import os
import json
from datetime import datetime
from flask import Flask, send_file, render_template, abort, send_from_directory, Response, url_for
from .parser import CanvasExport
from lxml import html
import io
import posixpath
from urllib.parse import urljoin, urlparse


def create_app(export_path):
    # disable Flask's automatic static handling so our custom /static route is used
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'), static_folder=None)
    export = CanvasExport(export_path)

    @app.context_processor
    def inject_nav():
        # compute availability of top-level sections so templates can hide empty menu items
        cats = export.categorize_resources()
        pages = export.get_pages_by_folder('wiki_content')
        files = export.get_files()
        mods = export.get_modules()
        return {
            'nav': {
                'home': bool(pages) or bool(export.get_syllabus()),
                'syllabus': bool(export.get_syllabus()),
                'announcements': bool(cats.get('announcements')),
                'modules': bool(mods),
                'pages': bool(pages),
                'files': bool(files),
                'quizzes': bool(cats.get('quizzes')),
                'discussions': bool(cats.get('discussions')),
                'people': bool(cats.get('people')),
            }
        }

    @app.route('/')
    def index():
        pages = export.list_pages()
        title = export.title or os.path.basename(export_path)
        metadata = export.get_course_metadata()
        external_tools = export.detect_external_tools()
        has_external_tools = bool(external_tools)
        # assets: include web_resources and course_settings files as 'assets'
        assets = [p for p in pages if p.get('href') and (p.get('href').startswith('web_resources') or p.get('href').startswith('course_settings'))]
        return render_template('index.html', pages=pages, title=title, organizations=export.organizations, metadata=metadata, assets=assets, external_tools=external_tools, has_external_tools=has_external_tools)

    @app.route('/page/<path:href>')
    def page(href):
        # href is a path relative to export
        full = export.resolve_path(href)
        if full and os.path.exists(full):
            # if HTML, render directly; otherwise send as file
            if full.lower().endswith('.html'):
                # rewrite local links to point to /static/<path> or /page/<path>
                with open(full, 'rb') as f:
                    raw = f.read()
                try:
                    doc = html.fromstring(raw)
                except Exception:
                    return send_file(full)

                # base directory for resolving relative links
                base_dir = posixpath.dirname(href)
                # remove embedded <style> blocks and external stylesheet links from exported pages
                try:
                    for s in doc.xpath('//style'):
                        parent = s.getparent()
                        if parent is not None:
                            parent.remove(s)
                except Exception:
                    pass
                try:
                    for l in doc.xpath('//link'):
                        rel = (l.get('rel') or '').lower()
                        # if it's a stylesheet link, remove it so our site CSS wins
                        if 'stylesheet' in rel or (l.get('type') or '').lower() == 'text/css':
                            parent = l.getparent()
                            if parent is not None:
                                parent.remove(l)
                except Exception:
                    pass

                def rewrite_attr(val):
                    if not val:
                        return val
                    parsed = urlparse(val)
                    # leave absolute URLs alone
                    if parsed.scheme in ('http', 'https', 'mailto') or val.startswith('//'):
                        return val
                    # handle anchors
                    if val.startswith('#'):
                        return val
                    # handle Canvas course reference links like $CANVAS_COURSE_REFERENCE$/modules
                    if val.startswith('$CANVAS_COURSE_REFERENCE$'):
                        tail = val.replace('$CANVAS_COURSE_REFERENCE$', '').lstrip('/')
                        # map known route names
                        if tail.startswith('modules'):
                            return '/modules'
                        if tail.startswith('pages'):
                            return '/pages'
                        return '/' + tail
                    # handle IMS filebase placeholders by mapping to web_resources
                    if val.startswith('$IMS-CC-FILEBASE$'):
                        tail = val.replace('$IMS-CC-FILEBASE$', '').lstrip('/')
                        return '/static/web_resources/' + tail
                    # build normalized path relative to base_dir
                    joined = posixpath.normpath(posixpath.join(base_dir, val)) if not posixpath.isabs(val) else val.lstrip('/')
                    # if it points to html -> page route
                    if joined.lower().endswith('.html'):
                        return '/page/' + joined
                    # otherwise serve as static
                    return '/static/' + joined

                # strip inline style attributes so the app's CSS takes precedence
                for el in doc.xpath('//*'):
                    # remove inline style attributes which would otherwise override site CSS
                    if 'style' in el.attrib:
                        try:
                            del el.attrib['style']
                        except Exception:
                            pass
                # rewrite tags (after stripping inline styles and removing stylesheet links)
                for el in doc.xpath('//*'):
                    tag = el.tag.lower() if hasattr(el, 'tag') else ''
                    if tag == 'img' and el.get('src'):
                        el.set('src', rewrite_attr(el.get('src')))
                    if tag == 'a' and el.get('href'):
                        el.set('href', rewrite_attr(el.get('href')))
                    # link tags have been mostly removed; if remaining and have href, rewrite
                    if tag == 'link' and el.get('href'):
                        el.set('href', rewrite_attr(el.get('href')))
                    if tag == 'script' and el.get('src'):
                        el.set('src', rewrite_attr(el.get('src')))

                out = html.tostring(doc, encoding='unicode', pretty_print=True)
                # render inside page layout so nav/sidebar persist
                return render_template('page.html', content=out, title=os.path.basename(href), organizations=export.organizations)
            return send_file(full, as_attachment=False)
        abort(404)

    from urllib.parse import unquote

    @app.route('/static/<path:filename>')
    def static_files(filename):
        # decode URL-encoded parts (e.g., %20 -> space)
        filename = unquote(filename)
        print(f"[static] request for: {filename}")
        # 1) check package-level static (canvas_viewer/static/...)
        pkg_static_dir = os.path.join(app.root_path, 'static')
        pkg_candidate = os.path.join(pkg_static_dir, filename)
        print(f"[static] pkg_candidate: {pkg_candidate} exists={os.path.exists(pkg_candidate)}")
        if os.path.exists(pkg_candidate):
            try:
                return send_file(pkg_candidate)
            except Exception as e:
                print(f"[static] send_file failed for pkg_candidate: {e}")

        # 2) check project-level static (../static/...)
        project_root = os.path.dirname(app.root_path)
        project_static_dir = os.path.join(project_root, 'static')
        project_candidate = os.path.join(project_static_dir, filename)
        print(f"[static] project_candidate: {project_candidate} exists={os.path.exists(project_candidate)}")
        if os.path.exists(project_candidate):
            try:
                return send_file(project_candidate)
            except Exception as e:
                print(f"[static] send_file failed for project_candidate: {e}")

        # 3) check inside the exported course folder
        # attempt variants in case of placeholders like $IMS-CC-FILEBASE$ or $CANVAS_COURSE_REFERENCE$
        candidates = [
            filename,
            filename.replace('$IMS-CC-FILEBASE$/', ''),
            filename.replace('$IMS-CC-FILEBASE$', ''),
            filename.replace('$CANVAS_COURSE_REFERENCE$/', ''),
            filename.replace('$CANVAS_COURSE_REFERENCE$', ''),
        ]
        for cand in candidates:
            full = os.path.join(export_path, cand)
            print(f"[static] export candidate: {full} exists={os.path.exists(full)}")
            if os.path.exists(full):
                try:
                    return send_file(full)
                except Exception as e:
                    print(f"[static] send_file failed for export candidate {full}: {e}")

        # 4) special-case: uploaded media often lives in web_resources/<Uploaded Media...>
        # try to map any path that contains 'Uploaded Media' or comes from $IMS-CC-FILEBASE$
        def try_web_resources(p):
            # strip any leading directories like 'wiki_content/'
            parts = p.split('/', 1)
            rest = parts[1] if len(parts) > 1 else parts[0]
            web_candidate = os.path.join(export_path, 'web_resources', rest)
            if os.path.exists(web_candidate):
                return os.path.join('web_resources', rest)
            return None

        # attempt mapping for original filename and decoded variants
        for orig in [filename]:
            mapped = try_web_resources(orig)
            if mapped:
                mapped_full = os.path.join(export_path, mapped)
                print(f"[static] mapped candidate: {mapped_full} exists={os.path.exists(mapped_full)}")
                if os.path.exists(mapped_full):
                    try:
                        return send_file(mapped_full)
                    except Exception as e:
                        print(f"[static] send_file failed for mapped_full {mapped_full}: {e}")

        # 5) as a last resort, search web_resources recursively for a file matching the basename
        base = os.path.basename(filename)
        web_root = os.path.join(export_path, 'web_resources')
        if os.path.exists(web_root):
            print(f"[static] searching web_resources under {web_root} for {base}")
            for root, dirs, files in os.walk(web_root):
                if base in files:
                    found = os.path.join(root, base)
                    print(f"[static] found in web_resources: {found}")
                    try:
                        return send_file(found)
                    except Exception as e:
                        print(f"[static] send_file failed for found {found}: {e}")

        abort(404)

    @app.route('/file/<path:ref>')
    def file_proxy(ref):
        """Serve a file referenced by resource id or by href. This provides a stable link used
        by the Files listing so we don't rely on fragile href->static path heuristics in templates."""
        from urllib.parse import unquote
        # try treating ref as an identifier first
        candidate_resource = export.resources.get(ref)
        # if not an identifier, maybe it's an href path
        if not candidate_resource:
            # allow callers to pass either id or href; try to find resource by href
            candidate_resource = export.href_to_resource(ref)
        # if we found a resource object, attempt to resolve file(s)
        if candidate_resource:
            # prefer any file entries listed in resource.files
            for f in candidate_resource.get('files', []) or []:
                # strip possible placeholders
                fpath = f
                # try direct resolution
                resolved = export.resolve_path(fpath)
                if resolved and os.path.exists(resolved):
                    return send_file(resolved)
                # try variations used by static handler
                alt = os.path.join(export.path, fpath.replace('$IMS-CC-FILEBASE$/', '').replace('$IMS-CC-FILEBASE$', ''))
                if os.path.exists(alt):
                    return send_file(alt)
            # fallback: try href field on resource
            href = candidate_resource.get('href')
            if href:
                resolved = export.resolve_path(href)
                if resolved and os.path.exists(resolved):
                    return send_file(resolved)

        # if ref looks like a path, try resolving relative to export
        ref_decoded = unquote(ref)
        tried = []
        p = export.resolve_path(ref_decoded)
        if p and os.path.exists(p):
            return send_file(p)
        # try removing placeholder prefixes
        for cand in [ref_decoded, ref_decoded.replace('$IMS-CC-FILEBASE$/', ''), ref_decoded.replace('$IMS-CC-FILEBASE$', ''), ref_decoded.replace('$CANVAS_COURSE_REFERENCE$/', ''), ref_decoded.replace('$CANVAS_COURSE_REFERENCE$', '')]:
            p2 = os.path.join(export_path, cand)
            tried.append(p2)
            if os.path.exists(p2):
                return send_file(p2)

        # last resort: search web_resources by basename
        base = os.path.basename(ref_decoded)
        web_root = os.path.join(export_path, 'web_resources')
        if os.path.exists(web_root):
            for root, dirs, files in os.walk(web_root):
                if base in files:
                    return send_file(os.path.join(root, base))

        abort(404)

    # Course-level sections
    @app.route('/syllabus')
    def syllabus():
        s = export.get_syllabus()
        if not s:
            return render_template('section.html', title='Syllabus', items=[], message='No syllabus found')
        return page(s['href'])

    @app.route('/files')
    def files():
        files = export.get_files()
        return render_template('section.html', title='Files', items=files)

    @app.route('/assignments')
    def assignments():
        assigns = export.get_assignments()
        return render_template('section.html', title='Assignments', items=assigns)

    @app.route('/pages')
    def pages():
        pages = export.get_pages_by_folder('wiki_content')
        return render_template('section.html', title='Pages', items=pages)

    @app.route('/home')
    def home():
        # try to pick a course welcome/homepage resource
        # check a few common filenames first, then fall back to the first wiki_content page
        candidates = [
            'wiki_content/homepage.html',
            'wiki_content/home.html',
            'wiki_content/welcome.html',
            'wiki_content/welcome-to-orf-245-fall-2020.html',
        ]
        for c in candidates:
            res = export.href_to_resource(c)
            if res:
                return page(res['href'])

        # fall back to the first wiki_content page found in the manifest
        pages = export.get_pages_by_folder('wiki_content')
        if pages:
            return page(pages[0]['href'])

        return render_template('section.html', title='Home', items=[], message='Welcome!')

    @app.route('/announcements')
    def announcements():
        cats = export.categorize_resources()
        items = cats.get('announcements', [])
        return render_template('section.html', title='Announcements', items=items)

    @app.route('/modules')
    def modules():
        mods = export.get_modules()
        return render_template('modules.html', title='Modules', modules=mods)

    @app.route('/canvas-data')
    def canvas_data():
        # curated metadata page (Canvas Data)
        meta = export.get_course_metadata()
        # derived counts
        pages = export.get_pages_by_folder('wiki_content')
        files = export.get_files()
        mods = export.get_modules()
        cats = export.categorize_resources()
        counts = {
            'pages': len(pages),
            'files': len(files),
            'modules': len(mods),
            'quizzes': len(cats.get('quizzes') or []),
            'discussions': len(cats.get('discussions') or []),
            'announcements': len(cats.get('announcements') or []),
        }
        # humanize some fields for display
        def yesno(v):
            return 'Yes' if v == 'true' or v is True else ('No' if v == 'false' or v is False else (v or '—'))

        def human_size(bytes_str):
            try:
                b = int(bytes_str)
            except Exception:
                return bytes_str or '—'
            for unit in ['B','KB','MB','GB','TB']:
                if b < 1024:
                    # show as integer for smaller units
                    if unit == 'B':
                        return f"{int(b)}{unit}"
                    return f"{b:.0f}{unit}"
                b = b/1024
            return f"{b:.1f}PB"

        def human_date(iso_str):
            if not iso_str:
                return '—'
            s = iso_str
            try:
                # accommodate trailing Z (UTC)
                if s.endswith('Z'):
                    s = s.replace('Z', '+00:00')
                dt = datetime.fromisoformat(s)
                # include timezone name if present, otherwise omit
                if dt.tzinfo:
                    return dt.strftime("%b %d, %Y %H:%M %Z")
                return dt.strftime("%b %d, %Y %H:%M")
            except Exception:
                # fallback to original string
                return iso_str or '—'

        # pretty-print tab configuration JSON if available
        pretty_tab = '—'
        raw_tab = meta.get('tab_configuration')
        if raw_tab:
            try:
                obj = json.loads(raw_tab)
                pretty_tab = json.dumps(obj, indent=2)
            except Exception:
                # already not-valid JSON: show as-is
                pretty_tab = raw_tab

        human = {
            'title': meta.get('title') or (export.title or os.path.basename(export_path)),
            'course_code': meta.get('course_code') or '—',
            'start_at': human_date(meta.get('start_at')),
            'conclude_at': human_date(meta.get('conclude_at')),
            'is_public': yesno(meta.get('is_public')),
            'public_syllabus': yesno(meta.get('public_syllabus')),
            'storage_quota': human_size(meta.get('storage_quota')),
            'grading_standard_id': meta.get('grading_standard_id') or '—',
            'tab_configuration': pretty_tab,
        }
        external_tools = export.detect_external_tools()
        has_external_tools = bool(external_tools)
        # allowed base domain(s) can be configured via CANVAS_BASE_DOMAIN (comma-separated).
        # default matches any *.instructure.com host.
        raw_base = os.environ.get('CANVAS_BASE_DOMAIN', 'https://*.instructure.com')
        base_domains = [d.strip() for d in raw_base.split(',') if d.strip()]
        # find external links not pointing to the configured base domains
        external_links = export.find_external_links(allowed_domains=base_domains)
        return render_template('canvas_data.html', title='Canvas Data', metadata=meta, counts=counts, human=human, external_tools=external_tools, has_external_tools=has_external_tools, external_links=external_links, base_domain=raw_base)

    @app.route('/quizzes')
    def quizzes():
        cats = export.categorize_resources()
        items = cats.get('quizzes', [])
        return render_template('section.html', title='Quizzes', items=items)

    @app.route('/discussions')
    def discussions():
        cats = export.categorize_resources()
        items = cats.get('discussions', [])
        return render_template('section.html', title='Discussions', items=items)

    @app.route('/people')
    def people():
        cats = export.categorize_resources()
        items = cats.get('people', [])
        return render_template('section.html', title='People', items=items)

    def rewrite_link_target(path):
        # helper to route href/src to either /page or /static depending on file type
        if not path:
            return path
        p = path.split('#')[0].split('?')[0]
        # local relative
        if p.startswith('http://') or p.startswith('https://') or p.startswith('mailto:'):
            return path
        # absolute-like starting with '/'
        if p.startswith('/'):
            # strip leading /
            p = p.lstrip('/')
        # if html -> page route
        if p.lower().endswith('.html'):
            return '/page/' + p
        return '/static/' + p

    # small wrapper available in this module scope
    def rewrite_link(path):
        return rewrite_link_target(path)

    return app
