#!/usr/bin/env python3
"""Generate authored TypeScript trigger fixtures offline, with optional live generation.

The default corpus covers realistic package workflows and adjacent non-matches.
--live explicitly opts into the existing paid model generation capability.

Usage:
    python3 lab/eval/triggers/generate_triggers.py              # All skills
    python3 lab/eval/triggers/generate_triggers.py --skill plan  # One skill
    python3 lab/eval/triggers/generate_triggers.py --dry-run     # Show what would be generated
"""

import argparse
import json
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)

from lab.eval.matchers import parse_frontmatter

PLUGIN_ROOT = os.path.join(PROJECT_ROOT, "plugins", "typescript-starter")
TRIGGERS_DIR = os.path.dirname(os.path.abspath(__file__))


def get_all_skill_descriptions() -> dict[str, str]:
    """Read all skill names and descriptions."""
    skills_dir = os.path.join(PLUGIN_ROOT, "skills")
    descriptions = {}
    for name in sorted(os.listdir(skills_dir)):
        skill_path = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(skill_path):
            continue
        with open(skill_path) as f:
            content = f.read()
        fm = parse_frontmatter(content)
        desc = str(fm.get("description", ""))
        if desc:
            descriptions[name] = desc
    return descriptions


def generate_with_model(skill_name: str, skill_desc: str, all_descriptions: dict[str, str]) -> dict | None:
    """Use haiku to generate trigger prompts for one skill."""

    # Build context: show ALL skill descriptions so haiku understands the landscape
    other_skills = "\n".join(
        f"- {name}: {desc[:100]}"
        for name, desc in all_descriptions.items()
        if name != skill_name
    )

    prompt = f"""You are generating test prompts for a Claude Code plugin skill trigger evaluation.

TARGET SKILL: {skill_name}
DESCRIPTION: {skill_desc}

OTHER SKILLS IN THE PLUGIN (for context — generate should_not_trigger prompts that match THESE instead):
{other_skills}

Generate EXACTLY this JSON (no markdown, no explanation):
{{
  "skill": "{skill_name}",
  "should_trigger": [
    "prompt1 — realistic user request that SHOULD load {skill_name}",
    "prompt2 — different phrasing, same intent",
    "prompt3 — casual/informal version",
    "prompt4 — edge case still in {skill_name}'s domain",
    "prompt5 — another scenario {skill_name} handles"
  ],
  "should_not_trigger": [
    "prompt6 — similar but belongs to a DIFFERENT skill (name which one)",
    "prompt7 — too generic, no specific skill needed",
    "prompt8 — adjacent domain but different skill"
  ]
}}

RULES:
- Prompts must be realistic — what a real developer would actually type
- should_trigger: Must clearly match {skill_name}'s description
- should_not_trigger: Must NOT match {skill_name} but COULD match another skill or none
- Mix formal and casual phrasing
- Include TypeScript starter-specific terms where natural
- Keep each prompt 5-20 words
- Output ONLY valid JSON, nothing else"""

    try:
        result = subprocess.run(
            [
                "claude", "-p", prompt,
                "--model", "haiku",
                "--output-format", "text",
                "--max-budget-usd", "0.50",
                "--no-session-persistence",
            ],
            capture_output=True, text=True, timeout=60,
        )

        if result.returncode != 0:
            print(f"  ERROR: claude returned {result.returncode}", file=sys.stderr)
            return None

        text = result.stdout.strip()

        # Strip any markdown fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        # Find the JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            return data

        print("  ERROR: Could not parse JSON from output", file=sys.stderr)
        return None

    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT for {skill_name}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ERROR for {skill_name}: {e}", file=sys.stderr)
        return None


