# Evaluation and guardrails

## Why evaluation is on every job advert

Anyone can produce a demo where the model answers well. The job is knowing
whether it answers well on the thousandth question, and noticing when it stops.

Evaluation means a fixed set of inputs with known correct answers, scored
automatically, so you can tell whether a change helped or hurt.

## Guardrails

Guardrails are the checks around the model call. Before: is this input even
something we should answer. After: does the answer contain something it
should not, and is it actually supported by the material we retrieved.

A model that confidently states something your documents never said is the
failure that matters, because it looks exactly like a correct answer.

## Observability

Observability is watching the behaviour of a live system. For a language model
that means recording what went in, what came back, how long it took and what
it cost, so that when someone reports a bad answer next week you can find it.
