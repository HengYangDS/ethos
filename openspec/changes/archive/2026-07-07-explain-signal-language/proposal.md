# Explain Signal Language

## Problem

`ethos explain` projects a string into the invalid-state taxonomy. Some strings
come from blocking required gaps; others are non-blocking advisory signals. The
payload should not overclaim that every explained signal is a required gap.

## Change

Keep the command read-only and taxonomy-centered, but make its wording neutral:
explain a governance gap or advisory signal as an invalid-state projection.
