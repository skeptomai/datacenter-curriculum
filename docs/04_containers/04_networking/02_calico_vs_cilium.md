---
level: specialized
estimated_time: 55 min
prerequisites:
  - 04_containers/04_networking/01_cni_deep_dive.md
  - 01_foundations/02_datacenter_topology/04_ecmp_load_balancing.md
next_recommended:
  - 04_containers/04_networking/03_ebpf_networking.md
tags: [calico, cilium, cni, bgp, ebpf, networking, performance]
---

# Calico vs Cilium: Architecture and Design Philosophy

## Learning Objectives

After reading this document, you will understand:
- Calico's BGP-based routing approach
- Cilium's eBPF-based datapath
- Fundamental architectural differences
- Performance characteristics of each
- NetworkPolicy implementation differences
- When to choose Calico vs Cilium
- Migration considerations

## Prerequisites

Before reading this, you should understand:
- CNI plugin architecture
- BGP routing basics
- Linux networking (routing, iptables)
- Kubernetes networking requirements

---

## 1. Architectural Overview

### Calico: Network-First Philosophy

**Design principle**: "Make the network smarter, not the host."

```
┌─────────────────────────────────────────────────┐
│ Calico Architecture                              │
│                                                  │
│ ┌─────────────────┐                             │
│ │ Felix (agent)   │ ← Runs on every node        │
│ │ - Programs      │                             │
│ │   routing       │                             │
│ │ - Programs      │                             │
│ │   iptables      │                             │
│ │ - Manages       │                             │
│ │   interfaces    │                             │
│ └────────┬────────┘                             │
│          │                                       │
│          ↓                                       │
│ ┌─────────────────┐       ┌──────────────────┐ │
│ │ BIRD (BGP)      │  ←→   │ BGP Router       │ │
│ │ - Advertises    │       │ (ToR/spine)      │ │
│ │   pod routes    │       │                  │ │
│ │ - Learns routes │       │                  │ │
│ └─────────────────┘       └──────────────────┘ │
│                                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ Linux Kernel Routing Table                  │ │
│ │ 10.244.1.0/24 via 192.168.1.10 (node2)      │ │
│ │ 10.244.2.0/24 via 192.168.1.11 (node3)      │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘

Data path: Standard Linux routing (no encapsulation)
```

**Key components**:
- **Felix**: Host agent, programs routes and iptables
- **BIRD**: BGP (Border Gateway Protocol) daemon, distributes routes
- **confd**: Monitors etcd, configures BIRD
- **Typha** (optional): Caching/fanout for large clusters

**Philosophy**: Use existing network infrastructure (BGP, ECMP) rather than overlays.

### Cilium: eBPF-First Philosophy

**Design principle**: "Programmable kernel networking with eBPF (extended Berkeley Packet Filter)."

```
┌─────────────────────────────────────────────────┐
│ Cilium Architecture                              │
│                                                  │
│ ┌─────────────────┐                             │
│ │ Cilium Agent    │ ← Runs on every node        │
│ │ - Compiles eBPF │                             │
│ │ - Loads into    │                             │
│ │   kernel        │                             │
│ │ - Manages       │                             │
│ │   endpoints     │                             │
│ └────────┬────────┘                             │
│          │                                       │
│          ↓                                       │
│ ┌─────────────────────────────────────────────┐ │
│ │ eBPF Programs (in kernel)                   │ │
│ │ - Socket layer (sockops, sockmap)           │ │
│ │ - TC (traffic control) ingress/egress       │ │
│ │ - XDP (eXpress Data Path)                   │ │
│ └─────────────────────────────────────────────┘ │
│          ↓                                       │
│ ┌─────────────────────────────────────────────┐ │
│ │ eBPF Maps (shared state)                    │ │
│ │ - Endpoint map (pod IPs)                    │ │
│ │ - Policy map (allow/deny rules)             │ │
│ │ - Service map (load balancing)              │ │
│ │ - NAT map (connection tracking)             │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘

Data path: eBPF (in kernel, bypasses much of network stack)
```

