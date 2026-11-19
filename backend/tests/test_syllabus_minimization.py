import pytest

from src.modules.syllabus.minimization import minimize, minimize_with_count


def test_counts_replacements_without_counting_existing_placeholders():
    text = "Primeiro [email removido], depois pessoa@example.test e outro@example.test."
    cleaned, count = minimize_with_count(text)
    assert cleaned == "Primeiro [email removido], depois [email removido] e [email removido]."
    assert count == 2
    assert minimize_with_count(cleaned) == (cleaned, 0)
