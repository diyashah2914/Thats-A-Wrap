from app.schemas.contracts import Job

class ProductionAgent:
    agent_id='production-agent'
    def diagnose(self, job: Job) -> dict:
        if job.status != 'FAILED': return {'action':'none','reason':'Job is not failed.'}
        error=(job.error or '').lower(); strategy='retry_with_safe_defaults'
        if 'ffmpeg' in error or 'codec' in error or 'audio' in error: strategy='retry_transcode_h264_aac'
        return {'action':'retry' if job.retry_count < 2 else 'escalate','reason':job.error or 'Unknown processing failure.','strategy':strategy,'retry_count':job.retry_count+1}
    def plan_assembly(self, scene_outputs: list[str]) -> dict:
        return {'scene_count':len(scene_outputs),'transition':'crossfade','transition_duration':0.65,
                'audio_policy':'preserve_and_crossfade','video_policy':'normalize_to_1280x720_h264',
                'qc_policy':'require_audio_video_duration_alignment'}
