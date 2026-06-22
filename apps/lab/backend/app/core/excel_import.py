"""Helpers for future Excel module import processing."""

from collections.abc import Mapping, Sequence
from hashlib import sha256
from io import BytesIO
import posixpath
from pathlib import Path
import re
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from PIL import Image as PILImage

from app.core.responses import (
    ModuleCreateDeviceHeaderInput,
    ModuleCreateRequest,
    ModuleCreateRowDeviceEntryInput,
    ModuleCreateRowImageInput,
    ModuleCreateRowInput,
)


WORK_TEXT_COLUMNS = ("E", "F", "G", "H")
COMMON_ROW_COLUMN_MAP = {
    "A": "major_no",
    "B": "middle_no",
    "C": "minor_no",
    "D": "tech_doc_text",
    "I": "expected_result",
}
MAX_DEVICE_SLOTS = 20
OFFICE_DOCUMENT_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
EMU_PER_PIXEL = 9525
HEADER_LABEL_SKIP_SET = {
    "時刻",
    "target",
    "p",
    "対象装置",
    "window",
    "コマンド",
    "大",
    "中",
    "小",
    "技術資料名",
    "作業内容",
    "確認事項or項目",
    "確認事項",
    "項目",
    "expectedresult",
    "item",
}


def normalize_excel_cell_text(value: object) -> str | None:
    """Normalize a value read from Excel into trimmed text.

    Args:
        value: Raw cell value.

    Returns:
        Trimmed text, or ``None`` when the value is empty.
    """

    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None
    return text


def _normalize_label_text(value: object | None) -> str:
    """Normalize header labels for loose worksheet matching."""

    text = normalize_excel_cell_text(value) or ""
    return "".join(text.lower().split())


def _column_letters_to_index(column_letters: str) -> int:
    """Convert Excel column letters such as ``A`` or ``AA`` to 1-based index."""

    index = 0
    for letter in column_letters:
        if not letter.isalpha():
            break
        index = index * 26 + (ord(letter.upper()) - ord("A") + 1)
    return index


def _column_index_to_letters(column_index: int) -> str:
    """Convert a 1-based Excel column index to letters."""

    letters: list[str] = []
    current = column_index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


def _split_cell_reference(cell_reference: str) -> tuple[str, int]:
    """Split an Excel cell reference such as ``J12``."""

    column_letters = "".join(character for character in cell_reference if character.isalpha())
    row_digits = "".join(character for character in cell_reference if character.isdigit())
    if not column_letters or not row_digits:
        raise ValueError(f"Unsupported Excel cell reference: {cell_reference}")
    return column_letters, int(row_digits)


def _resolve_related_part_path(source_part_path: str, target: str) -> str:
    """Resolve an OOXML relationship target to a ZIP part path."""

    normalized_target = target.replace("\\", "/")
    if normalized_target.startswith("/"):
        return normalized_target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(source_part_path), normalized_target))


def _relationship_map(archive: ZipFile, rels_path: str) -> dict[str, tuple[str, str]]:
    """Read an OOXML relationship file as ``id -> (type, target)``."""

    if rels_path not in archive.namelist():
        return {}

    root = ElementTree.fromstring(archive.read(rels_path))
    return {
        rel.attrib["Id"]: (rel.attrib.get("Type", ""), rel.attrib.get("Target", ""))
        for rel in root.findall("pkgrel:Relationship", OFFICE_DOCUMENT_NS)
        if "Id" in rel.attrib
    }


def _safe_image_key_part(value: str) -> str:
    """Normalize a text fragment for image keys and paths."""

    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return normalized.lower() or "module"


def _emu_to_px(value: str | int | None) -> int:
    """Convert Excel EMU coordinates to approximate pixels."""

    if value in (None, ""):
        return 0
    return round(int(value) / EMU_PER_PIXEL)


def _image_size_px(archive: ZipFile, media_path: str) -> tuple[int | None, int | None]:
    """Read image dimensions from an OOXML media part."""

    try:
        with PILImage.open(BytesIO(archive.read(media_path))) as image:
            return image.size
    except Exception:
        return None, None


