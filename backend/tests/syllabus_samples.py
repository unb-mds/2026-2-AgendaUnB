"""PDFs sintéticos em memória. Nenhum plano real, dado pessoal ou credencial."""
import io
import json
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def cases():
    corpus = json.loads((Path(__file__).parent / "fixtures/syllabus/cases.json").read_text(encoding="utf-8"))
    for case in corpus:
        count = case.get("fill_lines", 0)
        if count:
            filler = "\n".join(f"Conteudo didatico {line}: conceitos, exemplos teoricos e orientacoes gerais de estudo."
                               for line in range(1, count + 1))
            case["pages"] = [page + "\n" + filler for page in case["pages"]]
    return corpus


def make_pdf(pages: list[str]) -> bytes:
    writer = PdfWriter()
    font = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"), NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    }))
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        lines = []
        for line in text.splitlines():
            # Somente corpus de teste confiável; preservar literalmente os trechos.
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            lines.append(f"({escaped}) Tj T*")
        stream = DecodedStreamObject()
        stream.set_data(("BT /F1 9 Tf 12 TL 25 755 Td " + "\n".join(lines) + " ET").encode("cp1252"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def pad_pdf(pdf: bytes, size: int) -> bytes:
    # A comment after the xref table keeps the original byte offsets valid.
    padding = b"%" + b"0" * (size - len(pdf) - 2) + b"\n"
    return pdf.replace(b"startxref\n", padding + b"startxref\n", 1)


def approved_source(text, page=1):
    """Autorização sintética explícita; nunca usada com documentos reais."""
    from datetime import datetime, timezone
    from src.modules.syllabus.preparation import text_hash
    pages = [{"pagina": page, "texto": text}]
    now = datetime.now(timezone.utc)
    return dict(prepared_pages=pages, approved_pages=pages, approved_hash=text_hash(pages),
                authorized_at=now, queued_at=now, text_revision=1)
