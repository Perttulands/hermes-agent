"""Hermes profiles must rely on shared skill roots, not bundled local copies."""

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            calls.add(func.id)
        elif isinstance(func, ast.Attribute):
            calls.add(func.attr)
    return calls


def test_profile_entrypoints_do_not_seed_bundled_skill_copies():
    """Create/update/kanban/dashboard flows must not populate profile-local skills."""
    production_entrypoints = [
        PROJECT_ROOT / "hermes_cli" / "main.py",
        PROJECT_ROOT / "hermes_cli" / "web_server.py",
        PROJECT_ROOT / "hermes_cli" / "kanban.py",
    ]

    for path in production_entrypoints:
        calls = _call_names(path)
        assert "seed_profile_skills" not in calls, path
        assert "sync_skills" not in calls, path
