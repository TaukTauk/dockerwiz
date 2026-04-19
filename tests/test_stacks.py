"""Tests for stacks.py."""

from dockerwiz.stacks import STACKS, frameworks_for_language, get_stack


def test_all_stacks_present():
    combos = {(s.language, s.framework) for s in STACKS}
    assert ("python", "fastapi") in combos
    assert ("python", "django") in combos
    assert ("go", "gin") in combos
    assert ("go", "echo") in combos
    assert ("node", "express") in combos
    assert ("node", "nestjs") in combos


def test_get_stack():
    stack = get_stack("python", "fastapi")
    assert stack is not None
    assert stack.default_port == 8000
    assert stack.image_key == "python"


def test_get_stack_missing():
    assert get_stack("ruby", "rails") is None


def test_frameworks_for_language():
    python_fw = frameworks_for_language("python")
    assert len(python_fw) == 2
    frameworks = {s.framework for s in python_fw}
    assert frameworks == {"fastapi", "django"}
