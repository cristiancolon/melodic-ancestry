# Research record

The primary research for this project was two `deep-research` workflow passes. Neither ever
produced a standalone report file — the output lived only inside the workflow run records, in
the Claude Code session store, under the **Windows-side** working directory the workflows were
launched from:

```
/home/cca/.claude/projects/-mnt-c-Users-cicol/6484b41a-8321-48eb-aded-599ac518656d/workflows/
```

That location is on the drvfs mount and is subject to session pruning. These files are the
durable copy. Recovered 2026-09-02.

| File | What |
|---|---|
| `pass1-broad.md` / `.result.json` | Pass 1 — the broad question. 18 findings. |
| `pass2-gapfill.md` / `.result.json` | Pass 2 — gap-fill on uncovered areas. 5 findings. |

The `.md` files are a rendering for reading. The `.result.json` files are the workflow's own
structured output verbatim (`question`, `summary`, `findings`, `caveats`, `openQuestions`,
`refuted`, `unverified`, `sources`, `stats`) plus run metadata. **The JSON is authoritative** —
if the two ever disagree, the JSON is right.

## The runs

| Run | Status | Agents | Model | Findings | Tokens |
|---|---|---|---|---|---|
| `wf_eb775dff-367` | completed, 22.2 min | 104 | Opus | 18 | 3.66M |
| `wf_3307eee1-beb` | completed, 11.1 min | 103 | Sonnet (all stages) | 5 | 3.96M |
| `wf_c8df5193-3a8` | **killed** at 1.7 min | 6 | — | — | 0.21M |

`wf_c8df5193-3a8` was a false start of the gap-fill pass and produced no result. It is not
preserved here.

Both runs record `defaultModel: claude-opus-5[1m]`, but pass 2's *script* pins
`model: "sonnet"` on all five stages — scope, search, fetch, verify, synthesize. Pass 1 has no
model overrides. So pass 2 really did run on Sonnet; the workflow-level default is misleading.

## Why pass 2 came back thin — read this before drawing the wrong lesson

| | Pass 1 (Opus) | Pass 2 (Sonnet) |
|---|---|---|
| sources fetched | 22 | 21 |
| claims extracted | 110 | 76 |
| claims verified | 25 | 25 |
| confirmed | 22 | 20 |
| killed | 3 | 5 |
| **after synthesis** | **18** | **5** |
| budget-dropped | 4 | 7 |

The adversarial verifier was **not** the problem. On Sonnet it confirmed 20 of 25 (80%) against
Opus's 22 of 25 (88%) — and it confirmed four times more than it killed.

The collapse was at **synthesis**: 20 confirmed claims went in and 5 findings came out. Sonnet's
synthesizer discarded three quarters of what the verifier had confirmed. Budget-dropped also rose
from 4 to 7.

**So the fix is to pin `synthesize` to Opus, not the verifier.** Search, fetch and verification
are safe to run on Sonnet and that is where nearly all the token spend goes.

## Caveat on the `refuted` lists

`refuted` in this schema means *unverifiable from the cited source under adversarial voting* —
not *proven false*. Pass 1's refuted list contains three items, one of which ("the authors deny a
single original melody exists to be recovered") reads like a substantive finding. It is not
verified, and should not be cited as one. The abstention argument it appears to support stands
instead on pass 1 findings 11 and 14, which were confirmed.
