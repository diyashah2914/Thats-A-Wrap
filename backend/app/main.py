from pathlib import Path
from datetime import datetime, timezone
from fastapi import BackgroundTasks, FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.config import settings
from app.services.workflow import Workflow
from app.store import Store
from app.observability import Metrics
from app.grafana_live import GrafanaLiveClient, GrafanaLiveError
from app.mcp_grafana import GrafanaMCPClient, GrafanaMCPError
from app.mcp_observability import MCPObservability
from app.storage.gcs import Storage as GCSStorage, GCSStorageError
from app.schemas.contracts import ProjectRequest, SceneRequest, EditorRequest, FinalAssemblyRequest
from app.services.adk_orchestrator import ADKOrchestrator


import os
import logging
from concurrent.futures import ThreadPoolExecutor, Future

app=FastAPI(title="That's a Wrap! — AI Production Backend",version='2.1.0',description='AI-assisted filmmaking pipeline: script → agents → media → QC → approval → final film.')


from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter



# OpenTelemetry uses the same Settings object that reads backend/.env.
# This prevents the previous split-brain behavior where pydantic-settings could
# see .env while os.getenv() could not.
resource = Resource.create({
    "service.name": settings.otel_service_name or settings.service_name,
    "service.version": settings.service_version,
})
tracer_provider = TracerProvider(resource=resource)


def _parse_otel_headers(raw: str | None) -> dict[str, str]:
    """Parse OTEL_EXPORTER_OTLP_HEADERS without ever exposing secrets."""
    headers: dict[str, str] = {}
    if not raw:
        return headers
    from urllib.parse import unquote
    raw = raw.strip().strip('\"').strip("'")
    for part in raw.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = unquote(value.strip().strip('\"').strip("'"))
        if key:
            headers[key] = value
    return headers


_otlp_endpoint = (settings.otel_exporter_otlp_endpoint or "").strip().strip('\"').strip("'")
_otlp_headers = _parse_otel_headers(settings.otel_exporter_otlp_headers)

# Do not create a noisy localhost exporter when OTLP is intentionally disabled.
if _otlp_endpoint:
    _otlp_kwargs = {"headers": _otlp_headers} if _otlp_headers else {}
    otlp_exporter = OTLPSpanExporter(
        endpoint=f"{_otlp_endpoint.rstrip('/')}/v1/traces",
        **_otlp_kwargs,
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(settings.otel_service_name or settings.service_name)

# Export structured application logs through the same standard OTLP gateway.
# This gives Grafana/Loki a correlated application log stream without a custom
# Loki client. The endpoint is only enabled when OTLP is configured.
logger_provider = LoggerProvider(resource=resource)
if _otlp_endpoint:
    log_exporter = OTLPLogExporter(
        endpoint=f"{_otlp_endpoint.rstrip('/')}/v1/logs",
        **(_otlp_kwargs if _otlp_endpoint else {}),
    )
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
app_logger = logging.getLogger("thats-a-wrap")
app_logger.setLevel(logging.INFO)
app_logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))

FastAPIInstrumentor.instrument_app(app)


_allowed_origins=[o.strip() for o in settings.allowed_origins.split(',') if o.strip()]
app.add_middleware(CORSMiddleware,allow_origins=_allowed_origins,allow_credentials=False,allow_methods=['GET','POST','DELETE','OPTIONS'],allow_headers=['Content-Type'])
store=Store(settings.media_root); workflow=Workflow(settings.media_root, store=store); metrics=Metrics(); grafana_live=GrafanaLiveClient(); grafana_mcp = GrafanaMCPClient(); mcp_observability = MCPObservability(grafana_mcp); gcs=GCSStorage(settings.gcs_bucket, settings.google_cloud_project)
_live_request_times: dict[str, list[float]] = {}

def now(): return datetime.now(timezone.utc).strftime('%H:%M UTC')
def state(): return store.read()
def save(data): store.write(data)
def activity(title, description, icon='✦', level='INFO', source='application', details=None, trace_id=None, job_id=None, scene_id=None):
    event_id = int(datetime.now().timestamp() * 1000000)
    store.add_activity({
        'id': event_id,
        'title': title,
        'description': description,
        'time': now(),
        'icon': icon,
    })
    app_logger.log(getattr(logging, level.upper(), logging.INFO), description, extra={'event.title': title, 'event.source': source, 'event.job_id': job_id or '', 'event.scene_id': scene_id or ''})
    store.add_diagnostic_event({
        'id': event_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'level': level.upper(),
        'source': source,
        'title': title,
        'message': description,
        'details': details or {},
        'trace_id': trace_id,
        'job_id': job_id,
        'scene_id': scene_id,
    })
def projects_dict(d): return {int(k):v for k,v in d['projects'].items()}
def scenes_dict(d): return {int(k):v for k,v in d['scenes'].items()}

def ensure_seed():
    d=state()
    if not d['projects']:
        d['projects']['1']={'id':1,'name':'Demo Film','description':'AI-assisted short film production demo.','scenes':0,'completed':0,'script': ''}
        save(d)
