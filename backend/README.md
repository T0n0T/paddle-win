# Backend

## Run locally
```bash
uv run --project backend uvicorn app.main:app --reload
```

## Test
```bash
uv run --project backend pytest backend/tests/test_app_smoke.py -v
```
