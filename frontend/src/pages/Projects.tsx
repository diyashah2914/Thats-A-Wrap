import type { Project } from "../App";

type ProjectsProps = { projects: Project[]; setActivePage: (page: string) => void; onOpenProject: (id: number) => void };

function Projects({ projects, setActivePage, onOpenProject }: ProjectsProps) {
  return <div className="page"><div className="page-top"><div><p className="eyebrow">WORKSPACE</p><h1>Projects</h1><p className="page-description">Manage your film projects and productions.</p></div><button className="primary-button" onClick={() => setActivePage("NewProject")}>+ New Project</button></div><div className="projects-grid">
    {projects.map((project) => { const progress = project.scenes ? Math.round(project.completed / project.scenes * 100) : 0; return <div className="project-card" key={project.id}><div className="project-card-top"><span className="project-status">ACTIVE</span><span>{progress}%</span></div><h2>{project.name}</h2><p>{project.description}</p><div className="project-progress"><div className="project-progress-bar"><div className="project-progress-fill" style={{ width: `${progress}%` }} /></div></div><div className="project-info"><span>{project.scenes} Scenes</span><span>{project.completed} Complete</span></div><button className="secondary-button" onClick={() => onOpenProject(project.id)}>Open Project →</button></div>})}
    <div className="project-card new-project-card"><div className="new-project-icon">+</div><h2>Create a project</h2><p>Start a new film production.</p><button className="secondary-button" onClick={() => setActivePage("NewProject")}>New Project</button></div>
  </div></div>;
}
export default Projects;
