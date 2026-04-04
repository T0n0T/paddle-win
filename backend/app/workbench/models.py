from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class LayoutHint(BaseModel):
    width: str = "full"
    inline_with: str | None = None
    emphasis: str = "normal"


class FormSection(BaseModel):
    id: str
    title: str


class FormField(BaseModel):
    id: str
    section_id: str
    label: str
    type: str
    required: bool = False
    placeholder: str = ""
    options: list[str] = Field(default_factory=list)
    layout_hint: LayoutHint = Field(default_factory=LayoutHint)


class FormDocument(BaseModel):
    title: str
    description: str = ""
    sections: list[FormSection] = Field(default_factory=list)
    fields: list[FormField] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_field_ids(self) -> "FormDocument":
        ids = [field.id for field in self.fields]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate field id")
        return self


class ChangeSummary(BaseModel):
    user_intent: str
    applied: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    touched_field_ids: list[str] = Field(default_factory=list)


class CreateSessionRequest(BaseModel):
    image_path: Path
    ocr_json_path: Path
    run_id: str | None = None
    source_image_name: str | None = None


class EditMessageRequest(BaseModel):
    message: str


class SessionTurn(BaseModel):
    user_message: str | None = None
    assistant_message: str | None = None
    form_document: FormDocument
    html: str
    summary: ChangeSummary


class SessionSnapshot(BaseModel):
    session_id: str
    version: int
    run_id: str
    source_image_name: str
    image_path: Path
    ocr_json_path: Path
    current_form_json: FormDocument
    current_html: str
    summary: ChangeSummary
    turns: list[SessionTurn]

    @model_validator(mode="after")
    def validate_current_state_matches_latest_turn(self) -> "SessionSnapshot":
        if not self.turns:
            return self
        latest_turn = self.turns[-1]
        if (
            self.current_form_json != latest_turn.form_document
            or self.current_html != latest_turn.html
            or self.summary != latest_turn.summary
        ):
            raise ValueError("current state must match latest turn")
        return self


class SessionSnapshotResponse(BaseModel):
    session_id: str
    version: int
    run_id: str
    source_image_name: str
    current_form_json: FormDocument
    current_html: str
    summary: ChangeSummary
    turns: list[SessionTurn]

    @classmethod
    def from_snapshot(cls, snapshot: SessionSnapshot) -> "SessionSnapshotResponse":
        return cls(
            session_id=snapshot.session_id,
            version=snapshot.version,
            run_id=snapshot.run_id,
            source_image_name=snapshot.source_image_name,
            current_form_json=snapshot.current_form_json,
            current_html=snapshot.current_html,
            summary=snapshot.summary,
            turns=snapshot.turns,
        )
