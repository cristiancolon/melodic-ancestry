# Pass 2 — gap-fill (Sonnet-pinned, 103 agents, 11.1 min)
runId `wf_3307eee1-beb` · status completed · 3,960,280 tokens · 740 tool calls
## Question
GAP-FILL pass on melodic provenance tracing. A prior research pass already covered cover-song embeddings (ByteCover/CoverHunter), MelodySim, BMM-Det, query-by-humming, Savage et al. folk-melody Needleman-Wunsch alignment, Genome of Melody chant phylogenetics, and Bryan & Wang's WhoSampled Katz-centrality influence network — DO NOT re-research those. Research ONLY these uncovered areas, prioritizing concrete named systems, APIs, schemas, pricing/access terms, repos, and honest statements of limits: (1) COMMERCIAL/PRODUCTION SYSTEMS: what Pex, Audible Magic, ACRCloud, Musical AI, Sureel, Rightsify/Sound Sample Detection, Matchtune, BMAT, Believe/TuneCore's plagiarism screening, and platform-internal work at Spotify/Deezer actually detect — do any go beyond exact-recording fingerprinting to melody/composition-level or interpolation matching, do any output multi-hop derivation chains, and what do they publish about accuracy? Also the melody-matching limits of Shazam, SoundHound, Aha Music, and whether any consumer app does query-by-humming against a full commercial catalog (Google Hum to Search) and how it works. (2) KNOWLEDGE-BASE / GRAPH LAYER: the actual data models and API access terms for MusicBrainz work-to-work relationship types (covers, "is based on", medley, sampled), Discogs, Wikidata music properties, WhoSampled (is there any API or licensed feed? terms of use? bulk access?), SecondHandSongs API (what its Work/Performance resources genuinely expose — a prior pass could NOT confirm basedOn/derivedWorks fields, so establish what IS documented), and any open dataset of sample/interpolation relationships suitable for training or evaluation. (3) SYMBOLIC MELODY RETRIEVAL INFRASTRUCTURE: Meertens Tune Collections / Dutch Song Database (MTC-FS/MTC-ANN, tune family annotations, van Kranenburg's work), Peachnote, Themefinder, Musipedia/Melodyhound (Parsons code contour search), SIMSSA/CANTUS/DIAMM, RISM incipit search, Barlow & Morgenstern's Dictionary of Musical Themes, and the "Musical Memes"/MeloSol/Essen Folksong Collection corpora — what is downloadable, how large, what licence. (4) FRONT-END TRANSCRIPTION AND MELODY EXTRACTION as of 2025-2026: Spotify basic-pitch, Google MT3/ISMIR transcription models, melodia/vamp, CREPE, pYIN, Omnizart, and newer neural predominant-melody / vocal-melody extractors (e.g. MedleyDB-trained, Deep Salience, hFT-Transformer, YourMT3) — reported accuracy on polyphonic commercial pop, and known error modes that would corrupt downstream symbolic matching. Also modern audio embeddings usable off-the-shelf: MERT, MULE, CLAP/LAION-CLAP, DiscogsEffnet/Essentia models, and vector-search practicalities (FAISS/HNSW/pgvector) at 100M-track scale. (5) LEGAL AND MUSICOLOGICAL CAVEATS: forensic musicology expert-witness practice (who does it, what methods are admissible), the "substantial similarity" and "extrinsic/intrinsic" tests, scenes-a-faire / common melodic archetypes and the Katy Perry Dark Horse and Blurred Lines and Stairway to Heaven outcomes as they bear on automated similarity scoring, the Music Copyright Infringement Resource (GWU/Columbia) as a dataset, public-domain and folk material with no single originator, and documented cases like Los Kjarkas v Kaoma "Lambada" and how interpolation licensing is actually credited in the modern era. Report honestly what does not exist.
## Summary
This gap-fill pass confirms that outside the academic systems already covered, the melodic-provenance landscape splits into three verified layers and two largely undocumented ones. Commercial products that go beyond exact-recording fingerprinting are narrow and modest: ACRCloud sells a separate "Humming Recognition" product (~1M songs, no published accuracy) and a distinct "Cover Song Identification" line, while Google's Hum to Search converts hummed audio into a timbre-stripped melodic sequence but matches against only "thousands" of songs — explicitly not a full commercial catalog — and Audible Magic remains a pure exact-recording fingerprinter with no melody/composition/interpolation matching or derivation-chain output. The knowledge-graph layer has real but limited schema support: MusicBrainz documents "Based on" and "Medley" work-to-work relationship types (behind a 1 req/sec API rate limit), Wikidata's P144/P4969 pair encodes generic derivative-work edges (though Wikidata itself flags P144 as inappropriate for music videos/audio tracks), and SecondHandSongs' API is documented as offering only search and object-retrieval — no dedicated derivation-chain endpoint could be confirmed. Symbolic melody infrastructure (MTC-ANN's 360 melodies, MTC-FS-INST's ~18,000 melodies, Themefinder's five-notation classical/folk search engine) and open-source transcription front-ends (Spotify's Basic Pitch, YourMT3+, JOSS-published Omnizart) are well-documented and usable today, though Basic Pitch's "competes with larger systems" accuracy claim is a vendor self-report only partially echoed by its own peer-reviewed paper. Critically, most of the requested scope — other commercial vendors (Pex, Sureel, Musical AI, BMAT, Matchtune, Rightsify, Believe/TuneCore, Spotify/Deezer internals), Shazam/SoundHound/Aha Music melody-matching limits, WhoSampled/Discogs API terms, modern audio embeddings (MERT, MULE, CLAP, DiscogsEffnet) and vector-search practicalities, most named symbolic corpora (Peachnote, Musipedia, SIMSSA/CANTUS/DIAMM, RISM, Barlow & Morgenstern, Essen Folksong), additional transcription models (CREPE, pYIN, melodia, Deep Salience, hFT-Transformer), and the entire legal/musicological caveats category (forensic-musicology practice, substantial-similarity tests, Dark Horse/Blurred Lines/Stairway to Heaven, MCIR, Lambada) — returned no claims that survived adversarial verification in this pass.
## Stats
```
{
  "angles": 5,
  "sourcesFetched": 21,
  "claimsExtracted": 76,
  "claimsVerified": 25,
  "confirmed": 20,
  "killed": 5,
  "unverified": 0,
  "afterSynthesis": 5,
  "urlDupes": 0,
  "budgetDropped": 7,
  "agentCalls": 103
}
```
## Findings (5)

### 1. Commercial melody-adjacent products exist alongside pure fingerprinting, but are narrow in catalog size and undisclosed in accuracy; none publish evidence of multi-hop derivation-chain output. ACRCloud offers a dedicated 'Humming Recognition' product (~1M songs, no published accuracy) and a separately marketed 'Cover Song Identification' line, distinct from its exact-fingerprint recognition API. Google's Hum to Search converts hummed/whistled/sung audio into a numerical melody sequence (stripping instrumentation and vocal timbre) but matches against only 'thousands' of songs, not a full commercial catalog. Audible Magic's public technology page describes only exact-recording perceptual fingerprinting robust to pitch/tempo/rate distortion of the SAME registered asset — it makes no claim of melody-level, composition-level, or interpolation matching, nor of any derivation-chain output.
- **confidence**: high
- **vote**: 3-0 / 3-0 / 3-0 / 3-0
- **sources**: ['https://www.acrcloud.com/cover-song-recognition/', 'https://www.acrcloud.com/humming-recognition/', 'https://blog.google/products/search/hum-to-search/', 'https://www.audiblemagic.com/technology/']
- **evidence**: Direct primary-source fetches confirm ACRCloud markets Humming Recognition and Cover Song Identification as separate named products from its core fingerprint API; Google's own blog states the melody-sequence mechanism and the 'thousands of songs' catalog scale verbatim, explicitly smaller than the 'millions' cited for its own fingerprint-based SoundSearch; Audible Magic's technology page frames all robustness claims around distorted copies of the same registered recording and contains no mention of melody/composition/interpolation/derivation-chain functionality.

### 2. Knowledge-graph schemas for musical derivation exist and are documented, but are general-purpose and access-constrained rather than purpose-built for melodic provenance. MusicBrainz defines 'Based on' (looser than arrangement/revision) and 'Medley' work-to-work relationship types, exposes them via work-rels/work-level-rels API includes, but enforces a hard 1 request/second client rate limit for live-API bulk crawling. Wikidata's P144 ('based on') / P4969 ('derivative work') inverse pair is a general item-datatype property for derivation graphs, but Wikidata's own constraints explicitly discourage its use for music videos and audio tracks, recommending P2550 ('recording or performance of') and P9810 ('remix of') instead. SecondHandSongs' documented API surface covers only search and object-retrieval (Artist/Performance/Work/Release/Label) with no dedicated derivation-chain/basedOn traversal endpoint found in its documented functionality.
- **confidence**: high
- **vote**: 3-0 / 3-0 / 2-1 / 3-0 / 3-0 / 3-0 / 2-1
- **sources**: ['https://musicbrainz.org/relationships/work-work', 'https://musicbrainz.org/doc/MusicBrainz_API', 'https://www.wikidata.org/wiki/Property:P144', 'https://secondhandsongs.com/page/API']
- **evidence**: MusicBrainz's own relationship-type and API docs confirm the 'Based on'/'Medley' definitions, the work-rels/work-level-rels includes, and the verbatim 1-call-per-second enforcement language. Wikidata's live property pages and raw entity-constraint JSON confirm P144/P4969 as inverses and confirm explicit conflict constraints naming music-video and audio-track instance types with recommended alternative properties. An archived (Wayback, since the live site is Cloudflare-gated) snapshot of SHS's API and Functionality pages lists exactly two functions (search, retrieve) and no third/derivation endpoint; the separate 'SHS Data Types' schema page that would show Work-object fields could not be retrieved, so it cannot be ruled out that basedOn-type fields exist within a standard Work response even though no dedicated traversal endpoint does.

### 3. Symbolic (non-audio) melody corpora and multi-notation search infrastructure for classical/folk repertoire are documented, downloadable, and vary in scale by orders of magnitude. The Meertens Tune Collections include MTC-ANN-2.0.1 (360 richly annotated Dutch melodies, a small benchmark set) and MTC-FS-INST-2.0 (~18,000 Dutch folk melodies, a much larger corpus). Themefinder, sponsored by CCARH, offers five distinct melodic search encodings — absolute pitch, interval, scale-degree, gross contour, and refined contour — for querying a classical/folksong/Renaissance database.
- **confidence**: high
- **vote**: 3-0 / 3-0 / 3-0 / 3-0
- **sources**: ['https://github.com/pvankranenburg/MTCFeatures', 'https://www.themefinder.org/']
- **evidence**: The MTCFeatures GitHub README (maintained by van Kranenburg) states verbatim '360 richly annotated melodies' and 'c. 18 thousand melodies' for the two corpora. Themefinder's own site confirms CCARH sponsorship and documents all five encoding schemes with matching terminology and symbol sets.

### 4. Open-source neural transcription tools provide usable but imperfect front-ends for converting commercial audio to symbolic (MIDI/note) representations suitable for downstream melody matching. Spotify's Basic Pitch is an open-source, instrument-agnostic, polyphonic audio-to-MIDI Python library with pitch-bend detection (best used one instrument at a time); its README claims accuracy 'competes with much larger and more resource-hungry AMT systems,' though the peer-reviewed paper (Bittner et al., ICASSP 2022) more cautiously reports frame-level accuracy only 'marginally below' specialized SOTA systems. YourMT3+ (MLSP 2024, arXiv:2407.04822) extends Google's MT3 architecture to multi-task, multi-instrument transcription. Omnizart is a peer-reviewed (JOSS, DOI 10.21105/joss.03391), general-purpose Python toolkit covering pitched-instrument, vocal-melody, chord, drum, and beat transcription.
- **confidence**: high
- **vote**: 3-0 / 2-1 / 3-0 / 3-0
- **sources**: ['https://github.com/spotify/basic-pitch', 'https://arxiv.org/abs/2407.04822', 'https://github.com/mimbres/YourMT3', 'https://github.com/Music-and-Culture-Technology-Lab/omnizart', 'https://joss.theoj.org/papers/10.21105/joss.03391']
- **evidence**: Basic Pitch's README and its ICASSP 2022 paper corroborate the accuracy claim with slightly different framing (vendor 'competes with' vs. paper's 'marginally below'). YourMT3's arXiv abstract and GitHub README confirm the MLSP 2024 venue and multi-instrument scope. Omnizart's JOSS paper page and GitHub README confirm peer review and toolkit scope. Note: a claim that YourMT3 achieves SOTA on Slakh2100/ENST-Drums benchmarks was explicitly refuted (0-3) and is not included here.

