from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from models.products_model import Product
from models.utils import ProductStatus


# Common electronics synonyms and spec keywords
KEYWORD_MAPPINGS = {
    "phone": ["smartphone", "mobile", "iphone", "android", "galaxy"],
    "laptop": ["notebook", "macbook", "pc", "computer", "thinkpad", "ultrabook"],
    "audio": ["headphone", "earphone", "earbud", "speaker", "bluetooth", "sound"],
    "gaming": ["gpu", "rgb", "console", "playstation", "xbox", "controller"],
    "screen": ["monitor", "display", "tv", "4k", "oled"],
    "accessory": ["charger", "cable", "case", "adapter", "powerbank"],
}


def get_electronics_recommendations(
    session: Session,
    query: str,
    max_budget: Optional[Decimal] = None,
    preferred_category: Optional[str] = None,
) -> Dict[str, Any]:
    query_lower = query.lower()
    
    # 1. Fetch available products
    statement = select(Product).join(Product.product_status_record).where(ProductStatus.name == "AVAILABLE")
    if max_budget:
        statement = statement.where(Product.price <= max_budget)
    
    all_products = list(session.scalars(statement).all())
    
    # 2. Score products based on query keywords and specs
    scored_products = []
    expanded_terms = set(query_lower.split())
    for category, synonyms in KEYWORD_MAPPINGS.items():
        if category in query_lower or any(s in query_lower for s in synonyms):
            expanded_terms.add(category)
            expanded_terms.update(synonyms)
            
    if preferred_category:
        expanded_terms.add(preferred_category.lower())

    for prod in all_products:
        prod_text = f"{prod.name} {prod.description or ''}".lower()
        score = sum(2 for term in expanded_terms if term in prod_text)
        
        # Budget adherence bonus
        if max_budget and Decimal(str(prod.price)) <= max_budget:
            score += 1
            
        if score > 0:
            scored_products.append((score, prod))

    # Sort descending by score, or fallback to cheapest/top products
    scored_products.sort(key=lambda x: x[0], reverse=True)
    recommended = [p for _, p in scored_products[:5]]
    
    if not recommended and all_products:
        recommended = all_products[:3]

    advice = (
        f"Based on your requirements for '{query}'"
        + (f" with a budget under ${max_budget}" if max_budget else "")
        + f", we matched {len(recommended)} top electronics option(s) with high performance and value."
    )

    return {
        "query": query,
        "ai_advice": advice,
        "recommendations": recommended,
    }


def smart_search_electronics(
    session: Session,
    query: str,
) -> Dict[str, Any]:
    query_lower = query.strip().lower()
    statement = select(Product)
    
    search_terms = query_lower.split()
    clauses = []
    for term in search_terms:
        term_filter = f"%{term}%"
        clauses.append(Product.name.ilike(term_filter))
        clauses.append(Product.description.ilike(term_filter))

    if clauses:
        statement = statement.where(or_(*clauses))

    matches = list(session.scalars(statement).all())
    return {
        "query": query,
        "total_matches": len(matches),
        "matches": matches,
    }