ensure_seed()

@app.get('/health')
def health(): return {'ok':True,'version':'2.3.0-gcp-gcs','ai_mode':workflow.mode,'ffmpeg_available':workflow.media.available(),'opencv_available':workflow.cv.available(),'google_cloud_storage':gcs.status()}
@app.get('/metrics',response_class=PlainTextResponse)
def metrics_endpoint(): return metrics.prometheus()
@app.get('/projects')
def list_projects(): return list(projects_dict(state()).values())

@app.post('/projects')
def create_project(req:ProjectRequest):
    d=state(); ps=projects_dict(d); pid=max(ps.keys(),default=0)+1
    project={'id':pid,'name':req.name.strip(),'description':req.description.strip() or 'New film production.','scenes':0,'completed':0,'script':req.script}
    ps[pid]=project; d['projects']={str(k):v for k,v in ps.items()}
    generated=[]
    if req.script.strip():

        with tracer.start_as_current_span("director_scene_breakdown") as span:
            span.set_attribute("operation.type", "ai_scene_breakdown")
            span.set_attribute("scene.requested_count", req.scene_count)

            try:
                breakdown = workflow.director.analyse(
                    req.script,
                    req.scene_count
                )

                span.set_attribute(
                    "scene.generated_count",
                    len(breakdown.scenes)
                )
                span.set_attribute("operation.status", "success")

            except Exception as exc:
                span.record_exception(exc)
                span.set_status(
                    Status(StatusCode.ERROR, str(exc))
                )
                span.set_attribute("operation.status", "failed")
                raise

        sd=scenes_dict(d); next_id=max(sd.keys(),default=0)+1

        for offset,item in enumerate(breakdown.scenes):
            sid=next_id+offset
            row={
                'id':sid,
                'projectId':pid,
                'number':item.number,
                'title':item.title,
                'description':item.description,
                'status':'draft',
                'footage':[],
                'output':None,
                'breakdown':item.model_dump()
            }
            sd[sid]=row
            generated.append(row)

        d['scenes']={str(k):v for k,v in sd.items()}
        project['scenes']=len(generated)
        d['projects'][str(pid)]=project

        activity(
            f'Director Agent generated {len(generated)} scenes',
            f'Script analysed for {project["name"]}.',
            '✦'
        )

    else:
        activity(
            f'Created project {project["name"]}',
            'New production workspace created.',
            '+'
        )

    save(d)
    return {'project':project,'scenes':generated}

@app.delete('/projects/{project_id}')
def delete_project(project_id: int):
    d = state()
    ps = projects_dict(d)
    sd = scenes_dict(d)

    if project_id not in ps:
        raise HTTPException(404, 'Project not found')

    # Remove all scenes belonging to this project
    remaining_scenes = {
        str(k): v
        for k, v in sd.items()
        if v['projectId'] != project_id
    }

    # Remove the project
    del ps[project_id]

    d['projects'] = {
        str(k): v
        for k, v in ps.items()
    }
    d['scenes'] = remaining_scenes

    save(d)

    activity(
        'Project deleted',
        f'Project {project_id} was deleted.',
        '×'
    )

    return {
        'ok': True,
        'deleted_project_id': project_id
    }

@app.get('/projects/{project_id}')
def get_project(project_id:int):
    ps=projects_dict(state());
    if project_id not in ps: raise HTTPException(404,'Project not found')
    return ps[project_id]
@app.get('/projects/{project_id}/scenes')
def list_scenes(project_id:int): return [s for s in scenes_dict(state()).values() if s['projectId']==project_id]
@app.post('/projects/{project_id}/scenes')
def create_scene(project_id:int,req:SceneRequest):
    d=state(); ps=projects_dict(d); sd=scenes_dict(d)
    if project_id not in ps: raise HTTPException(404,'Project not found')
    sid=max(sd.keys(),default=0)+1; existing=[s for s in sd.values() if s['projectId']==project_id]
    row={'id':sid,'projectId':project_id,'number':len(existing)+1,'title':req.title.strip(),'description':req.description.strip() or 'Scene description.','status':'draft','footage':[],'output':None,'breakdown':{}}
    sd[sid]=row; ps[project_id]['scenes']=len(existing)+1; d['scenes']={str(k):v for k,v in sd.items()}; d['projects']={str(k):v for k,v in ps.items()}; save(d); activity(f'Created Scene {row["number"]:02d}',row['title'],'+'); return row



