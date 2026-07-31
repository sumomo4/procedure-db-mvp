"""Normalization and scoring helpers for module similarity checks."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
import hmac
import json
import math
import re
import time
import unicodedata

from app.core.responses import (
    ModuleCreateRequest,
    ModuleDetailData,
    ModuleSimilarityCalculationData,
    ModuleSimilarityCandidateData,
    ModuleSimilarityCheckData,
    ModuleSimilarityScoreBreakdownData,
)
from app.core.config import AppSettings


ModuleSimilaritySource = ModuleCreateRequest | ModuleDetailData


@dataclass(frozen=True, slots=True)
class ModuleSimilarityWeights:
    """Weights used to combine component similarity scores."""

    work_text: float = 0.30
    expected_result: float = 0.20
    command: float = 0.25
    name: float = 0.10
    structure: float = 0.10
    device_header: float = 0.05

    def as_dict(self) -> dict[str, float]:
        """Return weights keyed like the score-breakdown model."""

        return {
            "work_text": self.work_text,
            "expected_result": self.expected_result,
            "command": self.command,
            "name": self.name,
            "structure": self.structure,
            "device_header": self.device_header,
        }


DEFAULT_MODULE_SIMILARITY_WEIGHTS = ModuleSimilarityWeights()
SIMILARITY_CONFIRMATION_TOKEN_VERSION = 1


@dataclass(frozen=True, slots=True)
class ModuleSimilaritySignature:
    """Normalized module fields used for candidate search and detailed scoring."""

    normalized_name: str
    normalized_work_text: str
    normalized_expected_text: str
    normalized_command_text: str
    normalized_structure_text: str
    normalized_device_header_text: str
    normalized_image_text: str
    combined_text: str
    exact_sha256: str
    row_count: int
    image_count: int


def _candidate_set_sha256(candidates: list[ModuleSimilarityCandidateData]) -> str:
    """Return a stable digest for every candidate that requires confirmation."""

    candidate_values = [
        {
            "module_version_id": candidate.module_version_id,
            "module_key": candidate.module_key,
            "similarity": f"{candidate.similarity:.4f}",
        }
        for candidate in sorted(candidates, key=lambda item: item.module_version_id)
    ]
    serialized = json.dumps(
        candidate_values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _urlsafe_base64_encode(value: bytes) -> str:
    """Encode bytes for use in a compact URL-safe token."""

    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _urlsafe_base64_decode(value: str) -> bytes:
    """Decode URL-safe base64 text with omitted padding."""

    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def issue_similarity_confirmation_token(
    settings: AppSettings,
    input_sha256: str,
    candidate_set_sha256: str,
    *,
    now_epoch: int | None = None,
) -> str:
    """Issue a signed, short-lived token bound to input and candidate set."""

    issued_at = int(time.time()) if now_epoch is None else now_epoch
    payload = {
        "version": SIMILARITY_CONFIRMATION_TOKEN_VERSION,
        "input_sha256": input_sha256,
        "candidate_set_sha256": candidate_set_sha256,
        "expires_at": issued_at + settings.module_similarity_confirmation_ttl_seconds,
    }
    encoded_payload = _urlsafe_base64_encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(
        settings.module_similarity_confirmation_secret.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_urlsafe_base64_encode(signature)}"


def validate_similarity_confirmation_token(
    settings: AppSettings,
    result: ModuleSimilarityCheckData,
    confirmation_token: str | None,
    *,
    now_epoch: int | None = None,
) -> bool:
    """Validate a token against the latest similarity-check result."""

    if result.candidate_count == 0:
        return True
    if not confirmation_token:
        return False

    try:
        encoded_payload, encoded_signature = confirmation_token.split(".", maxsplit=1)
        expected_signature = hmac.new(
            settings.module_similarity_confirmation_secret.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        supplied_signature = _urlsafe_base64_decode(encoded_signature)
        if not hmac.compare_digest(expected_signature, supplied_signature):
            return False

        payload = json.loads(_urlsafe_base64_decode(encoded_payload))
        current_epoch = int(time.time()) if now_epoch is None else now_epoch
        return (
            payload.get("version") == SIMILARITY_CONFIRMATION_TOKEN_VERSION
            and payload.get("input_sha256") == result.input_sha256
            and payload.get("candidate_set_sha256") == result.candidate_set_sha256
            and int(payload.get("expires_at", 0)) >= current_epoch
        )
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return False


def normalize_prose_text(value: object | None) -> str:
    """Normalize human-readable text without changing its meaning."""

    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().casefold()


def normalize_command_text(value: object | None) -> str:
    """Normalize command text while preserving letter case and line order."""

    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    lines = [
        re.sub(r"[^\S\n]+", " ", line).strip()
        for line in normalized.split("\n")
    ]
    return "\n".join(line for line in lines if line)


def _join_non_empty_tokens(tokens: list[str]) -> str:
    """Join non-empty normalized tokens while preserving their order."""

    return "\n".join(token for token in tokens if token)


def _build_name_text(module: ModuleSimilaritySource) -> str:
    """Build normalized module-name and technical-document text."""

    tokens = [normalize_prose_text(module.module_name)]
    tokens.extend(
        value
        for row in sorted(module.rows, key=lambda item: item.row_order)
        if (value := normalize_prose_text(row.tech_doc_text))
    )
    return _join_non_empty_tokens(tokens)


def _build_work_text(module: ModuleSimilaritySource) -> str:
    """Build ordered work and note text."""

    tokens: list[str] = []
    for row in sorted(module.rows, key=lambda item: item.row_order):
        work_text = normalize_prose_text(row.work_text)
        note = normalize_prose_text(row.note)
        if work_text:
            tokens.append(work_text)
        if note:
            tokens.append(note)
    return _join_non_empty_tokens(tokens)


def _build_expected_text(module: ModuleSimilaritySource) -> str:
    """Build ordered expected-result text."""

    return _join_non_empty_tokens(
        [
            value
            for row in sorted(module.rows, key=lambda item: item.row_order)
            if (value := normalize_prose_text(row.expected_result))
        ]
    )


def _build_command_text(module: ModuleSimilaritySource) -> str:
    """Build ordered common and per-device command values."""

    tokens: list[str] = []
    for row in sorted(module.rows, key=lambda item: item.row_order):
        row_tokens: list[str] = []
        common_values = (
            normalize_command_text(row.time_text),
            normalize_command_text(row.window_text),
            normalize_command_text(row.p_text),
            normalize_command_text(row.command_text),
        )
        if any(common_values):
            row_tokens.append("common|" + "|".join(common_values))

        for entry in sorted(row.device_entries, key=lambda item: item.slot_no):
            entry_values = (
                normalize_command_text(entry.time_text),
                normalize_command_text(entry.window_text),
                normalize_command_text(entry.p_text),
                normalize_command_text(entry.command_text),
            )
            if any(entry_values):
                row_tokens.append(f"slot:{entry.slot_no}|" + "|".join(entry_values))

        if row_tokens:
            tokens.append(f"row:{row.row_order}")
            tokens.extend(row_tokens)

    return _join_non_empty_tokens(tokens)


def _build_structure_text(module: ModuleSimilaritySource) -> str:
    """Build normalized row structure without procedure prose."""

    tokens: list[str] = []
    for row in sorted(module.rows, key=lambda item: item.row_order):
        device_slots = ",".join(
            str(entry.slot_no)
            for entry in sorted(row.device_entries, key=lambda item: item.slot_no)
        )
        tokens.append(
            "|".join(
                [
                    f"row:{row.row_order}",
                    normalize_prose_text(row.row_type),
                    normalize_prose_text(row.major_no),
                    normalize_prose_text(row.middle_no),
                    normalize_prose_text(row.minor_no),
                    str(row.indent_level if row.indent_level is not None else ""),
                    f"slots:{device_slots}",
                ]
            )
        )
    return _join_non_empty_tokens(tokens)


def _build_device_header_text(module: ModuleSimilaritySource) -> str:
    """Build normalized device-header values in slot order."""

    tokens: list[str] = []
    legacy_values = (
        normalize_prose_text(module.header_time_text),
        normalize_prose_text(module.target_text),
        normalize_command_text(module.common_p_text),
        normalize_prose_text(module.target_device_text),
    )
    if any(legacy_values):
        tokens.append("legacy|" + "|".join(legacy_values))

    for header in sorted(module.device_headers, key=lambda item: item.slot_no):
        values = (
            normalize_prose_text(header.header_time_text),
            normalize_prose_text(header.target_text),
            normalize_command_text(header.p_text),
            normalize_prose_text(header.target_device_text),
        )
        if any(values):
            tokens.append(f"slot:{header.slot_no}|" + "|".join(values))

    return _join_non_empty_tokens(tokens)


def _build_image_text(module: ModuleSimilaritySource) -> str:
    """Build image metadata used for exact-match and supplemental display."""

    tokens: list[str] = []
    for row in sorted(module.rows, key=lambda item: item.row_order):
        for image in sorted(
            row.images,
            key=lambda item: (item.image_order, item.anchor_cell),
        ):
            tokens.append(
                "|".join(
                    [
                        f"row:{row.row_order}",
                        normalize_prose_text(image.anchor_cell),
                        str(image.offset_x_px),
                        str(image.offset_y_px),
                        str(image.width_px if image.width_px is not None else ""),
                        str(image.height_px if image.height_px is not None else ""),
                        str(image.image_order),
                    ]
                )
            )
    return _join_non_empty_tokens(tokens)


def build_module_similarity_signature(
    module: ModuleSimilaritySource,
) -> ModuleSimilaritySignature:
    """Build a deterministic signature from an imported or persisted module."""

    normalized_name = _build_name_text(module)
    normalized_work_text = _build_work_text(module)
    normalized_expected_text = _build_expected_text(module)
    normalized_command_text = _build_command_text(module)
    normalized_structure_text = _build_structure_text(module)
    normalized_device_header_text = _build_device_header_text(module)
    normalized_image_text = _build_image_text(module)

    canonical_data = {
        "name": normalized_name,
        "work_text": normalized_work_text,
        "expected_text": normalized_expected_text,
        "command_text": normalized_command_text,
        "structure_text": normalized_structure_text,
        "device_header_text": normalized_device_header_text,
        "image_text": normalized_image_text,
    }
    canonical_json = json.dumps(
        canonical_data,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    exact_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    combined_text = _join_non_empty_tokens(
        [
            normalized_name,
            normalized_work_text,
            normalized_expected_text,
            normalized_command_text,
            normalized_structure_text,
            normalized_device_header_text,
        ]
    )

    return ModuleSimilaritySignature(
        normalized_name=normalized_name,
        normalized_work_text=normalized_work_text,
        normalized_expected_text=normalized_expected_text,
        normalized_command_text=normalized_command_text,
        normalized_structure_text=normalized_structure_text,
        normalized_device_header_text=normalized_device_header_text,
        normalized_image_text=normalized_image_text,
        combined_text=combined_text,
        exact_sha256=exact_sha256,
        row_count=len(module.rows),
        image_count=sum(len(row.images) for row in module.rows),
    )


def _optional_similarity(before: str, after: str) -> float | None:
    """Compare values, excluding a component when both sides are empty."""

    if not before and not after:
        return None
    if not before or not after:
        return 0.0
    return SequenceMatcher(None, before, after, autojunk=False).ratio()


def calculate_module_similarity(
    before: ModuleSimilaritySignature,
    after: ModuleSimilaritySignature,
    weights: ModuleSimilarityWeights = DEFAULT_MODULE_SIMILARITY_WEIGHTS,
) -> ModuleSimilarityCalculationData:
    """Calculate an explainable weighted score between two signatures."""

    scores: dict[str, float | None] = {
        "work_text": _optional_similarity(
            before.normalized_work_text,
            after.normalized_work_text,
        ),
        "expected_result": _optional_similarity(
            before.normalized_expected_text,
            after.normalized_expected_text,
        ),
        "command": _optional_similarity(
            before.normalized_command_text,
            after.normalized_command_text,
        ),
        "name": _optional_similarity(
            before.normalized_name,
            after.normalized_name,
        ),
        "structure": _optional_similarity(
            before.normalized_structure_text,
            after.normalized_structure_text,
        ),
        "device_header": _optional_similarity(
            before.normalized_device_header_text,
            after.normalized_device_header_text,
        ),
    }
    weight_values = weights.as_dict()
    if any(value < 0 for value in weight_values.values()):
        raise ValueError("類似度の重みは0以上で指定してください。")
    if not math.isclose(sum(weight_values.values()), 1.0, abs_tol=1e-9):
        raise ValueError("類似度の重み合計は1.0にしてください。")

    applied_weight = sum(
        weight_values[name]
        for name, score in scores.items()
        if score is not None
    )
    if applied_weight <= 0:
        similarity = 0.0
    else:
        similarity = sum(
            score * weight_values[name]
            for name, score in scores.items()
            if score is not None
        ) / applied_weight

    return ModuleSimilarityCalculationData(
        similarity=round(similarity, 4),
        exact_match=before.exact_sha256 == after.exact_sha256,
        image_metadata_match=(
            before.normalized_image_text == after.normalized_image_text
        ),
        applied_weight=round(applied_weight, 4),
        score_breakdown=ModuleSimilarityScoreBreakdownData(
            **{
                name: round(score, 4) if score is not None else None
                for name, score in scores.items()
            }
        ),
    )


_MATCHED_FIELD_LABELS = {
    "work_text": "作業内容",
    "expected_result": "確認事項",
    "command": "コマンド",
    "name": "名称",
    "structure": "行構成",
    "device_header": "対象装置ヘッダー",
}


def _matched_field_labels(
    calculation: ModuleSimilarityCalculationData,
    threshold: float,
) -> list[str]:
    """Return user-facing names for components meeting the threshold."""

    scores = calculation.score_breakdown.model_dump()
    return [
        label
        for field_name, label in _MATCHED_FIELD_LABELS.items()
        if scores[field_name] is not None and scores[field_name] >= threshold
    ]


def _backfill_missing_published_signatures(settings: AppSettings) -> int:
    """Generate signatures for existing latest published module versions."""

    from app.db.module_similarity import (
        list_missing_published_module_versions,
        upsert_module_similarity_signatures,
    )
    from app.db.modules import get_module_detail

    pending_signatures: list[tuple[int, ModuleSimilaritySignature]] = []
    for module_id, module_version_id, version_no in (
        list_missing_published_module_versions(settings)
    ):
        detail = get_module_detail(settings, module_id, version_no)
        if detail is None or detail.module_version_id != module_version_id:
            continue
        pending_signatures.append(
            (
                module_version_id,
                build_module_similarity_signature(detail),
            )
        )

    upsert_module_similarity_signatures(settings, pending_signatures)
    return len(pending_signatures)


def check_similar_modules(
    settings: AppSettings,
    incoming_module: ModuleCreateRequest,
) -> ModuleSimilarityCheckData:
    """Return latest published modules meeting the configured threshold."""

    from app.db.module_similarity import list_module_similarity_candidates

    incoming_signature = build_module_similarity_signature(incoming_module)
    _backfill_missing_published_signatures(settings)
    excluded_module_key = (
        incoming_module.module_key.strip().upper()
        if incoming_module.module_key and incoming_module.module_key.strip()
        else None
    )
    shortlisted = list_module_similarity_candidates(
        settings,
        incoming_signature,
        excluded_module_key,
        settings.module_similarity_candidate_limit,
    )

    matches: list[ModuleSimilarityCandidateData] = []
    for record in shortlisted:
        calculation = calculate_module_similarity(
            incoming_signature,
            record.signature,
        )
        if calculation.similarity < settings.module_similarity_threshold:
            continue
        matches.append(
            ModuleSimilarityCandidateData(
                module_id=record.module_id,
                module_key=record.module_key,
                module_name=record.module_name,
                module_version_id=record.module_version_id,
                version_no=record.version_no,
                version_label=record.version_label,
                status="published",
                similarity=calculation.similarity,
                exact_match=calculation.exact_match,
                image_metadata_match=calculation.image_metadata_match,
                score_breakdown=calculation.score_breakdown,
                matched_fields=_matched_field_labels(
                    calculation,
                    settings.module_similarity_threshold,
                ),
            )
        )

    matches.sort(
        key=lambda item: (
            not item.exact_match,
            -item.similarity,
            item.module_key,
        )
    )
    candidate_set_sha256 = _candidate_set_sha256(matches)
    confirmation_token = (
        issue_similarity_confirmation_token(
            settings,
            incoming_signature.exact_sha256,
            candidate_set_sha256,
        )
        if matches
        else None
    )
    result_candidates = matches[: settings.module_similarity_result_limit]
    return ModuleSimilarityCheckData(
        threshold=settings.module_similarity_threshold,
        checked_count=len(shortlisted),
        candidate_count=len(matches),
        exact_match=any(item.exact_match for item in matches),
        input_sha256=incoming_signature.exact_sha256,
        candidate_set_sha256=candidate_set_sha256,
        confirmation_token=confirmation_token,
        candidates=result_candidates,
    )
