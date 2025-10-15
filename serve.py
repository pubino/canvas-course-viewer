import click
import os
import shutil
from pathlib import Path
from canvas_viewer.app import create_app
from canvas_viewer.parser import CanvasExport
import socket


@click.command()
@click.option('--export', 'export_path', required=True, help='Path to extracted Canvas export folder')
@click.option('--export-out', 'export_out', default=None, help='If provided, write a static export of the course to this directory and exit')
@click.option('--host', default='127.0.0.1')
@click.option('--port', default=5001)
@click.option('--canvas-base-domain', 'canvas_base_domain', default=None, help='Comma-separated base domain(s) to treat as internal (overrides CANVAS_BASE_DOMAIN env var)')
def serve(export_path, export_out, host, port, canvas_base_domain):
    export_path = os.path.abspath(export_path)
    if not os.path.exists(export_path):
        raise click.ClickException(f'Export path not found: {export_path}')

    # If user requested a static export, write files and exit
    if export_out:
        out_dir = Path(export_out)
        out_dir.mkdir(parents=True, exist_ok=True)

        # copy key folders if present
        for sub in ('wiki_content', 'web_resources', 'course_settings'):
            src = Path(export_path) / sub
            if src.exists():
                dst = out_dir / sub
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

        # build a minimal index.html matching the app's summaries
        try:
            exp = CanvasExport(export_path)
        except Exception as e:
            raise click.ClickException(f'Failed to parse export for static write: {e}')

        name = exp.title or Path(export_path).name
        pages = exp.list_pages()
        files = exp.get_files()
        modules = exp.get_modules()

        lines = [
            '<!doctype html>',
            '<html><head><meta charset="utf-8"><title>%s</title></head><body>' % name,
            f'<h1>{name}</h1>',
            '<h2>Pages</h2>',
            '<ul>'
        ]
        for p in pages:
            href = p.get('href')
            lines.append(f'<li><a href="{href}">{p.get("title") or href}</a></li>')
        lines.append('</ul>')

        lines.append('<h2>Files</h2><ul>')
        for f in files:
            href = f.get('href')
            lines.append(f'<li><a href="{href}">{f.get("title")}</a> ({f.get("date") or "—"})</li>')
        lines.append('</ul>')

        if modules:
            lines.append('<h2>Modules</h2>')
            for m in modules:
                lines.append(f'<h3>{m.get("title")}</h3><ul>')
                for it in m.get('items'):
                    href = it.get('href') or '#'
                    lines.append(f'<li><a href="{href}">{it.get("title")}</a></li>')
                lines.append('</ul>')

        lines.append('</body></html>')
        with open(out_dir / 'index.html', 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines))

        click.echo(f'Wrote static export to {out_dir}')
        return

    # find an available port starting at `port`
    def _port_available(p):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return True
            except OSError:
                return False

    chosen = None
    # never try to bind to port 5000; skip it explicitly
    for p in range(port, port + 50):
        if p == 5000:
            continue
        if _port_available(p):
            chosen = p
            break

    if chosen is None:
        raise click.ClickException(f'No free port found in range {port}-{port+49}')

    if chosen != port:
        click.echo(f'Port {port} in use; starting on {chosen} instead')

    # if provided via CLI, set environment variable so the app picks it up
    if canvas_base_domain:
        os.environ['CANVAS_BASE_DOMAIN'] = canvas_base_domain

    app = create_app(export_path)
    click.echo(f'Serving {export_path} at http://{host}:{chosen}')
    app.run(host=host, port=chosen)


if __name__ == '__main__':
    serve()