# Authored against the TypeScript starter responsibilities. The last two
# prompts exercise distinct held-out situations; negative routes are explicit
# neighboring responsibilities, with no answer labels embedded in the prompt.
CURATED_POSITIVES = {
'audit': 'Assess the overall health of this TypeScript monorepo before release.|Run a project health audit across architecture, security, tests and dependencies.|Give me a quick health assessment before a full starter audit.|Audit only security across the starter and identify uninspected areas.|Compare project health with our previous audit after this refactor.|Audit changes since commit abc123 across the affected starter packages.|Produce a scored health report with evidence from all specialist reviews.',
'background-jobs': 'Implement a worker handler that tolerates duplicate Postgres job delivery.|Check lease ownership before acknowledging this background job.|Add bounded retry handling to the custom worker registry.|Design worker shutdown so active handlers finish before storage closes.|Keep recurring jobs terminal across process restarts.|Explain why batchSize does not control parallel handler concurrency.|Test a stale worker acknowledgement after another worker reclaimed the lease.',
'boundaries': 'Assess imports and coupling across the Fastify modules and workspace packages.|Map package boundaries before splitting this repository adapter.|Find dependency cycles that cause runtime initialization hazards.|Score our service and repository boundaries with file evidence.|Check whether the worker imports API implementation code.|Propose an extraction while preserving public package exports and consumers.|Distinguish a type-only import cycle from an unsafe runtime dependency.',
'brainstorm': 'I have a vague idea for session notifications; help explore requirements.|We need better mobile collaboration but have not chosen an approach.|Help compare alternatives for offline session editing before planning.|Explore the scope and tradeoffs of adding document version history.|Interview me about what a session archive feature should accomplish.|Capture our feature discussion so a later implementation plan can reuse it.|Research uncertain requirements and return to the feature discussion afterward.',
'brief': 'Walk me through the reasoning behind this existing implementation plan.|Explain the schema decisions in the plan without implementing it.|Give me a short briefing of the latest pending plan.|Explain what the completed plan phases changed and why.|Use the scratchpad to explain this plan tradeoff.|Brief me on the differences between planned and completed tasks.|Show the plan explanation before asking me to continue the briefing.',
'challenge': 'Challenge this proposed architecture before we commit to it.|Stress-test our migration plan with hard questions about rollback.|Question my assumption that this cache solves the actual bottleneck.|Find the weakest evidence in this design decision.|Act as a skeptical reviewer of these implementation tradeoffs.|Challenge whether splitting this service improves anything measurable.|Question the failure modes we missed in the deployment proposal.',
'codex-loop': 'Run local Codex review and fix findings until the bounded loop is clean.|Use the installed Codex CLI to review this working tree repeatedly.|Repair actionable findings from local codex review with verification between rounds.|Continue the local Codex review loop for at most three rounds.|Review local changes with Codex and retain failure exit codes.|Handle an unavailable Codex CLI without claiming the review passed.|Stop the review loop when the same finding cannot be resolved safely.',
'compound-docs': 'Search our saved solution docs for the earlier stale subscription fix.|Find previous troubleshooting notes before investigating this recurring failure.|Look up an existing solution by package and error signature.|Load the documented workaround already stored under .claude/solutions.|Search the solution index for tested Postgres migration lessons.|Check whether a retrieved solution applies to our current locked versions.|Find related solution notes through their metadata and links.',
'compound': 'The stale response fix worked; capture it as a reusable solution.|Document the root cause and verified fix in our solution archive.|Turn this completed debugging session into a searchable solution note.|Save the tested workaround and the approaches that failed.|Record the incident symptoms, cause, verification and future prevention.|Update an existing solution note with the newly confirmed cause.|Capture a solved worker lease bug without copying sensitive SQL parameters.',
'deploy': 'Review the existing Docker and Compose production deployment setup.|Verify migration ordering before the API starts in the image.|Configure deployment using the starter environment and storage modes.|Check a built image with the existing deploy smoke tests.|Explain how production API and worker processes share persistent storage.|Investigate why the deployed container uses the memory driver unexpectedly.|Verify shutdown and health behavior in the prepared deployment artifact.',
'deps-audit': 'Audit the pnpm lock dependency graph for supply-chain risks.|Inspect package tarballs and verify their locked integrity before installation.|Compare dependency risk between this base commit and the new lock.|Run an offline dependency audit using recorded registry fixtures.|Check lifecycle scripts, advisories and unexpected package origins.|Keep the audit incomplete when required source coverage is unavailable.|Audit aliases and workspace dependencies without treating local packages as registry downloads.',
'deps-update': 'Update compatible dependency patches in the web workspace and verify them.|Inventory outdated pnpm packages before selecting a scoped upgrade.|Upgrade the Fastify package group while checking peer compatibility.|Prepare a new lock with lifecycle scripts disabled before auditing it.|Update only the requested Drizzle dependencies and review their changelogs.|Handle the Expo dependency group without forcing its React version onto web.|Stop and preserve evidence when a scoped dependency update fails verification.',
'deps-vet': 'Record this reviewed exact package artifact in dependency-vet.json.|Revoke the previous acceptance of this dependency artifact.|Review whether this audit meets our required deployment criterion.|Import a legacy dependency review as unverified evidence.|Record an explicitly accepted risk with the actual reviewer identity.|Reject a vetting entry whose integrity no longer matches the lock.|Check whether an old package approval remains valid after a patch changed.',
'docs-fetcher': 'Fetch official Fastify documentation for the version in our lockfile.|Look up the installed Drizzle API in its primary documentation.|Retrieve version-aware TypeBox docs for this schema method.|Find official Expo documentation matching this mobile package version.|Read the upstream documentation for a specific pnpm package API.|Resolve a scoped npm package name before fetching its API docs.|Report that documentation is unavailable instead of inventing a method signature.',
'document': 'Document the tested Fastify endpoint and its TypeBox response contract.|Update the README to explain the verified storage modes.|Write an ADR for this implemented package boundary decision.|Add API documentation matching the current OpenAPI response envelopes.|Document the worker lifecycle after its tests pass.|Check that the documented Server Action error result matches implementation.|Update examples to reflect the tested migration and deployment commands.',
'domain-resources': 'Design a domain operation across TypeBox contracts, services and repository ports.|Add a session capability without coupling its service to Fastify.|Model validation and domain behavior separately from Drizzle persistence.|Identify which existing layer should own this session invariant.|Trace a domain change through shared contracts and both clients.|Explain why a Session identifier is not an authenticated user identity.|Keep a domain resource change compatible with memory and Postgres adapters.',
'drizzle-constraint-debug': 'Diagnose this Postgres unique constraint failure in a Drizzle repository.|Trace SQLSTATE 23503 back to the schema and migration state.|Find why a generated migration conflicts with existing rows.|Investigate a constraint name mismatch without resetting the database.|Explain a repository insert failure using sanitized database error evidence.|Reproduce the constraint failure in disposable Postgres before proposing a fix.|Distinguish a domain conflict from an unexpected driver error wrapper.',
'drizzle-n1-check': 'Find the suspected N+1 queries in this Drizzle loader.|Count repeated repository queries as the result list grows.|Check whether this loop executes one SQL query per session.|Investigate missing batching in this database read path.|Compare query counts before and after eager loading these records.|Confirm the suspected N+1 with actual SQL evidence instead of source hits alone.|Check whether a proposed join multiplies rows while reducing query count.',
'drizzle-patterns': 'Implement a transactional write using the existing Drizzle repository adapter.|Design a schema migration while preserving memory and Postgres contracts.|Use parameterized Drizzle queries for this repository filter.|Keep generated SQL and schema changes consistent with migration history.|Add an explicit repository port method for this persistence operation.|Choose an appropriate integer or decimal representation for a money column.|Preserve post-write consistency when a transaction updates related records.',
'examples': 'Show a minimal Fastify and TypeBox endpoint example matching this starter.|Give me a Drizzle repository example with a meaningful test.|Walk through a React client example using the existing session contracts.|Provide sample code for a custom worker handler with cancellation.|Explain a small TypeScript example using the installed package APIs.|Show a mobile REST service example without web-only DOM components.|Demonstrate a domain service using the memory adapter in a test.',
'fastify-modules': 'Design a Fastify module with explicit AppContext and registry composition.|Separate transport validation from domain service behavior in this route.|Add a module without making API core import its domain implementation.|Explain how the Fastify plugin registry wires repository dependencies.|Refactor HTTP error handling while preserving the response envelope.|Check teardown ownership for resources created by a Fastify plugin.|Keep service code framework independent while adding a new endpoint.',
'freeze': 'Freeze edits to the database package for this investigation.|Make this session read only using the existing edit freeze.|Allow editing only apps/mobile and keep other directories frozen.|Turn off the explicit editing freeze for the authorized task.|Inspect the current allowed edit directories.|Explain which editing tools the freeze covers and why Bash is different.|Narrow the edit scope without allowing paths that escape through symlinks.',
'full': 'Run the complete feature lifecycle from planning through verified review.|Implement this feature with the full bounded plan work review workflow.|Resume the autonomous workflow from its recorded progress state.|Run full mode with a limited number of review correction cycles.|Carry this authorized feature through planning, implementation and final checks.|Preserve the full workflow cycle count after context compaction.|Stop full mode with an explicit blocker when its recovery limit is reached.',
'help': 'Which starter workflow should I use for this task?|List the available public TypeScript starter commands.|Help me choose between quick, plan and investigate.|Which workflow handles reviewer feedback on an existing PR?|Show the command for inspecting suspected repeated database queries.|Explain which skills are background knowledge rather than public commands.|Find the relevant workflow without starting implementation.',
'init': 'Initialize this plugin for the current TypeScript starter workspace.|Install starter instructions appropriate to this agent runtime.|Set up project rule references without overwriting existing instructions.|Detect actual package scripts before configuring the plugin.|Update the local plugin integration for this monorepo.|Initialize from a package directory while keeping state at the workspace root.|Preserve custom project instructions when refreshing generated references.',
'intent-detection': 'I have mixed Fastify and React concerns and am unsure which workflow fits.|Route this ambiguous starter request to the right technical guidance.|Determine whether this task needs investigation or coordinated planning.|I cannot tell whether the issue belongs to Drizzle or the API service.|Choose relevant starter knowledge for a request spanning server and mobile.|Identify the main intent before suggesting a workflow for this vague bug report.|Separate the debugging request from the unrelated documentation request.',
'intro': 'Walk me through how this TypeScript starter plugin is organized.|I am new to this plugin; explain its commands and workflows.|Introduce the plugin lifecycle with a small example task.|Explain how skills, agents and hooks work together here.|Show a new contributor how to find starter guidance.|Explain the differences between installed runtime capabilities.|Give me an onboarding tour without changing project files.',
'investigate': 'Diagnose this reproducible Fastify error before changing any code.|Find the root cause of the stale mobile screen after reconnect.|Reproduce this failing TypeScript behavior and test a hypothesis.|Investigate why the web client sometimes drops session updates.|Debug the first error from this failed workspace build.|Separate the trigger from downstream symptoms in this worker crash.|Use independent investigations to narrow a bug crossing several package boundaries.',
'learn-from-fix': 'Capture the TypeScript package lesson from this successful fix.|Save version-specific Fastify knowledge as a project package skill.|Record this verified Drizzle API rule for future sessions.|Update the relevant lesson without overwriting hand-authored skill content.|Choose project or personal scope for this package-specific discovery.|Normalize a scoped npm name before saving its generated knowledge skill.|Preserve the locked version and source evidence when recording the lesson.',
'narrow-catch': 'Narrow this broad catch so unexpected TypeScript errors still propagate.|Replace catch-and-ignore with handling for one known error type.|Inspect which thrown values this storage catch should classify.|Use unknown error narrowing before accessing the driver error code.|Keep an expected AppError separate from programmer defects.|Rethrow an unexpected filesystem error instead of reporting a successful archive.|Preserve worker retry behavior when narrowing an exception handler.',
'perf': 'Measure the cause of this slow API response before optimizing.|Investigate event loop delay and retained state under load.|Profile the mobile screen slowdown during repeated reconnects.|Find the dominant latency in this server and database request path.|Compare a performance baseline before and after this optimization.|Measure JSON serialization cost for growing session snapshots.|Distinguish CPU blocking from slow I/O in the Node worker.',
'permissions': 'Recommend scoped Bash permissions for the actual pnpm package scripts.|Reduce repeated permission prompts without allowing destructive commands.|Inspect script contents before proposing command allow patterns.|Set up safe agent permissions for typechecks, lint and tests.|Review which deployment commands require separate target authorization.|Explain why a broad pnpm wildcard grants more than verification commands.|Derive workspace permissions without enabling force pushes or database resets.',
'plan': 'Create an implementation plan for a feature spanning API, database and clients.|Plan the migration and consumer changes for a shared TypeBox contract.|Break this coordinated starter feature into verifiable tasks.|Design a plan with acceptance criteria and affected package checks.|Plan the implementation using the requirements we already agreed.|Include rollback evidence and disposable Postgres checks in the migration plan.|Record unresolved decisions without starting unrequested implementation.',
'pnpm-compression': 'Reduce noisy pnpm and Turbo output using the existing RTK setup.|Configure output compression while preserving failing command exit codes.|Inspect why compressed lint output hides the first useful diagnostic.|Make long workspace test output easier to read without losing logs.|Check whether RTK can filter these installed package scripts.|Compare raw and compressed output for a failed Turbo task.|Preserve full failure artifacts when summarizing command output.',
'pr-review': 'Address the unresolved review comments on this GitHub pull request.|Fetch reviewer feedback and prepare fixes for the current PR head.|Review each thread before deciding whether the suggested change is correct.|Draft responses to actionable PR feedback after checking the code.|Resolve the requested PR issues and run the affected checks.|Identify outdated review threads that refer to a previous commit.|Keep bot suggestions separate from verified defects in this PR review.',
'quick': 'Fix this typo in one mobile component with a contained edit.|Rename this local TypeScript variable and verify the affected package.|Add a small validation guard using the neighboring implementation pattern.|Update one component prop without changing the shared protocol.|Make this bounded API error-message change in the existing module.|Stop treating a TypeBox schema change as tiny when several consumers need edits.|Complete this authorized single-workspace fix without an unnecessary planning interview.',
'react-patterns': 'Implement the web session mutation through the existing Server Action.|Handle stale mobile REST responses using request ownership.|Wire the existing shared event projection into a web SSE subscription.|Add cancellation and cleanup to this mobile WebSocket hook.|Keep web and mobile transports separate while sharing pure contracts.|Recover the web stream after a revision gap without applying stale events.|Avoid putting server-only package imports in a client component.',
'react-state-audit': 'Audit retained React state after repeated screen mount and unmount.|Find leaking subscriptions in this client session hook.|Inspect whether stale promises retain an old mobile screen instance.|Measure growing client memory during repeated stream reconnects.|Check resource cleanup and ownership in the current React state model.|Identify unnecessary retained snapshots in this client store.|Trace a subscription that survives navigation when its screen should be disposed.',
'recall': 'Find how we fixed this problem in a previous session.|Search earlier session history for the migration decision.|Recall the work recorded before yesterday session ended.|Find the transcript evidence behind our earlier implementation choice.|Locate previous session notes about this repeated package error.|Distinguish remembered decisions from guesses when session evidence is missing.|Recover the context from an earlier conversation without recreating its work.',
'research': 'Research official guidance for this TypeScript package design decision.|Compare upstream approaches using primary sources and our locked versions.|Investigate whether this library supports the behavior we need.|Write an evidence-backed research note about Node lifecycle handling.|Research a Fastify integration tradeoff before we choose an implementation.|Separate upstream facts from inferences in the research result.|Compare alternatives without installing another framework into the starter.',
'review': 'Review this branch diff for correctness and starter architecture issues.|Perform a read-only review of changes since the merge base.|Inspect the changed API and repository code for actionable defects.|Review this patch with file and line evidence and relevant tests.|Check whether the proposed changes satisfy the stated requirements.|Report a concrete cross-client regression introduced by this diff.|Keep preexisting unrelated issues separate from new review findings.',
'runtime-inspection': 'Inspect the running starter API health and confirm its storage driver.|Use the existing OpenAPI endpoint to inspect runtime routes.|Check the live application through the inspection tools already available.|Explain which local runtime observations can confirm this API behavior.|Inspect HTTP responses and logs without starting a new server.|Distinguish a process on the default port from the actual starter health envelope.|Report that runtime inspection is unavailable instead of inventing an MCP connection.',
'security': 'Audit the starter boundary validation and accidental secret exposure.|Review SQL error handling for leaked parameters and driver details.|Check storage filename traversal and document shape validation.|Assess authorization assumptions before treating Session IDs as identity.|Review client bundles for server-only configuration leaks.|Design security tests for a future identity feature without claiming auth exists today.|Inspect REST, SSE and WebSocket trust boundaries without destructive live probes.',
'techdebt': 'Assess duplicated contracts and avoidable complexity in this starter.|Rank technical debt by current cost and change risk.|Find leaky service and repository abstractions without refactoring automatically.|Evaluate whether this repeated logic represents the same domain rule.|Identify unused dependencies and stale architecture documentation.|Explain why an intentional repository port is not needless indirection.|Prioritize evidence-backed cleanup proposals after a broad codebase assessment.',
'testing': 'Write Vitest coverage for this Fastify response envelope using inject.|Add a repository contract test shared by memory and Postgres adapters.|Fix test teardown so sockets and timers close after a failed assertion.|Add a Testing Library test for the web mutation error state.|Write a Playwright test for this browser session flow.|Test cancellation and stale response ownership in a mobile service hook.|Use disposable Postgres to verify concurrent job claim fencing.',
'trace': 'Trace SessionService.update from its declaration to all entry points.|Build a call tree for this TypeScript symbol across package exports.|Follow argument transformations from the web action to the API repository.|Find callers of this worker handler through the runtime registry.|Trace the mobile service path separately from the web Server Action.|Mark unresolved dynamic callbacks instead of inventing their callers.|Show source evidence for each edge in this import and call graph.',
'triage': 'Prioritize the findings from the completed review before applying fixes.|Walk through which review issues to fix, skip or defer.|Create a fix queue from the selected review findings.|Group review findings by severity for a decision.|Triage this review report and retain the rejected recommendations.|Separate deferred work from the current approved correction scope.|Show evidence for each finding before recording its triage decision.',
'typescript-idioms': 'Use strict TypeScript narrowing for this unknown error value.|Design a discriminated union for these boundary outcomes.|Check Node async resource ownership and shutdown handling.|Choose the correct type-only and emitted ESM import forms.|Refactor floating promises while preserving required operation order.|Explain why a timeout does not prove detached I/O has stopped.|Keep per-instance mutable state isolated across API tests.',
'verify': 'Run the appropriate typechecks, lint and tests for these starter changes.|Verify the affected workspace and its shared-contract consumers.|Choose integration checks after this database migration change.|Run pnpm verify before claiming this task is complete.|Report failed, unavailable and unexecuted verification separately.|Select mobile compatibility checks without claiming browser tests cover native rendering.|Verify package exports with builds when typechecks alone do not exercise packaging.',
'watch-pr': 'Watch this pull request for new review comments and check results.|Monitor PR deltas in the background until a terminal state.|Resume the PR watcher from its saved event cursor.|Watch only the CI checks for this existing pull request.|Request bounded Codex cloud review rounds for the current PR head.|Stop watching when the PR closes or the configured duration expires.|Detect a stale review completion that belongs to an older head commit.',
'work': 'Execute the tasks in this existing implementation plan.|Resume the in-progress plan from its remaining checkboxes.|Continue authorized plan phases with verification after each task.|Start work from task P2-T3 in the saved plan.|Read the scratchpad before implementing the next planned change.|Record a blocker after three failed attempts instead of retrying blindly.|Finish the current plan scope without starting an unrelated review workflow.',
}

