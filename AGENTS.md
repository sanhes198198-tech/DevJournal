\# DevJournal - Codex Instructions



\## Project



DevJournal is an existing desktop Vector Editor project.



This is an existing codebase. Preserve the current architecture unless the task explicitly requires architectural changes.



\## General rules



Before changing code:



1\. Inspect the existing implementation.

2\. Find all references to the affected code.

3\. Trace runtime dependencies.

4\. Check UI dependencies.

5\. Check serialization and persistence.

6\. Check tests and scripts.

7\. Explain the proposed change.

8\. Only then modify files.



Do not make broad speculative refactors.



Do not rewrite working systems merely to make them stylistically cleaner.



Do not modify unrelated files.



\## Git safety



Never run destructive Git commands without explicit user approval.



Do not run:



\- git reset --hard

\- git clean -fd

\- git push --force

\- git branch -D



Do not create commits unless explicitly requested.



Do not push to GitHub unless explicitly requested.



Before substantial changes, inspect:



git status

git diff



\## Code changes



Prefer small, targeted changes.



Before removing any class, method, field, module, or subsystem:



\- find every reference;

\- determine whether it is used at runtime;

\- determine whether it is used by the UI;

\- determine whether it is serialized;

\- determine whether tests or scripts depend on it.



Do not delete code based only on filename or apparent lack of references.



\## Architecture



Pay particular attention to interactions between:



\- Asset

\- ComponentItem

\- Group

\- Attachment

\- Snap

\- Anchors

\- auto\_rule

\- Editor

\- UI

\- serialization

\- undo/redo



When modifying model behavior, inspect the affected editor and UI paths as well.



\## Testing



After making changes:



1\. Run the most relevant tests.

2\. Run syntax/import checks when appropriate.

3\. Report all failures.

4\. Do not hide test failures.

5\. Do not modify tests merely to make them pass unless explicitly requested.



\## Working style



For architectural tasks:



First provide:

\- current behavior;

\- dependency map;

\- proposed changes;

\- affected files;

\- risks.



Then implement only after the plan is clear.



For bug fixes:



First reproduce or identify the failure path.



Then make the smallest reliable fix.



After the change, inspect git diff and verify that unrelated files were not modified.

