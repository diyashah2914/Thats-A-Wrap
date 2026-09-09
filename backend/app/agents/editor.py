from pathlib import Path
from app.agents.gemini_client import GeminiClient
from app.schemas.contracts import EditDecision, TakeScore

class EditorAgent:
    agent_id = 'editor-agent'
    def __init__(self, client: GeminiClient): self.client = client

    def select(self, scene_id: str, takes: list[str], scene_context: str = '') -> EditDecision:
        scores=[]
        for i, take in enumerate(takes):
            name=Path(take).stem.lower()
            score=max(62, 94-i*5)
            if any(x in name for x in ('final','best','hero','master')): score=min(99,score+5)
            scores.append(TakeScore(take_id=take, score=score, reason='Best available deterministic take ranking for the local demo.'))
        selected=[scores[0].take_id] if scores else []
        fallback=EditDecision(scene_id=str(scene_id), selected_takes=selected, take_scores=scores, audio_plan=['Preserve dialogue clarity','Normalize final mix'], colour_plan=['Maintain consistent cinematic grade'], notes=['AI editor recommendation generated; human approval remains required.'])
        prompt=f'''You are the Editor Agent. Select the strongest take(s) for {scene_id}. Consider performance, continuity and production usefulness from the provided filenames/context. Return structured JSON only.\nScene context: {scene_context}\nTakes: {takes}'''
        return self.client.structured(prompt, EditDecision, fallback)
