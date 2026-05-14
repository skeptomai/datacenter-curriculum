---
level: intermediate
estimated_time: 45 min
prerequisites:
  - 02_intermediate/01_advanced_networking/02_overlay_mechanics.md
next_recommended:
  - 05_specialized/02_overlay_networking/01_vxlan_geneve_bgp.md
  - 05_specialized/02_overlay_networking/02_bgp_communities_rr.md
tags: [networking, vxlan, evpn, bgp, spine-leaf, route-reflectors, irb, anycast]
---

# EVPN and BGP: The Control Plane That Makes VXLAN Practical

**Learning Objectives:**
- Explain why VXLAN alone is insufficient for large-scale datacenters
- Describe the three critical EVPN (Ethernet VPN) route types and what each advertises
- Understand BGP's (Border Gateway Protocol) evolved role as a datacenter fabric protocol
- Trace a complete packet flow through a VXLAN/EVPN/BGP spine-leaf fabric
- Distinguish Symmetric from Asymmetric IRB (Integrated Routing & Bridging) for inter-VNI traffic
- Explain the Anycast Gateway pattern and why it enables ECMP (Equal Cost Multipath) at the gateway level

---

## Why VXLAN Alone Isn't Enough

The previous document covered how VXLAN encapsulates Layer 2 frames inside UDP (User Datagram Protocol) packets, giving you 16 million virtual networks instead of 4,096 VLANs (Virtual Local Area Networks). But VXLAN's data plane creates a new set of problems:

| Problem | What It Means |
|---------|---------------|
| **VTEP discovery** | How do VXLAN Tunnel Endpoints find each other? |
| **MAC learning at scale** | Flood-and-learn requires multicast or head-end replication — both scale poorly |
| **Inter-VNI routing** | Traffic between two VNIs (e.g., VNI-100 web tier → VNI-200 DB tier) needs a routing step |
| **VM mobility signaling** | When a VM moves racks, all VTEPs must update their forwarding tables |

**EVPN (Ethernet VPN, RFC 7432) is the answer.** It is a family of BGP routes that gives VTEPs a control plane: instead of learning by flooding, they advertise MAC (Media Access Control) and IP reachability via BGP before the first data packet is sent.

```
WITHOUT EVPN (flood-and-learn):

  VM boots → VTEP floods ARP (Address Resolution Protocol) to all VTEPs
           → Destination VTEP responds
           → Source VTEP learns MAC→VTEP mapping
           → Subsequent traffic unicast
  
  Problem: Broadcast storms, multicast dependency, slow convergence

WITH EVPN (control-plane learning):

  VM boots → VTEP immediately advertises BGP route:
             "MAC=aa:bb:cc, IP=10.0.0.5, VNI=100, Next-Hop=VTEP-A"
           → All peer VTEPs pre-populate their forwarding tables
           → First data packet is already unicast — no flooding
  
  Result: Deterministic, scalable, no multicast required
```

---

## Part 1: EVPN Route Types

EVPN extends BGP with a new address family: **AFI/SAFI 25/70** (Address Family Identifier / Subsequent Address Family Identifier — L2VPN-EVPN). Within this family, five route types carry different reachability information. Three are essential to understand.

### Type 2: MAC/IP Advertisement Route (the Workhorse)

Type 2 is how VTEPs advertise that a host lives behind them. When a VM or container boots:

```
VTEP-A advertises BGP Type 2 route:
  MAC  = aa:bb:cc:dd:ee:ff
  IP   = 192.168.1.10  (optional, enables ARP suppression)
  VNI  = 100
  Next-Hop = 10.0.1.11  (VTEP-A's underlay IP)
  Route Target = 65000:100  (controls which VTEPs import this)
```

Every other VTEP that imports Route Target 65000:100 installs this entry in its forwarding database immediately — without having seen a single data packet from that host.

**ARP suppression:** Because Type 2 carries the IP→MAC binding, a receiving VTEP can answer ARP requests locally on behalf of remote hosts. The ARP never crosses the fabric.

### Type 3: Inclusive Multicast Ethernet Tag Route (BUM Membership)

Type 3 announces that a VTEP is a member of a VNI and tells peers where to send BUM (Broadcast, Unknown-unicast, Multicast) traffic. This replaces the need for IP multicast group configuration.

```
VTEP-A advertises BGP Type 3 route:
  VNI      = 100
  VTEP IP  = 10.0.1.11

All VTEPs receiving this route know:
  "For BUM traffic in VNI-100, send a unicast copy to 10.0.1.11"
  (This is BGP-driven ingress replication — no multicast infrastructure needed)
```

