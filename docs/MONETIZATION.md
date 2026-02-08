# Verirule Monetization Plan (Stripe)

## Pricing Tiers
- Free
- Pro
- Business

## Feature Gating by Tier
- Number of monitored sources per org.
- Monitoring frequency (e.g., daily vs hourly checks).
- Alert channels (email only vs email + Slack + webhook).
- Seat count and role granularity.
- Audit log retention window.
- SSO and advanced enterprise controls.

## Recommended Stripe Billing Flow
- Use Stripe Checkout for self-serve plan upgrades/downgrades.
- Persist customer and subscription identifiers in app database.
- Process Stripe webhooks (`checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`).
- Map webhook state to internal subscription status/entitlements.
- Enforce entitlements in API middleware and business logic.

## Operational Notes
- Keep idempotent webhook processing and signature verification enabled.
- Add grace-period handling for failed payments and past-due subscriptions.
- Separate trial rules from paid entitlements for clear upgrade paths.