@app.get('/diagnostics')
async def diagnostics(request: Request):
    """Return a secret-free, system-wide diagnostics snapshot."""
    import httpx

    jobs = [j.model_dump() for j in workflow.jobs.values()]
    jobs.sort(key=lambda j: j.get('created_at') or j.get('completed_at') or j.get('started_at') or '', reverse=True)
    failures = [j for j in jobs if j.get('status') == 'FAILED']

    async def probe(url: str, headers: dict[str, str] | None = None) -> dict[str, object]:
        try:
            async with httpx.AsyncClient(timeout=3.5, follow_redirects=False) as client:
                r = await client.get(url, headers=headers or {})
            return {'reachable': True, 'status_code': r.status_code, 'detail': r.text[:180] if r.status_code >= 400 else 'OK'}
        except Exception as exc:
            return {'reachable': False, 'status_code': None, 'detail': str(exc)[:180]}

    grafana_probe = {'reachable': False, 'status_code': None, 'detail': 'Not configured'}
    if settings.grafana_url:
        headers = {'Authorization': f'Bearer {settings.grafana_observability_token}'} if settings.grafana_observability_token else {}
        grafana_probe = await probe(f"{settings.grafana_url.rstrip('/')}/api/health", headers)

    return {
        'service': settings.service_name,
        'version': settings.service_version,
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'health': {'ok': True, 'ffmpeg_available': workflow.media.available(), 'opencv_available': workflow.cv.available(), 'ai_mode': workflow.mode},
        'telemetry': {
            'otlp_endpoint_configured': bool(settings.otel_exporter_otlp_endpoint),
            'otlp_headers_configured': bool(settings.otel_exporter_otlp_headers),
            'otel_service_name': settings.otel_service_name,
            'grafana_url_configured': bool(settings.grafana_url),
            'grafana_probe': grafana_probe,
            'grafana_mcp_transport': 'streamable-http',
            'grafana_mcp_url': settings.grafana_mcp_url,
            'grafana_mcp_configured': bool(settings.grafana_mcp_url and settings.grafana_service_account_token),
            'grafana_links': {
                'home': settings.grafana_url.rstrip('/') if settings.grafana_url else None,
                'explore': f"{settings.grafana_url.rstrip('/')}/explore" if settings.grafana_url else None,
                'dashboards': f"{settings.grafana_url.rstrip('/')}/dashboards" if settings.grafana_url else None,
            },
            'grafana_tempo_datasource_uid_configured': bool(settings.grafana_tempo_datasource_uid),
        },
        'jobs': jobs[:50], 'failures': failures[:25],
        'counts': {
            'jobs': len(jobs), 'failed_jobs': len(failures),
            'active_jobs': sum(1 for j in jobs if j.get('status') in {'PENDING','PROCESSING','RETRYING'}),
        },
    }


