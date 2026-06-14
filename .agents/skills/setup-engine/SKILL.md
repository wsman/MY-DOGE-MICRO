---
name: setup-engine
description: "Configure the project's technology foundation — game engine or general product stack. Pins the stack in AGENTS.md, detects knowledge gaps, and populates reference docs via WebSearch when versions are beyond the LLM's training data."
argument-hint: "[engine | framework | stack] [version] | refresh | upgrade [old-ver] [new-ver] | no args for guided selection"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, WebSearch, WebFetch, Task, AskUserQuestion
---

## User Guide

- When to use: Configure the project's technology foundation — game engine or general product stack. Pins the stack in AGENTS.md, detects knowledge gaps, and populates reference docs via WebSearch when versions are beyond the LLM's training data.
- Inputs: Command arguments: `/setup-engine [engine | framework | stack] [version] | refresh | upgrade [old-ver] [new-ver] | no args for guided selection`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: `memory_bank/t1_axioms/tech_context.md`.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

When this skill is invoked:

## 1. Parse Arguments

Five modes:

- **Full spec**: `/setup-engine godot 4.6` or `/setup-engine django 5.1` — stack and version provided
- **Stack only**: `/setup-engine unity` or `/setup-engine react` — stack provided, version will be looked up
- **No args**: `/setup-engine` — fully guided mode (domain detection, then recommendation + version)
- **Refresh**: `/setup-engine refresh` — update reference docs (see Section 10)
- **Upgrade**: `/setup-engine upgrade [old-ver] [new-ver]` — migrate to a new version (see Section 11)

**Domain detection.** The argument usually reveals the domain:
- **游戏专用 hints**: godot, unity, unreal, ue5, game engine → game mode
- **通用产品 hints**: python, django, fastapi, react, nextjs, node, rust, go, postgres, redis, docker → product mode
- **Ambiguous**: ask during guided mode

Sections below are marked **[通用场景]** (both domains), **[游戏专用]** (game-domain), or **[通用产品]** (product-domain).

---

## 2. Guided Mode (No Arguments)

If no stack is specified, run an interactive selection process.

### [通用场景] Check for existing concept

- **游戏专用**: Read `design/cdd/game-concept.md` if it exists — extract genre, scope, platform targets, art style, team size, and any engine recommendation from `/brainstorm`
- **通用产品**: Read `design/cdd/product-concept.md` if it exists — extract platform targets, stack preferences, performance needs, and any tech recommendation from `/brainstorm`. Also read `memory_bank/t1_axioms/tech_context.md` if it exists.

If no concept exists, inform the user:
- **游戏专用**: "No game concept found. Consider running `/brainstorm` first — it will recommend an engine."
- **通用产品**: "No product concept found. Consider running `/brainstorm` first — it will help identify stack requirements."

### [通用场景] Prior experience (ask first, always)

Use `AskUserQuestion`:
- Prompt: "Have you worked in any of these before?"

- **游戏专用** Options: `Godot` / `Unity` / `Unreal Engine 5` / `Multiple — I'll explain` / `None of them`
- **通用产品** Options: `Python (Django, FastAPI, Flask)` / `JavaScript/TypeScript (React, Next.js, Node)` / `Rust` / `Go` / `Multiple — I'll explain` / `None of them`

If they pick a specific stack → recommend it. Prior experience outweighs all other factors. Confirm with them and skip the matrix.

---

### [游戏专用] Engine Decision Matrix

Only if no prior engine experience. Ask in this order:

**Platform** (ask second, always — platform eliminates engines before any other factor):
- Prompt: "What platforms are you targeting?"
- Options: `PC (Steam/Epic)` / `Mobile (iOS/Android)` / `Console` / `Web` / `Multiple`
- Platform rules that feed directly into the recommendation:
  - Mobile → Unity strongly preferred; Unreal is a poor fit; Godot is viable for simple mobile
  - Console → Unity or Unreal; Godot console support requires third-party publishers or significant extra work
  - Web → Godot exports cleanly to web; Unity WebGL is functional; Unreal has poor web support
  - PC only → all engines viable; other factors decide
  - Multiple → Unity is the most portable across PC/mobile/console

