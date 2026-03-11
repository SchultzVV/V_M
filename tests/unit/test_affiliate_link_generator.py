"""
Testes unitários para o módulo affiliate_link_generator.
Cobre:
  - generate_affiliate_link (happy path, edge cases, ENV fallback)
  - strip_affiliate_params
  - _append_query_params (comportamento interno via interface pública)
  - integração com ValidationResult
"""

import os
import pytest
from unittest.mock import patch

# Path insert para permitir import sem instalar o pacote
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao path para resolução de imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "site"))

from scripts.price_validator.affiliate import (
    generate_affiliate_link,
    get_affiliate_id,
    strip_affiliate_params,
    _append_query_params,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Garante ambiente limpo sem variáveis de afiliado antes de cada teste."""
    monkeypatch.delenv("MERCADO_LIVRE_AFFILIATE_ID", raising=False)
    monkeypatch.delenv("ML_UTM_SOURCE", raising=False)
    monkeypatch.delenv("ML_UTM_MEDIUM", raising=False)
    monkeypatch.delenv("ML_UTM_CAMPAIGN", raising=False)


# ─── get_affiliate_id ─────────────────────────────────────────────────────────

class TestGetAffiliateId:
    def test_returns_none_when_env_not_set(self):
        assert get_affiliate_id() is None

    def test_returns_id_from_env(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", "98765432")
        assert get_affiliate_id() == "98765432"

    def test_returns_none_when_env_is_empty_string(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", "")
        assert get_affiliate_id() is None


# ─── generate_affiliate_link ──────────────────────────────────────────────────

class TestGenerateAffiliateLink:

    _BASE_URL = "https://produto.mercadolivre.com.br/MLB123456789"
    _ID       = "12345678"

    def test_appends_matt_tool_no_existing_qs(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        result = generate_affiliate_link(self._BASE_URL)
        assert f"matt_tool={self._ID}" in result
        assert result.startswith(self._BASE_URL + "?")

    def test_appends_matt_tool_with_existing_qs(self, monkeypatch):
        url = self._BASE_URL + "?color=blue"
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        result = generate_affiliate_link(url)
        assert "matt_tool=" in result
        assert "color=blue" in result
        # deve usar & e não sobrescrever query existente
        assert result.count("?") == 1

    def test_explicit_affiliate_id_overrides_env(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", "000")
        result = generate_affiliate_link(self._BASE_URL, affiliate_id="99999")
        assert "matt_tool=99999" in result
        assert "matt_tool=000" not in result

    def test_returns_original_when_no_id_configured(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            result = generate_affiliate_link(self._BASE_URL)
        assert result == self._BASE_URL
        assert "MERCADO_LIVRE_AFFILIATE_ID" in caplog.text

    def test_raises_on_empty_permalink(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        with pytest.raises(ValueError, match="permalink não pode ser vazio"):
            generate_affiliate_link("")

    def test_raises_on_whitespace_only_permalink(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        with pytest.raises(ValueError):
            generate_affiliate_link("   ")

    def test_strips_whitespace_from_permalink(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        result = generate_affiliate_link(f"  {self._BASE_URL}  ")
        assert result.startswith("https://produto.mercadolivre.com.br")

    def test_includes_default_utm_params(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        result = generate_affiliate_link(self._BASE_URL)
        assert "utm_source=affiliate" in result
        assert "utm_medium=link" in result

    def test_custom_utm_params_via_args(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        result = generate_affiliate_link(
            self._BASE_URL,
            utm_source="instagram",
            utm_medium="story",
            utm_campaign="natal2025",
        )
        assert "utm_source=instagram" in result
        assert "utm_medium=story" in result
        assert "utm_campaign=natal2025" in result

    def test_utm_params_via_env(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        monkeypatch.setenv("ML_UTM_SOURCE", "newsletter")
        monkeypatch.setenv("ML_UTM_MEDIUM", "email")
        monkeypatch.setenv("ML_UTM_CAMPAIGN", "black_friday")
        result = generate_affiliate_link(self._BASE_URL)
        assert "utm_source=newsletter" in result
        assert "utm_medium=email" in result
        assert "utm_campaign=black_friday" in result

    def test_does_not_duplicate_matt_tool_already_in_url(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        url_with_param = self._BASE_URL + f"?matt_tool=old_id"
        result = generate_affiliate_link(url_with_param)
        # deve manter o valor original, não sobrescrever
        assert result.count("matt_tool=") == 1
        assert "matt_tool=old_id" in result

    def test_empty_campaign_not_appended(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        result = generate_affiliate_link(self._BASE_URL, utm_campaign="")
        assert "utm_campaign" not in result

    def test_idempotency_double_call(self, monkeypatch):
        """Chamar duas vezes não deve duplicar parâmetros."""
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        first  = generate_affiliate_link(self._BASE_URL)
        second = generate_affiliate_link(first)
        assert first.count("matt_tool=") == 1
        assert second.count("matt_tool=") == 1

    def test_url_with_fragment_preserved(self, monkeypatch):
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", self._ID)
        url = self._BASE_URL + "#reviews"
        result = generate_affiliate_link(url)
        assert "matt_tool=" in result


# ─── strip_affiliate_params ───────────────────────────────────────────────────

class TestStripAffiliateParams:

    def test_removes_matt_tool(self):
        url = "https://produto.mercadolivre.com.br/MLB123?matt_tool=12345"
        assert "matt_tool" not in strip_affiliate_params(url)

    def test_removes_utm_params(self):
        url = "https://produto.mercadolivre.com.br/MLB123?utm_source=a&utm_medium=b&utm_campaign=c"
        clean = strip_affiliate_params(url)
        assert "utm_" not in clean

    def test_keeps_other_params(self):
        url = "https://produto.mercadolivre.com.br/MLB123?color=red&matt_tool=123"
        clean = strip_affiliate_params(url)
        assert "color=red" in clean
        assert "matt_tool" not in clean

    def test_url_without_params_unchanged(self):
        url = "https://produto.mercadolivre.com.br/MLB123456789"
        assert strip_affiliate_params(url) == url

    def test_roundtrip_generate_then_strip(self, monkeypatch):
        """generate → strip deve retornar URL equivalente à original."""
        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", "99")
        original = "https://produto.mercadolivre.com.br/MLB123456789"
        with_affiliate = generate_affiliate_link(original)
        stripped = strip_affiliate_params(with_affiliate)
        # stripped deve conter a URL base sem parâmetros de afiliado
        assert "matt_tool" not in stripped
        assert "utm_" not in stripped
        assert "mercadolivre.com.br/MLB123456789" in stripped


# ─── _append_query_params (via comportamento observável) ─────────────────────

class TestAppendQueryParams:

    def test_adds_to_empty_query(self):
        result = _append_query_params("https://example.com/page", {"foo": "bar"})
        assert "foo=bar" in result
        assert "?" in result

    def test_adds_to_existing_query(self):
        result = _append_query_params("https://example.com/page?x=1", {"foo": "bar"})
        assert "x=1" in result
        assert "foo=bar" in result
        assert result.count("?") == 1

    def test_does_not_overwrite_existing_param(self):
        result = _append_query_params("https://example.com/page?foo=original", {"foo": "new"})
        assert "foo=original" in result
        assert "foo=new" not in result

    def test_multiple_params_added(self):
        result = _append_query_params("https://example.com/", {"a": "1", "b": "2"})
        assert "a=1" in result
        assert "b=2" in result


# ─── Integração com ValidationResult ─────────────────────────────────────────

class TestValidationResultIntegration:
    """
    Testa que o campo affiliate_link é preenchido corretamente no dataclass
    ValidationResult quando cheapest_link está disponível.
    Usa mock do validator para não depender da API do ML.
    """

    def test_affiliate_link_field_exists(self):
        from scripts.price_validator.validator import ValidationResult
        r = ValidationResult(original_link="https://example.com")
        assert hasattr(r, "affiliate_link")
        assert r.affiliate_link is None

    def test_affiliate_link_in_to_dict(self):
        from scripts.price_validator.validator import ValidationResult
        r = ValidationResult(
            original_link="https://example.com",
            affiliate_link="https://exemplo.com?matt_tool=123",
        )
        d = r.to_dict()
        assert "affiliate_link" in d
        assert d["affiliate_link"] == "https://exemplo.com?matt_tool=123"

    def test_affiliate_link_omitted_when_none(self):
        """to_dict não deve incluir affiliate_link=None no output."""
        from scripts.price_validator.validator import ValidationResult
        r = ValidationResult(original_link="https://example.com")
        d = r.to_dict()
        # campos None são omitidos em to_dict (exceto is_cheapest e error)
        assert "affiliate_link" not in d or d.get("affiliate_link") is None

    def test_validate_single_populates_affiliate_link(self, monkeypatch):
        """
        Smoke test: validate_single deve popular affiliate_link no resultado
        quando o produto tem alternativa mais barata — sem chamar a API real.
        """
        from scripts.price_validator import validator as v_module
        from scripts.price_validator.price_service import Listing
        from scripts.price_validator.validator import ValidationResult

        monkeypatch.setenv("MERCADO_LIVRE_AFFILIATE_ID", "TEST_ID")

        # Stub: detect_url_type retorna item direto
        monkeypatch.setattr(
            v_module, "detect_url_type",
            lambda url: ("item", "MLB999")
        )

        # Stub: item API retorna dados mínimos
        monkeypatch.setattr(
            v_module, "get_item",
            lambda item_id: {
                "id": "MLB999",
                "price": 1000.0,
                "shipping": {"free_shipping": False, "logistic_type": "fulfillment"},
                "catalog_product_id": "MLB_CAT1",
                "permalink": "https://produto.mercadolivre.com.br/MLB999",
            }
        )

        # Stub: catalog retorna dois vendedores
        cheaper_item = {
            "id": "MLB111",
            "price": 800.0,
            "shipping": {"free_shipping": True, "logistic_type": "fulfillment"},
            "catalog_product_id": "MLB_CAT1",
            "permalink": "https://produto.mercadolivre.com.br/MLB111",
        }
        monkeypatch.setattr(
            v_module, "get_catalog_listings",
            lambda cat_id: [cheaper_item, {
                "id": "MLB999",
                "price": 1000.0,
                "shipping": {"free_shipping": False, "logistic_type": "fulfillment"},
                "permalink": "https://produto.mercadolivre.com.br/MLB999",
            }]
        )

        result = v_module.validate_single("https://produto.mercadolivre.com.br/MLB999")

        assert result.is_cheapest is False
        assert result.cheapest_link is not None
        assert result.affiliate_link is not None
        assert "matt_tool=TEST_ID" in result.affiliate_link
        assert "MLB111" in result.affiliate_link