@app.post('/diagnostics/run')
async def run_diagnostics():
    """Run safe local/configuration probes. Never returns credentials."""
    import httpx
    checks = []
    def add(name, ok, detail, status=None):
        checks.append({'name': name, 'status': status or ('PASS' if ok else 'FAIL'), 'detail': detail})

    add('API', True, 'FastAPI is responding.')
    ffmpeg_ok = workflow.media.available(); add('FFmpeg', ffmpeg_ok, 'Media engine available.' if ffmpeg_ok else 'FFmpeg executable unavailable.', 'PASS' if ffmpeg_ok else 'FAIL')
    opencv_ok = workflow.cv.available(); add('OpenCV', opencv_ok, 'OpenCV available.' if opencv_ok else 'OpenCV unavailable.', 'PASS' if opencv_ok else 'WARN')
    gemini_ok = workflow.mode == 'gemini'; add('Gemini', gemini_ok, 'Gemini API key detected and AI mode is active.' if gemini_ok else 'Gemini key not active; deterministic fallback is running.', 'PASS' if gemini_ok else 'WARN')
    otlp_ok = bool(settings.otel_exporter_otlp_endpoint); add('OTLP endpoint', otlp_ok, 'Loaded from backend/.env.' if otlp_ok else 'Missing OTEL_EXPORTER_OTLP_ENDPOINT.', 'PASS' if otlp_ok else 'FAIL')
    otlp_configured = bool(settings.otel_exporter_otlp_endpoint)
    auth_ok = bool(settings.otel_exporter_otlp_headers); add('OTLP authentication', auth_ok, 'Loaded from backend/.env.' if auth_ok else 'Missing OTEL_EXPORTER_OTLP_HEADERS; Grafana will reject direct OTLP with 401.', 'PASS' if auth_ok else 'FAIL')
    if otlp_configured:
        otlp_url = f"{settings.otel_exporter_otlp_endpoint.rstrip('/')}/v1/traces"
        try:
            async with httpx.AsyncClient(timeout=4, follow_redirects=False) as client:
                r = await client.get(otlp_url, headers=_parse_otel_headers(settings.otel_exporter_otlp_headers))
            if r.status_code == 401:
                add('OTLP gateway authentication', False, 'Grafana OTLP endpoint returned HTTP 401. The gateway rejected the configured credential. Configuration is present, but Grafana Cloud did not accept it.', 'FAIL')
            elif r.status_code in (404, 405):
                add('OTLP gateway connectivity', True, f'Grafana OTLP gateway is reachable (HTTP {r.status_code} to the read-only GET probe). POST is required for trace export; this probe does not validate the credential.', 'INFO')
            elif 200 <= r.status_code < 300:
                add('OTLP gateway connectivity', True, f'Grafana OTLP gateway responded HTTP {r.status_code} to the read-only probe. This does not validate trace-export authentication.', 'INFO')
            else:
                add('OTLP authentication probe', False, f'OTLP endpoint returned HTTP {r.status_code}.', 'WARN')
        except Exception as exc:
            add('OTLP authentication probe', False, f'Could not reach OTLP endpoint: {str(exc)[:160]}', 'WARN')

    if settings.grafana_url and settings.grafana_observability_token:
        try:
            async with httpx.AsyncClient(timeout=4, follow_redirects=False) as client:
                r = await client.get(f"{settings.grafana_url.rstrip('/')}/api/health", headers={'Authorization': f'Bearer {settings.grafana_observability_token}'})
            if r.status_code == 200: add('Grafana API', True, 'Grafana accepted the configured read/query credential.')
            elif r.status_code in (401, 403): add('Grafana API', False, f'Grafana returned HTTP {r.status_code}: credential is missing, expired, or lacks permission.', 'FAIL')
            else: add('Grafana API', False, f'Grafana returned HTTP {r.status_code}.', 'WARN')
        except Exception as exc: add('Grafana API', False, f'Could not reach Grafana: {str(exc)[:160]}', 'WARN')
    else: add('Grafana API', False, 'GRAFANA_URL and GRAFANA_OBSERVABILITY_TOKEN are not both configured.', 'WARN')

    add(
        'Grafana MCP configuration',
        bool(settings.grafana_url and settings.grafana_service_account_token),
        'Official grafana/mcp-grafana is configured for Grafana Cloud.'
        if settings.grafana_url and settings.grafana_service_account_token
        else 'Missing GRAFANA_URL or GRAFANA_SERVICE_ACCOUNT_TOKEN.',
        'PASS' if settings.grafana_url and settings.grafana_service_account_token else 'FAIL',
    )

    try:
        mcp_result = await grafana_mcp.probe()
        required = mcp_result.get('required_tools', {})
        missing = [name for name, present in required.items() if not present]
        if missing:
            add('Grafana MCP tool coverage', False, f'MCP connected but required tool groups are missing: {", ".join(missing)}.', 'WARN')
        else:
            add('Grafana MCP tool coverage', True, f"MCP connected with {mcp_result.get('tool_count', 0)} tools; Prometheus, Loki, dashboards, incidents and Tempo proxy are available.")
    except Exception as exc:
        add('Grafana MCP tool coverage', False, str(exc)[:180], 'WARN')

    add('Persistent activity log', True, f"{len(state().get('activities', []))} recent activity records available.")
    add('Job registry', True, f"{len(workflow.jobs)} jobs loaded; {sum(1 for j in workflow.jobs.values() if j.status == 'FAILED')} failed.")
    return {'ok': all(c['status'] != 'FAIL' for c in checks), 'checks': checks, 'timestamp': datetime.now(timezone.utc).isoformat()}


@app.get('/diagnostics/activity')
def diagnostics_activity(limit: int = 200, level: str | None = None, source: str | None = None):
    events = state().get('diagnostic_events', [])
    if level: events = [e for e in events if e.get('level') == level.upper()]
    if source: events = [e for e in events if e.get('source') == source]
    return events[:max(1, min(limit, 1000))]


@app.get('/diagnostics/mcp')
async def diagnostics_mcp(force: bool = False):
    """Inspect the real Cloud Run Grafana MCP server without exposing secrets."""
    inspected = await grafana_mcp.probe(force=force)
    if inspected.get('connected'):
        return {
            **inspected,
            'transport': 'streamable-http',
            'endpoint': settings.grafana_mcp_url,
            'probe': {
                'connected': True,
                'invocation': 'SUCCESS',
                'tool': 'tools/list',
                'reason': 'Remote Grafana MCP handshake and tools/list succeeded.',
            },
        }
    return {
        **inspected,
        'transport': 'streamable-http',
        'endpoint': settings.grafana_mcp_url,
        'probe': {
            'connected': False,
            'invocation': 'FAILED',
            'reason': inspected.get('error') or 'MCP probe failed.',
        },
    }


@app.get('/observability/mcp')
async def observability_mcp(
    request: Request,
    job_id: str | None = None,
    scene_id: str | None = None,
    force: bool = False,
):
    """Return live read-only Loki/Tempo/alert evidence obtained through Grafana MCP."""
    # Dashboard polling is intentionally lightweight. The MCP aggregation has
    # an 8-second cache and uses one MCP session for the three data queries.
    client_ip = request.client.host if request.client else 'unknown'
    now_ts = datetime.now(timezone.utc).timestamp()
    recent = [t for t in _live_request_times.get(f'mcp:{client_ip}', []) if now_ts - t < 60]
    if len(recent) >= 20:
        raise HTTPException(429, 'MCP observability rate limit exceeded; try again shortly.')
    recent.append(now_ts)
    _live_request_times[f'mcp:{client_ip}'] = recent
    return await mcp_observability.snapshot(
        job_id=job_id,
        scene_id=scene_id,
        force=force,
    )


