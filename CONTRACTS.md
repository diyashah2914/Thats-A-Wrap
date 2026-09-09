# Shared Contracts — That's a Wrap!

These names are the shared contract between frontend, backend, agents, and media workers.

## IDs

- `project_id`
- `scene_id`
- `job_id`
- `agent_id`
- `take_id`
- `asset_id`

## Job status

`PENDING` → `PROCESSING` → `COMPLETED`

Failure path:

`PROCESSING` → `FAILED` → `RETRYING` → `PROCESSING`

## Scene status

- `draft`
- `processing`
- `review`
- `complete`
- `failed`

## Job payload

```json
{
  "job_id": "job_1234",
  "scene_id": "scene_03",
  "status": "COMPLETED",
  "input_files": ["..."],
  "output": "...",
  "error": null,
  "retry_count": 0
}
```

## Agent decision

```json
{
  "agent_id": "editor-agent",
  "scene_id": "scene_03",
  "status": "completed",
  "summary": "Best take selected.",
  "payload": {}
}
```

## Rule

If a contract changes, update `backend/app/schemas/contracts.py` first and then update all consumers.
