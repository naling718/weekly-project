# Week of 2026-11-23: five project ideas

Research covered news from roughly 16 to 23 November 2026. Several sites (usenix.org, edpb.europa.eu, techrepublic.com) could not be opened directly from the build session, so some details come from search summaries of those pages.

No company on the list was found to have closed its Dublin site this week. Match Group (Tinder) is not on the list; it is included because its EU decision came from the Irish Data Protection Commission in Dublin and the same problem applies to every large platform regulated there.

## 1. Failover headroom checker (Microsoft)

**Problem.** On 12 and 13 November Microsoft 365 (Outlook, Teams, Copilot) went down for most of a day. Microsoft's preliminary report says a lock-contention bug added to its networking gateways in July lay dormant, Teams then failed over onto the Exchange gateways about 15 hours before the outage, and about 14% of gateway capacity was already out of service. More than 80% of gateway servers ended up unresponsive. Sources: [BleepingComputer](https://bleepingcomputer.com/news/microsoft/microsoft-says-months-old-bug-caused-global-microsoft-365-outage), [iTnews](https://www.itnews.com.au/news/microsoft-says-three-month-old-bug-behind-global-m365-outage-630382), [Network World](https://www.networkworld.com/article/4249392/microsoft-outage-a-cascading-failure-that-started-with-an-undetected-bug-2.html).

**What to build.** A Python CLI that takes a JSON description of a server pool (servers, how many are out, per-server capacity, current load) plus a planned failover, simulates load spreading and servers dropping out, and says SAFE / AT RISK / CASCADE with the largest traffic shift that is safe right now. In: deterministic cascade model, "latent bug" knob, scenario files, tests, exit code for CI. Out: real telemetry, latency/queueing models, a web UI.

**Stack.** Python standard library only.

**What it shows.** Reliability thinking that Dublin SRE and backend teams (Azure, AWS, Google) hire for. Interview line: "average utilisation looked fine at 76%, but the weakest servers were already past their real limit, so the pool collapsed. My tool checks the weakest server, not the average."

**Difficulty.** Easy to medium. Learn: how cascading failures work and why capacity planning uses headroom targets.

## 2. Data-export completeness auditor (Match Group / Tinder, DPC Dublin)

**Problem.** On 13 November the Irish DPC fined MTCH Technology Services (Tinder) EUR 11 million because its "Download My Data" tool left out some categories of personal data, or only summarised them, without telling users (GDPR Article 15(3)). Every platform regulated from Dublin (Meta, Google, LinkedIn, TikTok) runs a similar export tool. Sources: [EDPB news](https://www.edpb.europa.eu/news/irish-data-protection-commission-fines-mtch-eur-11-million-following-inquiry-into-tinder-users_es), [PPC Land](https://ppc.land/irelands-dpc-fines-tinder-operator-eur11m-over-incomplete-data-downloads/).

**What to build.** A tool that compares a data inventory (which tables and fields hold personal data) against an actual export ZIP and reports missing or summarised categories, as a small Flask page plus a CLI. Out: real company data, legal advice.

**Stack.** Python, Flask, JSON schema.

**What it shows.** Privacy engineering, which is a large part of Dublin big-tech work because of the DPC. Interview line: turning a legal requirement into an automated test.

**Difficulty.** Easy. Learn: GDPR access rights and data inventories.

## 3. Live operational-to-analytics sync (MongoDB)

**Problem.** On 17 November MongoDB announced it acquired Firebolt to run analytics next to its document database, so customers do not have to build separate pipelines. Sources: [MongoDB blog](https://mongodb.com/company/blog/news/mongodb-acquires-firebolt), [Techzine](https://www.techzine.eu/news/analytics/145917/mongodb-acquires-firebolt-for-real-time-analytics/).

**What to build.** A small change-data-capture demo: an append-only change log of document inserts and updates applied to a DuckDB columnar table, with a benchmark comparing analytic queries on documents versus columns. Out: real MongoDB change streams, distributed setup.

**Stack.** Python, DuckDB, pytest.

**What it shows.** Data engineering basics (CDC, row vs column storage). Interview line: why analytics on the operational store is hard and what the trade-offs are.

**Difficulty.** Medium to stretch. Learn: columnar storage and CDC.

## 4. Spending-policy engine for AI agent payments (Stripe)

**Problem.** Stripe is adding 200 roles at its Dublin HQ in engineering and go-to-market, with open Dublin roles in payments and risk, while its recent launches let AI agents pay through Link wallets. Agent payments need limits that a human sets. Sources: [Irish Examiner](https://www.irishexaminer.com/business/companies/arid-41918398.html), [Stripe Sessions 2026](https://stripe.com/ie/newsroom/news/sessions-2026). Both are older than this week.

**What to build.** A rule engine (per-transaction cap, daily limit, merchant allowlist, velocity check) that approves or declines mocked agent payment requests, with an audit log and idempotency keys. Out: real Stripe API calls.

**Stack.** Python, FastAPI, SQLite.

**What it shows.** Payments correctness (idempotency, limits, audit). Interview line: how you prevent double charges and runaway agents.

**Difficulty.** Medium. Learn: idempotency and rule engines.

## 5. Offline support-bot evaluation harness (Salesforce / Fin, formerly Intercom)

**Problem.** Salesforce's USD 3.6 billion purchase of Fin (formerly Intercom, with a large Dublin engineering team) is expected to close between November 2026 and January 2027. Fin's product is an AI support agent, and judging whether its answers are correct is the hard part. Sources: [TechTarget](https://www.techtarget.com/searchcustomerexperience/news/366644421/Salesforce-plans-to-acquire-Fin-agentic-customer-service-AI), [MarTech](https://martech.org/salesforce-acquires-fin-formerly-known-as-intercom/).

**What to build.** A retrieval-based help-centre bot (TF-IDF, no paid API) plus an eval harness that scores answers on a labelled question set: grounded or not, resolved or not. Out: an LLM, a chat UI.

**Stack.** Python, scikit-learn, pytest.

**What it shows.** A first step into AI with real evaluation. Interview line: how to measure an AI feature before shipping it.

**Difficulty.** Medium. Learn: retrieval and evaluation metrics.

## Where to start

Start with idea 1. The source is this week's biggest Dublin-relevant incident, it needs nothing but Python, and the demo makes one point clearly: a pool can look fine on average and still collapse.

## Ratings (1 to 5 each, max 30)

| Idea | Hiring signal | Buildability | Demo value | Fit | Source strength | Freshness | Total |
|---|---|---|---|---|---|---|---|
| 1. Failover headroom checker (Microsoft) | 5 | 5 | 4 | 4 | 5 | 5 | **28** |
| 2. Data-export completeness auditor (Match Group / DPC) | 3 | 5 | 4 | 5 | 5 | 4 | 26 |
| 4. Agent spending-policy engine (Stripe) | 5 | 5 | 4 | 4 | 3 | 5 | 26 |
| 3. Operational-to-analytics sync (MongoDB) | 4 | 4 | 3 | 3 | 5 | 5 | 24 |
| 5. Support-bot eval harness (Salesforce / Fin) | 4 | 4 | 4 | 4 | 3 | 3 | 22 |

Idea 1 won: the strongest and freshest source of the week, it runs with no installs, and Microsoft has not been used in a past build.