@app.get('/observability/links')
def observability_links():
    base=settings.grafana_url.rstrip('/') if settings.grafana_url else None
    return {'grafana':{'home':base,'explore':f'{base}/explore' if base else None,'dashboards':f'{base}/dashboards' if base else None},'mcp':{'endpoint':settings.grafana_mcp_url},'tempo':f'{base}/explore' if base else None}

@app.get('/observability/live')
async def observability_live(request: Request):
    """Return a small, sanitized live view of recent Tempo traces.

    Grafana credentials never leave the backend. The response contains only
    trace IDs, timing, operation names, and allow-listed stage names.
    """
    # Small process-local guardrail: the UI polls every 5 seconds, while an
    # external caller gets at most 30 Grafana-backed requests per minute/IP.
    now_ts = datetime.now(timezone.utc).timestamp()
    client_ip = request.client.host if request.client else "unknown"
    recent = [t for t in _live_request_times.get(client_ip, []) if now_ts - t < 60]
    if len(recent) >= 30:
        raise HTTPException(429, "Live telemetry rate limit exceeded; try again shortly.")
    recent.append(now_ts)
    _live_request_times[client_ip] = recent
    try:
        return await grafana_live.live_traces()
    except GrafanaLiveError as exc:
        return {'connected': False, 'reason': str(exc), 'traces': []}

@app.get('/activity')
def list_activity(): return state()['activities'][:50]

@app.get('/agents/status')
def agent_status():
    profiles={
        'director-agent':('Director Agent','Creative direction & scene breakdown','Script + scene context','Scene breakdown, mood, visual intent','Defines the creative brief before post-production.'),
        'editor-agent':('Editor Agent','Take selection & edit decisions','Footage takes + scene context','Selected takes, pacing and continuity decisions','Ranks takes and selects the strongest usable performance.'),
        'sound-agent':('Sound Agent','Dialogue cleanup & mix direction','Scene audio + dialogue context','Dialogue normalization and music ducking plan','Protects dialogue while preparing the final sound mix.'),
        'music-agent':('Music Agent','Music placement & mix supervision','Scene mood + story context','Track choice, volume and fades','Selects an in-app score matched to the scene emotion.'),
        'colour-agent':('Colour Agent','Cinematic colour treatment','Scene mood + visual context','Grade and image treatment','Chooses the scene grade used by the FFmpeg renderer.'),
        'vfx-agent':('VFX Agent','Visual effects direction','Scene requirements + context','Clarity, vignette and contextual effects','Chooses restrained effects that reinforce the scene without hiding performance.'),
        'qc-agent':('QC Agent','Technical media validation','Rendered video + audio','Stream, duration and integrity checks','Rejects broken renders before a scene reaches approval.'),
        'production-agent':('Production Agent','Assembly orchestration & recovery','Approved scenes + failed jobs','Assembly plan, crossfades and recovery strategy','Coordinates final film assembly and safe job recovery.')}
    latest={a:None for a in profiles}
    for job in workflow.jobs.values():
        status='RUNNING' if job.status in {'PENDING','PROCESSING','RETRYING'} else ('COMPLETED' if job.status=='COMPLETED' else job.status); scene=f'Scene {job.scene_id}'
        for a in ('editor-agent','sound-agent','music-agent','colour-agent','vfx-agent','qc-agent'): latest[a]={'status':status,'scene':scene,'time':job.completed_at or job.started_at or job.created_at}
    for a in ('director-agent','production-agent'):
        if workflow.jobs:
            j=sorted(workflow.jobs.values(),key=lambda x:x.created_at or '',reverse=True)[0]
            latest[a]={'status':'COMPLETED' if j.status=='COMPLETED' else ('RUNNING' if j.status in {'PENDING','PROCESSING','RETRYING'} else j.status),'scene':f'Scene {j.scene_id}','time':j.completed_at or j.started_at or j.created_at}
    return [{'id':aid,'name':p[0],'description':p[1],'status':'ONLINE','mode':workflow.mode if aid in ('director-agent','editor-agent','music-agent') else 'local','role':p[1],'inputs':p[2],'outputs':p[3],'primary_action':p[4],'last_run':latest[aid]} for aid,p in profiles.items()]

@app.post('/agents/editor/select')
def editor_select(req:EditorRequest):
    d=state(); sd=scenes_dict(d)
    if req.scene_id not in sd: raise HTTPException(404,'Scene not found')
    scene=sd[req.scene_id]; decision=workflow.editor.select(f"scene_{scene['number']:02d}",scene['footage'],scene['description']); metrics.agent('editor-agent'); activity('Editor Agent evaluated takes',f'Scene {scene["number"]:02d}: {decision.selected_takes[0] if decision.selected_takes else "no take selected"}.','✦'); return decision.model_dump()

