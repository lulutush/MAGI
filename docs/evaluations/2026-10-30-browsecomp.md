# BrowseComp exploratory evaluation — 2026-10-30

[Français](2026-10-30-browsecomp.fr.md) · [Numeric data](2026-10-30-browsecomp.data.json) · [Evaluation guide](../EVALUATION.md)

## Finding and scope

**Observed: 2/8 correct with standard Hermes; 3/8 with the deployment's integrated MAGI workflow. The difference is not statistically established.**

This is an executed, small, paired study of a **specific Hermes deployment**, not a benchmark of the standalone public MAGI package. The public repository contains a portable reference extraction; the tested deployment also has its own complete skills, context stores, retrieval and orchestration. Installing this repository alone does not recreate that environment.

| Scored condition | Correct | Accuracy |
| --- | ---: | ---: |
| Standard Hermes (`off`) | 2/8 | 25.0% |
| Hermes + integrated MAGI (`on`) | 3/8 | 37.5% |

Observed difference: **+12.5 percentage points**, consisting of one additional solved task. Both conditions solved the same other two tasks. Five tasks were unsuccessful in both conditions; none was solved only by the baseline. The two-sided exact McNemar test gives **p = 1.0**. This neither establishes a benefit nor proves equivalence. Per-condition Wilson intervals are included in the numeric data; they are not confidence intervals for the paired difference.

This is **not a full BrowseComp score or an official leaderboard submission**. There was one run per condition and task, not enough repeated evidence to characterize reliability or stochastic variation.

## Design fixed before scored inference

- Source: the official BrowseComp release, containing 1,266 rows. Source hashes and the pinned evaluator revision are provided below and in the numeric data.
- Selection: `random.Random(20261030).sample(range(1266), 10)` in Python. The first two selected rows were reserved for calibration; the remaining eight were scored. Indices are zero-based CSV data-row indices, excluding the header.
- Calibration tasks: `bc-1116`, `bc-0450`. Scored tasks, in selection order: `bc-1147`, `bc-0683`, `bc-0843`, `bc-0076`, `bc-1058`, `bc-1210`, `bc-0536`, `bc-0553`.
- The selection, protocol and implementation hashes were frozen locally before scored inference; this was **not a public preregistration**. No scored question was replaced based on its outcome.
- Conditions alternated `off → on`, then `on → off`. Two task pairs could run in parallel; conditions within each pair ran sequentially. Order was balanced by alternation, not randomized.
- Same requested engine in both conditions: native Hermes `AIAgent`, provider `openai-codex`, model identifier `gpt-6-astra`, native reasoning effort `low`, unchanged native temperature default. The selection seed is not a model-generation seed.
- Each case began with fresh writable copies of the same initial memory/skill snapshots. The comparison isolates activating this workflow, **not removal of all pre-existing reliability practices** from Hermes.

### Actual intervention

The baseline retained normal honesty requirements, context, skills and native tools. It did not invoke the MAGI-specific orchestration, Vérité absolue and artifact-governance workflow.

The MAGI condition loaded the **complete bodies** of `magi-orchestration`, `verite-absolue-mode` and `magi-struct-comp-governance`, rather than a short extracted checklist. The harness invoked the real route/context-retrieval commands before the model answered; the returned context was added to its input. Native memory, skill, session, delegation and terminal tools remained available.

The three full skills plus real routing/retrieval are a bundled intervention: **this is not an instruction-only ablation with identical effective model context**. The underlying initial context stores were matched, but MAGI automatically selected and exposed additional context. Extra prompt size and retrieval effects cannot be separated from the rest of the workflow here.

The implementation reports `manual_command_and_skill_not_global_middleware`. “Integrated” means these components were actually available/invoked in the isolated deployment, **not an always-on middleware, autonomous use of every feature, or coverage of the entire MAGI concept**.

### Tools, isolation and limits

Both conditions exposed the same **25 native tools**. Real Web search used the Hermes DDGS provider; extraction used HTTP fetching and document parsing. Search/extraction ran in disposable subprocesses after the calibration incident described below. Native browser/Chrome access was also available. Search, extraction and browser smoke checks succeeded before the scored runs. There were no fabricated search responses.

