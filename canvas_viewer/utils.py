from lxml import html
from urllib.parse import urlparse
import posixpath


def rewrite_html_bytes(raw_bytes, base_href):
    """Rewrite links in HTML bytes using base_href (posix path, e.g. 'wiki_content/dir/page.html').
    - HTML links to other .html files are rewritten to /page/<path>
    - other local links rewritten to /static/<path>
    External links, anchors, and mailto are left as-is.
    Returns bytes (utf-8) of rewritten HTML.
    """
    try:
        doc = html.fromstring(raw_bytes)
    except Exception:
        return raw_bytes

    base_dir = posixpath.dirname(base_href)

    def rewrite_attr(val):
        if not val:
            return val
        parsed = urlparse(val)
        if parsed.scheme in ('http', 'https', 'mailto') or val.startswith('//'):
            return val
        if val.startswith('#'):
            return val
        # resolve relative to base_dir
        if posixpath.isabs(val):
            joined = val.lstrip('/')
        else:
            joined = posixpath.normpath(posixpath.join(base_dir, val))
        if joined.lower().endswith('.html'):
            return '/page/' + joined
        return '/static/' + joined

    for el in doc.xpath('//*'):
        tag = el.tag.lower() if hasattr(el, 'tag') else ''
        if tag == 'img' and el.get('src'):
            el.set('src', rewrite_attr(el.get('src')))
        if tag == 'a' and el.get('href'):
            el.set('href', rewrite_attr(el.get('href')))
        if tag == 'link' and el.get('href'):
            el.set('href', rewrite_attr(el.get('href')))
        if tag == 'script' and el.get('src'):
            el.set('src', rewrite_attr(el.get('src')))

    return html.tostring(doc, encoding='utf-8', pretty_print=True)
