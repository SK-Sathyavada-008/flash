"""Action 5: create_spreadsheet - generates a styled real .xlsx Excel file with openpyxl."""

from datetime import datetime
from typing import Any
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.actions.base import BaseAction
from app.models import ActionResponse
from app.security import resolve_safe_path
from app.logging_config import get_logger

logger = get_logger("flash.action.create_spreadsheet")


class CreateSpreadsheetAction(BaseAction):
    name = "create_spreadsheet"
    description = "Generates a real Microsoft Excel workbook (.xlsx) with styled headers, data rows, and auto-sized columns."
    requires_confirmation = False
    parameters_schema = {
        "headers": {
            "type": "array",
            "required": True,
            "description": "List of column header names (e.g., ['Item', 'Category', 'Price', 'Qty']).",
        },
        "rows": {
            "type": "array",
            "required": False,
            "description": "2D list of row values matching the columns.",
            "default": [],
        },
        "sheet_name": {
            "type": "string",
            "required": False,
            "description": "Tab/sheet name within Excel (default: 'Sheet1').",
            "default": "Data",
        },
        "filename": {
            "type": "string",
            "required": False,
            "description": "Relative path ending in .xlsx (default: 'spreadsheets/sheet_YYYYMMDD_HHMM.xlsx').",
        },
        "include_total_row": {
            "type": "boolean",
            "required": False,
            "description": "If True and numerical columns exist, adds an Excel SUM() formula row at bottom.",
            "default": False,
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        headers = parameters.get("headers")
        if isinstance(headers, str):
            headers = [h.strip() for h in headers.split(",") if h.strip()]
        if not headers or not isinstance(headers, list) or len(headers) == 0:
            headers = ["Item", "Description", "Quantity", "Amount"]

        rows = parameters.get("rows", [])
        if not isinstance(rows, list):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'rows' must be a list of lists.",
                error="INVALID_PARAMETER",
            )

        sheet_name = str(parameters.get("sheet_name") or "Flash Sheet")[:31]  # Excel 31 char limit
        include_total = bool(parameters.get("include_total_row", False))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"spreadsheets/sheet_{timestamp}.xlsx"
        filename = str(parameters.get("filename") or default_filename).strip()

        if not filename.lower().endswith(".xlsx"):
            filename += ".xlsx"

        is_safe, resolved_path, error_msg = resolve_safe_path(
            filename,
            must_exist=False,
            create_parent=True,
            allowed_extensions={".xlsx"},
        )

        if not is_safe or resolved_path is None:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Access denied: {error_msg}",
                error="PATH_ACCESS_DENIED",
            )

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = sheet_name

            # Styling definitions: Flash signature forest green & gold
            header_fill = PatternFill(start_color="2D5A27", end_color="2D5A27", fill_type="solid")
            header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
            data_font = Font(name="Segoe UI", size=10, color="1F1916")
            thin_border = Border(
                left=Side(style="thin", color="E0E0E0"),
                right=Side(style="thin", color="E0E0E0"),
                top=Side(style="thin", color="E0E0E0"),
                bottom=Side(style="thin", color="E0E0E0"),
            )

            # Write header row (Row 1)
            ws.append([str(h) for h in headers])
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            # Write data rows
            current_row = 2
            for row_data in rows:
                if isinstance(row_data, (list, tuple)):
                    ws.append(list(row_data))
                else:
                    ws.append([row_data])

                for col_idx in range(1, len(headers) + 1):
                    cell = ws.cell(row=current_row, column=col_idx)
                    cell.font = data_font
                    cell.border = thin_border
                current_row += 1

            # Optional total row
            if include_total and len(rows) > 0:
                total_row_idx = current_row
                total_font = Font(name="Segoe UI", size=10, bold=True, color="1F1916")
                total_fill = PatternFill(start_color="F0F7EF", end_color="F0F7EF", fill_type="solid")

                ws.cell(row=total_row_idx, column=1, value="Total")
                ws.cell(row=total_row_idx, column=1).font = total_font
                ws.cell(row=total_row_idx, column=1).fill = total_fill

                for col_idx in range(2, len(headers) + 1):
                    col_letter = get_column_letter(col_idx)
                    # Check if column values appear numeric
                    first_val = rows[0][col_idx - 1] if col_idx - 1 < len(rows[0]) else None
                    if isinstance(first_val, (int, float)):
                        formula = f"=SUM({col_letter}2:{col_letter}{total_row_idx - 1})"
                        cell = ws.cell(row=total_row_idx, column=col_idx, value=formula)
                        cell.font = total_font
                        cell.fill = total_fill
                        cell.border = thin_border

            # Auto-fit column widths
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value:
                        val_str = str(cell.value)
                        max_len = max(max_len, len(val_str))
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            wb.save(resolved_path)
            row_count = len(rows)
            col_count = len(headers)
            logger.info("Saved spreadsheet '%s' (%d rows, %d cols)", resolved_path, row_count, col_count)

            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Generated spreadsheet '{resolved_path.name}' with {col_count} columns and {row_count} data rows.",
                output_path=str(resolved_path),
                data={
                    "filename": resolved_path.name,
                    "sheet_name": sheet_name,
                    "headers": headers,
                    "columns": col_count,
                    "rows": row_count,
                    "rows_count": row_count,
                    "has_total_row": include_total,
                    "path": str(resolved_path),
                },
            )
        except Exception as e:
            logger.error("Failed to generate spreadsheet: %s", e, exc_info=True)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Failed to generate spreadsheet: {e}",
                output_path=str(resolved_path),
                error=str(e),
            )