### Type 5: IP Prefix Route (Inter-VNI Routing)

Type 5 carries IP prefixes rather than MAC addresses. It is how VTEPs advertise routable subnets — enabling traffic to cross VNI boundaries without flooding.

```
VTEP-A advertises BGP Type 5 route:
  Prefix   = 192.168.2.0/24
  VNI      = 200           (the L3 VNI for routing)
  Next-Hop = 10.0.1.11

A VM in VNI-100 wanting to reach 192.168.2.50 (in VNI-200):
  → Looks up Type 5 route: next-hop is VTEP-A
  → Encapsulates with the L3 VNI
  → VTEP-A routes into VNI-200 locally
```

Type 5 is what makes leaf-level distributed routing possible — no central router required.

---

## Part 2: BGP's New Role in the Datacenter

BGP (Border Gateway Protocol, RFC 4271) was originally designed for inter-AS (Autonomous System) routing between ISPs (Internet Service Providers). In modern datacenters it has become the **universal control plane** for two separate jobs:

1. **Underlay routing** — routing physical IP packets between leaves and spines (replacing OSPF)
2. **EVPN overlay** — distributing MAC/IP/VNI reachability information between VTEPs

### Spine-Leaf Topology with BGP

Nearly all modern datacenters use a spine-leaf (Clos) fabric:

```
          Spine-1        Spine-2
           (AS 65000)    (AS 65000)
              |    \   /    |
              |     \ /     |
              |      X      |
              |     / \     |
           Leaf-1       Leaf-2       Leaf-3
          (AS 65001)  (AS 65002)  (AS 65003)
              |            |            |
           Servers      Servers      Servers
```

**BGP deployment in this fabric:**

- Every leaf switch runs BGP in its own private ASN (Autonomous System Number, range 64512–65534)
- Spines run BGP and act as route reflectors for EVPN routes (see below)
- Each leaf peers with both spines (eBGP — external BGP between different ASNs)
- ECMP across both spines is automatic: BGP selects multiple equal-cost paths, hardware load-balances flows across them

**Why BGP instead of OSPF (Open Shortest Path First) for the underlay?**

| Criterion | BGP | OSPF |
|-----------|-----|------|
| Scale | Thousands of devices | Hundreds before tuning needed |
| Path control | Policy-rich (communities, local-pref) | Limited |
| Convergence scope | Failure stays local (per-prefix) | LSA flood affects whole area |
| Multipath | Native ECMP | Requires tuning |
| EVPN integration | Same protocol, same sessions | Separate EVPN protocol needed |

### BGP EVPN Route Targets: VNI Membership Control

Route Targets (RTs) are BGP Extended Communities — 8-byte tags attached to routes that control which VTEPs import which VNIs. This is the mechanism that enforces tenant isolation.

```
Convention: RT = AS:VNI

VNI-100 → Route Target: 65000:100
VNI-200 → Route Target: 65000:200

VTEP-A exports:  MAC in VNI-100 tagged with RT 65000:100
VTEP-B imports:  only routes with RT 65000:100 (it hosts VNI-100 workloads)
VTEP-C imports:  only routes with RT 65000:200 (it does not host VNI-100)

Result: VTEP-C never installs forwarding entries for VNI-100 — complete isolation.
```

---

## Part 3: End-to-End Packet Flow

### Scenario: VM on Leaf-1 Sends to VM on Leaf-2 (Same VNI)

```
Setup:
  Both VMs in VNI-100
  Leaf-1 VTEP IP: 10.0.1.11 | Leaf-2 VTEP IP: 10.0.1.12
  Source VM:      MAC aa:aa:aa:aa:aa:aa, IP 192.168.1.10
  Destination VM: MAC bb:bb:bb:bb:bb:bb, IP 192.168.1.20
```

**Step 1 — Leaf-2 advertises its local VM via BGP EVPN Type 2:**

```
BGP update (Leaf-2 → Spine → Leaf-1):
  Route type:  2 (MAC/IP)
  MAC:         bb:bb:bb:bb:bb:bb
  IP:          192.168.1.20
  VNI:         100
  Next-Hop:    10.0.1.12
  RT:          65000:100

Leaf-1 installs in its FDB (Forwarding Database):
  bb:bb:bb:bb:bb:bb → VNI 100 → encap to 10.0.1.12
```

**Step 2 — Source VM sends a packet:**

