# NovelForge Remaining Limitations

1. Full-chapter humanization is not a cheap-model win yet. Gemini is fast and inexpensive but produced summary-like output in the live A/B. Auto now avoids that waste by selecting the strong editorial tier for full chapters.
2. Targeted development remains very context-heavy and should be optimized by reducing duplicated agent context, not by weakening continuity or author-intent checks.
3. A fresh two-chapter real-provider acceptance run was not repeated in this pass.
4. Story Studio history intentionally preserves old responses; the author must use Refresh against current story for a current answer. This is a trust boundary, not a defect.
5. Existing failed or waiting jobs remain visible until resolved; this is honest recovery state, though a future cleanup/filter could make old attention less prominent.
6. No TencentDB Agent Memory integration was attempted or needed. Native MongoDB-backed retrieval and authority remain the system of record.