@app.post("/media/upload")
async def upload(
    scene_id: int = File(...),
    file: UploadFile = File(...),
):
    d = state()
    sd = scenes_dict(d)

    if scene_id not in sd:
        raise HTTPException(404, "Scene not found")

    if not file.filename:
        raise HTTPException(400, "Filename required")

    original_name = Path(file.filename).name
    ext = Path(original_name).suffix.lower()

    if ext not in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}:
        raise HTTPException(400, "Unsupported video format")

    # Never trust the incoming filename as the filesystem filename.
    # Generate a short, safe filename instead.
    import uuid

    safe_name = f"footage_{uuid.uuid4().hex[:12]}{ext}"

    root = (
        Path(settings.media_root)
        / "input"
        / f"scene_{scene_id}"
    )

    root.mkdir(parents=True, exist_ok=True)

    target = root / safe_name

    try:
        with target.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                out.write(chunk)
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save uploaded media: {exc}",
        ) from exc

    scene = sd[scene_id]
    scene["footage"].append(str(target))
    # Uploading footage does not mean post-production is running.
    # Keep the scene draft until the user explicitly starts Process Scene.
    if scene.get("status") != "processing":
        scene["status"] = "draft"

    d["scenes"] = {
        str(k): v
        for k, v in sd.items()
    }

    save(d)

    activity(
        "Footage uploaded",
        f"{original_name} attached to Scene {scene['number']:02d}.",
        "↑",
    )

    return {
        "filename": original_name,
        "stored_filename": safe_name,
        "path": str(target),
        "size": target.stat().st_size,
        "scene": scene,
    }
@app.get('/media/file')
def media_file(path:str):
    resolved=Path(path).resolve(); root=Path(settings.media_root).resolve()
    if root not in resolved.parents: raise HTTPException(403,'Invalid media path')
    if not resolved.exists(): raise HTTPException(404,'Media file not found')
    return FileResponse(resolved)

_adk_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="adk-observability")


def _run_adk_sync(job_id: str, scene_id: int, scene_context: str):
    # Use a fresh ADK runner per background thread. This keeps the media worker
    # independent from Gemini/MCP latency while still executing the real agent.
    return ADKOrchestrator().run_scene_orchestration_sync(
        job_id=job_id,
        scene_id=str(scene_id),
        scene_context=scene_context,
    )


def _record_adk_result(job_id: str, scene_id: int, result: dict):
    if not store:
        return
    store.add_diagnostic_event({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "INFO" if result.get("executed") else "WARN",
        "source": "adk",
        "title": "ADK production orchestration",
        "message": (
            "ADK orchestration completed with Grafana MCP activity."
            if result.get("mcp_invoked")
            else "ADK orchestration completed without a Grafana MCP tool call."
        ),
        "details": {
            "job_id": job_id,
            "scene_id": scene_id,
            "executed": result.get("executed"),
            "event_count": result.get("event_count"),
            "function_call_count": result.get("function_call_count"),
            "function_response_count": result.get("function_response_count"),
            "mcp_invoked": result.get("mcp_invoked"),
            "mcp_tool_calls": result.get("mcp_tool_calls"),
            "error": result.get("error"),
            "final_response": result.get("final_response"),
        },
        "trace_id": None,
        "job_id": job_id,
        "scene_id": int(scene_id),
    })


def _adk_done_callback(job_id: str, scene_id: int, future: Future):
    try:
        result = future.result()
    except Exception as exc:
        result = {
            "executed": False,
            "mcp_invoked": False,
            "error": f"{type(exc).__name__}: {exc}",
            "event_count": 0,
            "function_call_count": 0,
            "function_response_count": 0,
            "mcp_tool_calls": [],
            "final_response": "",
        }
    try:
        _record_adk_result(job_id, scene_id, result)
    except Exception:
        logging.getLogger(__name__).exception(
            "Could not persist ADK result for %s", job_id
        )


