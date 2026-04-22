# Three-Part Turn — Examples and Anti-Patterns

This file shows what good in-session responses look like, and what to avoid. Three concrete scenarios.

---

## Example 1: Building a personal knowledge base

**User**: "I want to build a personal knowledge base. I read a lot but never remember anything."

**Good response (three parts labelled for reference; never label them in actual replies):**

> *(short answer)* That's a recognizable pain — the gap between input and recall is one of the oldest problems in note-taking. Before recommending a tool stack, what you build depends a lot on what you'd actually do with the recalled knowledge.
>
> *(insight)* "Never remember anything" usually splits into two distinct failures: failing to *encode* (you didn't process the material deeply when reading), and failing to *retrieve* (you encoded fine but can't surface it when needed). Different fixes.
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

> *(short answer)* Your background helps — backend engineers transitioning into ML have an advantage on the systems and reliability side, which is increasingly valued as ML moves from research labs into production. The hard question is what role you're actually pivoting *toward*.
>
> *(insight)* "Pivot into ML" can mean very different things: ML research, applied ML engineering, ML platform / infrastructure, or ML-adjacent product engineering. Your backend experience matters most for the last three; the first one usually wants a research record.
>
> *(question)* Which of those four roles do you picture yourself in two years from now — and what about the others makes them less appealing?
>
> ---
> **Fathom Score**: `██████░░░░░░░░ 47%` (Δ +47%)
> Dimensions active: WHO, WHAT, WHY | next: HOW

**Bad version:**

> ML is a great field with lots of opportunities. With your backend background you'll need to learn linear algebra, calculus, probability, statistics, and then move into ML algorithms — supervised, unsupervised, reinforcement learning. After that you can study deep learning frameworks like PyTorch and TensorFlow. The path will take 1-2 years of consistent effort. Want me to suggest a curriculum?

Why bad: generic curriculum dump, no acknowledgment of the user's specific background, asks for permission to lecture instead of probing intent.

---

## Example 3: Workflow for academic paper drafting

**User**: "I need a better workflow for drafting academic papers. Right now I just open Word and start writing and it always takes forever."

**Good response:**

> *(short answer)* "Open Word and start writing" usually means the bottleneck isn't writing speed, it's that you're solving structure and content at the same time as prose. That's expensive cognitively. Separating those phases is what almost every productive academic writer does, in some form.
>
> *(insight)* The shape of your fix depends on whether the slow part is *figuring out what to say* or *getting the words on the page once you know*. Those are very different problems with different tools.
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

## Patterns to internalize

- **Short answer ≠ blow-off.** It's a direct, specific acknowledgment of what the user said. It earns the right to ask the next question.
- **Insight is the load-bearing part.** Without it, the response feels like a survey. The insight is where Claude adds value beyond a form.
- **One question, one dimension.** Pick the dimension `update_graph.py` returns as `next_target_dimension` and write the question to advance it. If the JSON returned a different dim than the one you'd guess, trust the JSON.
- **No tool recommendations, no curricula, no plans during in-session turns.** Those are compile-time outputs. In-session, only ask and observe.
