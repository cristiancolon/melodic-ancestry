# Melody plagiarism detection on real data — implementation plan

**Thesis.** Melody-plagiarism benchmarks built on litigation measure whether a pair was *sued*
rather than whether it *infringed*; the differences the field reports between systems are smaller
than the variance of its own threshold protocol; and the entire documented corpus of US music
copyright litigation is roughly two orders of magnitude too small to resolve them.

**Track.** This is the research/publication track. The product track remains the prior-art index
described in `melodic-ancestry-mvp.html`, which this plan does not supersede; the brief should
carry a note distinguishing the two (**A0.0**).

**Tone rule, binding on every draft.** Every claim about another group's work is an observation
against a cited artifact version, never an attribution of error to people. Every finding is
reported alongside the authors' response where one was received. These authors are plausible
reviewers.

---

## Claim 1 — The labels do not mean what an evaluation using them assumes

### 1.1 The construction

MCIC is an outcome-labelled corpus: **116 cases — 32 infringed, 66 denied, 18 settled** — shipping
232 melody-only hand-transcribed MIDI files and 232 PDF scores, drawn from MCIR, Lost in Music and
Yuan et al. (2023).

MelodySim's re-use of it is not an outcome task. Every row of its Table 4 is exactly **116
positives and 116 negatives** (TP+FN = 116 and TN+FP = 116 across all five rows). The positive
class is "this pair was litigated"; the negative set is constructed by a method the paper does not
document — it specifies negative construction only for its own test split ("546 positive pairs and
an equal number of negative pairs from different tracks to ensure class balance"). Its stated aim
for MCIC is to "detect songs that have been **labeled as potential plagiarism cases** in past
copyright disputes."

Two bounds, robust under every coding of the settled cases:

- **84 of 116 positives (72.4%)** — 66 denied plus 18 settled — are not judicial findings of
  infringement.
- MelodySim's 101 true positives contain at most 32 infringement findings, so **at least 69 of 101
  (68.3%)** are pairs where no infringement was established.

Its own related-work section states the split verbatim — "116 actual court cases (66 denied, 32
infringed, 18 settled)" — so the composition was known.

*Footnote, not headline:* an oracle emitting the court's finding scores 0.638 with settlements
coded negative (below every row in Table 4) but 0.716 with them coded positive (above every row).
The oracle framing is coding-dependent; the two bounds above are not.

### 1.2 A label defect in the reference dataset

Yuan et al. (2023) report PMI at 75% accuracy / AUC 0.7247 and Musly at 68% / AUC 0.66 on 40
cases with a stated composition of 18 infringement / 22 non-infringement. **Both shipped ROC input
files contain 19 positives / 21 negatives.** Re-running the paper's own procedure:

| File | As shipped | Row 15 flipped to 0 | Paper reports |
|---|---|---|---|
| `PMI/ROC.csv` | 19/21 -> 72.5%, AUC 0.6742 | 18/22 -> **75.0%, AUC 0.7247** | 75%, AUC 0.7247 |
| `MuslyTest/ROC_Musly.csv` | 19/21 -> 65.0%, AUC 0.6165 | 18/22 -> **67.5%, AUC 0.6616** | 68%, AUC 0.66 |

Flipping the same single row reproduces both published results exactly. Row 15 is case 14 —
*Vargas & Roberts, "Bust Dat Groove (Without Ride)"* vs *Transeau, "Advertisement for Celebrex"* —
a drum groove, which is why its PMI value is 0.

**The court found no infringement.** *Vargas v. Transeau*, 514 F. Supp. 2d 439 (S.D.N.Y. 2007):
"Defendants move for summary judgment, contending that Plaintiffs cannot demonstrate that Transeau
had access to BDG. For the reasons set forth below, Defendants' motion is granted." Affirmed sub
nom. *Vargas v. Pfizer Inc.*, 352 F. App'x 458 (2d Cir., 5 Nov 2009).

So the **released data files are in error and the published paper is correct**. Report it as label
instability, not as a failure to reproduce: one label in forty moves the headline 2.5 points and
AUC 0.05, which is itself a statement about the power of n=40.

### 1.3 Novelty