Source VM sends: `192.168.1.10 → 192.168.1.20` (standard Ethernet frame, no VXLAN yet)

**Step 3 — Leaf-1 VTEP encapsulates and forwards:**

```
Leaf-1 VTEP logic:
  1. Receives frame: dst MAC = bb:bb:bb:bb:bb:bb, VNI 100
  2. FDB lookup: bb:bb:bb:bb:bb:bb in VNI-100 → next-hop 10.0.1.12
  3. Encapsulate:
       Outer IP:  src=10.0.1.11  dst=10.0.1.12
       UDP port:  4789
       VXLAN:     VNI=100
       Inner:     original Ethernet frame (unchanged)
  4. BGP (underlay) determines path to 10.0.1.12:
       ECMP across Spine-1 and Spine-2
  5. Transmit
```

**Step 4 — Leaf-2 VTEP decapsulates:**

```
Leaf-2 receives UDP/4789 packet:
  1. Strips outer headers
  2. Reads VNI=100 → maps to local VNI-100 bridge
  3. Delivers original Ethernet frame to destination VM
```

**No flooding. No ARP crossing the fabric. Fully deterministic.**

---

## Part 4: Advanced Concepts

### Symmetric vs. Asymmetric IRB (Inter-VNI Routing)

When a VM in VNI-100 needs to reach a VM in VNI-200 (a different logical network), the packet must be **routed** — Layer 3 forwarding between the two VNIs. There are two approaches:

**Asymmetric IRB:**

```
Ingress leaf does ALL the work:
  1. Receives frame in VNI-100
  2. Routes to destination IP (in VNI-200 subnet)
  3. Re-encapsulates using VNI-200
  4. Sends directly to egress leaf

Egress leaf:
  1. Decapsulates from VNI-200
  2. Delivers locally

Problem: Ingress leaf must have VNI-200 configured locally
         even if no VNI-200 VMs live on that leaf.
         Does not scale cleanly in large fabrics.
```

**Symmetric IRB (the modern standard):**

```
Uses a dedicated L3 VNI (per VRF — Virtual Routing and Forwarding instance):

Ingress leaf:
  1. Receives frame in VNI-100
  2. Routes to destination IP
  3. Re-encapsulates using L3 VNI (e.g., VNI-9000)
  4. Sends to egress leaf

Egress leaf:
  1. Decapsulates from L3 VNI-9000 (knows this is a routed packet)
  2. Delivers into VNI-200 locally

Each leaf only needs its own L2 VNIs + one L3 VNI per VRF.
Scales cleanly. EVPN Type 5 routes carry the L3 VNI mappings.
```

### Anycast Gateway

In a spine-leaf fabric every leaf can be the default gateway for local VMs. Rather than a dedicated gateway device, each leaf advertises the **same gateway IP and MAC** for a given VNI:

```
VNI-100 gateway: 192.168.1.1  (MAC: 00:00:5e:00:01:01)
Advertised by:   Leaf-1, Leaf-2, Leaf-3  (all leaves with VNI-100 workloads)

VM in VNI-100 sees one gateway regardless of which leaf it sits on.
Traffic exits via the nearest leaf — no hairpin to a central router.
ECMP naturally distributes inter-VNI flows across all leaves.
```

Anycast Gateway requires Symmetric IRB: all leaves must agree on the L3 VNI and use consistent routing tables, which EVPN Type 5 routes ensure.

### Route Reflectors for EVPN at Scale

In a large spine-leaf fabric, not every leaf needs a BGP session to every other leaf. Spine switches act as **BGP Route Reflectors (RRs)** for the EVPN address family:

```
Leaf-1 → Spine-1 (RR): "I have MAC aa:aa in VNI-100"
Spine-1 reflects →  Leaf-2, Leaf-3, Leaf-4 ...

Session count: O(N) instead of O(N²)

For 100 leaves:
  Full mesh: 4,950 sessions
  With 2 spine RRs: 200 sessions
```

See `05_specialized/02_overlay_networking/01_vxlan_geneve_bgp.md` for the full scaling analysis and loop-prevention mechanisms (Cluster ID, Originator ID).

---

## Part 5: Operational Implications

### The Combined Model

The key architectural insight of modern DC networking is the **separation of control plane and data plane**:

| Layer | Protocol | Job |
|-------|----------|-----|
| **Data plane** | VXLAN encapsulation | Carry actual packets between VTEPs |
| **Control plane** | EVPN routes over BGP | Distribute MAC/IP/prefix reachability |
| **Underlay routing** | BGP (eBGP between ASNs) | Route physical IP packets across fabric |

