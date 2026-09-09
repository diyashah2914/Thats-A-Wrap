from app.agents.gemini_client import GeminiClient
from app.schemas.contracts import AgentDecision, MusicDecision

class SpecialistAgent:
    def __init__(self, agent_id: str, speciality: str):
        self.agent_id, self.speciality = agent_id, speciality

    def run(self, scene_id: str, context: dict) -> AgentDecision:
        if self.speciality == 'Dialogue and sound cleanup':
            recommendations = ['Normalize dialogue loudness', 'Preserve original production audio', 'Duck music beneath dialogue']
            execution = {'audio_filter': 'loudnorm', 'preserve_source_audio': True, 'music_ducking': True}
        elif self.speciality == 'Cinematic colour treatment':
            recommendations = ['Balance exposure', 'Preserve skin-tone consistency', 'Apply restrained cinematic contrast']
            execution = {'grade': 'cinematic_contrast', 'contrast': 1.08, 'saturation': 1.04}
        else:
            recommendations = ['Add restrained clarity', 'Use a subtle vignette', 'Avoid effects that obscure performance']
            execution = {'effects': ['clarity', 'vignette'], 'intensity': 'subtle'}
        return AgentDecision(agent_id=self.agent_id, scene_id=str(scene_id), status='completed',
            summary=f'{self.speciality} agent executed a scene-specific treatment plan.',
            payload={'speciality': self.speciality, 'recommendations': recommendations, 'execution': execution})

class MusicAgent:
    agent_id = 'music-agent'
    def __init__(self, client: GeminiClient): self.client = client

    def choose(self, scene_id: str, context: str) -> MusicDecision:
        text=(context or '').lower()
        if any(x in text for x in ('fight','chase','action','battle','fast','urgent','danger')): track='action_pulse'
        elif any(x in text for x in ('tense','thriller','suspense','mystery','fear','dark')): track='cinematic_tension'
        elif any(x in text for x in ('sad','grief','loss','emotional','romance','love','heartbreak')): track='emotional_piano'
        elif any(x in text for x in ('happy','joy','celebration','hope','victory','uplifting')): track='uplifting'
        elif any(x in text for x in ('night','memory','dream','ethereal','quiet')): track='dark_ambient'
        else: track='minimal_ambient'
        fallback=MusicDecision(track=track, volume=0.16 if 'dialogue' in text else 0.20, reason='Scene-aware music selection with dialogue-safe mixing.')
        prompt=f'''You are the Music Supervisor Agent for a film post-production system. Choose the best original in-app music bed for this scene.
Available tracks: emotional_piano, cinematic_tension, action_pulse, dark_ambient, uplifting, minimal_ambient.
Prefer music that supports the story and never overwhelms dialogue. Return structured JSON only.
Scene ID: {scene_id}
Scene context: {context}'''
        return self.client.structured(prompt, MusicDecision, fallback)

def SoundAgent(): return SpecialistAgent('sound-agent','Dialogue and sound cleanup')
def ColourAgent(): return SpecialistAgent('colour-agent','Cinematic colour treatment')
def VFXAgent(): return SpecialistAgent('vfx-agent','Visual effects planning')
