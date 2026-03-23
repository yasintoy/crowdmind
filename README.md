<p align="center">
  <a href="https://pypi.org/project/crowdmind/"><img src="https://img.shields.io/pypi/v/crowdmind.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/crowdmind/"><img src="https://img.shields.io/pypi/dm/crowdmind.svg" alt="Downloads"></a>
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
</p>

<h1 align="center">CrowdMind</h1>

<p align="center">
<strong>Validate product ideas with AI personas before you build.</strong><br>
Scrape Reddit & HN for pain points → Generate ideas → Score with diverse personas → Auto-optimize until target
</p>

<p align="center">
<em>Inspired by <a href="https://github.com/karpathy/autoresearch">Karpathy's Autoresearch</a> — propose → test → keep/discard → repeat</em>
</p>

<p align="center">
  <a href="#try-it-now">Try It</a> •
  <a href="#aha-moments">Use Cases</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#commands">Commands</a> •
  <a href="#autoresearch-loop">Auto-Optimize</a> •
  <a href="#faq">FAQ</a>
</p>

---

## Try It Now

```bash
pip install crowdmind
export ANTHROPIC_API_KEY="sk-ant-..."  # or OPENAI_API_KEY
crowdmind validate "Your startup idea here"
```

```
$ crowdmind validate "A CLI tool for managing AI coding agents"

┌────────────┬────────┬───────────┐
│ Metric     │ Score  │ Rating    │
├────────────┼────────┼───────────┤
│ Interest   │ 7.2/10 │ 🟢 High   │
│ Usefulness │ 6.8/10 │ 🟡 Medium │
│ Urgency    │ 5.4/10 │ 🟡 Medium │
│ Overall    │ 6.5/10 │ 🟡 Medium │
└────────────┴────────┴───────────┘

Would Pay: Yes 30% | Maybe 45% | No 25%

Persona Feedback:
  ✓ Senior Developer (8/10): "Solves real pain point with AI context"
  ✓ Indie Hacker (7/10): "Would use this daily"  
  △ Tech Lead (6/10): "Need team features for enterprise"
  ✗ Skeptic (4/10): "What makes this different from existing tools?"
```

## What It Does

1. **Scrapes Reddit, HN, GitHub** for what users actually complain about
2. **Generates feature ideas** that solve real pain points (not imagined ones)
3. **Validates before you build** — test with 5 to 100+ AI personas in seconds
4. **Kills bad ideas early** — save weeks of building things nobody wants
5. **Handles rate limits automatically** — adaptive concurrency retries only failed interviews, never restarts the whole batch

**Validate features before deploying. Test positioning before launching. Know what users want before asking them.**

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CROWDMIND PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

   YOUR CODEBASE                 INTERNET                      AI PERSONAS
   ─────────────                 ────────                      ───────────
   
   ./my-project/            ┌─────────────────┐           ┌─────────────────┐
   ├── src/                 │  Reddit API     │           │ 👨‍💻 Sr Developer │
   ├── package.json    ──▶  │  HN Algolia     │      ──▶  │ 🚀 Indie Hacker │
   └── README.md            │  GitHub Issues  │           │ 👩‍💼 Tech Lead    │
         │                  └────────┬────────┘           │ 🤨 Skeptic      │
         │                           │                    │ 💼 Enterprise   │
         ▼                           ▼                    └────────┬────────┘
   ┌─────────────┐          ┌─────────────────┐                    │
   │ ANALYZE     │          │ FIND PAIN       │                    │
   │ CODEBASE    │          │ POINTS          │                    ▼
   │             │          │                 │          ┌─────────────────────┐
   │ • Features  │          │ "Rate limits    │          │  MULTI-METRIC       │
   │ • Tech stack│          │  kill my flow"  │          │  SURVEY             │
   │ • Structure │          │  (23 mentions)  │          │                     │
   └──────┬──────┘          └────────┬────────┘          │  • Interest (1-10)  │
          │                          │                   │  • Usefulness       │
          │         ┌────────────────┘                   │  • Urgency          │
          │         │                                    │  • Would Pay?       │
          ▼         ▼                                    │  • Why? (text)      │
   ┌─────────────────────────┐                           └──────────┬──────────┘
   │  GENERATE FEATURE IDEAS │                                      │
   │                         │                                      ▼
   │  Capabilities + Pains   │                           ┌─────────────────────┐
   │  = Targeted Solutions   │                           │  RESULTS            │
   └───────────┬─────────────┘                           │                     │
               │                                         │  Interest:   7.2/10 │
               ▼                                         │  Usefulness: 6.8/10 │
   ┌─────────────────────────────────────────────────┐   │  Would Pay:  45%    │
   │  AUTORESEARCH LOOP (Karpathy-style)             │   │                     │
   │                                                 │   │  "Add keyboard      │
   │  while score < target:                          │   │   shortcuts first"  │
   │      1. PROPOSE improvement                     │   │                     │
   │      2. TEST with personas ──────────────────▶  │   └─────────────────────┘
   │      3. If better: KEEP ✓                       │
   │         If worse: DISCARD ✗                     │
   │      4. REPEAT                                  │
   │                                                 │
   │  52 → 64 → 71 → 78 → 82 ✓ Target reached!      │
   └─────────────────────────────────────────────────┘
