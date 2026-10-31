from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from settings import get_db
from schemas.order_schema import OrderCreate, OrderStatusUpdate, OrderOut
from services import order_service
from services.request_limits import enforce_rate_limit
from core.security import get_current_user_optional, get_current_user, get_current_admin

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(
    payload: OrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    # Guest checkout remains available, but anonymous order creation is throttled.
    if current_user is None:
        enforce_rate_limit(request, "guest-order", limit=5, window_seconds=60)
    user_id = current_user.private_id if current_user else None
    try:
        return order_service.create_order(
            product_id=payload.product_id,
            quantity=payload.quantity,
            address=payload.address,
            contact=payload.contact,
            payment_method=payload.payment_method or "BANK",
            session=db,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=List[OrderOut])
def list_orders(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    is_admin = bool(current_user.role and current_user.role.name.upper() == "ADMIN")
    if is_admin:
        return order_service.get_all_orders(session=db, offset=offset, limit=limit)
    return order_service.get_user_orders(user_id=current_user.private_id, session=db)


@router.get("/{order_id}", response_model=OrderOut)
def get_order_by_id(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = order_service.get_order(order_id, db)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order #{order_id} not found")
    is_admin = str(getattr(getattr(current_user, "role", None), "name", "")).upper() == "ADMIN"
    if not is_admin and (order.user_id is None or order.user_id != current_user.private_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own orders")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut, dependencies=[Depends(get_current_admin)])
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    try:
        updated = order_service.update_order(order_id, payload.model_dump(exclude_unset=True), db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order #{order_id} not found")
    return updated


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    try:
        success = order_service.delete_order(order_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order #{order_id} not found")