1. **What kind of game?** (2D, 3D, or both?)
2. **Primary input method?** (keyboard/mouse, gamepad, touch, or mixed?)
3. **Team size and experience?** (solo beginner, solo experienced, small team?)
4. **Any strong language preferences?** (GDScript, C#, C++, visual scripting?)
5. **Budget for engine licensing?** (free only, or commercial licenses OK?)

**Engine honest tradeoffs** (identical to original):

**Godot 4**
- Genuine strengths: 2D (best in class), stylized/indie 3D, rapid iteration, free forever (MIT), open source, gentlest learning curve, best for solo devs who want full control
- Real limitations: 3D ecosystem is thin compared to Unity/Unreal (fewer tutorials, assets, community answers for 3D-specific problems); large open-world 3D is very hard and largely untested in Godot; console export requires third-party publishers or significant extra work; smaller professional job market
- Licensing reality: Truly free with no revenue thresholds ever. MIT license means you own everything.
- Best fit: 2D games of any scope; stylized/atmospheric 3D; contained 3D worlds (not open-world); first game projects where learning curve matters; projects where budget is a hard constraint at any scale

**Unity**
- Genuine strengths: Industry standard for mid-scope 3D and mobile; massive asset store and tutorial ecosystem; C# is a professional language; best console certification support for indie; strong community for almost every genre
- Real limitations: Licensing controversy in 2023 damaged trust (runtime fee was proposed then walked back — the risk of policy changes remains real); C# has a steeper initial curve than GDScript; heavier editor than Godot for simple projects
- Licensing reality: Free under $200K revenue AND 200K installs (Unity Personal/Plus). Only becomes costly if the game is genuinely successful — most indie games never hit this threshold. The 2023 controversy is worth knowing about but the actual current terms are reasonable for most indie developers.
- Best fit: Mobile games; mid-scope 3D; games targeting console; developers with C# background; projects needing large asset store; teams of 2-5

**Unreal Engine 5**
- Genuine strengths: Best-in-class 3D visuals (Lumen, Nanite, Chaos physics); industry standard for AAA and photorealistic 3D; large open-world support is mature and production-tested; Blueprint visual scripting lowers C++ barrier; strong for games targeting high-end PC or console
- Real limitations: Steepest learning curve; heaviest editor (slow compile times, large project sizes); overkill for stylized/2D/small-scope games; C++ is genuinely hard; not suitable for mobile or web; 5% royalty past $1M gross revenue
- Licensing reality: 5% royalty only applies AFTER $1M gross revenue per title. For a first game or any game that doesn't reach $1M, it costs nothing. This threshold is high enough that most indie developers will never pay it.
- Best fit: AAA-quality 3D; large open-world games; photorealistic visuals; developers with C++ experience or willing to use Blueprint; games targeting high-end PC/console where visual fidelity is a core selling point

**Genre-specific guidance** (factor this into the recommendation):
- 2D any style → Godot strongly preferred
- 3D stylized / atmospheric / contained world → Godot viable, Unity solid alternative
- 3D open world (large, seamless) → Unity or Unreal; Godot is not production-proven for this
- 3D photorealistic / AAA-quality → Unreal
- Mobile-first → Unity strongly preferred
- Console-first → Unity or Unreal; Godot console support requires extra work
- Horror / narrative / walking sim → any engine; match to art style and team experience
- Action RPG / Soulslike → Unity or Unreal for 3D; community support and assets matter here
- Platformer 2D → Godot
- Strategy / top-down / RTS → Godot or Unity depending on 2D vs 3D

**Recommendation format:**
1. Show a comparison table with the user's specific factors as rows
2. Give a primary recommendation with honest reasoning
3. Name the best alternative and when to choose it instead
4. Explicitly state: "This is a starting point, not a verdict — you can always migrate engines, and many developers switch between projects."
5. Use `AskUserQuestion` to confirm: "Does this recommendation feel right, or would you like to explore a different engine?"
   - Options: `[Primary engine] (Recommended)` / `[Alternative engine]` / `[Third engine]` / `Explore further` / `Type something`

**If the user picks "Explore further":**
Use `AskUserQuestion` with concept-specific deep-dive topics. Always generate these options from the user's actual concept — do not use generic options. Always include at minimum:
- The primary engine's specific limitations for this concept (e.g., "How far can Godot 3D actually go for [genre]?")
- The alternative engine's specific tradeoffs for this concept
- Language choice impact on this concept's technical challenges
- Any concept-specific technical concern (e.g., adaptive audio, open-world streaming, multiplayer netcode)

The user can select multiple topics. Answer each selected topic in depth before returning to the engine confirmation question.

---

### [通用产品] Stack Decision Matrix

Only if no prior stack experience. Ask in this order:

**Platform** (ask second, always — platform eliminates or heavily weights stacks before any other factor):
- Prompt: "What platforms are you targeting?"
- Options: `Web (browser)` / `Desktop (Windows/macOS/Linux)` / `Mobile (iOS/Android)` / `CLI / Server` / `Multiple platforms`
- Platform rules that feed directly into the recommendation:
  - Web → JS/TS ecosystem most mature for frontend; Python (Django/Flask) strong for server-rendered; Rust/Wasm viable for performance-critical browser workloads
  - Mobile → React Native or Flutter for cross-platform; Swift/Kotlin for native; PWA for simple mobile web
  - Desktop → Electron (JS) for rapid cross-platform; Tauri (Rust) for lightweight; native (Swift/C#/C++) for single-platform
  - CLI → Python, Go, or Rust depending on performance needs and distribution model (single binary vs pip install)
  - Server → Python, Go, Rust, or Node depending on throughput, concurrency model, and ecosystem needs
  - Multiple → JS/TS with React/React Native covers web+mobile; Go or Rust for CLI+server portability

**Question 3 — Project type** (ask this third):
- Prompt: "What kind of project is this?"
- Options: `Web app / SaaS` / `REST API / Backend` / `CLI tool` / `Desktop app` / `Mobile app` / `Data pipeline / ETL` / `AI/ML product` / `Library / SDK`

**Question 4 — Performance needs** (ask this fourth):
- Prompt: "What are the performance requirements?"
- Options: `Not a concern — developer speed matters more` / `Moderate — responsive is enough` / `High — low latency or high throughput` / `Critical — every millisecond counts`

**Question 5 — Team size and experience** (ask this fifth):
- Prompt: "What's your team setup?"
- Options: `Solo developer` / `Small team (2-5)` / `Medium team (6-20)` / `Large team (20+)`
- Team notes: Solo/small → prioritize ecosystem maturity and iteration speed. Medium+ → can invest in Rust/Go for performance-critical paths. Large → hiring pool and onboarding matter.

**Question 6 — Language preferences** (ask this sixth):
- Prompt: "Any strong language preferences or aversions?"
- Options: `Prefer dynamically typed (Python, JS)` / `Prefer statically typed (TypeScript, Rust, Go)` / `No preference` / `I'll describe`
- Reality notes: If the user hates async patterns, Python's asyncio may frustrate them. If they love type safety, Rust or TypeScript will feel more natural.

**Question 7 — Budget and licensing** (ask this seventh):
- Prompt: "Any licensing or cost constraints?"
- Options: `Free / open-source only` / `Commercial OK but prefer free` / `No constraints`

**Ecosystem honest tradeoffs:**

**Python (Django / FastAPI / Flask)**
- Strengths: Fastest iteration speed, massive library coverage (web, data, AI/ML), gentle learning curve, huge community
- Limitations: Slower runtime, GIL limits CPU concurrency, async story fragmented, dynamic typing
- Performance reality: Fast enough for 90% of products. Instagram/Spotify/Dropbox run on Python.
- Best fit: APIs, web backends, data tools, AI/ML, internal tools, rapid prototyping

**JavaScript/TypeScript (React / Next.js / Node)**
- Strengths: One language full-stack, best web UI ecosystem, Vercel/Netlify near-zero ops, TypeScript type safety, React Native extends to mobile
- Limitations: NPM churn, bundler/config complexity, Node overhead vs compiled languages
- Performance reality: Node fast for I/O-bound work. Not for CPU-bound. V8 JIT excellent for web workloads.
- Best fit: Web apps, SaaS, interactive UIs, real-time features, full-stack products

**Rust**
- Strengths: Best-in-class performance+safety, zero-cost abstractions, excellent CLI/Wasm, Cargo, fearless concurrency, single binary
- Limitations: Steepest learning curve, slower iteration (compile times), smaller web ecosystem, smaller hiring pool
- Performance reality: Right choice when performance is a hard requirement. Overkill for CRUD APIs.
- Best fit: Performance-critical systems, CLIs, Wasm, infrastructure, network services

**Go**
- Strengths: Simple language, excellent concurrency, fast compile, single binary, first-class cloud-native (K8s, Docker, Terraform)
- Limitations: Verbose error handling, limited generics, smaller web framework ecosystem
- Performance reality: Sweet spot between Python's speed and Rust's performance. Excellent for networked services.
- Best fit: Cloud services, APIs, CLIs, DevOps tooling, microservices, infrastructure

**Project type guidance**: Web app→JS/TS UI + Python/Go/TS backend; REST API→Python(FastAPI)/Go/Rust; CLI→Go/Rust; Desktop→Electron(JS)/Tauri(Rust); Mobile→React Native/Flutter; Data/ETL→Python; AI/ML→Python; Library→match target audience ecosystem

### [通用产品] Framework Sub-Selection

Once ecosystem is determined, narrow to a specific framework. This mirrors Godot's GDScript vs C# language selection — the ecosystem is the engine, the framework is the dialect.

Use `AskUserQuestion` with options from the user's project type:

**Python**: `FastAPI (APIs, async)` / `Django (full-featured)` / `Flask (minimal)` / `Litestar (typed FastAPI alt)` / `No framework — pure Python`

**JS/TS**: `Next.js (full-stack React, SSR)` / `React + Vite (SPA)` / `Vue / Nuxt` / `Express / Fastify (backend only)` / `Node — no frontend framework`

**Rust**: `Axum (async, Tokio-native)` / `Actix Web (mature)` / `Rocket (ergonomic)` / `CLI only — clap + anyhow` / `Library — no framework`

**Go**: `stdlib + chi router (minimal)` / `Gin (popular)` / `Echo (high-perf)` / `Fiber (Express-like)` / `CLI only — cobra + viper`

Record the framework choice. It drives the AGENTS.md template, default dependencies, and agent routing.

**Recommendation format**: Same as game mode — comparison table, primary recommendation, alternative, confirmation via `AskUserQuestion`.

**If the user picks "Explore further":**
Use `AskUserQuestion` with concept-specific deep-dive topics. Always generate these options from the user's actual concept — do not use generic options. Always include at minimum:
- The primary stack's specific limitations for this project type (e.g., "How far can FastAPI scale for [use case]?")
- The alternative stack's specific tradeoffs for this concept
- Language choice impact on this concept's technical challenges
- Any concept-specific technical concern (e.g., real-time collaboration, offline support, data sync, multi-tenancy)

The user can select multiple topics. Answer each selected topic in depth before returning to the stack confirmation question.

---

## 3. Look Up Current Version

[通用场景] Once the stack is chosen:

- If version provided → use it
- If no version → WebSearch: `"[stack] latest stable version [current year]"`
- Confirm: "The latest stable [stack] is [version]. Use this?"

---

## 4. Update AGENTS.md Technology Stack

Read `AGENTS.md` and show the user the proposed Technology Stack changes.
Ask: "May I write these settings to `AGENTS.md`?"

Wait for confirmation before making any edits.

Update the Technology Stack section, replacing the `[CHOOSE]` placeholders with the actual values:

**[游戏专用]** Engine templates:

### Language Selection (Godot only)

If Godot was chosen, ask the user which language to use **before** showing the proposed Technology Stack:

> "Godot supports two primary languages:
>
>   **A) GDScript** — Python-like, Godot-native, fastest iteration. Best for beginners, solo devs, and teams coming from Python or Lua.
>   **B) C#** — .NET 8+, familiar to Unity developers, stronger IDE tooling (Rider / Visual Studio), slight performance advantage on heavy logic.
>   **C) Both** — GDScript for gameplay/UI scripting, C# for performance-critical systems. Advanced setup — requires .NET SDK alongside Godot.
>
> Which will this project primarily use?"

