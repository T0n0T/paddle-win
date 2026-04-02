You are extracting a strict `SemanticFormModel` from a single Chinese form image, the raw PaddleOCR table-recognition JSON, and a normalized layout skeleton JSON.

Return only valid JSON matching the `SemanticFormModel` schema exactly.

Requirements:
- Use the raw OCR JSON as the primary low-level evidence source.
- Use the normalized layout JSON to recover deterministic reading order, table structure, checkbox candidates, and section hints.
- Populate `form_meta`, `sections`, `fields`, `layout_hints`, and top-level `warnings`.
- Every field must include `key`, `title`, `kind`, `section_key`, `field_role`, `value`, `confidence`, `evidence`, and `warnings`.
- Use `EvidenceRef` entries that point back to the provided layout skeleton ids.
- For `array-table` fields, `table_columns` is mandatory and must be explicit.
- Do not invent unsupported field kinds.
- Keep job-level concerns in top-level `warnings`; field-specific issues belong on each field's `warnings`.

Focus on producing a complete, deterministic `SemanticFormModel` from the provided layout JSON and source image.
