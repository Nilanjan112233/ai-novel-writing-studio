# NovelForge Project Name vs Story Title Report

## Implemented

Projects now support separate reader-facing and workspace-facing identity fields:

- `project_name`: internal workspace/library identifier;
- `story_title`: optional novel title, defaulting to Untitled when blank;
- legacy `title` remains compatible as the project-name alias.

The backend schemas, project creation/update APIs, library projection, context packet, manuscript default, and relevant frontend surfaces were updated without replacing the existing project authority.

## Browser evidence

The fresh project remained named `Memory Fantasy Experiment`. The author set the independent story title to `The Debt Beneath the River`. The project header showed both separately, and the Projects library displayed:

`Memory Fantasy Experiment` / `Novel: The Debt Beneath the River`.

## Behavior

An author can leave the story title blank/Untitled. Reader-facing manuscript defaults use the story title, while project management continues to use the project name.
