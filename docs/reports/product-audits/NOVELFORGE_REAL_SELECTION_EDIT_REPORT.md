# NovelForge Real Selection Edit Report

## Result

Selection-based AI editing works through the existing protected revision path.

## Browser evidence

In Writing, the approved Chapter 1 was opened and its protected textarea was selected. The browser exposed `Focused AI edit` actions: `Rewrite naturally`, `Shorten`, `Improve dialogue`, and `Custom instruction`.

The real `Rewrite naturally` request created an Editorial branch and a RevisionAgent version through OpenRouter/DeepSeek. The approved source remained Version 1 and unchanged. The created branch was draft/reviewable, with Compare and explicit use controls in Editorial.

## Safety

The selected text is sent with tightly scoped context. The result is a suggestion, never a silent replacement. Rejecting or leaving the branch unused preserves the active source. Applying still requires the existing Editorial approval and draft-lineage workflow.

