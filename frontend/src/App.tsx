import "./App.css";
import { useEffect, useMemo, useState } from "react";
import Projects from "./pages/Projects";
import Scenes from "./pages/Scenes";
import Agents from "./pages/Agents";
import Activity from "./pages/Activity";
import Settings from "./pages/Settings";
import Profile from "./pages/Profile";
import Diagnostics from "./pages/Diagnostics";
import NewScene from "./pages/NewScene";
import UploadFootage from "./pages/UploadFootage";
import ReviewScenes from "./pages/ReviewScenes";
import OpenProject from "./pages/OpenProject";
import NewProject from "./pages/NewProject";
import { api, type BackendProject, type BackendScene } from "./api";

export type Project = BackendProject;
export type Scene = BackendScene;
export type ActivityItem = { id: number; title: string; description: string; time: string; icon: string };

function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [selectedProjectId, setSelectedProjectId] = useState(1);
  const [projects, setProjects] = useState<Project[]>([]);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [backend, setBackend] = useState("Connecting…");
  const [error, setError] = useState("");

  const load = async (projectId?: number) => {
    try {
      const [health, projectList, activityList] = await Promise.all([api.health(), api.projects(), api.activities()]);
      setBackend(`${health.ffmpeg_available ? "Media ready" : "FFmpeg missing"} · ${health.ai_mode === "gemini" ? "Gemini online" : "AI fallback"}`);
      setProjects(projectList); setActivities(activityList);
      const id = projectId ?? projectList[0]?.id;
      if (id) { setSelectedProjectId(id); setScenes(await api.scenes(id)); } else setScenes([]);
      setError("");
    } catch (e) { setBackend("Backend offline"); setError(e instanceof Error ? e.message : "Backend unavailable"); }
  };
  useEffect(() => { void load(); }, []);

  const selectedProject = projects.find((p) => p.id === selectedProjectId) ?? projects[0];
  const selectedScenes = useMemo(() => scenes.filter((s) => s.projectId === selectedProjectId), [scenes, selectedProjectId]);
  const goToProject = async (id: number) => { setSelectedProjectId(id); setActivePage("OpenProject"); try { setScenes(await api.scenes(id)); } catch (e) { setError(String(e)); } };
  const createProject = async (
    name: string,
    description: string,
    script = "",
    sceneCount = 5
  ) => {
    try {
      const r = await api.createProject(
        name,
        description,
        script,
        sceneCount
      );

      setActivePage("OpenProject");
      await load(r.project.id);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not create project"
      );
    }
  };
  const deleteProject = async (projectId: number) => {
    try {
      await api.deleteProject(projectId);

      const remainingProjects = projects.filter(
        p => p.id !== projectId
      );

      setProjects(remainingProjects);

      if (remainingProjects.length > 0) {
        await load(remainingProjects[0].id);
        setActivePage("OpenProject");
      } else {
        setSelectedProjectId(0);
        setScenes([]);
        setActivePage("Projects");
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not delete project"
      );
    }
  };
  const createScene = async (title: string, description: string) => { if (!selectedProject) return; try { await api.createScene(selectedProject.id, title, description); await load(selectedProject.id); setActivePage("Scenes"); } catch (e) { setError(e instanceof Error ? e.message : "Could not create scene"); } };
  const attachFootage = async (sceneId: number, files: File[]) => {
    console.log("UPLOAD DEBUG", {
      sceneId,
      files: files.map(file => ({
        name: file.name,
        type: file.type,
        size: file.size,
        isFile: file instanceof File,
      })),
    });

    try {
      for (const file of files) await api.upload(sceneId, file);
      await load(selectedProjectId);
      setActivePage("Scenes");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    }
  };
  const processScene = async (sceneId: number) => {
    try { await api.process(sceneId); await load(selectedProjectId); setActivePage("Diagnostics"); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not start processing"); await load(selectedProjectId); }
  };
  const approveScene = async (id: number) => { try { await api.approve(id); await load(selectedProjectId); } catch (e) { setError(String(e)); } };
  const assembleProject = async () => {
    try {
      const result = await api.assemble(selectedProjectId);
      setError("");
      alert(`🎬 Final film assembled!\n${result.output}`);
      await load(selectedProjectId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Final assembly failed");
    }
  };
  const rejectScene = async (id: number) => { try { await api.reject(id); await load(selectedProjectId); setActivePage("Scenes"); } catch (e) { setError(String(e)); } };
  const nav = (page: string) => setActivePage(page);
  const completedScenes = scenes.filter((s) => s.status === "complete").length;
  const reviewScenes = scenes.filter((s) => s.status === "review").length;

  return <div className="app">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">TW</div><span>That's a Wrap!</span></div>
      <nav className="navigation">
        <div className="nav-group"><div className="nav-heading">WORKSPACE</div>{[["Dashboard","⌂"],["Projects","□"],["Scenes","◫"],["Agents","✦"],["Activity","◷"],["Diagnostics","⌁"]].map(([page,icon]) => <button key={page} className={`nav-link ${activePage===page?'active':''}`} onClick={()=>nav(page)}><span className="nav-icon">{icon}</span><span>{page}</span></button>)}</div>
        <div className="nav-group"><div className="nav-heading">PROJECTS</div>{projects.slice(0,4).map((p)=><button key={p.id} className={`nav-link project-link ${selectedProjectId===p.id&&activePage==='OpenProject'?'active':''}`} onClick={()=>void goToProject(p.id)}><span className="project-dot active-dot"></span><span>{p.name}</span></button>)}</div>
        <div className="nav-group"><div className="nav-heading">SYSTEM</div><button className={`nav-link ${activePage==='Settings'?'active':''}`} onClick={()=>nav('Settings')}><span className="nav-icon">⚙</span><span>Settings</span></button></div>
      </nav>
      <div className="sidebar-user"><div className="user-avatar">V</div><div className="user-info"><strong>Filmmaker</strong><span>{backend}</span></div><button className="more-button" onClick={()=>nav("Profile")}>•••</button></div>
    </aside>
    <main className="main">
      {error && <div className="error-banner">{error}<button onClick={()=>setError("")}>×</button></div>}
      {activePage==='Dashboard' && <div className="page dashboard-page"><div className="page-top"><div><p className="eyebrow">WORKSPACE / DASHBOARD</p><h1>Filmmaker Dashboard</h1><p className="page-description">Keep track of your production from first scene to final cut.</p></div><div className="header-actions"><div className="production-status"><span className="status-dot"></span>{backend}</div><button className="profile-button" onClick={()=>nav("Profile")}>Profile</button></div></div><div className="top-action"><button className="dark-button" onClick={()=>selectedProject&&void goToProject(selectedProject.id)}>Open project <span>→</span></button></div><section className="stats"><div className="stat-card"><span className="stat-label">PROJECTS</span><strong>{projects.length}</strong><span className="stat-description">Active workspaces</span></div><div className="stat-card"><span className="stat-label">SCENES</span><strong>{scenes.length}</strong><span className="stat-description">Current project</span></div><div className="stat-card"><span className="stat-label">COMPLETED</span><strong className="green-number">{completedScenes}</strong><span className="stat-description">Scenes finished</span></div><div className="stat-card"><span className="stat-label">NEEDS REVIEW</span><strong>{reviewScenes}</strong><span className="stat-description">Waiting for approval</span></div></section><section className="panel"><div className="panel-header"><div><span className="eyebrow">RECENT ACTIVITY</span><h2>What's happening</h2></div><button className="text-button" onClick={()=>nav("Activity")}>See all →</button></div><div className="activity-list">{activities.slice(0,4).map(a=><div className="activity-item" key={a.id}><div className="activity-avatar">{a.icon}</div><div className="activity-content"><strong>{a.title}</strong><span>{a.description}</span></div><time>{a.time}</time></div>)}</div></section></div>}
      {activePage==='Projects' && <Projects projects={projects} setActivePage={setActivePage} onOpenProject={goToProject} />}
      {activePage==='NewProject' && <NewProject setActivePage={setActivePage} onCreateProject={createProject} />}
      {activePage==='OpenProject' && selectedProject && (
        <OpenProject
          project={selectedProject}
          scenes={selectedScenes}
          setActivePage={setActivePage}
          onRefresh={async()=>{await load(selectedProject.id)}}
          onAssemble={assembleProject}
          onDelete={deleteProject}
        />
      )}
      {activePage==='Scenes' && <Scenes scenes={selectedScenes} setActivePage={setActivePage} onProcess={processScene} />}
      {activePage==='NewScene' && <NewScene setActivePage={setActivePage} onCreateScene={createScene} />}
      {activePage==='UploadFootage' && <UploadFootage scenes={selectedScenes} setActivePage={setActivePage} onUpload={attachFootage} />}
      {activePage==='ReviewScenes' && <ReviewScenes scenes={selectedScenes.filter((s)=>s.status==='review')} setActivePage={setActivePage} onApprove={approveScene} onReject={rejectScene} />}
      {activePage==='Agents' && <Agents />}{activePage==='Activity' && <Activity />}{activePage==='Diagnostics' && <Diagnostics />}{activePage==='Settings' && <Settings />}{activePage==='Profile' && <Profile setActivePage={setActivePage} />}
    </main>
  </div>;
}
export default App;
