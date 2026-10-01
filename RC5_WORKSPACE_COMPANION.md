# RC5 Workspace Companion

## Experience

The Companion is a persistent, quiet guide in the lower-right workspace corner. Its launcher communicates one useful headline without opening a notification wall. The expanded panel shows the current milestone, a bounded recap, and at most eight prioritized items.

The redesigned visual presence uses a compact gradient avatar and state-aware motion:

- **thinking:** gentle breathing while context loads;
- **working:** restrained illuminated pulse and rotating work indicator;
- **celebrating:** a short lift with bounded celebratory particles;
- **notifying:** a small attention indicator;
- **sleeping:** slow, low-contrast motion when there is nothing to do.

Animations stop under `prefers-reduced-motion`. The panel uses readable priority cards, a clear primary “Show me” action, and secondary Complete, Tomorrow, and Dismiss controls. It refreshes quietly every 30 seconds while the document is visible so completed background work can be reflected without spamming the author.

## Memory and recommendation lifecycle

Stable recommendation keys no longer include changing completeness fingerprints. Recommendation state is persisted as:

- active;
- dismissed;
- completed;
- snoozed;
- superseded.

Presentation count and cooldown state prevent continuous repetition. When a dependency changes or an action becomes complete, the old recommendation is completed or superseded before the next logical action is offered.

The Companion reuses Narrative Completeness, Story Health, Canon proposals, and background task state. It does not maintain a second story-analysis system.

## Interaction walkthrough

1. The launcher shows the highest-value current message.
2. The author opens the panel and sees milestone context and a short recap.
3. **Show me** navigates directly to the responsible workspace.
4. **Complete** records that the recommendation is handled.
5. **Tomorrow** snoozes it for 24 hours.
6. **Dismiss** removes it from the active lifecycle.
7. When no actionable item remains, the Companion sleeps and explicitly lets the author focus.

Visual proof: `artifacts/rc5-workspace-companion-desktop.png`.
## 2026-07-23 hardening update

The Companion now has a persistent left/right dock preference, an author-controlled animation toggle, and safe workspace padding at desktop widths. Its avatar has distinct thinking, working, notifying, celebrating, floating, and sleeping treatments while respecting reduced-motion preferences.

Feed refreshes consume cached Story Health and Narrative Completeness snapshots rather than recalculating the novel. Active Narrative Analysis and workflow jobs drive the working state. Opening the panel acknowledges the currently delivered feed even when the network response arrives after the panel opens; future messages remain unread. Stable recommendation identities, dismissal/completion/snooze state, cooldowns, and dependency-aware next actions prevent repeated prompting.

The panel exposes an `aria-live` status, keyboard-visible controls, author-language labels, direct **Show me** navigation, and a quiet caught-up state. A dedicated Playwright scenario verifies docking, remembered presentation state, read acknowledgement, navigation, overflow, console cleanliness, and all four desktop targets.

