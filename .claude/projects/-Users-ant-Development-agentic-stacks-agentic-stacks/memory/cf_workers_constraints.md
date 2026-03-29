---
name: CF Workers constraints
description: Cloudflare Workers Python runtime constraints — D1 is async, no threads, lazy imports required
type: feedback
---

D1 database operations return PyodideFuture (JS Promises) and MUST be awaited. All StacksDB methods must be async across all implementations (D1DB, SQLiteDB, StubDB) so routes can uniformly `await` them.

**Why:** Discovered 2026-03-28 — sync D1 calls caused `RuntimeError: await wasn't used with future` on /stacks endpoint. Homepage appeared to work only because empty results from `_all()` were caught by AttributeError fallback.

**How to apply:** When adding new DB methods, always make them `async def` in all three implementations. Route handlers must `await` every DB call. Tests that call DB methods directly use `_run()` helper with `asyncio.new_event_loop()`.
