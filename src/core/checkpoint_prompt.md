OUTPUT FORMAT — You MUST respond with a JSON checkpoint report. No preamble, no markdown around the JSON (use a ```json code fence OR bare JSON):

```json
{
  "state": "<in_progress|done|blocked|needs_input>",
  "summary": "<1-3 sentence summary of what happened>",
  "details": "<technical details: files changed, commands run, decisions made>",
  "blocker": "<if blocked: what's preventing progress>",
  "next_steps": "<what should happen next>",
  "evidence": ["<concrete item>", "<another item>"]
}
```

STATE RULES:
- `done` — task completed with concrete results. REQUIRES evidence.
- `in_progress` — work started but not finished. Include next_steps.
- `blocked` — cannot continue. REQUIRES blocker field with reason.
- `needs_input` — needs clarification or data from user.

EVIDENCE RULES:
- Must contain concrete indicators: numbers, file paths, URLs, commands executed, checkmarks
- At least 1 evidence item for `done` state
- NEVER use vague phrases like "everything works", "all good", "task completed"
- NEVER say "done." as the only summary

QUALITY:
- Technical precision, no fluff
- Spanish or English accepted
- If you don't know something, say so
- Be honest about blockers — don't hide them
