#!/usr/bin/env python3
"""source-survey: walk the GAIA source surface and report drift against the docs snapshot.

Implements SKILL.md Steps 1-8. Reads the committed tree at a gaia ref (via
`git archive`, so uncommitted or untracked files never leak into a snapshot),
prints the Step 7 report, and with --write replaces the snapshot.

Usage:
  python3 -I .claude/skills/source-survey/survey.py [--ref REF] [--gaia PATH] [--write] [--verbose]

Defaults: --gaia is the gaia checkout next to this docs repo; --ref is its HEAD.
"""
import argparse
import collections
import datetime
import fnmatch
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile

DOCS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SNAPSHOT = os.path.join(DOCS_ROOT, '.claude', 'audit', 'source-state.json')
DO_NOT_DOCUMENT = os.path.join(DOCS_ROOT, '.claude', 'audit', 'do-not-document.yml')
DOCS_CONTENT = os.path.join(DOCS_ROOT, 'src', 'content', 'docs')
CONTRIBUTOR_PAGES = 'contributors' + os.sep

CLI_SRC = '.gaia/cli/src'
MAX_CLI_DEPTH = 3
# Dirs whose files are surface records. A docs path under one of these that is
# missing from source is a DOC-ORPHAN; any other missing path (runtime files such
# as .gaia/local/* or settings.local.json) is created in the adopter's project.
SURFACE_DIRS = (
    '.claude/commands/', '.claude/skills/', '.claude/hooks/', '.claude/rules/', '.claude/agents/',
    '.claude/doctrine/', 'frontend/.claude/skills/', 'frontend/.claude/rules/', 'frontend/.claude/agents/',
    'frontend/.claude/instructions/', '.github/workflows/', '.githooks/', 'wiki/',
)
# Installed per machine and gitignored, so never in the committed tree.
PER_MACHINE = ('frontend/.claude/skills/react-doctor',)
ANY_MARKER = re.compile(r'^\s*(?:<!--|#)\s*gaia:maintainer-only:(start|end)\b')
AUDIENCES = ('adopter', 'contributor', 'mixed')


def file_hash(text):
    """Step 3: sha256 of the whole file, so an edit anywhere in it is drift."""
    return hashlib.sha256(text.encode()).hexdigest()


def lines_of(text):
    lines = text.split('\n')
    return lines[:-1] if text.endswith('\n') else lines


def split_frontmatter(text):
    lines = lines_of(text)
    if lines and lines[0] == '---':
        for i in range(1, len(lines)):
            if lines[i] == '---':
                return lines[1:i], lines[i + 1:]
    return None, lines


def frontmatter_field(frontmatter, key):
    if not frontmatter:
        return None
    for i, line in enumerate(frontmatter):
        match = re.match(r'^' + re.escape(key) + r':\s*(.*)$', line)
        if not match:
            continue
        value = match.group(1).strip()
        if value in ('>', '|', '>-', '|-', ''):
            parts = []
            for folded in frontmatter[i + 1:]:
                if folded.startswith(' ') or folded == '':
                    parts.append(folded.strip())
                else:
                    break
            value = ' '.join(part for part in parts if part)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]
        return value or None
    return None


def first_h1(body):
    for line in body:
        if line.startswith('# '):
            return line[2:].strip()
    return None


def first_prose(body):
    return next((l.strip() for l in body if l.strip() and not l.strip().startswith('#')), None)


def comment_description(text):
    """First comment line after the shebang, skipping shellcheck directives."""
    for line in text.splitlines()[1:]:
        stripped = line.strip()
        if not stripped.startswith('#'):
            if stripped:
                return None
            continue
        comment = stripped.lstrip('#').strip()
        if comment and not comment.startswith('shellcheck'):
            return comment
    return None


