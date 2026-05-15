# Default SkillSentinel policy pack (Rego).
# Phase 3 will integrate OPA and ship a real policy. This file is a placeholder
# so the rest of the project can reference it.

package skillsentinel.default

default verdict := "ALLOW"

# Example rule (not active yet): block on any CRITICAL finding.
# verdict := "BLOCK" {
#   some i
#   input.findings[i].severity == "CRITICAL"
# }
