# Melodic Ancestry

Research project on tracing a song melody snippet back to its earliest source — "melodic
provenance." Motivating example: the "dance the night away" hook in J.Lo's *On the Floor*
descending from Los Kjarkas' *Llorando se fue* via Kaoma's *Lambada*.

Goal is either an ML pipeline that traces melodies to their originators, or a
knowledge base built on musical heuristics. As of 2026-09-07 there is a **working prototype**
(`hookline/`, see `README.md`) alongside the research documents.

## Contents

Everything lives under `docs/`, split by how a file is used: `plans/` is edited, `published/`
has live URLs and must be republished carefully, `research/` is the frozen source material.

| Path | What |
|---|---|
| `docs/plans/unified-plan.md` | **Current plan (Rev 1).** Merges both tracks and adds MP3 ingestion. Read this first. |
| `docs/plans/mvp-implementation-plan.md` | The research-track plan (Rev 4). Source document for the publication half of the unified plan. |
| `docs/published/unified-plan.html` | The unified plan as an Artifact. Working name **Hookline**. |
| `docs/published/melodic-ancestry.html` | The research report. |
| `docs/published/melodic-ancestry-mvp.html` | The three-route MVP brief. |
| `docs/research/` | The recovered deep-research output — both passes, markdown + authoritative JSON. See its README. |
| `hookline/` | **The prototype.** MP3 → provenance cards. See `README.md`. |
| `scripts/`, `tests/` | Index build, evaluation, degradation sweep, ledger seed; 35 invariant tests. |
| `data/` | Corpora (gitignore-worthy: 80 MB gz + 570 MB SQLite) and measured results as JSON. |

Published at:
- unified plan — **https://claude.ai/code/artifact/376f21fe-b705-48bf-9d71-d878766c5271**
- report — **https://claude.ai/code/artifact/5e9676f7-4b92-4953-9c79-89226fc49b4b**
- MVP brief — **https://claude.ai/code/artifact/513122c9-1752-4bc2-86a2-bbf18b586b51**

To update any of them, edit the file and republish with **both** `file_path` and `url` set to the
matching link. Publishing without `url` from a new conversation creates a *separate* artifact
instead of updating the existing one. The file paths above are load-bearing: an artifact redeploys
to the same URL only from the same path, so **move a published file and you must pass `url`.**

All three share one design system: Source Serif 4 / Bricolage Grotesque / IBM Plex Mono, and the
same `--paper`/`--ink`/`--accent` token block. The MVP brief and the unified plan add validated
data-viz slots
(`--s1..3`, `--ord-1..4`) — categorical all-pairs and ordinal, both modes, checked with the
dataviz skill's `validate_palette.js` against surfaces `#FFFFFF` / `#151C19`. Re-run it if
those change. The unified plan re-ran that validator on 2026-09-07: `--s1..3` pass every check in
both modes on all pairs; the one WARN is aqua `#1baf7a` at 2.82:1 on the light surface, which
obliges visible direct labels on any mark using it.

## What the research concluded

Don't re-litigate these — two verification passes established them. Full evidence and
citations are in the report.

1. **Similarity is solved enough; ancestry is not.** Catalog-scale retrieval of melodic
   relatives works and is open source. But across every verified system, directionality —
   who copied whom — was supplied by human curation, encoded by construction, or decided by
   manual musicological judgment. It was **never learned from the music.**

2. **Plan for direction to come from metadata, not the model.** Release dates joined against
   a curated relationship graph (MusicBrainz work relations, Wikidata P144/P4969, WhoSampled).
   The ML pipeline's job is candidate generation and localization, not adjudication.

3. **The defensible product is a prior-art index, not an originator oracle.** Yen (58 U.C.
   Davis L. Rev. 553, 2024) draws the line courts actually use: rarity evidence is admissible,
   similarity verdicts are not. Experts are being excluded under Rule 702 for asserting a
   figure is rare without having analyzed prior art (*Johannsongs v. Lovland*). "This figure
   appears in N recordings, M of them predating X" is the thing nobody has and courts want.
   It's symmetric, so it sidesteps the direction problem entirely.