def glob_regex(pattern):
    """release-scrub.yml path glob: `**/` spans any directories, `*` stays in one segment."""
    out, i = '', 0
    while i < len(pattern):
        if pattern.startswith('**/', i):
            out += '(?:.*/)?'
            i += 3
        elif pattern.startswith('**', i):
            out += '.*'
            i += 2
        elif pattern[i] == '*':
            out += '[^/]*'
            i += 1
        elif pattern[i] == '?':
            out += '[^/]'
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile('^' + out + '$')


def yaml_scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
        return value[1:-1]
    return value


def help_text(module_text, const='HELP_TEXT'):
    match = re.search(r'const ' + const + r' = `(.*?)`;', module_text, re.S)
    return match.group(1) if match else None


def help_entry(text, sub):
    """The usage line plus description for one subcommand in a router's HELP_TEXT.

    An entry starts at a two-space-indented line naming the subcommand and runs to
    a blank line or the next two-space-indented entry.
    """
    if text is None:
        return None
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if re.match(r'^  ' + re.escape(sub) + r'(\s|$)', line):
            parts = [line.strip()]
            for following in lines[i + 1:]:
                if not following.strip() or re.match(r'^  \S', following):
                    break
                parts.append(following.strip())
            return ' '.join(' '.join(parts).split())
    return None


def help_summary(text):
    """First paragraph after the Usage line, for a command with no subcommands."""
    if text is None:
        return None
    paragraph = []
    for line in text.split('\n')[1:]:
        if line.strip():
            paragraph.append(line.strip())
        elif paragraph:
            break
    return ' '.join(paragraph) or None


