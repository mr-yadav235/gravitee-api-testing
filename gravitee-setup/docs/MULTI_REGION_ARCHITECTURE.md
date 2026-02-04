# Gravitee APIM Multi-Region Enterprise Architecture

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Date** | February 2, 2026 |
| **Status** | Production Ready |
| **Classification** | Internal - Architecture |
| **Author** | Platform Engineering Team |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Global Architecture Overview](#2-global-architecture-overview)
3. [Regional Deployment Model](#3-regional-deployment-model)
4. [Network Zone Architecture](#4-network-zone-architecture)
5. [Japan Secure Zone (JSZ)](#5-japan-secure-zone-jsz)
6. [Core Zone - Control Plane](#6-core-zone---control-plane)
7. [Internal API Gateway](#7-internal-api-gateway)
8. [Data Flow Architecture](#8-data-flow-architecture)
9. [Security Architecture](#9-security-architecture)
10. [Firewall Rules by Zone](#10-firewall-rules-by-zone)
11. [High Availability & Disaster Recovery](#11-high-availability--disaster-recovery)
12. [Operational Procedures](#12-operational-procedures)
13. [Compliance & Governance](#13-compliance--governance)

---

## 1. Executive Summary

### 1.1 Overview

This document describes the enterprise multi-region deployment architecture for Gravitee API Management (APIM) platform. The architecture is designed to support global API traffic distribution while maintaining strict security boundaries and regulatory compliance.

### 1.2 Deployment Regions

| Region | Code | Type | Data Plane | Control Plane |
|--------|------|------|------------|---------------|
| United States | US | Global Shared | Regional Gateway | Core Zone |
| European Union | EU | Global Shared | Regional Gateway | Core Zone |
| Asia Pacific | ASIA | Global Shared | Regional Gateway | Core Zone |
| Japan Secure Zone | JSZ | Isolated | Independent Gateway | Core Zone (Limited) |
| **Core Zone** | **CORE** | **Internal** | **Internal Gateway** | **Core Zone** |

### 1.3 Gateway Types

| Gateway Type | Location | Purpose | Access |
|--------------|----------|---------|--------|
| **External Gateway** | US/EU/ASIA Regions | Public API traffic from external consumers | Internet-facing |
| **JSZ Gateway** | Japan Secure Zone | Japan-only isolated traffic | Japan IPs only |
| **Internal Gateway** | Core Zone | Internal microservices, admin APIs, service-to-service | Internal network only |

### 1.5 Key Design Principles

| Principle | Description |
|-----------|-------------|
| **Centralized Control** | Single control plane in Core Zone manages all gateways |
| **Distributed Data Plane** | External gateways deployed close to consumers for low latency |
| **Internal Gateway** | Dedicated gateway in Core Zone for internal service-to-service communication |
| **Zone Isolation** | Strict network segmentation (Outer DMZ → Inner DMZ → Core) |
| **JSZ Independence** | Japan Secure Zone operates with isolated data plane |
| **Shared Backend** | Database and Elasticsearch centralized in Core Zone |
| **Global Sync** | All global gateways synchronized via Core Zone |

---

## 2. Global Architecture Overview

### 2.1 High-Level Multi-Region Architecture

![Global Architecture Overview](diagrams/01-global-architecture.svg)

<details>
<summary>View ASCII Diagram (fallback)</summary>

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                                  │
│                                           GLOBAL INTERNET                                                        │
│                                                                                                                  │
│         ┌─────────────┐          ┌─────────────┐          ┌─────────────┐          ┌─────────────┐              │
│         │  US Clients │          │  EU Clients │          │ ASIA Clients│          │ JSZ Clients │              │
│         └──────┬──────┘          └──────┬──────┘          └──────┬──────┘          └──────┬──────┘              │
│                │                        │                        │                        │                      │
└────────────────┼────────────────────────┼────────────────────────┼────────────────────────┼──────────────────────┘
                 │                        │                        │                        │
                 │                        │                        │                        │
    ┌────────────┼────────────────────────┼────────────────────────┼────────────────────────┼────────────────────┐
    │            │                        │                        │                        │                    │
    │            │        GLOBAL LOAD BALANCER / GSLB / CDN (GeoDNS Routing)              │                    │
    │            │                        │                        │                        │                    │
    └────────────┼────────────────────────┼────────────────────────┼────────────────────────┼────────────────────┘
                 │                        │                        │                        │
                 ▼                        ▼                        ▼                        ▼
┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────────┐
│                        │  │                        │  │                        │  │                            │
│     US REGION          │  │     EU REGION          │  │    ASIA REGION         │  │   JAPAN SECURE ZONE        │
│                        │  │                        │  │                        │  │        (JSZ)               │
│  ┌──────────────────┐  │  │  ┌──────────────────┐  │  │  ┌──────────────────┐  │  │  ┌──────────────────────┐  │
│  │   OUTER DMZ      │  │  │  │   OUTER DMZ      │  │  │  │   OUTER DMZ      │  │  │  │   OUTER DMZ          │  │
│  │                  │  │  │  │                  │  │  │  │                  │  │  │  │   (Air-Gapped)       │  │
│  │  ┌────────────┐  │  │  │  │  ┌────────────┐  │  │  │  │  ┌────────────┐  │  │  │  │  ┌────────────────┐  │  │
│  │  │    WAF     │  │  │  │  │  │    WAF     │  │  │  │  │  │    WAF     │  │  │  │  │  │    WAF         │  │  │
│  │  │    LB      │  │  │  │  │  │    LB      │  │  │  │  │  │    LB      │  │  │  │  │  │    LB          │  │  │
│  │  └─────┬──────┘  │  │  │  │  └─────┬──────┘  │  │  │  │  └─────┬──────┘  │  │  │  │  └───────┬────────┘  │  │
│  └────────┼─────────┘  │  │  └────────┼─────────┘  │  │  └────────┼─────────┘  │  │  └─────────┼────────────┘  │
│           │            │  │           │            │  │           │            │  │            │               │
│  ┌────────┼─────────┐  │  │  ┌────────┼─────────┐  │  │  ┌────────┼─────────┐  │  │  ┌─────────┼────────────┐  │
│  │        ▼         │  │  │  │        ▼         │  │  │  │        ▼         │  │  │  │         ▼            │  │
│  │   INNER DMZ      │  │  │  │   INNER DMZ      │  │  │  │   INNER DMZ      │  │  │  │    INNER DMZ         │  │
│  │                  │  │  │  │                  │  │  │  │                  │  │  │  │    (Isolated)        │  │
│  │  ┌────────────┐  │  │  │  │  ┌────────────┐  │  │  │  │  ┌────────────┐  │  │  │  │  ┌────────────────┐  │  │
│  │  │  GATEWAY   │  │  │  │  │  │  GATEWAY   │  │  │  │  │  │  GATEWAY   │  │  │  │  │  │   GATEWAY      │  │  │
│  │  │  CLUSTER   │  │  │  │  │  │  CLUSTER   │  │  │  │  │  │  CLUSTER   │  │  │  │  │  │   CLUSTER      │  │  │
│  │  │            │  │  │  │  │  │            │  │  │  │  │  │            │  │  │  │  │  │   (Isolated)   │  │  │
│  │  │ ┌──┐┌──┐   │  │  │  │  │ ┌──┐┌──┐   │  │  │  │  │ ┌──┐┌──┐   │  │  │  │  │ ┌──┐┌──┐         │  │  │
│  │  │ │GW││GW│   │  │  │  │  │ │GW││GW│   │  │  │  │  │ │GW││GW│   │  │  │  │  │ │GW││GW│         │  │  │
│  │  │ └──┘└──┘   │  │  │  │  │ └──┘└──┘   │  │  │  │  │ └──┘└──┘   │  │  │  │  │ └──┘└──┘         │  │  │
│  │  └────────────┘  │  │  │  └────────────┘  │  │  │  └────────────┘  │  │  │  └────────────────┘  │  │
│  │        │         │  │  │        │         │  │  │        │         │  │  │         │            │  │
│  └────────┼─────────┘  │  └────────┼─────────┘  │  └────────┼─────────┘  │  └─────────┼────────────┘  │
│           │            │           │            │           │            │            │               │
│           │  GLOBAL    │           │  GLOBAL    │           │  GLOBAL    │            │  ISOLATED     │
│           │  SYNC      │           │  SYNC      │           │  SYNC      │            │  (No Sync)    │
│           │            │           │            │           │            │            │               │
└───────────┼────────────┘           │            │           │            └────────────┼───────────────┘
            │                        │            │           │                         │
            │                        │            │           │                         │
            └────────────────────────┼────────────┼───────────┘                         │
                                     │            │                                     │
                                     ▼            ▼                                     │
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                                 │
│                                            CORE ZONE                                                            │
│                                     (Centralized Control Plane)                                                 │
│                                                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                                                          │  │
│   │   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐              │  │
│   │   │                 │    │                 │    │                 │    │                 │              │  │
│   │   │  Management     │    │   Console       │    │   Developer     │    │   MySQL         │              │  │
│   │   │     API         │    │     UI          │    │    Portal       │    │   Database      │              │  │
│   │   │                 │    │                 │    │                 │    │                 │              │  │
│   │   └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘              │  │
│   │                                                                                                          │  │
│   │   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────────────────────────┐    │  │
│   │   │                 │    │                 │    │                                                 │    │  │
│   │   │  Elasticsearch  │    │   Kubernetes    │    │         INTERNAL API GATEWAY                    │    │  │
│   │   │    Cluster      │    │    Cluster      │    │         (For Internal Apps)                     │    │  │
│   │   │                 │    │                 │    │                                                 │    │  │
│   │   └─────────────────┘    └─────────────────┘    │    ┌──────────┐  ┌──────────┐  ┌──────────┐    │    │  │
│   │                                                 │    │ INT-GW-1 │  │ INT-GW-2 │  │ INT-GW-3 │    │    │  │
│   │                                                 │    │ (Active) │  │ (Active) │  │ (Active) │    │    │  │
│   │                                                 │    └──────────┘  └──────────┘  └──────────┘    │    │  │
│   │                                                 │                                                 │    │  │
│   │                                                 │    • Internal Apps    • Admin Tools             │    │  │
│   │                                                 │    • Service-to-Service • CI/CD Pipelines       │    │  │
│   │                                                 │                                                 │    │  │
│   │                                                 └─────────────────────────────────────────────────┘    │  │
│   │                                                                                                          │  │
│   └─────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                 │
│                                          ┌───────────────────┐                                                 │
│                                          │  Limited Access   │◄────────────────────────────────────────────────┤
│                                          │  for JSZ          │                                                 │
│                                          │  (Config Only)    │                                                 │
│                                          └───────────────────┘                                                 │
│                                                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```
</details>

### 2.2 Component Distribution Matrix

| Component | US Region | EU Region | ASIA Region | JSZ | Core Zone |
|-----------|-----------|-----------|-------------|-----|-----------|
| **External API Gateway** | ✅ Cluster | ✅ Cluster | ✅ Cluster | ✅ Isolated | ❌ |
| **Internal API Gateway** | ❌ | ❌ | ❌ | ✅ JSZ App Zone | ✅ Cluster |
| Management API | ❌ | ❌ | ❌ | ❌ | ✅ |
| Console UI | ❌ | ❌ | ❌ | ❌ | ✅ |
| Developer Portal | ❌ | ❌ | ❌ | ❌ | ✅ |
| MySQL | ❌ | ❌ | ❌ | ❌ | ✅ |
| Elasticsearch | ❌ | ❌ | ❌ | ❌ | ✅ |
| WAF/LB | ✅ | ✅ | ✅ | ✅ | ✅ (Internal LB) |
| Config Sync | ✅ Global | ✅ Global | ✅ Global | ⚠️ Limited | ✅ Source |

---

## 3. Regional Deployment Model

### 3.1 US Region Architecture

![US Region Architecture](diagrams/07-us-region.svg)

<details>
<summary>View ASCII Diagram (fallback)</summary>

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    US REGION                                             │
│                         (On-Premise Data Centers)                                       │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              OUTER DMZ                                             │  │
│  │                         (Public Subnet)                                            │  │
│  │                                                                                    │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │                     EDGE SECURITY LAYER                                      │ │  │
│  │   │                                                                              │ │  │
│  │   │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │ │  │
│  │   │  │   WAF       │   │   DDoS      │   │   IDS/IPS   │   │    SSL      │     │ │  │
│  │   │  │             │   │  Protection │   │   System    │   │ Termination │     │ │  │
│  │   │  │             │   │             │   │             │   │             │     │ │  │
│  │   │  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘     │ │  │
│  │   │         │                 │                 │                 │            │ │  │
│  │   │         └─────────────────┴─────────────────┴─────────────────┘            │ │  │
│  │   │                                    │                                       │ │  │
│  │   │                           ┌────────▼────────┐                              │ │  │
│  │   │                           │                 │                              │ │  │
│  │   │                           │  Application    │                              │ │  │
│  │   │                           │  Load Balancer  │                              │ │  │
│  │   │                           │                 │                              │ │  │
│  │   │                           │                 │                              │ │  │
│  │   │                           └────────┬────────┘                              │ │  │
│  │   │                                    │                                       │ │  │
│  │   └────────────────────────────────────┼───────────────────────────────────────┘ │  │
│  │                                        │                                         │  │
│  └────────────────────────────────────────┼─────────────────────────────────────────┘  │
│                                           │                                            │
│                                           │ Port 443 (HTTPS)                           │
│                                           │                                            │
│  ┌────────────────────────────────────────┼─────────────────────────────────────────┐  │
│  │                                        ▼                                         │  │
│  │                              INNER DMZ                                           │  │
│  │                         (Private Subnet)                                         │  │
│  │                                                                                  │  │
│  │   ┌───────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │                    API GATEWAY CLUSTER                                     │ │  │
│  │   │                                                                            │ │  │
│  │   │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐        │ │  │
│  │   │   │                 │   │                 │   │                 │        │ │  │
│  │   │   │   Gateway #1    │   │   Gateway #2    │   │   Gateway #3    │        │ │  │
│  │   │   │   (Active)      │   │   (Active)      │   │   (Active)      │        │ │  │
│  │   │   │                 │   │                 │   │                 │        │ │  │
│  │   │   │   Data Center  │   │   Data Center  │   │   Data Center  │        │ │  │
│  │   │   │       A         │   │       B         │   │       C         │        │ │  │
│  │   │   │                 │   │                 │   │                 │        │ │  │
│  │   │   │   Port: 8082    │   │   Port: 8082    │   │   Port: 8082    │        │ │  │
│  │   │   │                 │   │                 │   │                 │        │ │  │
│  │   │   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘        │ │  │
│  │   │            │                     │                     │                 │ │  │
│  │   │            └─────────────────────┼─────────────────────┘                 │ │  │
│  │   │                                  │                                       │ │  │
│  │   │                         ┌────────▼────────┐                              │ │  │
│  │   │                         │  Internal LB    │                              │ │  │
│  │   │                         │  (Backend)      │                              │ │  │
│  │   │                         └────────┬────────┘                              │ │  │
│  │   │                                  │                                       │ │  │
│  │   └──────────────────────────────────┼───────────────────────────────────────┘ │  │
│  │                                      │                                         │  │
│  │   ┌──────────────────────────────────┼───────────────────────────────────────┐ │  │
│  │   │                                  ▼                                       │ │  │
│  │   │                    BACKEND SERVICES                                      │ │  │
│  │   │                                                                          │ │  │
│  │   │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │ │  │
│  │   │   │  Service A  │   │  Service B  │   │  Service C  │                   │ │  │
│  │   │   │  (K8s)      │   │  (Container)│   │  (VM)       │                   │ │  │
│  │   │   └─────────────┘   └─────────────┘   └─────────────┘                   │ │  │
│  │   │                                                                          │ │  │
│  │   └──────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                  │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                         │
│                              │                                                          │
│                              │ Sync to Core Zone                                        │
│                              │ (TLS over VPN)                                           │
│                              ▼                                                          │
│                    ┌─────────────────────┐                                             │
│                    │   VPN Connection    │                                             │
│                    │   (On-Premise)      │                                             │
│                    └─────────────────────┘                                             │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```
</details>

### 3.2 EU Region Architecture

![EU Region Architecture](diagrams/08-eu-region.svg)

<details>
<summary>View ASCII Diagram (fallback)</summary>

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    EU REGION                                             │
│                         (On-Premise Data Centers)                                       │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              OUTER DMZ                                             │  │
│  │                                                                                    │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │                     EDGE SECURITY LAYER                                      │ │  │
│  │   │                                                                              │ │  │
│  │   │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                        │ │  │
│  │   │  │   WAF       │   │   GDPR      │   │   Geo       │                        │ │  │
│  │   │  │             │   │  Compliant  │   │  Blocking   │                        │ │  │
│  │   │  │             │   │   Rules     │   │             │                        │ │  │
│  │   │  └─────────────┘   └─────────────┘   └─────────────┘                        │ │  │
│  │   │                                                                              │ │  │
│  │   │                    ┌─────────────────┐                                       │ │  │
│  │   │                    │  Load Balancer   │                                       │ │  │
│  │   │                    │  (GDPR Compliant)│                                       │ │  │
│  │   │                    └────────┬────────┘                                       │ │  │
│  │   │                             │                                                │ │  │
│  │   └─────────────────────────────┼────────────────────────────────────────────────┘ │  │
│  │                                 │                                                  │  │
│  └─────────────────────────────────┼──────────────────────────────────────────────────┘  │
│                                    │                                                     │
│  ┌─────────────────────────────────┼──────────────────────────────────────────────────┐  │
│  │                                 ▼                                                  │  │
│  │                              INNER DMZ                                             │  │
│  │                                                                                    │  │
│  │   ┌───────────────────────────────────────────────────────────────────────────┐   │  │
│  │   │                    API GATEWAY CLUSTER                                     │   │  │
│  │   │                                                                            │   │  │
│  │   │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐        │   │  │
│  │   │   │   Gateway #1    │   │   Gateway #2    │   │   Gateway #3    │        │   │  │
│  │   │   │   Data Center A  │   │   Data Center B │   │   Data Center C │        │   │  │
│  │   │   └─────────────────┘   └─────────────────┘   └─────────────────┘        │   │  │
│  │   │                                                                            │   │  │
│  │   │   GDPR Compliance:                                                         │   │  │
│  │   │   • No PII in logs exported outside EU                                     │   │  │
│  │   │   • Data residency enforced                                                │   │  │
│  │   │   • Right to erasure support                                               │   │  │
│  │   │                                                                            │   │  │
│  │   └───────────────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                                    │  │
│  └────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

</details>

### 3.3 ASIA Region Architecture

![ASIA Region Architecture](diagrams/09-asia-region.svg)

<details>
<summary>View ASCII Diagram (fallback)</summary>

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   ASIA REGION                                            │
│                         (On-Premise Data Centers)                                       │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              OUTER DMZ                                             │  │
│  │                                                                                    │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │                     EDGE SECURITY LAYER                                      │ │  │
│  │   │                                                                              │ │  │
│  │   │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                        │ │  │
│  │   │  │   WAF       │   │   Regional  │   │   China     │                        │ │  │
│  │   │  │             │   │   Compliance│   │  Firewall   │                        │ │  │
│  │   │  │             │   │   Rules     │   │  (If needed)│                        │ │  │
│  │   │  └─────────────┘   └─────────────┘   └─────────────┘                        │ │  │
│  │   │                                                                              │ │  │
│  │   │                    ┌─────────────────┐                                       │ │  │
│  │   │                    │  Load Balancer   │                                       │ │  │
│  │   │                    └────────┬────────┘                                       │ │  │
│  │   │                             │                                                │ │  │
│  │   └─────────────────────────────┼────────────────────────────────────────────────┘ │  │
│  │                                 │                                                  │  │
│  └─────────────────────────────────┼──────────────────────────────────────────────────┘  │
│                                    │                                                     │
│  ┌─────────────────────────────────┼──────────────────────────────────────────────────┐  │
│  │                                 ▼                                                  │  │
│  │                              INNER DMZ                                             │  │
│  │                                                                                    │  │
│  │   ┌───────────────────────────────────────────────────────────────────────────┐   │  │
│  │   │                    API GATEWAY CLUSTER                                     │   │  │
│  │   │                                                                            │   │  │
│  │   │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐        │   │  │
│  │   │   │   Gateway #1    │   │   Gateway #2    │   │   Gateway #3    │        │   │  │
│  │   │   │   Data Center   │   │   Data Center   │   │   Data Center   │        │   │  │
│  │   │   │       A         │   │       B         │   │       C         │        │   │  │
│  │   │   └─────────────────┘   └─────────────────┘   └─────────────────┘        │   │  │
│  │   │                                                                            │   │  │
│  │   └───────────────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                                    │  │
│  └────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```
</details>

---

## 4. Network Zone Architecture

### 4.1 Zone Model Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                              NETWORK ZONE MODEL                                          │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │                              INTERNET                                              │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────┬───────────────────────────────────────────┘  │
│                                          │                                              │
│                                          │ HTTPS (443)                                  │
│                                          ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │                           OUTER DMZ (Zone 1)                                       │  │
│  │                                                                                    │  │
│  │   Purpose: Edge security, DDoS protection, SSL termination                        │  │
│  │                                                                                    │  │
│  │   Components:                                                                      │  │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │  │
│  │   │    WAF      │  │   DDoS      │  │    CDN      │  │   Public    │             │  │
│  │   │             │  │  Protection │  │   Cache     │  │    LB       │             │  │
│  │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘             │  │
│  │                                                                                    │  │
│  │   Security Controls:                                                               │  │
│  │   • Rate limiting (10,000 req/sec per IP)                                         │  │
│  │   • Geo-blocking (configurable by region)                                         │  │
│  │   • Bot detection and mitigation                                                  │  │
│  │   • OWASP Top 10 protection                                                       │  │
│  │   • SSL/TLS 1.3 enforcement                                                       │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────┬───────────────────────────────────────────┘  │
│                                          │                                              │
│                                          │ Internal (8082)                              │
│                                          │ (Encrypted)                                  │
│                                          ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │                           INNER DMZ (Zone 2)                                       │  │
│  │                                                                                    │  │
│  │   Purpose: API Gateway processing, policy enforcement                             │  │
│  │                                                                                    │  │
│  │   Components:                                                                      │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │                      API GATEWAY CLUSTER                                     │ │  │
│  │   │                                                                              │ │  │
│  │   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │ │  │
│  │   │   │  Gateway 1  │  │  Gateway 2  │  │  Gateway N  │                         │ │  │
│  │   │   │             │  │             │  │             │                         │ │  │
│  │   │   │ • Routing   │  │ • Routing   │  │ • Routing   │                         │ │  │
│  │   │   │ • Auth      │  │ • Auth      │  │ • Auth      │                         │ │  │
│  │   │   │ • Rate Limit│  │ • Rate Limit│  │ • Rate Limit│                         │ │  │
│  │   │   │ • Transform │  │ • Transform │  │ • Transform │                         │ │  │
│  │   │   └─────────────┘  └─────────────┘  └─────────────┘                         │ │  │
│  │   │                                                                              │ │  │
│  │   └─────────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                    │  │
│  │   Security Controls:                                                               │  │
│  │   • API key validation                                                            │  │
│  │   • OAuth2/JWT verification                                                       │  │
│  │   • Request/response transformation                                               │  │
│  │   • Payload validation                                                            │  │
│  │   • Per-API rate limiting                                                         │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────┬───────────────────────────────────────────┘  │
│                                          │                                              │
│                                          │ Backend Calls                                │
│                                          │ (mTLS)                                       │
│                                          ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │                         APPLICATION ZONE (Zone 3)                                  │  │
│  │                                                                                    │  │
│  │   Purpose: Backend services, microservices                                        │  │
│  │                                                                                    │  │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │  │
│  │   │  Service A  │  │  Service B  │  │  Service C  │  │  Service N  │             │  │
│  │   │  (K8s)      │  │  (Container)│  │  (Container)│  │  (VM)       │             │  │
│  │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘             │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────┬───────────────────────────────────────────┘  │
│                                          │                                              │
│                                          │ Config Sync / Analytics                      │
│                                          │ (TLS + VPN)                                  │
│                                          ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │                            CORE ZONE (Zone 4)                                      │  │
│  │                                                                                    │  │
│  │   Purpose: Centralized control plane, shared data stores                          │  │
│  │                                                                                    │  │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │  │
│  │   │ Management  │  │  Console    │  │   Portal    │  │  MySQL      │             │  │
│  │   │    API      │  │    UI       │  │             │  │  Database   │             │  │
│  │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘             │  │
│  │                                                                                    │  │
│  │   ┌─────────────┐                                                                 │  │
│  │   │Elasticsearch│                                                                 │  │
│  │   │  Cluster    │                                                                 │  │
│  │   └─────────────┘                                                                 │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Zone Communication Matrix

| From Zone | To Zone | Protocol | Port | Purpose | Encryption |
|-----------|---------|----------|------|---------|------------|
| Internet | Outer DMZ | HTTPS | 443 | API Traffic | TLS 1.3 |
| Outer DMZ | Inner DMZ | HTTP | 8082 | Gateway Traffic | Internal TLS |
| Inner DMZ | Application | HTTP/gRPC | Various | Backend Calls | mTLS |
| Inner DMZ | Core Zone | HTTPS | 443 | Config Sync | TLS + VPN |
| Inner DMZ | Core Zone | HTTPS | 3306 | MySQL | TLS + VPN |
| Inner DMZ | Core Zone | HTTPS | 9243 | Elasticsearch | TLS + VPN |

---

## 5. Japan Secure Zone (JSZ)

### 5.1 JSZ Architecture Overview

The Japan Secure Zone (JSZ) is a highly restricted environment designed for sensitive Japanese market operations. JSZ Gateway connects to the **Core Zone MySQL and Elasticsearch** (shared infrastructure) but with **restricted access** and **Japan-only API traffic**.

![JSZ Architecture](diagrams/03-jsz-architecture.svg)

<details>
<summary>View ASCII Diagram (fallback)</summary>

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                            JAPAN SECURE ZONE (JSZ)                                       │
│                        (Uses Core Zone MySQL & Elasticsearch)                          │
│                                                                                          │
│                         ┌─────────────────────────────────┐                             │
│                         │      SECURITY BOUNDARY          │                             │
│                         │      (Japan Traffic Only)       │                             │
│                         └─────────────────────────────────┘                             │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │                           JSZ OUTER DMZ                                            │  │
│  │                        (Japan IPs Only)                                            │  │
│  │                                                                                    │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │                     ENHANCED SECURITY LAYER                                  │ │  │
│  │   │                                                                              │ │  │
│  │   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │ │  │
│  │   │  │   WAF       │  │   IDS/IPS   │  │   Japan     │  │   Strict    │        │ │  │
│  │   │  │  (Enhanced) │  │   System    │  │   Geo-Lock  │  │   IP Allow  │        │ │  │
│  │   │  │             │  │             │  │             │  │   List      │        │ │  │
│  │   │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │ │  │
│  │   │                                                                              │ │  │
│  │   │                    ┌─────────────────┐                                       │ │  │
│  │   │                    │  Dedicated LB   │                                       │ │  │
│  │   │                    │  (Japan Only)   │                                       │ │  │
│  │   │                    └────────┬────────┘                                       │ │  │
│  │   │                             │                                                │ │  │
│  │   └─────────────────────────────┼────────────────────────────────────────────────┘ │  │
│  │                                 │                                                  │  │
│  └─────────────────────────────────┼──────────────────────────────────────────────────┘  │
│                                    │                                                     │
│                                    │ Japan Traffic Only                                  │
│                                    │                                                     │
│  ┌─────────────────────────────────┼──────────────────────────────────────────────────┐  │
│  │                                 ▼                                                  │  │
│  │                           JSZ INNER DMZ                                            │  │
│  │                        (Japan API Gateway)                                         │  │
│  │                                                                                    │  │
│  │   ┌───────────────────────────────────────────────────────────────────────────┐   │  │
│  │   │                    JSZ API GATEWAY CLUSTER                                 │   │  │
│  │   │                                                                            │   │  │
│  │   │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐        │   │  │
│  │   │   │                 │   │                 │   │                 │        │   │  │
│  │   │   │   Gateway #1    │   │   Gateway #2    │   │   Gateway #3    │        │   │  │
│  │   │   │   (Japan)       │   │   (Japan)       │   │   (Japan)       │        │   │  │
│  │   │   │                 │   │                 │   │                 │        │   │  │
│  │   │   │   Connects to   │   │   Connects to   │   │   Connects to   │        │   │  │
│  │   │   │   Core Zone DB  │   │   Core Zone DB  │   │   Core Zone DB  │        │   │  │
│  │   │   │                 │   │                 │   │                 │        │   │  │
│  │   │   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘        │   │  │
│  │   │            │                     │                     │                 │   │  │
│  │   └────────────┼─────────────────────┼─────────────────────┼─────────────────┘   │  │
│  │                │                     │                     │                     │  │
│  │                └─────────────────────┼─────────────────────┘                     │  │
│  │                                      │                                           │  │
│  │                                      │ VPN / Secure Channel                      │  │
│  │                                      │ to Core Zone                              │  │
│  │                                      │                                           │  │
│  └──────────────────────────────────────┼───────────────────────────────────────────┘  │
│                                         │                                              │
│                                         │ Secure Connection to Core Zone               │
│                                         │ • MySQL (Config & Rate Limit)              │
│                                         │ • Elasticsearch (Analytics)                  │
│                                         │                                              │
│                                         ▼                                              │
│                              ┌─────────────────────────────────────────┐               │
│                              │                                         │               │
│                              │            CORE ZONE                    │               │
│                              │                                         │               │
│                              │   ┌─────────────┐   ┌─────────────┐    │               │
│                              │   │  MySQL      │   │Elasticsearch│    │               │
│                              │   │  Database   │   │  Cluster    │    │               │
│                              │   │  (Shared)   │   │  (Shared)   │    │               │
│                              │   └─────────────┘   └─────────────┘    │               │
│                              │                                         │               │
│                              └─────────────────────────────────────────┘               │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```
</details>

### 5.2 JSZ Key Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Data Storage** | Uses Core Zone MySQL and Elasticsearch (shared) |
| **Network Access** | Japan IPs only for API traffic |
| **Config Sync** | Automatic sync from Core Zone MySQL |
| **Analytics** | Sent to Core Zone Elasticsearch |
| **Internal Gateway** | Dedicated Internal API Gateway in App Zone for JSZ internal apps |
| **Geo-Restriction** | Strict Japan-only access at edge |
| **Compliance** | Enhanced security for Japanese regulations (FISC, APPI) |
| **Audit** | Complete audit trail for all operations |

### 5.3 JSZ vs Global Regions Comparison

| Feature | Global Regions (US/EU/ASIA) | Japan Secure Zone (JSZ) |
|---------|----------------------------|-------------------------|
| Config Sync | Automatic from Core Zone | Automatic from Core Zone |
| Analytics | Sent to Core Zone ES | Sent to Core Zone ES |
| Database | Core Zone MySQL (shared) | Core Zone MySQL (shared) |
| Internet Egress | Allowed (to backends) | Japan backends only |
| API Definition Source | Core Zone | Core Zone |
| Real-time Sync | Yes | Yes |
| Geo-restriction | Configurable | **Japan only (strict)** |
| Compliance | Standard | Enhanced (FISC, APPI) |
| Internal Gateway | Core Zone only | **JSZ App Zone** |

### 5.4 JSZ Internal API Gateway

The JSZ includes a dedicated **Internal API Gateway** deployed within the JSZ App Zone. This gateway handles internal service-to-service communication within the Japan Secure Zone, providing:

- **Internal Application Routing**: Routes traffic between JSZ internal applications (admin dashboards, monitoring tools, CI/CD pipelines)
- **Service-to-Service Communication**: Manages communication between JSZ backend services
- **No Internet Exposure**: Unlike the external JSZ Gateway, the Internal Gateway is not accessible from the internet
- **Same Management**: Uses the same Core Zone MySQL and Elasticsearch for configuration and analytics
- **JSZ Isolation**: Completely isolated from other regions (US, EU, ASIA) and the internet

**Key Features:**
- Authentication and authorization for internal services
- Rate limiting for internal API calls
- Request/response logging to Core Zone Elasticsearch
- Audit trail for compliance (FISC, APPI)
- Load balancing across JSZ backend services

---

## 6. Core Zone - Control Plane

### 6.1 Core Zone Architecture

![Core Zone Architecture](diagrams/04-core-zone.svg)

<details>
<summary>View ASCII Diagram (fallback)</summary>

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                                    CORE ZONE                                             │
│                            (Centralized Control Plane)                                   │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │                         KUBERNETES CLUSTER                                         │  │
│  │                      (Multi-AZ Deployment)                                         │  │
│  │                                                                                    │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │                       MANAGEMENT PLANE                                       │ │  │
│  │   │                                                                              │ │  │
│  │   │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐          │ │  │
│  │   │   │                 │   │                 │   │                 │          │ │  │
│  │   │   │  Management     │   │  Management     │   │  Management     │          │ │  │
│  │   │   │  API #1         │   │  API #2         │   │  API #3         │          │ │  │
│  │   │   │                 │   │                 │   │                 │          │ │  │
│  │   │   │  (Primary)      │   │  (Replica)      │   │  (Replica)      │          │ │  │
│  │   │   │                 │   │                 │   │                 │          │ │  │
│  │   │   └─────────────────┘   └─────────────────┘   └─────────────────┘          │ │  │
│  │   │                                                                              │ │  │
│  │   │   Responsibilities:                                                          │ │  │
│  │   │   • API lifecycle management                                                │ │  │
│  │   │   • Policy configuration                                                    │ │  │
│  │   │   • User/application management                                             │ │  │
│  │   │   • Gateway registration                                                    │ │  │
│  │   │   • Config distribution to all regions                                      │ │  │
│  │   │                                                                              │ │  │
│  │   └─────────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                    │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │                        UI COMPONENTS                                         │ │  │
│  │   │                                                                              │ │  │
│  │   │   ┌─────────────────┐   ┌─────────────────┐                                 │ │  │
│  │   │   │                 │   │                 │                                 │ │  │
│  │   │   │   Console UI    │   │   Developer     │                                 │ │  │
│  │   │   │   (Admin)       │   │   Portal        │                                 │ │  │
│  │   │   │                 │   │                 │                                 │ │  │
│  │   │   │   • API Design  │   │   • API Catalog │                                 │ │  │
│  │   │   │   • Analytics   │   │   • Subscribe   │                                 │ │  │
│  │   │   │   • Monitoring  │   │   • Documentation│                                │ │  │
│  │   │   │                 │   │                 │                                 │ │  │
│  │   │   └─────────────────┘   └─────────────────┘                                 │ │  │
│  │   │                                                                              │ │  │
│  │   └─────────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │                         SHARED DATA STORES                                         │  │
│  │                                                                                    │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │                        MYSQL DATABASE                                        │ │  │
│  │   │                                                                              │ │  │
│  │   │   On-Premise MySQL Cluster                                                  │ │  │
│  │   │                                                                              │ │  │
│  │   │   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐                │ │  │
│  │   │   │   Primary     │   │   Secondary   │   │   Secondary   │                │ │  │
│  │   │   │   (Write)     │   │   (Read)      │   │   (Read)      │                │ │  │
│  │   │   └───────────────┘   └───────────────┘   └───────────────┘                │ │  │
│  │   │                                                                              │ │  │
│  │   │   Databases:                                                                 │ │  │
│  │   │   • gravitee (API definitions, plans, subscriptions)                        │ │  │
│  │   │   • gravitee_us (US region rate limits)                                     │ │  │
│  │   │   • gravitee_eu (EU region rate limits)                                     │ │  │
│  │   │   • gravitee_asia (ASIA region rate limits)                                 │ │  │
│  │   │   • gravitee_jsz (JSZ region rate limits)                                   │ │  │
│  │   │                                                                              │ │  │
│  │   │   Note: All regions including JSZ use this shared MySQL                      │ │  │
│  │   │                                                                              │ │  │
│  │   └─────────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                    │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │                       ELASTICSEARCH CLUSTER                                  │ │  │
│  │   │                                                                              │ │  │
│  │   │   Cluster: On-Premise Elasticsearch Cluster                                │ │  │
│  │   │                                                                              │ │  │
│  │   │   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐                │ │  │
│  │   │   │   Data Node   │   │   Data Node   │   │   Data Node   │                │ │  │
│  │   │   │      #1       │   │      #2       │   │      #3       │                │ │  │
│  │   │   └───────────────┘   └───────────────┘   └───────────────┘                │ │  │
│  │   │                                                                              │ │  │
│  │   │   Indices:                                                                   │ │  │
│  │   │   • gravitee-request-us-* (US region analytics)                             │ │  │
│  │   │   • gravitee-request-eu-* (EU region analytics)                             │ │  │
│  │   │   • gravitee-request-asia-* (ASIA region analytics)                         │ │  │
│  │   │   • gravitee-request-jsz-* (JSZ region analytics)                           │ │  │
│  │   │   • gravitee-health-* (Gateway health)                                      │ │  │
│  │   │   • gravitee-monitor-* (System monitoring)                                  │ │  │
│  │   │                                                                              │ │  │
│  │   │   Note: All regions including JSZ send analytics here                       │ │  │
│  │   │   Cluster: On-Premise Elasticsearch                                         │ │  │
│  │   │                                                                              │ │  │
│  │   └─────────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                    │  │
│  │                      REGIONAL CONNECTIVITY                                         │  │
│  │                                                                                    │  │
│  │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐                │  │
│  │   │                 │   │                 │   │                 │                │  │
│  │   │   US Region     │   │   EU Region     │   │  ASIA Region    │                │  │
│  │   │   VPN/Private   │   │   VPN/Private   │   │   VPN/Private   │                │  │
│  │   │   Link          │   │   Link          │   │   Link          │                │  │
│  │   │                 │   │                 │   │                 │                │  │
│  │   │   ◄──────────►  │   │   ◄──────────►  │   │   ◄──────────►  │                │  │
│  │   │   Bidirectional │   │   Bidirectional │   │   Bidirectional │                │  │
│  │   │   Sync          │   │   Sync          │   │   Sync          │                │  │
│  │   │                 │   │   (GDPR aware)  │   │                 │                │  │
│  │   └─────────────────┘   └─────────────────┘   └─────────────────┘                │  │
│  │                                                                                    │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │                                                                              │ │  │
│  │   │                    JSZ LIMITED CONNECTION                                    │ │  │
│  │   │                                                                              │ │  │
│  │   │   ┌─────────────────┐                                                       │ │  │
│  │   │   │                 │                                                       │ │  │
│  │   │   │   JSZ Config    │                                                       │ │  │
│  │   │   │   Gateway       │                                                       │ │  │
│  │   │   │                 │                                                       │ │  │
│  │   │   │   ◄────────     │  One-Way (Config Import Only)                        │ │  │
│  │   │   │   (Inbound      │  Manual Approval Required                            │ │  │
│  │   │   │    Only)        │  No Analytics Export                                 │ │  │
│  │   │   │                 │                                                       │ │  │
│  │   │   └─────────────────┘                                                       │ │  │
│  │   │                                                                              │ │  │
│  │   └─────────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```
</details>

### 6.2 Core Zone Responsibilities

| Function | Description | Scope |
|----------|-------------|-------|
| API Management | Create, update, delete API definitions | All regions |
| Policy Management | Configure security and traffic policies | All regions |
| User Management | Manage admin users and roles | All regions |
| Application Management | Manage API consumer applications | All regions |
| Analytics Aggregation | Collect and store analytics from global regions | US, EU, ASIA only |
| Gateway Registration | Track and manage gateway instances | All regions |
| Config Distribution | Push configurations to gateways | All regions (JSZ limited) |

---

## 7. Internal API Gateway

### 7.1 Internal Gateway Overview

The Internal API Gateway is deployed within the Core Zone to handle **internal service-to-service communication**, **admin APIs**, and **internal application traffic**. Unlike external gateways, the Internal Gateway is not exposed to the internet and only serves internal consumers within the corporate network.

![Internal API Gateway](diagrams/06-internal-gateway.svg)

<details>
<summary>View ASCII Diagram (fallback)</summary>

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                          INTERNAL API GATEWAY ARCHITECTURE                               │
│                                                                                          │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │                           INTERNAL CONSUMERS                                     │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│   │   │  Internal   │  │   Admin     │  │   CI/CD     │  │  Backend    │           │   │
│   │   │    Apps     │  │   Tools     │  │  Pipelines  │  │  Services   │           │   │
│   │   │             │  │             │  │             │  │             │           │   │
│   │   │ • CRM       │  │ • Grafana   │  │ • Jenkins   │  │ • Payment   │           │   │
│   │   │ • ERP       │  │ • Kibana    │  │ • ArgoCD    │  │ • Inventory │           │   │
│   │   │ • HR System │  │ • Admin UI  │  │ • GitLab    │  │ • Billing   │           │   │
│   │   │             │  │             │  │             │  │             │           │   │
│   │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘           │   │
│   │          │                │                │                │                   │   │
│   │          └────────────────┴────────────────┴────────────────┘                   │   │
│   │                                    │                                            │   │
│   │                                    │ Internal Network Only                      │   │
│   │                                    │ (No Internet Access)                       │   │
│   │                                    ▼                                            │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │                              CORE ZONE                                           │   │
│   │                                                                                  │   │
│   │   ┌─────────────────────────────────────────────────────────────────────────┐   │   │
│   │   │                                                                          │   │   │
│   │   │                    INTERNAL API GATEWAY CLUSTER                          │   │   │
│   │   │                                                                          │   │   │
│   │   │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐       │   │   │
│   │   │   │                 │   │                 │   │                 │       │   │   │
│   │   │   │  Internal GW #1 │   │  Internal GW #2 │   │  Internal GW #3 │       │   │   │
│   │   │   │    (Active)     │   │    (Active)     │   │    (Active)     │       │   │   │
│   │   │   │                 │   │                 │   │                 │       │   │   │
│   │   │   │   Port: 8082    │   │   Port: 8082    │   │   Port: 8082    │       │   │   │
│   │   │   │                 │   │                 │   │                 │       │   │   │
│   │   │   │ ┌─────────────┐ │   │ ┌─────────────┐ │   │ ┌─────────────┐ │       │   │   │
│   │   │   │ │ Policies:   │ │   │ │ Policies:   │ │   │ │ Policies:   │ │       │   │   │
│   │   │   │ │ • mTLS      │ │   │ │ • mTLS      │ │   │ │ • mTLS      │ │       │   │   │
│   │   │   │ │ • JWT       │ │   │ │ • JWT       │ │   │ │ • JWT       │ │       │   │   │
│   │   │   │ │ • Rate Limit│ │   │ │ • Rate Limit│ │   │ │ • Rate Limit│ │       │   │   │
│   │   │   │ │ • Logging   │ │   │ │ • Logging   │ │   │ │ • Logging   │ │       │   │   │
│   │   │   │ └─────────────┘ │   │ └─────────────┘ │   │ └─────────────┘ │       │   │   │
│   │   │   │                 │   │                 │   │                 │       │   │   │
│   │   │   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘       │   │   │
│   │   │            │                     │                     │                │   │   │
│   │   │            └─────────────────────┼─────────────────────┘                │   │   │
│   │   │                                  │                                      │   │   │
│   │   └──────────────────────────────────┼──────────────────────────────────────┘   │   │
│   │                                      │                                          │   │
│   │                                      │                                          │   │
│   │   ┌──────────────────────────────────┼──────────────────────────────────────┐   │   │
│   │   │                                  ▼                                      │   │   │
│   │   │                    INTERNAL BACKEND SERVICES                            │   │   │
│   │   │                                                                         │   │   │
│   │   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │   │
│   │   │   │  User       │  │  Inventory  │  │  Payment    │  │  Reporting  │   │   │   │
│   │   │   │  Service    │  │  Service    │  │  Service    │  │  Service    │   │   │   │
│   │   │   │             │  │             │  │             │  │             │   │   │   │
│   │   │   │  /api/users │  │/api/inventory│ │ /api/payment│  │/api/reports │   │   │   │
│   │   │   │             │  │             │  │             │  │             │   │   │   │
│   │   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │   │   │
│   │   │                                                                         │   │   │
│   │   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │   │
│   │   │   │  Auth       │  │  Config     │  │  Messaging  │  │  Audit      │   │   │   │
│   │   │   │  Service    │  │  Service    │  │  Service    │  │  Service    │   │   │   │
│   │   │   │             │  │             │  │             │  │             │   │   │   │
│   │   │   │  /api/auth  │  │ /api/config │  │/api/messages│  │ /api/audit  │   │   │   │
│   │   │   │             │  │             │  │             │  │             │   │   │   │
│   │   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │   │   │
│   │   │                                                                         │   │   │
│   │   └─────────────────────────────────────────────────────────────────────────┘   │   │
│   │                                                                                  │   │
│   │   Uses same MySQL and Elasticsearch as external gateways                      │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```
</details>

### 7.2 Internal Gateway vs External Gateway Comparison

| Feature | External Gateway (US/EU/ASIA) | Internal Gateway (Core Zone) |
|---------|------------------------------|------------------------------|
| **Location** | Regional DMZ | Core Zone |
| **Access** | Internet-facing | Internal network only |
| **Consumers** | External API consumers | Internal apps, services, admin tools |
| **Authentication** | API Key, OAuth2, JWT | mTLS, JWT, Service Accounts |
| **Rate Limiting** | Per consumer/plan | Per service/team |
| **TLS** | TLS termination at LB | End-to-end mTLS |
| **Monitoring** | Public API metrics | Internal service metrics |
| **APIs Exposed** | Public APIs | Internal/Admin APIs |

### 7.3 Internal Gateway Use Cases

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                         INTERNAL GATEWAY USE CASES                                       │
│                                                                                          │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │   USE CASE 1: SERVICE-TO-SERVICE COMMUNICATION                                  │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐              │   │
│   │   │  Order      │  ────►  │  Internal   │  ────►  │  Inventory  │              │   │
│   │   │  Service    │  mTLS   │  Gateway    │  mTLS   │  Service    │              │   │
│   │   │             │         │             │         │             │              │   │
│   │   │ POST /order │         │ /api/       │         │ GET /stock  │              │   │
│   │   │             │         │ inventory   │         │             │              │   │
│   │   └─────────────┘         └─────────────┘         └─────────────┘              │   │
│   │                                                                                  │   │
│   │   Benefits:                                                                      │   │
│   │   • Centralized authentication                                                  │   │
│   │   • Traffic monitoring and logging                                              │   │
│   │   • Rate limiting between services                                              │   │
│   │   • Circuit breaker patterns                                                    │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │   USE CASE 2: ADMIN API ACCESS                                                  │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐              │   │
│   │   │  Admin      │  ────►  │  Internal   │  ────►  │  Admin      │              │   │
│   │   │  Console    │  JWT    │  Gateway    │  JWT    │  API        │              │   │
│   │   │             │         │             │         │             │              │   │
│   │   │ Grafana     │         │ /admin/     │         │ Metrics     │              │   │
│   │   │ Kibana      │         │ /metrics/   │         │ Config      │              │   │
│   │   └─────────────┘         └─────────────┘         └─────────────┘              │   │
│   │                                                                                  │   │
│   │   Benefits:                                                                      │   │
│   │   • Centralized admin access control                                            │   │
│   │   • Audit logging for all admin operations                                      │   │
│   │   • Role-based access control (RBAC)                                            │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │   USE CASE 3: CI/CD PIPELINE INTEGRATION                                        │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐              │   │
│   │   │  CI/CD      │  ────►  │  Internal   │  ────►  │  Deploy     │              │   │
│   │   │  Pipeline   │  Token  │  Gateway    │  Token  │  Service    │              │   │
│   │   │             │         │             │         │             │              │   │
│   │   │ Jenkins     │         │ /deploy/    │         │ K8s API     │              │   │
│   │   │ ArgoCD      │         │ /config/    │         │ Config Mgmt │              │   │
│   │   └─────────────┘         └─────────────┘         └─────────────┘              │   │
│   │                                                                                  │   │
│   │   Benefits:                                                                      │   │
│   │   • Secure deployment API access                                                │   │
│   │   • Deployment audit trail                                                      │   │
│   │   • Rate limiting for deployment operations                                     │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │   USE CASE 4: INTERNAL APPLICATION ACCESS                                       │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐              │   │
│   │   │  Internal   │  ────►  │  Internal   │  ────►  │  Backend    │              │   │
│   │   │  Web App    │  SSO    │  Gateway    │  SSO    │  APIs       │              │   │
│   │   │             │         │             │         │             │              │   │
│   │   │ CRM         │         │ /crm/       │         │ Customer    │              │   │
│   │   │ ERP         │         │ /erp/       │         │ Finance     │              │   │
│   │   │ HR Portal   │         │ /hr/        │         │ Employee    │              │   │
│   │   └─────────────┘         └─────────────┘         └─────────────┘              │   │
│   │                                                                                  │   │
│   │   Benefits:                                                                      │   │
│   │   • Single sign-on (SSO) integration                                            │   │
│   │   • Unified API access for internal apps                                        │   │
│   │   • Consistent security policies                                                │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.4 Internal Gateway Security Model

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                      INTERNAL GATEWAY SECURITY MODEL                                     │
│                                                                                          │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │                         AUTHENTICATION METHODS                                   │   │
│   │                                                                                  │   │
│   │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐              │   │
│   │   │                 │   │                 │   │                 │              │   │
│   │   │      mTLS       │   │       JWT       │   │  Service        │              │   │
│   │   │                 │   │                 │   │  Account        │              │   │
│   │   │ • Client cert   │   │ • Token-based   │   │                 │              │   │
│   │   │ • Server cert   │   │ • Claims verify │   │ • K8s SA        │              │   │
│   │   │ • Mutual auth   │   │ • Expiry check  │   │ • SPIFFE/SPIRE  │              │   │
│   │   │                 │   │                 │   │ • Workload ID   │              │   │
│   │   └─────────────────┘   └─────────────────┘   └─────────────────┘              │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │                         AUTHORIZATION POLICIES                                   │   │
│   │                                                                                  │   │
│   │   ┌─────────────────────────────────────────────────────────────────────────┐   │   │
│   │   │                                                                          │   │   │
│   │   │   Service A (Order Service)                                              │   │   │
│   │   │   ├── Can access: /api/inventory (GET)                                  │   │   │
│   │   │   ├── Can access: /api/payment (POST)                                   │   │   │
│   │   │   └── Cannot access: /api/admin/*                                       │   │   │
│   │   │                                                                          │   │   │
│   │   │   Service B (Admin Service)                                              │   │   │
│   │   │   ├── Can access: /api/admin/* (ALL)                                    │   │   │
│   │   │   ├── Can access: /api/config (GET, PUT)                                │   │   │
│   │   │   └── Cannot access: /api/payment/*                                     │   │   │
│   │   │                                                                          │   │   │
│   │   │   CI/CD Pipeline                                                         │   │   │
│   │   │   ├── Can access: /deploy/* (POST)                                      │   │   │
│   │   │   ├── Can access: /config/* (GET, PUT)                                  │   │   │
│   │   │   └── Rate limited: 10 requests/minute                                  │   │   │
│   │   │                                                                          │   │   │
│   │   └─────────────────────────────────────────────────────────────────────────┘   │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │                         NETWORK SECURITY                                         │   │
│   │                                                                                  │   │
│   │   • Internal Gateway only accessible from Core Zone network                     │   │
│   │   • No internet ingress or egress                                               │   │
│   │   • All traffic encrypted with mTLS                                             │   │
│   │   • Network policies restrict pod-to-pod communication                          │   │
│   │   • Service mesh integration (optional: Istio/Linkerd)                          │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.5 Internal Gateway Firewall Rules

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      INTERNAL GATEWAY FIREWALL RULES                                     │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ INT-1  │ ALLOW  │   8082   │   TCP/HTTPS     │ Core Zone Apps  │ Internal Apps     │ │
│  │ INT-2  │ ALLOW  │   8082   │   TCP/HTTPS     │ Admin Network   │ Admin Tools       │ │
│  │ INT-3  │ ALLOW  │   8082   │   TCP/HTTPS     │ CI/CD Network   │ Pipeline Access   │ │
│  │ INT-4  │ ALLOW  │   8082   │   TCP/HTTPS     │ K8s Pods        │ Service-to-Service│ │
│  │ INT-5  │ ALLOW  │   9090   │   TCP/HTTP      │ Monitoring      │ Prometheus        │ │
│  │ INT-6  │ DENY   │   ALL    │      ALL        │ External/DMZ    │ No external access│ │
│  │ INT-7  │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ INT-8  │ ALLOW  │  80/443  │  TCP/HTTP(S)    │ Core Zone Svcs  │ Backend Services  │ │
│  │ INT-9  │ ALLOW  │   3306   │   TCP/TLS       │ MySQL           │ Config/Rate Limit │ │
│  │ INT-10 │ ALLOW  │   443    │   TCP/HTTPS     │ Elasticsearch   │ Analytics         │ │
│  │ INT-11 │ ALLOW  │    53    │   UDP/TCP       │ DNS Servers     │ DNS Resolution    │ │
│  │ INT-12 │ DENY   │   ALL    │      ALL        │ Internet        │ No internet egress│ │
│  │ INT-13 │ DENY   │   ALL    │      ALL        │ External GW     │ No external GW    │ │
│  │ INT-14 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  ⚠️  INTERNAL GATEWAY HAS NO ACCESS TO:                                                 │
│      • Internet                                                                          │
│      • External DMZ zones (US, EU, ASIA Outer/Inner DMZ)                                │
│      • JSZ (Japan Secure Zone)                                                          │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.6 Internal Gateway Configuration

| Configuration | Value | Description |
|---------------|-------|-------------|
| **Replicas** | 3 | High availability |
| **Port** | 8082 | Gateway HTTP port |
| **TLS** | mTLS required | Mutual TLS for all traffic |
| **Rate Limiting** | Per service | Service-specific limits |
| **Logging** | Full request/response | Complete audit trail |
| **Analytics** | Internal ES index | Separate from external |
| **Sync** | Same MySQL | Shared config with external GW |

### 7.7 Internal APIs Catalog

| API Category | Context Path | Description | Consumers |
|--------------|--------------|-------------|-----------|
| **User Service** | /api/users | User management | CRM, HR, Admin |
| **Inventory** | /api/inventory | Stock management | Order, ERP |
| **Payment** | /api/payment | Payment processing | Order, Finance |
| **Config** | /api/config | Configuration management | All services |
| **Audit** | /api/audit | Audit logging | Admin, Compliance |
| **Deploy** | /deploy | Deployment operations | CI/CD only |
| **Admin** | /admin | Administrative APIs | Admin tools only |
| **Metrics** | /metrics | Internal metrics | Monitoring |

---

## 8. Data Flow Architecture

### 7.1 Global API Request Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                           GLOBAL API REQUEST FLOW                                        │
│                                                                                          │
│                                                                                          │
│   ┌──────────────┐                                                                      │
│   │              │                                                                      │
│   │  API Client  │                                                                      │
│   │  (US Based)  │                                                                      │
│   │              │                                                                      │
│   └──────┬───────┘                                                                      │
│          │                                                                               │
│          │ 1. DNS Query: api.company.com                                                │
│          ▼                                                                               │
│   ┌──────────────┐                                                                      │
│   │              │                                                                      │
│   │  GeoDNS /    │  Returns: us-api.company.com (closest region)                       │
│   │  GSLB        │                                                                      │
│   │              │                                                                      │
│   └──────┬───────┘                                                                      │
│          │                                                                               │
│          │ 2. HTTPS Request to US Region                                                │
│          ▼                                                                               │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                           US REGION                                              │   │
│   │                                                                                  │   │
│   │   ┌────────────────────────────────────────────────────────────────────────┐   │   │
│   │   │                        OUTER DMZ                                        │   │   │
│   │   │                                                                         │   │   │
│   │   │   3. WAF Inspection ──► 4. DDoS Check ──► 5. SSL Termination           │   │   │
│   │   │                                                │                        │   │   │
│   │   └────────────────────────────────────────────────┼────────────────────────┘   │   │
│   │                                                    │                            │   │
│   │   ┌────────────────────────────────────────────────┼────────────────────────┐   │   │
│   │   │                        INNER DMZ               │                        │   │   │
│   │   │                                                ▼                        │   │   │
│   │   │   ┌────────────────────────────────────────────────────────────────┐   │   │   │
│   │   │   │                    API GATEWAY                                  │   │   │   │
│   │   │   │                                                                 │   │   │   │
│   │   │   │  6. Route     7. Auth      8. Rate     9. Policy   10. Backend │   │   │   │
│   │   │   │     Match ──►    Check ──►    Limit ──►   Apply ──►    Call    │   │   │   │
│   │   │   │                                                                 │   │   │   │
│   │   │   └─────────────────────────────────────────────────────┬───────────┘   │   │   │
│   │   │                                                         │               │   │   │
│   │   └─────────────────────────────────────────────────────────┼───────────────┘   │   │
│   │                                                             │                   │   │
│   │   ┌─────────────────────────────────────────────────────────┼───────────────┐   │   │
│   │   │                    APPLICATION ZONE                     │               │   │   │
│   │   │                                                         ▼               │   │   │
│   │   │                              ┌─────────────────────────────┐            │   │   │
│   │   │                              │                             │            │   │   │
│   │   │                              │    11. Backend Service      │            │   │   │
│   │   │                              │        Processing           │            │   │   │
│   │   │                              │                             │            │   │   │
│   │   │                              └──────────────┬──────────────┘            │   │   │
│   │   │                                             │                           │   │   │
│   │   └─────────────────────────────────────────────┼───────────────────────────┘   │   │
│   │                                                 │                               │   │
│   │                                                 │ 12. Response                  │   │
│   │                                                 ▼                               │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                     │                                    │
│                                                     │ 13. Response to Client            │
│                                                     ▼                                    │
│   ┌──────────────┐                                                                      │
│   │              │                                                                      │
│   │  API Client  │  ◄──── 200 OK + Response Body                                       │
│   │              │                                                                      │
│   └──────────────┘                                                                      │
│                                                                                          │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │                      ASYNC: ANALYTICS FLOW                                       │   │
│   │                                                                                  │   │
│   │   Gateway ──► 14. Log Request ──► 15. Push to ES ──► Core Zone Elasticsearch   │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Configuration Sync Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                         CONFIGURATION SYNC FLOW                                          │
│                                                                                          │
│                                                                                          │
│   ┌──────────────┐                                                                      │
│   │              │                                                                      │
│   │    Admin     │                                                                      │
│   │    User      │                                                                      │
│   │              │                                                                      │
│   └──────┬───────┘                                                                      │
│          │                                                                               │
│          │ 1. Create/Update API                                                         │
│          ▼                                                                               │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │                              CORE ZONE                                           │   │
│   │                                                                                  │   │
│   │   ┌────────────────┐                                                            │   │
│   │   │                │                                                            │   │
│   │   │  Console UI    │                                                            │   │
│   │   │                │                                                            │   │
│   │   └───────┬────────┘                                                            │   │
│   │           │                                                                      │   │
│   │           │ 2. API Call                                                         │   │
│   │           ▼                                                                      │   │
│   │   ┌────────────────┐                                                            │   │
│   │   │                │                                                            │   │
│   │   │ Management API │                                                            │   │
│   │   │                │                                                            │   │
│   │   └───────┬────────┘                                                            │   │
│   │           │                                                                      │   │
│   │           │ 3. Store                                                            │   │
│   │           ▼                                                                      │   │
│   │   ┌────────────────┐                                                            │   │
│   │   │                │                                                            │   │
│   │   │  MySQL         │  ◄──── API Definition stored                              │   │
│   │   │  Database      │                                                            │   │
│   │   │                │                                                            │   │
│   │   └───────┬────────┘                                                            │   │
│   │           │                                                                      │   │
│   │           │ 4. Trigger Sync Event                                               │   │
│   │           │                                                                      │   │
│   └───────────┼──────────────────────────────────────────────────────────────────────┘   │
│               │                                                                          │
│               │                                                                          │
│      ┌────────┴────────┬─────────────────┬─────────────────┬─────────────────┐         │
│      │                 │                 │                 │                 │         │
│      ▼                 ▼                 ▼                 ▼                 │         │
│  ┌────────┐       ┌────────┐       ┌────────┐       ┌────────┐              │         │
│  │   US   │       │   EU   │       │  ASIA  │       │  JSZ   │              │         │
│  │ Region │       │ Region │       │ Region │       │        │              │         │
│  └───┬────┘       └───┬────┘       └───┬────┘       └───┬────┘              │         │
│      │                │                │                │                   │         │
│      │ 5a. Poll      │ 5b. Poll      │ 5c. Poll      │ 5d. Manual        │         │
│      │    MySQL      │    MySQL      │    MySQL      │     Approval      │         │
│      │               │               │               │     Required      │         │
│      ▼               ▼               ▼               ▼                   │         │
│  ┌────────┐     ┌────────┐     ┌────────┐     ┌────────────────┐        │         │
│  │Gateway │     │Gateway │     │Gateway │     │ Config Gateway │        │         │
│  │Cluster │     │Cluster │     │Cluster │     │ (JSZ)          │        │         │
│  │        │     │        │     │        │     │                │        │         │
│  │ Auto   │     │ Auto   │     │ Auto   │     │ Manual Import  │        │         │
│  │ Sync   │     │ Sync   │     │ Sync   │     │ After Approval │        │         │
│  └────────┘     └────────┘     └────────┘     └────────────────┘        │         │
│      │               │               │                │                  │         │
│      │ 6. Deploy    │ 6. Deploy    │ 6. Deploy     │ 6. Deploy        │         │
│      │    API       │    API       │    API        │    API (Manual)  │         │
│      ▼               ▼               ▼                ▼                  │         │
│  ┌────────┐     ┌────────┐     ┌────────┐     ┌────────────────┐        │         │
│  │  API   │     │  API   │     │  API   │     │     API        │        │         │
│  │ Ready  │     │ Ready  │     │ Ready  │     │    Ready       │        │         │
│  │        │     │        │     │        │     │   (Isolated)   │        │         │
│  └────────┘     └────────┘     └────────┘     └────────────────┘        │         │
│                                                                          │         │
│                                                                          │         │
│   Sync Timing:                                                           │         │
│   ┌──────────────────────────────────────────────────────────────────┐  │         │
│   │  US/EU/ASIA: ~5 seconds (automatic)                              │  │         │
│   │  JSZ: Manual approval process (minutes to hours)                 │  │         │
│   └──────────────────────────────────────────────────────────────────┘  │         │
│                                                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Security Architecture

### 8.1 Defense in Depth Model

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                           DEFENSE IN DEPTH - SECURITY LAYERS                             │
│                                                                                          │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │   LAYER 1: PERIMETER SECURITY (Outer DMZ)                                       │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│   │   │    WAF      │  │   DDoS      │  │    CDN      │  │   Geo       │           │   │
│   │   │             │  │ Protection  │  │   (Edge)    │  │  Blocking   │           │   │
│   │   │ • OWASP     │  │             │  │             │  │             │           │   │
│   │   │ • SQL Inj   │  │ • Rate      │  │ • Cache     │  │ • Country   │           │   │
│   │   │ • XSS       │  │   Limit     │  │ • TLS       │  │ • IP Range  │           │   │
│   │   │ • Bot       │  │ • Shield    │  │ • Compress  │  │             │           │   │
│   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘           │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│                                          ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │   LAYER 2: API SECURITY (Inner DMZ - Gateway)                                   │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│   │   │   API Key   │  │   OAuth2    │  │    JWT      │  │   mTLS      │           │   │
│   │   │             │  │   / OIDC    │  │             │  │             │           │   │
│   │   │ • Validate  │  │             │  │ • Signature │  │ • Cert      │           │   │
│   │   │ • Revoke    │  │ • Token     │  │ • Claims    │  │   Verify    │           │   │
│   │   │ • Rotate    │  │   Introspect│  │ • Expiry    │  │ • Chain     │           │   │
│   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘           │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│   │   │   Rate      │  │   Quota     │  │   IP        │  │  Payload    │           │   │
│   │   │   Limiting  │  │             │  │  Filtering  │  │  Validation │           │   │
│   │   │             │  │             │  │             │  │             │           │   │
│   │   │ • Per API   │  │ • Daily     │  │ • Whitelist │  │ • Schema    │           │   │
│   │   │ • Per User  │  │ • Monthly   │  │ • Blacklist │  │ • Size      │           │   │
│   │   │ • Global    │  │ • Per Plan  │  │             │  │ • Type      │           │   │
│   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘           │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│                                          ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │   LAYER 3: NETWORK SECURITY                                                     │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│   │   │  Network    │  │   VPN /     │  │  Firewall   │  │   IDS /     │           │   │
│   │   │ Segmentation│  │PrivateLink  │  │   Rules     │  │    IPS      │           │   │
│   │   │             │  │             │  │             │  │             │           │   │
│   │   │ • VPC       │  │ • Site-to-  │  │ • Ingress   │  │ • Detect    │           │   │
│   │   │ • Subnets   │  │   Site      │  │ • Egress    │  │ • Prevent   │           │   │
│   │   │ • NSG       │  │ • P2P       │  │ • Stateful  │  │ • Alert     │           │   │
│   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘           │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│                                          ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │   LAYER 4: DATA SECURITY                                                        │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│   │   │ Encryption  │  │  Encryption │  │   Secret    │  │   Data      │           │   │
│   │   │  at Rest    │  │  in Transit │  │  Management │  │   Masking   │           │   │
│   │   │             │  │             │  │             │  │             │           │   │
│   │   │ • AES-256   │  │ • TLS 1.3   │  │ • Vault     │  │ • PII       │           │   │
│   │   │ • KMS       │  │ • mTLS      │  │ • KMS       │  │ • Logs      │           │   │
│   │   │             │  │             │  │ • Rotation  │  │ • Analytics │           │   │
│   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘           │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│                                          ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │   LAYER 5: IDENTITY & ACCESS MANAGEMENT                                         │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│   │   │    RBAC     │  │    SSO      │  │    MFA      │  │   Audit     │           │   │
│   │   │             │  │             │  │             │  │   Logging   │           │   │
│   │   │             │  │             │  │             │  │             │           │   │
│   │   │ • Roles     │  │ • SAML      │  │ • TOTP      │  │ • Who       │           │   │
│   │   │ • Perms     │  │ • OIDC      │  │ • WebAuthn  │  │ • What      │           │   │
│   │   │ • Scope     │  │ • LDAP      │  │ • SMS       │  │ • When      │           │   │
│   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘           │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Security Controls by Zone

| Zone | Security Controls |
|------|-------------------|
| **Outer DMZ** | WAF, DDoS protection, SSL termination, Geo-blocking, Bot detection |
| **Inner DMZ** | API authentication, Rate limiting, Payload validation, IP filtering |
| **Application Zone** | mTLS, Service mesh, Network policies |
| **Core Zone** | RBAC, MFA, Encryption at rest, Audit logging |
| **JSZ** | All above + Air-gap capability, Data diode, Manual approvals |

---

## 10. Firewall Rules by Zone

### 9.1 Global Regions (US/EU/ASIA) Firewall Rules

#### Outer DMZ

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                     OUTER DMZ FIREWALL RULES (Global Regions)                            │
│                                                                                          │
│  INBOUND:                                                                                │
│  ┌───────────┬──────────┬────────────────┬──────────────────┬───────────────────────┐   │
│  │   Rule    │   Port   │    Protocol    │      Source      │       Purpose         │   │
│  ├───────────┼──────────┼────────────────┼──────────────────┼───────────────────────┤   │
│  │  DMZ-I-1  │   443    │   TCP/HTTPS    │    0.0.0.0/0     │ API Traffic           │   │
│  │  DMZ-I-2  │    80    │    TCP/HTTP    │    0.0.0.0/0     │ Redirect to HTTPS     │   │
│  │  DMZ-I-3  │   ALL    │      ALL       │    Blocked*      │ Geo-blocked countries │   │
│  └───────────┴──────────┴────────────────┴──────────────────┴───────────────────────┘   │
│                                                                                          │
│  OUTBOUND:                                                                               │
│  ┌───────────┬──────────┬────────────────┬──────────────────┬───────────────────────┐   │
│  │   Rule    │   Port   │    Protocol    │   Destination    │       Purpose         │   │
│  ├───────────┼──────────┼────────────────┼──────────────────┼───────────────────────┤   │
│  │  DMZ-O-1  │   8082   │    TCP/HTTP    │   Inner DMZ      │ Gateway Traffic       │   │
│  │  DMZ-O-2  │    53    │    UDP/TCP     │   DNS Servers    │ DNS Resolution        │   │
│  └───────────┴──────────┴────────────────┴──────────────────┴───────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Inner DMZ

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                     INNER DMZ FIREWALL RULES (Global Regions)                            │
│                                                                                          │
│  INBOUND:                                                                                │
│  ┌───────────┬──────────┬────────────────┬──────────────────┬───────────────────────┐   │
│  │   Rule    │   Port   │    Protocol    │      Source      │       Purpose         │   │
│  ├───────────┼──────────┼────────────────┼──────────────────┼───────────────────────┤   │
│  │  INN-I-1  │   8082   │    TCP/HTTP    │    Outer DMZ     │ Gateway Traffic       │   │
│  │  INN-I-2  │    22    │    TCP/SSH     │   Admin IPs      │ Management Access     │   │
│  └───────────┴──────────┴────────────────┴──────────────────┴───────────────────────┘   │
│                                                                                          │
│  OUTBOUND:                                                                               │
│  ┌───────────┬──────────┬────────────────┬──────────────────┬───────────────────────┐   │
│  │   Rule    │   Port   │    Protocol    │   Destination    │       Purpose         │   │
│  ├───────────┼──────────┼────────────────┼──────────────────┼───────────────────────┤   │
│  │  INN-O-1  │  80/443  │  TCP/HTTP(S)   │  Application Zone│ Backend Calls         │   │
│  │  INN-O-2  │   3306   │    TCP/TLS     │   Core Zone      │ MySQL (Config)        │   │
│  │  INN-O-3  │   443    │   TCP/HTTPS    │   Core Zone      │ Elasticsearch         │   │
│  │  INN-O-4  │    53    │    UDP/TCP     │   DNS Servers    │ DNS Resolution        │   │
│  │  INN-O-5  │   123    │      UDP       │   NTP Servers    │ Time Sync             │   │
│  └───────────┴──────────┴────────────────┴──────────────────┴───────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Japan Secure Zone (JSZ) Firewall Rules

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                     JSZ FIREWALL RULES (Enhanced Security)                               │
│                                                                                          │
│  JSZ OUTER DMZ - INBOUND:                                                               │
│  ┌───────────┬──────────┬────────────────┬──────────────────┬───────────────────────┐   │
│  │   Rule    │   Port   │    Protocol    │      Source      │       Purpose         │   │
│  ├───────────┼──────────┼────────────────┼──────────────────┼───────────────────────┤   │
│  │  JSZ-I-1  │   443    │   TCP/HTTPS    │  Japan IPs Only  │ API Traffic (JP only) │   │
│  │  JSZ-I-2  │   ALL    │      ALL       │  Non-JP Blocked  │ Strict Geo-blocking   │   │
│  └───────────┴──────────┴────────────────┴──────────────────┴───────────────────────┘   │
│                                                                                          │
│  JSZ INNER DMZ - INBOUND:                                                               │
│  ┌───────────┬──────────┬────────────────┬──────────────────┬───────────────────────┐   │
│  │   Rule    │   Port   │    Protocol    │      Source      │       Purpose         │   │
│  ├───────────┼──────────┼────────────────┼──────────────────┼───────────────────────┤   │
│  │  JSZ-I-3  │   8082   │    TCP/HTTP    │   JSZ Outer DMZ  │ Gateway Traffic       │   │
│  │  JSZ-I-4  │    22    │    TCP/SSH     │   JSZ Admin IPs  │ Management (Local)    │   │
│  └───────────┴──────────┴────────────────┴──────────────────┴───────────────────────┘   │
│                                                                                          │
│  JSZ INNER DMZ - OUTBOUND:                                                              │
│  ┌───────────┬──────────┬────────────────┬──────────────────┬───────────────────────┐   │
│  │   Rule    │   Port   │    Protocol    │   Destination    │       Purpose         │   │
│  ├───────────┼──────────┼────────────────┼──────────────────┼───────────────────────┤   │
│  │  JSZ-O-1  │  80/443  │  TCP/HTTP(S)   │  JSZ App Zone    │ Japan Backends        │   │
│  │  JSZ-O-2  │   3306   │    TCP/TLS     │  Core Zone       │ Core Zone MySQL       │   │
│  │  JSZ-O-3  │   443    │   TCP/HTTPS    │  Core Zone       │ Core Zone ES          │   │
│  │  JSZ-O-4  │    53    │    UDP/TCP     │  DNS Servers     │ DNS Resolution        │   │
│  │  JSZ-O-5  │   123    │      UDP       │  NTP Servers     │ Time Sync             │   │
│  │  JSZ-O-6  │   ALL    │      ALL       │  Internet        │ ❌ BLOCKED            │   │
│  │  JSZ-O-7  │   ALL    │      ALL       │  US/EU/ASIA      │ ❌ BLOCKED            │   │
│  └───────────┴──────────┴────────────────┴──────────────────┴───────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 9.3 Core Zone Firewall Rules

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          CORE ZONE FIREWALL RULES                                        │
│                                                                                          │
│  INBOUND:                                                                                │
│  ┌───────────┬──────────┬────────────────┬──────────────────┬───────────────────────┐   │
│  │   Rule    │   Port   │    Protocol    │      Source      │       Purpose         │   │
│  ├───────────┼──────────┼────────────────┼──────────────────┼───────────────────────┤   │
│  │  CORE-I-1 │   443    │   TCP/HTTPS    │  Admin Network   │ Console Access        │   │
│  │  CORE-I-2 │   443    │   TCP/HTTPS    │  Developer Net   │ Portal Access         │   │
│  │  CORE-I-3 │   3306   │    TCP/TLS     │  US Inner DMZ    │ MySQL from US GW      │   │
│  │  CORE-I-4 │   3306   │    TCP/TLS     │  EU Inner DMZ    │ MySQL from EU GW      │   │
│  │  CORE-I-5 │   3306   │    TCP/TLS     │  ASIA Inner DMZ  │ MySQL from ASIA GW    │   │
│  │  CORE-I-6 │   443    │   TCP/HTTPS    │  US Inner DMZ    │ ES from US GW         │   │
│  │  CORE-I-7 │   443    │   TCP/HTTPS    │  EU Inner DMZ    │ ES from EU GW         │   │
│  │  CORE-I-8 │   443    │   TCP/HTTPS    │  ASIA Inner DMZ  │ ES from ASIA GW       │   │
│  │  CORE-I-9 │   443    │   TCP/HTTPS    │  JSZ Config GW   │ Config Export to JSZ  │   │
│  │  CORE-I-10│    22    │    TCP/SSH     │  Admin IPs       │ Management Access     │   │
│  └───────────┴──────────┴────────────────┴──────────────────┴───────────────────────┘   │
│                                                                                          │
│  OUTBOUND:                                                                               │
│  ┌───────────┬──────────┬────────────────┬──────────────────┬───────────────────────┐   │
│  │   Rule    │   Port   │    Protocol    │   Destination    │       Purpose         │   │
│  ├───────────┼──────────┼────────────────┼──────────────────┼───────────────────────┤   │
│  │  CORE-O-1 │   3306   │   TCP/TLS      │  MySQL Cluster    │ On-Premise DB Access  │   │
│  │  CORE-O-2 │   443    │   TCP/HTTPS    │  Elastic Cloud   │ Managed ES Access     │   │
│  │  CORE-O-3 │   443    │   TCP/HTTPS    │  IdP (SSO)       │ Authentication        │   │
│  │  CORE-O-4 │    53    │    UDP/TCP     │  DNS Servers     │ DNS Resolution        │   │
│  │  CORE-O-5 │   123    │      UDP       │  NTP Servers     │ Time Sync             │   │
│  └───────────┴──────────┴────────────────┴──────────────────┴───────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 9.4 Complete Firewall Rules Summary Table

| Zone | Direction | Port | Protocol | Source/Dest | Purpose |
|------|-----------|------|----------|-------------|---------|
| **Outer DMZ (Global)** | IN | 443 | HTTPS | Internet | API Traffic |
| | OUT | 8082 | HTTP | Inner DMZ | To Gateway |
| **Inner DMZ (Global)** | IN | 8082 | HTTP | Outer DMZ | From LB |
| | OUT | 3306 | TLS | Core Zone | MySQL |
| | OUT | 443 | HTTPS | Core Zone | Elasticsearch |
| | OUT | 80/443 | HTTP/S | App Zone | Backend |
| **JSZ Outer DMZ** | IN | 443 | HTTPS | Japan IPs | API Traffic |
| **JSZ Inner DMZ** | IN | 8082 | HTTP | JSZ Outer | From LB |
| | OUT | 3306 | TLS | Core Zone | Core MySQL |
| | OUT | 443 | HTTPS | Core Zone | Core ES |
| | OUT | 80/443 | HTTP/S | JSZ App Zone | JP Backends |
| | OUT | * | * | Internet | **BLOCKED** |
| | OUT | * | * | US/EU/ASIA | **BLOCKED** |
| **Core Zone** | IN | 443 | HTTPS | Admin/Dev | Console/Portal |
| | IN | 3306 | TLS | All GW | MySQL |
| | IN | 443 | HTTPS | All GW | Elasticsearch |
| | OUT | 3306 | TLS | MySQL Cluster | On-Premise DB |
| | OUT | 443 | HTTPS | Elastic Cloud | Managed ES |

---

## 11. High Availability & Disaster Recovery

### 10.1 Regional HA Configuration

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                         REGIONAL HIGH AVAILABILITY                                       │
│                                                                                          │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                           US REGION HA                                           │   │
│   │                                                                                  │   │
│   │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐              │   │
│   │   │                 │   │                 │   │                 │              │   │
│   │   │   AZ: us-east-  │   │   AZ: us-east-  │   │   AZ: us-east-  │              │   │
│   │   │       1a        │   │       1b        │   │       1c        │              │   │
│   │   │                 │   │                 │   │                 │              │   │
│   │   │  ┌───────────┐  │   │  ┌───────────┐  │   │  ┌───────────┐  │              │   │
│   │   │  │ Gateway 1 │  │   │  │ Gateway 2 │  │   │  │ Gateway 3 │  │              │   │
│   │   │  │ (Active)  │  │   │  │ (Active)  │  │   │  │ (Active)  │  │              │   │
│   │   │  └───────────┘  │   │  └───────────┘  │   │  └───────────┘  │              │   │
│   │   │                 │   │                 │   │                 │              │   │
│   │   └─────────────────┘   └─────────────────┘   └─────────────────┘              │   │
│   │                                                                                  │   │
│   │   Load Balancing: Round-robin across all active gateways                        │   │
│   │   Failover: Automatic health-check based removal                                │   │
│   │   Recovery: Auto-scaling group replaces failed instances                        │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                           EU REGION HA                                           │   │
│   │                                                                                  │   │
│   │   Same pattern as US: 3 AZs, Active-Active gateways                             │   │
│   │   Additional: GDPR-compliant data handling                                      │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                          ASIA REGION HA                                          │   │
│   │                                                                                  │   │
│   │   Same pattern as US: 3 AZs, Active-Active gateways                             │   │
│   │   Additional: Multi-country support (Singapore, Tokyo, Sydney)                  │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                            JSZ HA                                                │   │
│   │                                                                                  │   │
│   │   ┌─────────────────┐   ┌─────────────────┐                                    │   │
│   │   │                 │   │                 │                                    │   │
│   │   │   Primary DC    │   │   Secondary DC  │                                    │   │
│   │   │   (Tokyo)       │   │   (Osaka)       │                                    │   │
│   │   │                 │   │                 │                                    │   │
│   │   │  ┌───────────┐  │   │  ┌───────────┐  │                                    │   │
│   │   │  │ Gateway 1 │  │   │  │ Gateway 2 │  │                                    │   │
│   │   │  │ (Active)  │  │   │  │ (Standby) │  │                                    │   │
│   │   │  └───────────┘  │   │  └───────────┘  │                                    │   │
│   │   │                 │   │                 │                                    │   │
│   │   │  ┌───────────┐  │   │  ┌───────────┐  │                                    │   │
│   │   │  │ MySQL     │  │   │  │ MySQL     │  │                                    │   │
│   │   │  │ (Primary) │◄─┼───┼─▶│ (Replica) │  │                                    │   │
│   │   │  └───────────┘  │   │  └───────────┘  │                                    │   │
│   │   │                 │   │                 │                                    │   │
│   │   └─────────────────┘   └─────────────────┘                                    │   │
│   │                                                                                  │   │
│   │   JSZ operates Active-Passive for enhanced security                             │   │
│   │   Manual failover with approval process                                         │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 RTO/RPO Targets

| Component | Region | RTO | RPO | Strategy |
|-----------|--------|-----|-----|----------|
| API Gateway | US/EU/ASIA | 30 sec | 0 | Active-Active, auto-failover |
| API Gateway | JSZ | 15 min | 0 | Active-Passive, manual |
| MySQL | Core Zone | 60 sec | < 1 sec | On-Premise cluster failover |
| Elasticsearch | Core Zone | 2 min | < 1 min | Cluster auto-recovery |
| Management API | Core Zone | 2 min | 0 | K8s auto-restart |
| Console/Portal | Core Zone | 2 min | N/A | K8s auto-restart |

### 10.3 Disaster Recovery Procedures

| Scenario | Impact | Recovery Procedure | Time |
|----------|--------|-------------------|------|
| Single Gateway failure | Minimal | Auto-removed from LB, ASG replaces | 30 sec |
| AZ failure | Partial | Traffic shifts to other AZs | 1 min |
| Region failure | Major | GeoDNS routes to other regions | 5 min |
| Core Zone failure | Critical | Restore from backup in DR region | 4 hours |
| JSZ failure | JSZ only | Manual failover to secondary DC | 15 min |
| Global outage | Complete | Execute full DR plan | 8 hours |

---

## 12. Operational Procedures

### 11.1 Deployment Workflow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                           API DEPLOYMENT WORKFLOW                                        │
│                                                                                          │
│                                                                                          │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                                   │  │
│   │   STEP 1: Development & Testing                                                  │  │
│   │                                                                                   │  │
│   │   Developer ──► API Design ──► Local Testing ──► PR Review ──► Merge            │  │
│   │                                                                                   │  │
│   └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                          │                                              │
│                                          ▼                                              │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                                   │  │
│   │   STEP 2: Staging Deployment (Core Zone)                                         │  │
│   │                                                                                   │  │
│   │   CI/CD ──► Deploy to Staging ──► Integration Tests ──► Approval                │  │
│   │                                                                                   │  │
│   └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                          │                                              │
│                                          ▼                                              │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                                   │  │
│   │   STEP 3: Production Deployment (Global Regions)                                 │  │
│   │                                                                                   │  │
│   │   ┌─────────────────────────────────────────────────────────────────────────┐   │  │
│   │   │                                                                          │   │  │
│   │   │   3a. Deploy to US ──► Canary (5%) ──► Monitor ──► Full Rollout         │   │  │
│   │   │                                                                          │   │  │
│   │   │   3b. Deploy to EU ──► Canary (5%) ──► Monitor ──► Full Rollout         │   │  │
│   │   │                                                                          │   │  │
│   │   │   3c. Deploy to ASIA ──► Canary (5%) ──► Monitor ──► Full Rollout       │   │  │
│   │   │                                                                          │   │  │
│   │   └─────────────────────────────────────────────────────────────────────────┘   │  │
│   │                                                                                   │  │
│   └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                          │                                              │
│                                          ▼                                              │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                                   │  │
│   │   STEP 4: JSZ Deployment (Special Process)                                       │  │
│   │                                                                                   │  │
│   │   ┌─────────────────────────────────────────────────────────────────────────┐   │  │
│   │   │                                                                          │   │  │
│   │   │   4a. Export Config Package from Core Zone                              │   │  │
│   │   │                     │                                                    │   │  │
│   │   │                     ▼                                                    │   │  │
│   │   │   4b. Security Review & Approval (JSZ Security Team)                    │   │  │
│   │   │                     │                                                    │   │  │
│   │   │                     ▼                                                    │   │  │
│   │   │   4c. Manual Import via JSZ Config Gateway                              │   │  │
│   │   │                     │                                                    │   │  │
│   │   │                     ▼                                                    │   │  │
│   │   │   4d. JSZ Internal Testing                                              │   │  │
│   │   │                     │                                                    │   │  │
│   │   │                     ▼                                                    │   │  │
│   │   │   4e. Production Deployment in JSZ                                      │   │  │
│   │   │                                                                          │   │  │
│   │   └─────────────────────────────────────────────────────────────────────────┘   │  │
│   │                                                                                   │  │
│   │   JSZ Deployment SLA: 24-48 hours (due to approval process)                     │  │
│   │                                                                                   │  │
│   └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Monitoring Dashboard

| Metric | US | EU | ASIA | JSZ | Core |
|--------|----|----|------|-----|------|
| Gateway Health | ✅ | ✅ | ✅ | ✅ | N/A |
| Request Rate | 📊 | 📊 | 📊 | 📊 (Local) | N/A |
| Error Rate | 📊 | 📊 | 📊 | 📊 (Local) | N/A |
| Latency P99 | 📊 | 📊 | 📊 | 📊 (Local) | N/A |
| MySQL Status | N/A | N/A | N/A | ✅ (Local) | ✅ |
| ES Status | N/A | N/A | N/A | ✅ (Local) | ✅ |
| Mgmt API Health | N/A | N/A | N/A | N/A | ✅ |
| Config Sync | ✅ | ✅ | ✅ | ⚠️ Manual | ✅ |

---

## 13. Compliance & Governance

### 12.1 Compliance Matrix

| Requirement | US | EU | ASIA | JSZ |
|-------------|----|----|------|-----|
| **SOC 2 Type II** | ✅ | ✅ | ✅ | ✅ |
| **ISO 27001** | ✅ | ✅ | ✅ | ✅ |
| **GDPR** | N/A | ✅ | N/A | N/A |
| **CCPA** | ✅ | N/A | N/A | N/A |
| **FISC** | N/A | N/A | N/A | ✅ |
| **APPI** | N/A | N/A | N/A | ✅ |
| **PCI-DSS** | ✅ | ✅ | ✅ | ✅ |
| **HIPAA** | ✅ | N/A | N/A | N/A |

### 12.2 Data Residency

| Region | Data Location | Replication | Export Allowed |
|--------|---------------|-------------|----------------|
| US | US data centers | Within US | Yes (to Core) |
| EU | EU data centers | Within EU | Yes (GDPR compliant) |
| ASIA | APAC data centers | Within APAC | Yes (to Core) |
| JSZ | Japan only | Within Japan | **NO** |
| Core | Multi-region | Global | Yes (except to JSZ) |

### 12.3 Audit Requirements

| Audit Type | Frequency | Scope | Retention |
|------------|-----------|-------|-----------|
| Access Logs | Real-time | All zones | 1 year |
| Config Changes | Real-time | All zones | 3 years |
| Security Events | Real-time | All zones | 3 years |
| Compliance Audit | Annual | All zones | 7 years |
| Penetration Test | Quarterly | All zones | 3 years |
| JSZ Special Audit | Monthly | JSZ only | 7 years |

---

## Appendix A: Quick Reference

### Regional Endpoints

| Region | API Gateway | Console | Portal |
|--------|-------------|---------|--------|
| US | api-us.company.com | console.company.com | portal.company.com |
| EU | api-eu.company.com | console.company.com | portal.company.com |
| ASIA | api-asia.company.com | console.company.com | portal.company.com |
| JSZ | api-jsz.company.co.jp | console.company.com | portal.company.com |

### Emergency Contacts

| Role | Region | Contact |
|------|--------|---------|
| Platform Lead | Global | platform-lead@company.com |
| Security Lead | Global | security@company.com |
| JSZ Admin | JSZ | jsz-admin@company.co.jp |
| NOC | 24/7 | noc@company.com |

---

*Document Version: 1.0 | Last Updated: February 2, 2026*

