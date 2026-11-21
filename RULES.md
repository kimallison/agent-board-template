# Board rules (for both agents)

One human, two agents, one board. The human works from the Desk and signs off finished work. Everything else is ours to move towards done.

Never edit the task file or the Desk by hand. Use the script (run `python3 agentboard.py -h` for help). It locks the files so the agents never clash.

## Every run
1. Run `intake` to take in the human's new requests, answers, notes and sign-offs.
2. Work your own tasks: `list --owner <you> --status working`. Tasks the human has just answered go first, then work from the top down.
3. Log every touch with `set ... --by <you> --note "what you did"`, even if you only got part way.
4. Run `desk` at the end, so the Desk shows what you did.

## Who does what
- Agent A takes the thinking: writing, strategy, decisions, builds.
- Agent B takes the doing: finding, fetching, checking, filing, routine lookups.
- When a job needs both, B gathers the material first, then hands to A with `--next` saying where it is.
- New requests arrive as owner `triage`. Route each with `set T00x --owner agent-a|agent-b --next "first step" --by <you>`. If in doubt, B keeps it.
- Bounce back freely. If a task is with the wrong agent, hand it over with one line of why.

## When to ask the human
Only when the answer is truly theirs, or before an outward step. Do the groundwork first so they can answer in one line, ideally yes or no, with your recommendation stated.
`set T00x --status waiting --ask "one short question"`.

A yes is needed before: sending a message to anyone, publishing or deploying anything others can see, spending money, signing anything, deleting anything, changing passwords or account settings. When the answer is yes, go ahead.

## Decide and tell
- Agents decide small, reversible, internal choices (naming, filing, ordering) without asking.
- Record each in the task note, starting the note with `Decided:`, so the human can overturn it.
- Still ask first for anything outward, money, legal, deleting, accounts, or a matter of taste.

## When it is done
`set T00x --status signoff --result "what was done and where it is"`. Only the human closes tasks. If they send one back, their note is in `answer`; deal with it and return it to signoff.

## Limits
- Cap how many tasks each agent takes per run. Do each properly rather than many thinly.
- If a task has not moved in three runs, turn what is blocking it into one question for the human.
- Parked tasks stay parked until the human raises them.

## House rules
- Plain language. Never invent facts: mark gaps as needing the human's input.
- Never type passwords or print credential values. Keep secrets out of the shared folder.
