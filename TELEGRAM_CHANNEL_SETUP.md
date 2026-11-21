# Optional ProSignals Telegram public-channel delivery

Public channel: https://t.me/ProSignalsSignalsHub

The two existing signal workflows send Telegram messages to one private chat using `TG_CHAT_ID`.
This opt-in feature allows them to send a **separate, clearly labeled experimental
copy** to a public channel without removing private alerts.

## Activate only when ready

1. In Telegram, open the ProSignals public channel, go to **Administrators**, and
   confirm that `@ZareSignalbot` is an administrator with **Post Messages** permission.
   Do not grant unnecessary administrator rights.
2. In GitHub, open the `zaretamur-wq/prosignals.` repository and navigate to
   **Settings → Secrets and variables → Actions → New repository secret**.
3. Create the secret **`TG_CHANNEL_ID`** with value **`@ProSignalsSignalsHub`**.
   This public channel username can be used as the Telegram Bot API chat_id.
   Do **not** change `TG_CHAT_ID`, or your private alerts may stop.
4. Merge the code change when you are ready to opt in. Both scheduled workflows
   will then deliver new alerts to both destinations while the channel secret exists.
   If `TG_CHANNEL_ID` is absent, behavior remains private-chat only.
5. Before inviting subscribers, verify the channel link and post a harmless test
   message. Manually dispatching a workflow can evaluate live market data, so do
   **not** treat it as a harmless message-only test.

## Subscriber safety

The public-channel version of each notification is labeled **EXPERIMENTAL / DEMO**
and notes trading risk. Public channel subscribers cannot post unless you link
a discussion group or grant channel posting permissions.

This feature **does not** send historical private-chat messages to the channel,
prove the signals profitable, or independently verify the public join link.
Track every outcome, including stop losses, and check applicable financial
promotion regulations before offering public or paid signals.

Never paste `TG_TOKEN` into GitHub source, screenshots, or public chat.
