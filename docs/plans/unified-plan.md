# Hookline — unified plan (Rev 1)

*Working name. The two tracks merge here; `melodic-ancestry-mvp.html` (product) and
`mvp-implementation-plan.md` (research) remain the source documents for their halves and are not
discarded — this supersedes only the claim that they are separate strategies.*

---

## The shape, in one paragraph

**You drop in an MP3. It finds the hooks, and for each one tells you how ordinary it is and what
came before it.** Not "this song copied that song" — never that. For each melodic figure the system
extracts, it returns a count with its list: *this figure appears in N works, M of them predating
this recording*, with the works enumerated, dated, playable, and an interval around N and M that
widens as the transcription gets less certain. Where a human has already documented a derivation,
it shows the chain and says a human documented it. Where the figure is a musical building block, or
where the earliest instances are folk, it says so and names nobody.

That is the product. It is also the instrument that produces two measurements nobody has published.

---

## Why the combination is not a compromise

The two tracks looked separate because one was a critique and the other was a build. They are the
same argument seen from both ends.

The research track's destructive half says litigation-derived benchmarks measure whether a pair was
*sued*, and that the corpus is ~2 orders of magnitude too small to resolve the differences the field
reports. Its **constructive half** — A5 — already names the replacement: *"threshold-free metrics
with CIs, and rarity / prior-art counts, which are symmetric and not outcome-dependent."*

That sentence is a product specification. The Rarity Index is what it describes. So:

| | Was | Now |
|---|---|---|
| Research track | A separate publication effort | The evaluation protocol and the honesty constraints of the product |
| Product track | A build with a deferred audio path | The instrument that generates the missing measurements |
| MP3 ingestion | The largest unmeasured risk, deferred behind gate 2 | The research contribution, promoted to the centre |

**The pivot.** CLAUDE.md records that *how transcription error compounds into downstream symbolic
matching accuracy on commercial pop* is unmeasured anywhere in the literature. The old plan treated
that as a reason to stay symbolic. Inverted: it is the one place where a small team can produce a
first result, it sits directly on the product's critical path, and the measurement **is** the
product's confidence model. You cannot ship honest intervals on N and M without it, and nobody has
it. Measuring it is both the paper and the feature.

### Three things audio unlocks that symbolic-only cannot reach

1. **The pop denominator.** The Rarity Index's whole defensibility is its denominator, and the
   available symbolic corpora skew folk and classical. Müllensiefen & Pendzich (2009) got 90%
   (18/20) on MCIR cases by weighting pitch-interval profiles for rarity against **14,063 pop
   songs** — the strongest published evidence that rarity discriminates, and it was measured on pop.
   BMM-Det's authors record that their dataset "is not public and also out-of-date." *The precedent
   exists and the corpus does not.* A transcription pipeline is how you rebuild it.
2. **Metric position, which the symbolic benchmark destroyed.** MCIC's MIDI has rests removed in
   97.34% of transitions, so cumulative onset no longer equals score position and Savage's
   *stressed* / *unstressed* levels are unrecoverable. Beat and downbeat tracking on audio recovers
   them directly. The rhythm-weighted edit distance (final > stressed > unstressed > ornamental)
   that both prior documents call for is **only implementable on the audio path.**
3. **Hook detection.** The interesting figure in a song is the repeated one. Self-similarity over
   audio finds it without anyone specifying a query. This is what makes it fun to use rather than a
   tool you have to already know how to drive.

---

## Input and output

### Input
- An **MP3** (or any decodable audio; a clip, a full track, a phone recording of someone humming).
- Optionally: a date to compare against. Defaults to the recording's own release date, resolved via
  the Ledger where the track is identifiable, or supplied by the user.
- Symbolic input (MIDI, notation) stays supported as a first-class path — it is the high-confidence
  stratum, and it is what you fall back to when the audio path abstains.

### Output — a provenance card per figure

For each hook the system finds, in a timeline view over the waveform:

| Field | Content |
|---|---|
| The figure | Notated, plus the extracted audio phrase, playable |
| Transcription confidence | Per-note, carried from the f0 stage; drives everything below |
| **N** | Works in the corpus containing the figure, **with a credible interval** |
| **M** | Of those, how many predate the reference date, with its interval |
| Rarity percentile | Position in the corpus frequency distribution, **reported per stratum** |
| The list | Every matching work: title, artist, date, corpus of origin, playable where rights allow |
| Lineage | A derivation chain **only where a human curated one**, labelled as such |
| Verdict | `distinctive` / `commonplace` / `no single originator` / `insufficient confidence` |

### What it will never output

Carried verbatim from the MVP brief, and now enforced in code rather than in prose:

- A similarity percentage presented as a conclusion.
- An "X copied Y" claim derived from the model. Direction comes from dates and curated edges or it
  is not claimed.
