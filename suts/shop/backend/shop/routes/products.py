from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shop.db import Product, get_session

router = APIRouter(tags=["products"])


@router.get("")
async def list_products(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product))
    products = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "stock": p.stock,
            # DEBUGRA_BUG:SHOP-07 — Broken image URL: uses a non-existent path pattern
            "image_url": p.image_url or f"/images/product-{p.id}.jpg",
        }
        for p in products
    ]


@router.get("/{product_id}")
async def get_product(product_id: str, session: AsyncSession = Depends(get_session)):
    from uuid import UUID
    product = await session.get(Product, UUID(product_id))
    if not product:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found")
    return {
        "id": str(product.id),
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "image_url": product.image_url or f"/images/product-{product.id}.jpg",
    }
