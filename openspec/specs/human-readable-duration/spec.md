# human-readable-duration Specification

## Purpose
TBD - created by archiving change fix-human-readable-duration. Update Purpose after archive.
## Requirements
### Requirement: Human-readable duration formatting
`get_human_readable_duration` SHALL convert a non-negative integer number of seconds
into a human-readable string. The string SHALL be non-empty for all valid inputs,
including durations under 60 seconds.

#### Scenario: Duration of zero or sub-minute value
- **WHEN** `get_human_readable_duration` is called with a duration less than 60 seconds
- **THEN** it returns `"less than a minute"`

#### Scenario: Duration of exactly one minute
- **WHEN** `get_human_readable_duration` is called with `duration=60`
- **THEN** it returns `"1 minute"`

#### Scenario: Duration spanning multiple units
- **WHEN** `get_human_readable_duration` is called with a duration covering days, hours, and minutes
- **THEN** it returns a comma-separated string of each non-zero unit (e.g. `"1 day, 3 hours, 26 minutes"`)