**Key components**:
- **Cilium Agent**: User-space daemon, manages eBPF
- **eBPF programs**: Kernel-space networking logic
- **eBPF maps**: Shared state between programs
- **Hubble**: Observability (flow logs, metrics)

**Philosophy**: Use eBPF to make the kernel programmable and bypass slow paths.

---

## 2. Data Path Comparison

### Calico Data Path (Native Routing)

**Pod-to-pod on same node**:
```
Pod A (10.244.0.5) → Pod B (10.244.0.6)

1. Pod A: Send packet with dst=10.244.0.6
2. veth pair → host network namespace
3. Host routing table: 10.244.0.6 is local
4. Host forwards via veth to Pod B
5. Pod B receives packet

No encapsulation, no iptables (for routing)
```

**Pod-to-pod across nodes** (BGP mode):
```
Node 1 (Pod A: 10.244.0.5) → Node 2 (Pod B: 10.244.1.10)

1. Pod A sends packet: dst=10.244.1.10
2. veth pair → Node 1 routing table
3. Node 1: 10.244.1.0/24 via 192.168.1.10 (Node 2)
4. Packet sent to Node 2: src=10.244.0.5, dst=10.244.1.10
5. Node 2 routing table: 10.244.1.10 is local
6. Node 2 forwards via veth to Pod B
7. Pod B receives packet

No encapsulation (native IP routing)
```

**Network policy enforcement** (iptables):
```
Pod A → Pod B (allowed by policy)

1. Packet enters Node 2
2. iptables rules (Calico chains):
   -A cali-fw-cali123 -j MARK --set-mark 0x1000/0x1000
   -A cali-fw-cali123 -m mark --mark 0x1000/0x1000 -j RETURN
   -A cali-fw-cali123 -j DROP
3. If packet matches policy: MARK + RETURN (allowed)
4. If no match: DROP
5. Allowed packets continue to Pod B
```

**Key characteristics**:
- Uses standard Linux routing
- NetworkPolicy via iptables
- No encapsulation overhead
- Scales with kernel routing (hundreds of thousands of routes)

### Cilium Data Path (eBPF)

**Pod-to-pod on same node**:
```
Pod A (10.244.0.5) → Pod B (10.244.0.6)

1. Pod A sends packet: dst=10.244.0.6
2. veth pair → eBPF TC (traffic control) hook
3. eBPF program (loaded by Cilium):
   - Looks up dst IP in endpoint map
   - Checks policy map (allow/deny)
   - If allowed: Redirects packet to Pod B veth
4. Packet delivered to Pod B

No iptables, no routing table lookup (eBPF redirect)
```

**Pod-to-pod across nodes** (VXLAN mode):
```
Node 1 (Pod A: 10.244.0.5) → Node 2 (Pod B: 10.244.1.10)

1. Pod A sends packet: dst=10.244.1.10
2. eBPF TC hook on veth
3. eBPF program:
   - Looks up dst=10.244.1.10 in endpoint map
   - Finds: Node 2 (192.168.1.10)
   - Encapsulates in VXLAN
4. Sends: outer dst=192.168.1.10, inner dst=10.244.1.10
5. Node 2 receives, VXLAN decap (eBPF XDP)
6. eBPF looks up inner dst, finds Pod B
7. Packet delivered to Pod B

Encapsulation done in eBPF (faster than kernel VXLAN)
```

**Pod-to-pod across nodes** (native routing mode):
```
Similar to Calico, but policy enforcement still in eBPF
```

**Network policy enforcement** (eBPF):
```
Pod A → Pod B

1. eBPF TC hook intercepts packet
2. eBPF program:
   a. Extract src IP, dst IP, protocol, port
   b. Hash (src, dst, protocol, port) → policy map key
   c. Lookup in policy map (eBPF hash table)
   d. Result: ALLOW or DROP
3. If ALLOW: Redirect to destination
4. If DROP: Drop packet immediately

No iptables traversal (faster)
```

**Key characteristics**:
- eBPF programs replace iptables
- Policy enforcement in kernel (eBPF maps)
- Supports VXLAN, native routing, or Geneve
- Can use XDP for extreme performance