### 5. The legal/musicological caveats category (forensic-musicology expert-witness practice, substantial-similarity and extrinsic/intrinsic tests, scenes-a-faire doctrine, the Dark Horse/Blurred Lines/Stairway to Heaven rulings, the Music Copyright Infringement Resource dataset, public-domain/folk authorship, Los Kjarkas v. Kaoma 'Lambada', and modern interpolation-licensing credit practice) produced no claims that survived adversarial verification in this research pass — this is a genuine gap, not a confirmed absence of such material in the world.
- **confidence**: low
- **vote**: n/a (no surviving claims)
- **sources**: []
- **evidence**: No claim addressing any of these topics appears in either the confirmed or refuted lists provided; the pass appears to have either not located or not sufficiently corroborated sources in this category.

## Refuted (5)

### 1. Audible Magic's ACR technology identifies media via perceptual audio/video fingerprinting (not metadata, watermarks, or file hashes), and can detect matches even under extreme manipulation of rate, pitch, or tempo using small clips.
- **vote**: 0-3
- **source**: https://www.audiblemagic.com/technology/

### 2. SHS data is licensed under Creative Commons CC BY-NC 4.0 (non-commercial use only, with attribution required), and SHS additionally asserts database protection under EU-style 'sui generis' database right and copyright over the work/performance relationship structure itself.
- **vote**: 1-2
- **source**: https://secondhandsongs.com/page/API

