Canvas Course Viewer
=====================

A small Python app that reconstructs and serves a local web view of an exported Canvas course (Common Cartridge / IMS export).

Usage (from project root):

1. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Serve an extracted export folder:

```bash
python serve.py --export examples/orf245-egr245-f2020-fundamentals-of-statistics-export
```

Open http://127.0.0.1:5000 in your browser.

Notes:
- This is an initial implementation that parses `imsmanifest.xml` and serves files referenced in `wiki_content/`, `web_resources/`, and files listed in the manifest. It uses Flask and a simple parser.

.gitignore policy
------------------
To avoid accidentally committing large or sensitive Canvas export folders, this repository uses a strict `.gitignore` policy:

- By default the repository ignores all files. The only allowed files/folders under `examples/` are:
	- `examples/minimal-course-export/` — a small, committed example used in CI and tests.

- Source code (`canvas_viewer/`), tests (`tests/`), CI workflows (`.github/workflows/`), and supporting files like `requirements.txt`, `README.md`, and `serve.py` are explicitly kept tracked.

If you need to add a larger export folder for local development, add it to your personal git-stash or work on an untracked local branch, or modify `.gitignore` temporarily — but avoid committing large exports into the repository.

App behavior and important notes
--------------------------------
- What is included in an export view:
	- HTML pages and files that are part of the IMS/Canvas export (e.g., `wiki_content/`, `web_resources/`, and `course_settings` files). The app rewrites links in exported HTML so they route through the local viewer.
	- A canonical `/file/<id>` endpoint to serve files referenced by resource identifier.
	- A curated "Canvas Data" page which surfaces `course_settings/course_settings.xml` metadata in a human-friendly way.

- What is NOT included (important):
	- Content hosted by external LTI/External Tools (Panopto, Gradescope, Zoom cloud recordings, etc.) is generally NOT bundled with the Canvas export — only links/launch metadata are present. The app includes heuristics to detect these and will show a warning when such integrations are likely present, but it does not retrieve external provider data.

- Static resolution heuristics:
	- The app tries several locations when resolving `/static/<path>` requests: package static, project static, the export folder (with placeholder variants), mapping into `web_resources/`, and finally a recursive basename search in `web_resources`.
	- This multi-stage strategy is intentionally permissive to handle differing export layouts; it may occasionally match files by basename when paths diverge.

- Limitations and edge cases:
	- The viewer attempts to strip inline styles and remove exported stylesheet links so the app's CSS provides a consistent look; complex pages might still render differently than in Canvas.
	- Date/time formatting and metadata extraction are best-effort from `course_settings`. Some fields may be missing depending on the Canvas version and export options.
	- The plugin/LTI detection is heuristic-based. It can produce false positives or miss uncommon integrations. If you rely on this for audits, verify the results manually.

Contributing and tests
----------------------
- A tiny, committed example (`examples/minimal-course-export`) is provided so CI can run without large exports.
- Run tests locally with:

```bash
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

If you add new examples for debugging, prefer to keep them out of the repository or add them to `.git/info/exclude` locally so they won't be committed.