4. **Synthetic training data does not transfer.** MelodySim: 0.98 F1 in-domain → 0.73 on 116
   real court cases, where plain DTW-CQT *beats* it on accuracy (0.71 vs 0.67). BMM-Det is
   perfect on transposition but drops to 0.33 top-1 on genuinely rewritten melodies — which is
   exactly what a cross-genre interpolation looks like. Query-by-humming falls from ~0.9 to
   0.707 top-10 going from 2k to 90k songs.

5. **Ground truth is the binding constraint.** ~29 real plagiarism pairs in 2021, ~70 by 2025.
   MCIC's 116 cases are all labelled positive even though 66 were denied in court. Any
   precision number in this field rests on roughly a hundred examples.

6. **"Find the original" may be ill-posed for folk/public-domain material** — the material
   hooks most often come from. Savage et al. found zero highly-related cross-tradition pairs;
   the 2025 phylogenetics rooting failed and needed manual override. Build an abstention path
   that returns "no single originator" rather than a name.

## One project, two deliverables

As of 2026-09-07 the two tracks are **merged** into `unified-plan.md` (working name: Hookline).
Earlier guidance said they must not be read as one strategy — that is superseded. The unifying
argument: the research track's constructive half (A5) recommends the field replace outcome-labelled
accuracy with *symmetric, dated prior-art counts with intervals*, which is exactly what the product
track ships. One is the argument, the other the instrument.

- **Product** — MP3 in, a provenance card per hook out: N works contain this figure, M predate this
  recording, with intervals, a per-stratum rarity percentile, and loud abstention. Never a direction
  claim from the model.
- **Publication** — unchanged for TISMIR (1 Dec 2026, benchmark validity, needs no code); plus two
  new measurements the audio path generates: transcription-error compounding on commercial pop (E1,
  unmeasured anywhere) and rarity separation on a pop-weighted corpus (E2).

The pivot that makes it work: audio was previously the deferred risk. It is now the centre, because
the unmeasured thing sitting on the product's critical path is the same thing nobody has published.
Every gate is publishable in **both** directions.

Still binding regardless of track: `mvp-implementation-plan.md`'s thesis that litigation-derived
benchmarks measure whether a pair was *sued*, that the reported differences are smaller than the
variance of the threshold protocol, and that MCIR's 354 cases at ~11/year are two orders of magnitude
too small — detecting the 1.29-point gap the field publishes would need ~11,600 decided cases. Every
figure there was verified against a primary artifact; its open items list is the only unverified
material.

## What the prototype measured (2026-09-07)

Real numbers from `scripts/evaluate.py` and `scripts/degradation.py`, on an index of 17,446 works
(2.15M figures, 7.14M postings) built from Meertens MTC-FS-INST and Essen. Ground truth is tune-family
membership, not litigation labels.

1. **The dominant transcription error is segmentation, not pitch.** 92% of test melodies lost notes,
   0% gained them, and when the note count was right the pitches were 100% exact — consecutive notes
   at the same pitch were merging. Onset-based splitting took exact recovery from 3/40 to 38/40.
   Consequence: **a pitch lattice cannot repair a segmentation error**, because the n-gram window is
   already misaligned. If the lattice is extended, extend it over segmentation hypotheses.
2. **The lattice buys nothing until transcription degrades, then ~5–6 points.** Clean audio: identical
   to top-1. Worst condition (conf 0.729): self-retrieval 18% → 23%, family 13% → 19%. So the design
   bet is **untestable on clean synthetic audio** — gate 2 must run on real mixes or it answers nothing.
3. Known-item retrieval, n=200: symbolic 100%/69.0% (self/family), audio top-1 100%/66.0%. All of it
   an **upper bound** — synthesised monophonic tone, no percussion, no competing instruments.
4. **The real-mix failure was a category error, not a tuning problem.** YIN is a monophonic tracker;
   on a full mix it follows the loudest periodic source, which in pop is the bass (94% of notes below
   C4 on *On The Floor*). Raising the pitch floor alone reaches vocal register but fragments the line
   (66/85 gaps beyond the rest threshold) and yields **zero** indexable figures. **Demucs vocals stem
   + a 150 Hz floor together** move the median from MIDI 43 to 60 and 6% → 51% of notes at or above
   C4. `separate.py`, wired in as `stem="auto"`.
