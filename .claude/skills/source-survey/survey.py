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

MARKER_START = re.compile(r'^\s*(<!--|#)\s*gaia:maintainer-only:start\b')
MARKER_END = re.compile(r'^\s*(<!--|#)\s*gaia:maintainer-only:end\b')
CLI_SRC = '.gaia/cli/src'
# Dirs whose files are surface records. A docs path under one of these that is
# missing from source is a DOC-ORPHAN; any other missing path (runtime files such
# as .gaia/local/* or settings.local.json) is created in the adopter's project.
SURFACE_DIRS = (
    '.claude/commands/', '.claude/skills/', '.claude/hooks/', '.claude/rules/', '.claude/agents/',
    'frontend/.claude/skills/', 'frontend/.claude/rules/', 'frontend/.claude/agents/',
    '.github/workflows/', '.githooks/', 'wiki/',
)
# Installed per machine and gitignored, so never in the committed tree.
PER_MACHINE = ('frontend/.claude/skills/react-doctor',)
AUDIENCES = ('adopter', 'contributor', 'mixed')


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


def md_hash(text):
    """Step 3 for .md: frontmatter lines plus the first 40 body lines.

    Mirrors the awk pipeline in SKILL.md: a file with no frontmatter hashes empty
    input, and a later `---` line in the body counts as body.
    """
    frontmatter, body, fences = [], [], 0
    for line in lines_of(text):
        if line == '---':
            fences += 1
            if fences <= 2:
                continue
        if fences == 1:
            frontmatter.append(line)
        elif fences >= 2:
            body.append(line)
    payload = ''.join(line + '\n' for line in frontmatter + body[:40])
    return hashlib.sha256(payload.encode()).hexdigest()


def plain_hash(text):
    """Step 3 for files without frontmatter: whole file under 200 lines, else the
    first 40 non-blank lines after any leading comment block."""
    lines = lines_of(text)
    if len(lines) < 200:
        return hashlib.sha256(text.encode()).hexdigest()
    i = 1 if lines and lines[0].startswith('#!') else 0
    while i < len(lines) and (lines[i].startswith('#') or not lines[i].strip()):
        i += 1
    kept = [line for line in lines[i:] if line.strip()][:40]
    return hashlib.sha256(''.join(line + '\n' for line in kept).encode()).hexdigest()


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


def marker_blocks(text):
    blocks, start = [], None
    for number, line in enumerate(text.split('\n'), 1):
        if MARKER_START.match(line):
            start = number
        elif MARKER_END.match(line) and start is not None:
            blocks.append([start, number])
            start = None
    return blocks