Record the choice. It determines the AGENTS.md template, naming conventions, specialist routing, and which agent is spawned for code files throughout the project.

**For Godot** — use the template matching the language chosen above. See **Appendix A** at the bottom of this skill for all three variants (GDScript, C#, Both).

**Unity:**
```markdown
- **Engine**: Unity [version]
- **Language**: C#
- **Build System**: Unity Build Pipeline
- **Asset Pipeline**: Unity Asset Import Pipeline + Addressables
```

**Unreal:**
```markdown
- **Engine**: Unreal Engine [version]
- **Language**: C++ (primary), Blueprint (gameplay prototyping)
- **Build System**: Unreal Build Tool (UBT)
- **Asset Pipeline**: Unreal Content Pipeline
```

**[通用产品]** Stack template:
```markdown
- **Language**: [Python / TypeScript / Rust / Go / ...] [version]
- **Framework**: [FastAPI / React / Django / ...] [version]
- **Runtime**: [CPython 3.12 / Node.js 22 / ...]
- **Database**: [PostgreSQL / SQLite / DuckDB / ...]
- **Build System**: [pip / npm / cargo / make / ...]
- **CI/CD**: [GitHub Actions / GitLab CI / ...]
```

---

## 5. Populate Technical Preferences

After updating AGENTS.md, create or update `standards/technical-preferences.md`.
Read the existing template first, then fill in.

### [通用场景] Language & Framework Section
Fill from the stack choice made in Section 2.

### [通用场景] Naming Conventions

**[游戏专用]** Engine defaults:

**Godot GDScript:**
- Classes: PascalCase (e.g., `PlayerController`)
- Variables/functions: snake_case (e.g., `move_speed`)
- Signals: snake_case past tense (e.g., `health_changed`)
- Files: snake_case matching class (e.g., `player_controller.gd`)
- Scenes: PascalCase matching root node (e.g., `PlayerController.tscn`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_HEALTH`)

**Godot C#:**
- Classes: PascalCase (`PlayerController`) — must also be `partial`
- Public properties/fields: PascalCase (`MoveSpeed`, `JumpVelocity`)
- Private fields: `_camelCase` (`_currentHealth`, `_isGrounded`)
- Methods: PascalCase (`TakeDamage()`, `GetCurrentHealth()`)
- Signal delegates: PascalCase + `EventHandler` suffix (`HealthChangedEventHandler`)
- Files: PascalCase matching class (`PlayerController.cs`)
- Scenes: PascalCase matching root node (`PlayerController.tscn`)
- Constants: PascalCase (`MaxHealth`, `DefaultMoveSpeed`)

**Godot Both — GDScript + C#:**
Use GDScript conventions for `.gd` files and C# conventions for `.cs` files. Mixed-language files do not exist — the boundary is per-file. When in doubt about which language a new system should use, ask the user and record the decision in `technical-preferences.md`.

**Unity (C#):**
- Classes: PascalCase (e.g., `PlayerController`)
- Public fields/properties: PascalCase (e.g., `MoveSpeed`)
- Private fields: _camelCase (e.g., `_moveSpeed`)
- Methods: PascalCase (e.g., `TakeDamage()`)
- Files: PascalCase matching class (e.g., `PlayerController.cs`)
- Constants: PascalCase or UPPER_SNAKE_CASE

**Unreal (C++):**
- Classes: Prefixed PascalCase (`A` for Actor, `U` for UObject, `F` for struct)
- Variables: PascalCase (e.g., `MoveSpeed`)
- Functions: PascalCase (e.g., `TakeDamage()`)
- Booleans: `b` prefix (e.g., `bIsAlive`)
- Files: Match class without prefix (e.g., `PlayerController.h`)

**[通用产品]** Language defaults:

**Python:**
- Classes: PascalCase (e.g., `UserService`, `OrderRepository`)
- Variables/functions: snake_case (e.g., `get_user_by_id`, `calculate_total`)
- Files/modules: snake_case (e.g., `user_service.py`, `order_repository.py`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`)
- Private members: `_leading_underscore` (e.g., `_cache`, `_db_pool`)

**TypeScript:**
- Classes/components: PascalCase (e.g., `UserProfile`, `DashboardView`)
- Variables/functions: camelCase (e.g., `fetchUserData`, `handleSubmit`)
- Files: kebab-case for components (e.g., `user-profile.tsx`), camelCase for utilities (e.g., `apiClient.ts`)
- Constants: UPPER_SNAKE_CASE for global (e.g., `API_BASE_URL`), camelCase for local
- Types/interfaces: PascalCase (e.g., `User`, `OrderStatus`), prefix with `I` only if team convention requires

**Rust:**
- Types/traits/enums: PascalCase (e.g., `UserRepository`, `ConnectionPool`)
- Variables/functions: snake_case (e.g., `get_user`, `handle_request`)
- Files/modules: snake_case (e.g., `user_repository.rs`, `connection_pool.rs`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_CONNECTIONS`, `DEFAULT_PORT`)
- Macros: snake_case or `macro_rules!` convention

**Go:**
- Exported: PascalCase (e.g., `UserService`, `GetUser`, `HTTPClient`)
- Unexported: camelCase (e.g., `userService`, `getUser`, `httpClient`)
- Files: snake_case or lowercase (e.g., `user_service.go`, `httpclient.go`)
- Constants: PascalCase if exported (e.g., `MaxRetries`), camelCase if not
- Acronyms: all-caps (e.g., `HTTPServer`, `userID`, `parseURL`)

### [通用场景] Platform & Configuration

**[游戏专用]** Input & Platform section.

Populate `## Input & Platform` using the answers gathered in Section 2 (or extracted from the game concept). Derive the values using this mapping:

| Platform target | Gamepad Support | Touch Support |
|-----------------|-----------------|---------------|
| PC only | Partial (recommended) | None |
| Console | Full | None |
| Mobile | None | Full |
| PC + Console | Full | None |
| PC + Mobile | Partial | Full |
| Web | Partial | Partial |

For **Primary Input**, use the dominant input for the game genre:
- Action/RPG/platformer targeting console → Gamepad
- Strategy/point-and-click/RTS → Keyboard/Mouse
- Mobile game → Touch
- Cross-platform → ask the user

Present the derived values and ask the user to confirm or adjust before writing.

Example filled section:
```markdown
## Input & Platform
- **Target Platforms**: PC, Console
- **Input Methods**: Keyboard/Mouse, Gamepad
- **Primary Input**: Gamepad
- **Gamepad Support**: Full
- **Touch Support**: None
- **Platform Notes**: All UI must support d-pad navigation. No hover-only interactions.
```

**[通用产品]** Platform & Deployment section.

Populate `## Platform & Deployment` using the platform answers from Section 2. Derive the values using this mapping:

| Platform target | Deployment strategy | Key concerns |
|-----------------|---------------------|-------------|
| Web | Vercel/Netlify (JS), Docker + cloud (Python/Go/Rust) | CDN, SSR/CSR, SEO, accessibility |
| Desktop | Electron-builder (JS), Tauri bundler (Rust) | Installer format, auto-update, OS compatibility |
| Mobile | App Store/Google Play, Expo (React Native) | Offline support, battery, push notifications |
| CLI | pip/npm/cargo/brew distribution | Single binary (Go/Rust), PATH installation |
| Server | Docker + Kubernetes, cloud-specific (ECS/Lambda/Cloud Run) | Scaling strategy, health checks, graceful shutdown |

Present the derived values and ask the user to confirm or adjust before writing.

Example filled section:
```markdown
## Platform & Deployment
- **Target Platforms**: Web, Mobile
- **Deployment**: Vercel (web frontend), Fly.io (API backend)
- **Containerization**: Docker for backend services
- **Platform Notes**: Mobile uses React Native with Expo. Offline-first with local SQLite + server sync.
```

### [通用场景] Remaining Sections

- **Performance Budgets**: Use `AskUserQuestion`:
  - Prompt: "Should I set default performance budgets now, or leave them for later?"
  - **游戏专用** Options: `[A] Set defaults now (60fps, 16.6ms frame budget, engine-appropriate draw call limit)` / `[B] Leave as [TO BE CONFIGURED] — I'll set these when I know my target hardware`
  - **通用产品** Options: `[A] Set defaults now (API latency <200ms p95, memory <512MB, cold start <5s)` / `[B] Leave as [TO BE CONFIGURED] — I'll set these when I know my target scale`
  - If [A]: populate with the suggested defaults. If [B]: leave as placeholder.
- **Testing**: Suggest stack-appropriate framework — ask before adding.
  - **游戏专用**: GUT for Godot, NUnit for Unity, UE Automation for Unreal
  - **通用产品**: pytest for Python, Vitest/Jest for JS/TS, `cargo test` for Rust, `go test` for Go
- **Forbidden Patterns**: Leave as placeholder
- **Allowed Libraries**: Leave as placeholder. **Guardrail**: Never add speculative dependencies.

### [通用场景] Agent Routing

**[游戏专用]** Engine Specialists Routing

Also populate the `## Engine Specialists` section in `technical-preferences.md` with the correct routing for the chosen engine:

**For Godot** — see **Appendix A** for the routing table matching the language chosen.

**For Unity:**
```markdown
## Engine Specialists
- **Primary**: unity-specialist
- **Language/Code Specialist**: unity-specialist (C# review — primary covers it)
- **Shader Specialist**: unity-shader-specialist (Shader Graph, HLSL, URP/HDRP materials)
- **UI Specialist**: unity-ui-specialist (UI Toolkit UXML/USS, UGUI Canvas, runtime UI)
- **Additional Specialists**: unity-dots-specialist (ECS, Jobs system, Burst compiler), unity-addressables-specialist (asset loading, memory management, content catalogs)
- **Routing Notes**: Invoke primary for architecture and general C# code review. Invoke DOTS specialist for any ECS/Jobs/Burst code. Invoke shader specialist for rendering and visual effects. Invoke UI specialist for all interface implementation. Invoke Addressables specialist for asset management systems.

### File Extension Routing

| File Extension / Type | Specialist to Spawn |
|-----------------------|---------------------|
| Game code (.cs files) | unity-specialist |
| Shader / material files (.shader, .shadergraph, .mat) | unity-shader-specialist |
| UI / screen files (.uxml, .uss, Canvas prefabs) | unity-ui-specialist |
| Scene / prefab / level files (.unity, .prefab) | unity-specialist |
| Native extension / plugin files (.dll, native plugins) | unity-specialist |
| General architecture review | unity-specialist |
```

**For Unreal:**
```markdown
## Engine Specialists
- **Primary**: unreal-specialist
- **Language/Code Specialist**: ue-blueprint-specialist (Blueprint graphs) or unreal-specialist (C++)
- **Shader Specialist**: unreal-specialist (no dedicated shader specialist — primary covers materials)
- **UI Specialist**: ue-umg-specialist (UMG widgets, CommonUI, input routing, widget styling)
- **Additional Specialists**: ue-gas-specialist (Gameplay Ability System, attributes, gameplay effects), ue-replication-specialist (property replication, RPCs, client prediction, netcode)
- **Routing Notes**: Invoke primary for C++ architecture and broad engine decisions. Invoke Blueprint specialist for Blueprint graph architecture and BP/C++ boundary design. Invoke GAS specialist for all ability and attribute code. Invoke replication specialist for any multiplayer or networked systems. Invoke UMG specialist for all UI implementation.

### File Extension Routing

| File Extension / Type | Specialist to Spawn |
|-----------------------|---------------------|
| Game code (.cpp, .h files) | unreal-specialist |
| Shader / material files (.usf, .ush, Material assets) | unreal-specialist |
| UI / screen files (.umg, UMG Widget Blueprints) | ue-umg-specialist |
| Scene / prefab / level files (.umap, .uasset) | unreal-specialist |
| Native extension / plugin files (Plugin .uplugin, modules) | unreal-specialist |
| Blueprint graphs (.uasset BP classes) | ue-blueprint-specialist |
| General architecture review | unreal-specialist |
```

**[通用产品]** Agent Routing — populate with language specialist + general agents:

```markdown
## Agent Routing
- **Primary**: lead-programmer
- **Language Specialist**: [python-specialist / typescript-specialist / rust-specialist / go-specialist]
- **Performance**: performance-analyst
- **Security**: security-engineer
- **DevOps**: devops-engineer
- **QA**: qa-tester / qa-lead
- **Accessibility**: accessibility-specialist (if UI)
- **UX**: ux-designer (if UI)
- **Analytics**: analytics-engineer (if data-heavy)
```

### File Extension Routing

**For Python:**
```markdown
### File Extension Routing

| File Extension / Type | Specialist to Spawn |
|-----------------------|---------------------|
| Source code (.py files) | python-specialist |
| Test files (test_*.py) | qa-tester |
| CI/CD config (.github/workflows/) | devops-engineer |
| Infrastructure (Dockerfile, docker-compose.yml) | devops-engineer |
| Config / typing (.pyi, pyproject.toml) | python-specialist |
| Security-sensitive paths (auth, permissions) | security-engineer |
| Performance-critical paths | performance-analyst |
| General architecture review | lead-programmer |
```

**For TypeScript:**
```markdown
### File Extension Routing

| File Extension / Type | Specialist to Spawn |
|-----------------------|---------------------|
| Source code (.ts, .tsx files) | typescript-specialist |
| Test files (*.test.ts, *.spec.ts) | qa-tester |
| CI/CD config (.github/workflows/) | devops-engineer |
| Infrastructure (Dockerfile, docker-compose.yml) | devops-engineer |
| UI / styling (.css, .scss, .tsx components) | ui-programmer |
| Config (tsconfig.json, next.config.*, vite.config.*) | typescript-specialist |
| Security-sensitive paths (auth, permissions) | security-engineer |
| Performance-critical paths | performance-analyst |
| General architecture review | lead-programmer |
```

**For Rust:**
```markdown
### File Extension Routing

| File Extension / Type | Specialist to Spawn |
|-----------------------|---------------------|
| Source code (.rs files) | rust-specialist |
| Test files (*_test.rs) | qa-tester |
| CI/CD config (.github/workflows/) | devops-engineer |
| Build config (Cargo.toml, build.rs) | rust-specialist |
| Infrastructure (Dockerfile) | devops-engineer |
| Unsafe blocks / FFI boundaries (.rs with `unsafe`) | rust-specialist + security-engineer |
| Performance-critical paths | performance-analyst |
| General architecture review | lead-programmer |
```

**For Go:**
```markdown
### File Extension Routing

| File Extension / Type | Specialist to Spawn |
|-----------------------|---------------------|
| Source code (.go files) | go-specialist |
| Test files (*_test.go) | qa-tester |
| CI/CD config (.github/workflows/) | devops-engineer |
| Build config (go.mod, go.sum, Makefile) | go-specialist |
| Infrastructure (Dockerfile) | devops-engineer |
| Security-sensitive paths (auth, permissions) | security-engineer |
| Performance-critical paths | performance-analyst |
| General architecture review | lead-programmer |
```

### [通用场景] Collaborative Step

Present the filled-in preferences to the user.

**[游戏专用]** For Godot, include the chosen language and note where the full naming conventions and routing tables live:
> "Here are the default technical preferences for [engine] ([language if Godot]). The naming conventions and specialist routing are in Appendix A of this skill — I'll apply the [GDScript/C#/Both] variant. Want to customize any of these, or shall I save the defaults?"

For all other engines, present the defaults directly without referencing the appendix.

**[通用产品]** For general stacks:
> "Here are the default technical preferences for [stack]. Want to customize any of these, or shall I save the defaults?"

Wait for approval before writing the file.

---

## 6. Determine Knowledge Gap

[通用场景] Check whether the version is beyond LLM training data.

**Known approximate coverage** (update as models change): LLM cutoff: **May 2025**

**[游戏专用]** Engine baselines: Godot ~4.3, Unity ~2023.x/early 6000.x, Unreal ~5.3/early 5.4

**[通用产品]** Framework baselines: Python ~3.12, Django ~5.0, FastAPI ~0.111, React ~18.3, Next.js ~14, Node ~22, TS ~5.4, Rust ~1.78, Go ~1.22

Compare chosen version against baselines:
- **Within training data** → LOW RISK — reference docs optional
- **Near the edge** → MEDIUM RISK — reference docs recommended
- **Beyond training data** → HIGH RISK — reference docs required

---

## 7. Populate Reference Docs

[通用场景]

### If WITHIN training data (LOW RISK):

Create a minimal `docs/engine-reference/<engine>/VERSION.md`:

```markdown
# [Engine] — Version Reference

| Field | Value |
|-------|-------|
| **Engine Version** | [version] |
| **Project Pinned** | [today's date] |
| **LLM Knowledge Cutoff** | May 2025 |
| **Risk Level** | LOW — version is within LLM training data |

## Note

This engine version is within the LLM's training data. Engine reference
docs are optional but can be added later if agents suggest incorrect APIs.

Run `/setup-engine refresh` to populate full reference docs at any time.
```

Do NOT create breaking-changes.md, deprecated-apis.md, etc. — they would
add context cost with minimal value.

**[通用产品]** For general stacks, create the equivalent file at `docs/reference/<stack>/VERSION.md`:

```markdown
# [Stack] — Version Reference

| Field | Value |
|-------|-------|
| **Stack Version** | [version] |
| **Project Pinned** | [today's date] |
| **LLM Knowledge Cutoff** | May 2025 |
| **Risk Level** | LOW — version is within LLM training data |

## Note

This stack version is within the LLM's training data. Stack reference
docs are optional but can be added later if agents suggest incorrect APIs.

Run `/setup-engine refresh` to populate full reference docs at any time.
```

Do NOT create breaking-changes.md, deprecated-apis.md, etc. for LOW RISK — they would
add context cost with minimal value.

### If BEYOND training data (MEDIUM or HIGH RISK):

Create the full reference doc set by searching the web:

1. **Search for the official migration/upgrade guide**:
   - `"[stack] [old version] to [new version] migration guide"`
   - `"[stack] [version] breaking changes"`
   - `"[stack] [version] changelog"`
   - `"[stack] [version] deprecated API"`

2. **Fetch and extract** from official documentation:
   - Breaking changes between each version from the training cutoff to current
   - Deprecated APIs with replacements
   - New features and best practices

Ask: "May I create the reference docs under `docs/[engine-]reference/<stack>/`?"

Wait for confirmation before writing any files.

3. **Create the full reference directory**:
   ```
   docs/engine-reference/<engine>/
   ├── VERSION.md              # Version pin + knowledge gap analysis
   ├── breaking-changes.md     # Version-by-version breaking changes
   ├── deprecated-apis.md      # "Don't use X → Use Y" tables
   ├── current-best-practices.md  # New practices since training cutoff
   └── modules/                # Per-subsystem references (create as needed)
   ```

4. **Populate each file** using real data from the web searches, following
   the format established in existing reference docs. Every file must have
   a "Last verified: [date]" header.

5. **For module files**: Only create modules for subsystems where significant
   changes occurred. Don't create empty or minimal module files.

**[通用产品]** For general stacks, use `docs/reference/<stack>/` as the root path instead of `docs/engine-reference/`.

---

## 8. Update AGENTS.md Import

Ask: "May I update the `@` import in `AGENTS.md` to point to the new reference?"

Wait for confirmation, then update:

```markdown
## Version Reference

@docs/engine-reference/<engine>/VERSION.md
```

If the previous import pointed to a different engine (e.g., switching from
Godot to Unity), update it.

**[通用产品]** For general stacks, the import points to `docs/reference/<stack>/VERSION.md` instead.

---

## 9. Update Agent Instructions

[通用场景] Ask before editing. Verify agents have a "Version Awareness" section:
1. Read VERSION.md
2. Check deprecated APIs before suggesting code
3. Check breaking changes for version transitions
4. Use WebSearch to verify uncertain APIs

---

## 10. Refresh Subcommand

[通用场景] `/setup-engine refresh`:

1. Read existing VERSION.md
2. WebSearch for new releases since last verification
3. Update all reference docs with new findings
4. Update "Last verified" dates
5. Report what changed

---

## 11. Upgrade Subcommand

[通用场景] `/setup-engine upgrade [old-ver] [new-ver]`:

### Step 1 — Read Current Version State

Read the VERSION.md to confirm the current pinned version, risk level, and any
migration note URLs already recorded. If `old-ver` was not provided as an
argument, use the pinned version from this file.

- **游戏专用**: `docs/engine-reference/<engine>/VERSION.md`
- **通用产品**: `docs/reference/<stack>/VERSION.md`

### Step 2 — Fetch Migration Guide

Use WebSearch and WebFetch to locate the official migration guide between
`old-ver` and `new-ver`:

- Search: `"[stack] [old-ver] to [new-ver] migration guide"`
- Search: `"[stack] [new-ver] breaking changes changelog"`
- Fetch the migration guide URL from VERSION.md if one is already recorded,
  or use the URL found via search.

Extract: renamed APIs, removed APIs, changed defaults, behavior changes, and
any "must migrate" items.

### Step 3 — Pre-Upgrade Audit

Scan `src/` for code that uses APIs known to be deprecated or changed in the
target version. File types depend on domain:
- **游戏专用**: `.gd`, `.cs`, `.cpp`, `.h`
- **通用产品**: `.py`, `.ts`, `.tsx`, `.rs`, `.go`

Use Grep to search for deprecated API names extracted from the migration
guide (e.g., old function names, removed modules, changed imports).
List each file that matches, with the specific API reference found.

Present the audit results as a table:

```
Pre-Upgrade Audit: [stack] [old-ver] → [new-ver]
==================================================

Files requiring changes:
  File                    | Deprecated API Found    | Effort
  ----------------------- | ----------------------- | ------
  src/api/users.py        | deprecated_function()   | Low
  src/models/base.py      | removed_decorator       | Medium

Breaking changes to watch for:
  - [change description from migration guide]
  - [change description from migration guide]

Recommended migration order (dependency-sorted):
  1. [module with fewest dependencies first]
  2. [next module]
  ...
```

If no deprecated APIs are found in `src/`, report: "No deprecated API usage
found in src/ — upgrade may be low-risk."

### Step 4 — Confirm Before Updating

Ask the user before making any changes:

> "Pre-upgrade audit complete. Found [N] files using deprecated APIs.
> Proceed with upgrading VERSION.md to [new-ver]?
> (This will update the pinned version and add migration notes — it does NOT
> change any source files. Source migration is done manually or via stories.)"

Wait for explicit confirmation before continuing.

### Step 5 — Update VERSION.md

After confirmation:

1. Update `docs/[engine-]reference/<stack>/VERSION.md`:
   - `Version` → `[new-ver]`
   - `Project Pinned` → today's date
   - `Last Docs Verified` → today's date
   - Re-evaluate and update the `Risk Level`
   - Add a `## Migration Notes — [old-ver] → [new-ver]` section
     containing: migration guide URL, key breaking changes, deprecated APIs
     found in this project, and recommended migration order from the audit

2. If `breaking-changes.md` or `deprecated-apis.md` exist in the reference
   directory, append the new version's changes to those files.

### Step 6 — Post-Upgrade Reminder

After updating VERSION.md, output:

```
VERSION.md updated: [stack] [old-ver] → [new-ver]

Next steps:
1. Migrate deprecated API usages in the [N] files listed above
2. Run /setup-engine refresh after upgrading the actual package to
   verify no new deprecations were missed
3. Run /architecture-review — the version upgrade may invalidate ADRs that
   reference specific APIs or framework capabilities
4. If any ADRs are invalidated, run /propagate-design-change to update
   downstream stories
```

---

## 11b. Sync T1 Technical Context

After the user approves the technology configuration writes, if `memory_bank/`
exists, update `memory_bank/t1_axioms/tech_context.md`.

Do not create `memory_bank/` from `/setup-engine`. If it does not exist, keep
the normal writes and tell the user to run `/constitute` to establish the
memory_bank governance control plane.

Record these fields in `memory_bank/t1_axioms/tech_context.md`:

- Selected engine, language, framework, runtime, and database as applicable
- Pinned version for each selected technology
- Reason chosen
- Alternatives rejected
- Compatibility constraints
- Knowledge risk
- Reference docs generated
- Last verified date

This T1 context is a memory mirror of the technical decision. `AGENTS.md`,
`standards/technical-preferences.md`, and the generated reference docs remain
the detailed working sources.

---

## 12. Output Summary

**[游戏专用]** Game summary:
```
Engine Setup Complete
=====================
Engine:          [name] [version]
Language:        [GDScript | C# | GDScript + C# | C# | C++ + Blueprint]
Knowledge Risk:  [LOW/MEDIUM/HIGH]
Reference Docs:  [created/skipped]
AGENTS.md:       [updated]
Tech Prefs:      [created/updated]
Agent Config:    [verified]

Next Steps:
1. Review docs/engine-reference/<engine>/VERSION.md
2. Continue Technical Setup: run /create-architecture
3. Run /architecture-decision for Foundation-layer decisions
4. Run /architecture-review, then /create-control-manifest
5. Run /test-setup to create the required test baseline
6. Run /gate-check technical-setup before normal advancement to Pre-Production
7. If this was run early from Concept or Systems Design, return to the current phase boundary first: /gate-check concept or /gate-check systems-design as appropriate
```

**[通用产品]** Product summary:
```
Stack Setup Complete
=====================
Stack:           [language] [version] + [framework] [version]
Platform:        [Web / Desktop / Mobile / CLI / Server]
Database:        [PostgreSQL / SQLite / DuckDB / ...]
Knowledge Risk:  [LOW/MEDIUM/HIGH]
Reference Docs:  [created/skipped]
AGENTS.md:       [updated]
Tech Prefs:      [created/updated]
Agent Config:    [verified]

Next Steps:
1. Review docs/reference/<stack>/VERSION.md
2. Continue Architecture: run /create-architecture
3. Run /architecture-decision for Foundation-layer decisions
4. Run /architecture-review, then /create-control-manifest
5. Run /test-setup to create the required test baseline
6. Run /gate-check technical-setup before normal advancement to Pre-Implementation
7. If this was run early from Concept or Specification, return to the current phase boundary first: /gate-check concept or /gate-check systems-design as appropriate
```

Verdict: **COMPLETE** — stack configured and reference docs populated.

---

## Guardrails

[通用场景]
- NEVER guess a version — verify via WebSearch or user confirmation
- NEVER overwrite existing reference docs without asking
- If reference docs exist for a different stack, ask before replacing
- Always show the user what you're about to change before making AGENTS.md edits
- If WebSearch returns ambiguous results, show the user and let them decide
- Never add speculative dependencies to Allowed Libraries

**[游戏专用]** Godot GDScript guardrail: When user chose GDScript, write Language as exactly "GDScript" — no additions. Do NOT append "C++ via GDExtension".

---

## Appendix A — Godot Language Configuration

[游戏专用] GDScript/C#/Both variants — AGENTS.md templates, naming conventions, and specialist routing tables. Referenced only when Godot is the chosen engine.

### A1. AGENTS.md Technology Stack Templates

**GDScript:**
```markdown
- **Engine**: Godot [version]
- **Language**: GDScript
- **Build System**: SCons (engine), Godot Export Templates
- **Asset Pipeline**: Godot Import System + custom resource pipeline
```

> **Guardrail**: When using this GDScript template, write the Language field as exactly "`GDScript`" — no additions. Do NOT append "C++ via GDExtension" or any other language. The C# template below includes GDExtension because C# projects commonly wrap native code; GDScript projects do not.

**C#:**
```markdown
- **Engine**: Godot [version]
- **Language**: C# (.NET 8+, primary), C++ via GDExtension (native plugins only)
- **Build System**: .NET SDK + Godot Export Templates
- **Asset Pipeline**: Godot Import System + custom resource pipeline
```

**Both — GDScript + C#:**
```markdown
- **Engine**: Godot [version]
- **Language**: GDScript (gameplay/UI scripting), C# (performance-critical systems), C++ via GDExtension (native only)
- **Build System**: .NET SDK + Godot Export Templates
- **Asset Pipeline**: Godot Import System + custom resource pipeline
```

### A2. Naming Conventions

**GDScript:** Classes: PascalCase, Variables/functions: snake_case, Signals: snake_case past tense, Files: snake_case, Scenes: PascalCase, Constants: UPPER_SNAKE_CASE

**C#:** Classes: PascalCase (partial), Public: PascalCase, Private: _camelCase, Methods: PascalCase, Files: PascalCase, Constants: PascalCase

**Both:** Use GDScript conventions for `.gd` files, C# conventions for `.cs` files.

### A3. Engine Specialists Routing

**GDScript:**
```markdown
## Engine Specialists
- **Primary**: godot-specialist
- **Language/Code Specialist**: godot-gdscript-specialist (all .gd files)
- **Shader Specialist**: godot-shader-specialist (.gdshader files, VisualShader resources)
- **UI Specialist**: godot-specialist (no dedicated UI specialist — primary covers all UI)
- **Additional Specialists**: godot-gdextension-specialist (GDExtension / native C++ bindings only)
- **Routing Notes**: Invoke primary for architecture decisions, ADR validation, and cross-cutting code review. Invoke GDScript specialist for code quality, signal architecture, static typing enforcement, and GDScript idioms. Invoke shader specialist for material design and shader code. Invoke GDExtension specialist only when native extensions are involved.

### File Extension Routing

| File Extension / Type | Specialist to Spawn |
|-----------------------|---------------------|
| Game code (.gd files) | godot-gdscript-specialist |
| Shader / material (.gdshader, VisualShader) | godot-shader-specialist |
| UI / screen (Control nodes, CanvasLayer) | godot-specialist |
| Scene / prefab / level (.tscn, .tres) | godot-specialist |
| Native extension (.gdextension, C++) | godot-gdextension-specialist |
| General architecture review | godot-specialist |
```

**C#:**
```markdown
## Engine Specialists
- **Primary**: godot-specialist
- **Language/Code Specialist**: godot-csharp-specialist (all .cs files)
- **Shader Specialist**: godot-shader-specialist (.gdshader files, VisualShader resources)
- **UI Specialist**: godot-specialist (no dedicated UI specialist — primary covers all UI)
- **Additional Specialists**: godot-gdextension-specialist (GDExtension / native C++ bindings only)
- **Routing Notes**: Invoke primary for architecture decisions, ADR validation, and cross-cutting code review. Invoke C# specialist for code quality, [Signal] delegate patterns, [Export] attributes, .csproj management, and C#-specific Godot idioms. Invoke shader specialist for material design and shader code. Invoke GDExtension specialist only when native C++ plugins are involved.

### File Extension Routing

| File Extension / Type | Specialist to Spawn |
|-----------------------|---------------------|
| Game code (.cs files) | godot-csharp-specialist |
| Shader / material (.gdshader, VisualShader) | godot-shader-specialist |
| UI / screen (Control nodes, CanvasLayer) | godot-specialist |
| Scene / prefab / level (.tscn, .tres) | godot-specialist |
| Project config (.csproj, NuGet) | godot-csharp-specialist |
| Native extension (.gdextension, C++) | godot-gdextension-specialist |
| General architecture review | godot-specialist |
```

**Both — GDScript + C#:**
```markdown
## Engine Specialists
- **Primary**: godot-specialist
- **GDScript Specialist**: godot-gdscript-specialist (.gd files — gameplay/UI scripts)
- **C# Specialist**: godot-csharp-specialist (.cs files — performance-critical systems)
- **Shader Specialist**: godot-shader-specialist (.gdshader files, VisualShader resources)
- **UI Specialist**: godot-specialist (no dedicated UI specialist — primary covers all UI)
- **Additional Specialists**: godot-gdextension-specialist (GDExtension / native C++ bindings only)
- **Routing Notes**: Invoke primary for cross-language architecture decisions and which systems belong in which language. Invoke GDScript specialist for .gd files. Invoke C# specialist for .cs files and .csproj management. Prefer signals over direct cross-language method calls at the boundary.

### File Extension Routing

| File Extension / Type | Specialist to Spawn |
|-----------------------|---------------------|
| Game code (.gd files) | godot-gdscript-specialist |
| Game code (.cs files) | godot-csharp-specialist |
| Cross-language boundary decisions | godot-specialist |
| Shader / material (.gdshader, VisualShader) | godot-shader-specialist |
| UI / screen (Control nodes, CanvasLayer) | godot-specialist |
| Scene / prefab / level (.tscn, .tres) | godot-specialist |
| Project config (.csproj, NuGet) | godot-csharp-specialist |
| Native extension (.gdextension, C++) | godot-gdextension-specialist |
| General architecture review | godot-specialist |
```