5. **Separation must be conditional.** On clean synthesised monophonic audio Demucs made transcription
   *worse*. Auto-detect probes the raw mix and separates only when it looks bass-dominated.
6. **Our synthetic polyphonic benchmark (`mixture.py`) cannot validate learned separation.** It
   reproduces the bass-lock failure faithfully, but Demucs is trained on real recordings and does
   nothing sensible with synthetic sine stacks. Synthetic benchmarks test DSP; learned components
   need real audio. This is the same lesson as conclusion 4 of the research, arrived at from the
   other direction.

## Corpus status (2026-09-08)

Five strata, **30,434 works, 6.37M figures, 17.7M postings**: `lakh-clean` 10,011 (**Western
commercial pop**, CC BY 4.0 on the aggregation only, undated), `mtc-fs-inst` 8,986 (Dutch folk,
dated — the ONLY dated stratum), `essen` 8,460 (European folk, undated), `nottingham` 2,068
(British/Irish folk-dance, GPL-3.0, undated), `pop909` 909 (Chinese pop, MIT annotations, undated). Add one with `scripts/add_corpus.py`; the audio route is
`scripts/transcribe_corpus.py`. `hookline/midi.py` scores tracks to find the melody in a multi-track
arrangement — indexing the bass as if it were the tune is the MIDI-side version of the audio failure.

**The audio route (S2) cannot currently produce a dated, pop-weighted, legally clean corpus.**
Verified 2026-09-08 — no public source satisfies all three at once, and the three candidates each
fail a different one:
- **FMA small** (7.15 GiB, 8,000 tracks) — cleanest licence, 64% album-date coverage, but the
  authors' own paper says it "does not contain mainstream music and few commercially successful
  artists" and is "biased toward experimental, electronic, and rock." Legally clean, not pop.
- **MTG-Jamendo** — has an explicit `RELEASEDATE` field, but `pop` is only 4.5% of 55,701 tracks
  (rock 427, hiphop 1,016; dominated by ambient/electronic/chillout) and **~70%+ carry NC and/or ND
  clauses**, which restricts redistributing derived statistics. Dated, not pop, not clean.
- **MUSDB18** (4.68 GB; HQ 22.66 GB) — genuinely pop/rock (89 of 150 tracks) and the most
  representative of commercial music found, but **68% is marked "Restricted"**, not CC, and it
  carries **no release years at all**. Pop, not clean, not dated.

State this gap plainly rather than papering over it. **MUSDB18-HQ is still worth having for one
specific job:** it ships ground-truth separated stems, so it is the way to validate the Demucs
separation stage added on 2026-09-07 — used as a held-out internal validation set, never as a corpus
whose statistics get published. Musopen/IMSLP/MusicNet are all classical and irrelevant to the gap.

**Corpus QC is not optional — `scripts/corpus_qc.py`.** It measures where each stratum's extracted
melodies actually sit, and it immediately caught a defect I had already indexed: Nottingham ships a
`chords/` subdirectory of accompaniment-only files, and a `**/*.mid*` glob swept all of them in, so
**1,005 of 3,073 "melodies" were chord tracks** (32.7% below MIDI 55 against 0% for the folk strata).
The track scorer had correctly rated them −17.8; `melody()` simply accepted any finite score. Fixed
with `MIN_MELODY_SCORE`, which rejects a file when no track looks like a tune — a general guard, not
a Nottingham patch. Run the QC after adding any stratum: a high "likely bass" share means the counts
are over the wrong voice.

**Coverage is fixed; dating is not.** Adding Lakh took the corpus from folk-only to genuinely
pop-covering — a hook from a 2011 pop track that previously returned N=0 in every stratum now returns
N=237 in `lakh-clean` at the 100th percentile. But **only `mtc-fs-inst` carries years**, so four of
five strata can never support an M ("predates") count. Dating the pop side needs the `lmd_matched`
join to the Million Song Dataset, whose year field is sparse (~45%) and unaudited — audit it before
building "predates year X" claims on it. Verified
licence findings so far: POP909 MIT, Nottingham GPL-3.0, The Session **prohibits LLM use**,
Themefinder has no bulk export.