- A named originator where the earliest instance is folk or public-domain material.
- A count without its denominator, or an N without its interval.

The abstention paths are not error handling. They are four of the seven possible outputs.

---

## The three novel claims

Stated as things that are true of no existing system, so they can be checked and killed.

1. **Error-aware retrieval.** Transcription uncertainty is propagated as a *lattice* — top-k note
   hypotheses with posteriors — into n-gram counting, so the output is a distribution over N and M
   rather than a point estimate off a single wrong transcription. Prior-art counts have never been
   published with uncertainty attached, because they have always been hand-compiled.
2. **The compounding curve.** How much of a known melodic relationship survives audio → symbolic on
   commercial pop, as a function of n-gram length, encoding, arrangement density and vocal vs
   instrumental lead. Unmeasured anywhere.
3. **Computational prior art.** In *Structured Asset Sales v. Sheeran* the court counted 29 prior
   uses, 23 predating, and that enumeration carried the holding — **hand-compiled.** A
   machine-produced enumeration with a stated denominator and a stated error model is the same
   evidentiary form, untested, and on the admissible side of the line Yen draws.

---

## Architecture

```
MP3
 ├─ beat / downbeat / key / tempo ──────────────┐  (restores metric stress)
 ├─ source separation (lead / vocal stem)       │
 ├─ f0 + note events, WITH per-note confidence  │
 ├─ phrase segmentation                         │
 └─ hook ranking by repetition (SSM)            │
                                                ▼
                          figure → 5 encodings (pitch, interval,
                          scale degree, contour ×2), n = 4–12
                                                │
                          top-k lattice, not one string
                                                ▼
        ┌───────────────────────────────────────────────────┐
        │  INVERTED N-GRAM INDEX — STRATIFIED, NEVER POOLED │
        │   S1 clean symbolic   Meertens 18,618 · Essen ·   │
        │                       Themefinder                 │
        │   S2 transcribed pop  built by this pipeline,     │
        │                       carries its own error model │
        └───────────────────────────────────────────────────┘
                                                │
                          count + date filter (dates from Ledger)
                                                ▼
                    N ± CI · M ± CI · rarity percentile per stratum
                                                │
                          abstention gate → verdict
                                                ▼
                   provenance card  +  curated lineage if one exists
```

**The Ledger** (MusicBrainz work-rels, Wikidata P144/P4969/P2550 → dated directed edge table, Katz
centrality) is unchanged from the MVP brief and now serves three jobs instead of one: it supplies
the release dates the date filter needs, the curated chains the UI displays, and the **positive
pairs the whole system is evaluated on**.

### The stratified denominator

The denominator problem is still the thing most likely to kill the product, and stratification is
the answer to it. S1 and S2 are counted, reported and percentiled **separately, always**. A court —
or a user — asking "what was this drawn from?" gets a per-stratum answer with a per-stratum error
model, rather than one pooled number that quietly averages a clean folk corpus with a noisy
transcribed one. Pooling is the failure mode; the schema forbids it.

### Evaluation — known-item retrieval, not accuracy

This is where the research track's conclusion becomes the engineering protocol. **We do not evaluate
against litigation labels.** The metric is: given the derivative's MP3, does the known ancestor
appear in the returned prior art, and at what rank? Recall@k over the Ledger's curated chains.

That metric is symmetric, threshold-free, needs no outcome labels, has a growing rather than fixed
denominator (every curated chain the Ledger surfaces is a new test item), and sidesteps every defect
Claims 1–3 identify in the existing benchmarks. It is the honest measurement the critique argues
for, used on ourselves first.

---

## Phases, gates and calendar

One engineer, starting 2026-09-07. Publishable results fall out at week 6 and week 13; the app is
usable at week 18.

| Phase | Weeks | Ships |
|---|---|---|
| **P0** Access, freeze, pre-registration | 1 | The four week-one questions answered; artifact SHAs frozen; E1 and E2 pre-registered before any measurement |
| **P1** The Ledger | 1–3 | Dated edge table + Katz + lineage browser. Unchanged from the brief |
| **P2** The audio spike = **E1** | 2–6 | The compounding curve, and the confidence model derived from it |
| **P3** Index + stratified denominator | 5–11 | Lattice query path over S1 and S2, N/M with intervals |
| **P4** Rarity separation = **E2** | 10–13 | Gate 3, measured per stratum |
| **P5** The app | 12–18 | MP3 in, annotated timeline out, playable comparisons, abstention verdicts |
| **P6** Publications | parallel | See below |

### Gates

