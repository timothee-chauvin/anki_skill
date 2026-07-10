---
name: anki
description: Create Anki flashcards from a conversation. Use when the user asks to make Anki cards, memorize something, create flashcards, or says "/anki".
---

# Anki Card Creation
## Workflow

1. **Search existing cards**: Before proposing, run `cd ~/prog/AI/anki && uv run python anki_add.py search "<query 1>" "<query 2>" ...` to look up the topic *and* related concepts and likely paraphrases. The command accepts many queries at once — pass ALL your keyword combinations in a single invocation (one invocation is fast; several waste startup time). Use different keyword combinations to catch existing cards that use different wording. Pass plain keywords only — no Anki search operators (`tag:`, `deck:`, `is:`). Topic markers like `(AI)` in fronts are not real Anki tags, just text. The script enforces `deck:Kn -is:suspended`.
   - Multi-word queries are **AND** (every word must appear somewhere on the card). So `sandbox evasion` requires *both* words and will miss a card that only uses one. Always also search each meaningful word separately.
   - If a narrow search returns no close matches, broaden to progressively larger categories until you get some content — e.g. `JumpReLU` → 0 hits → try `ReLU` → try `activation function` → try `neural network`. The goal is to land in *some* part of the collection so you can see how the user has covered the surrounding area, even when the specific concept is new. When you anticipate needing broader fallbacks, include them in the same invocation (`search "JumpReLU" "ReLU" "activation function"`); a follow-up invocation is only needed if the results demand new queries.

   Use the results to:
   - skip duplicates
   - inform your own understanding of which concepts the user already has cards on, so your new cards can build on that context naturally. This shapes how you phrase a new card — you don't need to re-define a concept the user clearly already knows. It does NOT mean inserting explicit references to other cards in the new card's text. Anki cards do not link to each other; each card stands alone.
   - match the style and tag conventions of existing cards on the same topic

2. **Propose cards**: Based on the conversation or topic, suggest a numbered list of cards. Prefix each card with `**N.**` on its own line (e.g. `**1.**`, `**2.**`) so the user can refer to cards by number when giving feedback. Format each card with **Front** and **Back** on separate lines, with blank lines between paragraphs of the back. Separate cards with `========================`. See the examples at the end of this skill for the exact format.

3. **Iterate**: The user will review and ask for edits, removals, or additions. Revise the list accordingly.

4. **Add cards**: When the user confirms (e.g. "add them", "looks good", "go ahead"):
   - Create a temp dir: `TMPDIR=$(mktemp -d)`
   - For each card N, write the front and back as HTML files in the temp dir (`$TMPDIR/1_front.html`, `$TMPDIR/1_back.html`, `$TMPDIR/2_front.html`, ...), then add ALL cards with a single invocation:
     ```
     cd ~/prog/AI/anki && uv run python anki_add.py add --cards_dir $TMPDIR --model 'YOUR_MODEL_ID'
     ```
   - Always pass your model ID (e.g. `claude-opus-4-6`). The script appends metadata (source, model, date) to the back automatically.
   - Pass `--deck` or `--notetype` if the user specified them (defaults: deck=Kn, notetype=b).
   - Clean up: `rm -rf $TMPDIR`

5. **Confirm**: Report how many cards were added.

Do NOT add the cards without user confirmation, even if you're running in auto mode or dangerously-skip-permissions mode. Nothing goes in the user's Anki collection without review.

## Card style guide

### Formatting
- Topic tags in parens at the start of Front: `(is)`, `(AI)`, `(net)`, `(CS)`, `(fin)`, etc. Multiple tags ok: `(AI) (is)`.
- Terse fronts: "def X", "what's X?", "X: acronym", "X vs Y". No filler words.
- Concise backs: get to the point. No "The answer is..." preamble. Sometimes just one word.
- Parenthetical asides for nuance, caveats, mnemonics.
- HTML for formatting in the actual card content: `<div>`, `<br>`, `<a href>`, bold/italic sparingly. Other inline tags (`<em>`, `<ul>`/`<li>`, `<img>` placed mid-paragraph) are fine when they aid reading. No markdown in card content.
- Links to sources at the bottom of the back when the card comes from a specific article/paper. Use `<a href="URL">URL</a>` format.
- When proposing cards to the user in chat:
  - Use actual line breaks between paragraphs, not HTML tags.
  - Do NOT show layout tags (`<div>`, `<br>`) — those are only for the actual card content when adding.
  - DO show all other HTML tags (`<a href>`, `<b>`, `<i>`, `<ul>`, `<li>`, `<img>`, etc.) so the user can verify them.
  - Wrap each line in backticks so the user sees exactly what will go into the card.
  - Separate cards with `========================`.
