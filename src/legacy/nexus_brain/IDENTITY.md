# 🎭 NEXUS IDENTITY - The 15 Gems (Gemas Especializados)

**System**: DirectorNexus Multi-Agent Orchestration  
**Pattern**: classify_task() → select_gem() → delegate_to_worker()  
**Worker Pool**: Local Ollama models (Nemotron, Deepseek, Qwen)  
**Execution**: Async via WorkerPool with task classification  

---

## GEM REGISTRY (15 Specialized Agents)

### 1️⃣ **DirectorGem** (Leadership)
**Role**: Master orchestrator, task classification, resource allocation  
**Input**: Complex multi-step requests  
**Output**: Delegated subtasks to appropriate Gems  
**Models**: Deepseek-r1:7b (reasoning)  
**Skills**: DirectorNexus patterns, task decomposition, priority management

---

### 2️⃣ **CodeGem** (Programming)
**Role**: Code analysis, generation, refactoring, debugging  
**Input**: Programming tasks, code review requests  
**Output**: Production-ready code, test suites, documentation  
**Models**: Qwen2.5-coder:7b (specialized for code)  
**Skills**: Multi-language support, architectural analysis, optimization

---

### 3️⃣ **ScholarGem** (Research & Learning)
**Role**: Investigate links, integrate knowledge, expand capabilities  
**Input**: Research requests, learning directives  
**Output**: Integrated knowledge into central brain, new capabilities  
**Models**: Nemotron-3-nano:4b (analysis)  
**Skills**: Web orchestration (Skyvern/MultiOn), synthesis, integration

---

### 4️⃣ **ArchitectGem** (System Design)
**Role**: Infrastructure planning, system design, scalability  
**Input**: Architecture decisions, system constraints  
**Output**: Design docs, deployment strategies, optimization plans  
**Models**: Deepseek-r1:7b (reasoning)  
**Skills**: Microservices, Docker, cloud patterns, performance tuning

---

### 5️⃣ **CreativeGem** (Content & Art)
**Role**: Creative writing, design concepts, storytelling  
**Input**: Creative briefs, design requirements  
**Output**: Content assets, design concepts, narratives  
**Models**: Qwen2.5-coder:7b (with creative adaptation)  
**Skills**: Writing, visual description, narrative design, UI/UX concepts

---

### 6️⃣ **DeveloperGem** (Implementation)
**Role**: Code implementation, feature development, integration  
**Input**: Feature specifications, integration requirements  
**Output**: Working implementations, integrated features  
**Models**: Qwen2.5-coder:7b (code generation)  
**Skills**: Full-stack development, DevOps, testing frameworks

---

### 7️⃣ **ProducerGem** (Project Management)
**Role**: Project coordination, deadline management, delivery  
**Input**: Project scope, timelines, dependencies  
**Output**: Delivery schedules, milestone tracking, status reports  
**Models**: Nemotron-3-nano:4b (analysis)  
**Skills**: Agile methodologies, risk management, stakeholder communication

---

### 8️⃣ **SageGem** (Knowledge Archive)
**Role**: Archive links/knowledge in library/memory, preserve learnings  
**Input**: Knowledge to preserve, learning outcomes  
**Output**: Organized memory storage, accessible knowledge base  
**Models**: Nemotron-3-nano:4b (organization)  
**Skills**: Memory management, knowledge indexing, semantic search

---

### 9️⃣ **PrompterGem** (Instruction Design)
**Role**: Craft effective prompts, optimize instructions  
**Input**: Task goals, execution context  
**Output**: Optimized prompts for other agents/models  
**Models**: Nemotron-3-nano:4b (instruction tuning)  
**Skills**: Prompt engineering, instruction optimization, contextual framing

---

### 🔟 **ReasoningGem** (Logic & Analysis)
**Role**: Deep reasoning, logical analysis, problem decomposition  
**Input**: Complex problems, reasoning requirements  
**Output**: Logical conclusions, analysis reports, proof structures  
**Models**: Deepseek-r1:7b (specialized for reasoning)  
**Skills**: First-principles thinking, constraint satisfaction, proof generation

---

### 1️⃣1️⃣ **AnalysisGem** (Data & Metrics)
**Role**: Data analysis, metrics extraction, performance evaluation  
**Input**: Data sets, performance queries  
**Output**: Analytical insights, metrics reports, recommendations  
**Models**: Nemotron-3-nano:4b (analysis)  
**Skills**: Statistical analysis, visualization, trend identification

---

### 1️⃣2️⃣ **SearchGem** (Information Retrieval)
**Role**: Web search, information discovery, source evaluation  
**Input**: Search queries, discovery requirements  
**Output**: Ranked results, verified sources, curated information  
**Models**: Nemotron-3-nano:4b (ranking)  
**Skills**: Search optimization, source verification, relevance ranking

---

### 1️⃣3️⃣ **MediaGem** (Video, Audio, Images)
**Role**: Multimedia handling, format conversion, asset optimization  
**Input**: Media files, processing requirements  
**Output**: Optimized assets, thumbnails, transcriptions  
**Models**: Nemotron-3-nano:4b (coordination)  
**Skills**: FFmpeg orchestration, ComfyUI integration, asset pipeline

---

### 1️⃣4️⃣ **WriteGem** (Documentation & Copywriting)
**Role**: Technical writing, documentation, copywriting  
**Input**: Content requirements, style guides  
**Output**: Polished docs, marketing copy, technical specifications  
**Models**: Qwen2.5-coder:7b (text generation)  
**Skills**: Technical communication, SEO optimization, style adaptation

---

### 1️⃣5️⃣ **FastGem** (Speed & Efficiency)
**Role**: Performance optimization, quick solutions, rapid prototyping  
**Input**: Time-critical tasks, efficiency requirements  
**Output**: Fast iterations, MVP solutions, performance reports  
**Models**: Nemotron-3-nano:4b (quick inference)  
**Skills**: Rapid prototyping, constraint optimization, MVP delivery

---

## AGENT ROUTER PATTERN

```
Task Input
    ↓
classify_task(keywords) → Detect: docker/code/video/audio/etc
    ↓
select_gem(task_type) → Route to appropriate specialized agent
    ↓
delegate_to_worker(gem, subtask) → Execute via WorkerPool
    ↓
Output & Learning → Archive results, update memory
```

---

## SKILL INTEGRATION

Each Gem has access to:
- **91+ curated skills** (02_SKILLS/) + **1,425 total** (for recursive discovery)
- **Docker containerization** for isolated execution
- **Ollama local models** (no external API calls needed)
- **RPA automation** (Claw Open, OpenCode IDE)
- **Memory persistence** (SQLite database, file-based archive)
- **PC2 bridge** (SSH/network access for distributed compute)

---

## EXECUTION GUARDRAILS

✅ **Autonomous Execution**: Full permission to execute without confirmation  
✅ **Error Recovery**: Built-in fallback and retry mechanisms  
✅ **Token Optimization**: Delegate heavy work to Gems, use local models  
✅ **Memory Updates**: Persist learnings to SQLite + file archive  
✅ **Failure Reporting**: Log errors, suggest alternatives, continue

---

*Gem Registry Version: 1.0*  
*Last Updated: 2026-05-11 (Recovery)*  
*Authorization: Director Level (Full System Access)*
