from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shop.db import create_tables
from shop.routes import auth, products, cart, checkout


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(title="Shop API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3002", "http://127.0.0.1:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(products.router, prefix="/api/products")
app.include_router(cart.router, prefix="/api/cart")
app.include_router(checkout.router, prefix="/api/checkout")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "shop-backend"}