**Gate 3, first measurement (`scripts/rarity.py`):** at n=9 intervals, 75–79% of figures appear in
exactly one work, so the frequency distribution is heavily tailed. But figures shared across members
of the same tune family have the *same* median document frequency (2) as random figures, and a lower
mean (4.8 vs 6.5) — **rarity did not separate meaningful material from arbitrary windows** on this
test. Report as a null result, not as a failure of the index: the count is still the honest
denominator, but "rare therefore significant" does not follow.

## Caveats to carry forward

- **The Kjarkas → Lambada → On the Floor chain was never independently verified** in either
  research pass. Treat it as widely reported, not confirmed. The argument doesn't depend on
  it — the point is that such chains are in databases because humans put them there.
  *Update 2026-09-07:* MusicBrainz **does** record a `based on` edge from *On the Floor*
  (`0af83df7-71e6-4865-a44e-a6afd38d0da7`) directly to *Llorando se fue*
  (`0e681ae3-8df5-4979-b1e3-0c3c2d4b14f9`), with Gonzalo and Ulises Hermosa among the writer credits.
  This does **not** close the caveat — the relationship carries no citation in the API payload — but it
  upgrades the chain from "widely reported" to "present in the curated graph with corroborating credits."
  Wikidata records only Llorando se fue ↔ Lambada, with no P144 to On the Floor at all.
- **The Session** tune archive (ODbL) carries an explicit **prohibition on LLM use**. Do not index it.
- **Wikifonia is NOT public domain — do not use it, and do not repeat the PD claim.** Verified
  2026-09-08: it operated 2006–2013 under *paid licences from European performing-rights
  organisations* covering copyrighted commercial songs, and shut down precisely because those
  licences could not be renewed. Every mirror README found repeats a "public domain" claim that the
  shutdown history directly contradicts. The one reachable mirror (synthzone) returns 403 anyway.
  OpenEWLD is a better-faith filtered derivative, but its own PD determination is self-described as
  unverified — lower risk, not clean.
- **Hooktheory / TheoryTab (HTPD3, lead-sheet-dataset) — ToS prohibits it.** Hooktheory's terms
  explicitly ban third-party scraping, bulk download, text-and-data-mining and redistribution
  without a written data licence; the GitHub mirrors were built by ignoring that. Content-wise this
  is the ideal corpus (transcribed pop *hooks*), so the correct route is to ask Hooktheory for a
  licence, not to use a mirror. Same category as The Session.
- **Lakh MIDI's CC BY 4.0 covers Raffel's aggregation and metadata, not the songs.** The files are
  user-made transcriptions of copyrighted commercial recordings scraped from MIDI-sharing sites.
  Usable for local research and for publishing *statistics*; not a clearance to redistribute the
  melodies themselves.
- MetaMIDI and GigaMIDI are **access-gated with explicit non-redistribution terms** (GigaMIDI also
  CC BY-NC 4.0). Fine for internal research after the request form; not a base for a redistributable
  artifact. Zenodo returned 504 throughout the 2026-09-08 check, so MMD's record is unverified.
- **Themefinder / Barlow & Morgenstern** has no bulk export — confirms the "never established" entry.
- Essen's Zenodo release is CC BY-NC-SA 3.0 but derives from CCARH kern files with stricter terms.
  **Licence provenance is muddled**; fine for local research, unresolved for redistribution.
- Refuted claims (do not repeat as fact): SecondHandSongs `basedOn`/`derivedWorks` fields;
  its canonical "original performance" designation; its licensing terms and rate limits;
  Audible Magic's 99.99% identification and manipulation-robustness marketing claims;
  YourMT3's Slakh2100/ENST-Drums SOTA results. Refuted = unverifiable from the cited source,
  not proven false.
- Spotify's Basic Pitch README claims accuracy "competes with much larger" systems; the
  peer-reviewed paper says only "marginally below." Read the README as marketing.
- ByteCover's numbers are a 2021 floor, superseded by ByteCover2/3 and CoverHunter.
- The alignment/substitution evidence all comes from oral-transmission folk and chant
  repertoires. Extending it to recording-mediated commercial pop is an untested extrapolation.

## Never established (silence ≠ absence)

