# Multi-Region Firewall Rules - Complete Reference

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Date** | February 2, 2026 |
| **Classification** | Internal - Security |

---

## Table of Contents

1. [Overview](#1-overview)
2. [Network Zones Summary](#2-network-zones-summary)
3. [US Region Firewall Rules](#3-us-region-firewall-rules)
4. [EU Region Firewall Rules](#4-eu-region-firewall-rules)
5. [ASIA Region Firewall Rules](#5-asia-region-firewall-rules)
6. [Japan Secure Zone (JSZ) Firewall Rules](#6-japan-secure-zone-jsz-firewall-rules)
7. [Core Zone Firewall Rules](#7-core-zone-firewall-rules)
8. [Internal API Gateway Firewall Rules](#8-internal-api-gateway-firewall-rules)
9. [Inter-Region Communication Rules](#9-inter-region-communication-rules)
10. [Implementation Examples](#10-implementation-examples)
11. [Verification & Testing](#11-verification--testing)

---

## 1. Overview

This document provides comprehensive firewall rules for the multi-region Gravitee APIM deployment spanning:

- **US Region** - Global API Gateway (shared)
- **EU Region** - Global API Gateway (shared)
- **ASIA Region** - Global API Gateway (shared)
- **Japan Secure Zone (JSZ)** - Isolated data plane
- **Core Zone** - Centralized control plane

### Network Architecture Summary

![Firewall Zones Overview](diagrams/02-firewall-zones.svg)

<details>
<summary>View ASCII Diagram (fallback)</summary>

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                              FIREWALL ZONES OVERVIEW                                     │
│                                                                                          │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐     │
│   │  US REGION  │    │  EU REGION  │    │ ASIA REGION │    │        JSZ          │     │
│   │             │    │             │    │             │    │   (Japan Only)      │     │
│   │ ┌─────────┐ │    │ ┌─────────┐ │    │ ┌─────────┐ │    │ ┌─────────────────┐ │     │
│   │ │Outer DMZ│ │    │ │Outer DMZ│ │    │ │Outer DMZ│ │    │ │  Outer DMZ      │ │     │
│   │ └────┬────┘ │    │ └────┬────┘ │    │ └────┬────┘ │    │ │  (Japan IPs)    │ │     │
│   │      │      │    │      │      │    │      │      │    │ └────────┬────────┘ │     │
│   │ ┌────▼────┐ │    │ ┌────▼────┐ │    │ ┌────▼────┐ │    │          │          │     │
│   │ │Inner DMZ│ │    │ │Inner DMZ│ │    │ │Inner DMZ│ │    │ ┌────────▼────────┐ │     │
│   │ │(Gateway)│ │    │ │(Gateway)│ │    │ │(Gateway)│ │    │ │   Inner DMZ     │ │     │
│   │ └────┬────┘ │    │ └────┬────┘ │    │ └────┬────┘ │    │ │  (JSZ Gateway)  │ │     │
│   │      │      │    │      │      │    │      │      │    │ └────────┬────────┘ │     │
│   │ ┌────▼────┐ │    │ ┌────▼────┐ │    │ ┌────▼────┐ │    │          │          │     │
│   │ │App Zone │ │    │ │App Zone │ │    │ │App Zone │ │    │ ┌────────▼────────┐ │     │
│   │ │(Backend)│ │    │ │(Backend)│ │    │ │(Backend)│ │    │ │  App Zone       │ │     │
│   │ └────┬────┘ │    │ └────┬────┘ │    │ └────┬────┘ │    │ │  (JP Backends)  │ │     │
│   │      │      │    │      │      │    │      │      │    │ └────────┬────────┘ │     │
│   └──────┼──────┘    └──────┼──────┘    └──────┼──────┘    └──────────┼──────────┘     │
│          │                  │                  │                      │                │
│          └──────────────────┼──────────────────┴──────────────────────┘                │
│                             │                                                          │
│                             ▼                                                          │
│          ┌───────────────────────────────────────────────────┐                        │
│          │                    CORE ZONE                       │                        │
│          │              (Control Plane + Data)                │                        │
│          │    ┌──────────────┐        ┌──────────────┐       │                        │
│          │    │   MySQL      │        │Elasticsearch │       │                        │
│          │    │   (Shared)   │        │   (Shared)   │       │                        │
│          │    └──────────────┘        └──────────────┘       │                        │
│          └───────────────────────────────────────────────────┘                        │
│                                                                                          │
│   Note: ALL regions (US, EU, ASIA, JSZ) connect to Core Zone MySQL & Elasticsearch   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```
</details>

---

## 2. Network Zones Summary

### Zone Definitions

| Zone | CIDR Example | Purpose | Security Level |
|------|--------------|---------|----------------|
| US Outer DMZ | 10.1.0.0/24 | Edge security, WAF | Public-facing |
| US Inner DMZ | 10.1.1.0/24 | API Gateway | Semi-trusted |
| US App Zone | 10.1.2.0/24 | Backend services | Trusted |
| EU Outer DMZ | 10.2.0.0/24 | Edge security, WAF | Public-facing |
| EU Inner DMZ | 10.2.1.0/24 | API Gateway | Semi-trusted |
| EU App Zone | 10.2.2.0/24 | Backend services | Trusted |
| ASIA Outer DMZ | 10.3.0.0/24 | Edge security, WAF | Public-facing |
| ASIA Inner DMZ | 10.3.1.0/24 | API Gateway | Semi-trusted |
| ASIA App Zone | 10.3.2.0/24 | Backend services | Trusted |
| JSZ Outer DMZ | 10.4.0.0/24 | Edge (Japan only) | Restricted |
| JSZ Inner DMZ | 10.4.1.0/24 | JSZ Gateway | Highly Restricted |
| JSZ App Zone | 10.4.2.0/24 | Internal Gateway + Japan backends | Trusted |
| Core Zone | 10.0.0.0/16 | Control plane | Highly Trusted |

---

## 3. US Region Firewall Rules

### 3.1 US Outer DMZ

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          US OUTER DMZ FIREWALL RULES                                     │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ US-O-1 │ ALLOW  │   443    │   TCP/HTTPS     │   0.0.0.0/0     │ API Traffic       │ │
│  │ US-O-2 │ ALLOW  │    80    │   TCP/HTTP      │   0.0.0.0/0     │ Redirect→HTTPS    │ │
│  │ US-O-3 │ DENY   │   ALL    │      ALL        │ Sanctioned IPs* │ Blocked countries │ │
│  │ US-O-4 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  * Sanctioned IPs: Countries under trade restrictions                                   │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ US-O-5 │ ALLOW  │   8082   │   TCP/HTTP      │ 10.1.1.0/24     │ To Inner DMZ GW   │ │
│  │ US-O-6 │ ALLOW  │    53    │   UDP/TCP       │ DNS Servers     │ DNS Resolution    │ │
│  │ US-O-7 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 US Inner DMZ (Gateway Zone)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          US INNER DMZ FIREWALL RULES                                     │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ US-I-1 │ ALLOW  │   8082   │   TCP/HTTP      │ 10.1.0.0/24     │ From Outer DMZ    │ │
│  │ US-I-2 │ ALLOW  │    22    │   TCP/SSH       │ 10.0.100.0/24   │ Admin access      │ │
│  │ US-I-3 │ ALLOW  │   9090   │   TCP/HTTP      │ 10.0.50.0/24    │ Prometheus scrape │ │
│  │ US-I-4 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ US-I-5 │ ALLOW  │  80/443  │  TCP/HTTP(S)    │ 10.1.2.0/24     │ To App Zone       │ │
│  │ US-I-6 │ ALLOW  │   3306   │   TCP/TLS       │ 10.0.10.0/24    │ MySQL (Core)     │ │
│  │ US-I-7 │ ALLOW  │   443    │   TCP/HTTPS     │ 10.0.20.0/24    │ Elasticsearch     │ │
│  │ US-I-8 │ ALLOW  │    53    │   UDP/TCP       │ DNS Servers     │ DNS Resolution    │ │
│  │ US-I-9 │ ALLOW  │   123    │      UDP        │ NTP Servers     │ Time sync         │ │
│  │US-I-10 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 US Application Zone

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          US APPLICATION ZONE FIREWALL RULES                              │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ US-A-1 │ ALLOW  │  80/443  │  TCP/HTTP(S)    │ 10.1.1.0/24     │ From Gateway      │ │
│  │ US-A-2 │ ALLOW  │   8080   │   TCP/HTTP      │ 10.1.1.0/24     │ From Gateway      │ │
│  │ US-A-3 │ ALLOW  │    22    │   TCP/SSH       │ 10.0.100.0/24   │ Admin access      │ │
│  │ US-A-4 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ US-A-5 │ ALLOW  │   443    │   TCP/HTTPS     │ External APIs   │ Third-party APIs  │ │
│  │ US-A-6 │ ALLOW  │  5432    │   TCP/TLS       │ Database Zone   │ PostgreSQL        │ │
│  │ US-A-7 │ ALLOW  │  6379    │   TCP/TLS       │ Cache Zone      │ Redis             │ │
│  │ US-A-8 │ ALLOW  │    53    │   UDP/TCP       │ DNS Servers     │ DNS Resolution    │ │
│  │ US-A-9 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. EU Region Firewall Rules

### 4.1 EU Outer DMZ

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          EU OUTER DMZ FIREWALL RULES                                     │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ EU-O-1 │ ALLOW  │   443    │   TCP/HTTPS     │   0.0.0.0/0     │ API Traffic       │ │
│  │ EU-O-2 │ ALLOW  │    80    │   TCP/HTTP      │   0.0.0.0/0     │ Redirect→HTTPS    │ │
│  │ EU-O-3 │ DENY   │   ALL    │      ALL        │ Non-GDPR IPs*   │ GDPR compliance   │ │
│  │ EU-O-4 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  * Non-GDPR IPs: Countries without adequate data protection (configurable)              │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ EU-O-5 │ ALLOW  │   8082   │   TCP/HTTP      │ 10.2.1.0/24     │ To Inner DMZ GW   │ │
│  │ EU-O-6 │ ALLOW  │    53    │   UDP/TCP       │ EU DNS Servers  │ DNS (EU only)     │ │
│  │ EU-O-7 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  GDPR COMPLIANCE NOTES:                                                                  │
│  • All logs must be stored within EU                                                    │
│  • PII must not leave EU boundaries                                                     │
│  • Data transfer to Core Zone must use GDPR-compliant channels                         │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 EU Inner DMZ (Gateway Zone)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          EU INNER DMZ FIREWALL RULES                                     │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ EU-I-1 │ ALLOW  │   8082   │   TCP/HTTP      │ 10.2.0.0/24     │ From Outer DMZ    │ │
│  │ EU-I-2 │ ALLOW  │    22    │   TCP/SSH       │ 10.0.100.0/24   │ Admin access      │ │
│  │ EU-I-3 │ ALLOW  │   9090   │   TCP/HTTP      │ 10.0.50.0/24    │ Prometheus scrape │ │
│  │ EU-I-4 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ EU-I-5 │ ALLOW  │  80/443  │  TCP/HTTP(S)    │ 10.2.2.0/24     │ To EU App Zone    │ │
│  │ EU-I-6 │ ALLOW  │   3306   │   TCP/TLS       │ 10.0.10.0/24    │ MySQL (Core)*    │ │
│  │ EU-I-7 │ ALLOW  │   443    │   TCP/HTTPS     │ 10.0.20.0/24    │ Elasticsearch*    │ │
│  │ EU-I-8 │ ALLOW  │    53    │   UDP/TCP       │ EU DNS Servers  │ DNS (EU only)     │ │
│  │ EU-I-9 │ ALLOW  │   123    │      UDP        │ EU NTP Servers  │ Time sync (EU)    │ │
│  │EU-I-10 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  * GDPR Note: Only non-PII data (config, aggregated analytics) sent to Core Zone        │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. ASIA Region Firewall Rules

### 5.1 ASIA Outer DMZ

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          ASIA OUTER DMZ FIREWALL RULES                                   │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ AS-O-1 │ ALLOW  │   443    │   TCP/HTTPS     │   0.0.0.0/0     │ API Traffic       │ │
│  │ AS-O-2 │ ALLOW  │    80    │   TCP/HTTP      │   0.0.0.0/0     │ Redirect→HTTPS    │ │
│  │ AS-O-3 │ DENY   │   ALL    │      ALL        │ Blocked IPs*    │ Regional blocks   │ │
│  │ AS-O-4 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  * Blocked IPs: Configurable based on regional requirements                             │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ AS-O-5 │ ALLOW  │   8082   │   TCP/HTTP      │ 10.3.1.0/24     │ To Inner DMZ GW   │ │
│  │ AS-O-6 │ ALLOW  │    53    │   UDP/TCP       │ DNS Servers     │ DNS Resolution    │ │
│  │ AS-O-7 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 ASIA Inner DMZ (Gateway Zone)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          ASIA INNER DMZ FIREWALL RULES                                   │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ AS-I-1 │ ALLOW  │   8082   │   TCP/HTTP      │ 10.3.0.0/24     │ From Outer DMZ    │ │
│  │ AS-I-2 │ ALLOW  │    22    │   TCP/SSH       │ 10.0.100.0/24   │ Admin access      │ │
│  │ AS-I-3 │ ALLOW  │   9090   │   TCP/HTTP      │ 10.0.50.0/24    │ Prometheus scrape │ │
│  │ AS-I-4 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ AS-I-5 │ ALLOW  │  80/443  │  TCP/HTTP(S)    │ 10.3.2.0/24     │ To ASIA App Zone  │ │
│  │ AS-I-6 │ ALLOW  │   3306   │   TCP/TLS       │ 10.0.10.0/24    │ MySQL (Core)     │ │
│  │ AS-I-7 │ ALLOW  │   443    │   TCP/HTTPS     │ 10.0.20.0/24    │ Elasticsearch     │ │
│  │ AS-I-8 │ ALLOW  │    53    │   UDP/TCP       │ DNS Servers     │ DNS Resolution    │ │
│  │ AS-I-9 │ ALLOW  │   123    │      UDP        │ NTP Servers     │ Time sync         │ │
│  │AS-I-10 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Japan Secure Zone (JSZ) Firewall Rules

### 6.1 JSZ Outer DMZ (Highly Restricted)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          JSZ OUTER DMZ FIREWALL RULES                                    │
│                             (HIGHLY RESTRICTED)                                          │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │JSZ-O-1 │ ALLOW  │   443    │   TCP/HTTPS     │ Japan IPs ONLY  │ API (Japan only)  │ │
│  │JSZ-O-2 │ DENY   │   ALL    │      ALL        │ Non-Japan IPs   │ Strict geo-block  │ │
│  │JSZ-O-3 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  JAPAN IP RANGES (Example):                                                             │
│  • 1.0.16.0/20                                                                          │
│  • 1.0.64.0/18                                                                          │
│  • 1.1.64.0/18                                                                          │
│  • (Full list maintained by security team)                                              │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │JSZ-O-4 │ ALLOW  │   8082   │   TCP/HTTP      │ 10.4.1.0/24     │ To JSZ Inner DMZ  │ │
│  │JSZ-O-5 │ ALLOW  │    53    │   UDP/TCP       │ JSZ DNS ONLY    │ Local DNS only    │ │
│  │JSZ-O-6 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  ⚠️  NO INTERNET EGRESS ALLOWED FROM JSZ OUTER DMZ                                      │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 JSZ Inner DMZ (Isolated Gateway)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          JSZ INNER DMZ FIREWALL RULES                                    │
│                        (Uses Core Zone MySQL & Elasticsearch)                          │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │JSZ-I-1 │ ALLOW  │   8082   │   TCP/HTTP      │ 10.4.0.0/24     │ From JSZ Outer    │ │
│  │JSZ-I-2 │ ALLOW  │    22    │   TCP/SSH       │ 10.4.100.0/28   │ JSZ Admin ONLY    │ │
│  │JSZ-I-3 │ ALLOW  │   9090   │   TCP/HTTP      │ 10.4.50.0/28    │ Prometheus        │ │
│  │JSZ-I-4 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │JSZ-I-5 │ ALLOW  │  80/443  │  TCP/HTTP(S)    │ 10.4.2.0/24     │ JSZ App Zone      │ │
│  │JSZ-I-6 │ ALLOW  │   3306   │   TCP/TLS       │ 10.0.10.0/24    │ Core Zone MySQL  │ │
│  │JSZ-I-7 │ ALLOW  │   443    │   TCP/HTTPS     │ 10.0.20.0/24    │ Core Zone ES      │ │
│  │JSZ-I-8 │ ALLOW  │    53    │   UDP/TCP       │ DNS Servers     │ DNS Resolution    │ │
│  │JSZ-I-9 │ ALLOW  │   123    │      UDP        │ NTP Servers     │ Time Sync         │ │
│  │JSZ-I-10│ DENY   │   ALL    │      ALL        │ INTERNET        │ ❌ NO INTERNET    │ │
│  │JSZ-I-11│ DENY   │   ALL    │      ALL        │ 10.1.0.0/16     │ ❌ NO US Region   │ │
│  │JSZ-I-12│ DENY   │   ALL    │      ALL        │ 10.2.0.0/16     │ ❌ NO EU Region   │ │
│  │JSZ-I-13│ DENY   │   ALL    │      ALL        │ 10.3.0.0/16     │ ❌ NO ASIA Region │ │
│  │JSZ-I-14│ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  ✅  JSZ INNER DMZ CONNECTS TO CORE ZONE FOR:                                           │
│      • MySQL (Config sync, Rate limiting)                                             │
│      • Elasticsearch (Analytics reporting)                                              │
│                                                                                          │
│  ❌  JSZ INNER DMZ BLOCKED FROM:                                                        │
│      • Internet (direct)                                                                │
│      • Other regional gateways (US, EU, ASIA)                                           │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 JSZ Security Controls

![JSZ Security Controls](diagrams/11-jsz-security-controls.svg)

<details>
<summary>View ASCII Diagram (fallback)</summary>

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          JSZ SECURITY CONTROLS                                           │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐│
│  │                                                                                      ││
│  │                           JSZ ARCHITECTURE (USES CORE ZONE DB)                       ││
│  │                                                                                      ││
│  │                                                                                      ││
│  │     ┌─────────────────────────────────────────────────────────────────────────┐     ││
│  │     │                         JSZ INNER DMZ                                    │     ││
│  │     │                                                                          │     ││
│  │     │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │     ││
│  │     │   │  Gateway 1  │   │  Gateway 2  │   │  Gateway 3  │                   │     ││
│  │     │   │  (Japan)    │   │  (Japan)    │   │  (Japan)    │                   │     ││
│  │     │   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘                   │     ││
│  │     │          │                 │                 │                          │     ││
│  │     │          └─────────────────┼─────────────────┘                          │     ││
│  │     │                            │                                            │     ││
│  │     └────────────────────────────┼────────────────────────────────────────────┘     ││
│  │                                  │                                                  ││
│  │                                  │ VPN / Secure Channel                             ││
│  │                                  │                                                  ││
│  │                                  ▼                                                  ││
│  │     ┌─────────────────────────────────────────────────────────────────────────┐     ││
│  │     │                         CORE ZONE                                        │     ││
│  │     │                                                                          │     ││
│  │     │   ┌─────────────────────┐       ┌─────────────────────┐                 │     ││
│  │     │   │                     │       │                     │                 │     ││
│  │     │   │   MySQL Database    │       │   Elasticsearch     │                 │     ││
│  │     │   │   (Shared)          │       │   (Shared)          │                 │     ││
│  │     │   │                     │       │                     │                 │     ││
│  │     │   │   • API Configs     │       │   • JSZ Analytics   │                 │     ││
│  │     │   │   • Rate Limits     │       │   • Request Logs    │                 │     ││
│  │     │   │   • Subscriptions   │       │   • Metrics         │                 │     ││
│  │     │   │                     │       │                     │                 │     ││
│  │     │   └─────────────────────┘       └─────────────────────┘                 │     ││
│  │     │                                                                          │     ││
│  │     └─────────────────────────────────────────────────────────────────────────┘     ││
│  │                                                                                      ││
│  └─────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                          │
│  JSZ SECURITY FEATURES:                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐│
│  │                                                                                      ││
│  │   ✅ Japan-only API traffic (geo-locked at edge)                                    ││
│  │   ✅ Uses Core Zone MySQL (shared config)                                         ││
│  │   ✅ Uses Core Zone Elasticsearch (shared analytics)                                ││
│  │   ✅ Automatic config sync (same as other regions)                                  ││
│  │   ✅ Enhanced WAF rules for Japanese compliance                                     ││
│  │   ✅ Strict IP allowlist for Japan IP ranges                                        ││
│  │                                                                                      ││
│  │   ❌ No direct internet egress from gateway                                         ││
│  │   ❌ No communication with other regional gateways                                  ││
│  │   ❌ Japan backends only (no external API calls)                                    ││
│  │                                                                                      ││
│  └─────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```
</details>

### 6.4 JSZ App Zone (Internal Gateway & Backend Services)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          JSZ APP ZONE FIREWALL RULES                                     │
│                    (Internal Gateway & Backend Services)                                 │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │JSZ-A-1 │ ALLOW  │   8083   │   TCP/HTTP      │ 10.4.1.0/24     │ From JSZ Gateway  │ │
│  │JSZ-A-2 │ ALLOW  │   8083   │   TCP/HTTP      │ 10.4.2.0/24     │ From Internal GW  │ │
│  │JSZ-A-3 │ ALLOW  │   8080   │   TCP/HTTP      │ 10.4.2.0/24     │ Internal Apps     │ │
│  │JSZ-A-4 │ ALLOW  │    22    │   TCP/SSH       │ 10.4.100.0/28   │ JSZ Admin ONLY    │ │
│  │JSZ-A-5 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │JSZ-A-6 │ ALLOW  │  80/443  │  TCP/HTTP(S)    │ 10.4.2.0/24     │ To Backend Svc    │ │
│  │JSZ-A-7 │ ALLOW  │   3306   │   TCP/TLS       │ 10.0.10.0/24    │ Core Zone MySQL  │ │
│  │JSZ-A-8 │ ALLOW  │   443    │   TCP/HTTPS     │ 10.0.20.0/24    │ Core Zone ES      │ │
│  │JSZ-A-9 │ ALLOW  │    53    │   UDP/TCP       │ DNS Servers     │ DNS Resolution    │ │
│  │JSZ-A-10│ DENY   │   ALL    │      ALL        │ INTERNET        │ ❌ NO INTERNET    │ │
│  │JSZ-A-11│ DENY   │   ALL    │      ALL        │ 10.1.0.0/16     │ ❌ NO US Region   │ │
│  │JSZ-A-12│ DENY   │   ALL    │      ALL        │ 10.2.0.0/16     │ ❌ NO EU Region   │ │
│  │JSZ-A-13│ DENY   │   ALL    │      ALL        │ 10.3.0.0/16     │ ❌ NO ASIA Region │ │
│  │JSZ-A-14│ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  JSZ APP ZONE COMPONENTS:                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                                      │ │
│  │   ┌──────────────────────────────────────────────────────────────────────────────┐   │ │
│  │   │                    INTERNAL API GATEWAY (JSZ)                                │   │ │
│  │   │                                                                              │   │ │
│  │   │   • Routes internal JSZ app traffic                                         │   │ │
│  │   │   • Service-to-service communication                                        │   │ │
│  │   │   • No internet exposure                                                    │   │ │
│  │   │   • Uses Core Zone MySQL/ES                                               │   │ │
│  │   │   • Port: 8083 (Internal)                                                   │   │ │
│  │   │                                                                              │   │ │
│  │   └──────────────────────────────────────────────────────────────────────────────┘   │ │
│  │                                                                                      │ │
│  │   ┌──────────────────────────────────────────────────────────────────────────────┐   │ │
│  │   │                    JSZ BACKEND SERVICES                                      │   │ │
│  │   │                                                                              │   │ │
│  │   │   • User Service                                                           │   │ │
│  │   │   • Payment Service                                                         │   │ │
│  │   │   • Reporting Service                                                       │   │ │
│  │   │   • Other Japan-specific services                                           │   │ │
│  │   │                                                                              │   │ │
│  │   └──────────────────────────────────────────────────────────────────────────────┘   │ │
│  │                                                                                      │ │
│  │   ┌──────────────────────────────────────────────────────────────────────────────┐   │ │
│  │   │                    JSZ INTERNAL APPLICATIONS                                  │   │ │
│  │   │                                                                              │   │ │
│  │   │   • Admin Dashboard                                                         │   │ │
│  │   │   • Monitoring Tools                                                        │   │ │
│  │   │   • CI/CD Pipelines                                                         │   │ │
│  │   │   • Security Scanners                                                       │   │ │
│  │   │                                                                              │   │ │
│  │   └──────────────────────────────────────────────────────────────────────────────┘   │ │
│  │                                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Core Zone Firewall Rules

### 7.1 Core Zone (Control Plane)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          CORE ZONE FIREWALL RULES                                        │
│                           (CENTRALIZED CONTROL PLANE)                                    │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │CORE-1  │ ALLOW  │   443    │   TCP/HTTPS     │ Admin Network   │ Console Access    │ │
│  │CORE-2  │ ALLOW  │   443    │   TCP/HTTPS     │ Developer Net   │ Portal Access     │ │
│  │CORE-3  │ ALLOW  │   3306   │   TCP/TLS       │ 10.1.1.0/24     │ US GW → MySQL     │ │
│  │CORE-4  │ ALLOW  │   3306   │   TCP/TLS       │ 10.2.1.0/24     │ EU GW → MySQL     │ │
│  │CORE-5  │ ALLOW  │   3306   │   TCP/TLS       │ 10.3.1.0/24     │ ASIA GW → MySQL   │ │
│  │CORE-6  │ ALLOW  │   443    │   TCP/HTTPS     │ 10.1.1.0/24     │ US GW → ES        │ │
│  │CORE-7  │ ALLOW  │   443    │   TCP/HTTPS     │ 10.2.1.0/24     │ EU GW → ES        │ │
│  │CORE-8  │ ALLOW  │   443    │   TCP/HTTPS     │ 10.3.1.0/24     │ ASIA GW → ES      │ │
│  │CORE-9  │ ALLOW  │   3306   │   TCP/TLS       │ 10.4.2.0/24     │ JSZ Internal GW → MySQL  │ │
│  │CORE-10 │ ALLOW  │   443    │   TCP/HTTPS     │ 10.4.2.0/24     │ JSZ Internal GW → ES │ │
│  │CORE-11 │ ALLOW  │    22    │   TCP/SSH       │ 10.0.100.0/24   │ Admin SSH         │ │
│  │CORE-12 │ ALLOW  │   6443   │   TCP/HTTPS     │ 10.0.100.0/24   │ K8s API           │ │
│  │CORE-13 │ DENY   │   ALL    │      ALL        │ JSZ (Direct)    │ ❌ No direct JSZ  │ │
│  │CORE-14 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │CORE-13 │ ALLOW  │   3306   │   TCP/TLS       │ MySQL Cluster   │ On-Premise DB     │ │
│  │CORE-14 │ ALLOW  │   443    │   TCP/HTTPS     │ Elastic Cloud   │ Managed ES        │ │
│  │CORE-15 │ ALLOW  │   443    │   TCP/HTTPS     │ IdP (SSO)       │ Authentication    │ │
│  │CORE-16 │ ALLOW  │   443    │   TCP/HTTPS     │ 10.4.3.0/28     │ JSZ Config Export │ │
│  │CORE-17 │ ALLOW  │    53    │   UDP/TCP       │ DNS Servers     │ DNS Resolution    │ │
│  │CORE-18 │ ALLOW  │   123    │      UDP        │ NTP Servers     │ Time sync         │ │
│  │CORE-19 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  NOTE: Core Zone can push configs to JSZ Config Gateway (CORE-16)                       │
│        but cannot receive any data back from JSZ                                        │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Internal API Gateway Firewall Rules

The Internal API Gateway is deployed within the Core Zone to handle internal service-to-service communication, admin APIs, and internal application traffic. It has **NO internet access** and **NO access to external DMZ zones**.

### 8.1 Internal Gateway Network Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│                      INTERNAL API GATEWAY NETWORK POSITION                               │
│                                                                                          │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │                           INTERNAL CONSUMERS                                     │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│   │   │  Internal   │  │   Admin     │  │   CI/CD     │  │  Backend    │           │   │
│   │   │    Apps     │  │   Tools     │  │  Pipelines  │  │  Services   │           │   │
│   │   │ 10.0.60.0/24│  │10.0.70.0/24 │  │10.0.80.0/24 │  │10.0.90.0/24 │           │   │
│   │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘           │   │
│   │          │                │                │                │                   │   │
│   │          └────────────────┴────────────────┴────────────────┘                   │   │
│   │                                    │                                            │   │
│   │                                    │ HTTPS (mTLS)                               │   │
│   │                                    ▼                                            │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │                    INTERNAL API GATEWAY ZONE (10.0.40.0/24)                      │   │
│   │                                                                                  │   │
│   │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐              │   │
│   │   │  Internal GW #1 │   │  Internal GW #2 │   │  Internal GW #3 │              │   │
│   │   │  10.0.40.10     │   │  10.0.40.11     │   │  10.0.40.12     │              │   │
│   │   │  Port: 8082     │   │  Port: 8082     │   │  Port: 8082     │              │   │
│   │   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘              │   │
│   │            │                     │                     │                        │   │
│   │            └─────────────────────┼─────────────────────┘                        │   │
│   │                                  │                                              │   │
│   └──────────────────────────────────┼──────────────────────────────────────────────┘   │
│                                      │                                                  │
│                                      │ HTTPS (mTLS)                                     │
│                                      ▼                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │                    INTERNAL BACKEND SERVICES (10.0.50.0/24)                      │   │
│   │                                                                                  │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│   │   │  User Svc   │  │ Inventory   │  │  Payment    │  │  Config     │           │   │
│   │   │ 10.0.50.10  │  │ 10.0.50.11  │  │ 10.0.50.12  │  │ 10.0.50.13  │           │   │
│   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘           │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │   BLOCKED DESTINATIONS:                                                          │   │
│   │   ❌ Internet (0.0.0.0/0)                                                        │   │
│   │   ❌ US Region (10.1.0.0/16)                                                     │   │
│   │   ❌ EU Region (10.2.0.0/16)                                                     │   │
│   │   ❌ ASIA Region (10.3.0.0/16)                                                   │   │
│   │   ❌ JSZ (10.4.0.0/16)                                                           │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Internal Gateway Firewall Rules

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      INTERNAL API GATEWAY FIREWALL RULES                                 │
│                                                                                          │
│  INBOUND RULES:                                                                          │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │     Source      │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ INT-1  │ ALLOW  │   8082   │   TCP/HTTPS     │ 10.0.60.0/24    │ Internal Apps     │ │
│  │ INT-2  │ ALLOW  │   8082   │   TCP/HTTPS     │ 10.0.70.0/24    │ Admin Tools       │ │
│  │ INT-3  │ ALLOW  │   8082   │   TCP/HTTPS     │ 10.0.80.0/24    │ CI/CD Pipelines   │ │
│  │ INT-4  │ ALLOW  │   8082   │   TCP/HTTPS     │ 10.0.90.0/24    │ Backend Services  │ │
│  │ INT-5  │ ALLOW  │   8082   │   TCP/HTTPS     │ 10.0.50.0/24    │ Service-to-Service│ │
│  │ INT-6  │ ALLOW  │   9090   │   TCP/HTTP      │ 10.0.55.0/24    │ Prometheus Scrape │ │
│  │ INT-7  │ ALLOW  │    22    │   TCP/SSH       │ 10.0.100.0/24   │ Admin SSH         │ │
│  │ INT-8  │ DENY   │   ALL    │      ALL        │ 10.1.0.0/16     │ ❌ No US Region   │ │
│  │ INT-9  │ DENY   │   ALL    │      ALL        │ 10.2.0.0/16     │ ❌ No EU Region   │ │
│  │ INT-10 │ DENY   │   ALL    │      ALL        │ 10.3.0.0/16     │ ❌ No ASIA Region │ │
│  │ INT-11 │ DENY   │   ALL    │      ALL        │ 10.4.0.0/16     │ ❌ No JSZ         │ │
│  │ INT-12 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ Default deny      │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  OUTBOUND RULES:                                                                         │
│  ┌────────┬────────┬──────────┬─────────────────┬─────────────────┬───────────────────┐ │
│  │ Rule # │ Action │   Port   │    Protocol     │   Destination   │    Description    │ │
│  ├────────┼────────┼──────────┼─────────────────┼─────────────────┼───────────────────┤ │
│  │ INT-13 │ ALLOW  │  80/443  │  TCP/HTTP(S)    │ 10.0.50.0/24    │ Backend Services  │ │
│  │ INT-14 │ ALLOW  │   8080   │   TCP/HTTP      │ 10.0.50.0/24    │ Backend Services  │ │
│  │ INT-15 │ ALLOW  │   3306   │   TCP/TLS       │ 10.0.10.0/24    │ MySQL             │ │
│  │ INT-16 │ ALLOW  │   443    │   TCP/HTTPS     │ 10.0.20.0/24    │ Elasticsearch     │ │
│  │ INT-17 │ ALLOW  │    53    │   UDP/TCP       │ 10.0.5.0/24     │ DNS Servers       │ │
│  │ INT-18 │ ALLOW  │   123    │      UDP        │ 10.0.6.0/24     │ NTP Servers       │ │
│  │ INT-19 │ DENY   │   ALL    │      ALL        │ 10.1.0.0/16     │ ❌ No US Region   │ │
│  │ INT-20 │ DENY   │   ALL    │      ALL        │ 10.2.0.0/16     │ ❌ No EU Region   │ │
│  │ INT-21 │ DENY   │   ALL    │      ALL        │ 10.3.0.0/16     │ ❌ No ASIA Region │ │
│  │ INT-22 │ DENY   │   ALL    │      ALL        │ 10.4.0.0/16     │ ❌ No JSZ         │ │
│  │ INT-23 │ DENY   │   ALL    │      ALL        │   0.0.0.0/0     │ ❌ No Internet    │ │
│  └────────┴────────┴──────────┴─────────────────┴─────────────────┴───────────────────┘ │
│                                                                                          │
│  ⚠️  INTERNAL GATEWAY SECURITY RESTRICTIONS:                                            │
│      • NO internet access (inbound or outbound)                                         │
│      • NO access to/from external regional gateways (US, EU, ASIA)                      │
│      • NO access to/from Japan Secure Zone (JSZ)                                        │
│      • ONLY internal Core Zone networks allowed                                         │
│      • mTLS required for all connections                                                │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Internal Gateway vs External Gateway Comparison

| Attribute | External Gateway | Internal Gateway |
|-----------|------------------|------------------|
| **Location** | Regional DMZ | Core Zone |
| **Internet Access** | ✅ Inbound (via LB) | ❌ None |
| **Regional Access** | ✅ Own region | ❌ None |
| **Core Zone Access** | ✅ MySQL, ES | ✅ MySQL, ES, Services |
| **Consumer Source** | Internet | Internal network only |
| **Authentication** | API Key, OAuth, JWT | mTLS, JWT, Service Account |
| **Use Cases** | Public APIs | Internal APIs, Admin, S2S |

### 8.4 Internal Gateway Allowed Traffic Summary

| Source | Destination | Port | Purpose |
|--------|-------------|------|---------|
| Internal Apps (10.0.60.0/24) | Internal GW | 8082 | App API access |
| Admin Tools (10.0.70.0/24) | Internal GW | 8082 | Admin operations |
| CI/CD (10.0.80.0/24) | Internal GW | 8082 | Deployment APIs |
| Backend Services (10.0.50.0/24) | Internal GW | 8082 | Service-to-service |
| Internal GW | Backend Services | 80/443/8080 | API routing |
| Internal GW | MySQL | 3306 | Config/Rate limit |
| Internal GW | Elasticsearch | 443 | Analytics |
| Prometheus | Internal GW | 9090 | Metrics scrape |

---

## 9. Inter-Region Communication Rules

### 8.1 VPN/PrivateLink Connections

![Inter-Region Communication](diagrams/10-inter-region-communication.svg)

<details>
<summary>View ASCII Diagram (fallback)</summary>

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          INTER-REGION COMMUNICATION MATRIX                               │
│                                                                                          │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                  │   │
│   │                         VPN / PRIVATELINK TOPOLOGY                               │   │
│   │                                                                                  │   │
│   │                                                                                  │   │
│   │        ┌──────────┐         ┌──────────┐         ┌──────────┐                   │   │
│   │        │    US    │◄───────►│   Core   │◄───────►│    EU    │                   │   │
│   │        │  Region  │   VPN   │   Zone   │   VPN   │  Region  │                   │   │
│   │        └──────────┘         └────┬─────┘         └──────────┘                   │   │
│   │                                  │                                               │   │
│   │                                  │ VPN                                           │   │
│   │                                  │                                               │   │
│   │                            ┌─────▼─────┐                                        │   │
│   │                            │   ASIA    │                                        │   │
│   │                            │  Region   │                                        │   │
│   │                            └───────────┘                                        │   │
│   │                                                                                  │   │
│   │                                                                                  │   │
│   │        ┌──────────┐         ONE-WAY          ┌──────────┐                       │   │
│   │        │   Core   │ ─────────────────────► │    JSZ    │                       │   │
│   │        │   Zone   │    (Config Only)        │           │                       │   │
│   │        └──────────┘                          └──────────┘                       │   │
│   │                                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│                                                                                          │
│  INTER-REGION VPN RULES:                                                                │
│  ┌────────────┬────────────┬──────────┬─────────────────┬───────────────────────────┐  │
│  │   From     │     To     │   Port   │    Protocol     │       Description         │  │
│  ├────────────┼────────────┼──────────┼─────────────────┼───────────────────────────┤  │
│  │ US Inner   │ Core Zone  │  27017   │   TCP/TLS       │ MongoDB sync              │  │
│  │ US Inner   │ Core Zone  │   443    │   TCP/HTTPS     │ ES analytics              │  │
│  │ EU Inner   │ Core Zone  │  27017   │   TCP/TLS       │ MongoDB sync              │  │
│  │ EU Inner   │ Core Zone  │   443    │   TCP/HTTPS     │ ES analytics (GDPR)       │  │
│  │ ASIA Inner │ Core Zone  │  27017   │   TCP/TLS       │ MongoDB sync              │  │
│  │ ASIA Inner │ Core Zone  │   443    │   TCP/HTTPS     │ ES analytics              │  │
│  │ Core Zone  │ JSZ Config │   443    │   TCP/HTTPS     │ Config export (one-way)   │  │
│  │ JSZ        │ Core Zone  │   ALL    │      ALL        │ ❌ BLOCKED                │  │
│  └────────────┴────────────┴──────────┴─────────────────┴───────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```
</details>
```

### 8.2 Cross-Region Traffic Matrix

| From | To | Allowed | Purpose |
|------|-----|---------|---------|
| US Inner DMZ | Core Zone | ✅ | Config sync, Analytics |
| EU Inner DMZ | Core Zone | ✅ | Config sync, Analytics (GDPR) |
| ASIA Inner DMZ | Core Zone | ✅ | Config sync, Analytics |
| Core Zone | US Inner DMZ | ✅ | Config push |
| Core Zone | EU Inner DMZ | ✅ | Config push |
| Core Zone | ASIA Inner DMZ | ✅ | Config push |
| Core Zone | JSZ Config GW | ✅ | Config export only |
| JSZ → Any | ❌ | **BLOCKED** | No outbound from JSZ |
| US ↔ EU | ❌ | **BLOCKED** | No direct region-to-region |
| US ↔ ASIA | ❌ | **BLOCKED** | No direct region-to-region |
| EU ↔ ASIA | ❌ | **BLOCKED** | No direct region-to-region |

---

## 10. Implementation Examples

### 9.1 On-Premise Firewall Rules (Example Configuration)

```hcl
# ============================================
# US Region Security Groups
# ============================================

# US Outer DMZ Firewall Rules
# Example: On-Premise Firewall Configuration
# US Outer DMZ Rules
  name        = "gravitee-us-outer-dmz"
  description = "US Outer DMZ - Edge Security"
  # Network segment: 10.1.0.0/24

  ingress {
    description = "HTTPS from Internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP redirect"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description     = "To Inner DMZ Gateway"
    from_port       = 8082
    to_port         = 8082
    protocol        = "tcp"
    # Allow from Inner DMZ
  }

  egress {
    description = "DNS"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name   = "gravitee-us-outer-dmz"
    Region = "us"
    Zone   = "outer-dmz"
  }
}

# US Inner DMZ Security Group
# US Inner DMZ Rules
  name        = "gravitee-us-inner-dmz"
  description = "US Inner DMZ - API Gateway"
  vpc_id      = var.us_vpc_id

  ingress {
    description     = "From Outer DMZ"
    from_port       = 8082
    to_port         = 8082
    protocol        = "tcp"
    # Allow from Outer DMZ
  }

  ingress {
    description = "Admin SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  egress {
    description = "To App Zone"
    from_port   = 80
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.us_app_zone_cidr]
  }

  egress {
    description = "MySQL to Core Zone"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [var.core_zone_cidr]
  }

  egress {
    description = "Elasticsearch to Core Zone"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.core_zone_cidr]
  }

  tags = {
    Name   = "gravitee-us-inner-dmz"
    Region = "us"
    Zone   = "inner-dmz"
  }
}

# ============================================
# JSZ Security Groups (Highly Restricted)
# ============================================

# JSZ Outer DMZ - Japan Only
# JSZ Outer DMZ Rules
  name        = "gravitee-jsz-outer-dmz"
  description = "JSZ Outer DMZ - Japan IPs Only"
  vpc_id      = var.jsz_vpc_id

  ingress {
    description = "HTTPS from Japan only"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.japan_ip_ranges  # Japan IP ranges only
  }

  egress {
    description     = "To JSZ Inner DMZ only"
    from_port       = 8082
    to_port         = 8082
    protocol        = "tcp"
    # Allow from JSZ Inner DMZ
  }

  # No other egress allowed

  tags = {
    Name   = "gravitee-jsz-outer-dmz"
    Region = "jsz"
    Zone   = "outer-dmz"
  }
}

# JSZ Inner DMZ - Completely Isolated
# JSZ Inner DMZ Rules
  name        = "gravitee-jsz-inner-dmz"
  description = "JSZ Inner DMZ - Isolated Gateway"
  vpc_id      = var.jsz_vpc_id

  ingress {
    description     = "From JSZ Outer DMZ"
    from_port       = 8082
    to_port         = 8082
    protocol        = "tcp"
    # Allow from Outer DMZ
  }

  ingress {
    description = "JSZ Admin SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.jsz_admin_cidr]  # JSZ admin only
  }

  egress {
    description = "To JSZ App Zone (Japan backends)"
    from_port   = 80
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.jsz_app_zone_cidr]
  }

  egress {
    description = "To Core Zone MySQL"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [var.core_zone_mysql_cidr]
  }

  egress {
    description = "To Core Zone Elasticsearch"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.core_zone_es_cidr]
  }

  # NO INTERNET EGRESS
  # NO OTHER REGION EGRESS (US/EU/ASIA)

  tags = {
    Name   = "gravitee-jsz-inner-dmz"
    Region = "jsz"
    Zone   = "inner-dmz"
  }
}

  # OUTBOUND: Only to JSZ Inner DMZ
  egress {
    description     = "To JSZ Inner DMZ"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    # Allow from JSZ Inner DMZ
  }

  # NO OTHER EGRESS - Especially no egress to Core Zone

  tags = {
    Name   = "gravitee-jsz-config-gateway"
    Region = "jsz"
    Zone   = "config-gateway"
  }
}
```

### 9.2 iptables Rules (Linux)

```bash
#!/bin/bash
# ============================================
# JSZ Gateway Server iptables Rules
# HIGHLY RESTRICTED - NO INTERNET ACCESS
# ============================================

# Flush existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# Default policies - DENY ALL
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# ============================================
# INBOUND RULES
# ============================================

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow from JSZ Outer DMZ (Gateway traffic)
iptables -A INPUT -p tcp --dport 8082 -s 10.4.0.0/24 -j ACCEPT

# Allow from JSZ Admin (SSH)
iptables -A INPUT -p tcp --dport 22 -s 10.4.100.0/28 -j ACCEPT

# Allow from JSZ Monitoring (Prometheus)
iptables -A INPUT -p tcp --dport 9090 -s 10.4.50.0/28 -j ACCEPT

# Log and drop everything else
iptables -A INPUT -j LOG --log-prefix "JSZ-INPUT-DROP: "
iptables -A INPUT -j DROP

# ============================================
# OUTBOUND RULES
# ============================================

# Allow loopback
iptables -A OUTPUT -o lo -j ACCEPT

# Allow established connections
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow to JSZ App Zone (Japan Backend services)
iptables -A OUTPUT -p tcp --dport 80 -d 10.4.2.0/24 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d 10.4.2.0/24 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 8080 -d 10.4.2.0/24 -j ACCEPT

# Allow to Core Zone MySQL
iptables -A OUTPUT -p tcp --dport 3306 -d 10.0.10.0/24 -j ACCEPT

# Allow to Core Zone Elasticsearch
iptables -A OUTPUT -p tcp --dport 443 -d 10.0.20.0/24 -j ACCEPT

# Allow DNS resolution
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

# Allow NTP
iptables -A OUTPUT -p udp --dport 123 -j ACCEPT

# ============================================
# EXPLICIT BLOCKS
# ============================================

# Block ALL internet access
iptables -A OUTPUT -d 0.0.0.0/0 -j LOG --log-prefix "JSZ-INTERNET-BLOCK: "
# (Already blocked by default DROP policy)

# Block Core Zone access
iptables -A OUTPUT -d 10.0.0.0/16 -j LOG --log-prefix "JSZ-CORE-BLOCK: "
iptables -A OUTPUT -d 10.0.0.0/16 -j DROP

# Block other regions
iptables -A OUTPUT -d 10.1.0.0/16 -j LOG --log-prefix "JSZ-US-BLOCK: "
iptables -A OUTPUT -d 10.1.0.0/16 -j DROP
iptables -A OUTPUT -d 10.2.0.0/16 -j LOG --log-prefix "JSZ-EU-BLOCK: "
iptables -A OUTPUT -d 10.2.0.0/16 -j DROP
iptables -A OUTPUT -d 10.3.0.0/16 -j LOG --log-prefix "JSZ-ASIA-BLOCK: "
iptables -A OUTPUT -d 10.3.0.0/16 -j DROP

# Log and drop everything else
iptables -A OUTPUT -j LOG --log-prefix "JSZ-OUTPUT-DROP: "
iptables -A OUTPUT -j DROP

# Save rules
iptables-save > /etc/iptables/rules.v4

echo "JSZ Gateway firewall rules applied"
echo "WARNING: NO INTERNET ACCESS ALLOWED"
```

---

## 11. Verification & Testing

### 10.1 Connectivity Tests

```bash
#!/bin/bash
# ============================================
# Multi-Region Firewall Verification Script
# ============================================

echo "=========================================="
echo "  GRAVITEE MULTI-REGION FIREWALL TEST"
echo "=========================================="

# Test US Region
echo ""
echo "=== US REGION TESTS ==="

# Test US Outer DMZ → Inner DMZ
echo -n "US Outer → Inner DMZ (8082): "
nc -zv -w 3 10.1.1.10 8082 2>&1 | grep -q "succeeded" && echo "✅ PASS" || echo "❌ FAIL"

# Test US Inner DMZ → Core Zone MySQL
echo -n "US Inner → Core MySQL (3306): "
nc -zv -w 3 10.0.10.10 3306 2>&1 | grep -q "succeeded" && echo "✅ PASS" || echo "❌ FAIL"

# Test US Inner DMZ → Core Zone ES
echo -n "US Inner → Core ES (443): "
nc -zv -w 3 10.0.20.10 443 2>&1 | grep -q "succeeded" && echo "✅ PASS" || echo "❌ FAIL"

# Test EU Region
echo ""
echo "=== EU REGION TESTS ==="

echo -n "EU Outer → Inner DMZ (8082): "
nc -zv -w 3 10.2.1.10 8082 2>&1 | grep -q "succeeded" && echo "✅ PASS" || echo "❌ FAIL"

echo -n "EU Inner → Core MySQL (3306): "
nc -zv -w 3 10.0.10.10 3306 2>&1 | grep -q "succeeded" && echo "✅ PASS" || echo "❌ FAIL"

# Test JSZ (Uses Core Zone MongoDB/ES, but restricted from other regions)
echo ""
echo "=== JSZ CONNECTIVITY TESTS ==="

# JSZ should reach Core Zone MySQL
echo -n "JSZ → Core Zone MySQL (3306): "
nc -zv -w 3 10.0.10.10 3306 2>&1 | grep -q "succeeded" && echo "✅ PASS" || echo "❌ FAIL"

# JSZ should reach Core Zone Elasticsearch
echo -n "JSZ → Core Zone ES (443): "
nc -zv -w 3 10.0.20.10 443 2>&1 | grep -q "succeeded" && echo "✅ PASS" || echo "❌ FAIL"

# JSZ should NOT reach Internet
echo -n "JSZ → Internet (should FAIL): "
nc -zv -w 3 8.8.8.8 53 2>&1 | grep -q "succeeded" && echo "❌ SECURITY ISSUE!" || echo "✅ BLOCKED (Expected)"

# JSZ should NOT reach other regions
echo -n "JSZ → US Region (should FAIL): "
nc -zv -w 3 10.1.1.10 8082 2>&1 | grep -q "succeeded" && echo "❌ SECURITY ISSUE!" || echo "✅ BLOCKED (Expected)"

echo -n "JSZ → EU Region (should FAIL): "
nc -zv -w 3 10.2.1.10 8082 2>&1 | grep -q "succeeded" && echo "❌ SECURITY ISSUE!" || echo "✅ BLOCKED (Expected)"

echo -n "JSZ → ASIA Region (should FAIL): "
nc -zv -w 3 10.3.1.10 8082 2>&1 | grep -q "succeeded" && echo "❌ SECURITY ISSUE!" || echo "✅ BLOCKED (Expected)"

# Test Core Zone
echo ""
echo "=== CORE ZONE TESTS ==="

# Core should reach MySQL Cluster
echo -n "Core → MySQL Cluster: "
nc -zv -w 3 mysql-cluster.internal 3306 2>&1 | grep -q "succeeded" && echo "✅ PASS" || echo "❌ FAIL"

echo ""
echo "=========================================="
echo "  TEST COMPLETE"
echo "=========================================="
```

### 10.2 Security Audit Checklist

| Check | US | EU | ASIA | JSZ | Core |
|-------|----|----|------|-----|------|
| No direct internet from Inner DMZ | ⬜ | ⬜ | ⬜ | ⬜ | N/A |
| Geo-blocking enabled | ⬜ | ⬜ | ⬜ | ⬜ | N/A |
| WAF rules active | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| TLS 1.3 enforced | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Default deny policy | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| JSZ uses Core Zone MySQL/ES | N/A | N/A | N/A | ⬜ | ⬜ |
| JSZ isolated from other regions | N/A | N/A | N/A | ⬜ | N/A |
| JSZ no internet egress | N/A | N/A | N/A | ⬜ | N/A |
| Audit logging enabled | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

---

*Document Version: 1.0 | Last Updated: February 2, 2026*

