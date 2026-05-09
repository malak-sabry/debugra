"use client";

import type { RunEvent, RunEventType } from "@debugra/schemas";

const WS_BASE =
  typeof window !== "undefined"
    ? `ws://${window.location.hostname}:8000`
    : "ws://localhost:8000";

type EventHandler = (event: RunEvent) => void;

export class RunEventStream {
  private ws: WebSocket | null = null;
  private handlers: Map<RunEventType | "*", EventHandler[]> = new Map();
  private pingInterval: ReturnType<typeof setInterval> | null = null;

  constructor(private runId: string) {}

  connect(): this {
    const url = `${WS_BASE}/ws/runs/${this.runId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.pingInterval = setInterval(() => {
        this.ws?.send("ping");
      }, 20_000);
    };

    this.ws.onmessage = (ev) => {
      try {
        const event: RunEvent = JSON.parse(ev.data as string);
        this._dispatch("*", event);
        this._dispatch(event.type as RunEventType, event);
      } catch {
        // ignore parse errors
      }
    };

    this.ws.onclose = () => {
      if (this.pingInterval) clearInterval(this.pingInterval);
    };

    return this;
  }

  on(type: RunEventType | "*", handler: EventHandler): this {
    const existing = this.handlers.get(type) ?? [];
    this.handlers.set(type, [...existing, handler]);
    return this;
  }

  off(type: RunEventType | "*", handler: EventHandler): this {
    const existing = this.handlers.get(type) ?? [];
    this.handlers.set(
      type,
      existing.filter((h) => h !== handler)
    );
    return this;
  }

  disconnect(): void {
    if (this.pingInterval) clearInterval(this.pingInterval);
    this.ws?.close();
    this.ws = null;
  }

  private _dispatch(type: RunEventType | "*", event: RunEvent): void {
    (this.handlers.get(type) ?? []).forEach((h) => h(event));
  }
}
