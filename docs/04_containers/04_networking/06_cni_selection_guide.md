---
level: intermediate
estimated_time: 30 min
prerequisites:
  - 04_containers/04_networking/01_cni_deep_dive.md
  - 04_containers/04_networking/02_calico_vs_cilium.md
next_recommended:
  - 04_containers/05_security/05_compliance_fips_pci.md
tags: [cni, flannel, calico, cilium, networking, kubernetes, decision-guide]
---

# CNI Provider Selection Guide

**Learning Objectives:**
- Understand the trade-offs between Flannel, Calico, Cilium, and cloud-native CNI providers
- Match CNI capabilities to deployment requirements
- Recognize when each provider is the right tool

---

## Introduction

Choosing a CNI (Container Network Interface) provider is one of the most consequential infrastructure decisions you make for a Kubernetes cluster. The choice affects security posture, operational complexity, performance headroom, and how deeply your cluster integrates with the physical network beneath it.

The previous document (`02_calico_vs_cilium.md`) covers the architectural internals of Calico and Cilium in depth. This guide takes the practitioner's view: given your constraints, which CNI should you pick?

---

## 1. Provider Overview

### Flannel

Flannel is a lightweight CNI created by CoreOS. It creates a flat overlay network across all cluster nodes using VXLAN (Virtual Extensible LAN) encapsulation by default.

**Architecture**:
```
┌─────────────────────────────────────────────┐
│ Node 1                    Node 2             │
│                                              │
│  Pod A (10.244.0.5)        Pod B (10.244.1.5)│
│      │                          │            │
│  flannel.1 (VTEP)          flannel.1 (VTEP) │
│      │   VXLAN tunnel           │            │
│      └──────────────────────────┘            │
│           Underlay: physical L3 network      │
└─────────────────────────────────────────────┘
```

**Pros**:
- Easiest CNI to deploy — installs with a single manifest, zero configuration
- Very low base resource consumption
- Works on any IP network without any router changes

**Cons**:
- No support for Kubernetes NetworkPolicy out of the box — all pods can reach all pods
- VXLAN encapsulation reduces effective MTU (Maximum Transmission Unit) by 50 bytes and incurs slight CPU overhead for encap/decap
- No observability features

