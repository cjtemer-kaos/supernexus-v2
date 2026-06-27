"""
prompter_knowledge — Knowledge base for the prompter gema.

Ported from nidhinjs/prompt-master v1.6.0 (MIT License).
Source: https://github.com/nidhinjs/prompt-master

Contiene:
  - 13 templates (A-M) validados con campo, ejemplo y best_for.
  - 37 credit-killing patterns organizados en 6 categorías.
  - Helpers para lookup, detección heurística y formateo.

Diseño:
  - Data pura (dicts/lists) — no side effects, no I/O.
  - Detección por keyword matching best-effort (no LLM dependency).
  - Las funciones helper son sincrónicas y stateless.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# Metadata
# ============================================================================

KB_VERSION = "1.6.0"
KB_SOURCE = "https://github.com/nidhinjs/prompt-master"
KB_LICENSE = "MIT"
KB_LOCAL_MIRROR = os.environ.get("PROMPT_MASTER_PATH", "")

CATEGORIES: Tuple[str, ...] = (
    "task", "context", "format", "scope", "reasoning", "agentic",
)

# ============================================================================
# 13 Templates (A-M)
# ============================================================================

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "A": {
        "name": "RTF",
        "full_name": "Role, Task, Format",
        "best_for": "Simple one-shot tasks where the request is clear and simple",
        "fields": ["role", "task", "format"],
        "template": (
            "Role: [One sentence defining who the AI is]\n"
            "Task: [Precise verb + what to produce]\n"
            "Format: [Exact output format and length]"
        ),
        "example": (
            "Role: You are a senior technical writer.\n"
            "Task: Write a one-paragraph description of what a REST API is.\n"
            "Format: Plain prose, 3 sentences maximum, no jargon, suitable for a "
            "non-technical audience."
        ),
    },
    "B": {
        "name": "CO-STAR",
        "full_name": "Context, Objective, Style, Tone, Audience, Response",
        "best_for": "Professional documents, business writing, reports, marketing",
        "fields": ["context", "objective", "style", "tone", "audience", "response"],
        "template": (
            "Context: [Background the AI needs to understand the situation]\n"
            "Objective: [Exact goal — what success looks like]\n"
            "Style: [Writing style: formal / conversational / technical / narrative]\n"
            "Tone: [Emotional register: authoritative / empathetic / urgent / neutral]\n"
            "Audience: [Who reads this — their knowledge level and expectations]\n"
            "Response: [Format, length, and structure of the output]"
        ),
        "example": (
            "Context: I am a founder pitching a B2B SaaS tool that automates expense "
            "reporting for mid-size companies.\n"
            "Objective: Write a cold email that gets a reply from a CFO.\n"
            "Style: Direct and conversational, not salesy.\n"
            "Tone: Confident but not pushy.\n"
            "Audience: CFO at a 200-person company, busy, skeptical of vendor emails.\n"
            "Response: 5 sentences max. Subject line included. No bullet points."
        ),
    },
    "C": {
        "name": "RISEN",
        "full_name": "Role, Instructions, Steps, End Goal, Narrowing",
        "best_for": "Complex multi-step projects requiring clear sequence of actions",
        "fields": ["role", "instructions", "steps", "end_goal", "narrowing"],
        "template": (
            "Role: [Expert identity the AI should adopt]\n"
            "Instructions: [Overall task in plain terms]\n"
            "Steps:\n"
            "  1. [First action]\n"
            "  2. [Second action]\n"
            "  3. [Continue as needed]\n"
            "End Goal: [What the final output must achieve]\n"
            "Narrowing: [Constraints, scope limits, what to exclude]"
        ),
        "example": (
            "Role: You are a product manager with 10 years of experience in mobile apps.\n"
            "Instructions: Write a product requirements document for a habit tracking "
            "feature.\n"
            "Steps:\n"
            "  1. Define the problem statement in one paragraph\n"
            "  2. List user stories in the format 'As a [user], I want [goal] so that "
            "[reason]'\n"
            "  3. Define acceptance criteria for each story\n"
            "  4. List out-of-scope items explicitly\n"
            "End Goal: A PRD that an engineering team can begin sprint planning from "
            "immediately.\n"
            "Narrowing: No technical implementation details. No wireframes. Under 600 "
            "words total."
        ),
    },
    "D": {
        "name": "CRISPE",
        "full_name": "Capacity, Role, Insight, Statement, Personality, Experiment",
        "best_for": "Creative work, brand voice writing, personality-driven tasks",
        "fields": ["capacity", "role", "insight", "statement", "personality", "experiment"],
        "template": (
            "Capacity: [What capability or expertise the AI should have]\n"
            "Role: [Specific persona to adopt]\n"
            "Insight: [Key background insight that shapes the response]\n"
            "Statement: [The core task or question]\n"
            "Personality: [Tone and style — witty / authoritative / casual / sharp]\n"
            "Experiment: [Request variants or alternatives to explore]"
        ),
        "example": (
            "Capacity: Expert copywriter specializing in SaaS product launches.\n"
            "Role: Brand voice for a productivity tool aimed at developers.\n"
            "Insight: Developers hate marketing speak and respond to honesty and "
            "specificity.\n"
            "Statement: Write the hero headline and sub-headline for the landing page.\n"
            "Personality: Sharp, dry, confident — no adjectives, no exclamation marks.\n"
            "Experiment: Give 3 variants ranging from minimal to bold."
        ),
    },
    "E": {
        "name": "Chain of Thought",
        "full_name": "Chain of Thought",
        "best_for": (
            "Logic, math, debugging, multi-factor analysis. "
            "Do NOT use with reasoning-native models (o1/o3, DeepSeek-R1, "
            "Qwen3 thinking, MiniMax thinking)."
        ),
        "fields": ["task", "thinking", "answer"],
        "template": (
            "[Task statement]\n\n"
            "Before answering, think through this carefully:\n"
            "<thinking>\n"
            "1. What is the actual problem being asked?\n"
            "2. What constraints must the solution respect?\n"
            "3. What are the possible approaches?\n"
            "4. Which approach is best and why?\n"
            "</thinking>\n\n"
            "Give your final answer in <answer> tags only."
        ),
        "example": (
            "[Task statement]\n\n"
            "Before answering, think through this carefully:\n"
            "<thinking>\n"
            "1. What is the actual problem being asked?\n"
            "2. What constraints must the solution respect?\n"
            "3. What are the possible approaches?\n"
            "4. Which approach is best and why?\n"
            "</thinking>\n\n"
            "Give your final answer in <answer> tags only."
        ),
    },
    "F": {
        "name": "Few-Shot",
        "full_name": "Few-Shot Examples",
        "best_for": "Consistent structured output, pattern replication, format-sensitive tasks",
        "fields": ["task_instruction", "examples", "actual_input"],
        "template": (
            "[Task instruction]\n\n"
            "Here are examples of the exact format needed:\n\n"
            "<examples>\n"
            "  <example>\n"
            "    <input>[example input 1]</input>\n"
            "    <output>[example output 1]</output>\n"
            "  </example>\n"
            "  <example>\n"
            "    <input>[example input 2]</input>\n"
            "    <output>[example output 2]</output>\n"
            "  </example>\n"
            "</examples>\n\n"
            "Now apply this exact pattern to: [actual input]"
        ),
        "example": (
            "See template — 2-5 examples is the sweet spot. Examples must include "
            "edge cases, not just easy cases. Use XML tags to wrap examples."
        ),
        "rules": (
            "2 to 5 examples is the sweet spot. More rarely helps and wastes tokens. "
            "Examples must include edge cases. Use XML tags. If re-prompting for the "
            "same formatting correction twice, switch to few-shot instead of rewriting "
            "instructions."
        ),
    },
    "G": {
        "name": "File-Scope",
        "full_name": "File-Scope (for IDE AI)",
        "best_for": "Cursor, Windsurf, GitHub Copilot, Cline, Bolt — any code-editing AI",
        "fields": [
            "file", "function_or_component", "current_behavior", "desired_change",
            "scope", "constraints", "done_when",
        ],
        "template": (
            "File: [exact/path/to/file.ext]\n"
            "Function/Component: [exact name]\n\n"
            "Current Behavior:\n"
            "[What this code does right now — be specific]\n\n"
            "Desired Change:\n"
            "[What it should do after the edit — be specific]\n\n"
            "Scope:\n"
            "Only modify [function / component / section].\n"
            "Do NOT touch: [list everything to leave unchanged]\n\n"
            "Constraints:\n"
            "- Language/framework: [specify version]\n"
            "- Do not add dependencies not in [package.json / requirements.txt]\n"
            "- Preserve existing [type signatures / API contracts / variable names]\n\n"
            "Done When:\n"
            "[Exact condition that confirms the change worked correctly]"
        ),
        "example": (
            "File: src/auth/handleLogin.ts\n"
            "Function/Component: handleLogin()\n\n"
            "Current Behavior:\n"
            "Returns Promise<User> on success, throws on network errors, does not "
            "validate input.\n\n"
            "Desired Change:\n"
            "Validate input (email format, password length >= 8). Return "
            "{ ok: true, user } or { ok: false, error } instead of throwing.\n\n"
            "Scope:\n"
            "Only modify handleLogin() in src/auth/handleLogin.ts.\n"
            "Do NOT touch: types/auth.ts, the /register endpoint, or any test file.\n\n"
            "Constraints:\n"
            "- TypeScript strict, no any.\n"
            "- Do not add dependencies.\n"
            "- Preserve existing function signature shape (Promise-based).\n\n"
            "Done When:\n"
            "Unit tests pass. New error path returns structured result, not throw."
        ),
    },
    "H": {
        "name": "ReAct+Stop",
        "full_name": "ReAct + Stop Conditions (for autonomous agents)",
        "best_for": "Claude Code, Devin, AutoGPT, Cline, OpenClaw — autonomous agents",
        "fields": [
            "objective", "starting_state", "target_state", "allowed_actions",
            "forbidden_actions", "stop_conditions", "checkpoints",
        ],
        "template": (
            "Objective:\n"
            "[Single, unambiguous goal in one sentence]\n\n"
            "Starting State:\n"
            "[Current file structure / codebase state / environment]\n\n"
            "Target State:\n"
            "[What should exist when the agent is done]\n\n"
            "Allowed Actions:\n"
            "- [Specific action the agent may take]\n"
            "- Install only packages listed in [requirements.txt / package.json]\n\n"
            "Forbidden Actions:\n"
            "- Do NOT modify files outside [directory/scope]\n"
            "- Do NOT run the dev server or deploy\n"
            "- Do NOT push to git\n"
            "- Do NOT delete files without showing a diff first\n"
            "- Do NOT make architecture decisions without human approval\n\n"
            "Stop Conditions:\n"
            "Pause and ask for human review when:\n"
            "- A file would be permanently deleted\n"
            "- A new external service or API needs to be integrated\n"
            "- Two valid implementation paths exist and the choice affects architecture\n"
            "- An error cannot be resolved in 2 attempts\n"
            "- The task requires changes outside the stated scope\n\n"
            "Checkpoints:\n"
            "After each major step, output: ✅ [what was completed]\n"
            "At the end, output a full summary of every file changed."
        ),
        "example": (
            "Objective: Add email + password login to the existing Next.js app.\n\n"
            "Starting State: Next.js 14 app with app router, no auth library "
            "installed, src/app/(public)/page.tsx exists.\n\n"
            "Target State: src/app/(auth)/login/page.tsx, src/app/api/auth/[...nextauth]/"
            "route.ts, session cookie working, redirect to /dashboard on success.\n\n"
            "Allowed Actions: edit files in src/app/, add next-auth to package.json, "
            "run npm install.\n\n"
            "Forbidden Actions: do not touch .env, do not modify tsconfig.json, do "
            "not run dev server.\n\n"
            "Stop Conditions: pause if NEXTAUTH_SECRET needs to be set, or if a DB "
            "schema change is needed.\n\n"
            "Checkpoints: after each file change, output ✅ and the file path."
        ),
    },
    "I": {
        "name": "Visual Descriptor",
        "full_name": "Visual Descriptor (image/video generation)",
        "best_for": "Midjourney, DALL-E 3, Stable Diffusion, Sora, Runway, ComfyUI",
        "fields": [
            "subject", "action_or_pose", "setting", "style", "mood", "lighting",
            "color_palette", "composition", "aspect_ratio", "negative_prompts",
            "style_reference",
        ],
        "template": (
            "Subject: [Main subject — specific, not vague]\n"
            "Action/Pose: [What the subject is doing]\n"
            "Setting: [Where the scene takes place]\n"
            "Style: [photorealistic / cinematic / anime / oil painting / vector / etc.]\n"
            "Mood: [dramatic / serene / eerie / joyful / etc.]\n"
            "Lighting: [golden hour / studio / neon / overcast / candlelight / etc.]\n"
            "Color Palette: [dominant colors or named palette]\n"
            "Composition: [wide shot / close-up / aerial / Dutch angle / etc.]\n"
            "Aspect Ratio: [16:9 / 1:1 / 9:16 / 4:3]\n"
            "Negative Prompts: [blurry, watermark, extra fingers, distortion, "
            "low quality]\n"
            "Style Reference: [artist / film / aesthetic reference if applicable]"
        ),
        "example": (
            "Subject: lone samurai in traditional armor, katana sheathed\n"
            "Action/Pose: standing still, looking at camera\n"
            "Setting: neon-lit Tokyo street, heavy rain, wet cobblestone\n"
            "Style: photorealistic, cinematic\n"
            "Mood: dramatic, melancholic\n"
            "Lighting: night, neon reflections, fog\n"
            "Color Palette: deep blues, reds, blacks\n"
            "Composition: low-angle medium shot\n"
            "Aspect Ratio: 16:9\n"
            "Negative Prompts: blurry, watermark, cartoon, anime, extra limbs\n"
            "Style Reference: Blade Runner 2049 cinematography"
        ),
    },
    "J": {
        "name": "Reference Image Editing",
        "full_name": "Reference Image Editing",
        "best_for": "Editing an existing image with a reference (Midjourney --cref, img2img, etc.)",
        "fields": [
            "reference_image", "what_to_keep", "what_to_change", "how_much_to_change",
            "style_consistency", "negative_prompt",
        ],
        "template": (
            "Reference image: [attached / URL]\n"
            "What to keep exactly the same: [list everything that must not change]\n"
            "What to change: [specific edit only — be precise]\n"
            "How much to change: [subtle / moderate / significant]\n"
            "Style consistency: maintain the exact style, lighting, and mood of the "
            "reference\n"
            "Negative prompt: [what to avoid introducing]"
        ),
        "example": (
            "Reference image: [attached portrait photo]\n"
            "What to keep exactly the same: face, hair, clothing, background, "
            "lighting\n"
            "What to change: head angle — rotate from facing left to facing straight "
            "forward\n"
            "How much to change: subtle, preserve all facial features exactly\n"
            "Style consistency: maintain photorealistic style, same lighting direction\n"
            "Negative prompt: no new elements, no style changes, no background changes"
        ),
        "preamble": (
            "Before writing the prompt, always tell the user: 'Attach your reference "
            "image to [tool name] before sending this prompt.'"
        ),
    },
    "K": {
        "name": "ComfyUI",
        "full_name": "ComfyUI (positive/negative split)",
        "best_for": "ComfyUI node-based image workflows (SD 1.5, SDXL, Flux, ...)",
        "fields": [
            "positive_prompt", "negative_prompt", "checkpoint", "sampler",
            "cfg_scale", "steps", "resolution",
        ],
        "template": (
            "POSITIVE PROMPT:\n"
            "[subject], [style], [mood], [lighting], [composition], "
            "[quality boosters: highly detailed, sharp focus, 8k]\n\n"
            "NEGATIVE PROMPT:\n"
            "[what to exclude: blurry, low quality, watermark, extra limbs, "
            "bad anatomy, distorted, oversaturated]\n\n"
            "CHECKPOINT: [model name]\n"
            "SAMPLER: Euler a (recommended starting point)\n"
            "CFG SCALE: 7 (increase for stricter prompt adherence)\n"
            "STEPS: 20-30\n"
            "RESOLUTION: [width x height — must be divisible by 64]"
        ),
        "example": (
            "POSITIVE PROMPT:\n"
            "cyberpunk street market at night, neon signs, rain, "
            "cinematic, moody, blue and pink lighting, 35mm, 8k, "
            "highly detailed\n\n"
            "NEGATIVE PROMPT:\n"
            "blurry, low quality, watermark, extra fingers, cartoon, "
            "oversaturated\n\n"
            "CHECKPOINT: dreamshaperXL_v21TurboDPMSDE.safetensors\n"
            "SAMPLER: Euler a\n"
            "CFG SCALE: 7\n"
            "STEPS: 25\n"
            "RESOLUTION: 1024 x 1024"
        ),
        "preamble": (
            "Always output Positive and Negative prompts as separate blocks. Ask "
            "for the checkpoint model before writing."
        ),
    },
    "L": {
        "name": "Prompt Decompiler",
        "full_name": "Prompt Decompiler (break down / adapt / simplify / split)",
        "best_for": "Analyzing and adapting an existing prompt to a different tool or context",
        "fields": ["mode", "original_prompt", "output_format"],
        "template": (
            "Mode: [break_down | adapt | simplify | split]\n"
            "Original prompt: [paste]\n\n"
            "Output format:\n"
            "- break_down: Structure analysis (Role/Task/Constraints/Format/Weaknesses/"
            "Recommended fix)\n"
            "- adapt: Original ([source tool]): ... / Adapted for [target tool]: ... / "
            "Key changes made: ...\n"
            "- simplify: tightened version, preserving intent\n"
            "- split: N sequential prompts if the original is doing N things"
        ),
        "example": (
            "Mode: break_down\n"
            "Original prompt: [paste your prompt here]\n\n"
            "Structure analysis:\n"
            "- Role/Identity: [what role is assigned and why]\n"
            "- Task: [what action is being requested]\n"
            "- Constraints: [what limits are set]\n"
            "- Format: [what output shape is expected]\n"
            "- Weaknesses: [what is missing or could cause wrong output]\n"
            "Recommended fix: [rewritten version with gaps filled]"
        ),
    },
    "M": {
        "name": "Opus 4.7 Task Brief",
        "full_name": "Opus 4.7 Task Brief",
        "best_for": (
            "Complex, multi-step, or agentic tasks on Claude Opus 4.7 (claude.ai, API, "
            "Claude Code). Opus reads prompts literally — missing context produces "
            "narrow output. Front-load everything so the first turn is the only turn."
        ),
        "fields": [
            "objective", "context", "target_state", "scope", "constraints",
            "acceptance_criteria", "stop_conditions", "progress", "session_strategy",
        ],
        "template": (
            "## Objective\n"
            "[What needs to be built, fixed, or produced — one clear sentence. Add "
            "WHY if it affects approach.]\n\n"
            "## Context\n"
            "[What exists now — relevant files, current behavior, stack already in "
            "place, what was tried and failed]\n\n"
            "## Target State\n"
            "[What done looks like — specific files changed, behavior produced, tests "
            "passing. Binary where possible.]\n\n"
            "## Scope\n"
            "- Work only in: [specific files and directories]\n"
            "- Do NOT touch: [forbidden files — .env, package-lock.json, configs, "
            "anything outside scope]\n\n"
            "## Constraints\n"
            "- [Stack version, naming conventions, no new dependencies without asking]\n"
            "- Only make changes directly requested. Do not add features, abstractions, "
            "or files beyond what was asked.\n\n"
            "## Acceptance Criteria\n"
            "- [ ] [Binary check 1]\n"
            "- [ ] [Binary check 2]\n"
            "- [ ] [Binary check 3]\n\n"
            "## Stop Conditions\n"
            "Stop and ask before:\n"
            "- Deleting any file\n"
            "- Adding any dependency\n"
            "- Modifying database schema or migrations\n"
            "- Touching anything outside Scope\n\n"
            "## Progress\n"
            "After each completed step: ✅ [what was done] — [file(s) affected]"
        ),
        "example": (
            "## Objective\n"
            "Fix the OAuth callback bug in production. WHY: blocks 12% of signups.\n\n"
            "## Context\n"
            "Next.js 14 app, src/app/api/auth/callback/route.ts. State param is being "
            "dropped on redirect. Already tried logging the state — it's missing from "
            "the redirect URL.\n\n"
            "## Target State\n"
            "OAuth callback preserves state. Production test login succeeds end-to-end. "
            "Unit test added for the state preservation.\n\n"
            "## Scope\n"
            "- Work only in: src/app/api/auth/callback/route.ts, "
            "tests/api/auth-callback.test.ts\n"
            "- Do NOT touch: any other auth files, the OAuth provider config\n\n"
            "## Constraints\n"
            "- No new dependencies\n"
            "- Preserve existing function signatures\n\n"
            "## Acceptance Criteria\n"
            "- [ ] Manual login with Google succeeds and lands on /dashboard\n"
            "- [ ] Unit test for state preservation passes\n"
            "- [ ] No console errors during the flow\n\n"
            "## Stop Conditions\n"
            "Stop and ask before changing the OAuth provider config or any env var.\n\n"
            "## Progress\n"
            "After each step: ✅ [what was done] — [file(s) affected]"
        ),
    },
}


# ============================================================================
# 37 Credit-Killing Patterns (organized by category)
# ============================================================================

PATTERNS: Dict[str, List[Dict[str, Any]]] = {
    "task": [
        {
            "id": 1, "name": "vague_task_verb",
            "description": "Vague task verb with no concrete deliverable",
            "before": "help me with my code",
            "after": "Refactor getUserData() to use async/await and handle null returns",
            "fix_hint": "Replace 'help with' / 'do something' with a precise verb "
                        "+ specific artifact.",
        },
        {
            "id": 2, "name": "two_tasks_in_one_prompt",
            "description": "Two distinct tasks crammed into a single prompt",
            "before": "explain AND rewrite this function",
            "after": "Split into two prompts: explain first, rewrite second",
            "fix_hint": "If you have two goals, send two prompts. Sequential beats "
                        "concurrent for distinct deliverables.",
        },
        {
            "id": 3, "name": "no_success_criteria",
            "description": "No 'done when' or measurable success condition",
            "before": "make it better",
            "after": "Done when the function passes existing unit tests and handles "
                     "null input without throwing",
            "fix_hint": "Always include a binary success condition. 'Better' is not "
                        "a condition.",
        },
        {
            "id": 4, "name": "over_permissive_agent",
            "description": "Over-permissive agent with no action boundary",
            "before": "do whatever it takes",
            "after": (
                "Explicit allowed actions list + explicit forbidden actions list. "
                "See ReAct+Stop (Template H)."
            ),
            "fix_hint": "For agents, always define allowed + forbidden actions. "
                        "Open-ended autonomy burns credits.",
        },
        {
            "id": 5, "name": "emotional_task_description",
            "description": "Emotional venting in place of a concrete error report",
            "before": "it's totally broken, fix everything",
            "after": "Throws uncaught TypeError on line 43 when user is null",
            "fix_hint": "State the symptom (error, line, input) — not the feeling.",
        },
        {
            "id": 6, "name": "build_the_whole_thing",
            "description": "Asking for the entire app in one shot",
            "before": "build my entire app",
            "after": (
                "Break into Prompt 1 (scaffold), Prompt 2 (core feature), "
                "Prompt 3 (polish)"
            ),
            "fix_hint": "Decompose into 3-5 sequential prompts. Each builds on the "
                        "previous.",
        },
        {
            "id": 7, "name": "implicit_reference",
            "description": "Implicit reference to a prior conversation",
            "before": "now add the other thing we discussed",
            "after": "Always restate the full task — never reference 'the thing we "
                     "discussed'",
            "fix_hint": "Restate the full context. Sessions don't share memory by "
                        "default — use a Memory Block.",
        },
    ],
    "context": [
        {
            "id": 8, "name": "assumed_prior_knowledge",
            "description": "Assumes the AI has context it does not have",
            "before": "continue where we left off",
            "after": "Include Memory Block with all prior decisions",
            "fix_hint": "New session = blank slate. Front-load every fact the AI "
                        "needs.",
        },
        {
            "id": 9, "name": "no_project_context",
            "description": "Generic request with no project-specific context",
            "before": "write a cover letter",
            "after": (
                "PM role at B2B fintech, 2yr SWE experience transitioning to "
                "product, shipped 3 features as tech lead"
            ),
            "fix_hint": "Add 3-5 facts about you + the target audience + the "
                        "situation.",
        },
        {
            "id": 10, "name": "forgotten_stack",
            "description": "New prompt contradicts prior tech choices",
            "before": "New prompt asks for Redux when prior prompt chose Context API",
            "after": "Always include Memory Block with established stack",
            "fix_hint": "If a decision was made before, restate it. Don't make the AI "
                        "guess.",
        },
        {
            "id": 11, "name": "hallucination_invite",
            "description": "Phrasing that invites the AI to invent sources",
            "before": "what do experts say about X?",
            "after": (
                "Cite only sources you are certain of. If uncertain, say so "
                "explicitly rather than guessing."
            ),
            "fix_hint": "Add a grounding rule: 'say [uncertain] if not'.",
        },
        {
            "id": 12, "name": "undefined_audience",
            "description": "No specification of who reads the output",
            "before": "write something for users",
            "after": "Non-technical B2B buyers, no coding knowledge, "
                     "decision-maker level",
            "fix_hint": "Name the audience + their knowledge level + their "
                        "decision-making role.",
        },
        {
            "id": 13, "name": "no_prior_failures",
            "description": "Doesn't mention what was already tried",
            "before": "(blank)",
            "after": "I already tried X and it didn't work because Y. "
                     "Do not suggest X.",
            "fix_hint": "Save the AI's time by explicitly ruling out dead ends.",
        },
    ],
    "format": [
        {
            "id": 14, "name": "missing_output_format",
            "description": "No specification of the output format",
            "before": "explain this concept",
            "after": "3 bullet points, each under 20 words, with a one-sentence "
                     "summary at top",
            "fix_hint": "Always specify length + structure. 'Explain' invites an "
                        "essay.",
        },
        {
            "id": 15, "name": "implicit_length",
            "description": "No length specification",
            "before": "write a summary",
            "after": "Write a summary in exactly 3 sentences",
            "fix_hint": "Use a number, not 'short' or 'brief'.",
        },
        {
            "id": 16, "name": "no_role_assignment",
            "description": "No expert persona assigned",
            "before": "(blank)",
            "after": "You are a senior backend engineer specializing in Node.js and "
                     "PostgreSQL",
            "fix_hint": "Role assignment calibrates depth and vocabulary. One sentence "
                        "is enough.",
        },
        {
            "id": 17, "name": "vague_aesthetic_adjectives",
            "description": "Vague aesthetic adjectives with no concrete spec",
            "before": "make it look professional",
            "after": "Monochrome palette, 16px base font, 24px line height, "
                     "no decorative elements",
            "fix_hint": "Translate adjectives into concrete numbers (hex, px, "
                        "spacing).",
        },
        {
            "id": 18, "name": "no_negative_prompts_image",
            "description": "No negative prompt for image AI",
            "before": "a portrait of a woman",
            "after": "Add: 'no watermark, no blur, no extra fingers, no distortion, "
                     "no text overlay'",
            "fix_hint": "Image AI without a negative prompt drifts. Always include "
                        "what to avoid.",
        },
        {
            "id": 19, "name": "prose_for_midjourney",
            "description": "Full sentence instead of comma-separated descriptors",
            "before": "Full descriptive sentence for Midjourney",
            "after": "subject, style, mood, lighting, --ar 16:9 --v 6",
            "fix_hint": "Midjourney prefers comma-separated descriptors + flags at "
                        "the end.",
        },
    ],
    "scope": [
        {
            "id": 20, "name": "no_scope_boundary",
            "description": "No boundary on what the AI may touch",
            "before": "fix my app",
            "after": "Fix only the login form validation in src/auth.js. "
                     "Touch nothing else.",
            "fix_hint": "Always state the boundary. Especially important for agents.",
        },
        {
            "id": 21, "name": "no_stack_constraints",
            "description": "No version/library constraints",
            "before": "build a React component",
            "after": "React 18, TypeScript strict, no external libraries, Tailwind only",
            "fix_hint": "Name the version, the typing mode, the styling system. The "
                        "AI will guess otherwise.",
        },
        {
            "id": 22, "name": "no_stop_condition_for_agents",
            "description": "No stop condition for an autonomous agent",
            "before": "build the whole feature",
            "after": "Explicit stop conditions + ✅ checkpoint output after each step",
            "fix_hint": "Use ReAct+Stop (Template H) for any autonomous task.",
        },
        {
            "id": 23, "name": "no_file_path_for_ide_ai",
            "description": "No exact file path for IDE AI",
            "before": "update the login function",
            "after": "Update handleLogin() in src/pages/Login.tsx only",
            "fix_hint": "Use File-Scope (Template G). Name the file + function + "
                        "scope.",
        },
        {
            "id": 24, "name": "wrong_template_for_tool",
            "description": "Prompt structure mismatched to the target tool",
            "before": "GPT-style prose prompt used in Cursor",
            "after": "Adapt to File-Scope Template (Template G) with path + scope",
            "fix_hint": "Each tool has a preferred structure. Cursor wants File-Scope, "
                        "Midjourney wants Visual Descriptor.",
        },
        {
            "id": 25, "name": "pasting_entire_codebase",
            "description": "Full repo context every prompt instead of scoped",
            "before": "Full repo context every prompt",
            "after": "Scope to only the relevant function and file",
            "fix_hint": "Token cost scales with context. Scope to the function or "
                        "class you care about.",
        },
    ],
    "reasoning": [
        {
            "id": 26, "name": "no_cot_for_logic_task",
            "description": "No chain-of-thought for a logic-heavy task",
            "before": "which approach is better?",
            "after": "Think through both approaches step by step before recommending",
            "fix_hint": "For logic, math, debugging, multi-factor analysis — force "
                        "step-by-step reasoning. For non-reasoning models only.",
        },
        {
            "id": 27, "name": "cot_for_reasoning_models",
            "description": "CoT instructions sent to reasoning-native models",
            "before": "'think step by step' sent to o1 / o3 / DeepSeek-R1 / "
                       "MiniMax thinking",
            "after": "Remove it — reasoning models think internally and CoT "
                     "instructions degrade output",
            "fix_hint": "NEVER add CoT to o1, o3, o4-mini, Claude extended "
                        "thinking, DeepSeek-R1, Qwen3 thinking mode, MiniMax "
                        "thinking mode.",
        },
        {
            "id": 28, "name": "no_self_check",
            "description": "No self-verification step on complex output",
            "before": "(nothing)",
            "after": "Before finishing, verify output against the constraints above",
            "fix_hint": "For complex outputs, add a final 'verify against constraints' "
                        "step.",
        },
        {
            "id": 29, "name": "expecting_inter_session_memory",
            "description": "Assumes the AI remembers prior sessions",
            "before": "you already know my project",
            "after": "Always re-provide the Memory Block in every new session",
            "fix_hint": "Sessions don't share memory. New session = full re-state.",
        },
        {
            "id": 30, "name": "contradicting_prior_decisions",
            "description": "New prompt ignores earlier architecture",
            "before": "New prompt ignores earlier architecture",
            "after": "Memory Block with all established decisions",
            "fix_hint": "Restate every prior decision in the Memory Block to avoid "
                        "drift.",
        },
    ],
    "agentic": [
        {
            "id": 31, "name": "no_starting_state",
            "description": "No specification of the current state",
            "before": "build me a REST API",
            "after": "Empty Node.js project, Express installed, src/app.js exists",
            "fix_hint": "For agents, always define the starting state — what files "
                        "exist, what's installed, what's the current behavior.",
        },
        {
            "id": 32, "name": "no_target_state",
            "description": "No specification of the desired end state",
            "before": "add authentication",
            "after": (
                "/src/middleware/auth.js with JWT verify. POST /login and "
                "POST /register in /src/routes/auth.js"
            ),
            "fix_hint": "Define the target state with file paths + behavior. The agent "
                        "needs to know 'done'.",
        },
        {
            "id": 33, "name": "silent_agent",
            "description": "No progress output from the agent",
            "before": "No progress output",
            "after": "After each step output: ✅ [what was completed]",
            "fix_hint": "Force a checkpoint protocol. Silent agents hide runaway loops.",
        },
        {
            "id": 34, "name": "unlocked_filesystem",
            "description": "No file restrictions for the agent",
            "before": "No file restrictions",
            "after": "Only edit files inside src/. Do not touch package.json, .env, "
                     "or any config file.",
            "fix_hint": "For any agent, name the directory and the forbidden zones.",
        },
        {
            "id": 35, "name": "no_human_review_trigger",
            "description": "Agent decides everything autonomously",
            "before": "Agent decides everything",
            "after": (
                "Stop and ask before: deleting any file, adding any dependency, or "
                "changing the database schema"
            ),
            "fix_hint": "Always define human-in-the-loop triggers for high-risk "
                        "actions.",
        },
        {
            "id": 36, "name": "vague_first_turn_on_opus_4_7",
            "description": (
                "Opus 4.7 reads prompts literally. 'fix the auth bug' with no scope, "
                "no files, no criteria produces narrow output."
            ),
            "before": "fix the auth bug",
            "after": "Use Template M (Opus 4.7 Task Brief). Front-load intent, file "
                     "scope, constraints, and acceptance criteria.",
            "fix_hint": "Opus 4.7 no longer fills implicit context like 4.6 did. "
                        "Always use Template M for Opus 4.7.",
        },
        {
            "id": 37, "name": "context_rot_long_sessions",
            "description": (
                "Keeps correcting in the same session for 60+ turns."
            ),
            "before": "Long session with many corrections",
            "after": (
                "New task = new session. Use /rewind instead of correcting. /compact "
                "at ~50% context. Subagents for file-heavy investigation."
            ),
            "fix_hint": "Long sessions rot. Spin a new session, /rewind, or "
                        "/compact.",
        },
    ],
}


# ============================================================================
# Tool detection (heuristic, not exhaustive)
# ============================================================================

TOOL_KEYWORDS: Dict[str, List[str]] = {
    "claude_code": ["claude code", "claude-code", "claudecode"],
    "cursor": ["cursor", "windsurf", "copilot", "cline", "antigravity",
               "bolt", "v0", "lovable"],
    "ide_ai": ["ide", "code editor", "in my editor"],
    "midjourney": ["midjourney", "mj ", "--ar", "--v 6", "--sref", "--cref"],
    "dall_e": ["dall-e", "dalle", "dall·e", "chatgpt image"],
    "stable_diffusion": ["stable diffusion", " sd ", "sdxl", "automatic1111",
                         "comfyui"],
    "comfyui": ["comfyui", "comfy ui"],
    "sora": ["sora", "runway", "kling", "ltx", "dream machine"],
    "elevenlabs": ["elevenlabs", "tts", "voice clone"],
    "perplexity": ["perplexity", "searchgpt"],
    "ollama": ["ollama", "llama", "mistral", "qwen", "local model", "modelfile"],
    "zapier": ["zapier", "make.com", "n8n", "workflow automation"],
    "blender": ["blender", "blendergpt"],
    "figma": ["figma", "figma make", "stitch"],
    "devin": ["devin", "swe-agent", "manus", "openclaw"],
}

REASONING_MODELS = (
    "o1", "o3", "o4-mini", "deepseek-r1", "deepseek r1", "qwen3", "qwen 3",
    "thinking", "minimax", "minimax-m3", "minimax thinking",
)


# ============================================================================
# Helpers
# ============================================================================

def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Retorna template por ID (case-insensitive: 'A'/'a'/'RTF'/'rtf')."""
    if not template_id:
        return None
    key = template_id.upper()
    if key in TEMPLATES:
        return TEMPLATES[key]
    # Try by name
    for tid, data in TEMPLATES.items():
        if data["name"].upper() == key:
            return data
    return None


