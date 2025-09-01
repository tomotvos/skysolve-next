# SkySolve UI — Product Requirements Document (PRD)

## Title
SkySolve Next — UI Redesign PRD

## Background / Context
SkySolve Next is a modernized replacement of the original SkySolve application. The web UI in the original project is dated and inconsistent. This PRD defines requirements for a responsive, accessible, Pi-friendly UI that prioritizes core SkySolve workflows: image solving and reporting solved coordinates to SkySafari/OnStep. The UI must work well both on desktop browsers and on iPhone (mobile-first).

## Goals (Primary)
1. Parity with SkySolve functionality: 
	* allow users to run a solve on a demo/uploaded image and view solved RA/Dec
	* ensure SkySafari tracking support (LX200 readonly outputs are provided by the backend on port 5002)
	* support configuration of solver and camera parameters
	* support "align" mode, where camera shows live view without solving
2. Fast, responsive UI that runs comfortably on Raspberry Pi-hosted backend. Prioritize low JS bundle size and server-side solving; client should be thin and efficient.
3. Mobile-first responsive design supporting iPhone Safari and desktop browsers. Provide an accessible Night Mode (muted red palette) for astronomy use.
4. Provide a developer-friendly prototype (Tailwind-based) and clear guidelines for integration into the existing project (FastAPI backend or equivalent).

## Out-of-scope (for initial release)
- Full Tetra integration UI workflows (this is backend work but UI should allow solver selection).
- Authentication and multi-user features (defer to later unless required).
- Camera live feed integration (Pi-specific; mock/upload flows for now).

## User personas
- Casual observer: wants an easy one-button solve and to see where the telescope is pointing on SkySafari.
- Enthusiast operator: wants solver selection, OnStep push control, and access to logs and advanced options.
- Developer / integrator: will integrate the UI with the SkySolve backend and deploy to Pi.

It is important to note that the casual/enthusiast personas are far more common. Typically, users will use the UI to set up SkySolve, and then operate in a "headless" mode from that point forward.

## Key user stories (must-have)
- As a user, I can upload a demo image or select a sample image and press **Solve** to get RA/Dec results.
- As a user, I can see the last solved coordinates and timestamp in a compact dashboard.
- As a user, I can toggle Night Mode (muted red palette) to reduce light impact while observing.
- As a user, I can enable OnStep and optionally push solves to OnStep (client behavior).
- As a user, I can open a SkySafari-compatible view showing current RA/Dec (read-only; the backend provides LX200 outputs on port 5002).
- As a user, I can see a live view of camera, without solving, to allow me to align the camera with the telescope eyepiece view.
- As a developer, I can drop the provided prototype into the repo's `web/prototype/` and the UI will call `/status` and `/solve` endpoints as documented.
- As a developer or enthusiast, I can create multiple solver and camera profiles to more easily tune operating parameters.

## Functional requirements
1. **Solve flow**
   - UI must provide "Upload image" and "Use demo image" options.
   - A big, prominent "Solve" button must be available and accessible on mobile (min touch target 44×44 px).
   - Show progress and result: RA, Dec, solve time, solver used, confidence. 
   - Provide "Push to OnStep" action when enabled.
   - Provide "Push to OnStep" checkbox to auto-push solves when enabled.
   - Provide a top-level toggle and default auto-on based on local time to turn main solver loop on/off.
2. **Status & history**
   - Display last solved coordinates, solved timestamp, and a small history list (last 10 solves) with compact metadata.
3. **Settings & advanced**
   - Solver selection (Astrometry/Tetra) — selection can be disabled if solver not installed (backend returns availability via `/status`).
   - OnStep host/port config and a toggle to enable/disable pushes.
   - Port settings info: default web port 5001, LX200 port 5002. Must be documented and overridable via env/config.
4. **Night Mode**
   - Provide a top-level toggle and default auto-on based on local time (configurable). Uses muted red palette, reduces blue light, maintains sufficient contrast.
5. **Accessibility**
   - Keyboard navigable, ARIA live announcements for solve completion, visible focus outlines, and proper contrast ratios.
6. **Performance & resilience**
   - Keep client payload under ~200 KB for Pi-hosted pages (minimize JS dependencies, use Tailwind JIT or CDN in prototype).
   - Use SSE or WebSocket for low-latency status updates when available; fallback to polling (2–5s) otherwise.

## Non-functional requirements
- Cross-browser: latest Safari (iPhone), Chrome, Firefox on desktop.
- Mobile-first responsive design; breakpoints at 640px (sm), 768px (md), 1024px (lg).
- Server compatibility: calls REST endpoints: `GET /status`, `POST /solve` (multipart/form-data image), `POST /onstep/push` (optional), and SSE at `/events` for status updates.
- Security: the UI will run in local networks by default; document firewall and port guidance in `docs/` (already present).

## Acceptance criteria (minimum)
- The prototype (Tailwind-based) renders correctly on desktop and iPhone Safari and supports Night Mode toggle.
- The prototype can call `/status` (and show mock data when backend is absent) and POST to `/solve` (mocked response) to display results.
- The UI must pass basic accessibility checks (keyboard navigation, ARIA live for solve completion, contrast for night mode).
- The developer can copy the prototype into the repo's `web/prototype/` directory and follow the README to connect to the backend endpoints.

## Wireframes & layout
- See `web/prototype/index.html` (provided). Mobile-first single primary view with header, main Solve area, and bottom action bar.
- Desktop: split view with preview/solve on the left and metadata/history/logs on the right.

## Metrics & telemetry (optional, privacy-aware)
- Optional opt-in telemetry for counts: solves started/completed, average solve time, onstep pushes. If enabled, document in README and make opt-in explicit.

## Dependencies & integrations
- Backend REST endpoints (FastAPI recommended) and LX200 server (port 5002) must be available and documented.
- Optional: SSE or WebSocket endpoint for real-time updates.
- Tailwind CSS (prototype uses Play CDN for quick development; production should use compiled Tailwind CSS).

## Risks & mitigations
- **Pi performance constraints**: mitigate by keeping JS minimal and server doing heavy lifting. Use server-side rendering for initial page if needed.
- **Night mode legibility**: test on multiple devices and with eyeglasses in real dark conditions.
- **Network connectivity**: use SSE or polling with backoff. Keep retry logic conservative to avoid overloading Pi.

## Rollout & acceptance plan
1. Add `web/prototype/` files into repo and sanity-check on desktop browsers.
2. Integrate with the backend test instance on macOS (point prototype to `http://localhost:5001` or configure `PROXY_BASE` as needed).
3. Deploy to Pi and test with real solver and SkySafari tracking (SkySafari pointed at LX200 port `5002`).
4. Conduct user acceptance test with 2-3 users and iterate on wording and layout.
5. Merge into main branch and create a lightweight release.

## Deliverables
- `web/prototype/index.html`, `web/prototype/README.md`, and supporting assets (Tailwind CDN usage).
- This PRD as a markdown file for repository inclusion: `docs/SKYSOLVE_UI_PRD.md`
