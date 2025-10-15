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

2. Serve an extracted export folder locally:

```bash
python serve.py --src courses/minimal-course-export
```

Open the URL printed by the server after starting `serve.py` (for example, http://127.0.0.1:<port>). The app selects an available port and intentionally avoids binding to port 5000 on macOS to prevent conflicts.

Notes:
- This is an initial implementation that parses `imsmanifest.xml` and serves files referenced in `wiki_content/`, `web_resources/`, and files listed in the manifest. It uses Flask and a simple parser.

Using this repository with your own course exports
-------------------------------------------------

If you'd like to publish your own course exports using this project, follow these steps:

1. Fork this repository to your GitHub account.
2. Add your exported course files into the `courses/` directory of your fork. You can add either:
	 - an extracted course folder (containing `imsmanifest.xml`, `wiki_content/`, `web_resources/`, etc.), or
	 - a `.zip` or `.imscc` archive; the workflow will unzip archives into sibling folders before building.
3. Commit and push your changes to your fork (do not push large private exports to public forks unless you intend to publish them).
4. In the repository Actions tab, run the "Manual Publish Courses" workflow (or wait for your configured trigger). The workflow will build the site and publish `public/` to `gh-pages` — the workflow will create `gh-pages` if it doesn't already exist.
5. After the workflow finishes, enable GitHub Pages for your fork: Settings -> Pages -> Branch -> `gh-pages` (select the published `gh-pages` branch).

This section has been promoted for visibility — keep course exports out of public forks unless you intend to publish them.

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
 - A tiny, committed example (`courses/minimal-course-export`) is provided so CI can run without large exports.
- Run tests locally with:

```bash
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

If you add new course exports for debugging, prefer to keep them out of the repository or add them to `.git/info/exclude` locally so they won't be committed.

Manual CI workflow (GitHub Actions)
----------------------------------

This repository includes a manually-triggered workflow that builds a tiny static site from the course exports and publishes it to the `gh-pages` branch. The workflow is available under `.github/workflows/manual_publish.yml` and is triggered via the Actions UI (Workflow -> Manual Publish Courses -> Run workflow).

What the workflow does (high level):

- Checks out the repository and sets up Python.
- Unzips any `.zip` or `.imscc` archives found in the `courses/` directory into sibling folders.
- For each directory that contains an `imsmanifest.xml`, the workflow runs `scripts/export_courses.py` which copies `wiki_content/`, `web_resources/`, and `course_settings/` into a per-course folder inside the generated `public/` directory and writes a minimal `index.html` page for each course.
- After building, the `public/` directory is published to the `gh-pages` branch via the `peaceiris/actions-gh-pages` action.

Why this is manual: untrusted uploaded course exports may contain arbitrary files. Requiring a human to trigger the job (via workflow_dispatch) reduces accidental publishing and gives maintainers a chance to review changes before the site is published.

How to run locally (same as CI):

```bash
python scripts/export_courses.py --courses-dir courses --output-dir public
# then serve `public/` with any static server (or open the generated files locally)
```


Optional: automatic publishing on changes to `courses/`
----------------------------------------------------

If you prefer to publish automatically when files in `courses/` change, edit `.github/workflows/manual_publish.yml` and replace the `on:` block with something that watches the `courses/` path, for example:

```yaml
on:
	push:
		paths:
			- 'courses/**'
```

This will trigger the workflow on pushes that modify `courses/`. Be cautious: publishing unreviewed uploads automatically can expose private content.

Security note
-------------

Course exports may contain arbitrary files. For public repositories, ensure you do not commit private student data or sensitive materials. The workflow is manual by default to reduce accidental publishing; keep it manual unless you control the uploaded content.

<!-- Removed: customization offer to keep README concise -->