**When Flannel makes sense**:
- Local development clusters (kind, k3s test environments)
- Lab environments where connectivity is needed but isolation is not
- Clusters where another tool (Calico's policy engine, Canal) will handle NetworkPolicy separately

---

### Calico

Calico configures a Layer 3 (L3) network using BGP (Border Gateway Protocol) routing. It is battle-tested across on-premises datacenters and cloud environments. See `02_calico_vs_cilium.md` for a detailed architectural breakdown.

**Architecture** (BGP native mode):
```
┌──────────────────────────────────────────────┐
│ Node 1                     Node 2             │
│                                               │
│  Pod A (10.244.0.5)         Pod B (10.244.1.5)│
│      │                           │            │
│  Felix (routes/policy)      Felix              │
│      │                           │            │
│  BIRD (BGP daemon)          BIRD               │
│      │ BGP session               │            │
│      └───────────────────────────┘            │
│           Physical routed network             │
└──────────────────────────────────────────────┘
No VXLAN — packets route natively
```

**Pros**:
- Native routing with no encapsulation overhead — packets traverse the physical fabric as standard IP traffic
- Mature, robust NetworkPolicy enforcement (L3/L4)
- Integrates directly with physical BGP infrastructure (ToR switches, spine routers)
- Highly compatible across bare-metal and all major cloud providers

**Cons**:
- BGP configuration requires solid understanding of routing — not beginner-friendly
- Route distribution at scale needs route reflectors or ToR peering to avoid full-mesh BGP session explosion
- No Layer 7 (L7) policy enforcement (HTTP, gRPC)

**When Calico makes sense**:
- On-premises datacenters with BGP-capable switches (Arista, Cisco Nexus, Juniper)
- Environments requiring strict NetworkPolicy enforcement (PCI-DSS, HIPAA)
- Multi-cloud or hybrid environments where network teams want a single policy model
- When Windows node support is required (Calico is the only major CNI with Windows support)

---

### Cilium

Cilium leverages eBPF (extended Berkeley Packet Filter) to process traffic directly in the Linux kernel, bypassing iptables entirely. See `02_calico_vs_cilium.md` and `03_ebpf_networking.md` for deep architectural coverage.

**Architecture**:
```
┌──────────────────────────────────────────────┐
│ Node 1                                        │
│                                               │
│  Pod A ──► eBPF TC hook ──► eBPF policy map  │
│                │                              │
│         eBPF encap (VXLAN or native)          │
│                │                              │
│         Physical network                      │
└──────────────────────────────────────────────┘
No iptables — all policy enforcement via eBPF maps (O(1) lookup)
```

**Pros**:
- Outstanding throughput and low latency — eBPF bypasses the kernel network stack slow path
- L3–L7 network policy enforcement (HTTP method, gRPC service, Kafka topic)
- Can fully replace kube-proxy for faster service routing
- Native observability via Hubble (flow logs, service dependency maps, DNS visibility)
- Sidecar-free service mesh (mTLS in kernel via eBPF)

**Cons**:
- Requires a modern Linux kernel (4.19+ minimum, 5.10+ recommended for full feature set)
- Steeper learning curve — eBPF concepts and Cilium-specific tooling (`cilium`, `hubble`)
- Higher baseline CPU on idle (eBPF program compilation at startup)

**When Cilium makes sense**:
- High-performance or latency-sensitive workloads
- Clusters with 100+ NetworkPolicies (eBPF O(1) lookup vs iptables linear scan)
- Zero-trust networking or environments requiring L7 visibility
- Service mesh deployments where you want to avoid Envoy sidecar CPU/memory overhead

---

### Cloud-Native Providers (AWS VPC CNI, Azure CNI, GKE Dataplane V2)

Major cloud providers offer CNIs that bind Kubernetes pods directly to the cloud network layer, assigning real VPC (Virtual Private Cloud) IP addresses to pods.

**Architecture** (AWS VPC CNI example):
```
┌──────────────────────────────────────────────┐
│ EC2 Node                                      │
│                                               │
│  Pod A (10.0.1.50)   ← Real VPC IP           │
│      │                                        │
│  ENI (Elastic Network Interface)              │
│      │                                        │
│  AWS VPC routing fabric                       │
└──────────────────────────────────────────────┘
No overlay — pods are first-class VPC citizens
```

**Pros**:
- Zero encapsulation overhead — pods use native VPC routing
- Pods integrate directly with cloud-managed services via security groups (AWS RDS, ElastiCache, etc.)
- No BGP configuration required — the cloud handles route distribution

**Cons**:
- Vendor lock-in — not portable to other clouds or on-premises
- Tightly coupled to cloud APIs — upgrades can break if API versions diverge
- IP address exhaustion: each pod consumes a real VPC IP, which can exhaust subnet space if nodes scale faster than subnets are provisioned

**When cloud-native CNI makes sense**:
- Pure single-cloud deployments where portability is not required
- When pods need direct integration with cloud-managed services via security groups
- When eliminating all networking complexity is more important than flexibility

---

## 2. Comparison Summary

| CNI Provider | Routing Model | NetworkPolicy | Observability | Ideal Use Case |
|---|---|---|---|---|
| **Flannel** | Overlay (VXLAN) | None (out of box) | None | Dev clusters, labs, simple connectivity |
| **Calico** | BGP native or VXLAN | L3/L4 (mature) | Medium | On-prem BGP fabric, compliance, multi-cloud |
| **Cilium** | eBPF + overlay or native | L3–L7 (eBPF) | High (Hubble) | High-performance, enterprise microservices |
| **Cloud CNI** | Native VPC routing | L3/L4 (cloud SG) | Cloud-native | Single-cloud, managed-service integration |

---

## 3. Decision Guide

### Start here: what is your deployment environment?

```
On-premises or bare metal?
  ├── BGP-capable switches (Arista, Nexus, Juniper)?
  │     └── → Calico (BGP native mode)
  ├── No BGP infrastructure, need simplicity?
  │     └── → Flannel (labs) or Cilium (VXLAN mode, production)
  └── Compliance/high-security requirements?
        └── → Calico or Cilium

Single cloud provider?
  ├── AWS / Azure / GCP and want native VPC integration?
  │     └── → Cloud-native CNI
  └── Need portability or advanced policy?
        └── → Calico or Cilium

Multi-cloud or hybrid?
  └── → Calico (consistent BGP model) or Cilium (cluster mesh)
```

### Secondary: what are your requirements?

| Requirement | Recommended |
|---|---|
| Layer 7 (HTTP/gRPC) policy enforcement | Cilium |
| FIPS 140-2/3 compliant node-to-node encryption | Calico + IPsec |
| Windows node support | Calico |
| kube-proxy replacement | Cilium |
| Direct BGP peering with physical switches | Calico |
| Network flow logs and service maps | Cilium (Hubble) |
| Simplest possible setup | Flannel |
| PCI-DSS default-deny segmentation at scale | Calico or Cilium |

---

## Quick Reference

| Requirement | Flannel | Calico | Cilium | Cloud CNI |
|---|---|---|---|---|
| NetworkPolicy | ✗ | ✓ | ✓ | ✓ (partial) |
| L7 policy | ✗ | ✗ | ✓ | ✗ |
| Native routing (no encap) | ✗ | ✓ | ✓ (native mode) | ✓ |
| BGP peering to switches | ✗ | ✓ | ✓ (BGP mode) | ✗ |
| Windows nodes | ✗ | ✓ | ✗ | ✓ (partial) |
| Flow logs / observability | ✗ | ✗ | ✓ (Hubble) | ✓ (cloud) |
| FIPS-compatible encryption | ✗ | ✓ (IPsec) | ✓ (IPsec) | Cloud-dependent |
| Setup complexity | Low | Medium | High | Low |

---

## What You've Learned

✅ Flannel's simplicity and its key limitation: no NetworkPolicy support  
✅ Calico's BGP-native approach and when physical network integration matters  
✅ Cilium's eBPF advantage at L7 and at scale  
✅ Cloud-native CNI trade-offs (zero overhead, vendor lock-in)  
✅ A decision framework for matching CNI to deployment requirements  

---

## Next Steps

**Related topics:**
→ [Calico vs Cilium Architecture](02_calico_vs_cilium.md) — deep internals of data plane modes and encryption  
→ [eBPF Networking](03_ebpf_networking.md) — how Cilium's kernel programs work  
→ [Network Policies Advanced](05_network_policies_advanced.md) — enforcing zero-trust with NetworkPolicy  
→ [Compliance: FIPS and PCI-DSS](../05_security/05_compliance_fips_pci.md) — encryption and audit requirements for regulated workloads