| Gate | Week | Question | If yes | If no |
|---|---|---|---|---|
| **1** | 3 | Enough dated directed edges for chains ≥ 3? | Lineage browser ships on its own while the index is built | Expected. Confirms the undocumented tail is the opportunity; edges become evaluation data |
| **2** | 6 | Does the melodic relationship survive audio → symbolic on 50 known pairs, and does top-k lattice recover what top-1 loses? | Audio-first is alive; S2 gets built; the app has its front end | The curve is still the paper — **we would be first** — and the product retreats to symbolic input with S1 only. The measurement is valuable in both directions |
| **3** | 13 | Does rarity separate known hooks from archetypes, per stratum? | Ship the prior-art index. Direction reduces to a date join | Index still ships as the denominator; the ancestry ambition retires loudly. Also publishable |

Note that **every gate is publishable in both directions.** That is deliberate: it is what stops the
project from having a failure mode where nothing comes out.

### Why gate 2 is honestly at risk

Basic Pitch's note-level F is **0.35 on monophonic vocals**, 0.65 on solo guitar. That is the number
that makes gate 2 a real gate and not a formality. The lattice design exists precisely because a
single top-1 transcription at that accuracy is not usable — the hypothesis under test is that the
correct notes are *present* in the top-k with recoverable posterior mass even when they are not
ranked first. If they are not, audio-first dies at week 6 having cost four weeks and produced a
first-in-literature measurement. That is an acceptable worst case.

### Publications

- **TISMIR** "Open Music Data" special collection, **1 December 2026** — the benchmark-validity
  paper, Claims 1–3 of `mvp-implementation-plan.md`. Needs no code and is largely written. Primary
  target, unchanged.
- **ISMIR 2026 LBD, 25 September 2026** — 18 days out. Claims 1 and 3 only, no code. Reachable if
  wanted; skip without loss.
- **ISMIR 2027** (London, Sept 2027) — E1 and E2: the compounding curve, error-aware retrieval, and
  the rarity distribution on a pop-weighted corpus. This is the new work.

The tone rule from the research plan is binding here too: every claim about another group's work is
an observation against a cited artifact version, never an attribution of error to people.

---

## What P0 must settle before anything else

The four questions from the brief, plus two the audio path adds.

| | Question | Blocks |
|---|---|---|
| 1 | Does WhoSampled offer an API, licensed feed, or bulk access? | Highest leverage — 42,447 directed dated records are the exact asset the only working ancestry paper ran on. Turns the Ledger from probe into graph |
| 2 | What audio can we legally hold, and at what scale? | S2 entirely. Note the asymmetry: *transient* per-query decoding for the front end is a far smaller ask than a stored corpus. Separate the two before asking anyone |
| 3 | Is there a commercial-pop symbolic corpus with defensible provenance? | If one exists, S2 may not need building at all |
| 4 | SecondHandSongs' actual schema | A second curated derivation layer for free, if `basedOn`/`derivedWorks` exist. One afternoon |
| 5 | **Licence audit of the audio stack** | Demucs, Basic Pitch, CREPE, madmom, Essentia — several are AGPL, NC, or carry patent notes. *Do not assume; check each.* Distinguish "may we run it locally" from "may we ship it" |
| 6 | **Where do 50 known interpolation pairs with obtainable audio come from?** | E1 is not executable without them. Ledger chains + WhoSampled + the Cronin/MCIR lineage |

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Denominator skew — a count is only evidence if the corpus is representative | **Critical** | Stratification, never pooling; per-stratum percentiles; P0-3 first |
| Transcription too noisy even for a lattice (0.35 note-F) | **Critical** | Gate 2 at week 6, publishable in both directions; symbolic fallback preserved |
| Cannot legally hold audio at corpus scale | **High** | P0-2 splits transient decode from stored corpus; S1-only product remains viable |
| Fun demo pulls the product toward "X copied Y" | **High** | The four never-ship rules enforced in the output schema, not in prose |
| Rarity does not separate | **High** | Gate 3 publishable either way; Müllensiefen precedent says it separated on pop once |
| Ground truth still ~100 pairs | Medium | Known-item retrieval over Ledger chains grows the test set instead of consuming it |
| Audio stack licensing blocks commercial use | Medium | P0-5 before any of it lands on the critical path |
| Scope: this is three builds plus two measurements | Medium | Each phase ships standing alone; P1 and P3 are products at their own gates |

---

## Open items inherited

Unchanged and still open: the Muñoz Melo UPF thesis (WAF-blocked, the last novelty check),
Malandrino et al. (2022) full text (bot-walled, figures second-hand, do not cite), Howard (2025)
IJDSA (paywalled), MelodySim's MCIC negative construction and audio rendering, and whether its
checkpoint is frozen across the 20-fold and 2-fold variants.

And the caveat that started all of this: the Kjarkas → Lambada → *On the Floor* chain was never
independently verified. It stays in the demo as the worked example of a chain that exists **because
a human wrote it down** — which is the whole point of the tail we are building for.