def _read_xlsx_shared_strings(archive: ZipFile) -> list[str]:
    """Read shared strings from an XLSX/XLSM archive when present."""

    shared_strings_path = "xl/sharedStrings.xml"
    if shared_strings_path not in archive.namelist():
        return []

    root = ElementTree.fromstring(archive.read(shared_strings_path))
    values: list[str] = []
    for item in root.findall("main:si", OFFICE_DOCUMENT_NS):
        values.append(_read_xlsx_text_without_phonetics(item))
    return values


def _read_xlsx_text_without_phonetics(node: ElementTree.Element) -> str:
    """Read OOXML text nodes while excluding Excel phonetic guide text."""

    text_parts = [text_node.text or "" for text_node in node.findall("main:t", OFFICE_DOCUMENT_NS)]
    text_parts.extend(
        text_node.text or ""
        for run_node in node.findall("main:r", OFFICE_DOCUMENT_NS)
        for text_node in run_node.findall("main:t", OFFICE_DOCUMENT_NS)
    )
    return "".join(text_parts)


def _extract_sheet_rows(archive: ZipFile, sheet_path: str) -> tuple[str | None, list[tuple[int, dict[str, str | None]]]]:
    """Extract one worksheet into row-wise cell mappings."""

    shared_strings = _read_xlsx_shared_strings(archive)
    root = ElementTree.fromstring(archive.read(sheet_path))
    rows: list[tuple[int, dict[str, str | None]]] = []

    for row_node in root.findall("main:sheetData/main:row", OFFICE_DOCUMENT_NS):
        row_index = int(row_node.attrib.get("r", "0"))
        cell_map: dict[str, str | None] = {}

        for cell_node in row_node.findall("main:c", OFFICE_DOCUMENT_NS):
            reference = cell_node.attrib.get("r")
            if not reference:
                continue
            column_letters, _ = _split_cell_reference(reference)
            cell_type = cell_node.attrib.get("t")
            value: str | None

            if cell_type == "inlineStr":
                inline_string_node = cell_node.find("main:is", OFFICE_DOCUMENT_NS)
                value = _read_xlsx_text_without_phonetics(inline_string_node) if inline_string_node is not None else None
            elif cell_type == "e" and "vm" in cell_node.attrib:
                value = None
            else:
                value_node = cell_node.find("main:v", OFFICE_DOCUMENT_NS)
                if value_node is None or value_node.text is None:
                    value = None
                elif cell_type == "s":
                    value = shared_strings[int(value_node.text)]
                else:
                    value = value_node.text

            cell_map[column_letters] = normalize_excel_cell_text(value)

        rows.append((row_index, cell_map))

    sheet_name = root.attrib.get("name")
    return sheet_name, rows


def _extract_rich_data_image_media_paths(archive: ZipFile) -> list[str]:
    """Extract media paths used by Excel rich data local images."""

    rich_value_rel_path = "xl/richData/richValueRel.xml"
    rich_value_rels_path = "xl/richData/_rels/richValueRel.xml.rels"
    if rich_value_rel_path not in archive.namelist() or rich_value_rels_path not in archive.namelist():
        return []

    relationships = _relationship_map(archive, rich_value_rels_path)
    root = ElementTree.fromstring(archive.read(rich_value_rel_path))
    media_paths: list[str] = []

    for rel_node in root:
        rel_id = rel_node.attrib.get(f"{{{OFFICE_DOCUMENT_NS['rel']}}}id")
        if rel_id is None or rel_id not in relationships:
            continue

        relationship_type, target = relationships[rel_id]
        if not relationship_type.endswith("/image") or not target:
            continue

        media_path = _resolve_related_part_path(rich_value_rel_path, target)
        if media_path in archive.namelist():
            media_paths.append(media_path)

    return media_paths


def _extract_rich_data_image_cells(archive: ZipFile, sheet_path: str) -> list[tuple[int, int, str]]:
    """Return cells that carry rich data value metadata."""

    root = ElementTree.fromstring(archive.read(sheet_path))
    image_cells: list[tuple[int, int, str]] = []
    for cell_node in root.findall(".//main:c", OFFICE_DOCUMENT_NS):
        reference = cell_node.attrib.get("r")
        if reference is None or "vm" not in cell_node.attrib:
            continue

        column_letters, row_index = _split_cell_reference(reference)
        image_cells.append((row_index, _column_letters_to_index(column_letters), reference))

    return sorted(image_cells, key=lambda item: (item[0], item[1], item[2]))


