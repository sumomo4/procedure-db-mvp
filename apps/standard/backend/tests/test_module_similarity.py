"""Tests for module similarity normalization and scoring."""

import pytest

from app.core.config import AppSettings
from app.core.responses import (
    ModuleCreateDeviceHeaderInput,
    ModuleCreateRequest,
    ModuleCreateRowDeviceEntryInput,
    ModuleCreateRowImageInput,
    ModuleCreateRowInput,
    ModuleSimilarityCheckData,
)
from app.db.module_similarity import ModuleSimilarityCandidateRecord
from app.services.module_similarity import (
    ModuleSimilarityWeights,
    build_module_similarity_signature,
    calculate_module_similarity,
    check_similar_modules,
    issue_similarity_confirmation_token,
    normalize_command_text,
    normalize_prose_text,
    validate_similarity_confirmation_token,
)


def build_module(
    *,
    module_key: str | None = None,
    module_name: str = "ログイン確認",
    work_text: str = "TeraTermを起動する",
    expected_result: str | None = "ログインできること",
    slot_1_command: str | None = "show tty",
    slot_2_command: str | None = "show config",
    source_path: str | None = "imports/source.xlsm",
    images: list[ModuleCreateRowImageInput] | None = None,
    with_devices: bool = True,
) -> ModuleCreateRequest:
    """Build a deterministic imported module payload."""

    return ModuleCreateRequest(
        module_key=module_key,
        module_name=module_name,
        source_xlsx_path=source_path,
        device_headers=(
            [
                ModuleCreateDeviceHeaderInput(
                    slot_no=1,
                    target_text="1",
                    target_device_text="SBC-01",
                ),
                ModuleCreateDeviceHeaderInput(
                    slot_no=2,
                    target_text="2",
                    target_device_text="SBC-02",
                ),
            ]
            if with_devices
            else []
        ),
        rows=[
            ModuleCreateRowInput(
                row_order=1,
                row_type="step",
                major_no="1",
                middle_no="1",
                minor_no="1",
                tech_doc_text="接続手順",
                work_text=work_text,
                indent_level=0,
                expected_result=expected_result,
                device_entries=(
                    [
                        ModuleCreateRowDeviceEntryInput(
                            slot_no=1,
                            p_text="#",
                            command_text=slot_1_command,
                        ),
                        ModuleCreateRowDeviceEntryInput(
                            slot_no=2,
                            p_text="#",
                            command_text=slot_2_command,
                        ),
                    ]
                    if with_devices
                    else []
                ),
                images=images or [],
            )
        ],
    )


def test_normalize_prose_text_unifies_width_case_and_whitespace() -> None:
    """Prose normalization should absorb display-only differences."""

    assert normalize_prose_text("  ＴｅｒａＴｅｒｍ　を\r\n起動  ") == "teraterm を 起動"


def test_normalize_command_text_preserves_case_and_line_order() -> None:
    """Command normalization should not case-fold executable text."""

    assert normalize_command_text("  Show　TTY\r\n  Set   Value  ") == "Show TTY\nSet Value"


def test_signature_ignores_module_identity_and_source_path() -> None:
    """Duplicate content should share a hash even when import metadata differs."""

    first = build_module(module_key="MOD-001", source_path="imports/a.xlsm")
    second = build_module(module_key="MOD-999", source_path="imports/b.xlsm")

    first_signature = build_module_similarity_signature(first)
    second_signature = build_module_similarity_signature(second)

    assert first_signature.exact_sha256 == second_signature.exact_sha256
    assert first_signature.combined_text == second_signature.combined_text


def test_identical_modules_have_full_similarity() -> None:
    """Identical procedure content should produce a complete match."""

    signature = build_module_similarity_signature(build_module())

    result = calculate_module_similarity(signature, signature)

    assert result.similarity == 1.0
    assert result.exact_match is True
    assert result.image_metadata_match is True


