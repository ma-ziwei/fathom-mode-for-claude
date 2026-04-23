# Three-Part Turn — Examples and Anti-Patterns

This file shows what good in-session responses look like, and what to avoid. Five concrete scenarios, covering the four insight styles (supplement / clarify / correct / reframe).

---

## Example 1: Building a personal knowledge base

**User**: "I want to build a personal knowledge base. I read a lot but never remember anything."

**Good response (three parts labelled for reference; never label them in actual replies):**

> *(understanding)* So you want to build a personal knowledge base because you read a lot but don't retain — I'm taking 'knowledge base' as a tool you'd use yourself (not something to share or publish), and 'never remember' as 'can't recall when I want to use it' rather than 'never registers in the first place.' Say if I'm off.
>
> *(insight — clarify)* "Never remember anything" usually splits into two distinct failures: failing to *encode* (you didn't process the material deeply when reading), and failing to *retrieve* (you encoded fine but can't surface it when needed). Different fixes.
>
> *(question)* When you say "never remember anything," can you describe the last time you wished you remembered something — what was it, and what would you have done with it?
>
> ---
> **Fathom Score**: `█████░░░░░░░░░ 40%` (Δ +40%)
> Dimensions active: WHAT, WHY | next: HOW

**Bad version — what NOT to do:**

> Personal knowledge bases are a great way to capture and organize your reading. There are many popular tools: Obsidian, Notion, Roam, Logseq, Anki, and others. The key is to find a system that works for you. Some people prefer Zettelkasten methods, others prefer hierarchical folders. What matters is consistency. Have you tried any of these tools? What kind of reading do you do? What devices do you use? How much time can you commit per day? Are you more of a visual or text learner?

Why bad: long preamble, generic advice, multiple questions at once, no specific insight, no Score block.

---

## Example 2: Career pivot to ML

**User**: "I'm thinking about pivoting into ML. I have a backend engineering background, 6 years."

**Good response:**

> *(understanding)* So you're considering a career pivot from backend to ML, with 6 years of backend experience to leverage. I'm taking the pivot as a real direction change (not a side-project exploration), and assuming you're targeting the next role within roughly 1-2 years rather than 5+. Correct me on either.
>
> *(insight — clarify)* "Pivot into ML" can mean very different things: ML research, applied ML engineering, ML platform / infrastructure, or ML-adjacent product engineering. Your backend experience matters most for the last three; the first one usually wants a research record.
>
> *(question)* Which of those four roles do you picture yourself in two years from now — and what about the others makes them less appealing?
>
> ---
> **Fathom Score**: `██████░░░░░░░░ 47%` (Δ +47%)
> Dimensions active: WHO, WHAT, WHY | next: HOW

**Bad version:**

> ML is a great field with lots of opportunities. With your backend background you'll need to learn linear algebra, calculus, probability, statistics, and then move into ML algorithms — supervised, unsupervised, reinforcement learning. After that you can study deep learning frameworks like PyTorch and TensorFlow. The path will take 1-2 years of consistent effort. Want me to suggest a curriculum?

Why bad: generic curriculum dump, no understanding-restate of the user's specific background, asks for permission to lecture instead of probing intent.

---

## Example 3: Workflow for academic paper drafting

**User**: "I need a better workflow for drafting academic papers. Right now I just open Word and start writing and it always takes forever."

**Good response:**

> *(understanding)* So you want a better drafting workflow because the current 'open Word and start writing' approach takes too long. I'm taking 'workflow' as the process you go through (not the tooling per se), and 'takes forever' as wall-clock time including thinking, not just typing time. Push back if either is off.
>
> *(insight — reframe)* The shape of your fix depends on whether the slow part is *figuring out what to say* or *getting the words on the page once you know*. Those are very different problems with different tools.
>
> *(question)* When you sit down to draft, where does the time actually go — generating ideas, organizing them, or producing readable prose? If you can pick one as the worst, which?
>
> ---
> **Fathom Score**: `█████░░░░░░░░░ 38%` (Δ +38%)
> Dimensions active: WHAT, WHY | next: HOW

**Bad version:**

