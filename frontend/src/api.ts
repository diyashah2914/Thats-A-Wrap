export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) { const message = await response.text(); throw new Error(message || `Request failed: ${response.status}`); }
  return response.json() as Promise<T>;
}

export type BackendProject = { id:number; name:string; description:string; scenes:number; completed:number; final_output?:string|null };
export type BackendScene = { id:number; projectId:number; number:number; title:string; description:string; status:"complete"|"processing"|"review"|"draft"|"failed"; footage:string[]; output?:string|null; postProduction?:any };
export type AgentStatus = { id:string; name:string; description:string; status:string; mode:string; role?:string; inputs?:string; outputs?:string; primary_action?:string; last_run?:{status:string;scene:string;time?:string|null}|null };
export type LiveTrace = { trace_id:string; root_service:string; root_operation:string; start_time:string; duration_ms:number; agents_and_stages:string[] };
export type LiveObservability = { connected:boolean; source?:string; window_minutes?:number; updated_at?:string; reason?:string; traces:LiveTrace[] };
export type GrafanaLinks = { grafana:{home:string|null;explore:string|null;dashboards:string|null}; mcp:{endpoint:string}; tempo:string|null };

export type MCPObservability = {
  connected:boolean;
  source?:string;
  checked_at?:string;
  tool_count:number;
  job_id?:string|null;
  scene_id?:string|null;
  error?:string|null;
  datasources:Array<{uid?:string;name?:string;type?:string;isDefault?:boolean}>;
  logs:Array<{timestamp?:string;line?:string;labels?:Record<string,string>;structuredMetadata?:Record<string,unknown>}>;
  log_metadata?:Record<string,unknown>;
  traces:Array<{trace_id?:string;root_service?:string;root_operation?:string;start_time?:string;duration_ms?:number;service_stats?:Record<string,unknown>;matched?:number}>;
  alerts:Array<{uid?:string;name?:string;state?:string;health?:string;folder?:string}>;
  tool_activity:Array<{tool:string;status:string;duration_ms?:number;arguments?:Record<string,unknown>;error?:string}>;
  evidence:Array<{label:string;tool:string;arguments?:Record<string,unknown>;status:string}>;
  queries?:{loki?:string;tempo?:string};
};

export type MCPStatus = { connected:boolean; transport?:string; endpoint?:string; server?:string; tool_count:number; tools:string[]; required_tools?:Record<string,boolean>; reason?:string; probe?:{connected?:boolean;invocation?:string;tool?:string;reason?:string;result_preview?:string} };

export const api = {
  health: () => request<{ok:boolean;version:string;ai_mode:string;ffmpeg_available:boolean;opencv_available:boolean}>("/health"),
  projects: () => request<BackendProject[]>("/projects"),
  createProject: (
  name: string,
  description: string,
  script = "",
  sceneCount = 5
) =>
  request<{ project: BackendProject; scenes: BackendScene[] }>(
    "/projects",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name,
        description,
        script,
        scene_count: sceneCount,
      }),
    }
  ),
  deleteProject: (projectId: number) =>
  request<{ok: boolean; deleted_project_id: number}>(
    `/projects/${projectId}`,
    {
      method: "DELETE"
    }
  ),
  scenes: (projectId:number) => request<BackendScene[]>(`/projects/${projectId}/scenes`),
  createScene: (projectId:number,title:string,description:string) => request<BackendScene>(`/projects/${projectId}/scenes`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({title,description})}),
  upload: (sceneId:number,file:File) => { const form=new FormData(); form.append("scene_id",String(sceneId)); form.append("file",file); return request<{filename:string;path:string;scene:BackendScene}>("/media/upload",{method:"POST",body:form}); },
  process: (sceneId:number) => request<{job:any;scene:BackendScene;status:string;message:string}>(`/scenes/${sceneId}/process`,{method:"POST"}),
  job: (jobId:string) => request<any>(`/jobs/${jobId}`),
  approve: (sceneId:number) => request<BackendScene>(`/scenes/${sceneId}/approve`,{method:"POST"}),
  reject: (sceneId:number) => request<BackendScene>(`/scenes/${sceneId}/reject`,{method:"POST"}),
  editor: (sceneId:number) => request<any>("/agents/editor/select",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scene_id:sceneId})}),
  agents: () => request<AgentStatus[]>("/agents/status"),
  observabilityLive: () => request<LiveObservability>("/observability/live"),
  activities: () => request<any[]>("/activity"),
  jobs: () => request<any[]>("/jobs"),
  diagnostics: () => request<any>("/diagnostics"),
  runDiagnostics: () => request<any>("/diagnostics/run", { method: "POST" }),
  diagnosticActivity: (limit=250) => request<any[]>(`/diagnostics/activity?limit=${limit}`),
  diagnosticsMcp: () => request<MCPStatus>("/diagnostics/mcp"),
  observabilityLinks: () => request<GrafanaLinks>("/observability/links"),
  observabilityMcp: (jobId?:string, sceneId?:number) => request<MCPObservability>(`/observability/mcp${jobId||sceneId ? `?${new URLSearchParams({...(jobId?{job_id:jobId}:{}),...(sceneId?{scene_id:String(sceneId)}:{})}).toString()}` : ""}`),
  recover: (jobId:string) => request<any>(`/jobs/${jobId}/recover`, { method: "POST" }),
  assemble: (projectId:number) => request<{project:BackendProject;output:string;scene_count:number}>(`/projects/${projectId}/assemble`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({project_id:projectId})}),
  mediaUrl: (path:string) => `${API_BASE}/media/file?path=${encodeURIComponent(path)}`,
};
