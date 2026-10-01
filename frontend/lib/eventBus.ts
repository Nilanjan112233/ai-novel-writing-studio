type EventCallback = (payload: any) => void;

class EventBus {
  private listeners: Map<string, EventCallback[]> = new Map();

  /**
   * Subscribe to a specific domain event.
   * Returns an unsubscribe function.
   */
  subscribe(event: string, callback: EventCallback): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(callback);

    return () => {
      const callbacks = this.listeners.get(event);
      if (callbacks) {
        this.listeners.set(
          event,
          callbacks.filter((cb) => cb !== callback)
        );
      }
    };
  }

  /**
   * Publish a domain event to all registered listeners.
   */
  publish(event: string, payload: any): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach((cb) => {
        try {
          cb(payload);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }
  }
}

export const eventBus = new EventBus();
export default eventBus;
