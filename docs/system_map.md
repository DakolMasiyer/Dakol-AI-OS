# System Map

```text
                    +----------------------+
                    |      /docs           |
                    | architecture/specs   |
                    +----------+-----------+
                               |
                               v
+-------------------+   +------+-------+   +---------------------+
| /tests            |-->| /core        |-->| certified kernel    |
| certification     |   | invariants   |   | replay + audit      |
| drift + replay    |   | execution    |   +---------------------+
+-------------------+   +------+-------+
                               |
                               v
                    +----------+-----------+
                    |     /platform        |
                    | CLI / policy / ops    |
                    +----------+-----------+
                               |
          +--------------------+--------------------+
          |                                         |
          v                                         v
    +-----+------+                           +------+------+
    | /agents    |                           | /apps       |
    | safe agents|                           | user apps   |
    +------------+                           +-------------+

/experimental remains isolated and may only call stable public APIs.
```

## Trust Zones

- Core: deterministic runtime kernel, invariants, replay, execution audit.
- Platform: operational tooling, dashboards, policy, and orchestration utilities.
- Agents: production-safe agents only.
- Experimental: unstable systems isolated from runtime mutation.
- Apps: user-facing products and workflows.
- Tests: certification, adversarial, replay, and drift detection.

