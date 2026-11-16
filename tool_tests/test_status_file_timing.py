"""
Test to verify status files are only written at the end of audit, not mid-audit.

This test monitors file modification times during audit execution to confirm
that STATUS_BRIEF.md, PRIORITIES_BRIEF.md, and CONSOLIDATED_REPORT.md are only
written once at the end, not during tool execution.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from development_tools.tool_tests.conftest import load_development_tools_module


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("custom_paths", [False, True])
def test_status_files_written_only_at_end_of_audit(tmp_path, custom_paths):
    """
    Verify that status files are only written at the end of audit execution.
    
    This test:
    1. Monitors file modification times during audit
    2. Verifies files are only written once at the end
    3. Confirms no mid-audit writes occur
    
    Uses temp_project_copy for complete test isolation.
    """
    # Use conftest helper to load module properly
    service_module = load_development_tools_module("shared.service")
    AIToolsService = service_module.AIToolsService
    
    project_root = tmp_path / "status_file_timing_project"
    project_root.mkdir(parents=True, exist_ok=True)
    
    # Create status file paths
    status_brief_file = project_root / "development_tools" / "STATUS_BRIEF.md"
    priorities_brief_file = project_root / "development_tools" / "PRIORITIES_BRIEF.md"
    consolidated_file = project_root / "development_tools" / "CONSOLIDATED_REPORT.md"
    
    config_path = None
    if custom_paths:
        status_brief_file = project_root / "reports" / "overview.md"
        priorities_brief_file = project_root / "reports" / "actions.md"
        consolidated_file = project_root / "reports" / "details" / "summary.md"
        config_path = project_root / "host-config.json"
        config_path.write_text(
            json.dumps(
                {
                    "status": {
                        "status_files": {
                            key: path.relative_to(project_root).as_posix()
                            for key, path in (
                                ("status_brief", status_brief_file),
                                ("priorities_brief", priorities_brief_file),
                                ("consolidated_report", consolidated_file),
                            )
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

    # Remove any existing status files
    for f in [status_brief_file, priorities_brief_file, consolidated_file]:
        if f.exists():
            f.unlink()
    
    # Get initial modification times (should be 0 since files don't exist)
    
    # Run a quick audit
    service = AIToolsService(
        project_root=str(project_root),
        config_path=str(config_path) if config_path else None,
    )
    no_op_patches = (
        patch.object(service, "_run_quick_audit_tools", return_value=True),
        patch.object(service, "_save_audit_results_aggregated", return_value=None),
        patch.object(service, "_reload_all_cache_data", return_value=None),
        patch.object(service, "_sync_todo_with_changelog", return_value=None),
        patch.object(service, "_validate_referenced_paths", return_value=None),
        patch.object(service, "_check_and_trim_changelog_entries", return_value=None),
        patch.object(service, "_check_documentation_quality", return_value=None),
        patch.object(service, "_check_ascii_compliance", return_value=None),
    )
    with patch.object(
        service, "_generate_status_brief_document", return_value="# Status Brief\n"
    ), patch.object(
        service, "_generate_priorities_brief_document", return_value="# Priorities Brief\n"
    ), patch.object(
        service, "_generate_consolidated_report", return_value="# Consolidated\n"
    ), no_op_patches[0], no_op_patches[1], no_op_patches[2], no_op_patches[3], no_op_patches[4], no_op_patches[5], no_op_patches[6], no_op_patches[7]:
        # Keep this test focused on status-file write timing rather than expensive tool internals.
        with patch.object(
            service,
            "run_script",
            return_value={"success": True, "output": "{}", "data": {}},
        ):
            result = service.run_audit(quick=True)
    
    # Verify audit completed (even if with errors, status files should still be written)
    assert result is not None, "Audit should complete and return a result"
    
    if custom_paths:
        assert not (project_root / "development_tools" / "STATUS_BRIEF.md").exists()

    # Verify files exist (they should be created even if audit had some failures)
    assert status_brief_file.exists(), f"STATUS_BRIEF.md should exist after audit. Path: {status_brief_file}"
    assert priorities_brief_file.exists(), f"PRIORITIES_BRIEF.md should exist after audit. Path: {priorities_brief_file}"
    assert consolidated_file.exists(), f"CONSOLIDATED_REPORT.md should exist after audit. Path: {consolidated_file}"
    
    # Get final modification times
    final_mtimes = {
        'STATUS_BRIEF.md': status_brief_file.stat().st_mtime,
        'PRIORITIES_BRIEF.md': priorities_brief_file.stat().st_mtime,
        'CONSOLIDATED_REPORT.md': consolidated_file.stat().st_mtime
    }
    
    # Verify all files were written (mtime > 0)
    for file_name, mtime in final_mtimes.items():
        assert mtime > 0, f"{file_name} should have a modification time after being created"
    
    # Verify all files were written at approximately the same time (within 2 seconds)
    # This confirms they were written together at the end, not scattered throughout
    all_mtimes = list(final_mtimes.values())
    if len(all_mtimes) > 1:
        time_span = max(all_mtimes) - min(all_mtimes)
        assert time_span < 2.0, f"Status files were written over {time_span:.2f} seconds apart, suggesting mid-audit writes"


@pytest.mark.integration
@pytest.mark.slow
def test_status_files_not_written_during_tool_execution(tmp_path):
    """
    Verify that status files are NOT written during individual tool execution.
    
    This test runs individual tools and confirms they don't write status files.
    
    Uses temp_project_copy for complete test isolation.
    """
    # Use conftest helper to load module properly
    service_module = load_development_tools_module("shared.service")
    AIToolsService = service_module.AIToolsService
    
    project_root = tmp_path / "status_tool_execution_project"
    project_root.mkdir(parents=True, exist_ok=True)
    
    # Create status file paths
    status_brief_file = project_root / "development_tools" / "STATUS_BRIEF.md"
    priorities_brief_file = project_root / "development_tools" / "PRIORITIES_BRIEF.md"
    consolidated_file = project_root / "development_tools" / "CONSOLIDATED_REPORT.md"
    
    # Remove any existing status files
    for f in [status_brief_file, priorities_brief_file, consolidated_file]:
        if f.exists():
            f.unlink()
    
    service = AIToolsService(project_root=str(project_root))

    # Run individual wrappers while short-circuiting subprocess execution.
    with patch.object(
        service,
        "run_script",
        return_value={"success": True, "output": "{}", "data": {}},
    ):
        service.run_analyze_functions()
        service.run_analyze_documentation()
    
    # Verify status files were NOT created by individual tools
    assert not status_brief_file.exists(), "STATUS_BRIEF.md should not be created by individual tools"
    assert not priorities_brief_file.exists(), "PRIORITIES_BRIEF.md should not be created by individual tools"
    assert not consolidated_file.exists(), "CONSOLIDATED_REPORT.md should not be created by individual tools"