No citing work states this critique. Citation counts differ by index — MelodySim: 7 (Semantic
Scholar), 3 (Google Scholar), 1 (OpenAlex); MCIC: 3 / 5 / 0. The closest prior instance is
Batlle-Roca, Melo & Serra (HCMIR25, ISMIR 2025 satellite), who deliberately selected a **balanced
9 denied / 9 infringed subset** "balancing legal outcomes" — an implicit methodological
acknowledgment, never argued as a point.

**Open novelty risk:** Muñoz Melo, UPF MSc thesis 2025 (`hdl.handle.net/10230/72081`), the extended
version of that workshop paper, is behind a WAF and unread. Check before writing.

---

## Claim 2 — The comparisons do not support the rankings

### 2.1 Threshold protocol dominates model choice

Same model, same data: MelodySim's 20-fold CV variant scores 156/232 = 0.6724; its 2-fold variant
scores 142/232 = 0.6121. **6.03 points from threshold selection alone**, against a
MelodySim-vs-DTW-CQT gap of **1.29 points** — a ratio of 4.7x.

*To verify and state:* this holds only if the checkpoint is frozen across both variants. If the CV
involves refitting, the 6.03 also carries a training-set-size effect.

### 2.2 The in-domain headline shares the dependency

The song-level threshold was also fitted on MCIC: "We determine the aggregation threshold with 20
fold-cross cross-validation **on MCIC**, finding that 40% segment overlap at 0.99 confidence level
optimally distinguishes similar pairs." That threshold produces the flagship 0.98 in Table 3 — so
the in-domain headline depends on a threshold fitted on the other dataset. The aggregation rule is
self-described as "heuristic and may not generalize."

### 2.3 The bias runs toward the baselines

The DTW baselines "apply an adaptive threshold to maximize F1-score" — direct in-sample
optimisation — while MelodySim used out-of-fold CV. **The baselines received the more generous
rule, and the learned model still did not win.** Their printed accuracies therefore sit at an
F1-optimal operating point, making that column apples-to-oranges in both directions.

### 2.4 The same effect, measured by the baseline's own authors

PMI's 75% came from ROC analysis on the same 40 cases. Yuan et al. report, in a footnote, that
cutoffs derived from other datasets give **68% (27/40)** using Savage et al. (2018) and **70%
(28/40)** using Yuan et al. (2020) — a directly measured 5–7 point threshold-optimism effect.

### 2.5 Most published comparisons are unresolvable

Of the ten pairwise comparisons in Table 4, only **three** are guaranteed non-significant under
every discordance pattern (bound: 2*0.5^d > 0.05 implies d <= 5 — Chroma-CQT d=1, Chroma-MelodySim
d=2, CQT-MelodySim d=3). The other seven are unresolvable from published data, not shown
non-significant: exact McNemar requires paired per-item decisions and only marginal confusion
matrices are published. **MelodySim reports no confidence interval, p-value, bootstrap or McNemar
anywhere**; its only "95%" is a listening-study MOS.

### 2.6 One unreconciled cell

DTW-CQT's printed accuracy 0.71 matches neither its F1 (0.7203) nor the accuracy implied by its own
matrix (159/232 = 0.6853). Report this separately from DTW-Chroma, whose printed 0.69 is exactly
its own F1 (0.6917) — a column slip, not a second computational error.

One further note: DTW-CQT's in-domain AUC is 0.01 (Table 3, the synthetic split); a sign-flipped
distance would give 0.99. Flag the tension — a globally flipped distance should also score worse
than chance on MCIC, yet CQT is the strongest row — without claiming it is "the best system."

### 2.7 Dev/test contamination

`music-copyright-expanded` is "all 40 MCIR cases with final decisions available as of October
2021." MCIC evaluates on "N=39 cases (subset from Yuan 2020/2023, excluding Vargas v. Pfizer)" and
prefers Yuan's transcriptions where available. **39 of the 40 sit inside MCIC**; Vargas is absent
from MCIC's 116 files, confirming the exclusion structurally.

---

## Claim 3 — No corpus of this kind can resolve them

Effective n for balanced accuracy at 32/66 is **86.2** = 4/(1/32 + 1/66); SE ~ **0.043–0.054**;
95% CI half-width ~ **+/-0.084–0.106**. This applies to the proposed outcome-labelled evaluation,
not to Table 4 (n=232, balanced).

