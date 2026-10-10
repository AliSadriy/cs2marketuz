# CS2MarketUZ production readiness

## Verified in staging

The safe end-to-end test passed: seller listing, buyer order, mock payment, mock trade, delivery, escrow release, seller balance and payout approval. The test cleans its own records after completion. Smoke tests for health, catalog, favorites, alerts, profile, marketplace and admin APIs also pass.

## Not enabled in this sandbox

Real payment and real Steam trade are intentionally disabled. They require credentials and account ownership that are not present in the project. No card, wallet, Steam session cookie or private key should be placed in chat or committed to the repository.

## Required external inputs

A real launch needs a stable HTTPS domain/server, a payment provider merchant account and webhook secret, a payout provider account, a Steam trade-bot account with a dedicated inventory, and a Telegram Mini App URL configured in BotFather. These are account-specific and cannot be safely invented or connected without the owner’s credentials.

## Release switch

Before any public launch, set `MINIAPP_DEV_MODE=0` and `MARKETPLACE_TEST_MODE=0`, set a real `ADMIN_ID`, configure the payment webhook secret, and run one staging payment/refund and one low-value Steam trade. Only then enable public listings and payouts.

## Current recommendation

Keep the current staging preview running for UI review. Deploy the release candidate to a private staging hostname first; do not advertise it as a real-money market until the external payment and Steam trade checks are completed.
