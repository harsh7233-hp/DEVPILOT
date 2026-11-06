import React from "react";
import { format } from "date-fns";
import { calculateTotal } from "./math";

const TAX_RATE = 0.08;

function formatPrice(amount) {
  return "$" + amount.toFixed(2);
}

async function loadOrder(id) {
  const response = await fetch("/api/orders/" + id);
  return response.json();
}

class OrderProcessor {
  constructor(orderId) {
    this.orderId = orderId;
  }

  async process() {
    const order = await loadOrder(this.orderId);
    const total = calculateTotal(order.items);
    return formatPrice(total * (1 + TAX_RATE));
  }
}

export { formatPrice, OrderProcessor };
export default loadOrder;