Each layer can evolve independently. VXLAN could be replaced by Geneve (Generic Network Virtualization Encapsulation); the EVPN control plane stays the same. BGP sessions carry both underlay routes and EVPN routes simultaneously.

### Benefits at Scale

- **16M VNIs** vs. 4,096 VLANs — supports massive multitenancy
- **No broadcast storms** — ARP suppression eliminates unknown unicast flooding
- **VM mobility** — VMs keep their MAC/IP; EVPN withdraws the old Type 2 and advertises a new one in seconds
- **Automation-friendly** — BGP is programmable; VNI provisioning is API-driven, not per-switch VLAN config

### Complexity Costs

- BGP expertise required across the operations team
- Debugging requires understanding both overlay (VNI, EVPN routes) and underlay (BGP paths, VTEP reachability) simultaneously
- MTU (Maximum Transmission Unit) tuning is critical: VXLAN adds ~50 bytes; underlay must support jumbo frames (9000-byte MTU) or overlay MTU must be reduced to 1450 bytes
- BGP convergence time affects failover: if a spine fails, BGP reconvergence determines how quickly traffic reroutes (typically 3–9 seconds with default timers, sub-second with BFD — Bidirectional Forwarding Detection)

---

## Summary Table

| Technology | Layer | Problem Solved | Key Limitation |
|------------|-------|----------------|----------------|
| **VXLAN** | Data plane encapsulation | 16M VNIs vs. 4K VLANs; L2 over L3 | Needs a control plane to avoid flooding |
| **EVPN** | Control plane (BGP routes) | MAC/IP/prefix learning without flooding | Requires BGP infrastructure |
| **BGP (underlay)** | Routing | Scalable fabric routing; ECMP | Operational complexity |
| **Route Targets** | Policy | VNI membership and tenant isolation | Must be consistently configured |
| **Symmetric IRB** | Routing architecture | Scalable inter-VNI routing | Requires L3 VNI per VRF |
| **Anycast Gateway** | Gateway placement | Distributed default gateway; ECMP | Requires consistent leaf config |

---

## What You've Learned

✅ Why VXLAN's flood-and-learn data plane does not scale and what problems it creates  
✅ EVPN Type 2 (MAC/IP), Type 3 (BUM membership), and Type 5 (IP prefix) routes  
✅ How BGP Route Targets enforce VNI isolation between tenants  
✅ BGP's dual role: underlay routing (eBGP between leaf ASNs) + EVPN control plane  
✅ End-to-end packet flow across a VXLAN/EVPN spine-leaf fabric  
✅ Symmetric vs. Asymmetric IRB for inter-VNI routing  
✅ Anycast Gateway as the distributed default gateway pattern  

---

## Hands-On Resources

> 💡 **Want more?** For comprehensive resources across all networking and storage topics, see:
> **→ [Complete Networking & Storage Learning Resources](../00_NETWORKING_RESOURCES.md)** 📚

- [RFC 7432 — BGP MPLS-Based Ethernet VPN](https://datatracker.ietf.org/doc/html/rfc7432) — The EVPN specification
- [RFC 7348 — Virtual eXtensible Local Area Network (VXLAN)](https://datatracker.ietf.org/doc/html/rfc7348) — The VXLAN data-plane specification
- [Cumulus Linux EVPN Guide](https://docs.nvidia.com/networking-ethernet-software/cumulus-linux/Network-Virtualization/Ethernet-Virtual-Private-Network-EVPN/) — Practical VXLAN+EVPN configuration with FRR
- [Juniper EVPN/VXLAN Overview](https://www.juniper.net/documentation/us/en/software/junos/evpn-vxlan/topics/concept/evpn-bgp-overview.html) — Vendor implementation reference

---

## Next Steps

**Continue the overlay networking deep-dives:**
→ [VXLAN, Geneve, and BGP Route Reflectors — Full Deep Dive](../../05_specialized/02_overlay_networking/01_vxlan_geneve_bgp.md)

**Understand BGP Communities and scaling strategies:**
→ [BGP Communities vs Route Reflectors](../../05_specialized/02_overlay_networking/02_bgp_communities_rr.md)

**Related topics:**
→ [VXLAN vs VLAN — Fundamental Differences](01_vlan_vs_vxlan.md)  
→ [VXLAN and Geneve Overlay Mechanics](02_overlay_mechanics.md)
