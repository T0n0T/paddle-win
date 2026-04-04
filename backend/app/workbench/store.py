from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Protocol
from uuid import uuid4

from app.workbench.models import ChangeSummary, FormDocument, SessionSnapshot, SessionTurn


RUN_ID_PATTERN = re.compile(r"^(?P<timestamp>\d{8}-\d{6})-(?P<sequence>\d{6})$")


class SessionStore(Protocol):
    def create(
        self,
        image_path: Path,
        ocr_json_path: Path,
        form_document: FormDocument,
        html: str,
        summary: ChangeSummary,
        run_id: str | None = None,
        source_image_name: str | None = None,
    ) -> SessionSnapshot: ...

    def get(self, session_id: str) -> SessionSnapshot: ...

    def append_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        form_document: FormDocument,
        html: str,
        summary: ChangeSummary,
    ) -> SessionSnapshot: ...

    def rollback(self, session_id: str) -> SessionSnapshot: ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self._history: dict[str, list[SessionSnapshot]] = {}
        self._run_sequences: dict[str, int] = {}

    def create(
        self,
        image_path: Path,
        ocr_json_path: Path,
        form_document: FormDocument,
        html: str,
        summary: ChangeSummary,
        run_id: str | None = None,
        source_image_name: str | None = None,
    ) -> SessionSnapshot:
        session_id = uuid4().hex
        resolved_run_id = run_id or self._next_run_id()
        initial_turn = SessionTurn(
            user_message=summary.user_intent,
            form_document=form_document,
            html=html,
            summary=summary,
        )
        snapshot = SessionSnapshot(
            session_id=session_id,
            version=1,
            run_id=resolved_run_id,
            source_image_name=source_image_name or image_path.name,
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
            run_id=last.run_id,
            source_image_name=last.source_image_name,
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

    def _next_run_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        next_sequence = self._run_sequences.get(timestamp, 0) + 1
        self._run_sequences[timestamp] = next_sequence
        return f"{timestamp}-{next_sequence:06d}"


class FileSessionStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        image_path: Path,
        ocr_json_path: Path,
        form_document: FormDocument,
        html: str,
        summary: ChangeSummary,
        run_id: str | None = None,
        source_image_name: str | None = None,
    ) -> SessionSnapshot:
        session_id = uuid4().hex
        resolved_run_id = run_id or self._next_run_id()
        initial_turn = SessionTurn(
            user_message=summary.user_intent,
            form_document=form_document,
            html=html,
            summary=summary,
        )
        snapshot = SessionSnapshot(
            session_id=session_id,
            version=1,
            run_id=resolved_run_id,
            source_image_name=source_image_name or image_path.name,
            image_path=image_path,
            ocr_json_path=ocr_json_path,
            current_form_json=form_document,
            current_html=html,
            summary=summary,
            turns=[initial_turn],
        )
        self._write_history(session_id, [snapshot])
        return deepcopy(snapshot)

    def get(self, session_id: str) -> SessionSnapshot:
        history = self._read_history(session_id)
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
        history = self._read_history(session_id)
        last = history[-1]
        snapshot = SessionSnapshot(
            session_id=last.session_id,
            version=last.version + 1,
            run_id=last.run_id,
            source_image_name=last.source_image_name,
            image_path=last.image_path,
            ocr_json_path=last.ocr_json_path,
            current_form_json=form_document,
            current_html=html,
            summary=summary,
            turns=[
                *last.turns,
                SessionTurn(
                    user_message=user_message,
                    assistant_message=assistant_message,
                    form_document=form_document,
                    html=html,
                    summary=summary,
                ),
            ],
        )
        history.append(snapshot)
        self._write_history(session_id, history)
        return deepcopy(snapshot)

    def rollback(self, session_id: str) -> SessionSnapshot:
        history = self._read_history(session_id)
        if len(history) > 1:
            history.pop()
            self._write_history(session_id, history)
        return deepcopy(history[-1])

    def _session_path(self, session_id: str) -> Path:
        return self.root_dir / f"{session_id}.json"

    def _next_run_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        sequences = [
            self._run_id_sequence(snapshot.run_id)
            for snapshot in self._all_latest_snapshots()
            if self._run_id_timestamp(snapshot.run_id) == timestamp
        ]
        next_sequence = max(sequences, default=0) + 1
        return f"{timestamp}-{next_sequence:06d}"

    def _read_history(self, session_id: str) -> list[SessionSnapshot]:
        path = self._session_path(session_id)
        if not path.exists():
            raise KeyError(session_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [SessionSnapshot.model_validate(item) for item in payload["history"]]

    def _write_history(self, session_id: str, history: list[SessionSnapshot]) -> None:
        path = self._session_path(session_id)
        payload = {"history": [snapshot.model_dump(mode="json") for snapshot in history]}
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _all_latest_snapshots(self) -> list[SessionSnapshot]:
        snapshots: list[SessionSnapshot] = []
        for path in self.root_dir.glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            history = payload.get("history", [])
            if not history:
                continue
            snapshots.append(SessionSnapshot.model_validate(history[-1]))
        return snapshots

    def _run_id_timestamp(self, run_id: str) -> str:
        match = RUN_ID_PATTERN.match(run_id)
        if match is None:
            return ""
        return match.group("timestamp")

    def _run_id_sequence(self, run_id: str) -> int:
        match = RUN_ID_PATTERN.match(run_id)
        if match is None:
            return 0
        return int(match.group("sequence"))