NEGATIVE_NEIGHBORS = {
'audit': ['quick','brief','freeze','docs-fetcher','watch-pr'],
'background-jobs': ['react-patterns','docs-fetcher','freeze','pr-review','brief'],
'boundaries': ['drizzle-constraint-debug','watch-pr','freeze','brief','deps-vet'],
'brainstorm': ['work','drizzle-constraint-debug','watch-pr','deps-vet','freeze'],
'brief': ['plan','work','drizzle-n1-check','deps-audit','watch-pr'],
'challenge': ['quick','work','watch-pr','docs-fetcher','compound'],
'codex-loop': ['watch-pr','brief','deps-audit','drizzle-n1-check','init'],
'compound-docs': ['compound','learn-from-fix','quick','plan','watch-pr'],
'compound': ['compound-docs','investigate','work','watch-pr','docs-fetcher'],
'deploy': ['react-patterns','drizzle-n1-check','brief','freeze','deps-vet'],
'deps-audit': ['deps-update','deps-vet','drizzle-patterns','react-patterns','brief'],
'deps-update': ['deps-audit','deps-vet','drizzle-constraint-debug','watch-pr','brief'],
'deps-vet': ['deps-audit','deps-update','review','freeze','docs-fetcher'],
'docs-fetcher': ['document','quick','work','deps-vet','freeze'],
'document': ['docs-fetcher','quick','work','drizzle-n1-check','freeze'],
'domain-resources': ['react-state-audit','deps-vet','watch-pr','freeze','docs-fetcher'],
'drizzle-constraint-debug': ['drizzle-n1-check','react-state-audit','watch-pr','freeze','deps-vet'],
'drizzle-n1-check': ['drizzle-constraint-debug','react-state-audit','deps-vet','watch-pr','brief'],
'drizzle-patterns': ['react-patterns','deps-vet','watch-pr','freeze','brief'],
'examples': ['work','watch-pr','deps-vet','freeze','pr-review'],
'fastify-modules': ['react-patterns','deps-vet','watch-pr','freeze','brief'],
'freeze': ['quick','work','review','deps-audit','watch-pr'],
'full': ['brief','quick','drizzle-constraint-debug','deps-vet','freeze'],
'help': ['work','quick','drizzle-constraint-debug','deps-vet','watch-pr'],
'init': ['intro','help','quick','work','deps-vet'],
'intent-detection': ['work','drizzle-constraint-debug','deps-vet','freeze','watch-pr'],
'intro': ['init','quick','work','drizzle-constraint-debug','deps-vet'],
'investigate': ['plan','brief','deps-vet','freeze','intro'],
'learn-from-fix': ['compound-docs','docs-fetcher','investigate','work','freeze'],
'narrow-catch': ['react-state-audit','drizzle-n1-check','watch-pr','freeze','brief'],
'perf': ['drizzle-constraint-debug','deps-vet','watch-pr','freeze','brief'],
'permissions': ['freeze','work','deps-audit','brief','docs-fetcher'],
'plan': ['work','brief','quick','deps-vet','watch-pr'],
'pnpm-compression': ['verify','deps-update','deps-vet','freeze','brief'],
'pr-review': ['watch-pr','review','deps-audit','freeze','brief'],
'quick': ['plan','research','deps-vet','freeze','watch-pr'],
'react-patterns': ['background-jobs','deps-vet','watch-pr','freeze','brief'],
'react-state-audit': ['drizzle-n1-check','background-jobs','deps-vet','watch-pr','brief'],
'recall': ['compound','quick','work','watch-pr','freeze'],
'research': ['work','quick','deps-vet','freeze','watch-pr'],
'review': ['pr-review','work','watch-pr','deps-vet','brief'],
'runtime-inspection': ['plan','deps-vet','freeze','brief','compound'],
'security': ['react-state-audit','drizzle-n1-check','brief','freeze','watch-pr'],
'techdebt': ['quick','work','drizzle-constraint-debug','deps-vet','watch-pr'],
'testing': ['plan','brief','deps-vet','freeze','watch-pr'],
'trace': ['drizzle-constraint-debug','deps-vet','watch-pr','freeze','brief'],
'triage': ['review','quick','deps-vet','freeze','watch-pr'],
'typescript-idioms': ['brief','deps-vet','watch-pr','freeze','init'],
'verify': ['testing','brief','deps-vet','freeze','watch-pr'],
'watch-pr': ['pr-review','codex-loop','brief','deps-vet','freeze'],
'work': ['plan','brief','review','deps-vet','freeze'],
}


