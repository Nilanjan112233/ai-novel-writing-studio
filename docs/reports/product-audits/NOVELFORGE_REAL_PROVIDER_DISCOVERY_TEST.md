# NovelForge Real Provider Discovery Test

## Result

A fresh dedicated project (`6a7765ab6873ed058569f36d`) produced six consecutive approved Discovery Writing chapters through the running UI and the existing provider gateway. The provider used was OpenRouter / `deepseek/deepseek-v4-flash`; no direct provider bypass was used.

Each chapter followed instruction → generate → review → approve. Approved prose triggered the normal extraction and chapter-intelligence lifecycle. Chapter 6 deliberately used a sparse continuation instruction and relied on retrieved project context.

| Chapter | Status | Words | Requested range | Result |
|---:|---|---:|---|---|
| 1 | approved | 1,735 | 1,000–1,200 | above maximum |
| 2 | approved | 1,128 | 1,000–1,200 | compliant |
| 3 | approved | 1,179 | 1,500–2,000 | below minimum after bounded correction |
| 4 | approved | 2,573 | 2,000–3,000 | compliant |
| 5 | approved | 1,101 | 1,000–1,200 | compliant after correction |
| 6 | approved | 1,177 | 1,000–1,200 | compliant |

All six chapters met the hard acceptance floor of 1,000 words. The run demonstrates usable multi-chapter writing, but not universal compliance with arbitrary ranges.

## Continuity evidence

The chapter-6 instruction did not restate Northglass, Mara’s injury, the marsh, the map, Ivo’s withheld knowledge, or the Elias mystery. The generated chapter nevertheless used those facts and advanced them: Northglass was in Ivo’s hand, Mara’s palm scar reacted, Elias’s map and promise mattered, the marsh opened, and Ivo revealed that Elias was alive. This is direct evidence that the native context path contributed to continuity.

## Acceptance judgment

Pass for a real-provider six-chapter smoke/soak workflow and the 1,000-word floor. Conditional pass for production-quality Discovery Writing because extraction quality and exact range enforcement remain uneven, and the author-change propagation test could not reach a canonical fact in this newly created project without inventing authority.

