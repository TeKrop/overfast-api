## Context

`get_human_readable_duration` is a `@cache`-decorated helper used in every router's
route description to display the cache TTL in human-readable form. It currently
produces an empty string for any duration under 60 seconds, resulting in malformed
documentation strings like `"Cache TTL : ."`.

## Goals / Non-Goals

**Goals:**
- Ensure the function always returns a non-empty string for any non-negative integer input
- Keep the fix minimal and non-breaking for all existing call sites

**Non-Goals:**
- Handling negative durations (not a valid input in this domain)
- Displaying seconds granularity for durations ≥ 60 seconds

## Decisions

### Decision: Use `"less than a minute"` as the sub-minute fallback

A `"0 minutes"` or `"30 seconds"` fallback would be technically accurate but
inconsistent with the natural-language style of the existing output (`"1 day"`,
`"2 hours"`, `"10 minutes"`). `"less than a minute"` matches that register and
is the conventional phrasing used by tools like git and GitHub.

The fallback is placed as a post-loop guard (`if not duration_parts`) rather than
a pre-check, keeping the existing logic untouched.

## Risks / Trade-offs

- No risk of breaking existing behavior — the fallback branch is only reached when
  `duration_parts` is empty, which was previously the silent-empty-string case.