def generate_for_skill(skill_name: str, skill_desc: str, all_descriptions: dict[str, str]) -> dict:
    """Return the offline, reviewable corpus; never call a model by default."""
    if skill_name not in CURATED_POSITIVES or skill_name not in all_descriptions:
        raise ValueError(f'No authored TypeScript trigger cases for {skill_name}')
    positives = CURATED_POSITIVES[skill_name].split('|')
    return {
        'skill': skill_name,
        'description_summary': skill_desc,
        'should_trigger': positives[:5],
        'should_trigger_test': positives[5:],
        'should_not_trigger': [CURATED_POSITIVES[name].split('|')[0] for name in NEGATIVE_NEIGHBORS[skill_name]],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate trigger test prompts")
    parser.add_argument("--skill", help="Generate for one skill only")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    parser.add_argument("--live", action="store_true", help="Opt into paid model generation instead of the offline corpus")
    parser.add_argument("--force", action="store_true", help="Overwrite existing trigger files")
    args = parser.parse_args()

    all_descriptions = get_all_skill_descriptions()
    print(f"Found {len(all_descriptions)} skills")

    if args.skill:
        skills_to_generate = [args.skill]
    else:
        skills_to_generate = sorted(all_descriptions.keys())

    generated = 0
    skipped = 0
    failed = 0

    for skill_name in skills_to_generate:
        trigger_path = os.path.join(TRIGGERS_DIR, f"{skill_name}.json")

        if os.path.isfile(trigger_path) and not args.force:
            skipped += 1
            continue

        if skill_name not in all_descriptions:
            print(f"  SKIP: {skill_name} (no description)")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  Would generate: {skill_name}")
            continue

        print(f"  Generating: {skill_name}...", end=" ", flush=True)
        generator = generate_with_model if args.live else generate_for_skill
        data = generator(skill_name, all_descriptions[skill_name], all_descriptions)

        if data and "should_trigger" in data and "should_not_trigger" in data:
            with open(trigger_path, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            st = len(data["should_trigger"])
            snt = len(data["should_not_trigger"])
            print(f"OK ({st} trigger, {snt} non-trigger)")
            generated += 1
        else:
            print("FAILED")
            failed += 1

    print(f"\nDone: {generated} generated, {skipped} skipped, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