Per-run mount/PID namespaces hid the answer key, sibling runs and live profile; writes went to test copies. Public network research remained enabled. These controls and the observed traces are **not a general security certification against an adversarial agent or proof of absence of prior benchmark contamination**. Benchmark/answer-key lookup was prohibited; the retained trace audit found no matching prohibited lookup pattern, which is a bounded check, not exhaustive proof.

Equal per-run limits:

| Limit | Setting |
| --- | ---: |
| Instrumented model-request constructions, including native child calls if used | 24 |
| Elapsed-time threshold, checked before the next model request | 360 seconds |
| Generated-output threshold, checked before the next model request | 12,000 tokens |
| Separate supervisor timeout | 430 seconds |
| Simultaneous task pairs | 2 |

These are not all hard ceilings: an in-flight request may cross a time/output threshold, and HTTP retries are not individually capped by the construction counter. Do not interpret them as a hard billing budget.

Outbound model/effort fields were checked and returned model identifiers recorded. The normalized response did not expose a reasoning-effort echo: `low` is verified in outgoing requests, **not independently at the provider's model weights**.

## Scoring and per-task results

Answers were frozen before a separate, stateless `gpt-6-astra`/`low` grading call with no tools or conversation history. The grader received the official reference and pinned semantic-equivalence rubric, but no condition label. This is **condition-blinded grading, not an independent model family or independent external replication**; answer style can still reveal clues to condition.

The pinned official evaluator's capture-group parsing issue was corrected (`group(1)` for `yes`/`no`, rather than comparing the entire `correct: yes` match with `yes`), with positive/negative parser checks. Credited and nonempty rejected answers were subsequently reviewed against the references; primary scores were unchanged. Strict normalized text matching was only a secondary diagnostic: formatting/initial-spacing false negatives did not determine the primary scores.

| Task | Standard Hermes | Integrated MAGI |
| --- | --- | --- |
| `bc-1147` | Resource limit; incorrect | Resource limit; incorrect |
| `bc-0683` | Correct | Correct |
| `bc-0843` | Resource limit; incorrect | Completed; incorrect |
| `bc-0076` | Correct | Correct |
| `bc-1058` | Completed; incorrect | Completed; incorrect |
| `bc-1210` | Resource limit; incorrect | Resource limit; incorrect |
| `bc-0536` | Resource limit; incorrect | Correct |
| `bc-0553` | Completed; incorrect | Completed; incorrect |

“Completed” describes execution, not correctness. Resource-limit stops count as unsuccessful tasks under the predeclared budget; they were not silently discarded. The only discordant success (`bc-0536`) therefore compares a MAGI answer with a baseline that exhausted its budget, not two conflicting completed answers.

Descriptively, baseline failures comprised four resource-limit stops, one explicit `UNKNOWN` and one partial answer. MAGI failures comprised two resource-limit stops, two explicit `UNKNOWN` answers and one partial answer. An abstention, an incomplete answer and an infrastructure crash are different events; this study does not measure a general hallucination rate.

## Observed component use

In the eight scored MAGI runs:

- full bodies of all three skills present in the instructions;
- **8** route-command executions and **8** contextual retrievals;
- context routing queried the built-in memory export, project registry and Cognee in **8** runs each; Cognee used the frozen CHUNKS/vector sidecar, not an additional generative model;
- **6** evidence-gate invocations and **6** provisional-artifact creations, after a final answer existed;
- **0** native delegation calls, memory-write tool calls or session-search calls, despite their availability.

**The gate and artifact commands ran after the scored answer was frozen.** They document post-answer governance but cannot explain an improvement to that already-frozen answer. A gate checks declared evidence presence, not correctness against the benchmark reference. These harness-driven operations must not be presented as spontaneous agent decisions. Their individual quality benefits were not tested.

No MAGI-specific invocation was observed in the baseline trace audit. Resetting state between tasks prevents cross-item learning here; persistent memory, delegation and long-term self-improvement benefits remain unmeasured.

## Time and token usage

Scored solver phase only:

