import click
import os
from canvas_viewer.app import create_app
import socket


@click.command()
@click.option('--export', 'export_path', required=True, help='Path to extracted Canvas export folder')
@click.option('--host', default='127.0.0.1')
@click.option('--port', default=5001)
@click.option('--canvas-base-domain', 'canvas_base_domain', default=None, help='Comma-separated base domain(s) to treat as internal (overrides CANVAS_BASE_DOMAIN env var)')
def serve(export_path, host, port, canvas_base_domain):
    export_path = os.path.abspath(export_path)
    if not os.path.exists(export_path):
        raise click.ClickException(f'Export path not found: {export_path}')

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
