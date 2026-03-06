# MA-01 Result (Runtime Baseline)

## Findings
- Effective runtime settings show project-local `.codex/config.toml` overrides global `~/.codex/config.toml` when both define the same key; otherwise global defaults remain effective.
- Role definitions are coherent and conflict-free across `explorer`, `docs_researcher`, `worker`, `reviewer`, and `monitor`.
- Sandbox posture is internally consistent with dispatch intent: one write-capable role (`worker`), all other roles read-only.
- No approval-policy contradictions were found in runtime config scope (no competing approval knobs in global/project TOML); publish-skill policy remains explicit-only.

Effective settings table (global/project/effective):

| Setting | Global (`~/.codex/config.toml`) | Project (`.codex/config.toml`) | Effective | Source |
|---|---|---|---|---|
| `model` | `gpt-5.3-codex` | unset | `gpt-5.3-codex` | global |
| `model_reasoning_effort` | `medium` | unset | `medium` | global |
| `features.multi_agent` | `true` | `true` | `true` | project |
| `otel.environment` | `macbook-prod` | `cpp-playground-local` | `cpp-playground-local` | project |
| `otel.log_user_prompt` | `true` | `true` | `true` | project |
| `otel.exporter.otlp-http.endpoint` | `http://127.0.0.1:4318/v1/logs` | `http://127.0.0.1:4318` | `http://127.0.0.1:4318` | project |
| `otel.trace_exporter.otlp-http.endpoint` | `http://127.0.0.1:4318/v1/traces` | `http://127.0.0.1:4318` | `http://127.0.0.1:4318` | project |
| `agents.max_threads` | unset | `6` | `6` | project |
| `agents.max_depth` | unset | `1` | `1` | project |
| `agents.job_max_runtime_seconds` | unset | `3600` | `3600` | project |

Conflict list:
- None.

## Evidence Commands
1. Read MA-01 prompt and MA policy docs:
```bash
sed -n '1,220p' .codex/multi-agent/prompts/MA-01.md
sed -n '1,260p' .codex/multi-agent/AGENTS.md
sed -n '1,260p' .codex/multi-agent/THREADS.md
sed -n '1,260p' .codex/multi-agent/DISPATCH_POLICY.md
```

2. Inspect project/global runtime config and role files:
```bash
sed -n '1,260p' .codex/config.toml
for f in .codex/agents/*.toml; do echo "--- $f"; sed -n '1,260p' "$f"; done
sed -n '1,260p' ~/.codex/config.toml
```

3. Compute effective setting values across both scopes:
```bash
python3 - <<'PY'
import tomllib, pathlib, json
g=pathlib.Path.home()/'.codex/config.toml'
p=pathlib.Path('.codex/config.toml')
with g.open('rb') as f: gc=tomllib.load(f)
with p.open('rb') as f: pc=tomllib.load(f)
keys=[('model',),('model_reasoning_effort',),('features','multi_agent'),('otel','environment'),('otel','log_user_prompt'),('otel','exporter'),('otel','trace_exporter'),('agents','max_threads'),('agents','max_depth'),('agents','job_max_runtime_seconds')]
def get(d,path):
    cur=d
    for k in path:
        if not isinstance(cur,dict) or k not in cur:
            return None
        cur=cur[k]
    return cur
rows=[]
for path in keys:
    gv=get(gc,path); pv=get(pc,path)
    rows.append({'key':'.'.join(path),'global':gv,'project':pv,'effective':pv if pv is not None else gv,'source':'project' if pv is not None else ('global' if gv is not None else 'unset')})
print(json.dumps(rows,indent=2,default=str))
PY
```

4. Validate role coherence and sandbox policy consistency:
```bash
python3 - <<'PY'
import tomllib, pathlib, json
cfg=tomllib.loads(pathlib.Path('.codex/config.toml').read_text())
roles=['explorer','docs_researcher','worker','reviewer','monitor']
rows=[]
errors=[]
seen=set()
for r in roles:
    cf=cfg.get('agents',{}).get(r,{}).get('config_file')
    p=pathlib.Path('.codex')/cf if cf else None
    exists=bool(p and p.exists())
    sandbox=None
    if exists:
        sandbox=tomllib.loads(p.read_text()).get('sandbox_mode')
    rows.append({'role':r,'config_file':cf,'exists':exists,'sandbox_mode':sandbox})
    if not exists: errors.append(f'missing config for {r}')
    if cf in seen: errors.append(f'duplicate config file {cf}')
    seen.add(cf)
    if r=='worker' and sandbox!='workspace-write': errors.append('worker sandbox mismatch')
    if r!='worker' and sandbox!='read-only': errors.append(f'{r} sandbox mismatch')
print(json.dumps(rows, indent=2))
print('errors=', errors)
PY
```

5. Confirm explicit invocation publish policy and approval/sandbox keyword scan:
```bash
sed -n '1,220p' .agents/skills/cpp26-dev-image-publish/agents/openai.yaml
rg -n "approval|sandbox|allow_implicit_invocation|policy:" .codex .agents/skills/cpp26-dev-image-publish/agents/openai.yaml
```

## PASS/FAIL
- Goal 1 (effective settings table for global/project precedence): **PASS**
- Goal 2 (role definitions coherent and conflict-free): **PASS**
- Goal 3 (safety/approval/sandbox interactions non-contradictory): **PASS**
- Overall MA-01: **PASS**

## Blockers (Owner Thread)
- None.

## Learnings
- For MA runtime baselines, include a computed effective-settings matrix (global vs project) rather than only listing raw TOML content.
- Role coherence checks are stronger when validated both structurally (declared + file exists) and behaviorally (sandbox alignment by role intent).
- Approval/safety checks should explicitly separate runtime-level controls from skill-level invocation policies to avoid false conflict reports.
