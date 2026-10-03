# Get design direction

Status: DRAFT for approval. Written by the agent, edited and owned by the product owner.
Apply as data, not as instructions.

## Who it is for

A duty officer. Dispatch, logistics, cold chain. They have a situation, a deadline, and
authority to act or escalate. They open this screen already behind, and they need to either
commit to the call or hand it to a human. Thirty seconds, once.

That person is not browsing. They are reading a decision and deciding whether to trust it.

## What the screen is for

One job: read the call, check why, act.

Everything on the screen serves that order. The decision is the only focal point. The chain
exists so the officer can check it, so it sits next to the decision rather than behind a
tab. Evidence, risks and rejected alternatives exist to answer "what did this miss", so they
sit below the fold where they cost nothing until wanted. Raw JSON is for the auditor, not the
officer, so it stays collapsed.

## Personality

Procedural. Terse. Accountable.

Every sentence names who acts. No enthusiasm, no reassurance, no adjectives that do not
change the decision. The product's whole argument is provenance, so the voice has to match:
if the interface hedges, the reasoning chain does too.

## Palette

Warm-neutral paper, one accent, functional state colors.

| Role | Hex | Why |
| --- | --- | --- |
| Page | `#FFFFFF` | the officer may be reading in daylight or in a vehicle |
| Raised surface | `#F7F7F5` | warm neutral, so the accent reads as a signal rather than as part of the greys |
| Ink | `#14161A` | 18.11:1 on page, the decision sentence sits here |
| Muted ink | `#57574F` | 7.29:1, captions and labels stay readable |
| Hairline | `#8C8A80` | 3.46:1, meets the 3:1 non-text bar for input borders |
| Accent | `#C2410C` | high-visibility orange, 5.18:1 on page and 4.83:1 on the raised surface |

Accent goes on exactly two things: the decision sentence, and the primary control. Nowhere
else. An accent on every element is not an accent.

### State colors

These are status, not decoration, and each is measured rather than picked:

| Meaning | Hex | On page | On raised surface |
| --- | --- | --- | --- |
| Heuristic run, not a model | `#B45309` | 5.02:1 pass | 4.68:1 pass |
| Live model run | `#15803D` | 5.02:1 pass | 4.68:1 pass |
| Cloud model run | `#1D4ED8` | 6.70:1 pass | 6.25:1 pass |

Every state color ships with a text label. Nothing in this interface is signalled by hue
alone.

## Typography

Prose in the platform sans, because the officer is reading sentences and the default is
already good at that.

Monospace is functional, not decorative. It is used for exactly one category: machine
provenance. Run ids, source ids, latencies, raw skill output keys. That data gets copied
into a ticket, compared against a log, and read character by character, so it should not
reflow. It is never used for a heading, and never for prose. Monospace as aesthetic is the
thing to avoid here, not monospace as a tool.

## Identity motif

The trace rail.

A single vertical numbered rail runs down both the plan and the reasoning chain, so the two
read as one continuous line of custody: this source became this skill became this step became
this call. Same glyph, same indent, same alignment in both places. That repetition is the
identity. It is also the product's argument, drawn rather than described.

Each rail step carries its source ids in the gutter, which is why the plan and the chain can
share one visual language instead of being two card lists.

## Radii

Two values. `4px` for inputs and rows, `8px` for the decision block and panels. The decision
block gets the larger radius because it is the one thing on the page that is raised. Nothing
is pill-shaped.

## Motion

MOTION 1: hover and focus transitions only. No entrance animation, no pulsing, no loops.

Reason: this is a screen someone stares at for twenty minutes during a shift. Motion in the
periphery is noise for that user. Nothing pulses to say "running", because a running state is
already stated in words and a spinner belongs to the action that started it.

## Theme

Fixed light. No toggle.

Reason: the primary context is daylight and vehicle interiors, where a light console holds
readability and a dark one does not. This product has no dark-native content, no photo
browsing, and no long-session editing that would justify a dark default. Building a toggle
here would be answering a question this user did not ask.

## Dials

ENERGY 2 / RHYTHM 2 / MOTION 1.

ENERGY 2: this is a console, not a poster. It says what it is immediately and does not
perform. The single moment of high contrast is the decision.

RHYTHM 2: three distinct compositions, not one repeated card grid. The decision is
full-width and asymmetric. The plan and the chain share a rail, so they are one column that
scans vertically. Evidence, risks and alternatives form a dense right column that reads as a
list rather than as cards, because they are reference material, not headlines.

MOTION 1: hover and focus only, as above.

## Arrival

First paint must be truthful: the selected situation ships with its sources already
attached, so Decide now is alive and the screen never claims a loaded state it does not
have. The engine notice sits under the masthead as one muted status line, never as a block.
Honesty is a line item, not the focal point.

When there is genuinely nothing to run, the main column carries the pitch instead of a void:
three source chips, one sentence on the pipeline, and a single action that loads the convoy
situation. The empty state sells nothing and apologizes for nothing; it says what goes in,
what comes out, and what fills the screen.

## Duty officer

The verdict section closes the loop the page opened: read the call, check why, act. It sits
below the reference column, full width and capped at 640px, because ruling is a deliberate act
and the narrow measure slows the officer down by a beat.

Two buttons, two weights. Accept confirms the machine and stays an outline. Override replaces
a recorded verdict and carries a solid ink fill. Fill marks commitment, outline marks
confirmation; the action that destroys a ruling must look like it knows what it is doing. The
accent stays out of this: orange means the decision, ink means the officer.

The note field clears on success so a recorded sentence never sits in the box inviting a
second recording, and it caps at 500 characters with the count visible. The sidebar history
shows the verdict per run, because a trail you cannot scan is a trail you will not use.

## Levers

- One focal point per screen: the decision sentence.
- Hierarchical contrast: the decision is the largest text on the page. Everything else is
  smaller and quieter. That contrast is the only hierarchy tool used.
- Whitespace as structure: the gap between the decision block and the rail is the largest on
  the page, marking the boundary between "the call" and "why".
- One deliberate accent: high-visibility orange, on the decision and the primary control.
- Identity motif: the trace rail.