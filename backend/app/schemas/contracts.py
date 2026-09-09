from typing import Literal
from pydantic import BaseModel, Field

JobStatus = Literal['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'RETRYING']
JobStage = Literal['QUEUED','AI_ANALYSIS','DIRECTOR','EDITOR','SOUND','MUSIC','COLOUR','VFX','POST_PRODUCTION','RENDERING','QC','GOOGLE_CLOUD_UPLOAD','REVIEW','FINAL_ASSEMBLY','COMPLETED','FAILED']
SceneStatus = Literal['draft', 'processing', 'review', 'complete', 'failed']

class SceneBreakdown(BaseModel):
    scene_id: str
    number: int
    title: str
    description: str
    location: str = 'Unknown'
    time_of_day: str = 'Unknown'
    characters: list[str] = Field(default_factory=list)
    mood: str = 'neutral'
    visual_style: str = 'cinematic'
    audio_requirements: list[str] = Field(default_factory=list)
    vfx_requirements: list[str] = Field(default_factory=list)

class ScriptBreakdown(BaseModel):
    title: str = 'Untitled Film'
    logline: str = ''
    scenes: list[SceneBreakdown]

class TakeScore(BaseModel):
    take_id: str
    score: float = Field(ge=0, le=100)
    reason: str
    issues: list[str] = Field(default_factory=list)

class EditDecision(BaseModel):
    scene_id: str
    selected_takes: list[str]
    cuts: list[dict] = Field(default_factory=list)
    transitions: list[str] = Field(default_factory=list)
    audio_plan: list[str] = Field(default_factory=list)
    colour_plan: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    take_scores: list[TakeScore] = Field(default_factory=list)

class ProcessingOperation(BaseModel):
    operation: Literal['trim', 'concat', 'extract_audio', 'replace_audio', 'mix_audio', 'normalize_audio', 'encode', 'colour']
    params: dict = Field(default_factory=dict)

class MediaProcessingPlan(BaseModel):
    scene_id: str
    input_files: list[str]
    operations: list[ProcessingOperation]
    output_filename: str

class MusicDecision(BaseModel):
    enabled: bool = True
    track: Literal['emotional_piano','cinematic_tension','action_pulse','dark_ambient','uplifting','minimal_ambient'] = 'minimal_ambient'
    volume: float = Field(default=0.18, ge=0.0, le=0.6)
    fade_in_seconds: float = Field(default=1.2, ge=0.0, le=10.0)
    fade_out_seconds: float = Field(default=1.5, ge=0.0, le=10.0)
    reason: str = 'Support the scene without overpowering dialogue.'


class AgentDecision(BaseModel):
    agent_id: str
    scene_id: str | None = None
    status: Literal['completed', 'needs_review', 'failed']
    summary: str
    payload: dict = Field(default_factory=dict)

class Job(BaseModel):
    job_id: str
    scene_id: str
    status: JobStatus
    stage: JobStage = 'QUEUED'
    progress: float | None = None
    message: str = 'Queued for processing.'
    updated_at: str | None = None
    error_code: str | None = None
    input_files: list[str] = Field(default_factory=list)
    output: str | None = None
    error: str | None = None
    retry_count: int = 0
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    decision: EditDecision | None = None
    specialist_decisions: list[AgentDecision] = Field(default_factory=list)
    qc: dict | None = None
    post_production_plan: dict = Field(default_factory=dict)

class QCResult(BaseModel):
    job_id: str
    passed: bool
    checks: dict[str, bool]
    duration_seconds: float | None = None
    video_duration_seconds: float | None = None
    audio_duration_seconds: float | None = None
    duration_difference_seconds: float | None = None
    message: str

class ProjectRequest(BaseModel):
    name: str
    description: str = ''
    script: str = ''
    scene_count: int = 5

class SceneRequest(BaseModel):
    title: str
    description: str = ''

class EditorRequest(BaseModel):
    scene_id: int

class FinalAssemblyRequest(BaseModel):
    project_id: int
