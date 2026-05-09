// DEBUGRA_BUG:SHOP-06 — Cart stored in localStorage without user-scoping.
// The key "shop_cart" is shared across all users on this device. If User A adds
// items then logs out, and User B logs in, they will see User A's cart items.
// Fix would be to key by user ID: `shop_cart_${userId}`.

const CART_KEY = "shop_cart"; // Bug: should be `shop_cart_${userId}`

export interface LocalCartItem {
  productId: string;
  name: string;
  price: number;
  quantity: number;
}

export function getLocalCart(): LocalCartItem[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(CART_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function addToLocalCart(item: Omit<LocalCartItem, "quantity">): void {
  const cart = getLocalCart();
  const existing = cart.find((i) => i.productId === item.productId);
  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({ ...item, quantity: 1 });
  }
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
}

export function clearLocalCart(): void {
  // DEBUGRA_BUG:SHOP-06 — This is NOT called on logout; cart survives session end
  localStorage.removeItem(CART_KEY);
}

export function getLocalCartCount(): number {
  return getLocalCart().reduce((sum, i) => sum + i.quantity, 0);
}
