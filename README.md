# Canvas Course Viewer

A small Python app that serves a web view of an exported Canvas course.

This implementation parses `imsmanifest.xml` and serves files referenced in `wiki_content/`, `web_resources/`, and any other files listed in the manifest.

It uses a very simple parser and may not represent the full extent of the exported data.  If in doubt, upload and import to a Canvas instance.

## Publish Course Exports

If you'd like to publish your own course exports:

1. Fork this Github repository.
2. Add your exported course files (`.imscc`, `.zip`) or the extracted course folders into the `courses/` directory of your fork. 
3. Commit and push your changes. 
4. Run the "Manual Publish Courses" workflow and wait for it to complete.
5. Enable GitHub Pages for the forked repository under Settings -> Pages.  Have the pages deployed from the `gh-pages` branch.

Keep course exports out of public forks unless you intend to and have permission to publish them.

## View Locally 

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

3. Open the URL printed by the server to navigate the course content.


## Notes

- The app serves HTML pages and files that are part of the IMS/Canvas export (e.g., `wiki_content/`, `web_resources/`, and `course_settings` files). The app rewrites links in exported HTML so they route through the local viewer and uses a canonical `/file/<id>` endpoint to serve files referenced by resource identifier.
- The "Canvas Data" page displays additional course metadata.
- Exports do not include content hosted by external LTI/External Tools (Panopto, Gradescope, Zoom cloud recordings, etc.) as they are generally NOT bundled with the Canvas export.  The app attempts to detect the use of third-party tools and shows a warning when such integrations are likely present.



- Static resolution heuristics:
	- The app tries several locations when resolving `/static/<path>` requests: package static, project static, the export folder (with placeholder variants), mapping into `web_resources/`, and finally a recursive basename search in `web_resources`.
	- This multi-stage strategy is intentionally permissive to handle differing export layouts; it may occasionally match files by basename when paths diverge.

- Limitations and edge cases:
	- The viewer attempts to strip inline styles and remove exported stylesheet links so the app's CSS provides a consistent look; complex pages might still render differently than in Canvas.
	- Date/time formatting and metadata extraction are best-effort from `course_settings`. Some fields may be missing depending on the Canvas version and export options.
	- The plugin/LTI detection is heuristic-based. It can produce false positives or miss uncommon integrations. If you rely on this for audits, verify the results manually.

## Tests

- A tiny, example (`courses/minimal-course-export`) is provided so CI can run with some baseline data.
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
