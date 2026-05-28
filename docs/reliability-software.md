# Reliability Studies and Software Strategy

**Title: Reliability Engineering and Maintenance Analytics Software for SMEs**

This document outlines the strategy for building a reliability software product targeting small and medium enterprises (SMEs), using the foundation of this sensor-app project as a technical base.

---

## Background

Starting with software-only (no hardware dependency) significantly lowers entry risk:

- Lower investment required
- Faster time to market
- Easier to scale and support
- Natural fit for subscription pricing
- IoT/sensor integration can be added later as an upsell

Positioning:

> "Reliability engineering and maintenance analytics software for SMEs."

---

## 1. Target Market

Many companies still manage maintenance manually using spreadsheets and cannot afford enterprise-grade systems. This creates a clear gap.

**Best initial targets:**

- SME factories and manufacturing plants
- Maintenance teams and reliability engineers
- Utilities and asset-intensive businesses
- Engineering service and consulting firms
- Maintenance contractors

**Avoid initially:** Large enterprises with existing ERP/CMMS investments.

---

## 2. Core Reliability Studies

The software is built around classical reliability engineering calculations:

### 2.1 MTBF — Mean Time Between Failures

$$
\text{MTBF} = \frac{\text{Total Uptime}}{\text{Number of Failures}}
$$

Tracks how long equipment operates between failures. A higher MTBF indicates more reliable assets.

### 2.2 MTTR — Mean Time To Repair

$$
\text{MTTR} = \frac{\text{Total Repair Time}}{\text{Number of Repairs}}
$$

Measures how quickly maintenance teams restore failed assets.

### 2.3 Availability

$$
\text{Availability} = \frac{\text{MTBF}}{\text{MTBF} + \text{MTTR}} \times 100\%
$$

The percentage of time an asset is operational and available for use.

### 2.4 Failure Rate

$$
\lambda = \frac{1}{\text{MTBF}}
$$

The frequency at which failures occur per unit time.

### 2.5 Downtime Analysis

- Planned vs. unplanned downtime breakdown
- Downtime by asset, by shift, by failure mode
- Cost of downtime estimation

---

## 3. Software Features — Version 1

Focus on solving the most common problems first. Do not overbuild.

### Reliability Calculations
- MTBF, MTTR, availability, failure rate
- Downtime trend analysis
- Maintenance history tracking

### Asset Management
- Machine/asset registry
- Failure logs and root cause tagging
- Maintenance records (planned + corrective)
- Spare parts tracking

### Dashboards
- Reliability KPI overview
- Downtime trends over time
- Maintenance cost tracking
- Critical asset ranking (worst performers)

### Reports
- PDF report generation
- Excel export
- Management summary view

---

## 4. Market Gap vs. Competitors

Existing systems are typically too expensive, too complex, or ERP-heavy for SMEs:

| Product | Issue |
|---|---|
| IBM Maximo | Enterprise-scale, high cost |
| SAP EAM | Complex, requires SAP ecosystem |
| Fiix CMMS | Mid-market, still complex for small teams |
| UpKeep | Good UX but limited reliability analytics |

**Your opportunity:**

- Simpler, reliability-engineering-first approach
- Affordable entry pricing
- Lightweight — no ERP required
- Engineering-focused calculations (not just work orders)

---

## 5. Recommended Tech Stack

Aligned with the existing sensor-app architecture:

| Layer | Technology |
|---|---|
| Frontend | React + Next.js |
| Backend API | Python FastAPI |
| Database | PostgreSQL |
| Charts | Plotly / Grafana |
| Auth | JWT (RS256) — already implemented |
| Hosting | AWS / Azure / DigitalOcean |

The sensor-app project already provides:

- FastAPI backend with RS256 JWT authentication (`services/ingestion_api/`)
- PostgreSQL schema and idempotent data ingestion
- Grafana dashboards for time-series visualization
- Docker Compose and Kubernetes deployment manifests

These can be directly extended for the reliability software product.

---

## 6. Pricing Strategy

### SaaS Subscription (Recommended)

| Tier | Price | Target |
|---|---|---|
| Starter | £15–£30/month | Small workshops, few assets |
| Professional | £99–£299/month | Factories, multi-user teams |
| Enterprise | £500–£2,000/month | Multi-site, custom reporting, integrations |

### Per-Asset Pricing (Alternative)

Charge £2–£10 per tracked asset per month. Scales naturally with customer size.

**Example:**

- 500 assets × £4/month = £2,000/month from a single customer

### Revenue Scenario

| Customers | Average/month | Monthly Revenue | Annual Recurring |
|---|---|---|---|
| 100 | £100 | £10,000 | £120,000 |
| 250 | £150 | £37,500 | £450,000 |

---

## 7. Sales Channels

### LinkedIn (Priority)

Publish content that builds authority with reliability engineers and maintenance managers:

- MTBF calculation examples
- Downtime cost analysis breakdowns
- Maintenance strategy comparisons (reactive vs. preventive vs. predictive)
- Industrial analytics insights

### Direct Outreach

- Maintenance managers
- Reliability engineers at SME manufacturers
- Utilities and asset-heavy operations

### Partner Channel

- Maintenance consultants and reliability engineers
- CMMS implementation partners
- They recommend or resell the software to their clients

---

## 8. Future Expansion Roadmap

Once the core product has paying customers, expand with:

| Feature | Notes |
|---|---|
| Weibull analysis | Failure probability and lifetime distribution modeling |
| AI anomaly detection | Already scaffolded in Phase 5 future work |
| IoT / sensor integration | Directly leverages this sensor-app codebase |
| Digital twin visualization | Real-time asset state overlaid on reliability data |
| ERP integration | SAP, Oracle connectors |
| Power BI integration | For enterprise reporting workflows |
| Predictive maintenance | ML models trained on historical failure data |

**Rule:** Do not add these until there are paying customers validating demand.

---

## 9. Connection to This Project

This sensor-app project provides the technical foundation for the IoT integration layer:

- Phase 1–3: Sensor simulation and MQTT telemetry → maps to real-time asset condition monitoring
- Phase 6: Fault tolerance and offline operation → critical for factory floor deployments
- Phase 7: AWS IoT Core bridge → cloud telemetry pipeline
- Phase 8–9: Dashboards and CloudWatch alerting → reliability KPI visualization
- Phase 10: HTTPS ingestion + JWT + PostgreSQL → secure multi-tenant data ingestion

The reliability software product sits above this layer, consuming telemetry and computing MTBF/MTTR/availability from real sensor events rather than manual log entry.

---

## Summary

| Decision | Choice |
|---|---|
| Initial product scope | Software only — no hardware |
| Core value | Reliability calculations + asset analytics |
| Target customer | SME factories and maintenance teams |
| Business model | SaaS subscription |
| Tech foundation | FastAPI + PostgreSQL + React (existing stack) |
| First milestone | 10 paying customers at any price |
