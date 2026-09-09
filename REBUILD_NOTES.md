# That's a Wrap! — responsive AI Scene Post-Production rebuild

This build keeps the existing frontend design and VS Code Grafana MCP configuration, while improving the backend Process Scene pipeline.

## Process Scene

Clicking **Process Scene** now starts an asynchronous job immediately. The browser is no longer blocked while AI/media work runs.

Pipeline:

1. Media validation with ffprobe
2. AI/editor take selection
3. Specialist planning:
   - dialogue/audio
   - music
   - cinematic color
   - VFX
4. AI-directed post-production plan
5. Real FFmpeg treatment:
   - cinematic color/contrast
   - aspect-ratio-safe 1280x720 delivery
   - subtle vignette
   - clarity/sharpening
   - cinematic fade in/out
   - loudness normalization when audio exists
6. QC validation
7. Scene moves to Review

The scene stores the post-production plan so the UI/backend can show what the AI directed.

## Responsiveness

`POST /scenes/{scene_id}/process` returns `202` quickly with a job ID. The frontend polls `/jobs/{job_id}` while showing **Processing Scene…**. Duplicate processing requests for the same scene are prevented.

## Grafana Cloud OTLP

The backend now explicitly passes `OTEL_EXPORTER_OTLP_HEADERS` to the HTTP OTLP exporter. The existing Windows environment variables are still used; no Grafana credentials are stored in this ZIP.

Grafana Cloud's current direct OTLP format is:

`Authorization=Basic <base64(instance_id:token)>`

If your existing environment variable was copied directly from Grafana Cloud, the backend also accepts URL-encoded values such as `Authorization=Basic%20...`.

## Grafana MCP

The existing `.vscode/mcp.json` is preserved. You do **not** need to reconnect MCP just because you replace the project folder, as long as you keep the same VS Code workspace configuration and continue running the local Grafana MCP server on port 8001.

## Run

Backend:

`cd backend`
`python -m uvicorn app.main:app --reload`

Frontend:

`cd frontend`
`npm install`
`npm run dev`

Do not put Grafana tokens in source files.

## AI Scene Music
Process Scene now includes an AI Music Supervisor. It chooses one of six original in-app music beds based on scene context/mood, then FFmpeg loops, fades, ducks, and mixes the selected bed under the scene audio. The selected music track and mix settings are stored in `scene.postProduction.music` for review.

The bundled tracks are original deterministic demo beds in `backend/media/music/`; no external music service or credential is required.