class Survey:
    def __init__(self, root):
        self.root = root
        self.items = []
        self.ambiguities = []
        self.exclude = self._load_exclude()
        self.do_not_document = self._load_do_not_document()

    def read(self, path):
        with open(os.path.join(self.root, path), encoding='utf-8', errors='replace') as handle:
            return handle.read()

    def files(self, pattern):
        found = glob.glob(os.path.join(self.root, pattern), recursive=True)
        return sorted(os.path.relpath(p, self.root) for p in found if os.path.isfile(p))

    def _load_exclude(self):
        patterns = []
        for number, line in enumerate(self.read('.gaia/release-exclude').splitlines(), 1):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                patterns.append((stripped.strip('/'), number))
        return patterns

    def _load_do_not_document(self):
        with open(DO_NOT_DOCUMENT, encoding='utf-8') as handle:
            text = handle.read()
        entry = re.compile(r'-\s+(path|name):\s*"?([^"\n]+)"?\n\s+reason:\s*(.+)')
        return [(m.group(1), m.group(2).strip(), m.group(3).strip()) for m in entry.finditer(text)]

    def exclude_line(self, path):
        for pattern, number in self.exclude:
            if path == pattern or path.startswith(pattern + '/') or fnmatch.fnmatch(path, pattern):
                return number
        return None

    def do_not_document_reason(self, path, name):
        for key, pattern, reason in self.do_not_document:
            if key == 'path' and fnmatch.fnmatch(path, pattern):
                return reason
            if key == 'name' and (fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(name, '*' + pattern)):
                return reason
        return None

    def add(self, kind, path, name, description, text, hasher):
        record = {'kind': kind, 'path': path, 'name': name, 'description': description}
        if self.exclude_line(path):
            record['audience'] = 'contributor'
        else:
            blocks = marker_blocks(text)
            record['audience'] = 'mixed' if blocks else 'adopter'
            if blocks:
                record['marker_blocks'] = blocks
        record['content_hash'] = hasher(text)
        record['excluded_from_docs'] = bool(self.do_not_document_reason(path, name))
        self.items.append(record)

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
            self.add('command', path, name, frontmatter_field(frontmatter, 'description'), text, md_hash)

    def walk_skills(self):
        for path in self.files('.claude/skills/*/SKILL.md') + self.files('frontend/.claude/skills/*/SKILL.md'):
            if '/react-doctor/' in path:
                continue
            text = self.read(path)
            frontmatter, _ = split_frontmatter(text)
            name = frontmatter_field(frontmatter, 'name') or path.split('/')[-2]
            self.add('skill', path, name, frontmatter_field(frontmatter, 'description'), text, md_hash)

    def walk_references(self):
        prefix = '.claude/skills/gaia/references/'
        for path in self.files(prefix + '**/*.md'):
            text = self.read(path)
            _, body = split_frontmatter(text)
            description = next((l.strip() for l in body if l.strip() and not l.strip().startswith('#')), None)
            self.add('reference', path, path[len(prefix):-3], description or first_h1(body), text, md_hash)

    def walk_cli(self):
        top = self.read(CLI_SRC + '/index.ts')
        imports = dict(re.findall(r"import \{run as (\w+)\} from '\./([^']+)\.js'", top))
        router = top.split('SUBCOMMAND_HANDLERS', 1)[1].split('};', 1)[0]
        handlers = re.findall(r"^\s+'?([a-z][a-z0-9-]*)'?: (\w+),$", router, re.M)
        help_text = top.split('HELP_TEXT = `', 1)[1].split('`', 1)[0]
        help_by_namespace = {}
        for line in help_text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith('Usage'):
                namespace, _, rest = stripped.partition(' ')
                help_by_namespace[namespace] = rest or None
        for namespace, handler in sorted(handlers):
            if handler not in imports:
                self.ambiguities.append(f'cli namespace {namespace}: handler {handler} has no relative import')
                continue
            module = f'{CLI_SRC}/{imports[handler]}.ts'
            module_text = self.read(module)
            if 'SUBCOMMAND_HANDLERS' in module_text:
                block = module_text.split('SUBCOMMAND_HANDLERS', 1)[1].split('};', 1)[0]
                subs = re.findall(r"^\s+'?([a-z][a-z0-9-]*)'?: \w+,$", block, re.M)
            else:
                subs = re.findall(r"\b(?:sub|subcommand) === '([a-z][a-z0-9-]*)'", module_text)
            description = help_by_namespace.get(namespace)
            if not subs:
                self.add('cli-subcommand', module, f'gaia {namespace}', description, module_text, plain_hash)
                continue
            for sub in sorted(set(subs)):
                own_file = f'{os.path.dirname(module)}/{sub}.ts'
                path = own_file if os.path.isfile(os.path.join(self.root, own_file)) else module
                self.add('cli-subcommand', path, f'gaia {namespace} {sub}', description, self.read(path), plain_hash)
        # Invocation audience: the adopter binary routes every handler above, even
        # though its source sits under the release-excluded .gaia/cli/src/.
        for record in self.items:
            if record['kind'] == 'cli-subcommand':
                record['audience'] = 'adopter'
                record.pop('marker_blocks', None)

    def walk_machinery(self):
        for path in self.files('.claude/hooks/*.sh'):
            text = self.read(path)
            self.add('hook', path, os.path.basename(path), hook_description(text), text, plain_hash)
        for path in self.files('.githooks/*'):
            self.add('githook', path, os.path.basename(path), None, self.read(path), plain_hash)
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
            self.add('rule', path, name, frontmatter_field(frontmatter, 'description') or first_h1(body), text, md_hash)
        for path in self.files('.claude/agents/*.md'):
            text = self.read(path)
            frontmatter, _ = split_frontmatter(text)
            name = frontmatter_field(frontmatter, 'name') or os.path.basename(path)[:-3]
            self.add('agent', path, name, frontmatter_field(frontmatter, 'description'), text, md_hash)
        for path in self.files('frontend/.claude/agents/code-audit-frontend/*.md'):
            text = self.read(path)
            frontmatter, body = split_frontmatter(text)
            name = 'code-audit-frontend/' + os.path.basename(path)[:-3]
            self.add('agent', path, name, frontmatter_field(frontmatter, 'description') or first_h1(body), text, md_hash)
        for path in self.files('.github/workflows/*.yml'):
            text = self.read(path)
            match = re.search(r'^name:\s*(.+)$', text, re.M)
            description = match.group(1).strip().strip('"\'') if match else None
            self.add('workflow', path, os.path.basename(path), description, text, plain_hash)
        for path in self.files('wiki/**/*.md'):
            if '/.obsidian/' in path:
                continue
            text = self.read(path)
            frontmatter, body = split_frontmatter(text)
            self.add('wiki-page', path, path, frontmatter_field(frontmatter, 'description') or first_h1(body), text, md_hash)