---

## 3. Routing Models

### Calico: BGP Everywhere

**BGP peer options**:

**1. Node-to-node mesh** (default, small clusters):
```
Each node peers with every other node

3 nodes: 3 × (3-1)/2 = 3 BGP sessions
10 nodes: 10 × 9/2 = 45 BGP sessions
100 nodes: 100 × 99/2 = 4,950 BGP sessions ← Doesn't scale!
```

**2. Route reflectors** (large clusters):
```
┌──────────────────────────────────────┐
│ Route Reflectors (2-3 nodes)        │
│   ↑   ↑   ↑                          │
└───┼───┼───┼──────────────────────────┘
    │   │   │
    ↓   ↓   ↓
  ┌───┬───┬───┬───┬───┬───┐
  │N1 │N2 │N3 │N4 │...│N100│ Worker nodes
  └───┴───┴───┴───┴───┴───┘

Each worker peers with 2-3 route reflectors
RR peers with all workers + other RRs
Worker sessions: 2-3 per node
```

**Connection to earlier concepts**:
Recall from `05_specialized/02_overlay_networking/01_bgp_communities_vs_route_reflectors.md`:
- Route reflectors reduce full-mesh scaling problems
- Similar to datacenter BGP spine-leaf designs

**3. ToR (Top-of-Rack) peering**:
```
┌──────────────────────────────────────┐
│ ToR Switch (BGP enabled)             │
│   ↑   ↑   ↑                          │
└───┼───┼───┼──────────────────────────┘
    │   │   │
    ↓   ↓   ↓
  ┌───┬───┬───┐
  │N1 │N2 │N3 │ Nodes in rack
  └───┴───┴───┘

Nodes peer with ToR switch
ToR advertises pod routes to spine
```

**Route advertisement**:
```
Node 1 advertises:
  10.244.0.0/24 via 192.168.1.5 (Node 1 IP)

Node 2 learns:
  10.244.0.0/24 → next-hop 192.168.1.5
  Installs in kernel routing table
```

**ECMP (Equal-Cost Multi-Path)**:
Recall from `01_foundations/02_datacenter_topology/04_ecmp_load_balancing.md`:
```
If multiple paths to destination:
  10.244.5.0/24 via 192.168.1.10
  10.244.5.0/24 via 192.168.1.11

Kernel uses 5-tuple hash to choose path (same flow → same path)
```

### Cilium: Flexible Routing

**Routing modes**:

**1. VXLAN** (default, works anywhere):
```
Pod CIDR allocated per node
Cilium maintains endpoint map with node IPs
eBPF handles encapsulation/decapsulation

No BGP needed (overlay network)
```

**2. Native routing** (best performance):
```
Use existing network infrastructure (BGP, static routes)

Similar to Calico, but policy enforcement still in eBPF:
  Routing: Linux kernel
  Policy: eBPF
```

**3. Direct routing** (cloud-native):
```
AWS: Use VPC routing tables
GCP: Use VPC routes
Azure: Use route tables

Cilium installs routes via cloud API
No BGP, no encapsulation
```

**4. Geneve** (more flexible overlay):
```
Like VXLAN, but supports more metadata
Better for multi-tenant scenarios
```

---

## 4. Network Policy Implementation

### Calico: iptables (traditional)

**Example policy**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

**Calico implementation** (iptables):
```bash
# Calico creates chains per pod
iptables -t filter -N cali-fw-cali123abc  # Firewall chain for pod
iptables -t filter -N cali-to-cali123abc  # To-pod chain

# Default deny
iptables -A cali-fw-cali123abc -j DROP

# Allow from frontend
iptables -I cali-fw-cali123abc \
  -m set --match-set cali-frontend-pods src \
  -p tcp --dport 8080 \
  -j MARK --set-mark 0x1000/0x1000

iptables -I cali-fw-cali123abc \
  -m mark --mark 0x1000/0x1000 \
  -j RETURN

# Chain linkage
iptables -A FORWARD -m comment --comment "cali:..." \
  -j cali-FORWARD
iptables -A cali-FORWARD -o cali123abc \
  -j cali-to-cali123abc
```

