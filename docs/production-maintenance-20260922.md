# Prodamus migration follow-up, 2026-09-22

## Scope

Preserve the current merchant account, bot, payment URLs and subscription periods.
No test payments, customer messages, polling, kicks or subscription jobs are run
as part of validation. Only normal live traffic invokes these actions.

The source baseline is developer commit `99a0e64`; production was clean before
changes. This repository is a separate private copy of that deployed project.

## Changes

- Reject missing/invalid webhook signatures before parsing business fields or
  doing any database, Telegram or access-control work.
- Remove the purchase handler's invalid-signature demo bypass.
- Preserve the deployed purchase and recurring HMAC canonicalization separately;
  use constant-time comparison. The current parser remains URL-encoded, as used
  by the deployed integration. Do not change Prodamus callback format separately.
- Record completed webhook digests in `webhook_receipts`; serialize identical
  deliveries with PostgreSQL advisory transaction locks. Ignore transport
  `attempt` in the digest, retain subscription payment attempt details.
- Recognize historical BUY_SUB/AUTO_PAY operations to avoid replaying completed
  payments from before the deployment.
- Bind the API's host port 8000 to loopback; keep the existing nginx ingress on
  8081 and its allowlist. Access logs confirmed legitimate webhooks use nginx.
- Remove Uvicorn development auto-reload.

## Deployment and recovery

Apply `server/sql/20260922_webhook_receipts.sql` to the Prodamus database before
starting the new API. This additive table contains only digests/type/timestamps.

The maintenance build layers only changed Python files on the exact running API
image, tagged `sheva-prodamus-api:rollback-20260922`. This avoids unrequested
package upgrades. The new image is `sheva-prodamus-api:20260922-security`.
Do not publish these runtime images: the inherited deployment contains .env.
The repository itself contains no .env or database dumps.

A temporary API instance is started on the same Docker network, bound to local
port 18000. Validate its root and database reads, switch the running nginx upstream
and gracefully reload. Drain the old API before replacing it. Restore nginx to the
regular `sheva-prodamus-api:8000` upstream after readiness checks, then retire the
temporary instance. The Telegram polling bot is never restarted.

Backups on the production host are in `/root/sheva-maintenance-20260922`, mode
restricted to root: code, compose/configuration, Prodamus dump and Sheva access
snapshot. For code rollback use the saved API image and restore its upstream.
The new receipts table can remain. Do not restore an entire database snapshot
over payments received after backup. Preserve all new live data.

## Sheva App configuration

The existing Sheva sync and app use the new local database through the existing
Docker gateway 172.19.0.1, host port 5433. Credentials are unchanged and kept only
in `/opt/sheva-app/app.env`. No application source changes were required.

Before switching, a read-only comparison found zero missing IDs, zero changed
user-to-subscription ID mappings and zero currently-valid mirrored subscriptions
that would lose access. A dry run read 15,779 rows and 106 current subscriptions.
Four manual access entries, including the October expiry, were preserved.

The app was handed through a temporary instance on local port 3779 while its
regular container was recreated with the new configuration. The original nginx
configuration and port 3778 are restored afterwards. If the Docker network is
recreated with another gateway, update the database host accordingly.

## Validation

Run `python tests/test_webhooks.py -v` with the API dependencies. The suite stubs
settings, ORM, database engine and all Telegram functions. The production check
runs it in a separate container with `--network none`, a read-only filesystem and
only a temporary writable directory. No production credentials are loaded by it.

Checks cover forged/missing signatures, invalid auto-deactivation, valid purchase
and recurring payments, duplicate/concurrent deliveries, historical operation
replay, failure rollback, Cyrillic/slash/nested payloads, unsuccessful payments,
and distinct recurring payment attempts.

## Boundaries

This is completed-event deduplication, not a transactional Telegram outbox. A
process crash after an external side effect but before the operation/receipt is
persisted can still require reconciliation. Existing notification-error handling
is preserved; durable notification retries would require a separate outbox.

The HTTP Telegram proxy remains unchanged. Encrypting that transport is separate
infrastructure work. No card data, merchant subscription recreation or changes to
billing schedules are involved.

## Sources consulted

- https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov
- https://help.prodamus.ru/payform/uvedomleniya/kak-ustroena-otpravka-uvedomlenii-ob-oplate
- https://help.prodamus.ru/payform/uvedomleniya/intervaly-uvedomlenii
- https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya
