import { useEffect, useMemo, useState } from "react";
import { api, type MCPObservability } from "../api";

type Check = { name:string; status:"PASS"|"WARN"|"FAIL"|"INFO"; detail:string };
type Event = {
  id:number; timestamp:string; level:string; source:string; title:string;
  message:string; details?:Record<string, unknown>; trace_id?:string|null;
  job_id?:string|null; scene_id?:number|null;
};
type Diagnostic = {
  service:string; version:string; checked_at:string;
  health:{ok:boolean;ffmpeg_available:boolean;opencv_available:boolean;ai_mode:string};
  telemetry:{
    otlp_endpoint_configured:boolean; otlp_headers_configured:boolean;
    otel_service_name:string; grafana_url_configured:boolean;
    grafana_probe:any; mcp_url_configured:boolean; mcp_health:any;
    grafana_tempo_datasource_uid_configured:boolean;
  };
  jobs:any[]; failures:any[];
  counts:{jobs:number;failed_jobs:number;active_jobs:number};
};

function Badge({status}:{status:string}) {
  return <b className={`diag-badge ${status.toLowerCase()}`}>{status}</b>;
}

function pretty(value: unknown) {
  try { return JSON.stringify(value, null, 2); } catch { return String(value); }
}

export default function Diagnostics(){
  const [data,setData]=useState<Diagnostic|null>(null);
  const [checks,setChecks]=useState<Check[]>([]);
  const [events,setEvents]=useState<Event[]>([]);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState("");
  const [filter,setFilter]=useState("ALL");
  const [agents,setAgents]=useState<any[]>([]);
  const [mcp,setMcp]=useState<any|null>(null);
  const [links,setLinks]=useState<any|null>(null);
  const [mcpLive,setMcpLive]=useState<MCPObservability|null>(null);
  const [mcpLiveError,setMcpLiveError]=useState("");

  const refresh=async()=>{
    try {
      const results = await Promise.allSettled([
        api.diagnostics(),
        api.diagnosticActivity(300),
        api.agents(),
        api.diagnosticsMcp(),
        api.observabilityLinks(),
      ]);
      if(results[0].status==="fulfilled") setData(results[0].value);
      if(results[1].status==="fulfilled") setEvents(results[1].value);
      if(results[2].status==="fulfilled") setAgents(results[2].value);
      if(results[3].status==="fulfilled") setMcp(results[3].value);
      if(results[4].status==="fulfilled") setLinks(results[4].value);

      const snapshot = results[0].status==="fulfilled" ? results[0].value : null;
      const latest = snapshot?.jobs?.[0];
      try {
        const live = await api.observabilityMcp(latest?.job_id, latest?.scene_id);
        setMcpLive(live);
        setMcpLiveError(live.connected ? "" : (live.error || "Grafana MCP unavailable"));
      } catch(e) {
        setMcpLiveError(e instanceof Error ? e.message : "Grafana MCP observability unavailable");
      }
    } catch(e) {
      setMessage(e instanceof Error?e.message:"Diagnostics unavailable");
    }
  };

  const run=async()=>{
    setBusy(true); setMessage("");
    try {
      const r=await api.runDiagnostics();
      setChecks(r.checks);
      await refresh();
    } catch(e) {
      setMessage(e instanceof Error?e.message:"Test run failed");
    } finally {
      setBusy(false);
    }
  };

  useEffect(()=>{
    void refresh();
    const id=window.setInterval(()=>void refresh(),3000);
    return()=>clearInterval(id);
  },[]);

  const filteredEvents=useMemo(
    ()=>filter==="ALL"?events:events.filter(e=>e.level===filter),
    [events,filter]
  );
  const safeDetail=(detail:string)=>detail
    .replace(/(authorization\s*(?:uses|header|=)?\s*[:=]?\s*)(?:basic|bearer)\s+[^\s,;]+/gi,"$1credential hidden")
    .replace(/(OTEL_EXPORTER_OTLP_HEADERS\s*[:=]?\s*)[^\s,;]+/gi,"$1credential hidden");
  const failed=data?.failures??[];
  const grafanaOk=data?.telemetry.grafana_probe?.status_code===200;
  const mcpOk=Boolean(mcp?.connected && mcp?.probe?.invocation === "SUCCESS");
  const latestAdk=events.find(e=>e.source==="adk");
  const adkDetails=(latestAdk?.details||{}) as any;

  return <div className="page diagnostics-page">
    <div className="page-top">
      <div>
        <p className="eyebrow">SYSTEM / OBSERVABILITY / CONTROL ROOM</p>
        <h1>Production Diagnostics</h1>
        <p className="page-description">Live evidence from the production worker, OpenTelemetry, Grafana Cloud and the real Grafana MCP runtime.</p>
      </div>
      <div className="header-actions">
        <div className="production-status"><span className={`status-dot ${failed.length?"":"healthy"}`}></span>{failed.length?`${failed.length} failed jobs`:"System operational"}</div>
        <button className="dark-button" onClick={()=>void run()} disabled={busy}>{busy?"Running tests…":"Run full diagnostics"}</button>
      </div>
    </div>

    {message&&<div className="diag-message">{message}</div>}

    <section className="stats diag-stats">
      <div className="stat-card"><span className="stat-label">TOTAL JOBS</span><strong>{data?.counts.jobs??"—"}</strong><span className="stat-description">Loaded from persistent registry</span></div>
      <div className="stat-card"><span className="stat-label">FAILED</span><strong>{data?.counts.failed_jobs??"—"}</strong><span className="stat-description">Post-production failures</span></div>
      <div className="stat-card"><span className="stat-label">ACTIVE</span><strong>{data?.counts.active_jobs??"—"}</strong><span className="stat-description">Currently processing</span></div>
      <div className="stat-card"><span className="stat-label">MCP TOOLS</span><strong>{mcpLive?.connected?mcpLive.tool_count:(mcp?.tool_count??"—")}</strong><span className="stat-description">{mcpLive?.connected?"Live Grafana MCP":"MCP unavailable"}</span></div>
    </section>

    <section className="diag-grid">
      <div className="panel diag-panel">
        <div className="panel-header"><div><span className="eyebrow">CORE SYSTEMS</span><h2>Runtime health</h2></div></div>
        <div className="check-list">
          <div className="check-row"><div className={`check-dot ${data?.health.ok?"pass":"fail"}`}></div><div><strong>FastAPI backend</strong><span>{data?.service} · v{data?.version}</span></div><Badge status={data?.health.ok?"PASS":"FAIL"}/></div>
          <div className="check-row"><div className={`check-dot ${data?.health.ffmpeg_available?"pass":"fail"}`}></div><div><strong>FFmpeg</strong><span>Real media processing engine</span></div><Badge status={data?.health.ffmpeg_available?"PASS":"FAIL"}/></div>
          <div className="check-row"><div className={`check-dot ${data?.health.opencv_available?"pass":"warn"}`}></div><div><strong>OpenCV</strong><span>Thumbnail / visual tooling</span></div><Badge status={data?.health.opencv_available?"PASS":"WARN"}/></div>
          <div className="check-row"><div className="check-dot pass"></div><div><strong>Persistent job registry</strong><span>{data?.counts.jobs??"—"} jobs loaded</span></div><Badge status="PASS"/></div>
        </div>
      </div>

      <div className="panel diag-panel">
        <div className="panel-header"><div><span className="eyebrow">GRAFANA / OTEL</span><h2>Observability path</h2></div></div>
        <div className="telemetry-list">
          <div><span>OTLP endpoint</span><Badge status={data?.telemetry.otlp_endpoint_configured?"PASS":"FAIL"}/></div>
          <div><span>OTLP authentication</span><Badge status={data?.telemetry.otlp_headers_configured?"PASS":"FAIL"}/></div>
          <div><span>Grafana API</span><Badge status={grafanaOk?"PASS":data?.telemetry.grafana_url_configured?"FAIL":"WARN"}/></div>
          <div><span>Tempo datasource UID</span><Badge status={data?.telemetry.grafana_tempo_datasource_uid_configured?"PASS":"WARN"}/></div>
          <div><span>Grafana MCP</span><Badge status={mcpLive?.connected?"PASS":"WARN"}/></div>
          <div><span>MCP tool coverage</span><Badge status={mcpLive?.connected&&mcpLive.tool_count>0?"PASS":"WARN"}/></div>
        </div>
        <p className="diag-note">Secrets stay server-side. The panels below show only live MCP results, queries, timestamps and sanitized metadata.</p>
      </div>
    </section>

    <section className="panel diag-panel mcp-observability-panel">
      <div className="panel-header">
        <div>
          <span className="eyebrow">LIVE GRAFANA MCP / RUNTIME EVIDENCE</span>
          <h2>MCP is seeing the production system</h2>
        </div>
        <div className="header-actions">
          <span className={`live-badge ${mcpLive?.connected?"":"offline"}`}><span/>{mcpLive?.connected?"MCP CONNECTED":"MCP UNAVAILABLE"}</span>
          <button className="text-button" onClick={()=>void refresh()}>Refresh →</button>
        </div>
      </div>

      {mcpLiveError && <div className="diag-message">{mcpLiveError}</div>}

      {!mcpLive?.connected ? (
        <div className="empty-state"><h2>No live MCP data</h2><p>{mcpLive?.error || "The backend has not returned a successful Grafana MCP observation yet."}</p></div>
      ) : <>
        <div className="stats diag-stats compact">
          <div className="stat-card"><span className="stat-label">TOOLS</span><strong>{mcpLive.tool_count}</strong><span className="stat-description">Returned by tools/list</span></div>
          <div className="stat-card"><span className="stat-label">DATASOURCES</span><strong>{mcpLive.datasources.length}</strong><span className="stat-description">Returned by Grafana MCP</span></div>
          <div className="stat-card"><span className="stat-label">LOG EVENTS</span><strong>{mcpLive.logs.length}</strong><span className="stat-description">{mcpLive.logs.length?"Real Loki results":"No matching log data"}</span></div>
          <div className="stat-card"><span className="stat-label">TRACES</span><strong>{mcpLive.traces.length}</strong><span className="stat-description">{mcpLive.traces.length?"Real Tempo results":"No matching trace data"}</span></div>
        </div>

        <div className="mcp-evidence-grid">
          <div className="mcp-evidence-card">
            <div className="panel-header"><div><span className="eyebrow">DATASOURCES</span><h3>Grafana backends</h3></div></div>
            {mcpLive.datasources.length===0?<p className="diag-note">No datasource data returned.</p>:
            <div className="mcp-table">{mcpLive.datasources.map((d,i)=><div className="mcp-table-row" key={`${d.uid||d.name||"ds"}-${i}`}><strong>{d.name||"Unnamed datasource"}</strong><span>{d.type||"type unavailable"}</span><small>{d.uid||"UID unavailable"}{d.isDefault?" · default":""}</small></div>)}</div>}
          </div>

          <div className="mcp-evidence-card">
            <div className="panel-header"><div><span className="eyebrow">ALERT RULES</span><h3>Current Grafana state</h3></div></div>
            {mcpLive.alerts.length===0?<p className="diag-note">No alert-rule data returned.</p>:
            <div className="mcp-table">{mcpLive.alerts.map((a,i)=><div className="mcp-table-row" key={`${a.uid||a.name||"alert"}-${i}`}><strong>{a.name||"Unnamed rule"}</strong><span>{a.state||"state unavailable"}</span><small>{a.health||"health unavailable"}{a.folder?` · ${a.folder}`:""}</small></div>)}</div>}
          </div>
        </div>

        <div className="mcp-evidence-grid">
          <div className="mcp-evidence-card">
            <div className="panel-header"><div><span className="eyebrow">LOKI / LIVE LOGS</span><h3>Real application events</h3></div><span>{mcpLive.checked_at?new Date(mcpLive.checked_at).toLocaleTimeString():""}</span></div>
            <div className="query-chip">{mcpLive.queries?.loki||"No LogQL query returned"}</div>
            {mcpLive.logs.length===0?<div className="empty-state"><h2>No log data</h2><p>The MCP query returned no Loki entries for the current window.</p></div>:
            <div className="diagnostic-log compact-log">{mcpLive.logs.slice(0,8).map((log,i)=><div className="diagnostic-event" key={`${log.timestamp}-${i}`}><time>{log.timestamp?new Date(Number(String(log.timestamp).replace(/"/g,""))/1_000_000).toLocaleTimeString():""}</time><span className="event-source">LOKI</span><div className="event-body"><strong>{log.labels?.event_title||"Application event"}</strong><p>{log.line||"Log line unavailable"}</p><small>{log.labels?.service_name||"service unavailable"}{log.labels?.trace_id?` · trace=${log.labels.trace_id}`:""}</small></div></div>)}</div>}
          </div>

          <div className="mcp-evidence-card">
            <div className="panel-header"><div><span className="eyebrow">TEMPO / LIVE TRACES</span><h3>Distributed traces</h3></div></div>
            <div className="query-chip">{mcpLive.queries?.tempo||"No TraceQL query returned"}</div>
            {mcpLive.traces.length===0?<div className="empty-state"><h2>No trace data</h2><p>The MCP query returned no matching Tempo traces.</p></div>:
            <div className="mcp-table">{mcpLive.traces.slice(0,8).map((t,i)=><div className="mcp-table-row" key={`${t.trace_id||"trace"}-${i}`}><strong>{t.root_operation||"Trace operation unavailable"}</strong><span>{t.duration_ms!=null?`${t.duration_ms} ms`:"duration unavailable"}</span><small>{t.trace_id||"trace ID unavailable"} · {t.root_service||"service unavailable"}</small></div>)}</div>}
          </div>
        </div>

        <div className="mcp-evidence-card">
          <div className="panel-header"><div><span className="eyebrow">ACTUAL MCP INVOCATIONS</span><h3>Tool activity behind this dashboard</h3></div><span>{mcpLive.tool_activity.length} calls</span></div>
          <div className="mcp-tool-grid">
            {mcpLive.tool_activity.map((call,i)=><div className="mcp-tool-card" key={`${call.tool}-${i}`}><div><strong>{call.tool}</strong><Badge status={call.status}/></div><small>{call.duration_ms!=null?`${call.duration_ms} ms`:"duration not returned"}</small><pre>{pretty(call.arguments||{})}</pre></div>)}
          </div>
        </div>

        <div className="mcp-evidence-card">
          <div className="panel-header"><div><span className="eyebrow">EVIDENCE / SOURCE</span><h3>What was actually queried</h3></div></div>
          <div className="mcp-evidence-list">{mcpLive.evidence.map((e,i)=><div key={`${e.label}-${i}`}><strong>{e.label}</strong><span>{e.tool}</span><small>{e.status} · {pretty(e.arguments||{})}</small></div>)}</div>
        </div>
      </>}
    </section>

    <section className="panel diag-panel">
      <div className="panel-header">
        <div><span className="eyebrow">ADK / GEMINI / MCP</span><h2>Production Orchestrator evidence</h2></div>
        <span>{latestAdk?.timestamp?new Date(latestAdk.timestamp).toLocaleTimeString():"No ADK run recorded"}</span>
      </div>
      {!latestAdk ? (
        <div className="empty-state"><h2>No ADK production run recorded</h2><p>The production worker has not yet persisted an ADK orchestration result.</p></div>
      ) : (
        <>
          <div className="telemetry-list">
            <div><span>Execution</span><b>{adkDetails.executed===true?"COMPLETED":adkDetails.executed===false?"DEGRADED":"Unavailable"}</b></div>
            <div><span>Grafana MCP invoked</span><b>{adkDetails.mcp_invoked===true?"YES — REAL TOOL CALLS":"No successful MCP invocation recorded"}</b></div>
            <div><span>Function calls</span><b>{adkDetails.function_call_count??"Unavailable"}</b></div>
            <div><span>Function responses</span><b>{adkDetails.function_response_count??"Unavailable"}</b></div>
            <div><span>Job</span><b>{latestAdk.job_id||"Unavailable"}</b></div>
          </div>
          {Array.isArray(adkDetails.mcp_tool_calls)&&adkDetails.mcp_tool_calls.length>0 ? (
            <div className="mcp-tool-grid" style={{marginTop:16}}>
              {adkDetails.mcp_tool_calls.map((call:any,i:number)=><div className="mcp-tool-card" key={`${call.id||call.name||"call"}-${i}`}><div><strong>{call.name||"Tool name unavailable"}</strong><Badge status="CALLED"/></div><small>{call.id||"call id unavailable"}</small><pre>{pretty(call.args||{})}</pre></div>)}
            </div>
          ) : <p className="diag-note">No ADK MCP tool-call records were persisted for the latest orchestration.</p>}
          {latestAdk.message&&<div className="diag-note"><strong>Agent result:</strong> {latestAdk.message}</div>}
          {adkDetails.final_response&&<div className="query-chip" style={{marginTop:12,whiteSpace:"pre-wrap"}}>{adkDetails.final_response}</div>}
          {adkDetails.error&&<div className="diag-message">ADK error: {adkDetails.error}</div>}
        </>
      )}
    </section>

    <section className="panel diag-panel">
      <div className="panel-header"><div><span className="eyebrow">GRAFANA CLOUD</span><h2>Live links</h2></div><span>{mcpOk?"MCP handshake verified":"MCP handshake not verified"}</span></div>
      <div className="telemetry-list">
        <div><span>Grafana Cloud</span>{links?.grafana?.home?<a className="grafana-link" href={links.grafana.home} target="_blank" rel="noreferrer">Open Grafana ↗</a>:<b>Unavailable</b>}</div>
        <div><span>Explore / Tempo & Loki</span>{links?.grafana?.explore?<a className="grafana-link" href={links.grafana.explore} target="_blank" rel="noreferrer">Open Explore ↗</a>:<b>Unavailable</b>}</div>
        <div><span>Dashboards</span>{links?.grafana?.dashboards?<a className="grafana-link" href={links.grafana.dashboards} target="_blank" rel="noreferrer">Open Dashboards ↗</a>:<b>Unavailable</b>}</div>
        <div><span>Cloud Run MCP</span>{links?.mcp?.endpoint?<a className="grafana-link" href={links.mcp.endpoint} target="_blank" rel="noreferrer">Open MCP endpoint ↗</a>:<b>Unavailable</b>}</div>
      </div>
    </section>

    <section className="panel diag-panel">
      <div className="panel-header"><div><span className="eyebrow">TEST LAB</span><h2>Latest full diagnostic run</h2></div><button className="text-button" onClick={()=>void refresh()}>Refresh →</button></div>
      {checks.length===0?<div className="empty-state"><h2>No manual test run yet</h2><p>Run the full diagnostics to validate configuration and connectivity.</p></div>:
      <div className="check-list">{checks.map(c=><div className="check-row" key={c.name}><div className={`check-dot ${c.status.toLowerCase()}`}></div><div><strong>{c.name}</strong><span>{safeDetail(c.detail)}</span></div><Badge status={c.status}/></div>)}</div>}
    </section>

    <section className="panel diag-panel">
      <div className="panel-header"><div><span className="eyebrow">AI / AGENTS</span><h2>Agent registry & latest activity</h2></div></div>
      <div className="check-list">{agents.map(a=><div className="check-row" key={a.id}><div className={`check-dot ${a.status==="ONLINE"?"pass":"warn"}`}></div><div><strong>{a.name}</strong><span>{a.description} · mode={a.mode} · last={a.last_run?.status||"not run"}</span></div><Badge status={a.status==="ONLINE"?"PASS":"WARN"}/></div>)}</div>
    </section>

    <section className="panel diag-panel">
      <div className="panel-header"><div><span className="eyebrow">LIVE JOBS</span><h2>Production workers</h2></div></div>
      {((data?.jobs)||[]).filter((j:any)=>["PENDING","PROCESSING","RETRYING"].includes(j.status)).length===0?
        <div className="empty-state"><h2>No active jobs</h2><p>The backend reports no currently processing jobs.</p></div>:
        <div className="live-job-grid">{(data?.jobs||[]).filter((j:any)=>["PENDING","PROCESSING","RETRYING"].includes(j.status)).slice(0,8).map((j:any)=><div className="live-job" key={j.job_id}><div><span>{j.job_id}</span><h3>Scene {j.scene_id}</h3></div><b>{j.stage}</b><p>{j.message}</p><div className="progress-track"><div className="progress-value" style={{width:j.progress==null?"0%":`${j.progress}%`}}/></div><small>{j.progress==null?"Progress unavailable":`${j.progress}%`} · {j.status}</small></div>)}</div>}
    </section>

    <section className="panel diag-panel">
      <div className="panel-header"><div><span className="eyebrow">FAILURE CENTER</span><h2>What failed / what recovered</h2></div></div>
      {failed.length===0?<div className="empty-state"><h2>No failed jobs</h2><p>The job registry currently contains no FAILED post-production jobs.</p></div>:
      <div className="failure-list">{failed.map(j=><div className="failure-card" key={j.job_id}>
        <div><span className="failure-id">{j.job_id}</span><h3>Scene {j.scene_id} · {j.error||"Unknown failure"}</h3><p>{j.created_at||""}</p></div>
        <button className="dark-button" onClick={async()=>{setMessage("Recovery started…");try{await api.recover(j.job_id);await refresh();setMessage("Recovery request completed.");}catch(e){setMessage(e instanceof Error?e.message:"Recovery failed");}}}>Retry / recover</button>
      </div>)}</div>}
    </section>

    <section className="panel diag-panel">
      <div className="panel-header"><div><span className="eyebrow">EVENT STREAM</span><h2>Detailed application activity</h2></div><div className="header-actions">{["ALL","INFO","WARN","ERROR"].map(x=><button key={x} className="text-button" onClick={()=>setFilter(x)}>{x}</button>)}</div></div>
      <div className="diagnostic-log">
        {filteredEvents.length===0?<div className="empty-state"><h2>No events yet</h2><p>New uploads, agent runs, processing jobs, approvals, failures and recoveries will appear here.</p></div>:
        filteredEvents.map(e=><div className="diagnostic-event" key={e.id}><time>{new Date(e.timestamp).toLocaleString()}</time><Badge status={e.level}/><span className="event-source">{e.source}</span><div className="event-body"><strong>{e.title}</strong><p>{e.message}</p>{(e.trace_id||e.job_id||e.scene_id)&&<small>{e.trace_id&&`trace=${e.trace_id} `}{e.job_id&&`job=${e.job_id} `}{e.scene_id&&`scene=${e.scene_id}`}</small>}</div></div>)}
      </div>
    </section>

    <section className="panel diag-panel">
      <div className="panel-header"><div><span className="eyebrow">GRAFANA MCP INVESTIGATION PLAYBOOK</span><h2>Live investigations</h2></div></div>
      <div className="mcp-prompts">
        <div><strong>Logs / Loki</strong><p>Search the real <code>service_name="thats-a-wrap-backend"</code> stream and inspect the returned event title, trace ID and OpenTelemetry metadata.</p></div>
        <div><strong>Traces / Tempo</strong><p>Use the actual TraceQL query shown above to correlate the latest job or scene with backend spans.</p></div>
        <div><strong>Alerts</strong><p>Review the alert rules returned by Grafana MCP. If there is no alert data, the UI says so instead of assuming health.</p></div>
        <div><strong>Grafana Explore</strong><p>Open Explore from this page to reproduce the same Loki/Tempo evidence directly in Grafana Cloud.</p></div>
      </div>
    </section>
  </div>;
}