def _run_scene_job(scene_id: int, job_id: str, scene_context: str):
    """Run heavy AI/media work off the request path so the UI stays responsive."""
    with tracer.start_as_current_span("scene_processing") as span:
        span.set_attribute("operation.type", "ai_scene_post_production")
        span.set_attribute("scene.id", scene_id)
        span.set_attribute("job.id", job_id)
        try:
            # ADK is advisory observability/orchestration. Run it concurrently
            # with the real media worker so Gemini/MCP latency does not make a
            # three-minute footage render wait for an AI conversation.
            adk_future = _adk_executor.submit(
                _run_adk_sync,
                job_id,
                scene_id,
                scene_context,
            )
            adk_future.add_done_callback(
                lambda future, jid=job_id, sid=scene_id:
                    _adk_done_callback(jid, sid, future)
            )

            activity(
                f"Scene {scene_id:02d} ADK orchestration started",
                "Gemini/ADK is inspecting live Grafana telemetry in parallel with media processing.",
                "✦",
                source="adk",
                job_id=job_id,
                scene_id=str(scene_id),
            )

            job = workflow.run_job(job_id, scene_context)
            metrics.job_finished(job.job_id,job.status)

            for agent in [
                'editor-agent','sound-agent','music-agent',
                'colour-agent','vfx-agent','qc-agent'
            ]:
                metrics.agent(agent)

            d=state()
            sd=scenes_dict(d)
            if scene_id not in sd:
                span.set_attribute("operation.status","failed")
                return

            scene=sd[scene_id]
            if job.status=='COMPLETED':
                scene['status']='review'
                scene['output']=job.output
                scene['postProduction']=job.post_production_plan

                # Real Google Cloud runtime integration: every successful
                # processed scene is persisted to Google Cloud Storage when
                # GCS_BUCKET is configured.
                if gcs.enabled:
                    try:
                        gcs_uri=gcs.upload(job.output,f"scenes/scene_{scene['number']:02d}/{Path(job.output).name}",content_type='video/mp4')
                        scene['gcsUri']=gcs_uri
                        span.set_attribute('google_cloud.storage_enabled',True)
                        span.set_attribute('google_cloud.storage_uri',gcs_uri)
                        job.stage='REVIEW'; job.progress=100; job.message='QC passed and the artifact is uploaded; human review is pending.'; job.updated_at=datetime.now(timezone.utc).isoformat(); workflow._persist_job(job)
                    except GCSStorageError as exc:
                        span.record_exception(exc)
                        span.set_attribute('google_cloud.storage_status','failed')
                        scene['gcsUri']=None
                        activity(f'Scene {scene["number"]:02d} Google Cloud upload failed',str(exc),'!',level='ERROR',source='google-cloud-storage',scene_id=str(scene_id),job_id=job_id)
                        job.status='FAILED'; job.stage='GOOGLE_CLOUD_UPLOAD'; job.progress=96; job.error=str(exc); job.error_code='GCS_UPLOAD_FAILED'; job.message='QC passed, but the Google Cloud Storage upload failed.'; job.updated_at=datetime.now(timezone.utc).isoformat(); workflow._persist_job(job); scene['status']='failed'
                else:
                    scene['gcsUri']=None
                    span.set_attribute('google_cloud.storage_enabled',False)
                    job.stage='REVIEW'; job.progress=100; job.message='QC passed; GCS is not configured, so the local artifact is ready for human review.'; job.updated_at=datetime.now(timezone.utc).isoformat(); workflow._persist_job(job)

                if job.status=='COMPLETED':
                    activity(f'Scene {scene["number"]:02d} post-production complete','AI edit + cinematography + color grade + VFX + audio finish + QC completed.','✓',source='production',job_id=job_id,scene_id=str(scene_id))
                    span.set_attribute("operation.status","success")
                else:
                    span.set_attribute("operation.status","failed")
            else:
                scene['status']='failed'
                activity(
                    f'Scene {scene["number"]:02d} processing failed',
                    job.error or 'Unknown post-production error.',
                    '!',
                    source='production',
                    job_id=job_id,
                    scene_id=str(scene_id),
                )
                span.set_attribute("operation.status","failed")
            d['scenes']={str(k):v for k,v in sd.items()}
            save(d)
            span.set_attribute("job.status",job.status)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR,str(exc)))
            job=workflow.jobs.get(job_id)
            if job:
                job.status='FAILED'
                job.error=str(exc)
                job.completed_at=datetime.now(timezone.utc).isoformat()
                workflow._persist_job(job)

@app.post('/scenes/{scene_id}/process', status_code=202)
def process_scene(scene_id:int, background_tasks: BackgroundTasks):
    d=state()
    sd=scenes_dict(d)

    if scene_id not in sd:
        raise HTTPException(404,'Scene not found')

    scene=sd[scene_id]
    if not scene['footage']:
        raise HTTPException(400,'Upload footage first')

    # Reuse an existing active job instead of launching duplicate FFmpeg work.
    job=workflow.create_job(scene_id,scene['footage'])
    if job.status == 'PENDING':
        metrics.job_started(job.job_id)
        scene['status']='processing'
        d['scenes']={str(k):v for k,v in sd.items()}
        save(d)
        context=scene.get('description','')
        breakdown=scene.get('breakdown') or {}
        if breakdown:
            context += f"\nMood: {breakdown.get('mood','')}\nVisual style: {breakdown.get('visual_style','')}\nVFX requirements: {breakdown.get('vfx_requirements',[])}"
        activity(
            f'Scene {scene["number"]:02d} post-production started',
            'AI is selecting takes and directing color, VFX, cinematography, transitions and audio.',
            '✦',
            source='production',
            job_id=job.job_id,
            scene_id=str(scene_id),
        )
        background_tasks.add_task(_run_scene_job,scene_id,job.job_id,context)

    return {
        'job':job.model_dump(),
        'scene':scene,
        'status':'processing',
        'message':'AI scene post-production started.',
    }