**Performance characteristics**:
```
For N pods, M policies:
  iptables rules: O(N × M)

100 pods, 10 policies = ~1000 rules
1000 pods, 100 policies = ~100,000 rules

iptables is linear scan (slow at scale)
```

**ipset optimization**:
```
Instead of one rule per source pod:
  -s 10.244.0.5 -j ACCEPT
  -s 10.244.0.6 -j ACCEPT
  ...

Use ipset (hash table lookup):
  ipset create cali-frontend-pods hash:ip
  ipset add cali-frontend-pods 10.244.0.5
  ipset add cali-frontend-pods 10.244.0.6

  iptables -A chain -m set --match-set cali-frontend-pods src -j ACCEPT

O(1) lookup instead of O(N)
```

### Cilium: eBPF (modern)

**Same policy** (NetworkPolicy API):
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
...
```

**Cilium implementation** (eBPF):
```c
// Simplified eBPF program (loaded by Cilium)
SEC("tc")
int tc_ingress(struct __sk_buff *skb) {
    struct endpoint_key key = {};
    struct policy_entry *policy;

    // Extract packet headers
    parse_packet(skb, &key);  // Gets src IP, dst IP, port, protocol

    // Lookup policy
    policy = bpf_map_lookup_elem(&POLICY_MAP, &key);
    if (!policy)
        return TC_ACT_SHOT;  // DROP

    if (policy->action == ALLOW)
        return TC_ACT_OK;  // ACCEPT

    return TC_ACT_SHOT;  // DROP
}
```

**eBPF maps** (in kernel memory):
```
POLICY_MAP (hash table):
  Key: (src_ip, dst_ip, protocol, dst_port)
  Value: {action: ALLOW/DROP, labels: [...]}

Example entry:
  (10.244.0.5, 10.244.1.10, TCP, 8080) → ALLOW

Lookup: O(1) hash table lookup (very fast)
```

**Performance characteristics**:
```
Policy lookup: O(1) (eBPF map hash lookup)
No iptables traversal (bypass kernel networking slow path)

Benchmark: 10,000 policies
  Calico (iptables): ~1ms per packet
  Cilium (eBPF): ~10µs per packet

100x faster for policy enforcement
```

**Layer 7 policies** (unique to Cilium):
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: allow-get-only
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/.*"
```

**eBPF can parse HTTP**:
```
1. Packet arrives
2. eBPF parses TCP payload
3. Extracts HTTP method + path
4. Checks policy (GET /api/.* allowed)
5. Allow or drop at kernel level
```

**Calico cannot do this** (iptables only sees IP/TCP, not HTTP).

---

## 5. Performance Comparison

### Throughput Benchmarks

**Test setup**: 10 Gbps NICs, 100 concurrent connections.

| Scenario                  | Calico     | Cilium (VXLAN) | Cilium (Native) | Baseline |
|---------------------------|------------|----------------|-----------------|----------|
| Pod-to-pod (same node)    | 9.2 Gbps   | 9.8 Gbps       | 9.8 Gbps        | 9.9 Gbps |
| Pod-to-pod (cross-node)   | 9.1 Gbps   | 8.3 Gbps       | 9.3 Gbps        | 9.9 Gbps |
| With NetworkPolicy (1 rule)| 8.9 Gbps  | 9.7 Gbps       | 9.7 Gbps        | -        |
| With NetworkPolicy (100 rules)| 7.2 Gbps | 9.6 Gbps    | 9.6 Gbps        | -        |

**Observations**:
- Calico native routing ≈ Cilium native routing (both use kernel routing)
- Cilium VXLAN ≈ 10% overhead (encapsulation)
- Cilium eBPF policy >> Calico iptables policy (100 rules)

### Latency Benchmarks

**Pod-to-pod latency** (p99):

| Configuration             | Calico     | Cilium (eBPF) |
|---------------------------|------------|---------------|
| No NetworkPolicy          | 0.15 ms    | 0.12 ms       |
| 10 NetworkPolicies        | 0.18 ms    | 0.13 ms       |
| 100 NetworkPolicies       | 0.35 ms    | 0.14 ms       |
| 1000 NetworkPolicies      | 1.2 ms     | 0.15 ms       |