| Measure | Standard Hermes | Integrated MAGI |
| --- | ---: | ---: |
| Median supervised time per task | 361.8 s | 329.8 s |
| Instrumented model-request constructions | 121 | 139 |
| Model-requested tool calls | 254 | 279 |
| Input tokens, cache included | 3,971,323 | 6,802,479 |
| Cached input subset | 3,627,648 | 6,206,720 |
| Uncached input | 343,675 | 595,759 |
| Output tokens | 20,885 | 23,391 |
| Reasoning subset of output | 9,892 | 10,163 |

MAGI used **73.3% more uncached input** and **12.0% more output** on this sample. Cached input is already included in input; reasoning tokens are already included in output. Do not add either subset a second time.

These times come from the supervisor: they include process startup and post-answer gate/artifact work when reached, but exclude separate grading and parent/setup/conversation work. Network variability, caches, concurrent tasks and resource-limit censoring make these medians descriptive; they do not establish that MAGI is faster. Model-requested tool totals exclude deterministic pre/post-task harness commands, even though their elapsed time falls within the supervisor's measurement.

### Calibration and other measured usage

Valid calibration was **1/2 correct in each condition**, excluded from the scored result. A first calibration was interrupted by a native heap abort during concurrent extraction. Search/extraction were moved to disposable subprocesses for **both** conditions, live preflight was repeated, and the same calibration tasks were rerun. This was an infrastructure repair before scored inference, not outcome-based question replacement.

| Solver stage | Input, cache included | Cached subset | Output | Request records / normalized responses |
| --- | ---: | ---: | ---: | ---: |
| Interrupted calibration (`calibration-v1`) | 2,166,876 | 1,953,408 | 7,038 | 49 / 48 |
| Valid calibration (`calibration-v2`) | 3,158,744 | 2,906,240 | 11,077 | 74 / 73 |
| Scored runs (`main-v1`) | 10,773,802 | 9,834,368 | 44,276 | 260 / 252 |

Separate grader usage: calibration **2,074 input / 141 output**; scored evaluation **6,721 input / 528 output**. Recorded grader input had no cache hits. Interrupted-run usage is retained rather than hidden.

Usage covers recorded responses. Missing/in-flight responses, HTTP retries and preparation/orchestrator/conversation work are not fully measured here. The request/response-count gap is not itself an error count or a count of billable calls. **No monetary cost or complete project-wide token total is claimed.**

## Public evidence and reproducibility boundary

The [numeric data](2026-10-30-browsecomp.data.json) includes the sampling seed/indices, protocol settings, aggregate and per-run metrics for calibration/scored runs, recorded overhead, component counts and hashes identifying retained local source records. Hashes establish byte identity when the source is available, not truth, external validation or public preregistration.

Offline checks, from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_benchmark_report.py' -v
```

They recompute selection, paired counts, confidence intervals, medians and recorded token totals. **They do not call a model, rerun BrowseComp or independently regrade the answers.**

Not published: question/answer-key text, raw solver answers, model/tool transcripts, personal memories, conversations, private prompt/skill bodies, credentials, host-specific configuration or the private execution harness/retrieval snapshot. Consequently, this is a **sanitized results-and-methods publication, not a fully reproducible end-to-end benchmark release**. Neither the success labels nor the full deployment can be independently reconstructed from this subset alone.

Sources:

- [Official BrowseComp data location](https://openaipublic.blob.core.windows.net/simple-evals/browse_comp_test_set.csv), downloaded CSV SHA-256: `7b24471cd5b3eb2a46830a14802b5c029ea62f488ff75a0f88af7923d1454abf`.
- [Pinned official evaluator](https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/browsecomp_eval.py), revision `652c89d0ca9df547706735883097e9537d40dc47`; downloaded-file SHA-256: `0bfb33cfdf5fa0e0d7da48068cc86c5a22acc755979be4a2b46f8a821cc44b74`.

## Interpretation

The defensible finding is **one additional solved task, higher token usage, and substantial uncertainty**. Eight tasks and one discordance do not establish a general quality advantage, equivalence, or a contribution from any individual component. Web content changes and possible prior model exposure to a public benchmark further limit interpretation.

A stronger future study would need a larger held-out sample, predeclared repetitions, transparent reproducible non-private fixtures/harness, matched-context ablations and independent grading. Those are proposed next experiments, **not experiments performed or evidence of an expected favorable result**.
