"""Read-only, paginated cross-case comment search and API contracts."""

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.core.exceptions import DatabaseConnectionError
from app.core.responses import CaseDocCommentSearchData
from app.core.security import get_current_user
from app.db import case_doc_instances
from app.routers import case_docs
from test_case_doc_execution_comments import FakeCursor, install_fake_psycopg


def row(**changes):
    return {
        "execution_comment_id": 9, "case_document_id": 7, "case_document_key": "CASE-TEST-7",
        "case_name": "Test case", "source_doc_key": "BP-1", "source_doc_name": "Source",
        "execution_status": "completed", "group_start_row_order": 4, "item_label": "0.4.1",
        "comment_text": "response delay", "updated_by": "Test user",
        "updated_at": datetime(2026, 10, 22, 3, 15, tzinfo=timezone.utc), **changes,
    }


class SearchCursor(FakeCursor):
    def __init__(self, total=1, rows=None):
        super().__init__()
        self.total, self.rows = total, rows if rows is not None else [row()]

    def execute(self, query, params=None):
        normalized = " ".join(query.split())
        assert normalized.startswith("SELECT"), "Search must never initialize schema or write data"
        self.calls.append((normalized, params))
        self.result = [{"total_count": self.total}] if normalized.startswith("SELECT COUNT") else self.rows


def test_search_returns_durable_address_with_two_selects(test_settings, monkeypatch):
    cursor = SearchCursor()
    install_fake_psycopg(monkeypatch, cursor)
    result = case_doc_instances.search_case_doc_comments(test_settings)
    assert (result.total_count, result.page, result.total_pages) == (1, 1, 1)
    item = result.items[0]
    assert (item.case_document_id, item.group_start_row_order, item.item_label) == (7, 4, "0.4.1")
    assert item.updated_at == "2026-10-22T03:15:00+00:00"
    assert len(cursor.calls) == 2
    assert "c.comment_text ~ '[^[:space:]]'" in cursor.calls[0][0]
    assert "ORDER BY c.updated_at DESC, c.execution_comment_id DESC" in cursor.calls[1][0]
    assert cursor.calls[1][1]["limit"] == 20
    assert cursor.calls[1][1]["offset"] == 0


@pytest.mark.parametrize("value,expected", [("  delay  ", "%delay%"), ("50%_\\", "%50\\%\\_\\\\%"), ("' OR 1=1 --", "%' OR 1=1 --%")])
def test_keywords_are_bound_and_wildcards_are_literal(test_settings, monkeypatch, value, expected):
    cursor = SearchCursor()
    install_fake_psycopg(monkeypatch, cursor)
    case_doc_instances.search_case_doc_comments(test_settings, keyword=value, case_keyword=value)
    query, params = cursor.calls[0]
    assert params["comment_keyword"] == expected
    assert params["keyword"] == expected
    assert value not in query
    assert "c.comment_text ILIKE %(comment_keyword)s" in query
    assert "cd.case_document_key ILIKE %(keyword)s" in query


@pytest.mark.parametrize("status,sql", [
    ("all", None), ("completed", "cd.status = 'completed'"), ("active", "cd.status = 'active'"),
    ("not_started", "NOT EXISTS"), ("in_progress", "EXISTS"),
])
def test_status_filter_matches_case_list_semantics(test_settings, monkeypatch, status, sql):
    cursor = SearchCursor()
    install_fake_psycopg(monkeypatch, cursor)
    case_doc_instances.search_case_doc_comments(test_settings, execution_status=status)
    if sql:
        assert sql in cursor.calls[0][0]
    else:
        assert "cd.status =" not in cursor.calls[0][0]


@pytest.mark.parametrize("total,page,size,effective,offset,pages", [(43, 2, 20, 2, 20, 3), (43, 999, 20, 3, 40, 3), (0, 99, 20, 1, 0, 0)])
def test_pagination_is_bounded_and_empty_results_are_stable(test_settings, monkeypatch, total, page, size, effective, offset, pages):
    cursor = SearchCursor(total=total, rows=[])
    install_fake_psycopg(monkeypatch, cursor)
    result = case_doc_instances.search_case_doc_comments(test_settings, page=page, page_size=size)
    assert (result.page, result.total_pages, result.total_count) == (effective, pages, total)
    assert cursor.calls[1][1]["offset"] == offset


@pytest.mark.parametrize("arguments", [{"page": 0}, {"page_size": 0}, {"page_size": 101}, {"execution_status": "bad"}, {"keyword": "x" * 201}, {"case_keyword": "x" * 201}])
def test_invalid_inputs_are_rejected_before_database_access(test_settings, arguments):
    with pytest.raises(ValueError):
        case_doc_instances.search_case_doc_comments(test_settings, **arguments)


def test_database_failure_has_no_raw_database_details(test_settings, monkeypatch):
    class BrokenCursor(SearchCursor):
        def execute(self, *args):
            raise RuntimeError("private database details")
    install_fake_psycopg(monkeypatch, BrokenCursor())
    with pytest.raises(DatabaseConnectionError) as error:
        case_doc_instances.search_case_doc_comments(test_settings)
    assert "private database details" not in str(error.value)


def assert_authenticated_search(client, monkeypatch):
    seen = []
    def search(*args):
        seen.append(args)
        return CaseDocCommentSearchData(items=[], total_count=0, page=1, page_size=20, total_pages=0)
    monkeypatch.setattr(case_docs, "search_case_doc_comments", search)
    response = client.get("/api/v1/case-docs/comments?keyword=delay&case_keyword=CASE&execution_status=completed&page=2")
    assert response.status_code == 200
    assert seen[0][1:] == ("delay", "CASE", "completed", 2, 20)


def test_admin_can_search(client, monkeypatch):
    assert_authenticated_search(client, monkeypatch)


def test_member_and_approver_can_search(non_admin_client, monkeypatch):
    assert_authenticated_search(non_admin_client, monkeypatch)


@pytest.mark.parametrize("query", ["page=0", "page_size=101", "execution_status=bad", "keyword=" + "a" * 201, "case_keyword=" + "a" * 201])
def test_api_validates_query_parameters(client, monkeypatch, query):
    def unexpected(*args):
        raise AssertionError("Invalid query must not access the database")
    monkeypatch.setattr(case_docs, "search_case_doc_comments", unexpected)
    assert client.get("/api/v1/case-docs/comments?" + query).status_code == 400


def test_api_requires_authentication(client, monkeypatch):
    def denied():
        raise HTTPException(status_code=401, detail="Not authenticated")
    client.app.dependency_overrides[get_current_user] = denied
    assert client.get("/api/v1/case-docs/comments").status_code == 401