**Why Cilium is faster with many policies**:
- iptables: Linear rule scan
- eBPF: Hash table lookup (constant time)

### CPU Usage

**Idle cluster** (100 nodes, 1000 pods):
- Calico: ~0.5% CPU per node
- Cilium: ~1.2% CPU per node (eBPF compilation overhead)

**Heavy traffic** (10 Gbps):
- Calico: ~15% CPU (iptables processing)
- Cilium: ~8% CPU (eBPF in kernel)

**Policy updates** (adding 100 policies):
- Calico: 5-10 seconds (iptables reload)
- Cilium: 1-2 seconds (eBPF map updates)

---

## 6. Feature Comparison

### Core Features

| Feature                | Calico         | Cilium         |
|------------------------|----------------|----------------|
| **CNI compliance**     | ✓              | ✓              |
| **NetworkPolicy API**  | ✓              | ✓              |
| **IPv4/IPv6 dual-stack**| ✓             | ✓              |
| **Native routing**     | ✓ (BGP)        | ✓ (BGP/cloud)  |
| **Overlay networking** | ✓ (VXLAN, IPinIP)| ✓ (VXLAN, Geneve)|
| **Encryption**         | ✓ (WireGuard)  | ✓ (WireGuard, IPsec)|
| **Service load balancing**| kube-proxy | eBPF (replaces kube-proxy)|

### Advanced Features

| Feature                | Calico         | Cilium         |
|------------------------|----------------|----------------|
| **Layer 7 policy**     | ✗              | ✓ (HTTP, gRPC, Kafka)|
| **eBPF datapath**      | ✗              | ✓              |
| **kube-proxy replacement**| ✗           | ✓              |
| **Multi-cluster networking**| ✓ (paid)  | ✓              |
| **Observability (Hubble)**| ✗           | ✓              |
| **Service mesh (no sidecar)**| ✗        | ✓              |
| **Bandwidth management**| ✓             | ✓              |
| **Windows nodes**      | ✓              | ✗              |

### Security Features

| Feature                | Calico         | Cilium         |
|------------------------|----------------|----------------|
| **Pod identity (mTLS)**| ✗              | ✓              |
| **DNS-aware policy**   | ✓              | ✓              |
| **Egress gateway**     | ✓              | ✓              |
| **Threat detection**   | ✗              | ✓ (Hubble)     |
| **Network flow logs**  | ✗              | ✓ (Hubble)     |

---

## 7. When to Use Each

### Choose Calico if:

**1. You have BGP-capable network infrastructure**
```
Existing datacenter with BGP:
  - ToR switches run BGP
  - Spine routers run BGP
  - Network team familiar with BGP

Calico integrates seamlessly (no overlays needed)
```

**2. Windows node support required**
```
Kubernetes cluster with Windows nodes
Calico is the only major CNI supporting Windows
```

**3. Simpler operations preferred**
```
Calico:
  - Mature (10+ years)
  - Well-documented
  - Large community
  - Familiar technologies (BGP, iptables)
```

**4. Conservative approach**
```
eBPF is newer technology
iptables is battle-tested
Team prefers proven tech
```

### Choose Cilium if:

**1. Performance critical (low latency, high throughput)**
```
Latency-sensitive workloads:
  - Real-time processing
  - High-frequency trading
  - Gaming

eBPF provides consistent low latency
```

**2. Many NetworkPolicies (100+)**
```
Micro-segmentation requirements:
  - Zero-trust networking
  - Compliance (PCI-DSS, HIPAA)
  - Multi-tenant clusters

Cilium scales to thousands of policies with O(1) lookup
```

**3. Layer 7 policies needed**
```
HTTP/gRPC/Kafka policy enforcement:
  - Allow only GET requests
  - Block specific API paths
  - Rate-limit by endpoint

iptables cannot do this (IP/port only)
```