class Survey:
    def __init__(self, root):
        self.root = root
        self.items = []
        self.ambiguities = []
        self.exclude = self._load_exclude()
        self.scrub = self._load_scrub()
        self.do_not_document = self._load_do_not_document()

    def read(self, path):
        with open(os.path.join(self.root, path), encoding='utf-8', errors='replace') as handle:
            return handle.read()

    def exists(self, path):
        return os.path.isfile(os.path.join(self.root, path))

    def files(self, pattern):
        found = glob.glob(os.path.join(self.root, pattern), recursive=True)
        return sorted(os.path.relpath(p, self.root) for p in found if os.path.isfile(p))

    def _load_exclude(self):
        """Step 1: each line is a literal path, anchored at the root, matching itself and
        everything under it (the release CLI compiles it to `^<path>(/|$)` and rejects globs)."""
        patterns = []
        for number, line in enumerate(self.read('.gaia/release-exclude').splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if any(ch in stripped for ch in '*?['):
                self.ambiguities.append(f'release-exclude line {number} is a glob ({stripped}); the release CLI rejects globs')
            patterns.append((stripped.strip('/'), number))
        return patterns

    def _load_scrub(self):
        """Step 1: the marker-strip transforms in .gaia/release-scrub.yml, as (path regexes, start, end)."""
        if not self.exists('.gaia/release-scrub.yml'):
            self.ambiguities.append('.gaia/release-scrub.yml is missing; no file can be mixed')
            return []
        transforms, current, in_paths = [], None, False
        for line in self.read('.gaia/release-scrub.yml').splitlines():
            if re.match(r'^\s*#', line) or not line.strip():
                continue
            item = re.match(r'^  - type:\s*(\S+)', line)
            if item:
                current = {'type': item.group(1), 'paths': [], 'start': None, 'end': None}
                transforms.append(current)
                in_paths = False
                continue
            if current is None:
                continue
            if re.match(r'^    paths:\s*$', line):
                in_paths = True
                continue
            path = re.match(r'^      - (.+)$', line)
            if in_paths and path:
                current['paths'].append(yaml_scalar(path.group(1)))
                continue
            field = re.match(r'^    (start|end):\s*(.+)$', line)
            if field:
                current[field.group(1)] = yaml_scalar(field.group(2))
            in_paths = False
        strips = []
        for transform in transforms:
            if transform['type'] != 'marker-strip':
                continue
            if not (transform['start'] and transform['end'] and transform['paths']):
                self.ambiguities.append(f'release-scrub.yml marker-strip entry is incomplete: {transform}')
                continue
            strips.append(([glob_regex(p) for p in transform['paths']], transform['start'], transform['end']))
        return strips

    def _load_do_not_document(self):
        with open(DO_NOT_DOCUMENT, encoding='utf-8') as handle:
            text = handle.read()
        entries = []
        for block in re.split(r'\n(?=  - )', text):
            target = re.search(r'^\s*-?\s*(path|name):\s*(.+)$', block, re.M)
            reason = re.search(r'^\s+reason:\s*(.+)$', block, re.M)
            if target and reason:
                entries.append((target.group(1), yaml_scalar(target.group(2)), reason.group(1).strip()))
        return entries

    def exclude_line(self, path):
        for pattern, number in self.exclude:
            if path == pattern or path.startswith(pattern + '/'):
                return number
        return None

    def do_not_document_reason(self, path, name):
        for key, pattern, reason in self.do_not_document:
            if key == 'path':
                prefix = pattern.rstrip('/')
                if fnmatch.fnmatchcase(path, pattern) or path == prefix or path.startswith(prefix + '/'):
                    return reason
            elif fnmatch.fnmatchcase(name, pattern) or fnmatch.fnmatchcase(name, '*' + pattern):
                return reason
        return None

    def marker_blocks(self, path, text):
        """Blocks the release scrub strips from this file, plus ambiguities for markers it would ship."""
        lines = text.split('\n')
        blocks = []
        for regexes, start, end in self.scrub:
            if not any(r.match(path) for r in regexes):
                continue
            # Mirrors gaia's release/marker-strip.ts: a marker counts wherever it
            # appears on a line, and the scrub drops the whole marker line.
            open_at = None
            for number, line in enumerate(lines, 1):
                has_start, has_end = start in line, end in line
                if (has_start or has_end) and line.strip() not in (start, end):
                    self.ambiguities.append(
                        f'{path}:{number}: maintainer-only marker shares its line with other text, '
                        'which the scrub drops with it')
                if open_at is None and has_start and has_end:
                    blocks.append([number, number])
                elif open_at is None and has_start:
                    open_at = number
                elif open_at is not None and has_end:
                    blocks.append([open_at, number])
                    open_at = None
                elif open_at is None and has_end:
                    self.ambiguities.append(f'{path}:{number}: maintainer-only end with no start')
            if open_at is not None:
                self.ambiguities.append(f'{path}:{open_at}: maintainer-only start never closed')
        if not blocks:
            stray = [n for n, line in enumerate(lines, 1) if ANY_MARKER.match(line)]
            if stray:
                self.ambiguities.append(
                    f'{path}: maintainer-only marker at line(s) {stray} but no release-scrub transform '
                    'strips this file, so the block ships verbatim (possible leak; report to gaia)')
        return sorted(blocks)

    def add(self, kind, path, name, description, text):
        record = {'kind': kind, 'path': path, 'name': name, 'description': description}
        if self.exclude_line(path):
            record['audience'] = 'contributor'
        else:
            blocks = self.marker_blocks(path, text)
            record['audience'] = 'mixed' if blocks else 'adopter'
            if blocks:
                record['marker_blocks'] = blocks
        record['content_hash'] = file_hash(text)
        record['excluded_from_docs'] = bool(self.do_not_document_reason(path, name))
        self.items.append(record)
        return record

    def walk(self):
        self.walk_commands()
        self.walk_skills()
        self.walk_references()
        self.walk_cli()
        self.walk_machinery()
        self.items.sort(key=lambda r: (r['kind'], r['name'], r['path']))
        return self.items

    def walk_commands(self):
        for path in self.files('.claude/commands/*.md'):
            text = self.read(path)
            frontmatter, _ = split_frontmatter(text)
            name = '/' + (frontmatter_field(frontmatter, 'name') or os.path.basename(path)[:-3])
            self.add('command', path, name, frontmatter_field(frontmatter, 'description'), text)

    def walk_skills(self):
        for skills_dir in ('.claude/skills', 'frontend/.claude/skills'):
            for path in self.files(skills_dir + '/**/*'):
                if path.startswith(PER_MACHINE) or path.startswith('.claude/skills/gaia/references/'):
                    continue
                text = self.read(path)
                if os.path.basename(path) == 'SKILL.md':
                    frontmatter, _ = split_frontmatter(text)
                    name = frontmatter_field(frontmatter, 'name') or path.split('/')[-2]
                    self.add('skill', path, name, frontmatter_field(frontmatter, 'description'), text)
                else:
                    frontmatter, body = split_frontmatter(text)
                    description = frontmatter_field(frontmatter, 'description') or first_h1(body) or first_prose(body)
                    self.add('skill-file', path, path, description, text)

    def walk_references(self):
        prefix = '.claude/skills/gaia/references/'
        for path in self.files(prefix + '**/*.md'):
            text = self.read(path)
            _, body = split_frontmatter(text)
            self.add('reference', path, path[len(prefix):-3], first_prose(body) or first_h1(body), text)

    def resolve_import(self, module, spec):
        base = os.path.normpath(os.path.join(os.path.dirname(module), spec))
        stem = base[:-3] if base.endswith('.js') else base
        for candidate in (stem + '.ts', stem + '.tsx', stem + '/index.ts'):
            if self.exists(candidate):
                return candidate
        return None

    def routes(self, module, text):
        """(sub, child module or None) pairs a router module dispatches to."""
        imports = {}
        for names, spec in re.findall(r"import\s*\{([^}]*)\}\s*from\s*'(\.[^']+)'", text):
            for name in names.split(','):
                parts = name.strip().split(' as ')
                if parts[0]:
                    imports[parts[-1].strip()] = spec
        pairs = []
        tables = sorted(set(re.findall(r'lookupOwn\((\w+),', text)) | set(re.findall(r'handlers:\s*(\w+)', text)))
        for table in tables:
            body = re.search(r'const ' + table + r'\b.*?=\s*\{(.*?)\n\};', text, re.S)
            if body is None:
                self.ambiguities.append(f'{module}: router table {table} not found')
                continue
            for sub, handler in re.findall(r"^\s+'?([a-z][a-z0-9-]*)'?(?::\s*(\w+))?,$", body.group(1), re.M):
                pairs.append((sub, handler or sub))
        if not tables:
            pairs = re.findall(r"\b(?:sub|subcommand|action) === '([a-z][a-z0-9-]*)'\)\s*(?:return\s+(?:await\s+)?(\w+)\()?", text)
        routed = {}
        for sub, handler in pairs:
            child = self.resolve_import(module, imports[handler]) if handler in imports else None
            routed.setdefault(sub, child)
        return sorted(routed.items())

    def add_cli(self, module, words, depth):
        text = self.read(module)
        subs = self.routes(module, text)
        help = help_text(text)
        for sub, child in subs:
            own = f'{os.path.dirname(module)}/{sub}.ts'
            path = child if child and child != module else (own if self.exists(own) else module)
            name = ' '.join(['gaia'] + words + [sub])
            self.add('cli-subcommand', path, name, help_entry(help, sub), self.read(path))
            if path != module and depth < MAX_CLI_DEPTH:
                child_text = self.read(path)
                if re.search(r"lookupOwn\(|handlers:|\b(?:sub|subcommand|action) === '", child_text):
                    self.add_cli(path, words + [sub], depth + 1)
        return bool(subs)

    def walk_cli(self):
        index = CLI_SRC + '/index.ts'
        top = self.read(index)
        top_help = help_text(top)
        if top_help is None:
            self.ambiguities.append(f'{index}: no HELP_TEXT; CLI descriptions skipped')
        for namespace, module in self.routes(index, top):
            if module is None:
                self.ambiguities.append(f'{index}: namespace {namespace} has no resolvable relative import; not walked')
                continue
            text = self.read(module)
            routed = self.routes(module, text)
            if not routed:
                description = help_summary(help_text(text)) or help_entry(top_help, namespace)
                self.add('cli-subcommand', module, f'gaia {namespace}', description, text)
                continue
            self.add_cli(module, [namespace], 1)
        # Invocation audience: the adopter binary routes every handler above, even
        # though its source sits under the release-excluded .gaia/cli/src/.
        for record in self.items:
            if record['kind'] == 'cli-subcommand':
                record['audience'] = 'adopter'
                record.pop('marker_blocks', None)

    def walk_machinery(self):
        for path in self.files('.claude/hooks/*.sh'):
            text = self.read(path)
            self.add('hook', path, os.path.basename(path), comment_description(text), text)
        for path in self.files('.claude/hooks/lib/*'):
            text = self.read(path)
            if path.endswith('.md'):
                frontmatter, body = split_frontmatter(text)
                description = frontmatter_field(frontmatter, 'description') or first_h1(body)
            else:
                description = comment_description(text)
            self.add('hook-lib', path, os.path.basename(path), description, text)
        for path in self.files('.githooks/*'):
            self.add('githook', path, os.path.basename(path), comment_description(self.read(path)), self.read(path))
        rules = self.files('.claude/rules/*.md') + self.files('.claude/rules/maintainers/*.md')
        for path in rules + self.files('frontend/.claude/rules/*.md'):
            text = self.read(path)
            frontmatter, body = split_frontmatter(text)
            base = os.path.basename(path)[:-3]
            if '/maintainers/' in path:
                name = 'maintainers/' + base
            elif path.startswith('frontend/'):
                name = 'frontend:' + base
            else:
                name = base
            self.add('rule', path, name, frontmatter_field(frontmatter, 'description') or first_h1(body), text)
        for path in self.files('.claude/agents/*.md'):
            text = self.read(path)
            frontmatter, _ = split_frontmatter(text)
            name = frontmatter_field(frontmatter, 'name') or os.path.basename(path)[:-3]
            self.add('agent', path, name, frontmatter_field(frontmatter, 'description'), text)
        for path in self.files('frontend/.claude/agents/code-audit-frontend/*.md'):
            text = self.read(path)
            frontmatter, body = split_frontmatter(text)
            name = 'code-audit-frontend/' + os.path.basename(path)[:-3]
            self.add('agent', path, name, frontmatter_field(frontmatter, 'description') or first_h1(body), text)
        for kind, pattern in (('doctrine', '.claude/doctrine/*.md'), ('instruction', 'frontend/.claude/instructions/*.md')):
            for path in self.files(pattern):
                text = self.read(path)
                frontmatter, body = split_frontmatter(text)
                description = frontmatter_field(frontmatter, 'description') or first_h1(body)
                self.add(kind, path, os.path.basename(path)[:-3], description, text)
        for path in self.files('.github/workflows/*.yml'):
            text = self.read(path)
            match = re.search(r'^name:\s*(.+)$', text, re.M)
            self.add('workflow', path, os.path.basename(path), yaml_scalar(match.group(1)) if match else None, text)
        for path in self.files('wiki/**/*.md'):
            if '/.obsidian/' in path:
                continue
            text = self.read(path)
            frontmatter, body = split_frontmatter(text)
            self.add('wiki-page', path, path, frontmatter_field(frontmatter, 'description') or first_h1(body), text)


def export_tree(gaia, ref, target):
    """Extract the committed tree at ref into target; return the full commit SHA."""
    sha = subprocess.run(['git', '-C', gaia, 'rev-parse', '--verify', ref + '^{commit}'],
                         check=True, capture_output=True, text=True).stdout.strip()
    archive_path = os.path.join(os.path.dirname(target), 'tree.tar')
    with open(archive_path, 'wb') as handle:
        subprocess.run(['git', '-C', gaia, 'archive', '--format=tar', sha], check=True, stdout=handle)
    with tarfile.open(archive_path) as tar:
        tar.extractall(target, filter='data')
    return sha


def key(record):
    return record['kind'], record['name'], record['path']


def drift(previous, current):
    """Step 6 classification against the previous snapshot."""
    groups = collections.defaultdict(list)
    previous_by_key = {key(r): r for r in previous}
    current_keys = set()
    for record in current:
        current_keys.add(key(record))
        before = previous_by_key.get(key(record))
        if record['excluded_from_docs']:
            groups['EXCLUDED'].append(record)
        elif before is None:
            groups['NEW'].append(record)
        elif before['audience'] != record['audience']:
            groups['AUDIENCE-CHANGED'].append((before, record))
        elif (before['content_hash'] != record['content_hash']
              or before['description'] != record['description']
              or before.get('marker_blocks') != record.get('marker_blocks')):
            groups['CHANGED'].append((before, record))
        else:
            groups['VERIFIED'].append(record)
    groups['REMOVED'] = [r for r in previous if key(r) not in current_keys]
    return groups


def backtick_spans(text):
    return re.findall(r'`([^`\n]+)`', text)


def word_in(needle, haystack):
    return re.search(r'(?<![\w-])' + re.escape(needle) + r'(?![\w-])', haystack) is not None


def walk_docs(tree, items, previous):
    """Step 4 plus the DOC-ORPHAN / UNDOCUMENTED cross-reference."""
    pages = {}
    for path in sorted(glob.glob(os.path.join(DOCS_CONTENT, '**', '*.md*'), recursive=True)):
        with open(path, encoding='utf-8') as handle:
            pages[os.path.relpath(path, DOCS_CONTENT)] = handle.read()
    commands = {r['name'] for r in items if r['kind'] == 'command'}
    skills = {r['name'] for r in items if r['kind'] == 'skill'}
    known_commands = {r['name'] for r in previous if r['kind'] == 'command'} | commands
    known_skills = {r['name'] for r in previous if r['kind'] == 'skill'} | skills
    cli = collections.defaultdict(set)
    for r in items:
        if r['kind'] == 'cli-subcommand':
            words = r['name'].split()
            cli[words[1]].add(words[2] if len(words) > 2 else None)
    retired_prefix = re.compile(r'^/(?:gaia|setup|update|speckit)[-.]')

    orphans = []
    for page, text in pages.items():
        for number, line in enumerate(text.splitlines(), 1):
            for span in backtick_spans(line):
                token = span.split()[0]
                if re.fullmatch(r'/[a-z][a-z0-9.-]*', token):
                    if token not in commands and token[1:] not in skills and (
                            token in known_commands or token[1:] in known_skills or retired_prefix.match(token)):
                        orphans.append(f'{page}:{number} references command {token}')
                elif token in known_skills and token not in skills and len(span.split()) == 1:
                    orphans.append(f'{page}:{number} references skill {token}')
                cli_ref = re.match(r'^gaia ([a-z][a-z0-9-]*)(?: ([a-z][a-z0-9-]*))?', span)
                if cli_ref and not span.startswith('gaia-'):
                    namespace, sub = cli_ref.groups()
                    if namespace not in cli:
                        orphans.append(f'{page}:{number} references CLI gaia {namespace}')
                    elif sub and None not in cli[namespace] and sub not in cli[namespace]:
                        orphans.append(f'{page}:{number} references CLI gaia {namespace} {sub}')
                path = span.rstrip('/.,')
                if path.startswith(SURFACE_DIRS) and not path.startswith(PER_MACHINE) and not re.search(r'[\s<>*]', path):
                    if not os.path.exists(os.path.join(tree, path)):
                        orphans.append(f'{page}:{number} references path {path}')

    adopter_text = '\n'.join(text for page, text in pages.items() if not page.startswith(CONTRIBUTOR_PAGES))
    undocumented, cli_unnamed = [], 0
    for record in items:
        if record['audience'] == 'contributor' or record['excluded_from_docs']:
            continue
        if record['kind'] in ('wiki-page', 'reference', 'skill-file', 'hook-lib', 'doctrine') \
                or record['name'].startswith('code-audit-frontend/'):
            continue  # reached through their command, the wiki, or their parent; never named one by one
        if record['kind'] == 'cli-subcommand':
            if not word_in(record['name'], adopter_text):
                cli_unnamed += 1
            continue
        if record['kind'] == 'rule':
            needle = record['name'].split(':')[-1]
        elif record['kind'] in ('command', 'skill', 'agent', 'instruction'):
            needle = record['name']
        else:
            needle = os.path.basename(record['path']).rsplit('.', 1)[0]
        if not word_in(needle, adopter_text):
            undocumented.append(record)
    return orphans, undocumented, cli_unnamed


def label(record):
    where = '' if record['name'] == record['path'] else f" at {record['path']}"
    return f"{record['kind']} {record['name']}{where}"


def print_report(survey, gaia, sha, groups, orphans, undocumented, cli_unnamed, verbose):
    out = []
    emit = out.append
    emit(f'source-survey: {datetime.date.today().isoformat()}')
    emit(f'gaia path: {gaia} @ {sha[:8]}')
    emit(f'docs path: {os.path.relpath(DOCS_CONTENT, DOCS_ROOT)}')
    emit(f'release-exclude patterns: {len(survey.exclude)}')
    emit(f'release-scrub marker transforms: {len(survey.scrub)}')
    emit(f'do-not-document entries: {len(survey.do_not_document)}')
    emit('hash rule: sha256 of the whole file')

    counts = collections.defaultdict(collections.Counter)
    for record in survey.items:
        counts[record['kind']][record['audience']] += 1
    emit('\n## counts by layer')
    for kind in sorted(counts):
        c = counts[kind]
        emit(f"- {kind}: {sum(c.values())} (adopter {c['adopter']}, contributor {c['contributor']}, mixed {c['mixed']})")

    def section(title, rows):
        if rows:
            emit(f'\n## {title}')
            out.extend(rows)

    def by_audience(records, render):
        rows = []
        for audience in AUDIENCES:
            subset = [r for r in records if (r[1] if isinstance(r, tuple) else r)['audience'] == audience]
            if subset:
                rows.append(f'### {audience}')
                for r in subset:
                    rows.extend(render(r))
        return rows

    moves = collections.defaultdict(list)
    for before, now in groups['AUDIENCE-CHANGED']:
        line = f"- {label(now)}: was {before['audience']}, now {now['audience']}"
        if now['audience'] == 'contributor':
            line += f" (excluded by release-exclude line {survey.exclude_line(now['path'])})"
        elif now['audience'] == 'mixed':
            line += f" (gaia:maintainer-only blocks at {now['marker_blocks']})"
        moves[f"{before['audience']} -> {now['audience']}"].append(line)
    section('AUDIENCE-CHANGED (high priority)',
            [row for move in sorted(moves) for row in [f'### {move}'] + moves[move]])
    section('NEW (in source, not in snapshot, not excluded)', by_audience(
        groups['NEW'], lambda r: [f'- {label(r)}'] + ([f"  description: {r['description']}"] if r['description'] else [])))
    section('CHANGED (description or content drift)', by_audience(
        groups['CHANGED'], lambda pair: [
            f'- {label(pair[1])}',
            f"  was-hash: {pair[0]['content_hash'][:12]}  now-hash: {pair[1]['content_hash'][:12]}",
            f"  description-changed: {'yes' if pair[0]['description'] != pair[1]['description'] else 'no'}",
        ] + ([f"  marker-blocks: {pair[0].get('marker_blocks')} -> {pair[1].get('marker_blocks')}"]
             if pair[0].get('marker_blocks') != pair[1].get('marker_blocks') else [])))
    section('REMOVED (in snapshot, not in source)', [f"- {label(r)} (was {r['audience']})" for r in groups['REMOVED']])
    excluded = []
    for r in groups['EXCLUDED']:
        excluded += [f"- {r['kind']} at {r['path']} (name withheld)",
                     f"  reason: {survey.do_not_document_reason(r['path'], r['name'])}"]
    section('EXCLUDED (matched do-not-document.yml; never written to the snapshot)', excluded)
    verified = [f"- count: {len(groups['VERIFIED'])}"]
    if verbose:
        verified += [f'  - {label(r)}' for r in groups['VERIFIED']]
    section('VERIFIED', verified)
    if orphans:
        orphans = [f'- {o}' for o in orphans] + [
            '  (a migration page may name a retired command on purpose; check the context)']
    section('DOC-ORPHAN (documented but no longer in source)', orphans)
    unnamed = [f'- {label(r)}' for r in undocumented]
    if cli_unnamed:
        unnamed.append(f'- cli-subcommand: {cli_unnamed} not named on any adopter page (Claude runs these; '
                       'pages name one only where the reader needs it)')
    section('UNDOCUMENTED (adopter source items no adopter page names)', unnamed)
    section('ambiguities (unresolved during survey)', [f'- {a}' for a in sorted(set(survey.ambiguities))])
    print('\n'.join(out))


def write_snapshot(items, sha):
    # Excluded records stay out of the committed snapshot: their names are what
    # do-not-document.yml protects. EXCLUDED is recomputed from source every run.
    kept = [r for r in items if not r['excluded_from_docs']]
    snapshot = {'version': 1, 'captured_at': datetime.date.today().isoformat(), 'gaia_commit': sha, 'items': kept}
    handle, temp = tempfile.mkstemp(dir=os.path.dirname(SNAPSHOT), suffix='.tmp')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as out:
            json.dump(snapshot, out, indent=2, ensure_ascii=False)
            out.write('\n')
        os.replace(temp, SNAPSHOT)
    except BaseException:
        os.unlink(temp)
        raise
    return len(kept)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    parser.add_argument('--gaia', default=os.path.join(os.path.dirname(DOCS_ROOT), 'gaia'))
    parser.add_argument('--ref', default='HEAD', help='gaia commit, tag or branch to survey')
    parser.add_argument('--write', action='store_true', help='replace the snapshot with this survey')
    parser.add_argument('--verbose', action='store_true', help='list every VERIFIED item')
    args = parser.parse_args()
    if not hasattr(tarfile, 'data_filter'):
        sys.exit('survey.py needs a Python with tarfile extraction filters (3.12+, or 3.8.17+/3.11.4+ backports)')

    with tempfile.TemporaryDirectory() as scratch:
        tree = os.path.join(scratch, 'tree')
        os.mkdir(tree)
        sha = export_tree(args.gaia, args.ref, tree)
        survey = Survey(tree)
        items = survey.walk()
        previous = []
        if os.path.isfile(SNAPSHOT):
            with open(SNAPSHOT, encoding='utf-8') as handle:
                previous = json.load(handle).get('items', [])
        groups = drift(previous, items)
        orphans, undocumented, cli_unnamed = walk_docs(tree, items, previous)
        print_report(survey, args.gaia, sha, groups, orphans, undocumented, cli_unnamed, args.verbose)

    if args.write:
        count = write_snapshot(items, sha)
        print(f'\nsnapshot written: {count} items -> {os.path.relpath(SNAPSHOT, DOCS_ROOT)} (gaia {sha[:8]})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
