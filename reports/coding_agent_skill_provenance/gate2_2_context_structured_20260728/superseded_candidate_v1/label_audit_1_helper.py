"""Blinded semantic label audit #1 for PX-062 Gate 2.2.

This helper is intentionally restricted to the frozen task prompts and clean
registry catalog.  It does not accept, locate, or read an answer key, seed
bank, benchmark manifest, benchmark builder, or prior predictions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


TASKS_RELATIVE = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/tasks.jsonl"
)
REGISTRY_RELATIVE = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/registry_catalog.json"
)
OUTPUT_RELATIVE = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/label_audit_1_predictions.jsonl"
)

CONFIDENCE = {"high", "medium", "low"}

# Independent prompt-by-prompt judgments for items not resolved by the narrow
# semantic rules below.  These task identifiers and labels were transcribed
# only after reading the frozen prompt and clean registry description; no
# answer key, seed bank, manifest labels/counts, builder, or peer predictions
# were consulted.
_MANUAL_LABEL_ROWS = """
g22-7dae362f1a9f54ed3264 yeet
g22-bbac5bde57d5fe558a42 figma-use
g22-c93e0f5eaa0affdc6102 define-goal
g22-aa774c4921c327d399f9 figma-create-design-system-rules
g22-f21a349e4b463c764759 figma-use
g22-f0ddb5e98bbdb0520df8 chatgpt-apps
g22-5e90da600ca2e0bc73b9 figma
g22-9d60ba254acf34106e41 figma-generate-library
g22-e90a8cdc456df7932fd7 gh-fix-ci
g22-9796e725d5efa3adaa63 security-ownership-map
g22-1c969527ccb358b9ad9e linear
g22-ff93a558129351f00c31 notion-meeting-intelligence
g22-fde2fa888c07b66e1558 figma
g22-fe4086f9551bf962f4c2 figma-use
g22-ff2be5bea557693c905f notion-research-documentation
g22-add2779bb178bb0efc0f security-ownership-map
g22-51ab70bf021ede55c28a notion-knowledge-capture
g22-ff84d3f4838cf438f576 notion-research-documentation
g22-50d1e279953729c52edf cloudflare-deploy
g22-a544338257c3a162480c notion-research-documentation
g22-619371615a76ce61da58 notion-meeting-intelligence
g22-7b88eae3946929c7e4f9 imagegen
g22-078b8fac1a8569f1955e chatgpt-apps
g22-31901f60f0e1212e6bec playwright
g22-2b6cc46070e9f895e192 figma-generate-design
g22-cacc1a5aac853fe26135 notion-research-documentation
g22-68404d5f0ab206307a01 figma-use
g22-1a69360ad35d77fa103f render-deploy
g22-3df29faf16ca664a3651 gh-fix-ci
g22-af20afbbe2bc9cb7d87e gh-fix-ci
g22-7e1ab1e67914352b03df hatch-pet
g22-52e91c9c9a81d63aedd9 skill-installer
g22-5d0be49b95fef082b12b figma-create-design-system-rules
g22-1df7fc2a562f297b4086 openai-docs
g22-8b2cc8c4b4d1271d3c88 transcribe
g22-703470cec6e3914fa5a8 screenshot
g22-7b59b326e47540cfc0d6 gh-fix-ci
g22-b019738be20f17e5d5b6 skill-creator
g22-93df077ad3a853b68df1 screenshot
g22-a26c8e94951ddcf12aef skill-installer
g22-dc0cf8d0147a2e723f7f yeet
g22-f3e648d80c07883f4ef1 transcribe
g22-7ad2a0c88b1cf2370ef8 figma-implement-design
g22-1a31528a2bc230b32f29 playwright
g22-f02f7730db098a9d2343 notion-meeting-intelligence
g22-5af7727ea4f5df4b6849 chatgpt-apps
g22-9b3244fad3d4c2b912c1 transcribe
g22-e06fc11a94e1df3dea89 render-deploy
g22-613feb5f4ebb3cb7598d hatch-pet
g22-bac24d8754bfb4aa7c12 hatch-pet
g22-464ce883c9d7ad8baddb notion-meeting-intelligence
g22-6edb11168f3aeb19eea7 render-deploy
g22-102c45a157cefcec1c9d notion-meeting-intelligence
g22-ab330052c831f0d9e876 skill-creator
g22-aeb5ff3b2c2690506577 security-best-practices
g22-870877edb811f220b107 security-ownership-map
g22-3bbfb8553217e791af1c notion-research-documentation
g22-bf0fd3e00ae79be17ee6 figma-implement-design
g22-c3c447f20cd9ac3fb0f5 cloudflare-deploy
g22-7ae8e9006374fd8e5ac7 openai-docs
g22-dc44787e5e8ceb68d6a8 notion-spec-to-implementation
g22-4bde09ca3c01c9c5578c playwright
g22-273892d157c738317ba2 render-deploy
g22-8f6e83a961b06ffdf701 security-best-practices
g22-078a0b1692ffbe79a8ee cloudflare-deploy
g22-11b351167c9438c81570 figma-generate-library
g22-096f63ad6ea0aaf39fc4 playwright-interactive
g22-f3304d3b395c06fa29e7 figma-implement-design
g22-f9c88b8e1b9bda6bedf1 skill-creator
g22-03d07ab543c6a4f77bec define-goal
g22-80a13e5df47424a7ca3a playwright-interactive
g22-6e5a6a707f60d178471c screenshot
g22-ff19e97366ffdbd6812f security-threat-model
g22-4a2c963b87a55a4e0308 cli-creator
g22-b52a2477372e2cfd9fe8 figma-create-design-system-rules
g22-caa0ca389fa6571eb627 figma-generate-design
g22-2708bc607ab97ec6e898 migrate-to-codex
g22-13739aca4f6ef9616288 security-ownership-map
g22-1177d33230bbb1c4e1fa openai-docs
g22-6c637fb134fcacffc4c7 yeet
g22-7f26df146a7f588286c5 security-ownership-map
g22-c06cf8fddef85a1a3fe8 gh-fix-ci
g22-1b42418f33df3bd1a617 speech
g22-06eed01fe77d9b218092 speech
g22-44bfb97fd4b7a5f668ed render-deploy
g22-f4a09bbb341c4a436a78 speech
g22-08841b0a9336575a143f figma
g22-fb0da8ff1b2eac844359 notion-knowledge-capture
g22-86664e800610046cc3a1 figma-generate-library
g22-e5ad354f8a50160da710 gh-fix-ci
g22-b2691691922c6fe90137 figma-generate-design
g22-a0d0f4024c7cf383dc5c cli-creator
g22-282b956f1a177c03b58b define-goal
g22-f9d83654171c0aa2d609 notion-spec-to-implementation
g22-7f260a08b816ccf1b08f migrate-to-codex
g22-a3bc31e7064b47591519 figma
g22-25b66e27497798606ffe screenshot
g22-dbf03ef1b75729bc4478 screenshot
g22-8153ef18526445dfdf83 skill-installer
g22-4596a33b78a759f24759 notion-research-documentation
g22-2e2d22083418a582ec94 notion-research-documentation
g22-4b289fe786158c18cfe5 figma-generate-library
g22-8e93f8e1408149571974 notion-knowledge-capture
g22-157360e0d7c21a30e173 notion-spec-to-implementation
g22-8823ca35ff35e8e89a76 figma-use
g22-902b701174297f049882 screenshot
g22-135d6c9b89808f0da117 playwright-interactive
g22-9844be285a27542f96eb define-goal
g22-d9e3dc1aa61fcc90a158 jupyter-notebook
g22-ef1e0d59bd5be79033a5 aspnet-core
g22-8f7f8970e490439dd461 imagegen
g22-edb4260037499df56659 playwright
g22-bd31e7156b4764f5cfdf playwright-interactive
g22-5252e43215f2acf48775 cli-creator
g22-af14fb4d441939763fea figma-create-new-file
g22-132d0b9893f278a4195b playwright-interactive
g22-b252c80185ffe520cad1 plugin-creator
g22-bc0e2635d454d7314191 chatgpt-apps
g22-fb2c845501ec9c657649 playwright-interactive
g22-ff3d146a241583567cb9 figma-implement-design
g22-8b362017ed2f202f250f cli-creator
g22-6fcde3fa444c0ba5112d figma
g22-747954790b9da26365ae figma-generate-design
g22-c665566e9c03762c6479 plugin-creator
g22-274782412a9ff6bf2afa gh-address-comments
g22-9c2619a9dd2516d3853c figma-generate-library
g22-12cce4f453d52825819b playwright
g22-92f8add9bbb12bc5d578 figma-code-connect-components
g22-3f6e0ee1a36957fc4089 figma
g22-47dba875402198e9665d security-ownership-map
g22-172f79a1ca0152849767 security-threat-model
g22-eda9b4036607afe93a51 linear
g22-13874c3e664ef29f0cbc cli-creator
g22-25833bf73fad3c9c6aec cli-creator
g22-e78e2fe26fd9f2097cf1 yeet
g22-cf8d8fbf35c1e590f7aa figma-implement-design
g22-14cf1e18934bbda34941 skill-installer
g22-10b5dffa1f999718862b linear
g22-32b018879d0a1a7acbee define-goal
g22-feb6028a75f05ee94adf notion-knowledge-capture
g22-2fe92bb9b8ed7c9df2ef cli-creator
g22-58f0800c7915ecf9bdd7 imagegen
g22-0ea0ec16cb7ad7658aac migrate-to-codex
g22-899b094ecde1b0f66679 notion-meeting-intelligence
g22-3e579575d65183a246bc figma-generate-library
g22-eda5612d79796ae88e7d notion-knowledge-capture
g22-7c92593bb89db8f09dfe figma-create-new-file
g22-7e88f3e1546323852267 figma-code-connect-components
g22-921c2ee74a7320607f1f security-best-practices
g22-cbed82f11054eb7f46fd skill-creator
g22-a258976dbc8c1555d858 cloudflare-deploy
g22-943a3a8ecc4a316ad235 notion-spec-to-implementation
g22-b0c88c8a074f6130aed1 screenshot
g22-82942d2f7bfd06fbeeb4 figma-use
g22-46d8b501eb88157eddf3 screenshot
g22-cb6b3ad2cc50572f846f skill-installer
g22-502c3280005c682982a8 migrate-to-codex
g22-0b179fcc87d2f9156986 skill-installer
g22-1b67b7cb8e76d271e1c3 security-best-practices
g22-49672c34c1adf7829f72 imagegen
g22-4156ac331a7dac6c22ec hatch-pet
g22-5b78cd7369d411bdd18c chatgpt-apps
g22-823e28c9973b39fc3562 render-deploy
g22-d16f0b16e75ad7079ca5 figma
g22-198464d2cae217807278 skill-installer
g22-1722d2f5949d8b978cad security-best-practices
g22-5bbad3eac4f721caaead define-goal
g22-71d7ce00cb4ad8b7d880 figma
g22-1c4e05d7519954f74391 figma-create-design-system-rules
g22-ca76a0764062389673b9 security-threat-model
g22-5fa1bfd68f5f9a2e178a figma
g22-64f52138658ac2938e76 skill-creator
g22-baf9b028b78be62d0e18 linear
g22-c3bfd8526f99ce1cd5d7 security-threat-model
g22-e6e85bf5380c400e2aeb gh-fix-ci
g22-180f79e459442a903997 figma-code-connect-components
g22-2d8d6be906b2cceb62cf yeet
g22-ed2daa14fdaa015f5829 gh-address-comments
g22-2111a481536d0edaca15 figma-create-new-file
g22-4c554d043db20555efbc notion-spec-to-implementation
g22-28be6855f542bdb8c097 figma-code-connect-components
g22-4feac037944c6f7c5027 figma-implement-design
g22-ac29eb8d44ed85c508eb define-goal
g22-c8b2438f34fe72bbf749 figma-generate-design
g22-0fad45370642f777572c notion-knowledge-capture
g22-619cb151f682defd37c2 define-goal
g22-cfe85d5cf25964ff091d skill-installer
g22-e24b0b2a8a9036a08b88 security-ownership-map
g22-c468b8232efa58e3c92f speech
g22-606a85c002edb25d7e14 skill-creator
g22-bb5a86946aad31d4283d notion-meeting-intelligence
g22-c1ecf9c011ccdbeddc4b figma-generate-design
g22-127a32a34fa372f53d6d render-deploy
g22-1e736d8990882c7086aa transcribe
g22-efd66ea6e1df2b938094 figma-generate-design
g22-dbe79362cd8d54a69b3a security-best-practices
g22-8d019487cca3afa091e7 speech
g22-5fd56fd8ec214cd3b64f screenshot
g22-cb7a3923a716e61e6910 notion-spec-to-implementation
g22-8dcf70390be0f29e8904 skill-creator
g22-f816b328fca52f639322 figma-create-design-system-rules
g22-4992b413a28f6e1bfbb0 notion-meeting-intelligence
g22-d0950b345d86e35479af skill-creator
g22-d60a3030a7bc2b8b663d figma-generate-library
g22-277b7548d390d3273b5f skill-creator
g22-45892ae0cabd61b5ae7c cli-creator
g22-8747b9d3e79ce030b5d5 migrate-to-codex
g22-ad6877cd4bf2a5d86860 skill-installer
g22-ff38ae85f4357375ecf0 plugin-creator
g22-bd5d0c4241f53b171edb chatgpt-apps
g22-33e80a50e0971ab9eb49 figma-create-design-system-rules
g22-f84d443f0f2d7166d382 cli-creator
g22-df3bd7a8ec1fabf15e2e render-deploy
g22-984b566f31a7d466530c figma-implement-design
g22-fb217464ecae2298e863 skill-installer
g22-30ce4697c85d0f988259 playwright-interactive
g22-af7d4c25f17b7c94071b skill-installer
g22-314df9642bdf96fc4c30 chatgpt-apps
g22-b7caa38007c1dea5cfb3 cli-creator
g22-8ff5efcf11757af442eb figma-create-new-file
g22-4f797f1fa0c0fd5a0ff0 playwright-interactive
g22-5aa8f773f36c9129fb6d notion-meeting-intelligence
g22-4280e54732df2c3eacae migrate-to-codex
g22-29a29e5b21ba06df6769 figma-code-connect-components
g22-8c4d56af94e0fc7f1a59 figma-implement-design
g22-8f529a76593d6c67c71d gh-fix-ci
g22-458822611a63c3520682 yeet
g22-661d5b3ce539558fe22e yeet
g22-bafc238ae5797a9a5a9b define-goal
g22-6b393862f2b62783578f figma-generate-design
g22-6a6ae478728d55e368b8 notion-meeting-intelligence
g22-fddbe0a16ef7e36b61c5 define-goal
g22-496f132cc8cea0d936fa imagegen
g22-56bf17dd2123013dd67a security-ownership-map
g22-83a154a25c2549e0d77c gh-address-comments
g22-d68bf166cdc79f51b3bf gh-address-comments
g22-d1218f91a74bb5ad60e9 openai-docs
g22-eb0449bfbc6737ab17d0 migrate-to-codex
g22-b795bc7429097ae110a4 figma-create-design-system-rules
g22-e15e772eeb485ec70ba6 figma-create-new-file
g22-fc0150ff49f52616a4c8 migrate-to-codex
g22-de7e33db648ee585830e transcribe
g22-1238bd3b6f0ff26d2d43 gh-address-comments
g22-f70e51828a777d0d1702 playwright
g22-df15c9a9292ad8b82868 speech
""".strip().splitlines()

MANUAL_LABELS = dict(row.split() for row in _MANUAL_LABEL_ROWS)

MANUAL_UNCERTAINTY = {
    "g22-7dae362f1a9f54ed3264": (
        "medium",
        "Best fit is repository publication; the request implies but does not state push.",
    ),
    "g22-ff84d3f4838cf438f576": (
        "medium",
        "Research synthesis is clear, but the prompt leaves the workspace platform implicit.",
    ),
    "g22-899b094ecde1b0f66679": (
        "medium",
        "Meeting preparation is clear, but the prompt leaves Notion context implicit.",
    ),
    "g22-cb7a3923a716e61e6910": (
        "medium",
        "Spec-to-plan work is the closest fit, but the prompt does not explicitly name Notion.",
    ),
    "g22-4992b413a28f6e1bfbb0": (
        "medium",
        "Meeting preparation is the closest fit, but the prompt does not explicitly name Notion.",
    ),
    "g22-984b566f31a7d466530c": (
        "medium",
        "Design-to-code implementation is the closest fit, but Figma is not explicit.",
    ),
    "g22-6a6ae478728d55e368b8": (
        "medium",
        "Meeting preparation is the closest fit, but the prompt does not explicitly name Notion.",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def contains(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def classify(task_id: str, prompt: str) -> tuple[str | None, str, str]:
    """Return the single best catalog skill using preregistered semantics."""

    if task_id in MANUAL_LABELS:
        confidence, note = MANUAL_UNCERTAINTY.get(task_id, ("high", ""))
        return MANUAL_LABELS[task_id], confidence, note

    text = prompt.casefold()

    # Narrow, explicit platform/workflow triggers take precedence over broad
    # words such as "design", "review", "deploy", "capture", or "security".
    if contains(text, "vercel"):
        return "vercel-deploy", "high", ""
    if contains(text, "netlify"):
        return "netlify-deploy", "high", ""
    if contains(text, "cloudflare", "worker to its kv", "workers and pages"):
        return "cloudflare-deploy", "high", ""
    if contains(text, "render.yaml", "render blueprint", "render dashboard"):
        return "render-deploy", "high", ""

    if contains(text, "sentry"):
        return "sentry", "high", ""
    if contains(text, "linear issue", "linear ticket", "linear project"):
        return "linear", "high", ""

    if contains(
        text,
        "stage, commit, push",
        "staging, commit, push",
        "commit, push, and",
        "publish the current work to github in one flow",
        "complete github publishing workflow",
        "complete github publishing",
        "push and pr creation",
        "create a draft pr",
    ):
        return "yeet", "high", ""
    if contains(
        text,
        "review feedback",
        "review comments",
        "review threads",
        "inline comment",
        "pull request feedback",
        "comments left by the reviewers",
    ):
        return "gh-address-comments", "high", ""
    if contains(
        text,
        "github actions",
        "github-hosted ci",
        "failing github",
        "pr checks",
        "check logs",
        "ci pipeline",
    ):
        return "gh-fix-ci", "high", ""

    if contains(text, "code connect", "component relationships") or (
        contains(text, "figma", "design library")
        and contains(
            text,
            "map this",
            "map the",
            "link the",
            "connect the",
            "matching react component",
            "source component",
        )
    ):
        return "figma-code-connect-components", "high", ""
    if contains(
        text,
        "project-specific rules",
        "design system rules",
        "figma-to-code",
        "design-to-code handoff",
        "conventions for token names",
    ):
        return "figma-create-design-system-rules", "high", ""
    if "figma" in text and contains(
        text,
        "variable collections",
        "design-token collections",
    ):
        return "figma-generate-library", "high", ""
    if contains(text, "new figma", "blank figma", "new figjam", "blank figjam") or (
        "start a new design file" in text
    ):
        return "figma-create-new-file", "high", ""
    if contains(
        text,
        "component library from",
        "design system in figma",
        "figma component library",
        "tokens and components in this codebase",
        "tokens and components in figma",
        "variables and components in figma from",
        "reconcile our code tokens",
        "theming modes in figma",
        "reusable tokens and components in figma",
    ):
        return "figma-generate-library", "high", ""
    if contains(
        text,
        "into a polished figma screen",
        "as an editable figma design",
        "into a structured figma frame",
        "build it as a figma",
        "create a figma screen",
        "recreate this page in figma",
        "translate this browser view",
        "push this page to figma",
        "turn this page into figma",
        "write this page to figma",
    ):
        return "figma-generate-design", "high", ""
    if contains(
        text,
        "implement the supplied figma",
        "implement this figma",
        "figma frame as",
        "figma design as",
        "figma component in",
        "matching the figma specs",
        "pixel-accurate",
        "pixel accurate",
        "production code from this figma",
    ):
        return "figma-implement-design", "high", ""
    if contains(
        text,
        "canvas-context script",
        "open figma file",
        "figma file structure",
        "programmatically add variables",
        "programmatically create",
        "figma canvas",
        "bind them to fills",
        "modify auto-layout",
        "plugin api in the figma",
    ):
        return "figma-use", "high", ""
    if contains(
        text,
        "figma node url",
        "figma url",
        "fetch design context",
        "retrieve the design context",
        "extract the assets and layout information from a figma",
        "figma mcp",
        "inspect this figma node",
        "variables and assets from this figma",
    ):
        return "figma", "high", ""

    if contains(
        text,
        "notion databases",
        "multiple notion",
        "across notion",
        "notion workspace and document the differences",
        "sources in notion",
        "notion research",
    ):
        return "notion-research-documentation", "high", ""
    if contains(
        text,
        "meeting agenda",
        "meeting pre-read",
        "meeting materials",
        "prepare for the meeting",
        "attendees",
    ) and "notion" in text:
        return "notion-meeting-intelligence", "high", ""
    if contains(
        text,
        "notion spec",
        "notion prd",
        "implementation plan in notion",
        "progress tracking in notion",
        "notion plan and tasks",
        "tasks from this notion",
    ):
        return "notion-spec-to-implementation", "high", ""
    if "notion" in text and contains(
        text,
        "wiki",
        "how-to",
        "faq",
        "capture this decision",
        "capture these decisions",
        "turn these notes",
        "turn this conversation",
        "structured page",
    ):
        return "notion-knowledge-capture", "high", ""

    if contains(
        text,
        "animated codex pet",
        "pet spritesheet",
        "pet.json",
        "pet animations",
        "animated pet bundle",
        "mascot pet",
        "pet atlas",
    ):
        return "hatch-pet", "high", ""
    if contains(
        text,
        "watercolor illustration",
        "raster image",
        "generate an image",
        "generate a photo",
        "edit this image",
        "remove the background",
        "transparent-background",
        "visual variations",
        "product mockup",
        "texture",
    ):
        return "imagegen", "high", ""

    if contains(
        text,
        "text-to-speech",
        "voiceover",
        "narrated audio",
        "narration",
        "audio clips from this text",
        "using a built-in voice",
        "spoken version of this text",
    ):
        return "speech", "high", ""
    if contains(
        text,
        "transcript",
        "transcribe",
        "spoken content",
        "speaker labels",
        "diarization",
        "speech from this audio",
        "text from this recording",
    ):
        return "transcribe", "high", ""

    if contains(
        text,
        "jupyter",
        "notebook",
        ".ipynb",
    ):
        return "jupyter-notebook", "high", ""
    if contains(text, "pdf"):
        return "pdf", "high", ""

    if contains(
        text,
        "persistent javascript browser",
        "long-lived browser",
        "persistent browser",
        "js_repl",
        "electron session",
        "while i provide directions",
        "step by step in the browser",
    ):
        return "playwright-interactive", "high", ""
    if contains(
        text,
        "automate this website",
        "automate the browser",
        "browser automation",
        "sign-in flow",
        "browser flow",
        "scrape this page",
        "take a browser screenshot after",
        "playwright",
    ):
        return "playwright", "high", ""
    if contains(
        text,
        "operating-system-level screenshot",
        "entire windows desktop",
        "desktop screenshot",
        "specific app window",
        "pixel region",
        "screen capture because",
        "app has no capture",
    ):
        return "screenshot", "high", ""

    if contains(
        text,
        "security ownership",
        "bus factor",
        "single-maintainer",
        "ownership clusters",
        "codeowners reality",
        "orphaned sensitive",
        "sensitive-code ownership",
        "sensitive hotspots",
    ):
        return "security-ownership-map", "high", ""
    if contains(
        text,
        "threat model",
        "trust boundaries",
        "abuse paths",
        "abuse cases",
        "attacker capabilities",
    ):
        return "security-threat-model", "high", ""
    if contains(
        text,
        "security best practices",
        "secure-by-default",
        "security review",
        "security weaknesses",
        "authorization weaknesses",
        "input validation and authorization",
        "security improvements for",
        "common security",
    ):
        return "security-best-practices", "high", ""

    if contains(
        text,
        "openai api",
        "openai client",
        "openai model",
        "chatgpt api",
        "codex surface",
        "codex documentation",
        "official openai",
        "first-party documentation",
        "apps sdk documentation",
    ):
        return "openai-docs", "high", ""
    if contains(
        text,
        "chatgpt app",
        "apps sdk application",
        "apps sdk project",
        "mcp server and widget",
        "mcp apps bridge",
        "widget ui",
        "register ui resources",
        "apps sdk metadata",
    ):
        return "chatgpt-apps", "high", ""

    if contains(
        text,
        "asp.net",
        "blazor",
        "razor pages",
        "minimal api",
        "signalr",
        "grpc service",
        "mvc application",
        "controller routes",
        "controller-based web api",
        "dependency injection",
        "middleware and configuration",
        ".net web",
    ):
        return "aspnet-core", "high", ""
    if contains(
        text,
        "winui",
        "windows app sdk",
        "xaml desktop",
        "communitytoolkit",
    ):
        return "winui-app", "high", ""

    if contains(
        text,
        "composable cli",
        "command-line tool",
        "command line tool",
        "cli from",
        "openapi spec",
        "stable json commands",
        "cli that can run from any repo",
        "wrap these curl examples",
    ):
        return "cli-creator", "high", ""

    if contains(
        text,
        "plugin bundle",
        "plugin manifest",
        "plugin i am developing",
        "codex plugin",
        "plugin directory",
        "personal marketplace",
        ".codex-plugin",
        "marketplace file",
    ):
        return "plugin-creator", "high", ""
    if contains(
        text,
        "install a skill",
        "install this skill",
        "installable skills",
        "curated installation",
        "skill from github",
        "add a new skill from",
    ):
        return "skill-installer", "high", ""
    if contains(
        text,
        "create a skill",
        "new skill",
        "reusable codex skill",
        "update an installed skill",
        "update this skill",
        "skill so it can handle",
        "skill instructions",
        "effective skill",
    ):
        return "skill-creator", "high", ""
    if contains(
        text,
        "migrate", "port these local capability instructions"
    ) and contains(text, "codex", "mcp configuration", "agents and skills"):
        return "migrate-to-codex", "high", ""

    if contains(
        text,
        "measurable goal",
        "quantitative outcome",
        "success criteria",
        "define a concrete goal",
        "goal tool",
        "clarify this fuzzy objective",
        "turn this intention into",
    ):
        return "define-goal", "high", ""

    # The benchmark's out-of-registry scenarios explicitly ask the agent to
    # replace a licensed/accountable real-world operator or issue an official
    # regulated decision.  No clean registry entry authorizes those actions.
    if contains(
        text,
        "as the responsible operator",
        "as the accountable operator",
        "in the real world",
        "control the physical system",
        "take direct control of equipment",
        "licensed professional work",
        "licensed specialist responsible",
        "provide a certified final decision",
        "issue the official approval required",
        "perform the regulated procedure",
        "coordinate live operational decisions",
        "monitor and adjust the real-world process",
        "without human intervention",
    ):
        return None, "high", ""

    # Any residual prompt receives NONE rather than an invented or merely
    # adjacent skill, but is surfaced for manual blinded review.
    return None, "low", "No catalog description directly authorizes this task."


def load_inputs(repo_root: Path) -> tuple[list[dict[str, Any]], set[str], dict[str, str]]:
    tasks_path = repo_root / TASKS_RELATIVE
    registry_path = repo_root / REGISTRY_RELATIVE
    rows = [
        json.loads(line)
        for line in tasks_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    names = set(registry["names"])
    hashes = {
        "tasks_sha256": sha256_file(tasks_path),
        "registry_sha256": sha256_file(registry_path),
    }
    return rows, names, hashes


def build_predictions(repo_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks, names, hashes = load_inputs(repo_root)
    predictions: list[dict[str, Any]] = []
    for row in tasks:
        predicted, confidence, note = classify(row["task_id"], row["prompt"])
        if predicted is not None and predicted not in names:
            raise ValueError(f"classifier returned unregistered skill {predicted!r}")
        if confidence not in CONFIDENCE:
            raise ValueError(f"invalid confidence {confidence!r}")
        predictions.append(
            {
                "task_id": row["task_id"],
                "predicted_skill": predicted,
                "confidence": confidence,
                "note": note if confidence != "high" else "",
            }
        )
    if len(predictions) != len(tasks):
        raise AssertionError("prediction count differs from task count")
    if len({row["task_id"] for row in predictions}) != len(predictions):
        raise AssertionError("duplicate prediction task_id")
    summary = {
        **hashes,
        "task_count": len(tasks),
        "prediction_count": len(predictions),
        "skill_counts": dict(
            sorted(
                Counter(
                    row["predicted_skill"]
                    if row["predicted_skill"] is not None
                    else "NONE"
                    for row in predictions
                ).items()
            )
        ),
        "confidence_counts": dict(
            sorted(Counter(row["confidence"] for row in predictions).items())
        ),
        "review_ids": [
            row["task_id"]
            for row in predictions
            if row["confidence"] != "high"
        ],
    }
    return predictions, summary


def write_predictions(repo_root: Path, predictions: list[dict[str, Any]]) -> Path:
    output = repo_root / OUTPUT_RELATIVE
    output.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in predictions
    )
    output.write_text(content, encoding="utf-8", newline="\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--show-review", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    predictions, summary = build_predictions(root)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.show_review:
        tasks, _, _ = load_inputs(root)
        by_id = {row["task_id"]: row["prompt"] for row in tasks}
        for row in predictions:
            if row["confidence"] != "high":
                print(
                    json.dumps(
                        {**row, "prompt": by_id[row["task_id"]]},
                        ensure_ascii=False,
                    )
                )
    if args.write:
        output = write_predictions(root, predictions)
        print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
