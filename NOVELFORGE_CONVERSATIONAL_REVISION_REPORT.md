# NovelForge Conversational Revision Report

## Result

Story Studio now recognizes chapter-revision language including rewrite, revise, less AI, more natural, humanize, and similar requests. It identifies the active chapter, creates or transitions into the existing reviewable revision path, and calls Editorial's request-review, branch, and revision services.

For an approved chapter, the source remains protected. The result is a reviewable version with a change reason and preserved continuity guidance. The author can open the chapter, inspect the revision, compare versions, keep the original, or use the revised version.

## Clarification behavior

Ambiguous requests such as `Make Chapter 1 darker` now pause for one meaningful creative choice. The live browser test confirmed that the answer remains connected to the original request and is labeled as a proposal until the author decides.

## Boundary

Story Studio is a coordinator over existing drafting and Editorial services; it is not a second writing or revision authority. The current test did not claim that an ambiguous “darker” request should automatically rewrite prose. It correctly produced a constrained planning proposal instead.

