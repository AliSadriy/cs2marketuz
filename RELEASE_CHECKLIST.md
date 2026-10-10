# CS2MarketUZ release checklist

## Current status

- [x] Mini App catalog, categories, images and favorites
- [x] Alerts, profile, market listings and orders
- [x] Admin moderation, audit log and order state machine
- [x] Mock payment, escrow ledger, refund and dispute flow
- [x] Mock trade offer, seller balance and payout request
- [x] Signed payment webhook verification
- [x] Production mode rejects unsigned admin requests
- [x] Skinport fallback catalog and disk caches

## Required before real-money launch

- [ ] Set `MINIAPP_DEV_MODE=0` and `MARKETPLACE_TEST_MODE=0`
- [ ] Set a real `ADMIN_ID`; never use demo IDs in production
- [ ] Set a long random `PAYMENT_WEBHOOK_SECRET`
- [ ] Configure a real payment provider and verify its webhook signature format
- [ ] Configure a real payout provider; mock payout must remain disabled
- [ ] Configure Steam trade bot credentials and test with a non-valuable item
- [ ] Verify seller Steam inventory ownership and buyer trade URL flow
- [ ] Add legal pages: Terms, Privacy, Refund and Dispute policy
- [ ] Run a staging transaction and refund before enabling production orders
- [ ] Use HTTPS with a stable domain and configure Telegram Mini App URL
- [ ] Enable backups, log rotation and service auto-restart
- [ ] Review commission, limits, fraud controls and support process

## Safe launch order

1. Deploy staging with both marketplace flags disabled for real transactions.
2. Run catalog, bot, auth and admin smoke tests.
3. Connect payment in sandbox mode and verify paid/failed/refunded webhooks.
4. Connect Steam trade with a test inventory item.
5. Enable a private beta for invited users.
6. Review audit logs and reconciliation.
7. Only then enable public listings and payouts.
