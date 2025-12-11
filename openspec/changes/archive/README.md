# Archived Changes

This directory contains OpenSpec changes that have been completed and superseded by newer implementations, or are no longer actively developed.

---

## Archived Changes

### add-redis-streaming
- **Archived**: 2025-12-11
- **Reason**: Superseded by `refactor-redis-pubsub-to-stream`
- **Status**: ✅ All functionality migrated
- **Details**:
  - Original proposal: Implement Redis Pub/Sub-based streaming pipeline
  - Current implementation: Redis Stream-based persistent workflow events (better durability, message persistence, subscription resumption)
  - Migration path: See `openspec/changes/refactor-redis-pubsub-to-stream/`

---

## How to Reference Archived Changes

If you need to understand the historical context or design decisions:

1. **For implementation details**: Check the archived proposal.md and tasks.md
2. **For current implementation**: Refer to the superseding change in `openspec/changes/`
3. **For migration notes**: See the "Migration Notes" section in the archived proposal.md

---

## Future Archival Guidelines

When archiving a change:
1. Move the entire change directory to `archive/`
2. Update proposal.md with:
   - Status: ⚠️ ARCHIVED
   - Archived Date
   - Reason for archival
   - Migration path (if superseded)
3. Update tasks.md with migration notes
4. Update `openspec/CHANGES_STATUS.md` to reflect the archival
