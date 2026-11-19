import pytest

from src.modules.syllabus.minimization import minimize, minimize_with_count


def test_counts_replacements_without_counting_existing_placeholders():
    text = "Primeiro [email removido], depois pessoa@example.test e outro@example.test."
    cleaned, count = minimize_with_count(text)
    assert cleaned == "Primeiro [email removido], depois [email removido] e [email removido]."
    assert count == 2
    assert minimize_with_count(cleaned) == (cleaned, 0)


@pytest.mark.parametrize("label", [
    "Professor(a):", "Docente:", "Monitor(a):", "Aluno(a):", "Discente:",
    "Coordenador(a):", "Prof.", "Profa.", "Dr.", "Dra.",
])
def test_masks_names_without_consuming_neighboring_fields(label):
    source = f"Disciplina: Estrutura de Dados 1 | {label} João da Silva | Prova 1"
    expected = f"Disciplina: Estrutura de Dados 1 | {label} [identificador removido] | Prova 1"
    assert minimize(source) == expected


def test_masks_name_in_running_text():
    assert minimize("Fale com a Profa. Ana Souza para confirmar a data.") == (
        "Fale com a Profa. [identificador removido] para confirmar a data."
    )


@pytest.mark.parametrize("separator", ["\t", "  ", ":\n", ":\r\n  ", " · "])
def test_masks_name_with_pdf_and_table_delimiters(separator):
    source = f"Monitor(a){separator}Álvaro D’Ávila\tSala 204"
    assert minimize(source) == f"Monitor(a){separator}[identificador removido]\tSala 204"


def test_masks_email_without_removing_wrappers_or_punctuation():
    assert minimize("Contato <ana+turma@dept.example.test>, Prova 1.") == (
        "Contato <[email removido]>, Prova 1."
    )


@pytest.mark.parametrize("value", [
    "+55 (61) 90000-0000", "(61) 3000-0000", "61 90000 0000", "61.90000.0000",
])
def test_masks_phone_with_ddd_in_running_text(value):
    assert minimize(f"Ligue para {value}, sala 204.") == "Ligue para [telefone removido], sala 204."


def test_masks_compact_whatsapp_when_labeled():
    assert minimize("WhatsApp: 61900000000 | Prova 1") == "WhatsApp: [telefone removido] | Prova 1"
