import os
from lxml import etree

NS = {
    'ims': 'http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1',
    'lom': 'http://ltsc.ieee.org/xsd/imsccv1p1/LOM/resource',
}


class CanvasExport:
    def __init__(self, path):
        self.path = path
        self.manifest_path = os.path.join(path, 'imsmanifest.xml')
        self.title = None
        self.resources = {}  # identifier -> {href, files: []}
        self.organizations = []
        # parsed metadata about files (course_settings/files_meta.xml)
        self.file_meta = {}

        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"imsmanifest.xml not found in {path}")

        self._parse_manifest()

    def _parse_manifest(self):
        parser = etree.XMLParser(remove_comments=True)
        tree = etree.parse(self.manifest_path, parser)
        root = tree.getroot()

        # title
        title_el = root.find('.//{http://ltsc.ieee.org/xsd/imsccv1p1/LOM/manifest}title')
        if title_el is not None:
            string_el = title_el.find('{http://ltsc.ieee.org/xsd/imsccv1p1/LOM/manifest}string')
            if string_el is not None and string_el.text:
                self.title = string_el.text

        # resources
        for res in root.findall('.//{http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1}resource'):
            ident = res.get('identifier')
            href = res.get('href')
            files = [f.get('href') for f in res.findall('{http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1}file') if f.get('href')]
            rtype = res.get('type')
            self.resources[ident] = {
                'identifier': ident,
                'href': href,
                'files': files,
                'type': rtype,
            }

        # organizations -> walk items to get structure
        org = root.find('.//{http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1}organization')
        if org is not None:
            self.organizations = self._parse_items(org)

        # try loading course_settings xml into metadata
        cs_path = os.path.join(self.path, 'course_settings', 'course_settings.xml')
        if os.path.exists(cs_path):
            try:
                cstree = etree.parse(cs_path)
                csroot = cstree.getroot()
                # get course title, short name
                title = csroot.find('.//course/name')
                if title is not None and title.text:
                    self.title = title.text
                self.course_settings = etree.tostring(csroot, encoding='utf-8')
            except Exception:
                self.course_settings = None
        else:
            self.course_settings = None

        # parse files metadata if present (course_settings/files_meta.xml)
        fm_path = os.path.join(self.path, 'course_settings', 'files_meta.xml')
        if os.path.exists(fm_path):
            try:
                fmtree = etree.parse(fm_path)
                fmroot = fmtree.getroot()
                # files are under the Canvas namespace; match by exact tag
                for f in fmroot.findall('.//{http://canvas.instructure.com/xsd/cccv1p0}file'):
                    ident = f.get('identifier')
                    display = None
                    unlock_at = None
                    dn = f.find('{http://canvas.instructure.com/xsd/cccv1p0}display_name')
                    if dn is not None and dn.text:
                        display = dn.text
                    ua = f.find('{http://canvas.instructure.com/xsd/cccv1p0}unlock_at')
                    if ua is not None and ua.text:
                        unlock_at = ua.text
                    self.file_meta[ident] = {'display_name': display, 'unlock_at': unlock_at}
            except Exception:
                self.file_meta = {}

    def get_course_metadata(self):
        """Return dict of course metadata parsed from course_settings/course_settings.xml if present.

        Fields returned include: title, course_code, start_at, conclude_at, image_identifier_ref,
        image_href (if resolvable), is_public, license, storage_quota, grading_standard_id
        """
        meta = {}
        cs_path = os.path.join(self.path, 'course_settings', 'course_settings.xml')
        if not os.path.exists(cs_path):
            return meta
        try:
            tree = etree.parse(cs_path)
            root = tree.getroot()
            ns = {'c': root.nsmap.get(None)} if None in root.nsmap else {}
            def get_text(tag):
                if ns:
                    el = root.find(f'.//{{{ns["c"]}}}{tag}')
                else:
                    el = root.find(f'.//{tag}')
                return el.text if el is not None and el.text else None

            meta['title'] = get_text('title')
            meta['course_code'] = get_text('course_code')
            meta['start_at'] = get_text('start_at')
            meta['conclude_at'] = get_text('conclude_at')
            meta['image_identifier_ref'] = get_text('image_identifier_ref')
            # common booleans and settings
            meta['is_public'] = get_text('is_public')
            meta['is_public_to_auth_users'] = get_text('is_public_to_auth_users')
            meta['public_syllabus'] = get_text('public_syllabus')
            meta['public_syllabus_to_auth'] = get_text('public_syllabus_to_auth')
            meta['allow_student_wiki_edits'] = get_text('allow_student_wiki_edits')
            meta['syllabus_course_summary'] = get_text('syllabus_course_summary')
            meta['allow_student_forum_attachments'] = get_text('allow_student_forum_attachments')
            meta['lock_all_announcements'] = get_text('lock_all_announcements')
            meta['default_wiki_editing_roles'] = get_text('default_wiki_editing_roles')
            meta['allow_student_organized_groups'] = get_text('allow_student_organized_groups')
            meta['default_view'] = get_text('default_view')
            meta['show_total_grade_as_points'] = get_text('show_total_grade_as_points')
            meta['filter_speed_grader_by_student_group'] = get_text('filter_speed_grader_by_student_group')
            meta['license'] = get_text('license')
            meta['indexed'] = get_text('indexed')
            meta['hide_final_grade'] = get_text('hide_final_grade')
            meta['hide_distribution_graphs'] = get_text('hide_distribution_graphs')
            meta['allow_student_discussion_topics'] = get_text('allow_student_discussion_topics')
            meta['allow_student_discussion_editing'] = get_text('allow_student_discussion_editing')
            meta['allow_student_discussion_reporting'] = get_text('allow_student_discussion_reporting')
            meta['show_announcements_on_home_page'] = get_text('show_announcements_on_home_page')
            meta['home_page_announcement_limit'] = get_text('home_page_announcement_limit')
            meta['usage_rights_required'] = get_text('usage_rights_required')
            meta['restrict_student_future_view'] = get_text('restrict_student_future_view')
            meta['restrict_student_past_view'] = get_text('restrict_student_past_view')
            meta['restrict_enrollments_to_course_dates'] = get_text('restrict_enrollments_to_course_dates')
            meta['homeroom_course'] = get_text('homeroom_course')
            meta['horizon_course'] = get_text('horizon_course')
            meta['conditional_release'] = get_text('conditional_release')
            meta['content_library'] = get_text('content_library')
            meta['grading_standard_enabled'] = get_text('grading_standard_enabled')
            meta['storage_quota'] = get_text('storage_quota')
            meta['overridden_course_visibility'] = get_text('overridden_course_visibility')
            meta['grading_standard_id'] = get_text('grading_standard_id')
            meta['root_account_uuid'] = get_text('root_account_uuid')
            meta['enable_course_paces'] = get_text('enable_course_paces')
            meta['hide_sections_on_course_users_page'] = get_text('hide_sections_on_course_users_page')
            # tab configuration and nested default_post_policy
            # tab_configuration may be JSON stored as text
            tc_el = None
            if ns:
                tc_el = root.find(f'.//{{{ns["c"]}}}tab_configuration')
            else:
                tc_el = root.find('.//tab_configuration')
            meta['tab_configuration'] = tc_el.text if tc_el is not None and tc_el.text else None
            # default_post_policy/post_manually
            dpp = None
            if ns:
                dpp = root.find(f'.//{{{ns["c"]}}}default_post_policy')
            else:
                dpp = root.find('.//default_post_policy')
            if dpp is not None:
                pm = dpp.find(f'{{{ns["c"]}}}post_manually') if ns else dpp.find('.//post_manually')
                meta['post_manually'] = pm.text if pm is not None and pm.text else None

            # resolve image identifier to a resource href if possible
            img_id = meta.get('image_identifier_ref')
            if img_id:
                # resource keys are identifiers; try direct lookup
                r = self.resources.get(img_id)
                if not r:
                    # maybe resource identifier is stored with slight variations; search values
                    for res in self.resources.values():
                        if res.get('identifier') == img_id:
                            r = res
                            break
                if r:
                    meta['image_href'] = r.get('href')
                else:
                    meta['image_href'] = None
        except Exception:
            return meta
        return meta

        # parse files metadata if present (course_settings/files_meta.xml)
        self.file_meta = {}
        fm_path = os.path.join(self.path, 'course_settings', 'files_meta.xml')
        if os.path.exists(fm_path):
            try:
                fmtree = etree.parse(fm_path)
                fmroot = fmtree.getroot()
                # files are under the default namespace; use local-name matching
                for f in fmroot.findall('.//{http://canvas.instructure.com/xsd/cccv1p0}file'):
                    ident = f.get('identifier')
                    display = None
                    unlock_at = None
                    dn = f.find('{http://canvas.instructure.com/xsd/cccv1p0}display_name')
                    if dn is not None and dn.text:
                        display = dn.text
                    ua = f.find('{http://canvas.instructure.com/xsd/cccv1p0}unlock_at')
                    if ua is not None and ua.text:
                        unlock_at = ua.text
                    self.file_meta[ident] = {'display_name': display, 'unlock_at': unlock_at}
            except Exception:
                self.file_meta = {}

    def categorize_resources(self):
        """Return a dict of likely categories with lists of resource dicts.
        Heuristics: filenames and folder names.
        """
        cats = {'announcements': [], 'modules': [], 'quizzes': [], 'discussions': [], 'people': [], 'files': []}
        for ident, r in self.resources.items():
            href = r.get('href') or ''
            lh = href.lower()
            if 'announcement' in lh or 'news' in lh:
                cats['announcements'].append(r)
            elif 'module' in lh or '/modules' in lh or 'module' in '/'.join(r.get('files', [])):
                cats['modules'].append(r)
            elif 'quiz' in lh or 'quizzes' in lh:
                cats['quizzes'].append(r)
            elif 'discussion' in lh or 'forum' in lh:
                cats['discussions'].append(r)
            elif lh.startswith('web_resources') or lh.startswith('course_settings'):
                cats['files'].append(r)
            # people heuristic: file name people, roster, or profile
            if 'people' in lh or 'roster' in lh or 'profile' in lh:
                cats['people'].append(r)
        return cats

    def _parse_items(self, parent):
        items = []
        for item in parent.findall('{http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1}item'):
            title_el = item.find('{http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1}title')
            title = title_el.text if title_el is not None else None
            identifierref = item.get('identifierref')
            children = self._parse_items(item)
            items.append({'title': title, 'identifierref': identifierref, 'children': children})
        return items

    def list_pages(self):
        # pages in resources with webcontent or associatedcontent hrefs
        pages = []
        for ident, r in self.resources.items():
            href = r.get('href')
            if href and (href.endswith('.html') or href.startswith('wiki_content') or 'web_resources' in (href or '')):
                pages.append({'id': ident, 'href': href, 'title': os.path.basename(href)})
        return pages

    def detect_external_tools(self):
        """Return a list of likely external tools or plugins referenced in the export.

        Heuristics used:
        - resource files or hrefs containing known vendor names (panopto, gradescope, echo360, panopto)
        - resources of type 'imsbasiclti_xmlv1p0' or similar LTI resource types
        - manifest<file> entries that look like an external launch (launch.html, lti.xml)
        - course_settings tab_configuration entries referencing external tools
        """
        found = set()
        known = {
            'panopto': ['panopto'],
            'gradescope': ['gradescope'],
            'echo360': ['echo360'],
            'kaltura': ['kaltura'],
            'zoom': ['zoom.us', 'zoom'],
            'turnitin': ['turnitin'],
            'panopto-lti': ['panopto.com'],
            'microsoft-stream': ['stream.microsoft.com'],
        }

        # scan resources and their files/hrefs
        for ident, r in self.resources.items():
            href = (r.get('href') or '').lower()
            rtype = (r.get('type') or '').lower()
            files = [f.lower() for f in (r.get('files') or [])]
            combined = ' '.join([href] + files + [rtype])
            # check for LTI resource type
            if 'lti' in rtype or 'imsbasiclti' in rtype or 'lticontent' in rtype:
                found.add('LTI/External Tools')
            for name, tokens in known.items():
                for t in tokens:
                    if t in combined:
                        found.add(name)

        # also scan course_settings for tab_configuration references
        cs_path = os.path.join(self.path, 'course_settings', 'course_settings.xml')
        if os.path.exists(cs_path):
            try:
                from lxml import etree
                tree = etree.parse(cs_path)
                root = tree.getroot()
                tc = root.find('.//tab_configuration')
                if tc is not None and tc.text:
                    tc_text = tc.text.lower()
                    for name, tokens in known.items():
                        for t in tokens:
                            if t in tc_text:
                                found.add(name)
            except Exception:
                pass

        return sorted(found)

    def find_external_links(self, allowed_domains=None):
        """Scan resources and HTML pages for absolute links that point outside allowed_domains.

        Returns a list of dicts: {'href': <url>, 'source': <resource or page path>, 'context': <title or element>}.
        """
        import re
        from urllib.parse import urlparse
        links = []
        seen = set()

        # normalize allowed domains into match patterns
        # supports entries like 'canvas.princeton.edu', 'https://canvas.princeton.edu', or 'https://*.instructure.com'
        if allowed_domains is None:
            allowed_domains = []
        patterns = []
        for d in allowed_domains:
            if not d:
                continue
            dd = d.strip().lower()
            # strip scheme if present
            try:
                parsed = urlparse(dd)
                host = parsed.hostname or dd
            except Exception:
                host = dd
            if host.startswith('*.'):
                # wildcard suffix
                patterns.append({'type': 'suffix', 'value': host[2:]})
            else:
                # exact host; also allow www. variant
                patterns.append({'type': 'exact', 'value': host})
                if not host.startswith('www.'):
                    patterns.append({'type': 'exact', 'value': 'www.' + host})

        def is_external(url):
            if not url or not (url.startswith('http://') or url.startswith('https://')):
                return False
            try:
                p = urlparse(url)
                host = (p.hostname or '').lower()
                if not host:
                    return False
                for pat in patterns:
                    if pat['type'] == 'exact':
                        if host == pat['value']:
                            return False
                    elif pat['type'] == 'suffix':
                        if host == pat['value'] or host.endswith('.' + pat['value']):
                            return False
                return True
            except Exception:
                return False

        # scan resources' hrefs and files
        for ident, r in self.resources.items():
            # check resource href
            href = r.get('href') or ''
            if href.startswith('http://') or href.startswith('https://'):
                if is_external(href) and href not in seen:
                    seen.add(href)
                    links.append({'href': href, 'source': f'resource:{r.get("identifier")}', 'context': href})
            # check file entries
            for f in (r.get('files') or []):
                if f.startswith('http://') or f.startswith('https://'):
                    if is_external(f) and f not in seen:
                        seen.add(f)
                        links.append({'href': f, 'source': f'resource-file:{r.get("identifier")}', 'context': f})

        # scan HTML pages referenced by manifest (wiki_content and course_settings and any html resources)
        # we will try to resolve path and parse anchors/img/src/script/link
        try:
            from lxml import html as lhtml
        except Exception:
            lhtml = None

        for ident, r in self.resources.items():
            href = r.get('href') or ''
            if href.lower().endswith('.html') or href.startswith('wiki_content') or href.startswith('course_settings'):
                p = os.path.join(self.path, href)
                if not os.path.exists(p):
                    p = os.path.join(self.path, href.strip())
                if not os.path.exists(p):
                    continue
                if lhtml is None:
                    # fallback: simple regex for http(s) links
                    try:
                        text = open(p, 'r', encoding='utf-8', errors='ignore').read()
                        for m in re.findall(r'https?://[^\s"\'>)]+', text):
                            if is_external(m) and m not in seen:
                                seen.add(m)
                                links.append({'href': m, 'source': f'page:{href}', 'context': href})
                    except Exception:
                        continue
                else:
                    try:
                        doc = lhtml.parse(p)
                        # collect from tags
                        for el in doc.iter():
                            for attr in ('href', 'src'):
                                val = el.get(attr)
                                if val and (val.startswith('http://') or val.startswith('https://')):
                                    if is_external(val) and val not in seen:
                                        seen.add(val)
                                        links.append({'href': val, 'source': f'page:{href}', 'context': (el.tag or '')})
                    except Exception:
                        # fallback regex
                        try:
                            text = open(p, 'r', encoding='utf-8', errors='ignore').read()
                            for m in re.findall(r'https?://[^\s"\'>)]+', text):
                                if is_external(m) and m not in seen:
                                    seen.add(m)
                                    links.append({'href': m, 'source': f'page:{href}', 'context': href})
                        except Exception:
                            continue

        # also scan course_settings/tab_configuration raw text for URLs
        cs_path = os.path.join(self.path, 'course_settings', 'course_settings.xml')
        if os.path.exists(cs_path):
            try:
                text = open(cs_path, 'r', encoding='utf-8', errors='ignore').read()
                for m in re.findall(r'https?://[^\s"\'>)]+', text):
                    if is_external(m) and m not in seen:
                        seen.add(m)
                        links.append({'href': m, 'source': 'course_settings', 'context': 'tab_configuration'})
            except Exception:
                pass

        return links

    def get_pages_by_folder(self, folder_prefix='wiki_content'):
        pages = []
        for ident, r in self.resources.items():
            href = r.get('href')
            if href and href.startswith(folder_prefix) and href.lower().endswith('.html'):
                pages.append({'id': ident, 'href': href, 'title': os.path.basename(href)})
        return sorted(pages, key=lambda p: p['href'])

    def get_files(self):
        files = []
        for ident, r in self.resources.items():
            href = r.get('href')
            if href and href.startswith('web_resources'):
                meta = self.file_meta.get(ident, {})
                title = meta.get('display_name') or os.path.basename(href)
                date = meta.get('unlock_at')
                date_source = None
                # fallback: if no date metadata, try filesystem mtime of resolved file
                if date:
                    date_source = 'meta'
                if not date:
                    p = os.path.join(self.path, href)
                    if not os.path.exists(p):
                        # sometimes hrefs may have stray leading/trailing whitespace
                        p = os.path.join(self.path, href.strip())
                    try:
                        if os.path.exists(p):
                            mtime = os.path.getmtime(p)
                            # ISO-like fallback (date only)
                            import datetime

                            date = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                            date_source = 'file'
                    except Exception:
                        date = None
                files.append({'id': ident, 'href': href, 'title': title, 'date': date, 'date_source': date_source})
        return sorted(files, key=lambda f: f['href'])

    def get_syllabus(self):
        # look for resource with intendeduse=syllabus or known syllabus path
        for ident, r in self.resources.items():
            if r.get('href') and 'syllabus' in r.get('href'):
                return r
            # intendeduse handled in manifest not stored; fallback to course_settings
        p = os.path.join(self.path, 'course_settings', 'syllabus.html')
        if os.path.exists(p):
            return {'identifier': 'syllabus', 'href': 'course_settings/syllabus.html', 'files': ['course_settings/syllabus.html']}
        return None

    def get_assignments(self):
        assigns = []
        for ident, r in self.resources.items():
            href = (r.get('href') or '').lower()
            if 'homework' in href or 'midterm' in href or 'final' in href or 'homework' in '/'.join(r.get('files', [])):
                assigns.append({'id': ident, 'href': r.get('href'), 'title': os.path.basename(r.get('href') or '')})
        return sorted(assigns, key=lambda a: a['href'] or '')

    def get_modules(self):
        """Construct modules from the manifest's organizations.

        Returns a list of modules where each module is a dict:
          {'title': <module title>, 'items': [{'title':..., 'href':...}, ...]}
        The method walks organization items and treats any item whose children
        reference resources (identifierref) as a module grouping.
        """
        modules = []

        def process_item(item):
            # if this item has children, and any child references a resource,
            # treat the item as a module container
            children = item.get('children') or []
            has_ref_child = any((c.get('identifierref') for c in children))
            if has_ref_child:
                mod = {'title': item.get('title') or 'Module', 'items': []}
                for child in children:
                    ident = child.get('identifierref')
                    res = self.resources.get(ident) if ident else None
                    href = res.get('href') if res else None
                    title = child.get('title') or (res and (res.get('title') or os.path.basename(href or ''))) 
                    mod['items'].append({'title': title, 'href': href})
                modules.append(mod)
            else:
                # recurse into children
                for c in children:
                    process_item(c)

        for top in self.organizations:
            process_item(top)

        return modules

    def href_to_resource(self, href):
        # return resource entry that matches href exactly
        for r in self.resources.values():
            if r.get('href') == href:
                return r
            for f in r.get('files', []) or []:
                if f == href:
                    return r
        return None

    def resolve_path(self, href):
        if not href:
            return None
        p = os.path.join(self.path, href)
        if os.path.exists(p):
            return p
        # sometimes hrefs have leading spaces
        return os.path.join(self.path, href.strip())
