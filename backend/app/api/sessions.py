from fastapi import APIRouter, HTTPException

from app.workbench import (
    CreateSessionRequest,
    EditMessageRequest,
    InvalidPayloadError,
    SessionNotFoundError,
    SessionSnapshot,
    WorkbenchService,
)


def create_sessions_router(service: WorkbenchService) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])

    @router.post("", response_model=SessionSnapshot)
    def create_session(request: CreateSessionRequest) -> SessionSnapshot:
        return _run_session_operation(lambda: service.create_session(request))

    @router.get("/{session_id}", response_model=SessionSnapshot)
    def get_session(session_id: str) -> SessionSnapshot:
        return _run_session_operation(lambda: service.get_session(session_id))

    @router.post("/{session_id}/messages", response_model=SessionSnapshot)
    def send_message(session_id: str, request: EditMessageRequest) -> SessionSnapshot:
        return _run_session_operation(lambda: service.send_message(session_id, request))

    @router.post("/{session_id}/rollback", response_model=SessionSnapshot)
    def rollback(session_id: str) -> SessionSnapshot:
        return _run_session_operation(lambda: service.rollback(session_id))

    return router


def _run_session_operation(operation):
    try:
        return operation()
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    except InvalidPayloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
