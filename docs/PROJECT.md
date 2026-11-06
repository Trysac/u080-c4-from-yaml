# Project record

## Objective

Generate C4 context, container and component diagrams in Mermaid syntax from one validated YAML architecture model with safe loading

## Scope

- In scope: the public API documented in [README.md](../README.md), typed and tested.
- Out of scope: anything that needs runtime dependencies or I/O without an accepted ADR.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 389227 / 91231 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.6911 |

## Factory run u080 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | claude-sonnet-5-5 | yes | 2411 | 76631 | 0 | 4246 | 0.3860 |
| fix-1 | claude-sonnet-5-5 | no | 10 | 1425 | 12495 | 87923 | 0.0543 |
| audit | claude-sonnet-5-5 | no | 12 | 4070 | 29624 | 122172 | 0.1270 |
| fix-2 | claude-sonnet-5-5 | no | 6 | 1534 | 7773 | 40348 | 0.0388 |
| docs | claude-haiku-5-5 | no | 132099 | 7571 | 0 | 0 | 0.0850 |

Total: $0.6911. Prices: Anthropic list prices.
