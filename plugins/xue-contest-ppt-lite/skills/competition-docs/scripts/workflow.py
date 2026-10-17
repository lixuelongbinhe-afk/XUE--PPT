#!/usr/bin/env python3
"""Local checkpoint DAG; records evidence, never claims to perform visual QA."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

STATES = {'pending', 'running', 'done', 'waiting', 'failed', 'skipped', 'stale'}
CHECKS = {'requirements', 'evidence', 'consistency', 'structure', 'visual'}

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def save(root, state):
    state['updated_at'] = now()
    tmp = root / 'state.json.tmp'
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(root / 'state.json')

def load(root):
    return json.loads((root / 'state.json').read_text())

def node(deps=()):
    return dict(status='pending', deps=list(deps), files={}, reason='', partial=False)

def init(root, formats):
    if (root / 'state.json').exists():
        raise ValueError('state.json exists; use refresh/show')
    fs = list(dict.fromkeys(formats))
    if not fs or set(fs) - {'docx', 'pdf', 'pptx', 'html'}:
        raise ValueError('select actual formats: docx,pdf,pptx,html')
    root.mkdir(parents=True, exist_ok=True)
    (root / 'work').mkdir(exist_ok=True)
    (root / 'outputs').mkdir(exist_ok=True)
    nodes = {'requirements': node(), 'sources': node(['requirements']),
             'research': node(['sources']), 'plan': node(['requirements', 'research']),
             'content': node(['plan', 'sources', 'research'])}
    if 'docx' in fs: nodes['docx'] = node(['content'])
    if 'pdf' in fs: nodes['pdf'] = node(['docx' if 'docx' in fs else 'content'])
    if set(fs) & {'pptx', 'html'}:
        nodes['design'] = node(['plan', 'content'])
        if 'html' in fs: nodes['html'] = node(['design', 'content'])
        if 'pptx' in fs: nodes['pptx'] = node(['design', 'content'])
    nodes['qa'] = node(fs)
    nodes['report'] = node()
    s = dict(schema=1, created_at=now(), formats=fs, nodes=nodes, history=[])
    save(root, s)
    return s

def invalidate(s, names, include=True):
    affected = set(names)
    while True:
        nxt = affected | {k for k, v in s['nodes'].items() if set(v['deps']) & affected}
        if nxt == affected: break
        affected = nxt
    for k in affected - (set() if include else set(names)):
        s['nodes'][k]['status'] = 'stale'
    return sorted(affected)

def refresh(root, s):
    changed = set()
    for k, v in s['nodes'].items():
        if v['status'] != 'done': continue
        for p, old in v['files'].items():
            q = Path(p) if Path(p).is_absolute() else root / p
            if not q.is_file() or digest(q) != old:
                changed.add(k)
                break
    # Also propagate explicitly failed/skipped/stale/waiting dependencies to old done outputs.
    for k, v in s['nodes'].items():
        if v['status'] == 'done' and any(s['nodes'][d]['status'] != 'done' and not (v.get('partial') and s['nodes'][d]['status'] in {'failed', 'skipped'}) for d in v['deps']):
            changed.add(k)
    if changed:
        invalidate(s, changed)
        s['history'].append(dict(at=now(), event='invalidate', nodes=sorted(changed)))
    return sorted(changed)

def acyclic(nodes):
    active, seen = set(), set()
    def walk(k):
        if k in active: raise ValueError('dependency cycle')
        if k in seen: return
        active.add(k)
        for d in nodes[k]['deps']:
            if d not in nodes: raise ValueError('unknown dependency: ' + d)
            walk(d)
        active.remove(k); seen.add(k)
    for k in nodes: walk(k)

def keypath(root, p, artifact=False):
    root = root.resolve()
    q = Path(p).expanduser()
    q = (root / q if not q.is_absolute() else q).resolve()
    if not q.is_file(): raise ValueError('missing file: ' + str(q))
    inside = q.is_relative_to(root)
    if artifact and not inside: raise ValueError('artifact must be inside task directory')
    return (str(q.relative_to(root)) if inside else str(q)), q

def qa_ok(root):
    try:
        qa = json.loads((root / 'qa.json').read_text())['checks']
        return all(qa[k]['status'] == 'passed' and isinstance(qa[k]['evidence'], str)
                   and (root / qa[k]['evidence']).resolve().is_relative_to(root)
                   and (root / qa[k]['evidence']).is_file() for k in CHECKS)
    except (OSError, KeyError, TypeError, ValueError):
        return False

def set_state(root, s, name, status, watch=(), artifacts=(), reason='', partial=False):
    refresh(root, s)
    if name not in s['nodes']: raise ValueError('unknown node')
    if status not in STATES: raise ValueError('unknown status')
    if status in {'waiting', 'failed', 'skipped'} and not reason.strip():
        raise ValueError('reason required')
    files = {}
    if status == 'done':
        deps = [s['nodes'][d] for d in s['nodes'][name]['deps']]
        if any(v['status'] in {'waiting', 'running', 'pending', 'stale'} for v in deps):
            raise ValueError('dependencies pending/stale/waiting; cannot consume')
        incomplete = any(v['status'] != 'done' or v.get('partial') for v in deps)
        if incomplete and not partial: raise ValueError('use --allow-partial for a draft from failed/skipped dependencies')
        partial = partial or incomplete
        if not artifacts: raise ValueError('done requires --artifact evidence')
        for a in artifacts:
            k, q = keypath(root, a, artifact=True); files[k] = digest(q)
        for w in watch:
            k, q = keypath(root, w); files[k] = digest(q)
        if name == 'qa':
            if partial or not qa_ok(root): raise ValueError('QA requires all five passed checks with existing evidence')
            k, q = keypath(root, 'qa.json'); files[k] = digest(q)
            qa = json.loads(q.read_text())['checks']
            for check in CHECKS:
                k, p = keypath(root, qa[check]['evidence'], artifact=True); files[k] = digest(p)
    invalidate(s, [name], include=False)
    s['nodes'][name].update(status=status, files=files, reason=reason, partial=partial, updated_at=now())
    s['history'].append(dict(at=now(), event='set', node=name, status=status, reason=reason))

def summary(root, s):
    refresh(root, s)
    issues = {k: v['status'] for k, v in s['nodes'].items() if k != 'report' and (v['status'] != 'done' or v.get('partial'))}
    ready = not issues and qa_ok(root)
    return dict(submission_status='ready' if ready else 'partial',
                requested=s['formats'], issues=issues,
                reasons={k: v['reason'] for k, v in s['nodes'].items() if v.get('reason')},
                note='record checks document actual review; hashes alone do not prove correctness')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sp = p.add_subparsers(dest='cmd', required=True)
    for cmd in ['init', 'show', 'refresh', 'report', 'add', 'link', 'set']:
        c = sp.add_parser(cmd); c.add_argument('task', type=Path)
        if cmd == 'init': c.add_argument('--formats', required=True)
        if cmd in {'add', 'link', 'set'}: c.add_argument('name')
        if cmd in {'add', 'link'}: c.add_argument('--deps', default='')
        if cmd == 'set':
            c.add_argument('status', choices=sorted(STATES))
            c.add_argument('--watch', action='append', default=[])
            c.add_argument('--artifact', action='append', default=[])
            c.add_argument('--reason', default='')
            c.add_argument('--allow-partial', action='store_true')
    a = p.parse_args(); root = a.task.resolve()
    try:
        if a.cmd == 'init': s = init(root, a.formats.split(','))
        else:
            s = load(root)
            if a.cmd in {'add', 'link'}:
                if a.cmd == 'add':
                    if a.name in s['nodes']: raise ValueError('node exists')
                    s['nodes'][a.name] = node()
                elif a.name not in s['nodes']: raise ValueError('unknown node')
                deps = list(dict.fromkeys(s['nodes'][a.name]['deps'] + [d for d in a.deps.split(',') if d]))
                s['nodes'][a.name]['deps'] = deps
                acyclic(s['nodes']); invalidate(s, [a.name])
            elif a.cmd == 'set':
                set_state(root, s, a.name, a.status, a.watch, a.artifact, a.reason, a.allow_partial)
            else: refresh(root, s)
            save(root, s)
        out = summary(root, s) if a.cmd == 'report' else s
        if a.cmd == 'report':
            (root / 'work' / 'delivery-report.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
        save(root, s)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        p.exit(2, f'error: {e}\n')

if __name__ == '__main__': main()
