import uuid
import json
from pathlib import Path
from datetime import datetime, timezone
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from app.agents.gemini_client import GeminiClient
from app.agents.director import DirectorAgent
from app.agents.editor import EditorAgent
from app.agents.specialists import SoundAgent, MusicAgent, ColourAgent, VFXAgent
from app.agents.qc import QCAgent
from app.agents.production import ProductionAgent
from app.media.ffmpeg_engine import FFmpegEngine
from app.media.opencv_tools import OpenCVTools
from app.schemas.contracts import Job

tracer=trace.get_tracer("thats-a-wrap-backend.workflow")

def iso(): return datetime.now(timezone.utc).isoformat()

class Workflow:
    def __init__(self, media_root: str, state_path: str | None = None, store=None):
        client=GeminiClient()
        self.mode=client.mode
        self.director=DirectorAgent(client)
        self.editor=EditorAgent(client)
        self.sound=SoundAgent()
        self.music=MusicAgent(client)
        self.colour=ColourAgent()
        self.vfx=VFXAgent()
        self.qc=QCAgent()
        self.production=ProductionAgent()
        self.media=FFmpegEngine(media_root)
        self.cv=OpenCVTools()
        self.store = store
        self.state_path = Path(state_path) if state_path else Path(media_root) / "state.json"
        self.jobs={}
        self.agent_runs=[]
        self._load_jobs()
        self.reconcile_interrupted_jobs()

    def _load_jobs(self):
        """Load persisted jobs so UI state and backend state survive reloads."""
        try:
            data = self.store.read() if self.store else json.loads(self.state_path.read_text(encoding="utf-8"))
            for job_id, payload in (data.get("jobs") or {}).items():
                try:
                    self.jobs[job_id] = Job.model_validate(payload)
                except Exception:
                    # Ignore malformed historical jobs rather than preventing startup.
                    continue
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return

    def _persist_job(self, job: Job):
        """Persist one job atomically, sharing the app Store lock when available."""
        try:
            if self.store:
                data = self.store.read()
                data.setdefault("jobs", {})
                data["jobs"][job.job_id] = job.model_dump()
                self.store.write(data)
                return
            try:
                data = self.store.read() if self.store else json.loads(self.state_path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                data = {"projects": {}, "scenes": {}, "activities": [], "jobs": {}}
            data.setdefault("jobs", {})
            data["jobs"][job.job_id] = job.model_dump()
            tmp = self.state_path.with_suffix(".jobs.tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.state_path)
        except OSError:
            pass

    def _persist_all_jobs(self):
        for job in self.jobs.values():
            self._persist_job(job)

    def reconcile_interrupted_jobs(self):
        """Convert orphaned in-memory work into explicit failures after a backend restart.

        BackgroundTasks cannot survive a process restart. Marking these jobs FAILED is safer
        than leaving scenes permanently PROCESSING or pretending the render is still running.
        The user can then retry from the Error Center.
        """
        interrupted = []
        for job in self.jobs.values():
            if job.status in {"PENDING", "PROCESSING", "RETRYING"}:
                job.status = "FAILED"
                job.error = "Processing was interrupted because the backend restarted. Retry the job."
                job.completed_at = iso()
                interrupted.append(job)
                self._persist_job(job)

        if interrupted:
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                scenes = data.get("scenes", {})
                for job in interrupted:
                    scene = scenes.get(str(job.scene_id))
                    if scene:
                        scene["status"] = "failed"
                        scene["error"] = job.error
                if self.store:
                    self.store.write(data)
                else:
                    tmp = self.state_path.with_suffix(".reconcile.tmp")
                    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                    tmp.replace(self.state_path)
            except (OSError, json.JSONDecodeError):
                pass

    def _set_stage(self, job: Job, stage: str, progress: float | None, message: str):
        job.stage=stage; job.progress=progress; job.message=message; job.updated_at=iso(); self._persist_job(job)
        if self.store:
            self.store.add_diagnostic_event({"timestamp":job.updated_at,"level":"INFO","source":"workflow","title":stage.replace("_"," ").title(),"message":message,"details":{"stage":stage,"progress":progress},"trace_id":None,"job_id":job.job_id,"scene_id":int(job.scene_id) if str(job.scene_id).isdigit() else None})

    def create_job(self, scene_id, input_files):
        # One active job per scene prevents accidental double-click processing.
        for existing in self.jobs.values():
            if existing.scene_id == str(scene_id) and existing.status in {"PENDING","PROCESSING","RETRYING"}:
                return existing
        job=Job(
            job_id=f'job_{uuid.uuid4().hex[:8]}',
            scene_id=str(scene_id),
            status='PENDING', stage='QUEUED', progress=0, message='Job created and waiting for a worker.', updated_at=iso(),
            input_files=list(input_files),
            created_at=iso(),
        )
        self.jobs[job.job_id]=job
        self._persist_job(job)
        return job

    def _validate_inputs(self, files):
        if not files:
            raise ValueError("No input footage supplied.")
        for path in files:
            try:
                data=self.media.probe(path)
            except Exception as exc:
                raise ValueError(f"Footage could not be decoded: {path}") from exc
            streams=data.get("streams",[])
            if not any(s.get("codec_type")=="video" for s in streams):
                raise ValueError(f"Footage has no readable video stream: {path}")

    def _post_plan(self, scene_context, decision, specialist_decisions, music_decision):
        text=(scene_context or '').lower()
        specialist_map={d.agent_id:d.payload for d in specialist_decisions}
        colour_exec=(specialist_map.get('colour-agent') or {}).get('execution') or {}
        vfx_exec=(specialist_map.get('vfx-agent') or {}).get('execution') or {}
        sound_exec=(specialist_map.get('sound-agent') or {}).get('execution') or {}
        if any(x in text for x in ('night','dark','thriller','mystery','tense')): grade='dramatic cool cinematic'
        elif any(x in text for x in ('sunset','romance','warm','love','happy','golden')): grade='warm cinematic'
        else: grade='cinematic contrast'
        vfx=list(vfx_exec.get('effects') or ['clarity','vignette'])
        if any(x in text for x in ('dream','memory','flashback','ethereal')): vfx.append('soft glow')
        if any(x in text for x in ('action','chase','fight','fast')): vfx.append('motion emphasis')
        cinematography=['stable cinematic framing']
        if any(x in text for x in ('close-up','close up','intimate','emotion','face')): cinematography=['subject emphasis','gentle cinematic crop']
        elif any(x in text for x in ('wide','landscape','establishing')): cinematography=['wide establishing composition']
        return {'edit':{'selected_take':decision.selected_takes[0] if decision.selected_takes else None,
                        'selected_take_count':len(decision.selected_takes),'pacing':'scene-aware pacing',
                        'continuity':'preserve visual continuity','editor_action':'Selected strongest available take and prepared continuity-safe edit.'},
                'cinematography':cinematography,'color_grade':grade,'vfx':vfx,
                'transitions':['fade in/out'],'transition':'fade in/out',
                'audio':['dialogue clarity','loudness normalization','protect emotional beats'],
                'sound_execution':sound_exec,'specialist_actions':specialist_map,
                'music':music_decision.model_dump(),
                'ai_direction':{'scene_context':scene_context,'intent':'Apply coordinated agent decisions while preserving the original performance.',
                                'specialists_completed':[d.agent_id for d in specialist_decisions]}}

    def _span(self, name, **attrs):
        span = tracer.start_as_current_span(name)
        return span

    def _mark_ok(self, span, **attrs):
        for key, value in attrs.items():
            if value is not None:
                span.set_attribute(key, value)
        span.set_attribute("operation.status", "success")

    def _mark_error(self, span, exc):
        span.record_exception(exc)
        span.set_status(Status(StatusCode.ERROR, str(exc)))
        span.set_attribute("operation.status", "failed")
        span.set_attribute("error.type", type(exc).__name__)

    def run_job(self, job_id, scene_context=''):
        job=self.jobs[job_id]
        job.status='PROCESSING'
        job.started_at=iso()
        self._set_stage(job,'AI_ANALYSIS',5,'Production workflow started; validating footage and preparing AI decisions.')

        with tracer.start_as_current_span("scene_post_production_pipeline") as root_span:
            root_span.set_attribute("operation.type", "ai_scene_post_production")
            root_span.set_attribute("scene.id", str(job.scene_id))
            root_span.set_attribute("job.id", str(job.job_id))
            root_span.set_attribute("media.input_count", len(job.input_files))
            root_span.set_attribute("ai.mode", self.mode)

            try:
                self._set_stage(job,'AI_ANALYSIS',10,'Validating source footage.')
                with tracer.start_as_current_span("media_validation") as span:
                    span.set_attribute("operation.type", "media_validation")
                    span.set_attribute("media.input_count", len(job.input_files))
                    try:
                        self._validate_inputs(job.input_files)
                        self._mark_ok(span, **{"media.validation":"passed"})
                    except Exception as exc:
                        self._mark_error(span, exc)
                        raise

                self._set_stage(job,'EDITOR',25,'Editor agent selecting the strongest available take.')
                with tracer.start_as_current_span("ai_editor_take_selection") as span:
                    span.set_attribute("operation.type", "ai_take_selection")
                    span.set_attribute("agent.id", self.editor.agent_id)
                    span.set_attribute("scene.id", str(job.scene_id))
                    span.set_attribute("ai.mode", self.mode)
                    try:
                        job.decision=self.editor.select(job.scene_id, job.input_files, scene_context)
                        span.set_attribute("editor.selected_take_count", len(job.decision.selected_takes))
                        span.set_attribute("editor.input_take_count", len(job.input_files))
                        self._mark_ok(span, **{"editor.selected_take_count": len(job.decision.selected_takes)})
                    except Exception as exc:
                        self._mark_error(span, exc)
                        raise

                self._set_stage(job,'DIRECTOR',35,'Director and specialist agents planning the scene.')
                with tracer.start_as_current_span("ai_specialist_planning") as span:
                    span.set_attribute("operation.type", "ai_specialist_planning")
                    span.set_attribute("scene.id", str(job.scene_id))
                    span.set_attribute("specialist.count", 4)
                    span.set_attribute("ai.mode", self.mode)
                    try:
                        self._set_stage(job,'MUSIC',45,'Music agent selecting the scene music direction.')
                        with tracer.start_as_current_span("ai_music_supervision") as music_span:
                            music_span.set_attribute("operation.type", "ai_music_selection")
                            music_span.set_attribute("agent.id", self.music.agent_id)
                            music_span.set_attribute("ai.mode", self.mode)
                            music_decision = self.music.choose(job.scene_id, scene_context)
                            music_span.set_attribute("music.track", music_decision.track)
                            music_span.set_attribute("music.enabled", bool(music_decision.enabled))
                            music_span.set_attribute("operation.status", "success")

                        specialist_runs=[]
                        self._set_stage(job,'SOUND',52,'Sound, colour and VFX specialists executing their decisions.')
                        for agent, label in ((self.sound, "sound"), (self.colour, "color"), (self.vfx, "vfx")):
                            with tracer.start_as_current_span(f"ai_{label}_specialist") as agent_span:
                                agent_span.set_attribute("operation.type", f"ai_{label}_specialist")
                                agent_span.set_attribute("agent.id", agent.agent_id)
                                agent_span.set_attribute("scene.id", str(job.scene_id))
                                try:
                                    result = agent.run(job.scene_id, {"scene_context":scene_context})
                                    agent_span.set_attribute("agent.status", result.status)
                                    agent_span.set_attribute("operation.status", "success")
                                    specialist_runs.append(result)
                                except Exception as exc:
                                    self._mark_error(agent_span, exc)
                                    raise
                        job.specialist_decisions=specialist_runs
                        self.agent_runs.extend([
                            job.decision.model_dump(),
                            music_decision.model_dump(),
                            *[a.model_dump() for a in job.specialist_decisions]
                        ])
                        span.set_attribute("music.track", music_decision.track)
                        span.set_attribute("music.enabled", bool(music_decision.enabled))
                        span.set_attribute("specialist.completed_count", len(job.specialist_decisions))
                        self._mark_ok(span, **{"specialist.completed_count": len(job.specialist_decisions)})
                    except Exception as exc:
                        self._mark_error(span, exc)
                        raise

                self._set_stage(job,'POST_PRODUCTION',65,'Combining agent decisions into the render plan.')
                with tracer.start_as_current_span("ai_post_production_direction") as span:
                    span.set_attribute("operation.type", "ai_post_production_direction")
                    span.set_attribute("scene.id", str(job.scene_id))
                    span.set_attribute("ai.mode", self.mode)
                    try:
                        job.post_production_plan=self._post_plan(scene_context, job.decision, job.specialist_decisions, music_decision)
                        job.post_production_plan["music"]["source"] = "AI Music Agent selected in-app original music bed"
                        span.set_attribute("plan.color_grade", str(job.post_production_plan.get("color_grade", "")))
                        span.set_attribute("plan.vfx_count", len(job.post_production_plan.get("vfx", [])))
                        span.set_attribute("plan.cinematography_count", len(job.post_production_plan.get("cinematography", [])))
                        span.set_attribute("plan.transition", str(job.post_production_plan.get("transition", "cut")))
                        self._mark_ok(span)
                    except Exception as exc:
                        self._mark_error(span, exc)
                        raise

                selected=job.decision.selected_takes or [job.input_files[0]]
                source=selected[0]
                root_span.set_attribute("editor.selected_source", str(source))

                with tracer.start_as_current_span("ai_vfx_direction") as span:
                    span.set_attribute("operation.type", "ai_vfx_direction")
                    span.set_attribute("vfx.count", len(job.post_production_plan.get("vfx", [])))
                    span.set_attribute("vfx.effects", ",".join(str(x) for x in job.post_production_plan.get("vfx", [])))
                    self._mark_ok(span)

                with tracer.start_as_current_span("ai_cinematography_direction") as span:
                    span.set_attribute("operation.type", "ai_cinematography_direction")
                    span.set_attribute("cinematography.effects", ",".join(str(x) for x in job.post_production_plan.get("cinematography", [])))
                    self._mark_ok(span)

                with tracer.start_as_current_span("ai_color_direction") as span:
                    span.set_attribute("operation.type", "ai_color_direction")
                    span.set_attribute("color.grade", str(job.post_production_plan.get("color_grade", "cinematic")))
                    self._mark_ok(span)

                with tracer.start_as_current_span("ai_audio_music_direction") as span:
                    music = job.post_production_plan.get("music", {})
                    span.set_attribute("operation.type", "ai_audio_music_direction")
                    span.set_attribute("music.enabled", bool(music.get("enabled", True)))
                    span.set_attribute("music.track", music.get("track", "minimal_ambient"))
                    span.set_attribute("music.volume", float(music.get("volume", 0.18)))
                    self._mark_ok(span)

                self._set_stage(job,'RENDERING',75,'FFmpeg rendering the processed scene.')
                with tracer.start_as_current_span("ffmpeg_scene_render") as span:
                    span.set_attribute("operation.type", "ffmpeg_cinematic_render")
                    span.set_attribute("media.source", str(source))
                    span.set_attribute("media.output_name", f"{job.scene_id}_final.mp4")
                    span.set_attribute("media.engine", "ffmpeg")
                    try:
                        output=self.media.cinematic_process(
                            source,
                            f'{job.scene_id}_final.mp4',
                            job.post_production_plan,
                        )
                        span.set_attribute("media.output", str(output))
                        self._mark_ok(span)
                    except Exception as exc:
                        self._mark_error(span, exc)
                        raise

                self._set_stage(job,'QC',90,'Validating the final media container and audio/video alignment.')
                with tracer.start_as_current_span("scene_qc") as span:
                    span.set_attribute("operation.type", "media_quality_control")
                    span.set_attribute("qc.agent", self.qc.agent_id)
                    try:
                        qc=self.qc.inspect(job.job_id, output)
                        span.set_attribute("qc.passed", bool(qc.passed))
                        if qc.duration_seconds is not None:
                            span.set_attribute("media.duration_seconds", float(qc.duration_seconds))
                        span.set_attribute("qc.has_video", bool(qc.checks.get("has_video", False)))
                        span.set_attribute("qc.has_audio", bool(qc.checks.get("has_audio", False)))
                        if qc.passed:
                            self._mark_ok(span)
                        else:
                            span.set_status(Status(StatusCode.ERROR, qc.message))
                            span.set_attribute("operation.status", "failed")
                            span.set_attribute("error.type", "QCFailure")
                    except Exception as exc:
                        self._mark_error(span, exc)
                        raise

                job.output=output
                job.qc=qc.model_dump()
                job.progress=100 if qc.passed else 90
                job.stage='COMPLETED' if qc.passed else 'FAILED'
                job.message='Scene passed media QC and is ready for cloud upload/review.' if qc.passed else qc.message
                job.updated_at=iso()
                job.error_code=None if qc.passed else 'QC_FAILED'
                job.status='COMPLETED' if qc.passed else 'FAILED'
                job.error=None if qc.passed else qc.message
                job.completed_at=iso()
                self._persist_job(job)
                root_span.set_attribute("job.status", job.status)
                root_span.set_attribute("qc.passed", bool(qc.passed))
                if qc.passed:
                    root_span.set_attribute("operation.status", "success")
                else:
                    root_span.set_status(Status(StatusCode.ERROR, qc.message))
                    root_span.set_attribute("operation.status", "failed")
                return job

            except Exception as exc:
                job.status='FAILED'
                job.stage='FAILED'
                job.progress=None
                job.error=str(exc)
                job.error_code=type(exc).__name__.upper()
                job.message='Processing failed. Inspect the error and retry if the failure is recoverable.'
                job.updated_at=iso()
                job.completed_at=iso()
                self._persist_job(job)
                root_span.set_attribute("job.status", "FAILED")
                self._mark_error(root_span, exc)
                return job

    def assemble(self, inputs, output_name='final_film.mp4'):
        plan=self.production.plan_assembly(list(inputs))
        with tracer.start_as_current_span('production_agent_assembly_plan') as span:
            span.set_attribute('operation.type','production_assembly_direction')
            span.set_attribute('agent.id',self.production.agent_id)
            span.set_attribute('assembly.scene_count',len(inputs))
            span.set_attribute('assembly.transition',plan['transition'])
            span.set_attribute('assembly.audio_policy',plan['audio_policy'])
            span.set_attribute('operation.status','success')
        return self.media.concat(inputs, output_name, plan=plan)
