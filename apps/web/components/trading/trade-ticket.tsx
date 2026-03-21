"use client";

import { FormEvent, useMemo, useState } from "react";

type Side = "buy" | "sell";
type OrderType = "market" | "limit";
type TimeInForce = "day" | "gtc" | "ioc" | "fok";

interface TradeTicketProps {
  defaultSymbol?: string;
}

interface TicketResponse {
  order?: {
    order_id: string;
    status: string;
    symbol: string;
    side: string;
    quantity: number;
  };
  error?: string;
  detail?: string;
}

export function TradeTicket({ defaultSymbol = "BTCUSDT" }: TradeTicketProps) {
  const [symbol, setSymbol] = useState(defaultSymbol);
  const [side, setSide] = useState<Side>("buy");
  const [orderType, setOrderType] = useState<OrderType>("limit");
  const [quantity, setQuantity] = useState("0.01");
  const [limitPrice, setLimitPrice] = useState("");
  const [timeInForce, setTimeInForce] = useState<TimeInForce>("day");
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<string>("");
  const [error, setError] = useState<string>("");

  const normalizedSymbol = useMemo(() => symbol.trim().toUpperCase(), [symbol]);
  const quantityNumber = useMemo(() => Number(quantity), [quantity]);
  const limitPriceNumber = useMemo(() => Number(limitPrice), [limitPrice]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (isSubmitting) return;
    setError("");
    setResult("");

    if (!normalizedSymbol) {
      setError("Symbol is required.");
      return;
    }
    if (!Number.isFinite(quantityNumber) || quantityNumber <= 0) {
      setError("Quantity must be greater than zero.");
      return;
    }
    if (orderType === "limit" && (!Number.isFinite(limitPriceNumber) || limitPriceNumber <= 0)) {
      setError("Limit price must be set for limit orders.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch("/api/execution/orders", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          symbol: normalizedSymbol,
          side,
          order_type: orderType,
          quantity: quantityNumber,
          limit_price: orderType === "limit" ? limitPriceNumber : null,
          time_in_force: timeInForce,
          note: note.trim(),
        }),
      });
      const payload = (await response.json().catch(() => ({}))) as TicketResponse;
      if (!response.ok) {
        setError(payload.error ?? payload.detail ?? `Order submission failed (${response.status}).`);
        return;
      }
      setResult(
        payload.order
          ? `Accepted ${payload.order.order_id} · ${payload.order.side.toUpperCase()} ${payload.order.quantity} ${payload.order.symbol} · ${payload.order.status}`
          : "Order submitted.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Order submission failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <article className="table-container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <h3 style={{ margin: 0 }}>Trade Ticket (Paper Router)</h3>
        <span className="status-chip status-chip-diagnostic_only">paper-only write path</span>
      </div>
      <p style={{ margin: "8px 0 14px", color: "var(--muted)" }}>
        Submissions flow through API contracts and require operator/admin auth for write actions.
      </p>

      <form onSubmit={onSubmit} style={{ display: "grid", gap: 10 }}>
        <div className="ticket-grid">
          <label>
            <span>Symbol</span>
            <input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="BTCUSDT" />
          </label>
          <label>
            <span>Side</span>
            <select value={side} onChange={(event) => setSide(event.target.value as Side)}>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </label>
          <label>
            <span>Order Type</span>
            <select value={orderType} onChange={(event) => setOrderType(event.target.value as OrderType)}>
              <option value="limit">Limit</option>
              <option value="market">Market</option>
            </select>
          </label>
          <label>
            <span>Qty</span>
            <input value={quantity} onChange={(event) => setQuantity(event.target.value)} inputMode="decimal" />
          </label>
          <label>
            <span>TIF</span>
            <select value={timeInForce} onChange={(event) => setTimeInForce(event.target.value as TimeInForce)}>
              <option value="day">DAY</option>
              <option value="gtc">GTC</option>
              <option value="ioc">IOC</option>
              <option value="fok">FOK</option>
            </select>
          </label>
          <label>
            <span>Limit Price</span>
            <input
              value={limitPrice}
              onChange={(event) => setLimitPrice(event.target.value)}
              inputMode="decimal"
              placeholder={orderType === "market" ? "n/a" : "required"}
              disabled={orderType === "market"}
            />
          </label>
        </div>
        <label>
          <span>Note</span>
          <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="strategy / rationale" />
        </label>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Submitting..." : "Submit Order"}
          </button>
          {result ? <span style={{ color: "var(--ok)" }}>{result}</span> : null}
          {error ? <span style={{ color: "var(--bad)" }}>{error}</span> : null}
        </div>
      </form>
    </article>
  );
}
