"""Action: create_presentation - Generates a styled PowerPoint (.pptx) presentation."""

from datetime import datetime
from typing import Any
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from app.actions.base import BaseAction
from app.models import ActionResponse
from app.security import resolve_safe_path
from app.config import settings
from app.logging_config import get_logger

logger = get_logger("flash.action.create_presentation")


class CreatePresentationAction(BaseAction):
    name = "create_presentation"
    description = "Generates a styled Microsoft PowerPoint presentation (.pptx) with title and content slides."
    requires_confirmation = False
    parameters_schema = {
        "title": {
            "type": "string",
            "required": True,
            "description": "Presentation title.",
        },
        "subtitle": {
            "type": "string",
            "required": False,
            "description": "Subtitle for the title slide.",
        },
        "slides": {
            "type": "array",
            "required": False,
            "description": "List of slide objects with 'title' and 'bullet_points' (list of strings).",
        },
        "filename": {
            "type": "string",
            "required": False,
            "description": "Relative filename ending in .pptx (default: 'documents/presentation_YYYYMMDD_HHMMSS.pptx').",
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        title = str(parameters.get("title") or "Presentation").strip()
        subtitle = parameters.get("subtitle") or "Prepared by Flash"
        slides_data = parameters.get("slides", [])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"documents/presentation_{timestamp}.pptx"
        filename = str(parameters.get("filename") or default_filename).strip()

        if not filename.lower().endswith(".pptx"):
            filename += ".pptx"

        is_safe, resolved_path, error_msg = resolve_safe_path(
            filename,
            must_exist=False,
            create_parent=True,
            allowed_extensions={".pptx"},
        )

        if not is_safe or resolved_path is None:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Access denied: {error_msg}",
                error="PATH_ACCESS_DENIED",
            )

        try:
            prs = Presentation()

            # Slide 1: Title Slide (Layout index 0)
            title_layout = prs.slide_layouts[0]
            slide1 = prs.slides.add_slide(title_layout)
            if slide1.shapes.title:
                slide1.shapes.title.text = title
            if len(slide1.placeholders) > 1:
                slide1.placeholders[1].text = f"{subtitle}\n{datetime.now().strftime('%B %d, %Y')}"

            # If no slides provided, create a default overview slide
            if not slides_data:
                slides_data = [
                    {
                        "title": "Overview",
                        "bullet_points": [
                            f"Key points regarding {title}",
                            "Action items and milestones",
                            "Summary and next steps",
                        ],
                    }
                ]

            bullet_layout = prs.slide_layouts[1]  # Title and Content

            for s_data in slides_data:
                if not isinstance(s_data, dict):
                    continue
                s_title = s_data.get("title", "Slide")
                bullets = s_data.get("bullet_points", s_data.get("bullets", []))

                slide = prs.slides.add_slide(bullet_layout)
                if slide.shapes.title:
                    slide.shapes.title.text = str(s_title)

                body_shape = slide.shapes.placeholders[1]
                tf = body_shape.text_frame

                if isinstance(bullets, list) and bullets:
                    for idx, b in enumerate(bullets):
                        if idx == 0:
                            p = tf.paragraphs[0]
                        else:
                            p = tf.add_paragraph()
                        p.text = str(b)
                        p.level = 0
                elif isinstance(bullets, str) and bullets.strip():
                    tf.paragraphs[0].text = bullets.strip()

            prs.save(str(resolved_path))
            rel_path = str(resolved_path.relative_to(settings.workspace_dir))

            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Successfully created PowerPoint presentation '{rel_path}' with {len(prs.slides)} slides.",
                output_path=str(resolved_path),
                data={"filename": rel_path, "title": title, "slides_count": len(prs.slides)},
            )
        except Exception as e:
            logger.error("Failed to create PowerPoint presentation: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Failed to create PowerPoint presentation: {e}",
                error=str(e),
            )
