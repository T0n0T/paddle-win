# Backend

## Run locally
```bash
uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011
```

## Test
```bash
uv run --project backend pytest backend/tests/test_app_smoke.py -v
```
