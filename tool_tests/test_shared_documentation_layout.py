"""Regression coverage for shared documentation and relocated changelogs."""
from pathlib import Path

import pytest

from development_tools.docs.analyze_documentation_sync import DocumentationSyncChecker
from development_tools.docs import fix_version_sync


@pytest.mark.unit
@pytest.mark.parametrize("pairs, prose, has_drift", [
    ({}, "### 4.1. Shared documentation ownership\nNo pairs.\n", False),
    ({"GUIDE.md": "AI_GUIDE.md"}, "### 4.1. Shared documentation ownership\nNo pairs.\n", True),
    ({}, "### 4.1. Paired documentation files\n- GUIDE.md and AI_GUIDE.md\n", True),
])
def test_optional_pair_registration(tmp_path, pairs, prose, has_drift):
    """No-pair hosts pass; missing and stale registrations still fail."""
    (tmp_path / "DOCUMENTATION_GUIDE.md").write_text(prose, encoding="utf-8")
    checker = DocumentationSyncChecker(str(tmp_path))
    checker.paired_docs = pairs
    assert bool(checker.check_paired_docs_list_drift()) == has_drift


@pytest.mark.unit
@pytest.mark.parametrize("brief_path, archive_path", [("notes/RECENT.md", "history/OLD.md"), ("RECENT.md", "OLD.md")])
def test_configured_changelog_paths_drive_count_trim_and_todo(tmp_path, monkeypatch, brief_path, archive_path):
    """The configured brief/archive paths serve all changelog operations."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(fix_version_sync.VERSION_SYNC_CONFIG, "changelog_path", brief_path)
    monkeypatch.setitem(fix_version_sync.VERSION_SYNC_CONFIG, "changelog_archive_path", archive_path)
    brief = Path(brief_path)
    brief.parent.mkdir(exist_ok=True)
    brief.write_text("## Recent Changes (Most Recent First)\n\n### 2999-12-31 - Newer\n- new\n\n### 2999-12-30 - Older\n- old\n", encoding="utf-8")
    Path("TODO.md").write_text("# TODO\n- [x] Completed work\n", encoding="utf-8")
    assert fix_version_sync.check_changelog_entry_count(max_entries=1)["status"] == "fail"
    assert fix_version_sync.sync_todo_with_changelog()["completed_entries"] == 1
    result = fix_version_sync.trim_changelog_entries(max_entries=1)
    assert result["kept_entries"] == 1
    assert result["archive_path"] == archive_path
    assert "Older" in Path(archive_path).read_text(encoding="utf-8")
    assert "Older" not in brief.read_text(encoding="utf-8")
    assert not Path("ai_development_docs").exists()


@pytest.mark.unit
@pytest.mark.parametrize("path", ["DEVELOPMENT_WORKFLOW.md", "core/ERROR_HANDLING_GUIDE.md", "logs/LOGGING_GUIDE.md", "tests/TESTING_GUIDE.md"])
def test_shared_guide_review_links(path):
    """Shared guides at the root and in product folders remain clickable."""
    from development_tools.shared.service.report_generation_linkify import linkify_review_paths_bullet
    result = linkify_review_paths_bullet(f"Review for guidance: {path}")
    assert f"[{Path(path).name}](../{path})" in result