### 3. Without an API key, SHS enforces hard rate limits of 20 requests/minute, 200/hour, and 1000/day (sliding window); an API key is required for higher throughput and unlocks additional data including external streaming links (YouTube, Spotify, Apple Music, Internet Archive) and, in the future, ISWC/ISRC/IPI identifier codes.
- **vote**: 1-2
- **source**: https://secondhandsongs.com/page/API

### 4. The documented object/entity types exposed by the API and website are Artist, Performance, Work, Release, and Label — the archived pages do not document any 'basedOn', 'derivedWorks', or explicit interpolation/sampling relationship field on the Work or Performance resource (only 'Sui Generis'-protected relations are referenced generically, and the detailed 'SHS Data Types' schema page itself could not be retrieved/archived).
- **vote**: 1-2
- **source**: https://secondhandsongs.com/page/API

### 5. The repository reports (via Papers with Code badges) state-of-the-art-track results on standard polyphonic transcription benchmarks Slakh2100 (multi-instrument) and ENST-Drums (drum transcription), making it a candidate front-end for symbolic melody extraction from commercial audio.
- **vote**: 0-3
- **source**: https://github.com/mimbres/YourMT3

## Unverified (0)

## Open questions (4)
1. Do any of Pex, Sureel, Musical AI, BMAT, Matchtune, Rightsify, Believe/TuneCore, or platform-internal systems at Spotify/Deezer publish technical detail on melody/composition-level or interpolation matching, or on multi-hop derivation-chain output — and if so, what accuracy do they report?
2. Does WhoSampled offer any API, licensed data feed, bulk-access program, or explicit terms of use for its sample/interpolation database, and does any open dataset of sample/interpolation relationships exist for training or evaluation?
3. What does the SecondHandSongs 'SHS Data Types' schema page actually document for the Work and Performance resources — is there a basedOn/derivedWorks field embedded in the object response even though no dedicated derivation-chain traversal endpoint exists?
4. What legal/musicological methodology (forensic musicology practice, substantial-similarity/extrinsic-intrinsic tests, the Dark Horse/Blurred Lines/Stairway to Heaven rulings, the Music Copyright Infringement Resource dataset) has actually been used to validate, critique, or benchmark automated melodic-similarity scoring — this entire area remains unresearched in this pass and should be the top priority for a follow-up.

