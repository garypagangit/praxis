"""Blinded semantic label-audit helper for PX-062 Gate 2.2.

This helper reads only the frozen task prompts and adjacent clean registry catalog.
It applies an independently authored, prompt-semantic rule set.  It never reads an
answer key, manifest, seed bank, benchmark configuration, builder, or tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
TASKS = HERE / "frozen_inputs" / "tasks.jsonl"
REGISTRY = HERE / "frozen_inputs" / "registry_catalog.json"
OUTPUT = HERE / "label_audit_2_predictions.jsonl"


def contains(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def classify(prompt: str) -> tuple[str, str, str]:
    """Choose the single best primary workflow from prompt semantics alone."""
    p = prompt.lower()

    # Resolve a few deliberately close Figma/Notion primary-workflow boundaries.
    if "light and dark variable collections" in p:
        return "figma-generate-library", "high", ""
    if "read the spacing and color variables" in p:
        return "figma", "high", ""
    if "application code for this figma screen" in p:
        return "figma-implement-design", "high", ""
    if "pre-read for tomorrow's review" in p:
        return "notion-meeting-intelligence", "high", ""

    # Narrow workflows precede broader workflows where their vocabulary overlaps.
    rules: list[tuple[str, tuple[str, ...]]] = [
        ("gh-fix-ci", ("ci logs", "failing github", "github actions", "pr checks", "workflow failure", "failing checks", "actions checks are red", "failed build check", "github-hosted ci", "unit-test job", "workflow error", "check logs")),
        ("gh-address-comments", ("pull request feedback", "review feedback", "review comments", "review conversations", "requested changes", "review threads", "open pull request", "actionable inline comment", "actionable issue comments", "pr comments", "reviewers on this branch")),
        ("yeet", ("stage, commit", "staging, commit", "commit, push", "commit everything", "draft pr", "draft review", "create a github pull request", "open the repository's pull request", "complete github publishing workflow", "publish the current work to github", "take these finished edits through staging", "stage my changes", "one-command repository publication")),
        ("figma-code-connect-components", ("code connect", "mapping between a figma component", "map this figma", "link the design library", "connect this component", "matching react component", "component to its implementation", "mappings between these figma", "mapping file that associates", "design variants to the correct code")),
        ("figma-create-design-system-rules", ("design system rules", "project-specific rules", "conventions for token names", "design system guidance tailored", "design-to-code handoff", "translating our figma library", "coding conventions for developers implementing screens", "design translation guidelines", "rules that keep figma implementations", "rules file for future figma-to-code", "custom rules for spacing")),
        ("figma-create-new-file", ("blank figma", "new figma", "new figjam", "empty figma", "start a new design file", "create a new design file", "create the empty figma", "new design file with the name", "empty design document", "fresh figma file")),
        ("figma-generate-library", ("tokens and components in figma", "component library in figma", "figma component library", "design system in figma from", "figma library from our code", "figma variables and components", "reconcile our code tokens", "build a reusable figma library", "theme files", "complete design-system library", "typography, color, and spacing foundations", "coded components and the figma library", "modernize an existing figma library", "professional figma design system", "component variants to our professional")),
        ("figma-generate-design", ("figma screen", "editable figma design", "page into figma", "screen into figma", "recreate this product page", "update the existing figma screen", "landing page implementation into", "application code into a figma", "build this page in figma", "structured figma frame", "assemble a settings screen", "responsive checkout screen in figma", "analytics dashboard in figma", "onboarding flow in figma", "multi-section layout in figma")),
        ("figma-implement-design", ("figma specification", "figma specs", "figma design in code", "figma design into", "implement this figma", "match the figma", "from this figma", "design into production", "component so it matches", "supplied figma frame", "figma flow into production", "figma component in our application", "page to its figma frame", "provided design variants as reusable code")),
        ("figma-use", ("programmatically add variables", "bind them to fills", "figma canvas", "create nodes in the open figma", "edit nodes in the open figma", "use_figma", "modify auto-layout", "inspect file structure programmatically", "canvas-context script", "javascript bridge", "unique canvas read", "active figma document", "selected figma nodes", "delete obsolete canvas nodes")),
        ("figma", ("figma node url", "retrieve the design context", "fetch design context", "figma mcp", "inspect this figma", "figma assets", "figma screenshot", "assets and layout information from a figma", "variables and image assets", "figma connection", "figma integration", "design context from these figma", "screenshot of the specified figma")),
        ("aspnet-core", ("asp.net", "blazor", "razor pages", "minimal api", "mvc application", "controller routes", "signalr", "grpc service", ".net web", "c# web backend", "c# web service", "middleware and configuration")),
        ("chatgpt-apps", ("chatgpt app", "apps sdk", "mcp server and widget", "mcp apps bridge", "widget ui", "register ui resource", "chatgpt interface", "server-backed chatgpt widget", "widget resource", "chatgpt widget")),
        ("cli-creator", ("composable cli", "command-line tool", "command line tool", "terminal client", "cli from", "openapi spec into a cli", "stable json commands", "create a cli", "command line program", "api client that can be piped", "api cli", "json-emitting command line", "run from any repository", "installable command line interface", "curl examples in a reusable terminal tool")),
        ("cloudflare-deploy", ("cloudflare", "worker to its kv", "workers and pages", "wrangler configuration", "publishes a worker", "pages build")),
        ("define-goal", ("measurable goal", "measurable objective", "quantitative outcome", "clarify success criteria", "narrow this objective", "progress can be evaluated numerically", "vague intention", "time-bounded outcome", "clear success criteria", "goal workflow", "quantitative goal", "fuzzy project idea", "what success should mean")),
        ("hatch-pet", ("codex pet", "pet spritesheet", "pet.json", "pet animations", "animated pet", "pet atlas", "mascot pet", "eight-by-nine animation", "lightweight mascot", "qa contact sheet for every animation")),
        ("imagegen", ("generate a watercolor", "generate an image", "create an illustration", "marketing mockup", "remove the background", "replace it with transparency", "edit this image", "product image", "raster image", "transparent-background", "visual variants", "edit the attached photo", "seamless stone texture", "rough sketch into a polished raster")),
        ("jupyter-notebook", ("jupyter notebook", "experimental notebook", "notebook that demonstrates", "notebook for exploring", ".ipynb", "ipynb file", "add visualization and conclusion sections to my experimental notebook", "experiment notebook", "reproducible notebook", "research notebook", "analysis notes into a structured jupyter")),
        ("linear", ("linear issue", "linear ticket", "linear project", "open linear", "issues associated with", "linear sprint", "linear tasks", "search linear")),
        ("migrate-to-codex", ("migrate the project's mcp", "use codex instead", "convert our existing agent", "migrate to codex", "codex project and global files", "current agent configuration", "instruction files into codex", "codex-compatible skills", "move this repository's supported instruction", "migrate instruction, skill, and mcp", "global agent setup", "assistant configuration to codex")),
        ("netlify-deploy", ("netlify",)),
        ("notion-knowledge-capture", ("notion wiki", "capture this decision", "turn these notes into", "notion faq", "structured notion page", "document this conversation", "structured notion how-to", "how-to in notion", "notion knowledge base", "record the team's process", "reusable knowledge in notion", "architecture decision in notion", "notion reference guide")),
        ("notion-meeting-intelligence", ("meeting materials", "drafting the agenda", "draft an agenda", "meeting pre-read", "planning session", "tailor the agenda", "summarize prior decisions before", "attendee-specific briefing", "decision-focused pre-read", "agenda using", "executive meeting brief", "talking points for a customer meeting")),
        ("notion-research-documentation", ("research across notion", "notion workspace and", "stored in our notion", "notion sources", "proposals stored", "synthesize the findings", "compare the proposals", "multiple notion databases", "workspace and publish the synthesis", "notion pages and produce", "information distributed across notion", "links back to every supporting notion", "notion records and document")),
        ("notion-spec-to-implementation", ("notion spec", "notion prd", "progress tracking in notion", "implementation plan and tasks", "implementation described by this document", "turn this prd", "feature spec into", "product specification into", "engineering work required by this prd", "feature document in notion", "requirements into a sequenced plan", "progress states")),
        ("openai-docs", ("openai model", "openai endpoint", "openai api", "codex itself", "official openai", "first-party documentation", "current openai", "build with openai", "model upgrade", "openai client library", "openai reasoning request", "official api reference")),
        ("pdf", ("pdf",)),
        ("playwright-interactive", ("js_repl", "persistent browser", "electron interaction", "iterative ui debugging", "keep the browser session", "browser session open", "interactive browser session", "long-lived browser", "persistent javascript browser", "electron application without restarting", "preserving cookies", "persistent page handles", "browser interactively", "interactive browser repl", "changing application state")),
        ("playwright", ("browser test", "automate a real browser", "terminal-driven browser", "end-to-end flow", "browser automation", "playwright", "clicking through the site", "website's sign-in flow", "local web application's navigation", "file upload and download behavior", "dynamically loaded browser element")),
        ("plugin-creator", ("plugin manifest", "plugin directory", "plugin i am developing", ".codex-plugin", "marketplace.json", "local plugin", "scaffold a plugin", "plugin structure", "mcp server folder and skill directory", "codex plugin", "package several codex capabilities", "personal codex plugin", "plugin ordering and availability")),
        ("render-deploy", ("render.yaml", "render blueprint", "deploy to render", "render dashboard", "host on render", "web service on render", "project to render", "repository onto render", "render build", "render deployment", "deploy the application to render")),
        ("screenshot", ("operating-system-level screenshot", "os-level screenshot", "full-screen screenshot", "capture a specific app window", "pixel region screenshot", "app has no capture feature", "entire windows desktop", "focused application window", "visible error dialog", "only the browser window", "rectangular region", "lower-right portion of the display", "full-screen snapshot", "screen capture")),
        ("security-best-practices", ("security best practices", "security improvements", "secure-by-default", "security review of this python", "security review of this go", "security review of this javascript", "security-focused code review", "common input validation and authorization", "secure coding mistakes", "security best-practices", "secure coding guidance", "security review report", "unsafe secrets handling and injection", "typescript api implementation")),
        ("security-ownership-map", ("security ownership", "security-focused ownership", "bus factor", "sensitive-code ownership", "orphaned sensitive code", "codeowners reality", "ownership topology", "security maintainers", "ownership clusters", "single-maintainer hotspots", "who owns the security-sensitive", "developers who actually modify sensitive", "likely maintainers of sensitive", "people-to-file ownership")),
        ("security-threat-model", ("threat model", "trust boundaries", "abuse cases", "abuse paths", "attacker capabilities", "trust-boundary crossings", "misuse scenarios", "appsec threat-modeling", "document threats")),
        ("sentry", ("sentry",)),
        ("skill-creator", ("reusable codex skill", "create a new skill", "new codex skill", "update an installed skill", "extend this skill", "skill.md", "turn this operating procedure into", "author a skill", "existing skill definition", "specialized skill", "skill package that extends", "scope, triggers, and fallback", "references and scripts to a skill", "domain knowledge")),
        ("skill-installer", ("install a skill", "installable skills", "skills from github", "curated skill", "skill from another repo", "add this skill to codex", "curated installation choices", "skill from the github repository", "supported skill package", "private-repository skill", "approved skill bundle", "skills that can be installed", "named codex skill from its repository", "skill from the available catalog")),
        ("speech", ("voiceover", "text-to-speech", "spoken versions", "audio narration", "narrate this", "speech generation", "narrated audio", "lesson scripts into voice files", "openai audio service", "render this announcement as speech", "audio reading")),
        ("transcribe", ("transcript", "transcribe", "spoken content", "voice recording", "speaker hints", "known-speaker", "meeting audio", "recording to text", "spoken text", "podcast episode into readable text")),
        ("vercel-deploy", ("vercel",)),
        ("winui-app", ("winui", "windows app sdk", "xaml desktop", "windows desktop application", "communitytoolkit components")),
    ]

    for skill, needles in rules:
        if contains(p, *needles):
            return skill, "high", ""
    return "NONE", "high", ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--show-none", action="store_true")
    parser.add_argument("--show-skill")
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    names = set(registry["names"])
    rows = [json.loads(line) for line in TASKS.read_text(encoding="utf-8").splitlines()]
    predictions = []
    for row in rows:
        skill, confidence, note = classify(row["prompt"])
        if skill != "NONE" and skill not in names:
            raise ValueError(f"unregistered prediction: {skill}")
        predictions.append({
            "task_id": row["task_id"],
            "predicted_skill": skill,
            "confidence": confidence,
            "note": note,
        })

    counts = Counter(r["predicted_skill"] for r in predictions)
    print(f"tasks={len(rows)} unique_ids={len({r['task_id'] for r in rows})}")
    print("tasks_sha256=" + hashlib.sha256(TASKS.read_bytes()).hexdigest())
    print("registry_sha256=" + hashlib.sha256(REGISTRY.read_bytes()).hexdigest())
    print("prediction_counts=" + json.dumps(dict(sorted(counts.items())), sort_keys=True))
    if args.show_none:
        for task, pred in zip(rows, predictions):
            if pred["predicted_skill"] == "NONE":
                request = task["prompt"].split("User request:", 1)[-1].split("\n", 1)[0]
                print(f"{task['task_id']}\t{request}")
    if args.show_skill:
        for task, pred in zip(rows, predictions):
            if pred["predicted_skill"] == args.show_skill:
                request = task["prompt"].split("User request:", 1)[-1].split("\n", 1)[0]
                print(f"{task['task_id']}\t{request}")
    if args.write:
        with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
            for pred in predictions:
                handle.write(json.dumps(pred, ensure_ascii=False, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
