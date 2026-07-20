"""Le diagnostic IA (Claude) doit s'appuyer sur la prédiction du modèle ML local
au lieu de risquer de la contredire dans son explication technique."""
import sys
import types

import app as kronocolor_app


class _FakeTextBlock:
    def __init__(self, text):
        self.text = text


class _FakeMessage:
    def __init__(self, text):
        self.content = [_FakeTextBlock(text)]


def _install_fake_anthropic(monkeypatch, captured_prompts):
    fake_module = types.ModuleType("anthropic")

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = self

        def create(self, model, max_tokens, messages):
            captured_prompts.append(messages[0]["content"])
            return _FakeMessage("Réponse simulée de Claude.")

    fake_module.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)


def test_prompt_includes_ml_prediction_context(monkeypatch):
    captured = []
    _install_fake_anthropic(monkeypatch, captured)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")

    ml_prediction = {"finish": "Mat", "binder": "Silicate", "confidence": 82, "lightness_bucket": "moyen"}
    text, error = kronocolor_app.call_diagnostic_ai(
        [{"name": "Oxyde de Merzouga", "hex": "#9b3a2b", "pct": 100}],
        "#9b3a2b", "Mur extérieur", "Chaud & sec", ml_prediction,
    )

    assert error is None
    assert text == "Réponse simulée de Claude."
    assert len(captured) == 1
    prompt = captured[0]
    assert "Mat" in prompt
    assert "Silicate" in prompt
    assert "82%" in prompt
    assert "ne la contredis pas" in prompt


def test_prompt_omits_ml_context_block_when_no_prediction(monkeypatch):
    captured = []
    _install_fake_anthropic(monkeypatch, captured)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")

    kronocolor_app.call_diagnostic_ai(
        [{"name": "Oxyde de Merzouga", "hex": "#9b3a2b", "pct": 100}],
        "#9b3a2b", "Mur extérieur", "Chaud & sec", None,
    )
    assert "ne la contredis pas" not in captured[0]
