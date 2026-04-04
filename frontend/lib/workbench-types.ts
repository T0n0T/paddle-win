export type LayoutHint = {
  width: string;
  inline_with: string | null;
  emphasis: string;
};

export type FormSection = {
  id: string;
  title: string;
};

export type FormField = {
  id: string;
  section_id: string;
  label: string;
  type: string;
  required: boolean;
  placeholder: string;
  options: string[];
  layout_hint: LayoutHint;
};

export type FormDocument = {
  title: string;
  description: string;
  sections: FormSection[];
  fields: FormField[];
};

export type ChangeSummary = {
  user_intent: string;
  applied: string[];
  warnings: string[];
  unresolved: string[];
  touched_field_ids: string[];
};

export type SessionTurn = {
  user_message: string | null;
  assistant_message: string | null;
  form_document: FormDocument;
  html: string;
  summary: ChangeSummary;
};

export type SessionSnapshot = {
  session_id: string;
  version: number;
  image_path: string;
  ocr_json_path: string;
  current_form_json: FormDocument;
  current_html: string;
  summary: ChangeSummary;
  turns: SessionTurn[];
};

export type CreateSessionInput = {
  imagePath: string;
  ocrJsonPath: string;
};

export type SendMessageInput = {
  sessionId: string;
  message: string;
};