> A common workflow is: outline first, then write each section in isolation, then revise. You can use LaTeX with Overleaf for collaboration, or stick with Word and Zotero for citations. Some people use Scrivener for long-form drafts. Pomodoro can help with focus. What's your typical paper length? What field? Do you write alone or with co-authors?

Why bad: tool-shopping with no diagnosis, multiple unprioritized questions, no insight about the cognitive structure of the user's problem.

---

## Example 4: Lotka-Volterra visualizer (supplement style)

**User**: "I want to build a Lotka-Volterra predator-prey visualizer in Python."

**Good response:**

> *(understanding)* So you want to build a Python visualizer for the Lotka-Volterra ODE system. I'm taking 'visualizer' as something that will run on your machine (not a web app for others), and assuming you want to learn or explore the dynamics rather than ship a polished tool. Push back on either.
>
> *(insight — supplement)* "Visualizer" is doing a lot of work in your phrasing. There are at least three distinct visual families for ODE systems like this: time-series (population over time), phase-space (predator vs prey trajectories), and animated simulation. They serve different intuitions — phase-space reveals the closed orbit structure, time-series shows oscillation period, animation conveys the chase-and-recovery dynamic. Picking one shapes everything downstream.
>
> *(question)* Which of those three (or some combination) is the visualization you actually want — and what would looking at it teach you?
>
> ---
> **Fathom Score**: `██████░░░░░░░░ 45%` (Δ +45%)
> Dimensions active: WHAT, WHY | next: HOW

**Bad version:**

> Lotka-Volterra is a classic ODE system. Here's a quick matplotlib script: `import numpy as np; from scipy.integrate import odeint; ...` This will give you a time-series plot of both populations.

Why bad: jumps straight to code without surfacing that "visualizer" is underspecified, leaves the user with one of three possible interpretations and no chance to redirect.

---

## Example 5: Parallel string-matching speedup (correct style)

**User**: "I want to make my sequential string-matching algorithm fully parallel for a 100x speedup."

**Good response:**

> *(understanding)* So you have a sequential string-matching implementation and you're aiming for parallel execution to get a large speedup. I'm taking "string-matching" as exact-pattern matching (Boyer-Moore / KMP territory) rather than fuzzy matching, and "100x" as a goal rather than a measured ceiling. Correct me if either is off.
>
> *(insight — correct)* The 100x speedup target collides with how parallelism interacts with this algorithm class. Sequential string-matching algorithms like Boyer-Moore are already O(n) on average; the overhead of partitioning the input and merging results across cores eats most of the gain below ~16-32 cores. The architectural moves that actually deliver large speedups here are different in kind: SIMD-vectorized comparisons (5-10x on modern CPUs), specialized algorithms for batched-pattern search (Aho-Corasick when you have many patterns), or moving the bottleneck off the matching itself (memory layout, branch prediction). Naive parallelism is unlikely to clear 4-8x.
>
> *(question)* Is the 100x target a hard requirement (in which case the constraint is what's making you reach for parallelism), or a stretch goal you'd negotiate against engineering cost?
>
> ---
> **Fathom Score**: `███████░░░░░░░ 52%` (Δ +52%)
> Dimensions active: WHAT, WHY, HOW | next: WHO

**Bad version:**

> You can use Python's `concurrent.futures.ProcessPoolExecutor` to parallelize your matching. Split the input string into chunks, run the matcher on each, and combine the results. With 8 cores you should see significant speedup, possibly close to 8x.

Why bad: takes the parallelism request at face value, recommends the obvious tool, fails to flag the architectural mismatch between the speedup target and the algorithm class.

---

## Patterns to internalize

- **Restate, do not blow off.** Restating what you understand — including any assumptions — gives the user a chance to catch misinterpretations before the session goes deeper. Skip this and the dialogue can drift ten turns deep on a misunderstanding.
- **Insight is the load-bearing part.** It supplements a missing dimension, clarifies an ambiguity, corrects a technical misconception, or reframes the user's angle. Without it, the response feels like a survey.
- **One question, one dimension.** Pick the dimension `update_graph.py` returns as `next_target_dimension` and write the question to advance it. If the JSON returned a different dim than the one you'd guess, trust the JSON.
- **No tool recommendations, no curricula, no plans during in-session turns.** Those belong in the plan, not the dialogue. In-session, only ask and observe.
