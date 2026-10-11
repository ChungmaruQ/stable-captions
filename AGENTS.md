# Instructions for coding agents

This repository must work from a fresh clone. Read README.md, docs/AZURE_SETUP.md and docs/BUILD_AND_TEST.md before changing the build or onboarding.

## User ownership and secrets

- Never use the original developer's Azure account, credentials, machine paths, event documents or old binaries. None are required.
- Never ask the user to paste API keys into chat. Guide them to masked app fields or the read-only import script.
- Keep secrets in the per-user runtime_config.py location, never source, an executable, GitHub secrets for this build, logs or release assets.
- Do not provision billable resources without describing the concrete resource/SKU/region/model and obtaining the user's authorization. Sign-in, subscription and payment consent are user actions.
- The repository import script only reads resources; it does not provision them. Follow the portal guide for new users. Availability and cost must be checked in their subscription, not assumed from the developer's region.
- Do not run paid live validation implicitly. The default test/build path is fully offline.

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
- Model request parameter choice currently depends on deployment name starting with gpt-5. Preserve/document this contract or implement and test an explicit capability setting before changing it.

## Publishing

Run python scripts/scan_public.py and inspect the staged diff. Only ship newly built, key-free artifacts from dist and their manifest. Never include config.json, existing personal EXEs, recordings or screenshots. Distinguish offline tests, packaged execution, real microphone/cloud tests and physical file delivery in the final report. Do not claim unperformed tests.