def list_templates() -> List[str]:
    """Retorna los 13 IDs de template (A-M) ordenados."""
    return sorted(TEMPLATES.keys())


def list_patterns(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna patterns. Si category, filtra (task/context/format/scope/reasoning/agentic)."""
    if category is None:
        out: List[Dict[str, Any]] = []
        for cat in CATEGORIES:
            out.extend(PATTERNS[cat])
        return out
    if category not in CATEGORIES:
        return []
    return list(PATTERNS[category])


def get_pattern_by_id(pattern_id: int) -> Optional[Dict[str, Any]]:
    """Retorna pattern por ID (1-37) o None si no existe."""
    for cat in CATEGORIES:
        for p in PATTERNS[cat]:
            if p["id"] == pattern_id:
                return {**p, "category": cat}
    return None


def detect_pattern(text: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Detecta heurísticamente patterns que aplican al texto.

    Matching por keyword presence en el texto (case-insensitive, substring).
    Retorna lista de patterns que matchearon al menos 1 keyword.

    Args:
        text: Texto del prompt a analizar.
        category: Si se pasa, filtra por categoría (task/context/format/...).

    Returns:
        Lista de patterns detectados, con campo extra 'matched_keywords'.
    """
    if not text or not text.strip():
        return []
    text_lower = text.lower()
    cats = (category,) if category and category in CATEGORIES else CATEGORIES
    out: List[Dict[str, Any]] = []
    for cat in cats:
        for p in PATTERNS[cat]:
            matched = _pattern_keywords(p)
            hits = [kw for kw in matched if kw in text_lower]
            if hits:
                enriched = {**p, "category": cat, "matched_keywords": hits}
                out.append(enriched)
    return out


def _pattern_keywords(p: Dict[str, Any]) -> List[str]:
    """Extrae keywords para matching de un pattern (from before/after/description).

    Heurística best-effort: incluye words ≥ 3 chars del before/description,
    más el 'name' (slug) del pattern. False positives son aceptables
    (mejor over-detect que miss).
    """
    kws: set = set()
    desc = (p.get("description") or "").lower()
    for word in desc.split():
        clean = re.sub(r"[^a-z0-9_-]", "", word)
        if len(clean) >= 3:
            kws.add(clean)
    before = (p.get("before") or "").lower()
    for word in before.split():
        clean = re.sub(r"[^a-z0-9_-]", "", word)
        if len(clean) >= 3:
            kws.add(clean)
    # Add the pattern name slug (helps for "vague_task_verb" → "vague")
    name = p.get("name", "").lower().replace("_", " ")
    for word in name.split():
        clean = re.sub(r"[^a-z0-9_-]", "", word)
        if len(clean) >= 3:
            kws.add(clean)
    return list(kws)


def detect_target_tool(text: str) -> str:
    """Heurística: detecta el tool target a partir de keywords en el texto.

    Returns:
        ID del tool detectado, o 'auto' si no se puede determinar.
    """
    if not text:
        return "auto"
    text_lower = text.lower()
    # Match por longitud descendente para evitar que 'sora' matchee antes que
    # 'claude code', etc.
    sorted_tools = sorted(TOOL_KEYWORDS.items(), key=lambda kv: -max(len(k) for k in kv[1]))
    for tool_id, keywords in sorted_tools:
        for kw in keywords:
            if kw in text_lower:
                return tool_id
    return "auto"


def is_reasoning_model(model_name: str) -> bool:
    """True si el modelo es nativo de razonamiento (no debe recibir CoT)."""
    if not model_name:
        return False
    name = model_name.lower()
    return any(rm in name for rm in REASONING_MODELS)


def format_with_template(template_id: str, **values: Any) -> str:
    """Formatea un template con los valores provistos.

    Los templates usan placeholders `[description text]` por legibilidad.
    El matching es posicional: el N-ésimo `[...]` se asocia al N-ésimo
    field del template. Si el field name está en `values`, se sustituye
    por su valor. Si no, se reemplaza por `[field_name]` para visibilidad.

    Args:
        template_id: ID del template (A-M) o nombre (RTF, CO-STAR, ...).
        **values: Valores para los campos del template.

    Returns:
        String del template con valores sustituidos.
    """
    t = get_template(template_id)
    if t is None:
        return f"[unknown template: {template_id}]"
    tpl = t["template"]
    fields = list(t.get("fields", []))
    placeholders = re.findall(r"\[([^\]]+)\]", tpl)

    # Reemplazar placeholders posicionalmente (reverse para preservar índices)
    n = min(len(placeholders), len(fields))
    for i in range(n - 1, -1, -1):
        field_name = fields[i]
        placeholder_text = placeholders[i]
        original = f"[{placeholder_text}]"
        if field_name in values:
            tpl = tpl.replace(original, str(values[field_name]), 1)
        else:
            # Replace with [field_name] for visibility
            tpl = tpl.replace(original, f"[{field_name}]", 1)

    return tpl


def pick_template_for(target_tool: str, task: str) -> str:
    """Heurística simple para recomendar un template según el target.

    Returns:
        ID del template (A-M).
    """
    t = (target_tool or "").lower()
    task_l = (task or "").lower()
    if t in ("claude_code", "devin", "openclaw"):
        return "H"
    if t in ("cursor", "windsurf", "copilot", "cline", "antigravity",
             "bolt", "v0", "lovable"):
        return "G"
    if t == "midjourney":
        return "I"
    if t == "dall_e":
        return "I"
    if t in ("stable_diffusion", "comfyui"):
        return "K"
    if t in ("sora", "runway", "kling", "ltx", "dream_machine"):
        return "I"
    if t in ("perplexity", "searchgpt"):
        return "B"
    if t in ("ollama", "llama", "mistral", "qwen"):
        return "B"
    if t in ("elevenlabs",):
        return "B"
    if t in ("zapier", "n8n", "make.com"):
        return "C"
    if t == "blender":
        return "C"
    if t == "figma":
        return "G"
    # Default: si task menciona 'opus 4.7' o 'claude opus', usar M
    if "opus 4.7" in task_l or "opus 4" in task_l:
        return "M"
    # Si task es corta, RTF
    if len(task_l.split()) <= 5:
        return "A"
    # Si task es larga/compleja, RISEN
    if len(task_l.split()) > 30:
        return "C"
    # Default medio: CO-STAR
    return "B"


def get_knowledge_summary() -> str:
    """Resumen textual de la knowledge base para inyectar en system prompts."""
    parts: List[str] = [
        f"PROMPTER KNOWLEDGE BASE v{KB_VERSION} (source: {KB_SOURCE}, "
        f"license: {KB_LICENSE})",
        f"- {len(TEMPLATES)} templates: A-M ({', '.join(t['name'] for t in TEMPLATES.values())})",
        f"- {sum(len(v) for v in PATTERNS.values())} credit-killing patterns in 6 categories: "
        f"{', '.join(CATEGORIES)}",
        "",
        "TEMPLATES:",
    ]
    for tid in sorted(TEMPLATES.keys()):
        t = TEMPLATES[tid]
        parts.append(f"  {tid} — {t['name']} ({t['full_name']}): {t['best_for']}")
    parts.append("")
    parts.append("PATTERN CATEGORIES:")
    for cat in CATEGORIES:
        n = len(PATTERNS[cat])
        names = ", ".join(p["name"] for p in PATTERNS[cat])
        parts.append(f"  {cat} ({n}): {names}")
    return "\n".join(parts)


def get_kb_metadata() -> Dict[str, Any]:
    """Metadata de la knowledge base (versión, conteos, source)."""
    return {
        "version": KB_VERSION,
        "source": KB_SOURCE,
        "license": KB_LICENSE,
        "local_mirror": KB_LOCAL_MIRROR,
        "template_count": len(TEMPLATES),
        "template_ids": list_templates(),
        "pattern_count": sum(len(v) for v in PATTERNS.values()),
        "categories": list(CATEGORIES),
        "patterns_by_category": {c: len(PATTERNS[c]) for c in CATEGORIES},
    }
