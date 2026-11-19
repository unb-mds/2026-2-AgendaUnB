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


@pytest.mark.parametrize(("field", "expected"), [
    ("CPF: 00000000000", "CPF: [identificador removido]"),
    ("000.000.000-00", "[identificador removido]"),
    ("R.G. nº: 12.345.678-X", "R.G. nº: [identificador removido]"),
    ("RG 1234567", "RG [identificador removido]"),
])
def test_masks_identity_documents_without_touching_academic_numbers(field, expected):
    assert minimize(f"{field} | Código 123456789 | Turma 01") == f"{expected} | Código 123456789 | Turma 01"


@pytest.mark.parametrize(("field", "expected"), [
    ("Matrícula UnB: 260000000", "Matrícula UnB: [identificador removido]"),
    ("Matrícula: 26/0000000", "Matrícula: [identificador removido]"),
    ("26 / 0000000", "[identificador removido]"),
    ("SIAPE: 1234567", "SIAPE: [identificador removido]"),
])
def test_masks_institutional_person_identifiers(field, expected):
    assert minimize(f"Período 2026/2 | {field} | CIC0004") == f"Período 2026/2 | {expected} | CIC0004"


@pytest.mark.parametrize("date", ["01/02/1990", "1990-02-01", "1.2.90", "1 de março de 1990"])
def test_masks_birth_date_only_in_personal_context(date):
    assert minimize(f"Data de nascimento: {date} | Avaliação em {date}") == (
        f"Data de nascimento: [identificador removido] | Avaliação em {date}"
    )


def test_masks_personal_links_and_preserves_institutional_links():
    source = ("Lattes https://lattes.cnpq.br/0000000000000000; www.linkedin.com/in/pessoa-exemplo. "
              "Site pessoal: https://pessoa.example.test/card | https://unb.br/disciplinas")
    assert minimize(source) == (
        "Lattes [identificador removido]; [identificador removido]. "
        "Site pessoal: [identificador removido] | https://unb.br/disciplinas"
    )


def test_counts_link_with_embedded_contact_once():
    cleaned, count = minimize_with_count("WhatsApp https://api.whatsapp.com/send?phone=5561900000000")
    assert cleaned == "WhatsApp [telefone removido]"
    assert count == 1


@pytest.mark.parametrize(("source", "expected"), [
    ("Endereço residencial: Rua Exemplo, 123 | Sala 204", "Endereço residencial: [identificador removido] | Sala 204"),
    ("Mora em Rua Exemplo, apto 2. Prova 1", "Mora em [identificador removido]. Prova 1"),
    ("Endereço: Campus Darcy Ribeiro, Bloco B", "Endereço: Campus Darcy Ribeiro, Bloco B"),
])
def test_masks_residential_address_and_preserves_academic_address(source, expected):
    assert minimize(source) == expected
    assert minimize_with_count(expected) == (expected, 0)


@pytest.mark.parametrize(("source", "expected"), [
    ("Professor(a) responsável: Prof. João Silva", "Professor(a) responsável: Prof. [identificador removido]"),
    ("Docente: joão da silva | Cálculo II", "Docente: [identificador removido] | Cálculo II"),
    ("Professores João Silva", "Professores [identificador removido]"),
    ("Professor de Matemática", "Professor de Matemática"),
])
def test_handles_role_variants_and_lowercase_structured_names(source, expected):
    assert minimize(source) == expected


def test_masks_table_row_with_pipe_delimiter_and_name_initial():
    assert minimize("| Monitor(a) | Ana P. Silva | Sala 204 |") == (
        "| Monitor(a) | [identificador removido] | Sala 204 |"
    )


def test_masks_professor_with_full_role_in_running_text():
    assert minimize("Consulte a professora Ana Silva antes da prova.") == (
        "Consulte a professora [identificador removido] antes da prova."
    )


def test_masks_dotted_rg_without_optional_digit():
    assert minimize("| RG | 12.345.678 | Prova 1") == "| RG | [identificador removido] | Prova 1"


@pytest.mark.parametrize("academic", [
    "Estrutura de Dados 1", "Matemática Discreta 2", "Cálculo Diferencial e Integral II",
    "CIC0004", "Turma 01", "2026.2", "2026/2", "Código 123456789",
    "Prova 1", "P1", "Trabalho Final", "20/11/2026", "20-11-26", "20.11.2026",
    "20 de novembro de 2026", "2026-11-20", "2026-11-20T14:30-03:00", "14:30",
    "das 08h00 às 10h00", "Sala 204", "Auditório Central", "Bloco B",
])
def test_preserves_academic_fields_exactly_alongside_personal_data(academic):
    source = f"{academic}\t| E-mail: pessoa@example.test |\t{academic}"
    expected = f"{academic}\t| E-mail: [email removido] |\t{academic}"
    assert minimize_with_count(source) == (expected, 1)
    assert minimize_with_count(expected) == (expected, 0)