def test_second_device_command_difference_changes_command_score() -> None:
    """Commands from every device slot must participate in scoring."""

    before = build_module_similarity_signature(
        build_module(slot_2_command="show config")
    )
    after = build_module_similarity_signature(
        build_module(slot_2_command="delete config")
    )

    result = calculate_module_similarity(before, after)

    assert "slot:2" in before.normalized_command_text
    assert result.score_breakdown.command is not None
    assert result.score_breakdown.command < 1.0
    assert result.similarity < 1.0
    assert result.exact_match is False


def test_components_blank_on_both_sides_do_not_inflate_score() -> None:
    """Blank optional components should be removed from the weight denominator."""

    before = build_module_similarity_signature(
        build_module(
            module_name="完全に異なる名前A",
            work_text="作業A",
            expected_result=None,
            slot_1_command=None,
            slot_2_command=None,
            with_devices=False,
        )
    )
    after = build_module_similarity_signature(
        build_module(
            module_name="別の名前B",
            work_text="別作業B",
            expected_result=None,
            slot_1_command=None,
            slot_2_command=None,
            with_devices=False,
        )
    )

    result = calculate_module_similarity(before, after)

    assert result.score_breakdown.expected_result is None
    assert result.score_breakdown.command is None
    assert result.applied_weight < 1.0
    assert result.similarity < 0.70


def test_image_metadata_changes_exact_match_but_not_weighted_text_score() -> None:
    """Images are supplemental in the PoC and excluded from weighted scoring."""

    before = build_module_similarity_signature(
        build_module(
            images=[
                ModuleCreateRowImageInput(
                    image_key="before",
                    image_path="before.png",
                    anchor_cell="E12",
                    width_px=200,
                    height_px=100,
                )
            ]
        )
    )
    after = build_module_similarity_signature(
        build_module(
            images=[
                ModuleCreateRowImageInput(
                    image_key="after",
                    image_path="after.png",
                    anchor_cell="I12",
                    width_px=200,
                    height_px=100,
                )
            ]
        )
    )

    result = calculate_module_similarity(before, after)

    assert result.similarity == 1.0
    assert result.exact_match is False
    assert result.image_metadata_match is False
    assert before.image_count == 1
    assert after.image_count == 1


def test_command_case_difference_is_detected() -> None:
    """Command letter case should remain meaningful."""

    before = build_module_similarity_signature(
        build_module(slot_1_command="Show TTY")
    )
    after = build_module_similarity_signature(
        build_module(slot_1_command="show tty")
    )

    result = calculate_module_similarity(before, after)

    assert result.score_breakdown.command is not None
    assert result.score_breakdown.command < 1.0


def test_weights_must_total_one() -> None:
    """Invalid custom weights should fail before returning a misleading score."""

    signature = build_module_similarity_signature(build_module())

    with pytest.raises(ValueError, match="重み合計"):
        calculate_module_similarity(
            signature,
            signature,
            ModuleSimilarityWeights(work_text=0.50),
        )


