---
name: section-drafter
description: >
  Writes one markdown file per RFP response section, grounded in the coverage matrix
  and collateral brief. Every claim is either traced to a source or flagged as an
  assertion. Trigger when the user says "draft the sections," "write the response,"
  "start drafting," or after the requirements mapper has produced coverage-matrix.md.
  Can also be triggered for a single section: "draft the technical approach" or
  "write the security section."
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

## Inputs

- **`brief.md`** — collateral brief with client vocabulary, tone signals, and evidence map
- **`coverage-matrix.md`** — per-requirement coverage classification and recommended actions
- **`gap-report.md`** — gap details for areas where evidence is missing
- **RFP document(s)** — the original RFP for section structure, page limits, and evaluation criteria
- **Section templates** from `assets/section-templates/` — structural starting points for each section type

## Outputs

- **`response/*.md`** - the response text, one file per Heading 1 of the response template docx, with every docx heading mirrored exactly (see CLAUDE.md). `/rfps:new-engagement` creates the files with the headings and empty bodies; the drafter writes text under the existing headings. It never renames, adds, or removes a heading: heading changes are made in the template docx and the files updated to match.

---

## Purpose

This skill produces the actual proposal prose. Every sentence must earn its place: it either answers a requirement, provides evidence, or builds the evaluator's confidence. The drafter does not invent — it composes from evidence. Where evidence is absent, it says so. The coverage matrix is the drafter's permission slip: Grounded means cite, Assertable means claim with a flag, Gap means acknowledge honestly.

## Process

### Step 1: Read the Structure from the Response Template

The structure comes from the response template docx, whose headings are mirrored in `response/*.md`. List those headings and check them against what the solicitation prescribes:

1. **Explicit section list** in the solicitation ("The response shall contain: 1. Executive Summary, 2. Technical Approach...") - confirm each required section has a heading in the template, in the required order.
2. **Evaluation factors** - confirm each factor is answerable under some heading.
3. **No prescribed structure** - use the template as given and note which headings carry which evaluation emphasis.

If the template and the solicitation disagree (a required section with no heading, a different order), tell the user; do not rename or reorder headings yourself.

For each heading, identify:
- The page limit that applies (if any)
- Which requirements from the coverage matrix map to it
- The evaluation weight or priority signal for it

### Step 2: Select and Adapt Templates

Choose the appropriate template from `assets/section-templates/` for each section. The templates provide structure, not content — they show the skeleton the drafter fills with evidence and argument.

If the RFP's section does not match any template cleanly, adapt the closest template or draft from scratch following the drafting patterns in `references/drafting-patterns.md`.

### Step 3: Draft Each Section

For each section, write prose following these rules:

**Open with the client's problem, not your solution.** The first paragraph of every section should demonstrate that you understood what the client asked for. Use their vocabulary from the brief. Name their specific pain point. Then — and only then — describe how you address it.

**Specific before general.** Lead with concrete evidence: named projects, quantified results, specific technologies, named team members. Follow with the general capability claim. Never lead with the general claim and follow with "for example..." — the example should be the lead.

**Evidence before claim.** Structure paragraphs as: [Evidence] → [What it demonstrates] → [How it applies to this client]. Not: [Claim about our capability] → [Here's some evidence].

**Use client vocabulary.** The brief's Vocabulary & Tone Notes section lists the client's key terms. Use them. If the client says "platform modernization," do not say "digital transformation." If the client says "citizens," do not say "end users."

**Mark every claim.** Every substantive claim in the proposal must carry one of two markers:

- `[GROUNDED: source]` — this claim is directly supported by evidence. Cite the evidence source (collateral file, case study, certification). Example: `[GROUNDED: Acme Corp case study, 2024]`

- `[ASSERTION: rationale]` — this claim is reasonable but not directly evidenced. State why it is reasonable. Example: `[ASSERTION: standard capability for organizations of our size and maturity]`

These markers are for internal review. The empathy reviewer and compliance validator use them to assess the proposal's evidence quality. They are stripped during final assembly.

**Use the open-work markers too.** Where the solicitation or the team leaves something unresolved, write `[DECISION: what must be decided]` (a choice the team makes), `[OPEN: the question or missing fact]` (needs an answer or a stated assumption) or `[EVIDENCE NEEDED: what source would support this]`. Never settle these silently in the prose.

**Make the markers scannable.** Write each marker in its bracket form only; do not type the icons. After drafting, run `rfps-open-items --mark`. It puts a colored icon in front of every marker in `response/*.md` (🔴 DECISION, 🟠 OPEN, 🟣 EVIDENCE NEEDED, 🟡 ASSERTION, 🟢 GROUNDED) and writes `open-items.md` in the solution folder, a table of every marker with a link to its line, ordered decisions first. Keep the icon with its marker when you edit; the build ignores it. Tell the user where `open-items.md` is.

**Do not mark obvious statements.** Factual statements about methodology, process descriptions, and common knowledge do not need markers. Only substantive claims about capability, experience, and outcomes need marking.

**Match length to weight.** If the RFP allocates 40% of technical points to the approach section and 10% to the team section, the approach section should be proportionally more detailed. Do not pad thin sections to fill pages — evaluators punish filler. A concise, evidence-rich page beats three pages of padding.

### Step 4: Handle Gaps

When the coverage matrix classifies a requirement as Gap:

**Do not fabricate an answer.** An evaluator reading your response alongside your competitors' can tell the difference between a vendor who has done this before and one who is making it up. Fabrication is the single most damaging thing a proposal can do.

**Acknowledge and mitigate.** The honest approach: "We have not yet completed [X certification]. We have initiated the process and expect to achieve authorization by [date]. In the interim, our approach includes [compensating controls]."

**Frame the gap as a plan.** If you lack experience in a specific area but have relevant adjacent experience, say so: "While we have not implemented [specific technology] in [specific context], our team has delivered [adjacent technology] in [similar context], including [specific project]. Our approach to [this requirement] builds on that experience."

**Never leave a gap unaddressed.** Silence on a requirement is worse than honest acknowledgment. The evaluator assumes silence means inability, not oversight.

### Step 5: Add Section Bridges

Each section should end with a forward reference to the next section where appropriate. This creates narrative flow for evaluators reading sequentially:

"The technical architecture described above is operationalized through our staffing approach, detailed in the following section."

Bridges should be natural, not formulaic. If the sections are independent, skip the bridge.

## Graceful Degradation

**Coverage matrix heavily weighted toward Assertable/Gap:**
- Proceed. Draft the sections, but expect heavy `[ASSERTION]` marking.
- The empathy reviewer and compliance validator will flag sections that are insufficiently grounded. This is correct behavior — it surfaces risk for the team.

**Missing brief (collateral analyzer was skipped):**
- Draft from the RFP alone. All claims will be assertions.
- Use generic professional tone in the absence of client vocabulary signals.
- Flag this prominently: sections lack client-specific framing and grounding.

**Single section requested (not full proposal):**
- Draft only the requested section. Still read the full coverage matrix and brief for context.
- Note which requirements are addressed and which fall outside this section's scope.

**RFP has no clear section structure:**
- Use the canonical order from the assembly template.
- Note in each section file which RFP requirements it addresses, since the mapping is the drafter's interpretation rather than the RFP's explicit structure.

## Integration with Other Skills

- **Empathy Reviewer** reads `response/*.md` and reviews it for tone, voice, and client-centricity
- **Compliance Validator** reads `response/*.md` and checks it against RFP compliance requirements
- **The build** (`/rfps:build-wip`, `/rfps:build-final`) pours `response/*.md` into the response docx
