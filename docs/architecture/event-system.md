# Subsystem Architecture: Event & Synchronization System

NovelForge utilizes an event-driven architecture to keep frontend workspaces synchronized with background agent executions in real time.

## Central Domain Event Bus

The `DomainEventBus` (`backend/app/services/event_bus.py`) handles decoupling domain events from downstream execution.
- In-memory event routing.
- Thread-safe and asynchronous background execution.
- Safe execution handler prevents pipeline failures from crash-prone subscriber callbacks.

### Major Events

- `ParagraphUpdated`: Dispatched when a paragraph skeleton is edited or has prose updated.
- `StoryBibleRebuilt`: Dispatched after story bible aggregate compiles.
- `ProjectUpdated`: Dispatched on cycle execution changes, proposal additions, or question resolutions.

## Server-Sent Events (SSE)

Real-time UI refresh uses Server-Sent Events:
1. Endpoint `GET /api/projects/{projectId}/stream` opens a persistent event stream.
2. Changes inside backend services publish events to `project_event_service`.
3. The SSE publisher pushes events to connected browser clients.
4. The frontend Zustand store listens to events and selectively invalidates data, initiating a data refetch.