def _extract_sheet_images(
    *,
    archive: ZipFile,
    sheet_path: str,
    image_storage_dir: str | Path | None,
    source_sha256: str,
) -> dict[int, list[dict[str, int | str | None]]]:
    """Extract worksheet images, save them, and return metadata by Excel row."""

    if image_storage_dir is None:
        return {}

    sheet_rels_path = posixpath.join(
        posixpath.dirname(sheet_path),
        "_rels",
        f"{posixpath.basename(sheet_path)}.rels",
    )
    sheet_relationships = _relationship_map(archive, sheet_rels_path)
    drawing_targets = [
        target
        for relationship_type, target in sheet_relationships.values()
        if relationship_type.endswith("/drawing") and target
    ]
    rich_data_media_paths = _extract_rich_data_image_media_paths(archive)
    if not drawing_targets and not rich_data_media_paths:
        return {}

    storage_root = Path(image_storage_dir)
    source_key = _safe_image_key_part(source_sha256[:12])
    target_dir = storage_root / source_key
    target_dir.mkdir(parents=True, exist_ok=True)

    images_by_row: dict[int, list[dict[str, int | str | None]]] = {}
    image_counts_by_row: dict[int, int] = {}

    def save_image_metadata(
        *,
        row_index: int,
        column_index: int,
        media_path: str,
        offset_x_px: int = 0,
        offset_y_px: int = 0,
        width_px: int | None = None,
        height_px: int | None = None,
    ) -> None:
        image_counts_by_row[row_index] = image_counts_by_row.get(row_index, 0) + 1
        image_order = image_counts_by_row[row_index]
        image_key = f"img_{source_key}_r{row_index}_img{image_order}"
        extension = Path(media_path).suffix.lower() or ".png"
        image_path = target_dir / f"{image_key}{extension}"
        image_path.write_bytes(archive.read(media_path))

        images_by_row.setdefault(row_index, []).append(
            {
                "image_key": image_key,
                "image_path": image_path.as_posix(),
                "anchor_cell": f"{_column_index_to_letters(column_index)}{row_index}",
                "offset_x_px": offset_x_px,
                "offset_y_px": offset_y_px,
                "width_px": width_px,
                "height_px": height_px,
                "image_order": image_order,
            }
        )

    for drawing_target in drawing_targets:
        drawing_path = _resolve_related_part_path(sheet_path, drawing_target)
        if drawing_path not in archive.namelist():
            continue

        drawing_rels_path = posixpath.join(
            posixpath.dirname(drawing_path),
            "_rels",
            f"{posixpath.basename(drawing_path)}.rels",
        )
        drawing_relationships = _relationship_map(archive, drawing_rels_path)
        drawing_root = ElementTree.fromstring(archive.read(drawing_path))

        for anchor_node in list(drawing_root.findall("xdr:oneCellAnchor", OFFICE_DOCUMENT_NS)) + list(
            drawing_root.findall("xdr:twoCellAnchor", OFFICE_DOCUMENT_NS)
        ):
            from_node = anchor_node.find("xdr:from", OFFICE_DOCUMENT_NS)
            blip_node = anchor_node.find(".//a:blip", OFFICE_DOCUMENT_NS)
            if from_node is None or blip_node is None:
                continue

            embed_id = blip_node.attrib.get(f"{{{OFFICE_DOCUMENT_NS['rel']}}}embed")
            if embed_id is None or embed_id not in drawing_relationships:
                continue

            _, media_target = drawing_relationships[embed_id]
            media_path = _resolve_related_part_path(drawing_path, media_target)
            if media_path not in archive.namelist():
                continue

            row_node = from_node.find("xdr:row", OFFICE_DOCUMENT_NS)
            col_node = from_node.find("xdr:col", OFFICE_DOCUMENT_NS)
            if row_node is None or col_node is None or row_node.text is None or col_node.text is None:
                continue

            row_index = int(row_node.text) + 1
            column_index = int(col_node.text) + 1
            ext_node = anchor_node.find("xdr:ext", OFFICE_DOCUMENT_NS)
            col_off_node = from_node.find("xdr:colOff", OFFICE_DOCUMENT_NS)
            row_off_node = from_node.find("xdr:rowOff", OFFICE_DOCUMENT_NS)
            save_image_metadata(
                row_index=row_index,
                column_index=column_index,
                media_path=media_path,
                offset_x_px=_emu_to_px(col_off_node.text if col_off_node is not None else None),
                offset_y_px=_emu_to_px(row_off_node.text if row_off_node is not None else None),
                width_px=_emu_to_px(ext_node.attrib.get("cx")) if ext_node is not None else None,
                height_px=_emu_to_px(ext_node.attrib.get("cy")) if ext_node is not None else None,
            )

    rich_data_image_cells = _extract_rich_data_image_cells(archive, sheet_path)
    for (row_index, column_index, _), media_path in zip(rich_data_image_cells, rich_data_media_paths, strict=False):
        width_px, height_px = _image_size_px(archive, media_path)
        save_image_metadata(
            row_index=row_index,
            column_index=column_index,
            media_path=media_path,
            width_px=width_px,
            height_px=height_px,
        )

    return images_by_row


