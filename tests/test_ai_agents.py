from decimal import Decimal

from models import Product
from models.utils import ProductStatus
from services.ai_agents import run_agent
from services.lookup_service import get_lookup


def test_agents_use_deterministic_fallback_without_api_key(session, monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    product = Product(
        name="Oak desk", price=Decimal("100.00"), quantity=4,
        description="Solid oak office desk",
        product_status_record=get_lookup(session, ProductStatus, "AVAILABLE"),
    )
    session.add(product)
    session.commit()

    result = run_agent("product_discovery", "Find an oak desk", session)

    assert result["agent"] == "product_discovery"
    assert result["model"] == "deterministic-fallback"
    assert "Oak desk" in result["answer"]
    assert result["data_summary"]["catalogue_products"] == 1
