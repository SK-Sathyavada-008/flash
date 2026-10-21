"""Action: create_word_document - Generates a styled Microsoft Word (.docx) document."""

from datetime import datetime
from typing import Any
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from app.actions.base import BaseAction
from app.models import ActionResponse
from app.security import resolve_safe_path
from app.config import settings
from app.logging_config import get_logger

logger = get_logger("flash.action.create_word_document")


class CreateWordDocumentAction(BaseAction):
    name = "create_word_document"
    description = "Generates a styled Microsoft Word document (.docx) with headings, paragraphs, bullet points, and tables."
    requires_confirmation = False
    parameters_schema = {
        "title": {
            "type": "string",
            "required": True,
            "description": "Document title.",
        },
        "content": {
            "type": "string",
            "required": False,
            "description": "Main body text or overview.",
        },
        "sections": {
            "type": "array",
            "required": False,
            "description": "List of sections, each with 'heading', 'paragraphs' (list of str), and optional 'bullet_points' (list of str).",
        },
        "filename": {
            "type": "string",
            "required": False,
            "description": "Relative filename ending in .docx (default: 'documents/doc_YYYYMMDD_HHMMSS.docx').",
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        title = str(parameters.get("title") or "Document").strip()
        body_content = parameters.get("content")
        sections = parameters.get("sections", [])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"documents/doc_{timestamp}.docx"
        filename = str(parameters.get("filename") or default_filename).strip()

        if not filename.lower().endswith(".docx"):
            filename += ".docx"

        is_safe, resolved_path, error_msg = resolve_safe_path(
            filename,
            must_exist=False,
            create_parent=True,
            allowed_extensions={".docx"},
        )

        if not is_safe or resolved_path is None:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Access denied: {error_msg}",
                error="PATH_ACCESS_DENIED",
            )

        try:
            doc = Document()

            # Set normal style font
            style = doc.styles["Normal"]
            font = style.font
            font.name = "Calibri"
            font.size = Pt(11)
            font.color.rgb = RGBColor(0x22, 0x22, 0x22)

            # Title
            title_p = doc.add_heading(title, level=0)
            title_p.alignment = WD_ALIGN_PARAGRAPH.LEFT

            # Subtitle / Date
            sub_p = doc.add_paragraph()
            sub_run = sub_p.add_run(f"Created by Flash on {datetime.now().strftime('%B %d, %Y at %H:%M')}")
            sub_run.font.italic = True
            sub_run.font.size = Pt(9.5)
            sub_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

            doc.add_paragraph()  # spacing

            # Body content if provided
            if body_content and isinstance(body_content, str):
                for p_text in body_content.split("\n\n"):
                    if p_text.strip():
                        doc.add_paragraph(p_text.strip())

            # Paragraphs list if provided
            paragraphs = parameters.get("paragraphs")
            if paragraphs:
                if isinstance(paragraphs, list):
                    for p_text in paragraphs:
                        if str(p_text).strip():
                            doc.add_paragraph(str(p_text).strip())
                elif isinstance(paragraphs, str):
                    for p_text in paragraphs.split("\n"):
                        if p_text.strip():
                            doc.add_paragraph(p_text.strip())

            # Sections
            if isinstance(sections, list):
                for sec in sections:
                    if isinstance(sec, dict):
                        h = sec.get("heading")
                        if h:
                            doc.add_heading(str(h), level=1)

                        paras = sec.get("paragraphs", [])
                        if isinstance(paras, list):
                            for p in paras:
                                doc.add_paragraph(str(p))
                        elif isinstance(paras, str) and paras.strip():
                            doc.add_paragraph(paras.strip())

                        bullets = sec.get("bullet_points", [])
                        if isinstance(bullets, list):
                            for b in bullets:
                                doc.add_paragraph(str(b), style="List Bullet")
                    elif isinstance(sec, str):
                        doc.add_paragraph(sec)

            # Save
            doc.save(str(resolved_path))
            rel_path = str(resolved_path.relative_to(settings.workspace_dir))

            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Successfully created Word document '{rel_path}'.",
                output_path=str(resolved_path),
                data={"filename": rel_path, "title": title, "paragraphs_count": len(doc.paragraphs)},
            )
        except Exception as e:
            logger.error("Failed to create Word document: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Failed to create Word document: {e}",
                error=str(e),
            )