def _resolve_workbook_sheet_path(archive: ZipFile, sheet_name: str | None = None) -> tuple[str, str]:
    """Resolve the first or named sheet path inside the workbook archive."""

    workbook_root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    workbook_rels_root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationship_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in workbook_rels_root.findall("pkgrel:Relationship", OFFICE_DOCUMENT_NS)
    }

    sheets = workbook_root.findall("main:sheets/main:sheet", OFFICE_DOCUMENT_NS)
    if not sheets:
        raise ValueError("Workbook does not contain any sheets.")

    selected_sheet = None
    if sheet_name:
        normalized_sheet_name = _normalize_label_text(sheet_name)
        for candidate in sheets:
            if _normalize_label_text(candidate.attrib.get("name")) == normalized_sheet_name:
                selected_sheet = candidate
                break
        if selected_sheet is None:
            raise ValueError("Requested sheet_name was not found in workbook.")
    else:
        selected_sheet = sheets[0]

    relation_id = selected_sheet.attrib.get(f"{{{OFFICE_DOCUMENT_NS['rel']}}}id")
    if relation_id is None or relation_id not in relationship_map:
        raise ValueError("Workbook sheet relationship is missing.")

    target_path = relationship_map[relation_id].replace("\\", "/")
    if not target_path.startswith("xl/"):
        target_path = f"xl/{target_path.lstrip('/')}"
    return selected_sheet.attrib.get("name", "sheet"), target_path


def _find_header_row_index(rows: Sequence[tuple[int, dict[str, str | None]]]) -> int | None:
    """Find the table header row by matching common procedure labels."""

    required_label_sets = (
        {"大", "中", "小", "作業内容"},
        {"major", "middle", "minor", "work"},
    )
    for row_index, cell_map in rows:
        normalized_values = {_normalize_label_text(value) for value in cell_map.values() if value}
        if any(
            all(_normalize_label_text(label) in normalized_values for label in required_labels)
            for required_labels in required_label_sets
        ):
            return row_index
    return None


def _extract_device_headers_from_rows(
    rows_before_header: Sequence[tuple[int, dict[str, str | None]]],
    device_count: int,
) -> list[dict[str, str | int | None]]:
    """Extract device header blocks from worksheet rows before the table header."""

    headers: list[dict[str, str | int | None]] = []
    for slot_no in range(1, device_count + 1):
        start_index = 10 + ((slot_no - 1) * 4)
        field_names = ("header_time_text", "target_text", "p_text", "target_device_text")
        header_values: dict[str, str | int | None] = {"slot_no": slot_no}

        for offset, field_name in enumerate(field_names):
            column_name = _column_index_to_letters(start_index + offset)
            candidates = [
                value
                for _, cell_map in rows_before_header
                if (value := cell_map.get(column_name)) is not None
                and _normalize_label_text(value) not in HEADER_LABEL_SKIP_SET
            ]
            header_values[field_name] = candidates[-1] if candidates else None

        if header_values["target_device_text"] is None:
            header_values["target_device_text"] = f"device-{slot_no:02d}"
        headers.append(header_values)

    return headers