def hook_description(text):
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


def export_tree(gaia, ref, target):
    """Extract the committed tree at ref into target; return the full commit SHA."""
    sha = subprocess.run(['git', '-C', gaia, 'rev-parse', ref + '^{commit}'],
                         check=True, capture_output=True, text=True).stdout.strip()
    archive = subprocess.run(['git', '-C', gaia, 'archive', '--format=tar', sha],
                             check=True, capture_output=True).stdout
    archive_path = os.path.join(target, '..', 'tree.tar')
    with open(archive_path, 'wb') as handle:
        handle.write(archive)
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


def walk_docs(tree, items):
    """Step 4 plus the DOC-ORPHAN / UNDOCUMENTED cross-reference."""
    pages = {}
    for path in sorted(glob.glob(os.path.join(DOCS_CONTENT, '**', '*.md*'), recursive=True)):
        with open(path, encoding='utf-8') as handle:
            pages[os.path.relpath(path, DOCS_ROOT)] = handle.read()
    commands = {r['name'] for r in items if r['kind'] == 'command'}
    skills = {'/' + r['name'] for r in items if r['kind'] == 'skill'}
    orphans = []
    command_ref = re.compile(r'`(/(?:gaia|setup|update)-[a-z0-9-]+|/distribution-vet|/health-audit)`')
    path_ref = re.compile(r'`((?:\.claude|\.gaia|frontend|wiki|\.githooks|\.github)/[^`\s<>*]+)`')
    for page, text in pages.items():
        for number, line in enumerate(text.splitlines(), 1):
            for match in command_ref.finditer(line):
                if match.group(1) not in commands | skills:
                    orphans.append(f'{page}:{number} references command {match.group(1)}')
            for match in path_ref.finditer(line):
                path = match.group(1).rstrip('/.,')
                if path.startswith(PER_MACHINE):
                    continue
                if path.startswith(SURFACE_DIRS) and not os.path.exists(os.path.join(tree, path)):
                    orphans.append(f'{page}:{number} references path {path}')
    corpus = '\n'.join(pages.values())
    undocumented, cli_unnamed = [], 0
    for record in items:
        if record['audience'] == 'contributor' or record['excluded_from_docs']:
            continue
        if record['kind'] in ('wiki-page', 'reference') or record['name'].startswith('code-audit-frontend/'):
            continue  # reached through their command, the wiki, or the parent auditor; never named one by one
        if record['kind'] == 'cli-subcommand':
            if record['name'][len('gaia '):] not in corpus:
                cli_unnamed += 1
            continue
        if record['kind'] == 'rule':
            needle = record['name'].split(':')[-1]
        elif record['kind'] in ('command', 'skill', 'agent'):
            needle = record['name']
        else:
            needle = os.path.basename(record['path']).rsplit('.', 1)[0]
        if needle not in corpus:
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
    emit(f'do-not-document entries: {len(survey.do_not_document)}')
    emit('hash rule: .md frontmatter + first 40 body lines; other files whole if under 200 lines (sha256)')

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

    aud = []
    for before, now in groups['AUDIENCE-CHANGED']:
        line = f"- {label(now)}: was {before['audience']}, now {now['audience']}"
        if now['audience'] == 'contributor':
            line += f" (excluded by release-exclude line {survey.exclude_line(now['path'])})"
        elif now['audience'] == 'mixed':
            line += f" (gaia:maintainer-only blocks at {now['marker_blocks']})"
        aud.append(line)
    section('AUDIENCE-CHANGED (high priority)', aud)
    section('NEW (in source, not in snapshot, not excluded)', by_audience(
        groups['NEW'], lambda r: [f'- {label(r)}'] + ([f"  description: {r['description']}"] if r['description'] else [])))
    section('CHANGED (description or content drift)', by_audience(
        groups['CHANGED'], lambda pair: [
            f'- {label(pair[1])}',
            f"  was-hash: {pair[0]['content_hash'][:12]}  now-hash: {pair[1]['content_hash'][:12]}",
            f"  description-changed: {'yes' if pair[0]['description'] != pair[1]['description'] else 'no'}",
        ]))
    section('REMOVED (in snapshot, not in source)', [f"- {label(r)} (was {r['audience']})" for r in groups['REMOVED']])
    excluded = []
    for r in groups['EXCLUDED']:
        excluded += [f'- {label(r)}', f"  reason: {survey.do_not_document_reason(r['path'], r['name'])}"]
    section('EXCLUDED (matched do-not-document.yml)', excluded)
    verified = [f"- count: {len(groups['VERIFIED'])}"]
    if verbose:
        verified += [f'  - {label(r)}' for r in groups['VERIFIED']]
    section('VERIFIED', verified)
    if orphans:
        orphans = orphans + ['  (a migration page may name a retired command on purpose; check the context)']
    section('DOC-ORPHAN (documented but no longer in source)', [f'- {o}' if not o.startswith(' ') else o for o in orphans])
    unnamed = [f'- {label(r)}' for r in undocumented]
    if cli_unnamed:
        unnamed.append(f'- cli-subcommand: {cli_unnamed} not named on any page (Claude runs these; '
                       'pages name one only where the reader needs it)')
    section('UNDOCUMENTED (adopter source items with no docs reference)', unnamed)
    section('ambiguities (unresolved during survey)', [f'- {a}' for a in survey.ambiguities])
    print('\n'.join(out))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    parser.add_argument('--gaia', default=os.path.join(os.path.dirname(DOCS_ROOT), 'gaia'))
    parser.add_argument('--ref', default='HEAD', help='gaia commit, tag or branch to survey')
    parser.add_argument('--write', action='store_true', help='replace the snapshot with this survey')
    parser.add_argument('--verbose', action='store_true', help='list every VERIFIED item')
    args = parser.parse_args()

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
        orphans, undocumented, cli_unnamed = walk_docs(tree, items)
        print_report(survey, args.gaia, sha, groups, orphans, undocumented, cli_unnamed, args.verbose)

    if args.write:
        snapshot = {'version': 1, 'captured_at': datetime.date.today().isoformat(), 'gaia_commit': sha, 'items': items}
        with open(SNAPSHOT, 'w', encoding='utf-8') as handle:
            json.dump(snapshot, handle, indent=2, ensure_ascii=False)
            handle.write('\n')
        print(f'\nsnapshot written: {len(items)} items -> {os.path.relpath(SNAPSHOT, DOCS_ROOT)} (gaia {sha[:8]})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
