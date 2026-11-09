"""Subprocessos reais: provar prazo e limpeza, sem rede nem dados reais."""
import multiprocessing
import time
from dataclasses import replace

import pytest

from src.modules.syllabus.processing_config import ProcessingConfig, ProcessingError
from src.modules.syllabus.processing_task import run_isolated
from syllabus_samples import make_pdf


def stalled_parser(content, config):
    time.sleep(60)


class SyntheticStorage:
    def __init__(self, stage=None, reached=None):
        self.stage = stage
        self.reached = reached

    def download_file(self, path):
        if self.stage == "storage":
            self.reached.set()
            time.sleep(60)
        if self.stage == "parser":
            import src.modules.syllabus.processing_task as task
            task.extract_pages = stalled_parser
            self.reached.set()
        return make_pdf(["Plano sintetico, sem cronograma."])


class SyntheticProvider:
    def __init__(self, stage=None, reached=None):
        self.stage = stage
        self.reached = reached

    def extract(self, pages):
        if self.stage == "provider":
            self.reached.set()
            time.sleep(60)
        if self.stage == "exception":
            raise ValueError("PRIVATE_CONTENT_NOT_FOR_LOGS")
        return '{"candidatos": []}'


def test_isolated_success_returns_only_validated_results():
    output = run_isolated("sintetico.pdf", SyntheticStorage(), SyntheticProvider(), ProcessingConfig())
    assert output.page_count == 1
    assert output.extraction.candidates == []


@pytest.mark.parametrize("stage", ["storage", "parser", "provider"])
def test_entire_attempt_has_deadline_and_leaves_no_child(stage):
    context = multiprocessing.get_context("spawn")
    reached = context.Event()
    before = {child.pid for child in multiprocessing.active_children()}
    started = time.monotonic()
    config = replace(ProcessingConfig(), attempt_timeout_seconds=3)
    with pytest.raises(ProcessingError) as caught:
        run_isolated("sintetico.pdf", SyntheticStorage(stage, reached), SyntheticProvider(stage, reached), config)
    assert reached.is_set(), "O subprocesso precisa ter chegado à etapa que simula travamento"
    assert caught.value.code == "tempo_esgotado" and caught.value.retryable
    assert time.monotonic() - started < 6
    assert {child.pid for child in multiprocessing.active_children()} <= before


def test_child_exception_does_not_expose_document(capsys):
    with pytest.raises(ProcessingError) as caught:
        run_isolated("sintetico.pdf", SyntheticStorage(), SyntheticProvider("exception"), ProcessingConfig())
    assert caught.value.code == "erro_interno"
    assert "PRIVATE_CONTENT" not in str(caught.value) + str(capsys.readouterr())


def test_attempt_deadline_must_expire_before_lease():
    with pytest.raises(ValueError):
        replace(ProcessingConfig(), attempt_timeout_seconds=90)