def _build_sheet_rows_from_cells(
    rows_after_header: Sequence[tuple[int, dict[str, str | None]]],
    device_count: int,
    row_images_by_row_index: Mapping[int, Sequence[Mapping[str, int | str | None]]] | None = None,
) -> list[dict[str, Any]]:
    """Convert worksheet rows after the header into helper-compatible row cells."""

    normalized_rows: list[dict[str, Any]] = []
    row_images_by_row_index = row_images_by_row_index or {}

    for row_index, cell_map in rows_after_header:
        row_payload: dict[str, Any] = {column_name: cell_map.get(column_name) for column_name in COMMON_ROW_COLUMN_MAP}
        row_payload.update({column_name: cell_map.get(column_name) for column_name in WORK_TEXT_COLUMNS})

        device_entries: list[dict[str, str | int | None]] = []
        for slot_no in range(1, device_count + 1):
            start_index = 10 + ((slot_no - 1) * 4)
            device_entries.append(
                {
                    "slot_no": slot_no,
                    "time_text": cell_map.get(_column_index_to_letters(start_index)),
                    "window_text": cell_map.get(_column_index_to_letters(start_index + 1)),
                    "p_text": cell_map.get(_column_index_to_letters(start_index + 2)),
                    "command_text": cell_map.get(_column_index_to_letters(start_index + 3)),
                }
            )

        row_payload["device_entries"] = device_entries
        row_payload["images"] = list(row_images_by_row_index.get(row_index, []))
        normalized_rows.append(row_payload)

    return normalized_rows


def extract_work_text_and_indent_level(
    work_cells: Mapping[str, object | None],
) -> tuple[str | None, int | None]:
    """Resolve work text and indent level from Excel work-area columns.

    The current Excel prototypes express indentation by placing text in one of
    the work columns ``E`` through ``H``. The first non-empty column becomes the
    displayed work text and its zero-based position becomes ``indent_level``.

    Args:
        work_cells: Mapping of column letter to cell value.

    Returns:
        A tuple of ``(work_text, indent_level)``. Both values are ``None`` when
        every tracked work column is empty.
    """

    for indent_level, column_name in enumerate(WORK_TEXT_COLUMNS):
        text = normalize_excel_cell_text(work_cells.get(column_name))
        if text is not None:
            return text, indent_level
    return None, None


def _normalize_sheet_device_headers(
    raw_device_headers: Sequence[Mapping[str, object | None]],
) -> list[ModuleCreateDeviceHeaderInput]:
    """Normalize device header blocks extracted from one Excel sheet."""

    normalized_headers: list[ModuleCreateDeviceHeaderInput] = []
    slot_nos: set[int] = set()

    for raw_header in raw_device_headers:
        slot_no = int(raw_header.get("slot_no", 1))
        if slot_no > MAX_DEVICE_SLOTS:
            raise ValueError("Excel device headers must not exceed 20 slots.")
        header = ModuleCreateDeviceHeaderInput(
            slot_no=slot_no,
            header_time_text=normalize_excel_cell_text(raw_header.get("header_time_text")),
            target_text=normalize_excel_cell_text(raw_header.get("target_text")),
            p_text=normalize_excel_cell_text(raw_header.get("p_text")),
            target_device_text=normalize_excel_cell_text(raw_header.get("target_device_text")),
        )
        if (
            header.header_time_text is None
            and header.target_text is None
            and header.p_text is None
            and header.target_device_text is None
        ):
            continue
        if header.slot_no in slot_nos:
            raise ValueError("slot_no must be unique within Excel device headers.")
        slot_nos.add(header.slot_no)
        normalized_headers.append(header)

    if len(normalized_headers) > MAX_DEVICE_SLOTS:
        raise ValueError("Excel device headers must not exceed 20 slots.")

    if not normalized_headers:
        normalized_headers.append(ModuleCreateDeviceHeaderInput(slot_no=1))

    return sorted(normalized_headers, key=lambda item: item.slot_no)