Minimum detectable effect, exact McNemar, 80% power, alpha = 0.05 two-sided:

| n | pi_d=0.1 | 0.2 | 0.3 | 0.4 |
|---|---|---|---|---|
| 232 (Table 4's n) | 5.8 | 8.2 | 10.0 | 11.6 |
| 98 | 8.8 | 12.5 | 15.3 | 17.7 |
| 40 | 10.0 | 19.2 | 23.6 | 27.2 |

**Match n to claim.** On the Yuan 40, significantly beating PMI requires **>=90% accuracy** (36/40)
against its in-sample 75%, or **82.5–85%** (33–34/40) against the honest out-of-sample 68–70%; on
AUC, **~0.90 at r = 0.7** (~0.95 at r = 0.5). Note 36/40 is a floor attainable only if discordance
is wholly one-directional.

### The power envelope

Decided cases required to detect an improvement over a ~70% baseline (exact McNemar, 80% power,
alpha = 0.05), with pi_d sensitivity:

| Effect | pi_d=0.10 | 0.25 | 0.40 |
|---|---|---|---|
| 20 points | *(delta >= pi_d, invalid)* | 47 *(edge of validity)* | 88 |
| 10 points | ~90 | **194** | ~309 |
| 5 points | ~330 | **783** | ~1,250 |
| **1.29 points** *(the actual reported difference)* | **~2,275** | **~11,600** | **~18,500** |

**MCIR — the entire documented corpus of US music copyright litigation — holds 354 cases** (counted
across all fourteen decade index pages, September 2026). Yuan et al. record 301 in October 2021 and
315 in January 2023, giving an accrual rate of 11.2/yr and 10.6/yr across the two intervals
independently: **~11 cases per year**.

With every documented case transcribed, the minimum detectable effect is **7.4 points**; restricted
to decided cases (~266), **8.5 points**. The difference the field actually reports between the best
learned system and the best DTW baseline is **1.29 points**, requiring **~11,600 decided cases** —
**roughly a thousand years of accrual**.

Report the envelope as a band. pi_d = 0.25 is a convention, the model degenerates when
delta >= pi_d, and the conclusion is robust across the whole pi_d range only at the 1.29-point row.
Anchor there. The envelope is computed for paired *accuracy* comparisons, the statistic in which
the field's claims are stated; AUC comparisons do not materially improve the picture at these n.

---

## Data

### Splits

| Split | Cases | Composition |
|---|---|---|
| Development — MCIC minus Yuan | 77 | 14 infringed / 45 denied / 18 settled |
| Test — Yuan 40 | 40 | 18 infringed / 22 non-infringed |

**Labelled development data is 59 cases, 14 of them positive.** MCIC transcribes 116 but analyses
108, excluding settlements lacking payment records — state which number every claim uses.

### MCIC MIDI structure (measured across all 232 files)

| Property | Value |
|---|---|
| Files with a `time_signature` meta-event | 232 / 232 (100%) |
| Meters | 4/4 x213, 3/4 x10, 6/8 x7, 2/4 x1, 12/8 x1 |
| Contiguous transitions (`note_off` == next `note_on`) | 97.34% of 14,065 |
| Gaps (rests surviving) | 374 (2.66%) |
| Files containing polyphony | 4 / 232 |
| Notes per file | min 6, median 54, max 175 |

Meter is present in every file and is **not uniformly 4/4** — any analysis assuming 4/4 is wrong on
18 files. Because rests were removed in ~97% of transitions, cumulative onset time no longer equals
score position, so barline alignment remains unreliable despite the time signature. Savage's
*stressed* / *unstressed* levels are therefore not recoverable from the MIDI alone; only
phrase-final is approximable from long IOI. Recovering meter properly requires OMR over the 232
PDFs, which is real cost.

### Licensing

- **MCIC has no LICENSE file.** The CC-BY notice belongs to the ISMIR paper, not the dataset.
- **The Yuan repository has no LICENSE file either** — and it is the test set. Its README carries
  the article's CC-BY 4.0 notice; audio excerpts are "provided under fair use," with anything
  beyond requiring direct negotiation.
- MelodySim's checkpoint is declared Apache-2.0 while embedding **CC-BY-NC-4.0 MERT weights**, with
  the model card silent on the conflict. NC constrains redistribution and commercial use, not local
  research inference.
- Da-TACOS is CC BY-NC-SA and ships no audio; SHS100K is YouTube metadata requiring a crawl;
  Covers80 is 80 pairs; Sample100 is metadata-only, GPL-3.0, audio by request.

### Prior work to position against

- **Müllensiefen & Pendzich (2009)**, *Musicae Scientiae* 13(1_suppl):257–295 — 90% (18/20) on 20
  MCIR cases, weighting pitch-interval profiles by **rarity against 14,063 pop songs**.
- **Malandrino et al. (2022)**, *Data Mining and Knowledge Discovery* 36(4):1301–1334 — reportedly
  164 MCIR cases at 88–90%. *This description is second-hand, from Yuan et al.'s summary; the
  Springer full text is bot-walled and unverified. Obtain it before citing the numbers.*
- **Yuan et al. (2023)** already publish the ground-truth-reliability argument — "only the most
  ambiguous and controversial cases... make it into the MCIR, limiting its ability to provide a
  balanced and reliable ground-truth sample... the 'ground-truth' data may themselves have limited
  reliability (cf. Flexer & Grill, 2016)" — and already propose the training-data fix: "leveraging
  existing cover song datasets, and/or experimentally manipulating songs."
- **MelodySim** already attributes its own gap to synthetic augmentation: "the performance gap
  between MelodySim (0.98 F1) and MCIC (0.73 F1) reflects the controlled nature of synthetic
  augmentations."

**What remains novel:** the label defect and its direction; the 116/116 construction used with the
outcome split known; the quantified threshold dominance; the absence of significance testing and
the three-of-ten bound; the 39-of-40 contamination; and the power envelope — the selection-bias
argument exists qualitatively, but the arithmetic does not.

---

## Plan of work

### A0 — Prerequisites (week 1)

| | Task |
|---|---|
| **A0.0** | Add the two-track note to `melodic-ancestry-mvp.html`. |
| **A0.1** | **Pre-registration**: one primary endpoint, one dataset, one metric, one decision rule; everything else labelled secondary or exploratory. Tagged **before A1**. |
| **A0.2** | **Artifact freeze, before any outreach.** Record commit SHA / DOI / retrieval timestamp for MCIC, the Yuan repository (`PMI/ROC.csv` and `MuslyTest/ROC_Musly.csv` specifically) and MelodySim's checkpoint; archive to Software Heritage or Zenodo; cite versions, not repositories. |
| **A0.3** | **Author contact** (MelodySim, MCIC, Yuan): request per-item predictions — **A1 is not executable without them**; resolve MCIC's audio-rendering method and MelodySim's MCIC negative construction; raise the Vargas labels and the DTW-CQT cell. *If no per-item predictions by end of week 3, A1 ships bounds-only and the request is documented.* |
| **A0.4** | **Licence resolution.** Separate "may we run it locally" (yes) from "may we redistribute weights or derivatives" (the real question). Fold into A0.3. |
| **A0.5** | **Novelty close-out.** Read the Muñoz Melo UPF thesis; obtain Malandrino et al. (2022) full text; obtain Howard (2025), IJDSA (paywalled, `10.1007/s41060-025-00992-9`). |

### Stage A-paper — no GPU, no audio (weeks 2–5)

- **A1. Task-identity and significance analysis.** The 116/116 construction; the 84/116 and >=69/101
  bounds; the three-of-ten bound and the seven unresolvable comparisons; the threshold-protocol
  ratio; the in-domain threshold dependency; the unreconciled DTW-CQT cell.
- **A2. Contamination audit.** Case-level intersection across MCIC (116), Yuan (40), BMM-Det's 29
  real pairs and SMP (72 pairs / 175 segment-pairs), on party names and work titles.
- **A3. Label-validity analysis.** Stratify by MCIC's `Parts` column and report the melody-only
  stratum as primary, with its MDE cost — stratifying to ~49 cases raises the MDE to ~19.5 points,
  which is a finding, not an oversight. Code denial grounds (access / unprotectable / de minimis /
  procedural) **from the court opinions via MCIR and CourtListener**, not from MCIC's "Summary of
  Judgment Grounds" column, which is generated by a ChatGPT-based tool. Denominator: the 98 decided
  cases. Two coders, report kappa. **Budget 2–4 person-weeks.**
- **A4. Baseline contamination check.** Join Slakh2100 -> Lakh MIDI -> MSD titles against MCIC's 232
  works; MelodySim trains on Slakh2100.
- **A5. Power envelope.** Claim 3's tables, the corpus ceiling and accrual rate, and a
  recommendation for what to measure instead: threshold-free metrics with CIs, and rarity /
  prior-art counts, which are symmetric and not outcome-dependent. **Co-primary contribution.**
- **A6. Label-defect analysis.** The frozen ROC files, the one-label sensitivity across both
  algorithms, the Vargas disposition, and the corrected human estimands (51 participants across
  conditions; full-audio n=28, mean 57.95%, max 77.50%; melody-only n=23, mean 57.50%, max 72.50%;
  lyrics-only n=23, mean 51.53%).

### Stage A-compute — GPU and audio (weeks 6–9)

- **A7. Threshold sweep** of the released MelodySim checkpoint and each DTW baseline over both label
  schemes; report best achievable balanced accuracy, separating calibration from representation.
- **A8. Honest re-baselining** under one pre-registered protocol — identical inputs, identical
  threshold rule (nested CV), identical folds, threshold-free primary metric. **Label schemes:**
  primary = adjudicated (32 infringed / 66 denied, settlements excluded, n=98); secondary =
  litigated-vs-constructed, reproducing MelodySim's construction for a like-for-like comparison,
  with the negative construction pre-registered in A0.1. **Threshold derivation runs on
  MCIC-minus-Yuan only.** Any run touching the Yuan 40 is a reported baseline characterisation, not
  model development, and Stage B's hashed pre-commitment is made before it. Under the adjudicated
  scheme on dev only, positives = 14.
- **A9. Rendering-fairness control.** Render MCIC's MIDI to audio, transcribe back with Basic Pitch
  and Omnizart, run the symbolic scorer on the recovered transcription. **A control for A8, not a
  headline result** — on clean synthesised monophonic input the round trip is far easier than on
  real mixes (Basic Pitch's note-level F is 0.35 on monophonic vocals, 0.65 on solo guitar, with no
  published clean-synthesis evaluation), and it does not isolate transcription error on commercial
  audio, which MCIC does not ship.

**Gate A.** Under an honest, uniformly-thresholded protocol, does any published system separate
from any other at p < 0.05?
*No* (expected) -> that is the paper, with A5 as its constructive half; Stage B optional.
*Yes* -> there is a real ranking, and Stage B has a target.

### Stage B — modelling (weeks 10–24). Contingent on Gate A.

- **B1. Training distribution.** No source ships symbolic melody at scale, and a cover preserves the
  melody while varying the arrangement — the same invariance axis as MelodySim's augmentations, only
  with human rather than synthetic variation. If real borrowing does the inverse, covers fail for
  the same reason. **Gate 2 must measure the axis, not the magnitude:** do covers vary melody while
  holding arrangement fixed, or the reverse, and what fraction of the work is the matched fragment?
  Options: fragment-grafted positives; Sample100 (76/68 pairs, metadata only); Meertens
  MTC-FS-INST (18,618 symbolic folk melodies with tune-family labels, CC BY-NC-SA 3.0, with a
  documented folk-to-pop extrapolation risk); or accepting the audio pipeline.
- **B2. Controlled single-variable test.** Hold architecture and modality fixed, swap training data:
  retrain MelodySim's released architecture on the chosen positives plus mined hard negatives. This
  re-imports the audio pipeline and the NC MERT stack — budget it or drop the claim.
- **B3. Alignment model.** Constrained by the MIDI structure above. Estimate any substitution matrix
  on a proxy corpus, never on MCIC. Flat-edit-distance ablation required; treat rhythm-function
  weighting as a hypothesis under test, not an imported result.
- **B4. Held-out evaluation.** One scoring run on the Yuan 40, hashed predictions committed first.
  Primary comparison against PMI's out-of-sample 68–70% (33–34/40); the 90% figure is the
  comparison against the in-sample 75% and must be labelled as such.

---

## Success criteria and statistics

| Level | Criterion |
|---|---|
| **Primary** | The three-claim paper: label semantics, comparison validity, and the power envelope. Independent of any model working. |
| **Secondary** | Honest re-baselining under one protocol, threshold-free, with CIs and explicit bounds where per-item data is unavailable. |
| **Tertiary** | Any model result, with its CI and an explicit statement that the required effect is not plausibly reachable at these n. |

Exact McNemar on discordant pairs for paired accuracy; paired permutation for balanced accuracy
(McNemar does not apply to a balanced metric); cluster-robust or case-level resampling, because the
232 decisions reuse the same works and are not independent. Bootstrap CIs descriptive, not the
test. State alpha, sidedness and the multiplicity correction. Effective n (86.2) and discordant-pair
count are different quantities governing different tests — say which is which.

---

## Venue

- **TISMIR special collection, "Open Music Data for Music Processing Research" — deadline
  1 December 2026.** Guest editors Balke, Fuentes, Jeong, Müller. The call names benchmarking,
  reproducibility, dataset curation, and "critical reflections on bias, diversity, cultural
  representation, copyright, licensing, and ethics in music data practices." **Primary target.**
- **ISMIR 2026 Late-Breaking Demo — deadline 25 September 2026**, capped at 75 posters, rolling
  review. Carries Claims 1 and 3 only; both require no code. (Abu Dhabi, 8–12 November 2026; the
  main track closed 27 April 2026. ISMIR 2027 is London, 12–16 September 2027, CFP not yet posted.)
- TISMIR has six article categories and no reproducibility category, so this enters as a **Research
  Article** — 36% acceptance (27 of 90 in 2025), mean 247 days to publication. **Precedent exists:**
  Six, Bressan & Leman, "A Case for Reproducibility in MIR: Replication of 'A Highly Robust Audio
  Fingerprinting System'", TISMIR, DOI 10.5334/tismir.4 — a replication-and-critique published as an
  ordinary Research Article.

**Effort.** A0: week 1. A-paper: weeks 2–5. A-compute: weeks 6–9. Stage A total **9 weeks**; Stage B
weeks 10–24. A3 alone is 2–4 person-weeks, so either name a second full-time person for A-paper or
move A3 to the TISMIR-only track and out of LBD scope.

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Required effect (82.5–85%, or AUC ~0.90) unreachable | **Critical** | Stage A is the deliverable; model claims tertiary |
| Muñoz Melo thesis anticipates the critique | **High** | A0.5, before writing |
| Authors issue a corrigendum | **High** | A0.2 freeze first; Claims 1 and 3 survive one |
| A1 not executable without per-item predictions | **High** | A0.3 with a week-3 deadline; bounds-only fallback |
| Dev/test contamination (39 of 40) | **High** | A2; disjoint split defined; 14 dev positives stated |
| MCIC and Yuan both unlicensed; checkpoint licence conflict | **High** | A0.4; publish labels keyed to File IDs from public records only |
| A3 exceeds budget | **High** | Specified denominator and codebook; movable to TISMIR-only |
| Covers vary the wrong axis | **High** | Axis-aware Gate 2 before any Stage B spend |
| Malandrino's numbers unverified | Medium | A0.5; do not cite until read |
| Stratification cuts n to ~49 | Medium | Report as a finding: validity and power trade off |
| Pair clustering violates independence | Medium | Cluster-robust or case-level permutation |
| SHS100K link rot | Medium / contingent | Only bites in Stage B; resolved by the B1 decision |

---

## Open items

1. Muñoz Melo, UPF MSc thesis 2025 (`hdl.handle.net/10230/72081`) — WAF-blocked; the last novelty check.
2. Malandrino et al. (2022) full text — Springer bot-walled; the 164/50/88–90% figures are second-hand.
3. Howard (2025), IJDSA `10.1007/s41060-025-00992-9` — fully paywalled; cites both MelodySim and MCIC.
4. MelodySim's MCIC negative construction and audio rendering — undocumented; A0.3.
5. Whether MelodySim's checkpoint is frozen across the 20-fold and 2-fold variants — affects section 2.1.
