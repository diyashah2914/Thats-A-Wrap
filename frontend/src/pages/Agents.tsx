import { useEffect, useState } from "react";
import { api, type AgentStatus, type LiveObservability, type MCPStatus } from "../api";

function Agents(){
 const [agents,setAgents]=useState<AgentStatus[]>([]);
 const [live,setLive]=useState<LiveObservability|null>(null);
 const [mcp,setMcp]=useState<MCPStatus|null>(null);
 const refresh=async()=>{
   const [agentResult,liveResult,mcpResult]=await Promise.allSettled([api.agents(),api.observabilityLive(),api.diagnosticsMcp()]);
   if(agentResult.status==="fulfilled") setAgents(agentResult.value);
   if(liveResult.status==="fulfilled") setLive(liveResult.value);
   if(mcpResult.status==="fulfilled") setMcp(mcpResult.value);
 };
 useEffect(()=>{void refresh(); const timer=window.setInterval(()=>void refresh(),5000); return()=>window.clearInterval(timer);},[]);
 const latestStages=live?.traces.flatMap(t=>t.agents_and_stages).filter((v,i,a)=>a.indexOf(v)===i).slice(0,8)??[];
 return <div className="page"><div className="page-top"><div><p className="eyebrow">AI SYSTEM / PRODUCTION CREW</p><h1>Agents</h1><p className="page-description">Specialist agents with defined inputs, decisions and execution responsibilities across the post-production pipeline.</p></div><span className="live-badge"><span/> {mcp?.probe?.invocation==="SUCCESS"?"GRAFANA MCP LIVE":live?.connected?"TEMPO LIVE":"TELEMETRY UNAVAILABLE"}</span></div>
 <div className="agents-grid">{agents.map(a=><div className="agent-page-card" key={a.id}><div className="agent-large-icon">✦</div><div className="agent-card-main"><div className="agent-card-heading"><span className="agent-type">{(a.role||a.name.replace(" Agent","")).toUpperCase()}</span><span className="agent-online">{a.status}</span></div><h2>{a.name}</h2><p>{a.description}</p><div className="agent-profile-grid"><div><span>INPUTS</span><strong>{a.inputs}</strong></div><div><span>OUTPUT</span><strong>{a.outputs}</strong></div></div><div className="agent-action"><span>PRIMARY ACTION</span><p>{a.primary_action}</p></div><div className="agent-last">{a.last_run?<><span>LAST RUN · {a.last_run.status}</span><strong>{a.last_run.scene}</strong></>:<><span>STATUS</span><strong>Ready for first scene</strong></>}</div><small>{a.mode==="gemini"?"Gemini structured reasoning + local execution":"Local execution with deterministic fallback"}</small></div></div>)}</div>
 <section className="panel diag-panel" style={{marginTop:24}}><div className="panel-header"><div><span className="eyebrow">LIVE TELEMETRY</span><h2>What Grafana is seeing</h2></div><span>{live?.updated_at?new Date(live.updated_at).toLocaleTimeString():"Waiting…"}</span></div>{!live?.connected?<p className="diag-note">{live?.reason||"Connect the backend to Grafana Cloud to stream recent Tempo traces here."}</p>:<><div className="telemetry-list"><div><span>MCP</span><b>{mcp?.probe?.invocation==="SUCCESS"?"REAL CALL VERIFIED":mcp?.connected?"CONNECTED / NO TOOL CALL":"UNAVAILABLE"}</b></div><div><span>Source</span><b>{live.source}</b></div><div><span>Window</span><b>Last {live.window_minutes} minutes</b></div><div><span>Recent traces</span><b>{live.traces.length}</b></div><div><span>Observed stages</span><b>{latestStages.length}</b></div></div><div className="failure-list">{live.traces.slice(0,5).map(t=><div className="failure-card" key={t.trace_id}><div><span className="failure-id">{t.trace_id.slice(0,16)}…</span><h3>{t.root_operation}</h3><p>{t.duration_ms} ms · {t.agents_and_stages.slice(0,4).join(" → ")||"Trace recorded"}</p></div></div>)}</div></>}</section>
 </div>
}
export default Agents;
