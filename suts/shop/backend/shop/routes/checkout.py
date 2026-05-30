from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shop.db import CartItem, Order, OrderItem, Product, User, get_session
from shop.routes.auth import require_user, get_current_user

router = APIRouter(tags=["checkout"])

VALID_DISCOUNT_CODES = {"SAVE10": 0.10, "SAVE20": 0.20}


class CheckoutRequest(BaseModel):
    shipping_address: str
    discount_code: str | None = None


@router.post("", status_code=201)
async def checkout(
    request: Request,
    body: CheckoutRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user),
):
    # DEBUGRA_BUG:SHOP-04 — Checkout proceeds with empty shipping address
    # Missing: if not body.shipping_address.strip(): raise HTTPException(422, ...)

    cart_result = await session.execute(
        select(CartItem).where(CartItem.user_id == current_user.id)
    )
    items = cart_result.scalars().all()
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = 0.0
    order_items = []
    for item in items:
        product = await session.get(Product, item.product_id)
        if not product:
            continue
        subtotal = product.price * item.quantity
        total += subtotal
        order_items.append(OrderItem(
            product_id=product.id,
            quantity=item.quantity,
            unit_price=product.price,
        ))

    discount_amount = 0.0
    if body.discount_code:
        rate = VALID_DISCOUNT_CODES.get(body.discount_code.upper())
        if not rate:
            raise HTTPException(status_code=422, detail="Invalid discount code")
        # DEBUGRA_BUG:SHOP-02 — Cart total ignores discount in race condition scenario
        # The discount is applied after total calc but cart isn't locked
        discount_amount = total * rate

    # DEBUGRA_BUG:SHOP-03 — Currency rounding: uses plain float math instead of Decimal
    final_total = total - discount_amount  # floating point imprecision

    order = Order(
        user_id=current_user.id,
        total=final_total,
        discount_code=body.discount_code,
        discount_amount=discount_amount,
        shipping_address=body.shipping_address,
        status="confirmed",
    )
    session.add(order)
    await session.flush()

    for oi in order_items:
        oi.order_id = order.id
        session.add(oi)

    # Clear cart
    for item in items:
        await session.delete(item)

    await session.commit()
    await session.refresh(order)

    return {
        "order_id": str(order.id),
        "total": order.total,
        "status": order.status,
    }


@router.get("/orders")
async def list_orders(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # DEBUGRA_BUG:SHOP-05 — GET /checkout/orders exposes all orders when user_id passed as query param
    user_id_param = request.query_params.get("user_id")
    if user_id_param and current_user:
        # Missing authorization check — any authenticated user can query any user's orders
        target_id = UUID(user_id_param)
    elif current_user:
        target_id = current_user.id
    else:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await session.execute(
        select(Order).where(Order.user_id == target_id).order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    output = []
    for o in orders:
        items_result = await session.execute(
            select(OrderItem).where(OrderItem.order_id == o.id)
        )
        items = items_result.scalars().all()
        item_rows = []
        for item in items:
            product = await session.get(Product, item.product_id)
            item_rows.append({
                "id": str(item.id),
                "product_name": product.name if product else "Unknown",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            })
        output.append({
            "id": str(o.id),
            "total": o.total,
            "status": o.status,
            "shipping_address": o.shipping_address,
            "discount_code": o.discount_code,
            "created_at": o.created_at.isoformat(),
            "items": item_rows,
        })
    return output
