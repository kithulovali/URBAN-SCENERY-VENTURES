from decimal import Decimal

from models import Product
from models.utils import ProductStatus
from services.ai_service import smart_search_electronics, get_electronics_recommendations
from services.lookup_service import get_lookup


def test_ai_shopping_search_and_recommendations_exclude_out_of_stock(session):
    available = Product(
        name="Wireless headphones", price=Decimal("40.00"), quantity=2,
        product_status_record=get_lookup(session, ProductStatus, "AVAILABLE"),
    )
    empty = Product(
        name="Wireless headphones out of stock", price=Decimal("35.00"), quantity=0,
        product_status_record=get_lookup(session, ProductStatus, "EMPTY"),
    )
    session.add_all([available, empty])
    session.commit()

    search = smart_search_electronics(session, "wireless headphones")
    recommendations = get_electronics_recommendations(session, "wireless headphones")

    assert [p.id for p in search["matches"]] == [available.id]
    assert search["total_matches"] == 1
    assert [p.id for p in recommendations["recommendations"]] == [available.id]