- Do NOT include metadata in the card content. The script automatically appends metadata (source, model ID, date) to the back of every card.

### Content
- One fact per card. Atomic.
- Every back must contain an atomic gradable fact — the thing the user is expected to recall — preferably near the top. Beyond that core answer, feel free to include related context, supporting data, citations, fun facts, anecdotes, or asides that enrich the card. The user grades on the core fact and reads the rest for interest. Don't strip enrichment out in the name of conciseness when it adds genuine value.
- Front should be a clear, unambiguous prompt. Don't give away the answer in the front.
- For "def X" cards, the first sentence of the Back should be a short plain-English description of what it is (e.g. "a similarity hashing algorithm for near-duplicate detection"), followed by the detailed explanation.
- For definitions, add a concrete example at the end if the concept is abstract.
- For formal definitions (math, CS), include both the precise definition and an intuitive summary.
- For "acronym" cards, use "X: acronym and definition" as the Front, so the Back includes both.
- "def X" vs "explain X" / "high-level description of X": use "def X" when X is a *term* (the answer is essentially what it means). Use "explain X" or "high-level description of X" when X is a *mechanism, algorithm, or attack* and the answer is procedural — i.e. you're describing how it works, not what it is.
- Embed problem context in the front when the question is about a solution. E.g. `(net) how does QUIC solve the Parking Lot Problem (overhead of establishing a new connection in TCP when switching networks because the server was relying on the IP address of the client)?` The back can then be a clean mechanism without re-explaining the problem.
- When the source's wording is sharper than any paraphrase you'd write, include the verbatim quote in `"…"` after a brief paraphrase. Don't lead with a long quote — the paraphrase first establishes the takeaway, the quote then provides the evidence/voice.
- When including non-trivial numerical examples, verify the computations by running a one-off Python script in the background before proposing the card.
- Verify factual claims that aren't common knowledge before proposing the card: specific dates, percentages, "first X to do Y", attributions ("X said Y"), historical sequences. Use WebSearch/WebFetch. Same standard as numerical examples: don't propose unverified specifics.

### Papers and articles
- Most papers get a SINGLE summary card. Two or three only if truly warranted.
- Format: Front = `(tags) summary of "Full Paper Title" (Author1, Author2, ... Mon Year)`
- Always include full author names (First Name Last Name, not just last names). If > 5 authors, use: first 3, ..., last 2. Date is Mon Year (e.g. "Mar 2026").
- Other cards referencing the paper should include the full paper title and authors in parentheses at the end of the Front.
- Back = short summary + key mechanism/pipeline/method briefly included so the card is self-contained + arxiv/source link at the bottom.
- ALL cards that reference a specific paper should include the link at the bottom of their back (before metadata).
- Use the earliest public date for the paper (usually the arxiv submission date, not the conference date).
- When first proposing cards that reference papers, search online to verify the exact title, author list, date, and URL. No need to re-verify after each user edit.
- Every time cards are shown, output "✅ I checked the paper information online and confirmed that the title, date, URL, and author list are correct." before the cards.
- Multi-paper cards: when a single concept genuinely spans multiple papers (e.g. introduction paper + later application paper), each citation gets the full title + authors + Mon Year + arxiv/source link. Use this sparingly — only when the concept can't be cleanly split into separate cards. Example: a `(AI) def JumpReLU` card that cites both the original 2019 adversarial-defense paper and the 2024 SAE-application paper.

### Card overlap
- It's fine and even good for multiple cards to have overlapping information. Each card should be self-contained and readable on its own. Redundancy aids memorization.

## Examples