**4. Advanced observability required**
```
Hubble provides:
  - Network flow logs
  - Service dependency maps
  - DNS visibility
  - HTTP metrics

No equivalent in Calico (need external tools)
```

**5. Service mesh without sidecars**
```
Cilium can replace Istio data plane:
  - No Envoy sidecar overhead
  - mTLS in kernel (eBPF)
  - Lower latency, less CPU

Ideal for: Cost optimization, performance
```

---

## 8. Migration Considerations

### Calico → Cilium

**Risks**:
- Different data path (potential bugs)
- eBPF requires kernel 4.19+ (check node OS)
- Different troubleshooting tools

**Strategy**:
```
1. Test in dev cluster first
2. Gradual rollout:
   a. Drain node
   b. Remove Calico
   c. Install Cilium
   d. Uncordon node
   e. Verify connectivity
3. One node at a time (reduce blast radius)
```

**Preserve policies**:
```
NetworkPolicy API is standard
  → Policies work on both Calico and Cilium

CiliumNetworkPolicy (L7) only works on Cilium
  → Add these after migration complete
```

### Cilium → Calico

**Risks**:
- Loss of L7 policies (not supported in Calico)
- Loss of Hubble observability

**Strategy**:
```
1. Remove CiliumNetworkPolicy resources
2. Verify only NetworkPolicy API used
3. Follow similar gradual rollout
```

---

## Quick Reference

### Architecture Summary

```
Calico:
  Data path: Linux kernel routing + iptables
  Policy: iptables chains + ipset
  Routing: BGP (BIRD)
  Strength: Mature, BGP integration

Cilium:
  Data path: eBPF programs in kernel
  Policy: eBPF maps (hash tables)
  Routing: VXLAN/Geneve/native
  Strength: Performance, L7 policy, observability
```

### Decision Matrix

| Requirement                  | Calico | Cilium |
|------------------------------|--------|--------|
| BGP datacenter network       | ✓✓     | ✓      |
| Windows nodes                | ✓✓     | ✗      |
| Layer 7 policy               | ✗      | ✓✓     |
| Observability (Hubble)       | ✗      | ✓✓     |
| Low latency (<1ms p99)       | ✓      | ✓✓     |
| Many policies (>100)         | ✓      | ✓✓     |
| Conservative operations      | ✓✓     | ✓      |
| Service mesh (no sidecar)    | ✗      | ✓✓     |

✓✓ = Excellent fit, ✓ = Supported, ✗ = Not supported

### Common Commands

```bash
# Calico
calicoctl get nodes
calicoctl get bgpPeer
calicoctl get ipPool
kubectl get felixconfiguration

# Cilium
cilium status
cilium connectivity test
cilium config view
hubble observe flows --pod mypod
hubble observe --http-status 500
```

---

## Summary

**Calico**: Network-first design using BGP and standard Linux networking.
- Mature, battle-tested
- BGP integration with datacenter switches
- iptables-based policy (scales to ~1000 pods/node)
- Windows support

**Cilium**: eBPF-first design for programmable kernel networking.
- High performance (eBPF bypasses networking slow paths)
- Layer 7 policies (HTTP, gRPC, Kafka)
- Observability with Hubble (flow logs, service maps)
- Service mesh without sidecars

**Both are production-ready**. Choose based on:
- Infrastructure (BGP network → Calico advantage)
- Requirements (L7 policy → Cilium advantage)
- Performance needs (latency-sensitive → Cilium advantage)
- Team expertise (BGP/iptables → Calico, eBPF → Cilium)

**Next**: Now that you understand Cilium's eBPF approach, we'll dive deeper into **eBPF networking** fundamentals.

---

## Related Documents

- **Previous**: `04_networking/01_cni_deep_dive.md` - CNI fundamentals
- **Next**: `04_networking/03_ebpf_networking.md` - eBPF deep dive
- **Foundation**: `01_foundations/02_datacenter_topology/04_ecmp_load_balancing.md` - BGP ECMP
- **Related**: `05_specialized/02_overlay_networking/01_bgp_communities_vs_route_reflectors.md` - BGP scaling