def test_check_similar_modules_returns_only_threshold_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The orchestrator should shortlist, score, sort, and limit candidates."""

    from app.db import module_similarity as similarity_db

    incoming = build_module(module_key="MOD-NEW")
    identical_signature = build_module_similarity_signature(
        build_module(module_key="MOD-001")
    )
    unrelated_signature = build_module_similarity_signature(
        build_module(
            module_key="MOD-002",
            module_name="バックアップ削除",
            work_text="保存済みバックアップを削除する",
            expected_result="バックアップが存在しないこと",
            slot_1_command="delete backup",
            slot_2_command="remove archive",
        )
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        similarity_db,
        "list_missing_published_module_versions",
        lambda _settings: [],
    )
    monkeypatch.setattr(
        similarity_db,
        "upsert_module_similarity_signatures",
        lambda _settings, signatures: captured.update(
            {"upserted": signatures}
        ),
    )

    def fake_list_candidates(
        _settings: AppSettings,
        _incoming_signature: object,
        excluded_module_key: str | None,
        limit: int,
    ) -> list[ModuleSimilarityCandidateRecord]:
        captured["excluded_module_key"] = excluded_module_key
        captured["limit"] = limit
        return [
            ModuleSimilarityCandidateRecord(
                module_id=1,
                module_key="MOD-001",
                module_name="ログイン確認",
                module_version_id=10,
                version_no=2,
                version_major=1,
                version_minor=0,
                status="published",
                signature=identical_signature,
                shortlist_similarity=1.0,
            ),
            ModuleSimilarityCandidateRecord(
                module_id=2,
                module_key="MOD-002",
                module_name="バックアップ削除",
                module_version_id=20,
                version_no=1,
                version_major=1,
                version_minor=0,
                status="published",
                signature=unrelated_signature,
                shortlist_similarity=0.1,
            ),
        ]

    monkeypatch.setattr(
        similarity_db,
        "list_module_similarity_candidates",
        fake_list_candidates,
    )

    result = check_similar_modules(
        AppSettings(
            module_similarity_threshold=0.70,
            module_similarity_candidate_limit=50,
            module_similarity_result_limit=10,
        ),
        incoming,
    )

    assert result.checked_count == 2
    assert result.candidate_count == 1
    assert result.exact_match is True
    assert [item.module_key for item in result.candidates] == ["MOD-001"]
    assert result.candidates[0].similarity == 1.0
    assert len(result.candidate_set_sha256) == 64
    assert result.confirmation_token is not None
    assert validate_similarity_confirmation_token(
        AppSettings(
            module_similarity_threshold=0.70,
            module_similarity_candidate_limit=50,
            module_similarity_result_limit=10,
        ),
        result,
        result.confirmation_token,
    )
    assert captured["excluded_module_key"] == "MOD-NEW"
    assert captured["limit"] == 50
    assert captured["upserted"] == []


def test_similarity_confirmation_token_rejects_tampering_and_expiry() -> None:
    """Confirmation tokens should be bound to the checked content and lifetime."""

    settings = AppSettings(
        module_similarity_confirmation_secret="unit-test-confirmation-secret",
        module_similarity_confirmation_ttl_seconds=120,
    )
    result = ModuleSimilarityCheckData(
        threshold=0.70,
        checked_count=1,
        candidate_count=1,
        exact_match=False,
        input_sha256="a" * 64,
        candidate_set_sha256="b" * 64,
        candidates=[],
    )
    token = issue_similarity_confirmation_token(
        settings,
        result.input_sha256,
        result.candidate_set_sha256,
        now_epoch=100,
    )

    assert validate_similarity_confirmation_token(
        settings,
        result,
        token,
        now_epoch=219,
    )
    assert not validate_similarity_confirmation_token(
        settings,
        result,
        f"{token}x",
        now_epoch=150,
    )
    assert not validate_similarity_confirmation_token(
        settings,
        result,
        token,
        now_epoch=221,
    )


def test_similarity_confirmation_token_rejects_changed_input_or_candidates() -> None:
    """A token must not confirm different Excel content or a changed candidate set."""

    settings = AppSettings(
        module_similarity_confirmation_secret="unit-test-confirmation-secret",
        module_similarity_confirmation_ttl_seconds=120,
    )
    original = ModuleSimilarityCheckData(
        threshold=0.70,
        checked_count=1,
        candidate_count=1,
        exact_match=False,
        input_sha256="a" * 64,
        candidate_set_sha256="b" * 64,
        candidates=[],
    )
    token = issue_similarity_confirmation_token(
        settings,
        original.input_sha256,
        original.candidate_set_sha256,
        now_epoch=100,
    )

    changed_input = original.model_copy(update={"input_sha256": "c" * 64})
    changed_candidates = original.model_copy(
        update={"candidate_set_sha256": "d" * 64}
    )

    assert not validate_similarity_confirmation_token(
        settings,
        changed_input,
        token,
        now_epoch=150,
    )
    assert not validate_similarity_confirmation_token(
        settings,
        changed_candidates,
        token,
        now_epoch=150,
    )