def _normalize_sheet_row_device_entries(
    raw_device_entries: Sequence[Mapping[str, object | None]],
    allowed_slot_nos: set[int],
) -> list[ModuleCreateRowDeviceEntryInput]:
    """Normalize one row's device-specific command cells."""

    normalized_entries: list[ModuleCreateRowDeviceEntryInput] = []
    slot_nos: set[int] = set()

    for raw_entry in raw_device_entries:
        slot_no = int(raw_entry.get("slot_no", 1))
        if slot_no not in allowed_slot_nos:
            raise ValueError("row device entries must reference configured device headers.")

        entry = ModuleCreateRowDeviceEntryInput(
            slot_no=slot_no,
            time_text=normalize_excel_cell_text(raw_entry.get("time_text")),
            window_text=normalize_excel_cell_text(raw_entry.get("window_text")),
            p_text=normalize_excel_cell_text(raw_entry.get("p_text")),
            command_text=normalize_excel_cell_text(raw_entry.get("command_text")),
        )
        if (
            entry.time_text is None
            and entry.window_text is None
            and entry.p_text is None
            and entry.command_text is None
        ):
            continue
        if entry.slot_no in slot_nos:
            raise ValueError("slot_no must be unique within one row's Excel device entries.")
        slot_nos.add(entry.slot_no)
        normalized_entries.append(entry)

    return sorted(normalized_entries, key=lambda item: item.slot_no)


def _normalize_sheet_row_images(
    raw_images: Sequence[Mapping[str, object | None]],
) -> list[ModuleCreateRowImageInput]:
    """Normalize image metadata extracted from one Excel row."""

    normalized_images = [
        ModuleCreateRowImageInput(
            image_key=str(raw_image.get("image_key") or "").strip(),
            image_path=str(raw_image.get("image_path") or "").strip(),
            anchor_cell=str(raw_image.get("anchor_cell") or "").strip(),
            offset_x_px=int(raw_image.get("offset_x_px") or 0),
            offset_y_px=int(raw_image.get("offset_y_px") or 0),
            width_px=int(raw_image["width_px"]) if raw_image.get("width_px") is not None else None,
            height_px=int(raw_image["height_px"]) if raw_image.get("height_px") is not None else None,
            image_order=int(raw_image.get("image_order") or 1),
        )
        for raw_image in raw_images
    ]
    return sorted(normalized_images, key=lambda item: item.image_order)


def build_module_create_request_from_sheet_data(
    *,
    module_name: str,
    row_cells: Sequence[Mapping[str, object | None]],
    device_header_cells: Sequence[Mapping[str, object | None]] = (),
    module_key: str | None = None,
    description: str | None = None,
    change_note: str | None = None,
    source_xlsx_path: str | None = None,
    source_sha256: str | None = None,
    created_by: str | None = None,
) -> ModuleCreateRequest:
    """Convert one Excel sheet's normalized cells into ``ModuleCreateRequest``.

    Args:
        module_name: Target module name.
        row_cells: Row-wise Excel cell values. Common columns use ``A`` through
            ``I`` and device-specific row data is passed via ``device_entries``.
        device_header_cells: Device header blocks for the sheet.
        module_key: Optional target module key.
        description: Optional module description.
        change_note: Optional module change note.
        source_xlsx_path: Optional source workbook path.
        source_sha256: Optional source workbook hash.
        created_by: Optional import operator.

    Returns:
        ``ModuleCreateRequest`` normalized for existing create API.
    """

    normalized_headers = _normalize_sheet_device_headers(device_header_cells)
    allowed_slot_nos = {header.slot_no for header in normalized_headers}
    normalized_rows: list[ModuleCreateRowInput] = []

    for raw_row in row_cells:
        work_text, indent_level = extract_work_text_and_indent_level(raw_row)
        common_values = {
            field_name: normalize_excel_cell_text(raw_row.get(column_name))
            for column_name, field_name in COMMON_ROW_COLUMN_MAP.items()
        }
        device_entries = _normalize_sheet_row_device_entries(
            raw_row.get("device_entries", []) or [],
            allowed_slot_nos,
        )
        images = _normalize_sheet_row_images(raw_row.get("images", []) or [])

        if (
            work_text is None
            and all(value is None for value in common_values.values())
            and not device_entries
            and not images
        ):
            continue

        normalized_rows.append(
            ModuleCreateRowInput(
                row_order=len(normalized_rows) + 1,
                row_type="step",
                major_no=common_values["major_no"],
                middle_no=common_values["middle_no"],
                minor_no=common_values["minor_no"],
                tech_doc_text=common_values["tech_doc_text"],
                work_text=work_text,
                indent_level=indent_level,
                expected_result=common_values["expected_result"],
                device_entries=device_entries,
                images=images,
            )
        )

    if not normalize_excel_cell_text(module_name):
        raise ValueError("module_name must not be blank.")
    if not normalized_rows:
        raise ValueError("sheet must contain at least one non-empty row.")

    return ModuleCreateRequest(
        module_key=normalize_excel_cell_text(module_key),
        module_name=normalize_excel_cell_text(module_name) or "",
        description=normalize_excel_cell_text(description),
        change_note=normalize_excel_cell_text(change_note),
        source_xlsx_path=normalize_excel_cell_text(source_xlsx_path),
        source_sha256=normalize_excel_cell_text(source_sha256),
        created_by=normalize_excel_cell_text(created_by),
        device_headers=normalized_headers,
        rows=normalized_rows,
    )


