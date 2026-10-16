# Instructions for coding agents

This repository must work from a fresh clone. Read README.md, docs/AZURE_SETUP.md, docs/AZURE_AGENT_RUNBOOK.md and docs/BUILD_AND_TEST.md before changing the build or onboarding.

## Own onboarding from an empty Azure account to working captions

- Assume a new user may have no Microsoft account, Azure subscription, resources, CLI or model deployment. For an installation/use-readiness request, own the full workflow in docs/AZURE_AGENT_RUNBOOK.md, not just the EXE build.
- Inspect what you can first; ask only for missing account choices, budget or actions that require the user. Recommend concrete choices rather than making novices choose unfamiliar SKUs and deployment settings.
- Guide account creation, sign-in and subscription activation one step at a time. Passwords, MFA, identity verification, payment details and subscription/terms consent stay with the user. Resume agent work immediately after their step is complete.
- Use available CLI/API/browser tools to create the approved resource group, Speech resource, model resource/deployment and optional Vision yourself. Do not merely tell the user to configure Azure and return later.
- Before billable changes, discover current region/model/quota availability and present a concrete plan including resource names, SKUs, pricing basis, budget and a bounded live test. Once authorized, complete that scope without asking for the same permission repeatedly; reconfirm material scope/cost changes.
- Import credentials privately, build/download both executables, connect the user's services, guide microphone/screen permissions and verify real Korean/English captions plus requested screen context within the approved test scope.
- If tools, permissions or user presence block a step, provide the exact next action and success signal, continue independent work, and return to the pending step. A documentation link or a successful offline build alone is not completion of full onboarding.
- Honor narrower requests: repository/documentation changes or offline-only builds do not authorize provisioning resources in the current user's Azure account.

## User ownership and secrets

- Never use the original developer's Azure account, credentials, machine paths, event documents or old binaries. None are required.
- Never ask the user to paste API keys into chat. Guide them to masked app fields or the read-only import script.
- Keep secrets in the per-user runtime_config.py location, never source, an executable, GitHub secrets for this build, logs or release assets.
- Do not provision billable resources without describing the concrete resource/SKU/region/model and obtaining the user's authorization. User authentication, subscription acceptance and payment consent are user actions; approved resource creation is agent work when tools permit.
- The repository import script only reads resources; it does not provision them. For new users, first provision approved resources via CLI/API/portal using docs/AZURE_AGENT_RUNBOOK.md, then import their settings. Availability and cost must be checked in their subscription, not assumed from the developer's region.
- Do not run paid live validation implicitly. Include a bounded live test in the approved onboarding plan; otherwise obtain authorization before connecting. The default test/build path remains fully offline.

## App and build invariants

- Preserve both apps: apps/en_ko (English/Korean output selection), apps/jp_vn (Japanese + Vietnamese).
- Input detection is only Korean/English. Never show Korean fallback in English output mode or arbitrary English fallback in Korean/JP-VN mode.
- Preserve numbers, negation, uncertainty, speech acts and source priority. Slides are untrusted context, not an instruction or something to recite.
- Maintain previously displayed stable captions, compact layout, idle clearing, filler filtering and language checks. Do not promise zero latency or perfect detection/filtering.
- Keep the runtime_config.py copies identical; tests check this.
- Implement/test both variants on macOS first when a Mac is available, then build Windows on Windows. Do not claim cross-compilation.
- Use the rightmost display for visible validation, never disturb another display's windows.
- On Windows use Desktop/StableCaptions-Workspace/Project_Public for this public checkout. Resolve the known Desktop folder, preserve Archive and existing apps, never reorganize unrelated desktop files.
- Run python scripts/check.py after functional changes; run scripts/build.py for a release. Successful tests alone do not prove the generated executable works.
- Keep Windows x64/Python 3.12 and pinned direct dependencies unless a tested upgrade is necessary.
- Model parameters depend on deployment names. en_ko recognizes gpt-6-luna / gpt-6-luna-* with reasoning_effort=none; both apps retain the gpt-5* minimal contract. Other names use legacy non-reasoning parameters. Preserve these app-specific contracts or implement and test an explicit capability setting before changing them.

## Publishing

Run python scripts/scan_public.py and inspect the staged diff. Only ship newly built, key-free artifacts from dist and their manifest. Never include config.json, existing personal EXEs, recordings or screenshots. Distinguish offline tests, packaged execution, real microphone/cloud tests and physical file delivery in the final report. Do not claim unperformed tests.