The following 15 cards span the patterns covered above (atomic def, X vs Y, algorithm with images, paper summary, article summary, LaTeX math, counterintuitive concept, embedded quote, etc.). Use them to calibrate style.

**1.**
`Front: (hw) what's a Tensor core in a GPU?`
`Back: a unit that performs very effective matrix multiplication`
``
`most important consideration for deep learning according to <a href="https://timdettmers.com/2023/01/30/which-gpu-for-deep-learning/">https://timdettmers.com/2023/01/30/which-gpu-for-deep-learning/</a>`

========================

**2.**
`Front: git reset: 3 options in order of number of steps done`
`Back: --soft`
`-- mixed`
`-- hard`

========================

**3.**
`Front: (is) vertical vs horizontal privilege escalation`
`Back: Vertical Privilege Escalation: Attacker goes from low-level privilege to high-level privilege (often admin or root).`
`Horizontal Privilege Escalation: Attacker moves laterally across users with the same level of privilege.`

========================

**4.**
`Front: (CS) explain the "path compression" optimization of Union-Find`
`Back: when finding the root of an item, also make all intermediate parents point directly to that root.`
`go from:`
`<img src="paste-f2d7661342f3c76fa753c9e9e2888e0135cd7d35.jpg">`
`to:`
`<img src="paste-a9288bff9c1015676d5fdf98d96ea9356e072fdf.jpg">`

========================

**5.**
`Front: (is) high-level description of the DUAL_EC_DRBG backdoor`
`Back: constants P and Q had to be chosen at random for the security proof to work. But the specification provided default values of P and Q (chosen by the NSA), which many used`

========================

**6.**
`Front: (AI) explain (non-sparse & sparse) mixture of experts (MoE)`
`Back: in the feed forward layer, instead of a single block, there are multiple (e.g. 8). There is now a routing function for these blocks.`
`- non-sparse: each token is routed through each expert. Number of active parameters = number of total parameters.`
`- sparse: each token is only routed through e.g. 2 out of 8 experts`
``
`routing function (itself based on a feed-forward neural net):`
`<img src="paste-0b944f886874a83217483d92150c89174558d233.jpg">`
`(if K = the number of blocks, it's non-sparse)`

========================

**7.**
`Front: (is) how can hard drives be used as microphones??`
`Back: the Position Error Signal (PES) measures the offset of the head from the center of the track. Ordinarily used in a feedback control loop. Can be used to capture sound. Speech can be parsed!`
``
`(<a href="https://www.gwern.net/docs/technology/2019-kwong.pdf">https://www.gwern.net/docs/technology/2019-kwong.pdf</a>, 2019)`

========================

**8.**
`Front: better than f"here we have myvar={myvar}"`
`Back: f"here we have {myvar=}"`

========================

**9.**
`Front: (AI) (is) summary of "Buffer Overflow in Mixture of Experts" (Jamie Hayes, Ilia Shumailov, Itay Yona, Feb 2024)`
`Back: IF there's a finite queue in front of each expert (in order to equalize use of the different experts, at the expense of lower output quality), then an adversary can fill up one of the queues to force other tokens in the same batch to be routed to a different expert than the one they should have.`
`<img src="paste-aec2d62c6d0d5cf672b5bdcc3425519b4a653dbd.jpg">`
``
`<a href="https://arxiv.org/abs/2402.05526">https://arxiv.org/abs/2402.05526</a>`

========================

**10.**
`Front: (econ) summary of "Is the great stagnation actually just a 'so-so' stagnation?" (Maxwell Tabarrok, Nov 2024)`
`Back: people are getting more educated, but this is mostly signalling: they don't actually perform better.`
`(test score average across the population doesn't change, while it declines in every educational attainment group).`
`Yet economists use years of education as an input in their calculation of TFP (as a contributor to human capital).`
`So the decline in TFP may be in part caused by more educated people resulting in the same results.`
`Removing the educational attainment adjustment, the great stagnation is reduced by a third`
``
`<img src="paste-79a1d3f980044a84163c10dd14be3b0873ba19d7.jpg">`
`<img src="paste-a914387e6a8a5f9246295aee780a698540fc616d.jpg">`
``
`<a href="https://www.maximum-progress.com/p/is-the-great-stagnation-actually">https://www.maximum-progress.com/p/is-the-great-stagnation-actually</a>`

