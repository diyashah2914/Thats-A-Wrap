import { useState } from "react";
import type { Project, Scene } from "../App";
import { api } from "../api";

type Props={project:Project;scenes:Scene[];setActivePage:(page:string)=>void;onRefresh?:()=>Promise<void>;onAssemble: () => Promise<void>;onDelete: (projectId: number) => Promise<void>;};
function OpenProject({project,scenes,setActivePage,onRefresh,onAssemble,onDelete}:Props){
 const [busy,setBusy]=useState(false); const complete=scenes.filter(s=>s.status==="complete").length; const progress=project.scenes?Math.round(project.completed/project.scenes*100):0;
 const assemble=async()=>{setBusy(true);try{await api.assemble(project.id);await onRefresh?.()}catch(e){alert(e instanceof Error?e.message:"Assembly failed")}finally{setBusy(false)}};
 return <div className="page"><div className="page-top"><div><button
      className="primary-button"
      onClick={() => void onAssemble()}
      disabled={scenes.filter(s => s.status === "complete").length === 0}
    >
      🎬 Assemble Final Film
    </button> 
    <button
  className="secondary-button"
  onClick={async () => {
    const confirmed = window.confirm(
      `Delete "${project.name}"? This will remove the project and all its scenes.`
    );

    if (!confirmed) return;

    await onDelete(project.id);
  }}
>
  🗑 Delete Project
</button>
    <p className="eyebrow">PROJECT / OVERVIEW</p><h1>{project.name}</h1><p className="page-description">{project.description}</p></div><div className="page-actions"><button className="secondary-button" onClick={()=>setActivePage("Scenes")}>View Scenes →</button>{project.final_output&&<button className="primary-button" onClick={()=>window.open(api.mediaUrl(project.final_output!),"_blank")}>Watch Final Film ↗</button>}</div></div>
 <section className="stats"><div className="stat-card"><span className="stat-label">SCENES</span><strong>{project.scenes}</strong><span className="stat-description">Total scenes</span></div><div className="stat-card"><span className="stat-label">COMPLETED</span><strong className="green-number">{project.completed}</strong><span className="stat-description">Approved scenes</span></div><div className="stat-card"><span className="stat-label">PROCESSING</span><strong>{scenes.filter(s=>s.status==="processing").length}</strong><span className="stat-description">Currently working</span></div><div className="stat-card"><span className="stat-label">NEEDS REVIEW</span><strong>{scenes.filter(s=>s.status==="review").length}</strong><span className="stat-description">Waiting for approval</span></div></section>
 <section className="panel"><div className="panel-header"><div><span className="eyebrow">PROJECT PROGRESS</span><h2>Production</h2></div><strong>{progress}%</strong></div><div className="progress-summary"><span>{complete} of {project.scenes} scenes approved</span><span>{Math.max(project.scenes-complete,0)} remaining</span></div><div className="progress-track"><div className="progress-value" style={{width:`${progress}%`}}/></div></section>
 <section className="panel"><div className="panel-header"><div><span className="eyebrow">FINAL CUT</span><h2>Assemble the film</h2></div><span className="scene-status complete">{project.completed} APPROVED</span></div><p className="page-description">Approved scenes are assembled in scene order using the media worker.</p><div className="action-buttons"><button onClick={()=>setActivePage("NewScene")}>＋ New Scene</button><button onClick={()=>setActivePage("UploadFootage")}>↑ Upload Footage</button><button onClick={()=>setActivePage("ReviewScenes")}>✓ Review</button><button className="primary-button" disabled={!project.completed||busy} onClick={()=>void assemble()}>{busy?"Assembling…":"Assemble Final Film →"}</button></div>{project.final_output&&<div className="final-output"><strong>Final film ready.</strong><span>{project.final_output}</span></div>}</section>
 <section className="panel"><div className="panel-header"><div><span className="eyebrow">PRODUCTION</span><h2>Control room</h2></div></div><div className="action-buttons"><button onClick={()=>setActivePage("Agents")}>✦ Agents</button><button onClick={()=>setActivePage("Activity")}>◷ Activity</button></div></section></div>
}
export default OpenProject;
