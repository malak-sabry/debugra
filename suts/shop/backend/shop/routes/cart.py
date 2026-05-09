from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shop.db import CartItem, Product, User, get_session
from shop.routes.auth import require_user

router = APIRouter(tags=["cart"])


class AddToCartRequest(BaseModel):
    product_id: str
    quantity: int = 1


@router.get("")
async def get_cart(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user),
):
    result = await session.execute(
        select(CartItem).where(CartItem.user_id == current_user.id)
    )
    items = result.scalars().all()
    cart_items = []
    for item in items:
        product = await session.get(Product, item.product_id)
        if product:
            cart_items.append({
                "id": str(item.id),
                "product_id": str(item.product_id),
                "product_name": product.name,
                "unit_price": product.price,
                "quantity": item.quantity,
                "subtotal": product.price * item.quantity,
            })
    return {"items": cart_items, "total": sum(i["subtotal"] for i in cart_items)}


@router.post("", status_code=201)
async def add_to_cart(
    body: AddToCartRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user),
):
    product = await session.get(Product, UUID(body.product_id))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # DEBUGRA_BUG:SHOP-01 — Stock decremented twice on double-click (no idempotency key)
    existing = (await session.execute(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == UUID(body.product_id),
        )
    )).scalar_one_or_none()

    if existing:
        existing.quantity += body.quantity
    else:
        session.add(CartItem(
            user_id=current_user.id,
            product_id=UUID(body.product_id),
            quantity=body.quantity,
        ))

    await session.commit()
    return {"added": True}


@router.delete("/{item_id}", status_code=204)
async def remove_from_cart(
    item_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user),
):
    item = await session.get(CartItem, UUID(item_id))
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Cart item not found")
    await session.delete(item)
    await session.commit()


@router.delete("", status_code=204)
async def clear_cart(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user),
):
    result = await session.execute(
        select(CartItem).where(CartItem.user_id == current_user.id)
    )
    for item in result.scalars().all():
        await session.delete(item)
    await session.commit()
