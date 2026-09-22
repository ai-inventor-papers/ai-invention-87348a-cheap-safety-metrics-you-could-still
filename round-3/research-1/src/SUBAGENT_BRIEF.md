# Shared brief for novelty-sweep subagents (today = 2026-09-21)
Workspace (write ONLY here): /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_research_1
Candidate definitions: candidates_iter3.md in the workspace.
Study context: a cheap, PARENT-FREE (no base/reference model), single-model, few-prompt (~16 prompts) safety score for random HF checkpoints, validated ACROSS architecture families against benchmark safety (harmful-refusal AND over-refusal; blanket refuser must lose).

## Web tools (read /ai-inventor/.claude/skills/aii-web-tools/SKILL.md). Prefer built-in WebSearch/WebFetch (load via ToolSearch "select:WebSearch,WebFetch"); use the grep script for exact quotes:
export SKILL_DIR=/ai-inventor/.claude/skills/aii-web-tools; export PY="$SKILL_DIR/../.ability_client_venv/bin/python"
$PY "$SKILL_DIR/scripts/aii_fast_web_search.py" --query "..." --max-results 10
$PY "$SKILL_DIR/scripts/aii_fast_web_fetch.py" grep --url "https://arxiv.org/pdf/<id>" --pattern "causal\s+gain" -i --max-matches 10 --context-chars 250
Save useful raw grep/fetch outputs to raw/<prefix>_*.txt in the workspace.

## Tooling rules
T1 scholarly mode (OpenAlex/Crossref) is off-topic for LLM safety: use GENERAL mode with site hints (arxiv, openreview, aclanthology). Never conclude "no prior work" from scholarly mode.
T2 PDF text has hard line breaks: grep with whitespace-flexible patterns (e.g. 'refusal\s+direction'), try >=2 phrasings before NOT-FOUND.
T3 use arxiv.org/abs/<id> for metadata; arxiv.org/pdf/<id> or /html/<id> for grep. Record version (v1/v2).
T4 known ID collisions: 2606.22676 (Skin-Deep) vs 2606.22686 (Geometry of Refusal, TrustNLP); 2606.25750 (RAS) vs 2607.25750.
T5 iteration-1 dependency (/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art/gen_art_research_1/research_out.json, raw/candidates.json, raw/adversarial_C3_C4_C5.json) used labels C1-C5 for DIFFERENT metrics. Map by CONTENT only. Its verdicts on AMS 2608.05578, Skin-Deep 2606.22676, N-GLARE 2511.14195, RAS 2606.25750, HRCI_repr 2606.16349, IRT (2608.05086, 2606.20626), 2608.13329 are reusable—cite, don't re-derive. Skim with grep/python, do not cat whole 144KB file.
VERIFY EVERY seed arXiv ID via its abs page before using it (seeds come from memory; some may be wrong). If an ID does not match the expected title, find the right ID by title search. Never keep a guessed ID.

## Verdict rule (apply exactly)
PUBLISHED = a paper computes the same functional form per model AND compares or ranks models by it as a safety indicator.
ADJACENT = the same quantity is computed but only inside one model (interpretability/mechanism analysis/steering tool), OR a different functional form is used as a cross-model safety score.
NEW = neither exists after >=4 general-mode queries plus 1 citation-chasing hop from the closest hit. For NEW, list what was searched and quote the nearest miss.
Do NOT soften PUBLISHED to ADJACENT. Note: "computed on several models" in a mechanism paper (e.g. Arditi's 13 models) is not "ranked as safety indicator" unless the paper treats the per-model number as a safety comparison — quote the evidence either way; if ambiguous, say so in adversarial_note.

## Output record per candidate (JSON list)
{candidate, closest_prior_work:[{arxiv_id_or_doi,title,first_author,year,venue}], what_it_measured, n_models_and_families, used_to_rank_models:{value:"yes|no|partial",quote}, parent_free:"yes|no|n/a", prompt_budget, correlated_with_benchmark_safety:{value:"yes|no",number}, verdict:"NEW|ADJACENT|PUBLISHED", verbatim_quote, locator:"section/table/eq/page + arXiv version", queries_run:[{query,mode,hits_scanned}] (>=4), adversarial_note, positioning_sentence (one sentence the paper can paste, citing by arXiv ID)}
Quotes must be EXACT text copied from the fetched source (they will be string-matched against the URL). Also add a top-level list "papers_checked" [{id,title,first_author,year,url,verified_title_matches:true/false}] so the bibliography can be built from it.
Final reply to orchestrator: <=25 lines: per candidate verdict + closest ID, any seed-ID corrections, blockers. No narration.
