import json, subprocess
from pathlib import Path
from app.schemas.contracts import QCResult
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
tracer=trace.get_tracer("thats-a-wrap-backend.qc")
class QCAgent:
    agent_id="qc-agent"
    def inspect(self,job_id:str,output:str)->QCResult:
        with tracer.start_as_current_span("ffprobe_quality_control") as span:
            span.set_attribute("operation.type","media_quality_control"); span.set_attribute("qc.agent",self.agent_id); span.set_attribute("job.id",str(job_id)); span.set_attribute("media.output",str(output))
            p=Path(output); checks={"exists":p.exists(),"readable":False,"has_video":False,"has_audio":False,"audio_video_aligned":False}; duration=None; vd=None; ad=None; difference=None
            if p.exists():
                try:
                    data=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(p)],text=True)); streams=data.get("streams",[]); checks["readable"]=True; checks["has_video"]=any(s.get("codec_type")=="video" for s in streams); checks["has_audio"]=any(s.get("codec_type")=="audio" for s in streams); duration=float(data.get("format",{}).get("duration",0) or 0)
                    for st in streams:
                        if st.get("codec_type")=="video" and vd is None: vd=float(st.get("duration") or duration or 0)
                        if st.get("codec_type")=="audio" and ad is None: ad=float(st.get("duration") or 0)
                    difference=abs((vd or duration or 0)-(ad or 0)) if checks["has_audio"] else 0.0; checks["audio_video_aligned"]=(not checks["has_audio"]) or difference<=0.25
                    span.set_attribute("media.video_duration_seconds",float(vd or 0)); span.set_attribute("media.audio_duration_seconds",float(ad or 0)); span.set_attribute("media.duration_difference_seconds",float(difference))
                except Exception as exc:
                    span.record_exception(exc); span.set_status(Status(StatusCode.ERROR,str(exc))); span.set_attribute("qc.probe_error",type(exc).__name__)
            passed=checks["exists"] and checks["readable"] and checks["has_video"] and checks["audio_video_aligned"]; span.set_attribute("qc.passed",bool(passed)); span.set_attribute("qc.has_audio",bool(checks["has_audio"])); span.set_attribute("qc.audio_video_aligned",bool(checks["audio_video_aligned"])); span.set_attribute("operation.status","success" if passed else "failed")
            if passed: message="QC passed. Final container is readable and audio/video streams are aligned."
            elif checks["has_audio"] and difference is not None: message=f"QC failed: audio/video duration mismatch ({difference:.3f}s)."
            else: message="QC failed: invalid or incomplete media output."
            return QCResult(job_id=job_id,passed=passed,checks=checks,duration_seconds=duration,video_duration_seconds=vd,audio_duration_seconds=ad,duration_difference_seconds=difference,message=message)
