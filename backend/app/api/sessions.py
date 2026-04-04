from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.workbench import (
    EditMessageRequest,
    InvalidPayloadError,
    SessionNotFoundError,
    SessionSnapshotResponse,
    WorkbenchService,
)


def create_sessions_router(service: WorkbenchService) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])

    @router.post("", response_model=SessionSnapshotResponse)
    def create_session(image: UploadFile = File(...)) -> SessionSnapshotResponse:
        return _run_session_operation(
            lambda: SessionSnapshotResponse.from_snapshot(
                service.create_session_from_upload(
                    filename=image.filename or "upload.bin",
                    content=_read_validated_image_upload(image),
                )
            )
        )

    @router.get("/{session_id}", response_model=SessionSnapshotResponse)
    def get_session(session_id: str) -> SessionSnapshotResponse:
        return _run_session_operation(
            lambda: SessionSnapshotResponse.from_snapshot(service.get_session(session_id))
        )

    @router.post("/{session_id}/messages", response_model=SessionSnapshotResponse)
    def send_message(session_id: str, request: EditMessageRequest) -> SessionSnapshotResponse:
        return _run_session_operation(
            lambda: SessionSnapshotResponse.from_snapshot(service.send_message(session_id, request))
        )

    @router.post("/{session_id}/rollback", response_model=SessionSnapshotResponse)
    def rollback(session_id: str) -> SessionSnapshotResponse:
        return _run_session_operation(
            lambda: SessionSnapshotResponse.from_snapshot(service.rollback(session_id))
        )

    return router


def _read_validated_image_upload(image: UploadFile) -> bytes:
    filename = image.filename or ""
    content_type = image.content_type or ""
    suffix = Path(filename).suffix.lower()
    allowed_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
    if not (content_type.startswith("image/") or suffix in allowed_suffixes):
        raise HTTPException(status_code=422, detail="uploaded file must be an image")
    content = image.file.read()
    if not content:
        raise HTTPException(status_code=422, detail="uploaded image is empty")
    return content


def _run_session_operation(operation):
    try:
        return operation()
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    except InvalidPayloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        if "OCR" in message or "ocr" in message:
            raise HTTPException(status_code=500, detail="初始化失败：OCR 处理未完成") from exc
        if "llm" in message.lower() or "model response" in message.lower():
            raise HTTPException(status_code=500, detail="初始化失败：首轮表单重建未完成") from exc
        raise
