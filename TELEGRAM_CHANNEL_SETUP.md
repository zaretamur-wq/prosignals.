# ProSignals Telegram public channel delivery

Channel: https://t.me/ProSignalsSignalsHub
Bot: @ZareSignalbot

Both the existing Forex and crypto GitHub Actions workflows keep sending private
notifications to `TG_CHAT_ID`. They now also address the public channel directly
with `TG_CHANNEL_ID: "@ProSignalsSignalsHub"` (public username, not a secret).
No changes to the existing `TG_TOKEN` or `TG_CHAT_ID` secrets are necessary.

## Required Telegram setup

1. In Telegram, open the public ProSignals channel.
2. Go to **Administrators** and confirm that `@ZareSignalbot` is included with
   **Post Messages** permission. Do not grant unnecessary privileges.
3. Keep Discussion unlinked to prevent comments. Members cannot post in channels.
4. Verify that the public link resolves and joining works from another account.
5. Confirm the next scheduled signal or status update reaches both destinations.
   Sending messages via GitHub workflows may require waiting for a qualifying
   signal; no guarantee a new trade is emitted on each run.

## Public testing precautions

Every public message is explicitly prefixed as **EXPERIMENTAL / DEMO SIGNALS ONLY**
and includes a risk disclaimer. Results are not verified; publication should
not imply profitability. Record all trade outcomes, including losses, and
review applicable UAE financial-promotion requirements before sharing broadly
or charging members.

Existing private bot-chat history is not automatically migrated. Do not expose
`TG_TOKEN` or your private `TG_CHAT_ID` publicly.
