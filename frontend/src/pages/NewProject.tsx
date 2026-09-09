import { useState } from "react";

type Props={
  setActivePage:(page:string)=>void;
  onCreateProject:(name:string,description:string,script:string,sceneCount:number)=>void
};

function NewProject({ setActivePage, onCreateProject }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [script, setScript] = useState("");
  const [scriptName, setScriptName] = useState("");
  const [sceneCount, setSceneCount] = useState(5);
  const [busy, setBusy] = useState(false);

  const readScript = async (file: File) => {
    setScriptName(file.name);

    if (
      file.type.startsWith("text/") ||
      file.name.endsWith(".txt")
    ) {
      setScript(await file.text());
    } else {
      setScript(`Imported script: ${file.name}`);
    }
  };

  const createProject = async () => {
    setBusy(true);

    try {
      await onCreateProject(
        name,
        description,
        script,
        sceneCount
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page new-project-page">
      <div className="page-top">
        <div>
          <p className="eyebrow">WORKSPACE / PROJECTS</p>
          <h1>New Project</h1>
          <p className="page-description">
            Start a new film production and give the Director Agent your
            script.
          </p>
        </div>
      </div>

      <button
        className="back-button"
        onClick={() => setActivePage("Projects")}
      >
        ← Back to Projects
      </button>

      <section className="new-project-form">
        <div className="form-header">
          <p className="eyebrow">PROJECT DETAILS</p>
          <h2>Create your production</h2>
          <p>
            Choose how many scenes you want to start with. You can add
            more scenes later.
          </p>
        </div>

        <div className="form-fields">

          <div className="form-group">
            <label htmlFor="project-name">Project name</label>

            <input
              id="project-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. The Last Light"
            />
          </div>

          <div className="form-group">
            <label htmlFor="project-description">
              Description
            </label>

            <textarea
              id="project-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe your film..."
              rows={5}
            />
          </div>

          <div className="form-group">
            <label htmlFor="scene-count">
              Starting number of scenes
            </label>

            <div className="scene-count-control">
              <button
                type="button"
                className="scene-count-button"
                onClick={() =>
                  setSceneCount((count) => Math.max(1, count - 1))
                }
                disabled={sceneCount <= 1}
              >
                −
              </button>

              <input
                id="scene-count"
                type="number"
                min={1}
                max={50}
                value={sceneCount}
                onChange={(e) => {
                  const value = Number(e.target.value);

                  if (!Number.isFinite(value)) return;

                  setSceneCount(
                    Math.min(50, Math.max(1, value))
                  );
                }}
              />

              <button
                type="button"
                className="scene-count-button"
                onClick={() =>
                  setSceneCount((count) => Math.min(50, count + 1))
                }
                disabled={sceneCount >= 50}
              >
                +
              </button>
            </div>

            <p className="form-hint">
              You can add more scenes after creating the project.
            </p>
          </div>

          <div className="form-group">
            <label className="script-upload">
              <input
                type="file"
                accept=".txt,.md,.pdf,.doc,.docx"
                onChange={(e) => {
                  const f = e.target.files?.[0];

                  if (f) void readScript(f);
                }}
              />

              <div className="upload-content">
                <span className="upload-icon">↑</span>

                <div>
                  <strong>
                    {scriptName || "Import your script"}
                  </strong>

                  <p>
                    TXT is read directly; other formats are registered
                    for the project.
                  </p>
                </div>
              </div>
            </label>
          </div>
        </div>

        <div className="form-actions">
          <button
            className="secondary-button"
            onClick={() => setActivePage("Projects")}
          >
            Cancel
          </button>

          <button
            className="primary-button"
            disabled={!name.trim() || busy}
            onClick={() => void createProject()}
          >
            {busy ? "Creating…" : "Create Project →"}
          </button>
        </div>
      </section>
    </div>
  );
}

export default NewProject;