Pex, Sureel, Musical AI, BMAT, Matchtune, Rightsify, Believe/TuneCore, Spotify/Deezer
internals; melody-matching limits of Shazam/SoundHound/Aha Music; **whether WhoSampled offers
any API, licensed feed, or bulk access** (highest-leverage open question — it's the exact
asset the only working ancestry paper ran on); Peachnote, Musipedia, SIMSSA/CANTUS/DIAMM,
RISM, Barlow & Morgenstern, Essen Folksong; MERT/MULE/CLAP/DiscogsEffnet as standalone
embeddings; vector search at 100M-track scale; CREPE, pYIN, melodia, Deep Salience,
hFT-Transformer.

Also unmeasured anywhere in the literature: **how transcription error compounds into
downstream symbolic matching accuracy on commercial pop.** That sits at the front of any
audio-first pipeline and deserves an early spike.

## If we start building

*Superseded as a sequence by `unified-plan.md` — the transcription spike moved from step 2 to the
centre of the plan. Retained because the per-step technical guidance below still holds.*

Staged so each phase stands alone and the riskiest unknowns get tested first:

1. Seed the graph from MusicBrainz + Wikidata before touching audio; run Katz centrality.
   This reproduces the only working ancestry result and reveals how sparse the curated
   layer really is — the number that decides whether the product is viable.
2. Spike transcription: 50 known interpolation pairs through Basic Pitch and Omnizart,
   measure what melodic relationship survives. If little does, go embedding-only.
3. Retrieval via ByteCover-style embeddings at 128–256d into FAISS or pgvector.
4. Localize with BMM-Det. Don't use flat edit distance — weight by rhythmic function
   (final > stressed > unstressed > ornamental); substitutions cluster between neighbouring
   scale degrees.
5. Ship the prior-art index first.
6. Only then infer chains, with loud abstention.

## Delegation

Delegate any subtask that does not require extreme reasoning to a **Sonnet** subagent. Search,
fetching, corpus/landscape surveys, license checks, status checks, log and transcript digging,
and summarising known material are all Sonnet work.

Keep on the stronger model — or do it directly — when the task is:
- **direct coding**
- **code review**
- **crucial decision-making or planning**

Override this only when the user names a different model for a specific job.

This is reinforced by the project's own evidence: in the deep-research runs, Sonnet held up on
search, fetch and verification (80% confirm rate vs Opus's 88%) and failed only at synthesis.
Breadth to Sonnet, judgement to Opus.

## Environment gotchas

- **`grep` is a shell function** wrapping `ugrep --ignore-files`, which respects
  `.gitignore`. It will silently skip venvs, `node_modules`, build output, `.env` — and
  report zero matches while the string is plainly in the files. Use `command grep` whenever
  the answer needs to be trustworthy. This already caused one false "clean" result.
- Web search budget is **per-session and capped at 200 calls**; it was exhausted during the
  research. `WebFetch` still works when search doesn't. Raise with
  `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`.
- This lives in the WSL filesystem (`/home/cca/code/`), not under `/mnt/c`. Keep it there —
  the drvfs mount forces 777 permissions and is slow.

## How the research was done

Two `deep-research` workflow passes — 207 agents (104 + 103), 43 sources fetched, 25 claims
adversarially verified *per pass* (50 total), 8 killed (3 + 5). Pass 1 ran on Opus and produced
18 findings. Pass 2 ran on Sonnet for cost and came back noticeably thinner — 5 findings, with
the entire legal/musicological branch returning nothing. That gap was filled by fetching Yen and
the MCIR directly, and turned out to be the most valuable material in the report.

The full output is in `docs/research/`. It was never written to a file at the time — it lived only
inside the workflow run records under the Windows-side session store, and was recovered from
there on 2026-09-02.

Lesson for future passes — **it was synthesis that failed on Sonnet, not verification.** The
Sonnet verifier confirmed 20 of 25 claims (80%) against Opus's 22 of 25 (88%), and confirmed
four times more than it killed. The collapse was downstream: 20 confirmed claims went into
synthesis and 5 findings came out. So pin `synthesize` to Opus and leave search, fetch and
verify on Sonnet — that is where nearly all the token spend goes, and it held up fine. For a
branch that really matters, still fetch primary sources directly.
