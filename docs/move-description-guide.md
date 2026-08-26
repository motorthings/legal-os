# Describing a move — a writing guide

The "moves" (pricing, seams, comp, latency, leverage) are the heart of the report a managing
partner reads. They must read like something a partner says in a room, not like a variable
name or a model's internals. Every sentence below comes from edits that failed the test: a
partner stopped on a word, or had to guess what a pronoun pointed at.

## The rules

1. **Name the change the way a partner would say it.**
   "Move to flat fees," "write down the know-how at your hand-offs." Never a variable: no
   "pricing lever," "seams lever," "comp."

2. **Show the mechanism, don't state the conclusion.**
   Say what actually happens today, then what the change does to it.
   - "Under hourly billing, a saved hour is a lost bill" beats "this sets the sign."

3. **One mechanism per move.**
   If a second idea belongs to another bullet, leave it there. Two ideas in one sentence is
   how "the sign" and "margin" got buried.

4. **Name the referent.**
   No dangling "it." Say "how you bill," "this switch," "the bonus." If a reader has to guess
   what a pronoun points at, it's wrong.

5. **Tell the hitch where there is one.**
   The cost and the dependency are part of the description. "It takes senior hours and a few
   quarters." "But only after flat fees are in." A move with no cost reads as a pitch.

6. **Every claim traces to the engine.**
   Don't invent a reason. If the model doesn't support a "why," say what it does support, or
   say the model prices the destination, not the trip. The mechanisms live in
   `simulation/src/orchestrator.py` (`_adoption_rate`, `_collect_metrics`) and the
   coefficient table in `simulation/src/models/elasticities.py`.

7. **Read it aloud in a room.**
   If a partner would stop to decode any word, rewrite it. "Margin," "gates," "mechanism,"
   "sets the sign," "hour-compression" all failed this test.

8. **Keep each move to two to four sentences.**
   The whole page is ninety seconds. A move that needs more than that is two moves.

## The source of truth

The expanded, plain-English descriptions live in `simulation/report.py` as
`_LEVER_DESCRIPTIONS`. That is the one place a move's copy lives; the report and the
one-pager render from it. Update the description there, not in prose that lives in a doc.

## Worked example

The pricing move went from "this sets the sign on everything after it" (abstract, dangling
pronoun) to:

> **Move to flat fees.** Under your current hourly billing, an hour AI saves is an hour you
> don't bill. Under a flat fee, that saved hour becomes profit. This switch sets the
> direction for everything after it.
