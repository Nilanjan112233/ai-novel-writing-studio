# NovelForge Direct Chat-to-Chapter Report

## Live result

The following real-provider requests were entered in Story Studio:

1. `Write Chapter 1 around 2,000-2,500 words...`
2. `Write Chapter 2 around 1,200-1,600 words...`

Both requests created real `chapter_drafts` through `DiscoveryWriterAgent`. No manual database seeding or alternate writing pipeline was used.

## Author-facing flow

The browser showed:

- `Reviewable chapter draft`;
- readable prose preview;
- requested word range and actual word count;
- `Open chapter`;
- `Edit or revise`;
- `Approve prose`;
- `Continue writing` after approval.

After approval, the chapter library showed the active version as authoritative and exposed context, story leads, and continuation.

## Word ranges

- Chapter 1: minimum 2,000, target 2,250, maximum 2,500; actual 2,375; compliant.
- Chapter 2: minimum 1,200, target 1,400, maximum 1,600; actual 1,534; compliant after one bounded correction attempt because the first response was 153 words.

The existing bounded range correction was reused. The system did not silently accept a short chapter or blindly request an unbounded giant response.

## Authority path

`Story Studio -> existing discovery writer -> chapter draft lineage -> review -> explicit approval -> extraction/intelligence -> future context`.
