# Discovery Writing Report

Flow: instruction → provider generation → versioned `chapter_drafts` record → validation → author review → explicit approval → existing chapter intelligence → candidate extraction.

Discovery drafts can start without a chapter plan or arc. They still carry draft id, version, status, active state, provider metadata, word range, validation report, chapter number, and provenance. Approval uses the existing draft transition boundary. The approval hook indexes chapter intelligence and extracts characters, relationships, world facts, timeline, knowledge changes, mysteries, promises, plot threads, foreshadowing, artifacts, POV/style, and unresolved elements when available.

Extraction records remain `candidate` and include source collection, source draft, version, workflow mode, and evidence. Canon is never silently promoted.

Word ranges are minimum/target/maximum and are validated by Pydantic. Current generation uses a bounded provider request; very large requested chapters should be split into scene-sized continuations in the next hardening pass before production-scale novel generation.

