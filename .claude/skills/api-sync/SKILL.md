---
name: api-sync
description: Verify OpenAPI spec and generated frontend client are in sync with backend routes
---

# API Sync Check

Verify the OpenAPI codegen pipeline is in sync: backend routes → OpenAPI spec → generated frontend client → type re-exports.

## Steps

### 1. Extract Backend Routes

List all routes defined in `backend/app/routes/`:

```bash
grep -rn '@router\.' backend/app/routes/ --include='*.py'
```

Record each endpoint's method, path, request model, and response model.

### 2. Compare Against OpenAPI Spec

Read `backend/openapi.json` and compare:
- Every backend route should have a corresponding path in the spec
- Request/response schemas should match Pydantic model definitions
- If mismatched, the spec is stale — recommend running: `python scripts/export-openapi.py`

### 3. Check Frontend Generated Client

Verify `frontend/src/lib/generated/` matches the OpenAPI spec:
- Compare operation IDs and type names in `types.gen.ts` and `sdk.gen.ts`
- If mismatched, the client is stale — recommend running: `make generate-api`

### 4. Verify Type Re-exports

Check `frontend/src/lib/types.ts`:
- All types used by frontend components should be re-exported here
- Imports should reference `@/lib/generated/`, not use types inline
- Flag any generated type used directly in components without going through the re-export barrel

### 5. Full Pipeline Test

If any step found drift:

```bash
make generate-api
cd frontend && npx tsc --noEmit
```

Verify the regenerated client passes typecheck.

## Output

| Layer | Status | Details |
|-------|--------|---------|
| Backend routes | N endpoints found | List any unregistered routes |
| OpenAPI spec | In sync / Stale | Missing or extra paths |
| Generated client | In sync / Stale | Mismatched operations or types |
| Type re-exports | Complete / Gaps | Missing re-exports |

**Recommendation:** If anything is out of sync, provide the exact commands to fix it.
