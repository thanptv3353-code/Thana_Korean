# Pending external setup

The local release and AI voice authoring code are available for review.
These items remain pending; they are not silently replaced by mock behavior.

1. AI voice: obtain an Azure Speech resource/key, choose its actual region, set
   THANA_TTS_ENABLED=1, AZURE_SPEECH_KEY and AZURE_SPEECH_REGION privately on the
   server, then generate a short Korean and Lao sample. Check real voice
   availability/cost and have a competent speaker review pronunciation. The
   authoring UI will remain disabled until configured. Never paste keys into
   the browser, source code or chat.
2. Recognition, pronunciation and tutor services: separate flags and credential
   setup described in INTEGRATIONS.md. They are independent from AI voice TTS.
3. Content: review imported EPS answers/translations, extend the Lao curriculum,
   and review each synthetic voice before publication. AI audio is labelled as AI.
4. Staging: the user-selected Render Free demo is deployed; verify public HTTPS
   and authenticated review from another network (STAGING_RENDER.md). Free data
   can reset. Before production cutover, decide durable storage, back up actual
   production data, dry-run migration and obtain approval for the cutover.
5. Physical-device testing: Android/iPhone microphone, playback and PWA install.
   Viewport checks and unit tests do not substitute for actual device evaluation.

Run `python3 scripts/verify_release.py` for the clean local source-package check.
Source ZIP excludes private databases, credentials, generated audio and receipts.
