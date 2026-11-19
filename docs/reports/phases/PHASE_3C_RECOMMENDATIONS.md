# NovelForge Narrative Studio V2 - Phase 3C Recommendations

Recommendation date: 2026-06-14

## Priority 1 - Author Throughput

1. Add shared search, filter, sort, pagination, and virtualization controls to
   long chapter, editorial, audit, canon, impact, and manuscript collections.
2. Replace the mobile fixed sidebar with a collapsible navigation drawer.
3. Add deep links from every Story Health finding to its exact source record.
4. Group change impact by unique chapters and record type before showing the
   total affected-record count.
5. Add queue triage by blocker, priority, age, arc, chapter, and author
   decision status.

## Priority 1 - Quality Confidence

1. Calibrate prose findings against a blind human-rated benchmark.
2. Track repeated recommendations and suppress duplicates without new
   evidence.
3. Add chapter-structure diversity metrics across openings, scene counts,
   conflict shape, resolution type, POV, dialogue ratio, and emotional
   direction.
4. Keep all quality findings advisory. Do not introduce automatic prose
   replacement.

## Priority 1 - Reliability

1. Track corrective schema retries, retry success, and retry cost by agent and
   model.
2. Add required-output validation for every agent schema at the provider
   boundary.
3. Run large audits and impact scans as observable background jobs for very
   large projects.
4. Preserve the current hard failure when a corrective retry still omits
   required content.

## Priority 2 - Memory

1. Create a 100-question long-range memory benchmark across genres.
2. Add entity aliases and rename history to chapter intelligence.
3. Score retrieval precision, recall, token cost, and cross-project false
   positives.
4. Show authors why an old obligation was retrieved and where it originated.
5. Retain structured obligations independently of compressed prose.

## Priority 2 - Story Health

1. Show trends and deltas between health snapshots.
2. Separate warnings from approval blockers visually and semantically.
3. Let authors acknowledge, defer, dismiss, or intentionally preserve a
   finding with a reason.
4. Add arc-level and character-level health drilldowns.
5. Explain score weights and avoid implying objective literary quality.

## Priority 2 - Validation Realism

1. Generate a smaller benchmark novel entirely through normal APIs and
   approval events instead of direct database seeding.
2. Introduce realistic author changes at Chapters 10, 25, and 40, then verify
   impact, memory, and revisions.
3. Include renamed characters, split arcs, removed mysteries, reordered
   chapters, and a changed ending.
4. Add human editor review of at least five early and five late chapters.

## Priority 3 - Operations

1. Replace deprecated FastAPI startup events with lifespan handlers.
2. Set explicit `pytest-asyncio` loop scope.
3. Update deprecated Pydantic configuration and serializers.
4. Add health metrics for audit duration, impact scan duration, memory packet
   size, and snapshot age.
5. Add a project-scope query lint or audit for all owned collections.

## Scope Guard

Do not start export, publishing, EPUB, PDF, DOCX, collaboration, marketplace,
or team features until the Priority 1 author-throughput and quality-confidence
work is addressed.