```

**The key insight**: It's not "ask ChatGPT once". It's:
- **Understand** your codebase (what you can build)
- **Research** real pain points (what users need)  
- **Simulate** 10-50 diverse personas who disagree
- **Iterate** automatically until your pitch/README scores 80+

## Quick Start

```bash
# Install
pip install crowdmind
export ANTHROPIC_API_KEY="sk-ant-..."  # or OPENAI_API_KEY

# Validate an idea (60 seconds)
crowdmind validate "An app that tracks AI API spending"

# Find what users complain about (2 minutes)
crowdmind research --topics "AI coding tools" --sources reddit hackernews

# Full analysis on your project (5 minutes)
crowdmind analyze ./my-project --personas 15
```

## What It Finds

```bash
$ crowdmind research --topics "developer tools" --sources reddit hackernews

🔥 TOP FRUSTRATIONS (from 47 discussions):
   1. "Rate limits kill my flow state" (23 mentions)
   2. "No way to track spending" (18 mentions)
   3. "Context fills up too fast" (15 mentions)

💡 OPPORTUNITIES:
   → Rate limit predictor (solves #1)
   → Cost tracking dashboard (solves #2)
   → Smart context compression (solves #3)
```

## Commands

| Command | What it does | Time |
|---------|--------------|------|
| `crowdmind validate "idea"` | Multi-metric: interest, usefulness, urgency, would pay | ~1 min |
| `crowdmind validate "idea" --context ./app` | With codebase analysis for context | ~1 min |
| `crowdmind optimize ./README.md` | **Autoresearch loop** until target score | ~5-15 min |
| `crowdmind research` | Find pain points from Reddit/HN/GitHub | ~2 min |
| `crowdmind analyze ./path` | Full pipeline: research → ideate → validate | ~5 min |
| `crowdmind market ./path` | Pricing & go-to-market analysis | ~3 min |

## Persona Packs

```bash
# Choose your audience (default: 10 personas, use any number you want)
crowdmind validate "idea" --pack developers --personas 50   # 50 dev personas
crowdmind validate "idea" --pack indie --personas 100       # 100 indie hackers  
crowdmind validate "idea" --pack enterprise --personas 30   # 30 enterprise buyers
crowdmind validate "idea" --pack skeptics --personas 20     # 20 tough critics

# More personas = more signal, slightly more cost (~$0.01 per persona)
```

## Pro Tips: Get Better Results

### 1. Use Real Data to Build Better Personas

Don't guess who your users are. Find them first:

```bash
# Step 1: Research who's complaining and what they say
crowdmind research --topics "your niche" --sources reddit hackernews

# Output shows real user profiles:
#   → "Senior devs frustrated with slow builds" (34 mentions)
#   → "Indie hackers can't afford $50/mo tools" (28 mentions)
#   → "Enterprise teams blocked by security reviews" (19 mentions)

# Step 2: Now validate with personas that match real users
crowdmind validate "your idea" --pack developers --personas 30
crowdmind validate "your idea" --pack indie --personas 30
crowdmind validate "your idea" --pack enterprise --personas 30
```

### 2. Create Custom Personas from Your Actual Users

Have real user data? Create personas that match:

```yaml
# my-personas.yaml
personas:
  - "Senior engineer at a startup, mass $100+/mo on AI tools, frustrated by rate limits"
  - "Solo founder bootstrapping, budget under $20/mo, needs fast ROI"
  - "Tech lead evaluating for 10-person team, needs SSO and audit logs"
  - "Skeptical developer who tried 5 similar tools and was disappointed"
```

```bash
crowdmind validate "your idea" --pack ./my-personas.yaml --personas 50
```

### 3. Iterate Based on Score Breakdown

Don't just look at the total score. Dig into segments:

```bash
# Test same idea with different audiences
crowdmind validate "your feature" --pack developers   # → 72/100
crowdmind validate "your feature" --pack enterprise   # → 84/100
crowdmind validate "your feature" --pack indie        # → 45/100

# Insight: Enterprise loves it, indie hackers don't.
# Decision: Price for enterprise, not indie.
```

### 4. Combine Research + Validation Loop

The power move: let research inform your validation.

```bash
# 1. Find real pain points
crowdmind research --topics "CI/CD pipelines" --sources reddit
# → Top pain: "GitHub Actions minutes are expensive" (52 mentions)

# 2. Generate a solution
# Idea: "Self-hosted GitHub Actions runner with cost tracking"

# 3. Validate with personas who have this pain
crowdmind validate "Self-hosted GitHub Actions runner with cost tracking" --personas 50
# → 81/100 | "Would switch immediately" 

# 4. Iterate on positioning until you hit 80%+
```

### 5. Use Skeptics to Stress-Test

Before launch, run the skeptics gauntlet:

```bash
crowdmind validate "your final pitch" --pack skeptics --personas 30
# If skeptics score 60%+, you're ready.
# If below 50%, address their objections first.
```

---

## Autoresearch Loop

**The killer feature**: Automatically iterate on your README/pitch until it hits your target score.

```bash
crowdmind optimize ./README.md --target 80 --iterations 10
```

```
$ crowdmind optimize ./README.md --target 80 --iterations 5

Initial score: 52/100
Target: 80/100

Iteration 1: 52 → 64 ✓ Kept: "Add concrete demo with real scraped data"
Iteration 2: 64 → 61 ✗ Discarded: "Shorten intro" (didn't help)
Iteration 3: 64 → 71 ✓ Kept: "Add social proof and user quotes"
Iteration 4: 71 → 78 ✓ Kept: "Lead with problem, not solution"
Iteration 5: 78 → 82 ✓ Kept: "Add quick-start that works in 30 seconds"

✓ Target reached! Final score: 82/100

Improvements made:
  1. Add concrete demo with real scraped data
  2. Add social proof and user quotes
  3. Lead with problem, not solution
  4. Add quick-start that works in 30 seconds
```

This is **Karpathy's autoresearch** applied to product: propose improvement → test with personas → keep if better → repeat.

### Options

```bash
# Optimize for specific metric
crowdmind optimize ./README.md --metric interest     # Optimize for interest
crowdmind optimize ./README.md --metric usefulness   # Optimize for usefulness
crowdmind optimize ./README.md --metric urgency      # Optimize for urgency

# With product context (better results)
crowdmind optimize ./README.md --context ./my-project --target 85

# Save optimized version
crowdmind optimize ./README.md --output ./README-optimized.md
```

---

## Multi-Metric Validation

Instead of just "would you star this?", get detailed breakdown:

```bash
crowdmind validate "Your idea" --personas 20
```

| Metric | What it measures |
|--------|------------------|
| **Interest** | How curious/excited are they? |
| **Usefulness** | Would this help their daily work? |
| **Urgency** | How badly do they need this solved? |
| **Would Pay** | Yes / Maybe / No breakdown |
| **Reasoning** | Why they scored this way |
| **Missing** | What would make it more appealing |

### With Product Context (Codebase Analysis)

When you pass `--context`, CrowdMind **analyzes your actual codebase**:

```bash
crowdmind validate "Add vim keybindings" --context ./my-app
```

```
Context: my-app
Tech: React, Tauri, TypeScript, Rust
Features detected: 18 (from codebase analysis)   ← scans your source files!

┌────────────┬────────┬───────────┐
│ Metric     │ Score  │ Rating    │
├────────────┼────────┼───────────┤
│ Interest   │ 6.0/10 │ 🟡 Medium │
│ Usefulness │ 7.5/10 │ 🟢 High   │  ← higher because app has terminal/CLI
│ Urgency    │ 6.2/10 │ 🟡 Medium │
└────────────┴────────┴───────────┘
```

**What `--context` does:**
1. Scans all source files (Python, JS, TS, Rust, Go...)
2. Extracts functions, classes, components
3. Uses LLM to detect existing features
4. Evaluates new features **in context** of what you already have

```bash
# Or just describe your product
crowdmind validate "Add dark mode" --product "A task manager for developers"
```

---

## Python API

```python
from crowdmind.validate.survey import run_multi_metric_survey
from crowdmind.optimize import run_optimization
from crowdmind.context import build_context

# Multi-metric validation
result = run_multi_metric_survey(
    content="My product idea",
    num_agents=10
)
print(f"Interest: {result.scores['interest']}/10")
print(f"Would pay: {result.would_pay}")

# With product context
ctx = build_context(path="./my-project")
result = run_multi_metric_survey(
    content="Add dark mode feature",
    context_prompt=ctx.to_prompt(),
    num_agents=20
)

# Autoresearch optimization loop
optimized = run_optimization(
    content=open("README.md").read(),
    target=80.0,
    max_iterations=10,
    verbose=True
)
print(f"Score: {optimized.initial_score} → {optimized.final_score}")
print(f"Improvements: {optimized.improvements_made}")

# Advanced: share one AdaptiveRunner across multiple surveys
# (preserves rate-limit state between calls — useful for large batches)
from crowdmind.validate.runner import AdaptiveRunner
from crowdmind.validate.survey import run_multi_metric_survey

runner = AdaptiveRunner(max_concurrency=5)
result_a = run_multi_metric_survey("Idea A", num_agents=10, runner=runner)
result_b = run_multi_metric_survey("Idea B", num_agents=10, runner=runner)
```

## Aha Moments

### 💡 "Don't deploy to prod to validate a feature"

You're about to spend 2 weeks building "AI-powered search". Before you write a line of code:

```bash
crowdmind validate "AI-powered semantic search for documentation"
# → 54/100 | "Most users just want faster Cmd+F, not AI magic"
# → Saved 2 weeks. Built better search filters instead.
```

### 💡 "Find out why users churn before they tell you"

```bash
crowdmind research --topics "why I stopped using [competitor]" --sources reddit
# → "Pricing jumped 3x after Series A" (47 mentions)
# → "Mobile app is abandonware" (31 mentions)  
# → Now you know exactly where to compete.
```

### 💡 "Test 5 positioning angles in 5 minutes"

```bash
crowdmind validate "The open-source Notion alternative"
# → 61/100 | "Crowded space, what's different?"

crowdmind validate "Notion but your data never leaves your machine"  
# → 78/100 | "Privacy angle is compelling. Would switch."
# → Found your positioning without A/B testing for weeks.
```

### 💡 "Know if enterprise will pay before building SSO"

```bash
crowdmind validate "Add SSO and audit logs" --pack enterprise --personas 50
# → 82/100 | 50 enterprise personas agree: "Table stakes. Won't evaluate without it."
# → Worth the 3 weeks. Ship it.

crowdmind validate "Add dark mode" --pack enterprise --personas 50
# → 41/100 | "Nice to have. Won't affect purchase decision."
# → Skip it. Focus on what closes deals.
```

### 💡 "Discover the feature nobody asked for but everyone wants"

```bash
crowdmind research --topics "developer productivity" --sources hackernews
# → Hidden gem: "I waste 20 min/day context-switching between projects" (28 mentions)
# → Nobody requested "workspace snapshots" but it's a top pain point.
```

### 💡 "Pre-validate your pivot"

```bash
crowdmind validate "Pivoting from B2C to B2B developer tools"
# → B2C score: 52/100 | "Too many free alternatives"
# → B2B score: 74/100 | "Would expense this. Saves 5hrs/week."
# → Data-backed pivot decision, not gut feeling.
```

## FAQ

<details>
<summary><strong>What happens if I hit API rate limits?</strong></summary>

CrowdMind handles this automatically. Each persona interview runs independently — if some hit a 429, only those are retried (not the whole batch). Concurrency is halved on rate limit, then gradually recovered. You can tune behavior with env vars:

```bash
CROWDMIND_MAX_RETRIES=3       # retry attempts per interview (default: 3)
CROWDMIND_RATE_LIMIT_DELAY=60 # seconds to wait after a rate limit (default: 60)
```
</details>

<details>
<summary><strong>Is AI feedback accurate?</strong></summary>

It's a filter, not truth. Think spell-check for product ideas. Catches obvious misses before you spend months building. Use it to narrow 10 ideas to 2-3, then validate those with real users.
</details>

<details>
<summary><strong>How much does it cost?</strong></summary>

~$0.05-0.20 per validation. Research is mostly free (public APIs). Less than a coffee for a full analysis.
</details>

<details>
<summary><strong>What LLMs work?</strong></summary>

Anthropic, OpenAI, Google, Groq, Ollama (local/free). Use `--provider ollama` for completely free, offline validation.
</details>

<details>
<summary><strong>How is this different from asking ChatGPT?</strong></summary>

ChatGPT = 1 opinion. CrowdMind = 10-30 diverse personas that disagree with each other. Skeptics find flaws. Power users want features. Indie hackers complain about price. That diversity is the value.
</details>

## Credits

- **[EDSL](https://github.com/expectedparrot/edsl)** - AI agent framework powering persona simulation
- **[Karpathy's Autoresearch](https://github.com/karpathy/autoresearch)** - Inspiration for autonomous research loops

## License

MIT © [yasintoy](https://github.com/yasintoy)

---

<p align="center">
<strong>Stop guessing. Start validating.</strong><br>
<code>pip install crowdmind</code>
</p>