def build_module_create_request_from_workbook_bytes(
    *,
    workbook_bytes: bytes,
    filename: str,
    created_by: str | None = None,
    sheet_name: str | None = None,
    image_storage_dir: str | Path | None = None,
) -> ModuleCreateRequest:
    """Convert an uploaded XLSX/XLSM workbook into ``ModuleCreateRequest``.

    The current Sprint 3 scope reads only one sheet and normalizes it using the
    same helper path as the JSON-based ``import-sheet`` endpoint.
    """

    if not workbook_bytes:
        raise ValueError("Workbook bytes must not be empty.")

    extension = Path(filename).suffix.lower()
    if extension not in {".xlsx", ".xlsm"}:
        raise ValueError("filename must end with .xlsx or .xlsm.")

    source_hash = sha256(workbook_bytes).hexdigest()
    try:
        with ZipFile(BytesIO(workbook_bytes)) as archive:
            selected_sheet_name, sheet_path = _resolve_workbook_sheet_path(archive, sheet_name=sheet_name)
            _, extracted_rows = _extract_sheet_rows(archive, sheet_path)
            row_images_by_row_index = _extract_sheet_images(
                archive=archive,
                sheet_path=sheet_path,
                image_storage_dir=image_storage_dir,
                source_sha256=source_hash,
            )
    except BadZipFile as exception:
        raise ValueError("Uploaded file is not a valid XLSX/XLSM workbook.") from exception
    except KeyError as exception:
        raise ValueError("Workbook structure is incomplete.") from exception
    except ElementTree.ParseError as exception:
        raise ValueError("Workbook XML could not be parsed.") from exception

    header_row_index = _find_header_row_index(extracted_rows)
    if header_row_index is None:
        raise ValueError("Worksheet header row was not found.")

    rows_before_header = [row for row in extracted_rows if row[0] < header_row_index]
    rows_after_header = [row for row in extracted_rows if row[0] > header_row_index]
    if not rows_after_header:
        raise ValueError("Worksheet does not contain any data rows.")

    max_column_index = max(
        (
            _column_letters_to_index(column_name)
            for _, cell_map in rows_after_header
            for column_name, value in cell_map.items()
            if value is not None
        ),
        default=9,
    )
    device_count = max(1, ((max_column_index - 10) // 4) + 1) if max_column_index >= 10 else 1
    if device_count > MAX_DEVICE_SLOTS:
        raise ValueError("Excel device headers must not exceed 20 slots.")

    return build_module_create_request_from_sheet_data(
        module_key=None,
        module_name=selected_sheet_name,
        description=None,
        change_note="imported from workbook upload",
        source_xlsx_path=filename,
        source_sha256=source_hash,
        created_by=created_by,
        device_header_cells=_extract_device_headers_from_rows(rows_before_header, device_count),
        row_cells=_build_sheet_rows_from_cells(rows_after_header, device_count, row_images_by_row_index),
    )
