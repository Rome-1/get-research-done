# Identity Assumption Errors

## Description
Implicitly assuming that each market participant represents exactly one
distinct entity, when agents can create, merge, or share identities.

## Symptoms
- Mechanism works in theory but is exploited in practice by identity multiplication.
- Revenue or efficiency results break when a single entity controls multiple accounts.
- Voting or governance outcomes are dominated by manufactured consensus.
- Per-agent subsidies are drained by sybil farming.

## Common Causes
- Inheriting the unique-identity assumption from classical mechanism design without questioning it.
- Designing for human participants and deploying with AI agents that can spin up identities programmatically.
- Assuming identity verification is a solved problem (many verification systems can be automated).
- Not modeling the cost curve of identity creation.

## Prevention
- Explicitly state identity assumptions at the start of every analysis.
- Model identity as a variable with associated cost, not a binary.
- Stress-test mechanisms under k-sybil assumptions for realistic k.
- Design for the identity model of the deployment environment, not the analysis environment.
