from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from app.workbench.models import ChangeSummary, FormDocument, SessionSnapshot, SessionTurn


class InMemorySessionStore:
    def __init__(self) -> None:
        self._history: dict[str, list[SessionSnapshot]] = {}

    def create(
        self,
        image_path: Path,
        ocr_json_path: Path,
        form_document: FormDocument,
        html: str,
        summary: ChangeSummary,
    ) -> SessionSnapshot:
        session_id = uuid4().hex
        initial_turn = SessionTurn(
            user_message=summary.user_intent,
            form_document=form_document,
            html=html,
            summary=summary,
        )
        snapshot = SessionSnapshot(
            session_id=session_id,
            version=1,
            image_path=image_path,
            ocr_json_path=ocr_json_path,
            current_form_json=form_document,
            current_html=html,
            summary=summary,
            turns=[initial_turn],
        )
        self._history[session_id] = [deepcopy(snapshot)]
        return deepcopy(snapshot)

    def get(self, session_id: str) -> SessionSnapshot:
        history = self._history.get(session_id)
        if history is None or not history:
            raise KeyError(session_id)
        return deepcopy(history[-1])

    def append_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        form_document: FormDocument,
        html: str,
        summary: ChangeSummary,
    ) -> SessionSnapshot:
        history = self._history.get(session_id)
        if history is None:
            raise KeyError(session_id)
        last = history[-1]
        new_turn = SessionTurn(
            user_message=user_message,
            assistant_message=assistant_message,
            form_document=form_document,
            html=html,
            summary=summary,
        )
        snapshot = SessionSnapshot(
            session_id=last.session_id,
            version=last.version + 1,
            image_path=last.image_path,
            ocr_json_path=last.ocr_json_path,
            current_form_json=form_document,
            current_html=html,
            summary=summary,
            turns=[*last.turns, new_turn],
        )
        history.append(deepcopy(snapshot))
        return deepcopy(snapshot)

    def rollback(self, session_id: str) -> SessionSnapshot:
        history = self._history.get(session_id)
        if history is None or not history:
            raise KeyError(session_id)
        if len(history) == 1:
            return deepcopy(history[0])
        history.pop()
        return deepcopy(history[-1])
