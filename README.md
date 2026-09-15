# Hookline

An MP3 goes in. For each hook it finds, a count comes out: **how many indexed works contain that
figure, how many of them predate a reference date**, with an interval on both, reported per corpus
stratum and never pooled. It does not say who copied whom.

This is the unified MVP from [`docs/plans/unified-plan.md`](docs/plans/unified-plan.md) — the product
track and the research track built as one system, because the measurement the research track needs
and the confidence model the product needs are the same object.

## Run it

Everything runs from the repository root. Developed and tested on Python 3.12.

### 1. Install

```bash
pip install numpy soundfile imageio-ffmpeg mido
pip install demucs          # optional; pulls in torch
```

| Package | Needed for |
|---|---|
| `numpy` | Everything, including `stats` and the tests. |
| `soundfile` or `imageio-ffmpeg` | Decoding MP3 — either one will do. `imageio-ffmpeg` bundles its own ffmpeg, so no system install. With neither, only PCM WAV loads. |
| `mido` | The tests, and adding MIDI corpora. |
| `demucs` | Separating the vocal from a full mix. Without it `analyse` still runs on the raw mix and says so — which on commercial pop means tracking the bass (see *Real-mix failure* below). |

### 2. Get an index

The index is `data/hookline.db` (about 1.7 GB). It is gitignored, as are the corpora it is built from,
because several of their licences forbid redistributing the melodies. Check whether you have one:

```bash
python3 -m hookline.cli stats
```

