from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from settings import get_db
from schemas.order_schema import OrderCreate, OrderStatusUpdate, OrderOut
from services import order_service
from core.security import get_current_user_optional, get_current_user, get_current_admin

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    user_id = current_user.private_id if current_user else None
    try:
        order = order_service.create_order(
            product_id=payload.product_id,
            quantity=payload.quantity,
            address=payload.address,
            contact=payload.contact,
            payment_method=payload.payment_method or "BANK",
            session=db,
            user_id=user_id,
        )
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


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
    else:
        return order_service.get_user_orders(user_id=current_user.private_id, session=db)


@router.get("/{order_id}", response_model=OrderOut)
def get_order_by_id(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    order = order_service.get_order(order_id, db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order #{order_id} not found",
        )

    if current_user:
        is_admin = bool(current_user.role and current_user.role.name.upper() == "ADMIN")
        if order.user_id and order.user_id != current_user.private_id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot view orders placed by other users",
            )
    return order


@router.patch("/{order_id}/status", response_model=OrderOut, dependencies=[Depends(get_current_admin)])
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    updated = order_service.update_order(order_id, updates, db)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order #{order_id} not found",
        )
    return updated


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    success = order_service.delete_order(order_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order #{order_id} not found",
        )
