# Preparing mail for ksu.codes

MailCraft is the user's mailbox app. The proposed mail server is Stalwart, which handles Internet delivery, mailbox storage, JMAP and spam filtering. Its private admin console covers operations. A second WebOS admin app is optional. This guide prepares a future deployment. No public mailbox, DNS cutover or mail relay is provisioned by this branch.

## 1. Reserve addresses before accepting mail

The live WebOS signup rule accepts 3–28 lowercase ASCII letters or digits starting with a letter, after normalization. Each accepted username fits the local part of an email address. The intended mailbox of a signed-in user is their canonical username at ksu.codes. Anon has browser-local data only.

Before provisioning, run the read-only check against the Accounts database on its host:

```sh
python3 webos/check_mail_names.py "$WEBOS_ACCOUNTS_DB"
```

The tool reports counts, never names, credentials or mailbox data. Investigate nonzero results before enabling mail. Reserve postmaster, abuse, security, hostmaster, webmaster, dmarc, quarantine and mailer-daemon at signup before assigning role aliases. The public demo account and temporary test identities should use fixture mailboxes during beta. Suppress external sending for unverified signups. Separate test-account expiry from persistent mail before cutover.

Bind each mailbox principal to the immutable WebOS account subject. Persist the address reservation independently of an account's active login. Provision and reconcile idempotently on creation, disable access on deletion and quarantine the address for operator review. A newly created account with a reused name must never inherit earlier messages. Retry provisioning failures and expose a pending state in MailCraft. Back up and test restoring principals, message storage, address reservations and configuration together.

## 2. Prove the browser integration privately

Build the existing web target and exercise the included synthetic JMAP fixture. The upstream guide describes its browser startup hook, discovery and submission. [MailCraft JMAP guide](../docs/jmap.md)

```sh
cargo test --locked -p mailcraft-jmap
cargo build --locked --target wasm32-unknown-unknown -p mailcraft-web
cargo test --locked -p mailcraft-cli --test jmap_loopback -- --ignored --nocapture
```

The last command starts a loopback test server. In the proposed WebOS integration, Desktop mounts the app, obtains the verified signed-in identity, and supplies the documented account and credential callback. Use a same-origin HTTPS session URI such as `/mail/jmap/session` resolved against the site origin. Proxy only configured mail routes. Configure discovery to advertise the public JMAP API, upload and download URLs on that origin. Confirm that attachments and submission work under the actual browser policy. Scope short-lived credentials to the current subject and mailbox, keep them in memory, and clear client state on session change. The gateway must enforce identity and revoke access independently of the UI.

Test with two ordinary accounts and Anon. Check create/draft/send/receive/reply, upload/download, failure and retry, sign-out revocation, and isolation across both accounts. Anon must make no private mailbox requests. Confirm opening a message or switching accounts cannot expose the previous user's local message cache. Use a controlled recipient and a private test domain for delivery tests.

## 3. Set up receiving and sending

Deploy Stalwart on a stable host with persistent storage, TLS, a tested backup and a mail admin identity. Use a private interface for management. Inbound Internet mail needs TCP 25 to a receiving MTA. If the public connection cannot accept it, arrange an inbound mail relay before changing MX. Outbound direct delivery also needs TCP 25 and suitable address reputation. An authenticated upstream submission relay is an alternative for outbound delivery. Browsers only need the existing public HTTPS entry point. Enable other public mailbox-client ports only if supporting external clients. [Stalwart requirements](https://stalw.art/docs/install/requirements/)

At Porkbun, prepare the following records. Fill values from the actual host and chosen sending service. Compare existing records before changing them. [Porkbun DNS instructions](https://kb.porkbun.com/article/68-how-do-i-edit-dns)

| Record | Proposed value and check |
|---|---|
| mail A, optionally AAAA | Receiving server's reachable address. Publish IPv6 only after testing inbound delivery over IPv6. |
| Domain MX | Priority 10, mail.ksu.codes for direct inbound hosting, or the inbound relay's specified host. |
| Domain SPF TXT | One policy covering the authorized sending hosts or relay. |
| DKIM selector TXT | Public key generated for the active signing domain. Keep the signing key on the server. |
| _dmarc TXT | Start in reporting mode with a working restricted report address. Move to enforcement after verifying alignment. |
| Reverse DNS | Ask the address provider for the PTR used for direct sending. Confirm the name resolves back to the sending address and matches the announced host name. |

Validate the certificate and DNS from outside the LAN. Test controlled inbound and outbound messages and inspect authentication results. Reject attempts to relay for an unrelated sender and recipient. Keep a copy of the prior routing settings for rollback and drain accepted mail before retiring a route.

## 4. Choose recipients and spam policy

Start with explicit mailboxes and role aliases. Reject unknown recipients during SMTP. If a catch-all is required later, deliver unmatched addresses to one private quarantine with quotas, expiry and an accountable reviewer. Never create a mailbox for every spelling. Test known, unknown and role addresses independently. Enable spam filtering and inbound sender-authentication checks, cap message sizes, and set per-account outbound limits. Test Junk recovery and blocked relay behavior before opening registration for external sending. [Stalwart aliases](https://stalw.art/docs/domains/addresses/) · [Spam filtering](https://stalw.art/docs/spamfilter/)

## 5. Operate and decide on cutover

Use Stalwart's admin interface privately for the owner or delegated mail admins. Monitor queue depth and oldest delivery, persistent retries or bounces, disk and certificate expiry, spam quarantine growth, failed provisioning and last successful metrics scrape. Report a missing scrape as unavailable. Start with read-only monitoring, separate privileged queue operations, and keep sender/recipient details and message bodies out of public dashboards. If using Prometheus, scrape the private exporter with a dedicated credential. [Stalwart metrics](https://stalw.art/docs/telemetry/metrics/prometheus/)

Before changing public routing, record a dated test for account isolation, mailbox restoration, controlled two-way delivery, spam handling, failure alerts and rollback. A successful web build covers only the client. The operator makes the cutover decision after the private end-to-end checks pass.