If it lists all five strata, go to step 3. Otherwise build it — first the two folk corpora, which are
the MTCFeatures 1.1 release on [Zenodo](https://zenodo.org/records/3551003) (CC BY-NC-SA 3.0):

```bash
curl -L -o data/mtc.jsonl.gz   "https://zenodo.org/records/3551003/files/MTC-FS-INST-2.0_sequences-1.1.jsonl.gz?download=1"  # 61 MB
curl -L -o data/essen.jsonl.gz "https://zenodo.org/records/3551003/files/essen_sequences-1.1.jsonl.gz?download=1"            # 19 MB
python3 scripts/build_index.py 9000
```

`9000` caps the *lines read* from each file, not the works indexed: melodies under 12 notes are
dropped, which is how 9,000 lines became 8,986 and 8,460 works. The script defaults to 8,000, so pass
9000 to match the index as built.

Then the three MIDI corpora. `data/corpora/` is gitignored for this:

```bash
mkdir -p data/corpora
git clone https://github.com/music-x-lab/POP909-Dataset data/corpora/POP909-Dataset
git clone https://github.com/jukedeck/nottingham-dataset data/corpora/nottingham-dataset
curl -L http://hog.ee.columbia.edu/craffel/lmd/clean_midi.tar.gz | tar xz -C data/corpora   # 234 MB

python3 scripts/add_corpus.py pop909 data/corpora/POP909-Dataset/POP909 \
    --pattern "[0-9][0-9][0-9]/[0-9][0-9][0-9].mid"
python3 scripts/add_corpus.py lakh-clean data/corpora/clean_midi \
    --artist-from-parent --dedupe --max-notes 160
python3 scripts/add_corpus.py nottingham data/corpora/nottingham-dataset/MIDI \
    --tradition folk --pattern "melody/*.mid"
python3 scripts/corpus_qc.py      # after adding any stratum — see Corpus quality control
```

No build log was kept, so these flags were recovered from the index itself: Lakh's artists come from
the parent directory, no two of its works share a song, and 8,154 of them stop at exactly 160 notes.
The one deliberate difference is Nottingham's `--pattern` — see the known issue under *The index, as
built*.

Re-running any build step is safe: a work already in its stratum is skipped, so nothing is counted
twice. Before 2026-09-14 that was not true. Re-running `build_index.py` inserted every work again,
and this index carried 1,785 duplicate folk works — inflating every count they touched — until they
were removed that day.

### 3. Use it

```bash
python3 -m hookline.cli serve                                      # GUI at http://127.0.0.1:8765
python3 -m hookline.cli analyse song.mp3 --year 2011               # audio → a card per hook
python3 -m hookline.cli symbolic C5 A4 G4 F4 G4 A4 C5 --year 1900  # notes → one card
```

`--year` is the reference date for the M ("predates") count. `analyse` also takes `--stem`
(`auto`, the default, separates only when the mix looks bass-dominated; or `vocals`, `vocals+other`,
`none`), `--fmin` for the pitch floor in Hz, and `--json`. Every command takes `--db` to point at a
different index.

The GUI does the same in a browser: upload audio or type notes, set the reference year, stem and pitch
floor, and play each hook back against the song. Its demo button needs `data/demo/`, which is
gitignored; make it with the first command below. The second is optional too:

```bash
python3 scripts/make_demo.py      # data/demo/ — a real MTC melody, synthesised (needs data/mtc.jsonl.gz)
python3 scripts/seed_ledger.py    # data/ledger.db — live Wikidata + MusicBrainz queries; see The Ledger
```

### 4. Test

```bash
python3 tests/test_hookline.py    # 44 invariant checks; builds its own throwaway index
```

### 5. Reproduce the measured results

```bash
python3 scripts/evaluate.py 200     # known-item retrieval      → data/eval_results.json
python3 scripts/degradation.py 100  # the compounding curve     → data/degradation.json
python3 scripts/rarity.py           # gate 3                    → data/rarity_gate3.json
python3 scripts/corpus_qc.py        # voice per stratum         → data/corpus_qc.json
```

Each overwrites a tracked result file. All read the index; the first three also need `data/mtc.jsonl.gz`.

## What is actually built

| Module | What it does |
|---|---|
| `audio.py` | MP3/WAV/FLAC → mono float32. libsndfile, then a pip-installed static ffmpeg, then stdlib `wave`. No system ffmpeg needed. |
| `separate.py` | Demucs source separation to a lead stem. Optional: falls back to the raw mix and says so. |
| `mixture.py` | Controlled polyphonic mixtures (melody + bass + chords + drums) with ground truth, for measuring melody extraction. |
| `f0.py` | YIN pitch tracking that emits **ranked candidates with posteriors**, not one answer. Primary picked by YIN's period rule; subharmonic penalty on the rest. |
| `notes.py` | Frame candidates → note events, each keeping its alternatives. |
| `beats.py` | Spectral-flux onsets, tempo, beat grid, metric stress (final > downbeat > beat > offbeat). |
| `phrases.py` | Phrase segmentation and hook ranking by recurrence — no query to write. |
| `encode.py` | Five Themefinder-style encodings, n-grams n = 4–12. |
| `lattice.py` | Query expansion over readings. E[N] and Var[N] exact given the path distribution. |
| `index.py` | Stratified inverted index on SQLite. Counts never pooled; undated works never enter a "predates" figure. |
| `ledger.py` | Live Wikidata P144 + MusicBrainz work-rels, cached, with Katz centrality. |
| `verdict.py` | The abstention ladder. Three of the four verdicts name nobody. |
| `server.py` | Stdlib HTTP server and the GUI. |

## The index, as built

**30,434 works · 6,365,312 distinct figures · 17,682,330 postings** across five strata, counted and
reported separately, never pooled.

| Stratum | Works | Dated | Repertoire | Licence |
|---|---|---|---|---|
| `lakh-clean` | 10,011 | 0% | **Western commercial pop** | CC BY 4.0 on Raffel's *aggregation only*; the transcriptions are of copyrighted recordings |
| `mtc-fs-inst` | 8,986 | 100% | Dutch folk | CC BY-NC-SA 3.0 |
| `essen` | 8,460 | 0% | European folk | CC BY-NC-SA 3.0 on Zenodo, from stricter CCARH terms; **provenance muddled** |
| `nottingham` | 2,068 | 0% | British/Irish folk-dance | GPL-3.0 |
| `pop909` | 909 | 0% | Chinese popular music | MIT (annotations); compositions remain in copyright |

**Known issue — Nottingham is counted twice.** Found 2026-09-14 and not yet corrected. The stratum
was ingested with the default `**/*.mid*` glob, which takes each tune both from `MIDI/melody/` and
from the full arrangement beside it; 1,030 of its 1,034 tunes are stored twice with identical notes.
It really holds 1,034 works, not 2,068, so every Nottingham count is roughly doubled, and the totals
above include the 1,034 extra. The build command under *Run it* takes the melody files only.

The corpus now spans folk *and* commercial pop, which it did not before — a pop hook that previously
returned N=0 everywhere now returns real counts. What it still cannot do is date them: **only
`mtc-fs-inst` carries years**, so four of five strata contribute to N and can never support an M
("predates") figure. Getting dates for the pop side means the `lmd_matched` join to the Million Song
Dataset, whose year field is sparse and unaudited.

Adding a corpus is one command, and a corpus without a stated licence and provenance is refused:

```bash
python3 scripts/add_corpus.py pop909 <dir> --pattern "[0-9][0-9][0-9]/[0-9][0-9][0-9].mid"
python3 scripts/transcribe_corpus.py <name> <audio_dir>   # the audio route
```

`midi.py` picks the melodic line out of a multi-track arrangement by scoring each track (name
evidence, register, polyphony) and then forcing monophony with a skyline pass. Indexing the bass or
a pad as if it were the tune is the same failure the audio front end had, and it is scored rather
than guessed.

## Why there is no clean pop audio corpus

The plan's S2 stratum — pop melodies transcribed from audio we are licensed to hold — is blocked on
data, not on code (`scripts/transcribe_corpus.py` is ready). Verified 2026-09-08: **no public audio
corpus is simultaneously dated, pop-weighted and cleanly redistributable.** Each candidate fails a
different one of the three:

| Corpus | Size | Dated? | Pop? | Clean? |
|---|---|---|---|---|
| FMA small | 7.15 GiB | 64% album dates | **No** — its own paper says it "does not contain mainstream music" | Yes |
| MTG-Jamendo | 156–508 GB | Yes, explicit `RELEASEDATE` | **No** — `pop` is 4.5% of 55,701 tracks | **No** — ~70% carry NC/ND |
| MUSDB18 | 4.68 GB | **No** — no years at all | **Yes** — 89/150 pop/rock | **No** — 68% "Restricted", not CC |

MUSDB18 is still worth having for one job: it ships **ground-truth separated stems**, so it is how
the Demucs stage would be validated — as a held-out internal set, never as a corpus whose statistics
are published.

## Corpus quality control

`scripts/corpus_qc.py` reports where each stratum's melodies sit in pitch. It earned its place
immediately: Nottingham ships a `chords/` directory of accompaniment-only files, and the glob that
ingested it swept those in as melodies — **1,005 of 3,073 were chord tracks**, 32.7% of the stratum
sitting below MIDI 55 while every other corpus was at 0%. The track scorer had rated them −17.8;
`melody()` accepted any finite score. There is now a score floor, so a file with no melodic track is
rejected outright.

| Stratum | In melodic band | Likely bass |
|---|---|---|
| `mtc-fs-inst` | 100.0% | 0.0% |
| `essen` | 100.0% | 0.0% |
| `pop909` | 99.6% | 0.0% |
| `lakh-clean` | 96.0% | 3.2% |

A count is only as good as the voice it was taken from, so this check belongs beside any number the
index produces.

## Does rarity separate?

Gate 3, measured on the folk strata (`scripts/rarity.py`). At 9 notes in the interval encoding,
**75–79% of figures appear in exactly one work** — the distribution is heavily tailed, so most
figures genuinely are rare. Nottingham is the outlier at 19% singletons, its dance repertoire being
far more formulaic. *That reading is now suspect:* the stratum holds every tune twice (see *The
index, as built*), which by itself pushes singletons toward zero. Re-measure before relying on it.

But the separation test is close to null. Figures that recur across independent members of the same
tune family — musicologically meaningful material — have the **same median document frequency (2)**
as figures drawn at random, and a slightly *lower* mean (4.8 vs 6.5). On this evidence rarity does
not distinguish meaningful melodic material from an arbitrary window. The count remains an honest
denominator; "rare therefore significant" does not follow from it.

## Measured results

Ground truth is the Meertens **tune-family** assignment: melodies in one family are established
variants of each other, decided by musicologists and independent of any litigation record. This is
the evaluation the plan argues for, and it needs no court outcomes.

**Known-item retrieval, n = 200 queries**

| Condition | Self-retrieval | Family sibling |
|---|---|---|
| symbolic (ceiling) | 100.0% | 69.0% |
| audio, top-1 | 100.0% | 66.0% |
| audio, lattice | 100.0% | 66.0% |

**The compounding curve** — retrieval as the audio degrades (n = 100 per row):

| noise | vibrato | mean conf | top-1 self | lattice self | top-1 family | lattice family |
|---|---|---|---|---|---|---|
| 0.00 | 0¢ | 0.871 | 100% | 100% | 59% | 59% |
| 0.35 | 0¢ | 0.889 | 100% | 100% | 62% | 63% |
| 0.60 | 45¢ | 0.837 | 80% | 80% | 51% | 51% |
| 0.90 | 60¢ | 0.729 | **18%** | **23%** | **13%** | **19%** |

Three findings, and the second is the one worth arguing about:

1. **The dominant transcription error was segmentation, not pitch.** Before onset-based splitting,
   92% of melodies lost notes and 0% gained them; when the note count was right the pitches were
   100% exact. Consecutive notes at the same pitch were merging into one. Adding onset detection
   took exact pitch-sequence recovery from 3/40 to 38/40. **A pitch lattice cannot repair a
   segmentation error** — the n-gram window is already misaligned.
2. **The lattice buys nothing until transcription actually degrades, then it buys 5–6 points.**
   On clean audio the top-1 reading is already right, so carrying uncertainty is pure cost. At the
   worst condition it lifts self-retrieval 18% → 23% and family retrieval 13% → 19%. The design bet
   is therefore **untestable on clean synthetic audio** — which is a methodological result: gate 2
   has to run on real mixes or it answers nothing.
3. **Every number here is an upper bound.** Synthesised monophonic tone has no percussion, no
   competing instruments, no reverb. Basic Pitch reports 0.35 note-level F on real monophonic
   vocals; nothing here contradicts that or speaks to it.

## Real-mix failure, and the fix

The first test on a real commercial track (*On The Floor*, 266s MP3) ran end to end and produced
nothing useful. **Root cause: YIN is a monophonic pitch tracker and it was pointed at a full mix.**
Time-domain autocorrelation finds the strongest periodicity in the signal, which in commercial pop
is the bass — 94% of detected notes fell below C4, median MIDI 43.

Raising the pitch floor alone does not fix it. It reaches vocal register but the line fragments:
median inter-note gap 0.453s with 66 of 85 gaps beyond the rest threshold, yielding **zero**
figures of indexable length. The vocal is only intermittently the dominant periodicity.

The fix is separation *and* a register floor together:

| | notes | conf | median | %≥C4 | countable figures |
|---|---|---|---|---|---|
| raw mix @ 65 Hz | 179 | 0.65 | 43 (G2) | 6% | 8 — all bass |
| raw mix @ 220 Hz | 61 | 0.85 | 65 | 74% | **0** — fragmented |
| **vocals stem @ 150 Hz** | **140** | **0.70** | **60 (C4)** | **51%** | **7** |

Three things this settled:

- **Separation repairs the fragmentation that the register floor alone causes.** Neither change
  works without the other.
- **`vocals` alone beats `vocals+other`** on this track (median 59 vs 46): "other" readmits the
  synth bass.
- **Separation must not be unconditional.** On clean synthesised monophonic audio Demucs has no real
  timbre to work with and made transcription *worse*. `stem="auto"` probes the raw mix first and
  separates only when it looks bass-dominated (median MIDI < 55, or >70% of notes below C4).

A limitation this exposed in our own benchmark: `mixture.py` reproduces the bass-lock failure
faithfully (100% of notes below C4, median 48 against a true median of 72), but **it cannot validate
learned separation** — Demucs is trained on real recordings and does nothing useful with stacks of
synthetic sine tones. The synthetic benchmark is valid for DSP-level fixes only; learned components
have to be tested on real audio.

Still unchanged: N=0 in both strata, because they are folk collections and this is a 2011 pop track.
That is the denominator problem, not a transcription result.

## The Ledger

504 directed edges, 454 works, 264 fully dated, from live Wikidata + MusicBrainz queries — no bulk
dumps. Katz centrality tops out at *I Got Rhythm*, which is the right answer for a derivation graph.

**On the project's standing caveat:** MusicBrainz records a `based on` edge from *On the Floor*
directly to *Llorando se fue*, with Gonzalo and Ulises Hermosa in the work's writer credits. That
does not close the caveat — the relationship carries no citation in the API payload — but it moves
the chain from "widely reported" to "present in the curated graph with corroborating credits."

## What it will never output

A similarity percentage presented as a conclusion. An "X copied Y" claim derived from the model.
A named originator where the earliest matches are folk or undated. A count without its denominator
and its interval. These are enforced in the output schema and covered by tests, not left to prose.

## Licensing notes worth carrying

- **The Session** (Irish trad, ODbL) carries an explicit **prohibition on LLM use**. Excluded.
- **Themefinder / Barlow & Morgenstern** has no bulk export — confirms the project's "never
  established" list.
- Audio stack licences (Essentia AGPL, madmom patent notes) are **unaudited** and remain a P0 item.