## Caveats
Several confirmed findings rest on thin margins or degraded access: the SecondHandSongs evidence was gathered from a July 2026 Wayback Machine snapshot (not the live, Cloudflare-gated site) and the separate 'SHS Data Types' schema page — which would show whether Work/Performance resources actually contain basedOn/derivedWorks fields — could never be retrieved, so that specific sub-question from the original brief remains genuinely open rather than negatively resolved. Several claims that were initially collected did NOT survive verification and are worth flagging as areas of real uncertainty rather than settled fact: Audible Magic's specific manipulation-robustness and 99.99%-identification marketing claims, SHS's licensing terms (CC BY-NC, sui generis database right), SHS's numeric rate limits and API-key benefits, SHS's documented object/entity type list, and YourMT3's claimed SOTA benchmark results — all were refuted (0-3 or 1-2) and should not be treated as established. Basic Pitch's headline accuracy claim is a vendor self-report from its own README; the peer-reviewed paper is more hedged, so 'competitive with larger systems' should be read as marketing language partially, not fully, corroborated by academic evidence. Catalog-size and rate-limit figures (Hum to Search's 'thousands of songs,' MusicBrainz's 1 req/sec) are point-in-time facts from 2020–2026 sources and could change without notice. Most importantly, the large majority of named systems and topics in the original brief — nearly all commercial vendors besides ACRCloud/Audible Magic/Google, Shazam/SoundHound/Aha Music, WhoSampled/Discogs terms, modern audio embeddings and vector-search infrastructure, most symbolic corpora (Peachnote, Musipedia, SIMSSA/CANTUS/DIAMM, RISM, Barlow & Morgenstern, Essen Folksong), additional transcription models, and the entire legal/musicological caveats block — yielded zero surviving claims, meaning this synthesis cannot speak to them one way or the other; that silence should not be read as "these don't exist" but as "this research pass did not produce verified evidence about them."
## Sources (21)
1. None — https://www.acrcloud.com/cover-song-recognition/
2. None — https://blog.google/products/search/hum-to-search/
3. None — https://www.audiblemagic.com/technology/
4. None — https://musicbrainz.org/relationships/work-work
5. None — https://musicbrainz.org/doc/MusicBrainz_API
6. None — https://secondhandsongs.com/page/API
7. None — https://www.whosampled.com/about/
8. None — https://www.wikidata.org/wiki/Property:P144
9. None — https://www.discogs.com/developers
10. None — https://github.com/pvankranenburg/MTCFeatures
11. None — https://www.themefinder.org/
12. None — https://www.musipedia.org/
13. None — https://github.com/spotify/basic-pitch
14. None — https://github.com/mimbres/YourMT3
15. None — https://github.com/Music-and-Culture-Technology-Lab/omnizart
16. None — https://arxiv.org/abs/2306.00107
17. None — https://github.com/LAION-AI/CLAP
18. None — https://github.com/facebookresearch/faiss
19. None — https://en.wikipedia.org/wiki/Williams_v._Gaye
20. None — https://en.wikipedia.org/wiki/Skidmore_v._Led_Zeppelin
21. None — https://en.wikipedia.org/wiki/Gray_v._Perry
