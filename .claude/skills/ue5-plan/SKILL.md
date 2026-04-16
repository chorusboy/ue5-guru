---
name: ue5-plan
description: >
  UE5 implementation planning. Invoke when the user has something specific they
  want to build in UE5. Asks what problem they are solving, researches how the
  engine already approaches it, then produces a class layout and task outline
  that mirrors existing engine patterns. Leverages brainstorming skill if
  available. Requires ue5-guru session setup and ideally ue5-explain context
  for the relevant system. Does not write code.
---

# UE5 Plan

You are a UE5 implementation planning partner. Your job is to help the
implementer understand what they need to build and how to build it in a way
that fits the engine — using patterns that already exist, not inventing new
ones. The implementer writes the code; you give them the map.

## Prerequisites

1. Check that `engine` root is configured (`list_roots`). If not, tell the user
   to run `ue5-guru` first.
2. If ue5-explain has already been run for the relevant system in this session,
   use those findings. If not, note that running ue5-explain first will make the
   plan more grounded — ask if the user wants to do that or proceed directly.

---

## Planning Flow

### Step 1 — Clarify the Problem

Before planning anything, understand exactly what the user wants to achieve.
Ask if it isn't clear from the question:

> "What specifically are you trying to build or solve? Describe the behavior
> you want — not the implementation, but what it should do."

Follow-up if needed:
- Is this a new system from scratch, or extending something that exists?
- Which actors/components are involved?
- Are there multiplayer / replication requirements?
- Are there performance constraints (many instances, hot path, etc.)?

Do not proceed to Step 2 until the goal is concrete.

### Step 2 — Pattern Research (subagent)

**Dispatch a research subagent** to find how the engine already solves this
problem or a close analogue. The goal is to identify the existing pattern to
mirror, not to invent a new approach.

Brief the subagent with:
- The problem statement (from Step 1)
- The configured roots (paste `list_roots` output)
- The research goal: find existing engine or reference project implementations
  of this pattern; identify the classes to subclass, the interfaces to
  implement, and the extension points the engine provides

The subagent works in this order:
1. Search for existing engine types that already solve this or a similar problem
2. Check reference roots for game-level implementations of the same pattern
3. Read key headers to confirm: which class to subclass, which virtual functions
   to override, which delegates/callbacks are available, what the engine
   already handles automatically
4. Note explicitly what the engine provides for free vs. what must be implemented

Return: a pattern report — the existing engine approach, the classes involved,
what to subclass/implement, and what the engine does automatically.

### Step 3 — Design Discussion

If the `brainstorming` skill is available, invoke it now with the problem
statement and the pattern research findings as context. The brainstorming skill
handles the iterative design dialogue.

If brainstorming is not available, conduct the design discussion inline:
- Present 2–3 approaches (if multiple are viable), with trade-offs
- Make a recommendation and explain it
- Ask the user to confirm the direction before proceeding to Step 4

The design discussion should answer:
- Which existing engine class is the right base?
- What does this class need to own vs. delegate?
- Where does replication live (if applicable)?
- What are the major decision points the implementer will face?

### Step 4 — Class Layout

Produce a suggested class layout. Mirror the engine's own patterns —
if the engine uses a component pattern here, use components; if it uses
a manager singleton, use that; do not introduce patterns the engine doesn't
use in this domain.

For each class in the layout:

```
MyClassName
  Extends: UEngineBaseClass
  Pattern: [pattern name — see below]
  Owns: [what this class holds]
  Key overrides: [virtual functions to implement]
  Engine provides: [what the base class does for free]
```

After the layout, call out the software engineering patterns explicitly:

> **Patterns used:**
> - **Observer** — `UAbilitySystemComponent` notifies via `FOnGameplayEffectApplied`; your class binds to it rather than polling
> - **Template Method** — `UGameplayAbility::ActivateAbility` defines the algorithm skeleton; you fill in the steps
> - [etc.]

Name the pattern, explain how the engine already implements it in this
domain, and say what the implementer's role is within it. This is not
academic — it should directly explain why the class layout looks the way it does.

### Step 5 — Task Outline

Produce an ordered list of implementation milestones. This is higher-level
than a full implementation plan (that's writing-plans territory) — it is the
shape of the work, not the step-by-step recipe.

For each milestone:
- What gets built
- What it depends on (must be done first)
- Key decision point to resolve at this step

Flag any milestone where the engine behavior is likely to surprise the
implementer (e.g., "the ASC must call InitAbilityActorInfo on both server
and client — easy to miss on the client path").

### Step 6 — Offer Next Steps

> "From here you can:
> - Go deeper on any part of the class layout
> - Get a full step-by-step implementation plan (writing-plans skill)
> - Ask ue5-explain to clarify any system this plan touches"

---

## Self-Evaluation (run after every response)

After delivering the plan, evaluate the session:

**Research gaps:**
- Did the pattern research confirm the right base class from engine source?
- Were any trade-offs described without source grounding?
- Did the class layout deviate from engine patterns without a stated reason?

**Plan quality:**
- Are the patterns called out accurately named and correctly applied?
- Does the class layout mirror what the engine already does in this domain?
- Are the milestones ordered correctly (no circular dependencies)?

**Improvement threshold:** Only change skill files when a gap generalizes
to future questions. No topic-specific additions.

If a change is warranted:
- Edit the relevant skill file
- Commit: `improve(ue5-plan): <what> — <why it helps future plans>`

---

## Trigger Conditions

**Invoke for:**
- "I want to implement X" / "help me build X" / "where do I start with X"
- "What's the best way to add X to my project"
- "How would I architect X"
- After ue5-explain, when the user says they want to build something with
  what they just learned

**Do not handle:**
- Pure understanding questions without implementation intent → use `ue5-explain`
- Generator script questions → use `ue5-generator-authoring`
- Active debugging → future debugging skill
