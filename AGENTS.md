# Repository working conventions

## Branch names

- Exception: Community Explorer queue work performed by the continuous hourly
  worker is integrated directly on `main`, as explicitly requested by the
  repository owner. Do not create or switch to `AKO-<N>` branches for that
  queue; preserve a clean, fast-forwardable `main` and commit validated queue
  implementations there.

- Every change associated with a GitHub issue must use the exact branch name
  `AKO-<N>`, where `<N>` is that issue's numeric identifier.
- Examples: issue `#5` uses `AKO-5`; issue `#142` uses `AKO-142`.
- Do not add personal, tool, or category prefixes such as `codex/`, `feat/`, or
  `docs/` to issue branches.
- Create the issue before creating its implementation branch so the identifier
  is authoritative.