@app.post('/scenes/{scene_id}/approve')
def approve(scene_id:int):
    d=state(); sd=scenes_dict(d); ps=projects_dict(d)
    if scene_id not in sd: raise HTTPException(404,'Scene not found')
    scene=sd[scene_id]; scene['status']='complete'
    for job in workflow.jobs.values():
        if str(job.scene_id)==str(scene_id) and job.status=='COMPLETED':
            job.stage='COMPLETED'; job.progress=100; job.message='Human review approved the scene for final assembly.'; job.updated_at=datetime.now(timezone.utc).isoformat(); workflow._persist_job(job)
    pid=scene['projectId']; ps[pid]['completed']=sum(1 for s in sd.values() if s['projectId']==pid and s['status']=='complete'); d['scenes']={str(k):v for k,v in sd.items()}; d['projects']={str(k):v for k,v in ps.items()}; save(d); activity(f'Scene {scene["number"]:02d} approved','Scene is ready for final assembly.','✓'); return scene
@app.post('/scenes/{scene_id}/reject')
def reject(scene_id:int):
    d=state(); sd=scenes_dict(d)
    if scene_id not in sd: raise HTTPException(404,'Scene not found')
    scene=sd[scene_id]; scene['status']='processing'; d['scenes']={str(k):v for k,v in sd.items()}; save(d); activity(f'Scene {scene["number"]:02d} sent back','Scene requires another processing pass.','↺'); return scene

@app.post('/jobs/{job_id}/recover', status_code=202)
def recover_job(job_id:str, background_tasks: BackgroundTasks):
    if job_id not in workflow.jobs:
        raise HTTPException(404,'Job not found')
    job=workflow.jobs[job_id]
    decision=workflow.production.diagnose(job)
    metrics.agent('production-agent')
    if decision['action']=='retry':
        job.status='RETRYING'
        job.retry_count+=1
        workflow._persist_job(job)
        d=state(); sd=scenes_dict(d)
        scene=sd.get(int(job.scene_id)) if str(job.scene_id).isdigit() else None
        context=scene.get('description','') if scene else ''
        if scene:
            scene['status']='processing'
            d['scenes']={str(k):v for k,v in sd.items()}
            save(d)
        metrics.job_started(job.job_id)
        background_tasks.add_task(_run_scene_job, int(job.scene_id), job.job_id, context)
        activity('Production Agent started recovery', f'{decision["strategy"]} → retrying Scene {scene["number"]:02d}.' if scene else decision["strategy"], '↺')
    else:
        activity('Production Agent escalated a failed job',decision['reason'],'!')
    return {'decision':decision,'job':job.model_dump()}

@app.get('/jobs')
def list_jobs(): return [j.model_dump() for j in workflow.jobs.values()]
@app.get('/jobs/{job_id}')
def get_job(job_id:str):
    if job_id not in workflow.jobs: raise HTTPException(404,'Job not found')
    return workflow.jobs[job_id].model_dump()

@app.get('/cloud/google-cloud')
def google_cloud_status():
    """Expose non-secret Google Cloud Storage configuration status for the UI/demo."""
    return gcs.status()


@app.post('/projects/{project_id}/assemble')
def assemble(project_id:int,req:FinalAssemblyRequest):
    with tracer.start_as_current_span('final_film_assembly') as span:
        span.set_attribute('operation.type','final_film_assembly')
        span.set_attribute('project.id', project_id)
        if project_id!=req.project_id: raise HTTPException(400,'Project ID mismatch')
        d=state(); sd=scenes_dict(d); ps=projects_dict(d)
        if project_id not in ps: raise HTTPException(404,'Project not found')
        approved=sorted([s for s in sd.values() if s['projectId']==project_id and s['status']=='complete' and s.get('output')],key=lambda s:s['number'])
        if not approved: raise HTTPException(400,'Approve at least one processed scene before final assembly.')
        span.set_attribute('assembly.scene_count', len(approved))
        try:
            output=workflow.assemble([s['output'] for s in approved],f'project_{project_id}_final_film.mp4')
            span.set_attribute('media.output', str(output))
            if gcs.enabled:
                try:
                    gcs_uri=gcs.upload(output,f'projects/project_{project_id}/final/project_{project_id}_final_film.mp4',content_type='video/mp4')
                    span.set_attribute('google_cloud.storage_enabled',True); span.set_attribute('google_cloud.storage_uri',gcs_uri)
                except GCSStorageError as exc:
                    span.record_exception(exc)
                    span.set_attribute('google_cloud.storage_status', 'failed')
                    raise HTTPException(502, f'Final film created locally but Google Cloud Storage upload failed: {exc}') from exc
            else:
                gcs_uri=None
                span.set_attribute('google_cloud.storage_enabled',False)
                span.set_attribute('google_cloud.storage_status','not_configured')
            span.set_attribute('operation.status','success')
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR,str(exc)))
            span.set_attribute('operation.status','failed')
            raise
        ps[project_id]['final_output']=output; ps[project_id]['final_gcs_uri']=gcs_uri; d['projects']={str(k):v for k,v in ps.items()}; save(d); activity('Final assembly completed', f'{len(approved)} approved scenes assembled.' + (f' Uploaded to Google Cloud Storage: {gcs_uri}' if gcs_uri else ' GCS is not configured; final film remains local.'), '🎬', source='final-assembly'); return {'project':ps[project_id],'output':output,'gcs_uri':gcs_uri,'scene_count':len(approved)}
