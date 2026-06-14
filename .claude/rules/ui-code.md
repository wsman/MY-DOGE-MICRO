---
paths:
  - "src/ui/**"
  - "src/app/**"
  - "src/web/**"
---

# UI Code Rules

- UI must NEVER own or directly modify game state — display only, use commands/events to request changes
- All UI text must go through the localization system — no hardcoded user-facing strings
- Support both keyboard/mouse AND gamepad input for all interactive elements
- All animations must be skippable and respect user motion/accessibility preferences
- UI sounds trigger through the audio event system, not directly
- UI must never block the game thread
- Scalable text and colorblind modes are mandatory, not optional
- Test all screens at minimum and maximum supported resolutions
- Product UI must not own server/domain state directly — use typed commands, API clients, or service adapters.
- Product screens must document loading, empty, error, permission, offline, and partial-success states.
- Product forms and workflows must preserve user input on recoverable errors and expose actionable validation messages.
- Public user flows need interaction, component, or E2E evidence before story completion.
