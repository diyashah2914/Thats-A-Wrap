import re
from app.agents.gemini_client import GeminiClient
from app.schemas.contracts import ScriptBreakdown, SceneBreakdown

class DirectorAgent:
    agent_id = 'director-agent'
    def __init__(self, client: GeminiClient): self.client = client

    def _fallback(self, script: str, scene_count: int) -> ScriptBreakdown:
        cleaned = [p.strip() for p in re.split(r'\n\s*\n|(?=SCENE\s+\d+)', script, flags=re.I) if p.strip()]
        chunks = cleaned[:scene_count] if cleaned else []
        if not chunks:
            chunks = [f'Production scene {i:02d} from the supplied screenplay.' for i in range(1, scene_count + 1)]
        while len(chunks) < scene_count:
            chunks.append(f'Scene {len(chunks)+1:02d}: continuation of the screenplay.')
        scenes = []
        for i, text in enumerate(chunks[:scene_count], 1):
            first = re.sub(r'\s+', ' ', text).strip()
            title = first[:54].rstrip(' .,:;') or f'Scene {i:02d}'
            scenes.append(SceneBreakdown(scene_id=f'scene_{i:02d}', number=i, title=title, description=first[:280], mood='dramatic' if any(w in first.lower() for w in ('fight','argument','fear','dark','danger')) else 'cinematic'))
        return ScriptBreakdown(title='AI Assisted Film', logline=(chunks[0][:180] if chunks else ''), scenes=scenes)

    def analyse(self, script: str, scene_count: int = 10) -> ScriptBreakdown:
        fallback = self._fallback(script, scene_count)
        prompt = f'''You are the Director Agent for a film-production system. Analyse the screenplay below and return exactly {scene_count} scene records. Preserve story order. Give each scene a concise production-ready title and description. Identify location, time of day, characters, mood, visual style, audio requirements and VFX requirements. Do not invent plot events when the screenplay provides enough detail.\n\nSCREENPLAY:\n{script}'''
        return self.client.structured(prompt, ScriptBreakdown, fallback)