========================

**11.**
`Front: [latex](markov) marche aléatoire sur $\mathbb{Z}$ : comment est la marche si $p \neq \frac 1 2$ ?[/latex]`
`Back: transitoire`

========================

**12.**
`Front: (fin) (hist) what's the biggest single-day loss in the SP500?`
`Back: -20.47% in 1987`
``
`in recent times: around -12% (-11.98%) in March 2020 (2020-03-16)`
``
`<a href="https://en.wikipedia.org/wiki/List_of_largest_daily_changes_in_the_S%26P_500_Index">https://en.wikipedia.org/wiki/List_of_largest_daily_changes_in_the_S&amp;P_500_Index</a>`

========================

**13.**
`Front: (econ) why are voters rationally ignorant in a democracy?`
`Back: because there are low payoffs to more knowledge: each voter has a very small chance of changing an election. Similar to a teacher that would grade a test not individually, but assigning the average score to everyone`

========================

**14.**
`Front: (SSC) def weak man fallacy`
`Back: attacking not an argument no one really holds (straw man), but an argument only a few unrepresentative people hold`
``
`<a href="https://slatestarcodex.com/2014/05/12/weak-men-are-superweapons/">https://slatestarcodex.com/2014/05/12/weak-men-are-superweapons/</a>`

========================

**15.**
`Front: why is boycotting palm oil a bad idea?`
`Back: because it's insanely productive, by a factor of about 10`
``
`One hectare of palm currently gives us 2.8 tonnes of oil in return. Olives give us 0.3 tonnes. Coconuts give us 0.26 tonnes – that's 10 times less. Groundnuts, just 0.18 tonnes.`
``
`that is, if it's replaced by other oils. But in e.g. shampoos and cosmetics, synthetic oils can be used instead. It's also stupid to use it as bioethanol.`
``
`"Globally, we only put small amounts of palm oil into bioenergy. Just 5% of production. But for some countries – often the richest ones – bioenergy is a big user of palm oil. Germany is one example: 41% of its palm imports go to bioenergy. That's more than it imports for food products. This is incredibly stupid, and terrible for the environment. To be clear: Germany imports palm oil from an area at high risk of tropical deforestation to put it into <em>cars</em>. What's even more insulting is that it then counts this towards its 'renewable energy' target. In reality, biodiesel from palm oil results in more carbon emissions than petrol or diesel."`
``
`source: <a href="https://www.hachettebookgroup.com/titles/hannah-ritchie/not-the-end-of-the-world/9780316536752/">Not the End of the World</a>, Hannah Ritchie (2024)`

### Images
- Use images when they save the back from transcribing something visual: formulas (when LaTeX would be unwieldy), before/after diagrams (e.g. an algorithm transformation), schematics, plots embedded in articles. Don't add an image just for decoration.
- Anki media lives in `"$HOME/.local/share/Anki2/User 1/collection.media/"`. Each card references a media file by filename only: `<img src="filename.png">`. The collection database doesn't store paths.
- Workflow during review:
  1. Source the image (provided by user, downloaded from a paper/article via WebFetch, or generated locally e.g. matplotlib/mermaid/graphviz).
  2. Save it to a temp location, e.g. `/tmp/anki_review/<n>.png`.
  3. Show the user with `eog /tmp/anki_review/<n>.png &` (opens a separate window — Claude Code does not currently render inline images, see anthropics/claude-code#29254). Mention the path in chat so the user can re-open it if needed.
- Workflow on approval:
  1. Pick a descriptive filename for the media dir. Verify it's not already taken: `ls "$HOME/.local/share/Anki2/User 1/collection.media/<name>.png"` should return "no such file" — if it does exist, pick another name.
  2. `cp /tmp/anki_review/<n>.png "$HOME/.local/share/Anki2/User 1/collection.media/<name>.png"`
  3. Reference `<img src="<name>.png">` in the card's HTML.
- Copyright is not a concern: this is a personal Anki collection, not redistribution.
