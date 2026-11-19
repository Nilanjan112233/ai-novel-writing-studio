# NovelForge Full Author Journey UX Audit

## Journey verdict

The application can complete many individual steps, but the visible journey does not form one coherent author workflow. A technically informed tester can infer the authority model. A normal author will see multiple contradictory versions of story state.

## Journey findings

| Journey step | Result | Novice-author assessment |
|---|---|---|
| Create Project | Works | Clear enough; project library contains many similarly named validation projects in this environment, which reduces findability |
| Story Studio discussion | Partial | Useful questions and brainstorming; history is long and confirmed/candidate/rejected states are not actionable |
| Develop Story | Partial/fail | Long run, large hidden context, unconfirmed Kael plan; no clear preview of what becomes structure |
| Write Chapter 1 | Works with friction | Target controls are understandable; generation state can become stale |
| Review Chapter 1 | Partial | Editorial and approval concepts are protected, but the approval button did not reliably refresh visible state |
| Approve | Partial | API state became approved while the Writing UI still showed draft until refresh |
| See what was learned | Confusing | Story Knowledge shows 28 suggestions and Canon shows 0 facts; candidate extraction is not explained at the moment of approval |
| Continue Chapter 2 | Fail | Retry targeting can create a different chapter; Chapter 2 was a hard identity break |
| Return later | Partial | Dashboard and Companion surface recommendations, but milestone and health are inconsistent |
| Find previous chapters | Works | Writing library exposes ten chapters and versions, but raw duplicate lineage is not trustworthy |
| Edit Chapter 1 | Partial | Editorial path protects source, but whole-chapter revision failed and selection revision is not obvious |
| Characters/world/mysteries | Confusing | Pages are populated with provisional Develop artifacts that conflict with the generated/approved story |
| Relationships/timeline | Confusing | Graph and timeline names/anchors reflect Kael/farm/well planning and candidate state in mixed presentations |
| Companion | Partial | Recommendations are relevant but compete with Story Studio and can say “Getting oriented” or “Review Chapter 2” without a clear explanation of the mixed workflow |
| Review health | Misleading | Story Health score and Dashboard progress suggest a healthier/earlier project state than the author sees in Writing |
| Understand next action | Partial | “Review Chapter 2” is technically the lifecycle next action, but the application does not warn that Chapter 2 is unsafe and unapproved |

## Most confusing surfaces

### Discovery Writing versus Drafting

Writing contains ten discovery chapters, while the controlled Drafting Toolbox says “Your first chapter starts here” and waits for approved scene drafts. The author is not told whether these are two ways to write, two stages of one workflow, or two separate products.

### Characters, World, Arcs, and Timeline

These pages are populated and visually credible, but their main records are provisional Develop outputs: Kael, a farm, Thornwick, a well, and a buried-sky plan. Suggestions from approved Chapter 1 are shown separately, yet the visual hierarchy makes the provisional plan look like the story's current truth.

### Knowledge and Canon

After approving Chapter 1, Knowledge showed suggestions and Canon showed zero facts. This can be authority-correct, but the UI does not explain the difference between “noticed,” “candidate,” “confirmed,” and “canon,” or what the author should do next.

### Dashboard and Companion

Dashboard said “Chapter 1 approved,” “10 chapters saved,” and “Continue with Chapter 2,” while the Companion returned `current_milestone=Getting Started`, `story_health=81`, and a next action of “At least one theme.” The Dashboard had also shown a health/milestone state that did not match the Companion. This creates distrust.

### Editorial

Editorial says source drafts are protected and alternatives are reviewable, which is good. The full revision failure, the unlabelled browser prompt for branch creation, and the weak visibility of branch/version state make the safe behavior hard to use.

## Product-quality conclusion

The visible application is not yet a single author home. It is a collection of strong architectural surfaces whose state transitions are not sufficiently unified. Before literary refinement, the product needs a single writing-state model rendered consistently across Dashboard, Companion, Writing, Story Knowledge, Canon, and Toolbox.

