from decimal import Decimal

from models import Product
from models.utils import ProductStatus
from services.ai_agents import run_agent, _collect_context
from services.lookup_service import get_lookup
from services.order_service import create_order, update_order


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


def test_business_intelligence_separates_cancelled_and_paid_order_value(session):
    available_status = get_lookup(session, ProductStatus, "AVAILABLE")
    product = Product(
        name="Analytics test product",
        price=Decimal("50.00"),
        quantity=10,
        product_status_record=available_status,
    )
    session.add(product)
    session.commit()

    create_order(
        product_id=product.id, quantity=1, address="Test address",
        contact="0700000000", session=session,
    )
    cancelled_order = create_order(
        product_id=product.id, quantity=1, address="Test address",
        contact="0700000000", session=session,
    )
    paid_order = create_order(
        product_id=product.id, quantity=1, address="Test address",
        contact="0700000000", session=session,
    )

    update_order(cancelled_order.id, {"order_status": "CANCELLED"}, session)
    update_order(paid_order.id, {"payment_status": "PAID"}, session)

    summary = _collect_context(session)["summary"]

    assert summary["orders_loaded"] == 3
    assert summary["order_value_loaded"] == 150.0
    assert summary["non_cancelled_order_value_loaded"] == 100.0
    assert summary["cancelled_order_value_loaded"] == 50.0
    assert summary["order_value_marked_paid_loaded"] == 50.0
    assert summary["order_status_counts"]["CANCELLED"] == 1
    assert summary["payment_status_counts"]["PAID"] == 1
    assert "not verified revenue" in summary["data_note"]


def test_non_bi_agent_context_excludes_order_records(session, monkeypatch):
    import services.ai_agents as ai_agents

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    original_collect_context = ai_agents._collect_context
    calls = []

    def capture_context(db, include_orders=True):
        calls.append(include_orders)
        return original_collect_context(db, include_orders=include_orders)

    monkeypatch.setattr(ai_agents, "_collect_context", capture_context)
    result = ai_agents.run_agent("product_discovery", "Find a desk", session)

    assert calls == [False]
    assert result["data_summary"]["orders_loaded"] == 0
