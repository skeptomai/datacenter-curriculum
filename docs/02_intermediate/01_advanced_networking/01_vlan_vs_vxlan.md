---
level: intermediate
estimated_time: 40 min
prerequisites:
  - 01_foundations/02_datacenter_topology/04_ecmp_load_balancing.md
next_recommended:
  - 02_intermediate/01_advanced_networking/02_overlay_mechanics.md
tags: [networking, vlan, vxlan, overlay, layer2]
---

# VLAN vs VXLAN: Fundamental Differences

## The Misconception

**Common belief:** "VXLAN is just VLAN with a bigger ID space (24 bits vs 12 bits)"

**Reality:** VXLAN and VLAN are **fundamentally different technologies** that operate at different layers and solve completely different problems.

---

## Core Architectural Differences

### VLAN (Virtual LAN) - 802.1Q

**What it is:**
A Layer 2 technology that segments a single physical network into multiple logical networks.

**How it works:**
```
Original Ethernet Frame:
┌──────────┬──────────┬───────────┬──────┬─────┐
│ Dst MAC  │ Src MAC  │ EtherType │ Data │ FCS │
└──────────┴──────────┴───────────┴──────┴─────┘
   6 bytes    6 bytes     2 bytes

802.1Q Tagged Frame:
┌──────────┬──────────┬──────────┬───────────┬──────┬─────┐
│ Dst MAC  │ Src MAC  │ 802.1Q   │ EtherType │ Data │ FCS │
│          │          │   Tag    │           │      │     │
└──────────┴──────────┴──────────┴───────────┴──────┴─────┘
   6 bytes    6 bytes    4 bytes     2 bytes

802.1Q Tag (4 bytes):
┌─────────┬─────┬──────────────┬───────────────┐
│  TPID   │ PCP │     DEI      │   VLAN ID     │
│ (0x8100)│(3b) │     (1b)     │   (12 bits)   │
└─────────┴─────┴──────────────┴───────────────┘
  2 bytes                        0-4095
```

**Key characteristics:**
- **Inserts 4-byte tag** into Ethernet frame
- **12-bit VLAN ID** → 4,096 VLANs
- **Operates at Layer 2** only
- **No encapsulation** - modifies existing frame
- **Switch-dependent** - all switches must understand VLANs

---

### VXLAN (Virtual Extensible LAN)

**What it is:**
A Layer 2 **overlay** technology that tunnels Layer 2 frames inside Layer 3 (IP/UDP) packets.

**How it works:**
```
Complete VXLAN Packet:
┌─────────────────────────────────────────────────────────┐
│            Outer Ethernet Frame                         │
├─────────────────────────────────────────────────────────┤
│ Outer Dst MAC │ Outer Src MAC │ Type: 0x0800 (IPv4)    │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│            Outer IP Header                              │
├─────────────────────────────────────────────────────────┤
│ Src: 192.168.1.10 (VTEP1) │ Dst: 192.168.1.20 (VTEP2) │
│ Protocol: 17 (UDP)                                      │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│            Outer UDP Header                             │
├─────────────────────────────────────────────────────────┤
│ Src Port: 49152 │ Dst Port: 4789 (VXLAN)              │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│            VXLAN Header                                 │
├─────────────────────────────────────────────────────────┤
│ Flags │ Reserved │ VNI: 5000 (24 bits) │ Reserved     │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│         ORIGINAL ETHERNET FRAME (unchanged)             │
├─────────────────────────────────────────────────────────┤
│ Inner Dst MAC │ Inner Src MAC │ Type │ IP │ TCP │ Data│
└─────────────────────────────────────────────────────────┘
```

**Key characteristics:**
- **Complete encapsulation** - original frame untouched
- **24-bit VNI** → 16.7 million networks
- **Operates as overlay** - L2 over L3
- **50-byte overhead** (outer headers + VXLAN)
- **Switch-independent** - only needs IP routing

---

## The Critical Difference: Scope

### VLAN Scope

**VLANs work within a Layer 2 domain:**

```
Data Center 1:
┌─────────────────────────────────────────────────┐
│                                                 │
│  Switch1 ──── Switch2 ──── Switch3              │
│    │            │            │                  │
│  Servers     Servers      Servers               │
│                                                 │
│  VLAN 100: All switches configured for VLAN 100│
│  Frames tagged with VLAN 100 everywhere        │
│                                                 │
└─────────────────────────────────────────────────┘

LIMITATION: Cannot extend across routers!

Router
  │
  │ ← VLANs STOP here (Layer 2 doesn't cross Layer 3)
  │
Data Center 2
```

**Why VLANs can't cross routers:**
```
Server in VLAN 100 sends frame:
  [Src MAC: aa:aa | Dst MAC: bb:bb | VLAN: 100 | IP | Data]

Frame arrives at router:
  - Router operates at Layer 3 (IP)
  - Strips Layer 2 header (including VLAN tag)
  - Routes based on IP
  - Creates NEW Layer 2 header for next hop
  - VLAN tag is LOST

Server on other side receives:
  [Src MAC: router MAC | Dst MAC: server MAC | IP | Data]
  No VLAN tag!
```

**Workarounds (all have problems):**
```
1. VLAN Trunking (802.1Q):
   - Still limited to L2 domain
   - Can't truly span data centers
   
2. Layer 2 extension over Layer 3 (OTV, VPLS):
   - Complex, expensive
   - Vendor-specific
   - Doesn't scale
   
3. Just don't span data centers:
   - Most common solution before overlays
   - Limits flexibility
```

---

### VXLAN Scope

**VXLAN works OVER Layer 3 networks:**

```
Data Center 1           WAN/Internet         Data Center 2
┌──────────────┐                            ┌──────────────┐
│  Pod A       │                            │  Pod B       │
│  MAC: aa:aa  │                            │  MAC: bb:bb  │
│  VNI: 5000   │                            │  VNI: 5000   │
└──────┬───────┘                            └──────┬───────┘
       │                                           │
   ┌───▼────┐         Routers/WAN            ┌────▼────┐
   │ VTEP1  │◄────────────────────────────────►│ VTEP2   │
   │192.168.│         IP Network              │10.20.30.│
   │  1.10  │                                 │   40    │
   └────────┘                                 └─────────┘

Pod A sends to Pod B:
1. Original frame: [aa:aa → bb:bb | IP: 10.1.1.10 → 10.1.1.20]

2. VTEP1 encapsulates in UDP/IP:
   Outer IP: 192.168.1.10 → 10.20.30.40
   VXLAN: VNI 5000
   Inner: [aa:aa → bb:bb | IP: 10.1.1.10 → 10.1.1.20]

3. Routers forward based on OUTER IP (they see UDP packet)
   - Multiple hops OK
   - Across WAN OK
   - Different subnets OK
   - Firewalls OK (just UDP/4789)

4. VTEP2 receives, decapsulates, delivers original frame

Pod B receives EXACT original frame!
```

**Key insight:** Routers only see the outer IP packet. They have no idea there's a VLAN/VNI inside. They just route a UDP packet like any other traffic.

---

## Comparison Table

```
┌──────────────────────┬──────────────────┬──────────────────────┐
│ Aspect               │ VLAN             │ VXLAN                │
├──────────────────────┼──────────────────┼──────────────────────┤
│ Layer                │ Layer 2 only     │ L2 over L3 (overlay) │
│                      │                  │                      │
│ ID Space             │ 12 bits (4,096)  │ 24 bits (16.7M)      │
│                      │                  │                      │
│ Frame Modification   │ Inserts 4-byte   │ Full encapsulation   │
│                      │ tag in frame     │ (50 bytes overhead)  │
│                      │                  │                      │
│ Scope                │ Single L2 domain │ Anywhere with IP     │
│                      │ (one datacenter) │ (global)             │
│                      │                  │                      │
│ Can Cross Routers?   │ NO               │ YES                  │
│                      │                  │                      │
│ Infrastructure Req.  │ VLAN-aware       │ Just IP routing      │
│                      │ switches         │ (dumb switches OK)   │
│                      │                  │                      │
│ Configuration        │ Every switch     │ Only VTEPs (hosts)   │
│                      │ must be config'd │                      │
│                      │                  │                      │
│ Multitenancy         │ Limited (4,096)  │ Excellent (16.7M)    │
│                      │                  │                      │
│ Multi-datacenter     │ Very difficult   │ Easy                 │
│                      │                  │                      │
│ Cloud-friendly       │ No               │ Yes                  │
│                      │                  │                      │
│ Standards            │ IEEE 802.1Q      │ RFC 7348             │
│                      │ (1998)           │ (2014)               │
│                      │                  │                      │
│ Complexity           │ Simple           │ More complex         │
│                      │                  │                      │
│ Performance Overhead │ ~0% (just tag)   │ 5-10% (encap/decap)  │
│                      │                  │                      │
│ MTU Impact           │ +4 bytes         │ -50 bytes            │
│                      │ (1504 typical)   │ (1450 typical)       │
└──────────────────────┴──────────────────┴──────────────────────┘
```

---

## Real-World Scenarios

### Scenario 1: Single Data Center, Simple Network

**Requirements:**
- 50 VLANs for different departments
- All servers in one building
- Simple network topology

**Best choice: VLAN**

**Why:**
```
✓ Simple - just configure VLANs on switches
✓ No performance overhead
✓ Well understood by network teams
✓ No need for overlay complexity
✓ 50 VLANs << 4,096 limit

Network:
  Switch (configured with VLANs 10, 20, 30...)
    ├── VLAN 10: Engineering
    ├── VLAN 20: Sales
    ├── VLAN 30: Marketing
    └── VLAN 40: Finance
```

**VXLAN would be overkill here.**

---

### Scenario 2: Multi-Datacenter Cloud

**Requirements:**
- 10,000 tenants
- 3 data centers across the country
- Pods need to move between data centers
- Underlying network is routed (no L2 between DCs)

**Best choice: VXLAN**

**Why:**
```
✓ Unlimited tenant isolation (16.7M VNIs)
✓ Works over routed WAN (L3)
✓ Pods can migrate between DCs (MAC mobility)
✓ No switch configuration required
✓ Scales to cloud requirements

Network:
  DC1 ←───── Routed WAN ─────→ DC2 ←───── Routed WAN ─────→ DC3
  VTEP1                        VTEP2                        VTEP3
  (Hosts)                      (Hosts)                      (Hosts)
  
  Tenant 1: VNI 5000 (spans all 3 DCs)
  Tenant 2: VNI 5001 (spans all 3 DCs)
  ...
  Tenant 10,000: VNI 15000
```

**VLAN cannot do this.**

---

### Scenario 3: Kubernetes Cluster

**Requirements:**
- 500 nodes across 5 racks
- Pods need to communicate regardless of node
- Network is routed (L3 ToR switches)
- No VLAN management overhead

**Best choice: VXLAN (or VXLAN alternative)**

**Why:**
```
✓ Works over routed infrastructure
✓ No switch configuration per pod network
✓ Dynamic - pods come and go
✓ Network team doesn't need to manage VLANs
✓ Single VNI for cluster (or per namespace)

Flannel VXLAN:
  - VNI 1 for entire cluster
  - Pods get IPs from node CIDR (e.g., 10.244.1.0/24)
  - VXLAN tunnels between nodes
  - Network team just provides IP connectivity
```

**With VLANs:**
```
✗ Would need VLANs configured on all switches
✗ Network team involved in every cluster change
✗ Limited to single L2 domain (can't span racks with L3 ToR)
✗ Doesn't scale as cluster grows
```

---

## What VXLAN Really Solves

### Problem 1: The 4096 VLAN Limit

```
Cloud provider with 10,000 tenants:
  - Each tenant needs isolated network
  - VLANs: Only 4,096 possible
  - VXLAN: 16.7 million possible ✓
```

**But this is the LEAST important problem VXLAN solves!**

---

### Problem 2: Layer 2 Extension Over Layer 3 (The BIG One)

```
Traditional network (VLANs):
┌─────────────────────────────────────────┐
│        Layer 2 Domain (Campus)          │
│                                         │
│  Switch ─── Switch ─── Switch           │
│    │          │          │              │
│  Servers   Servers   Servers            │
│                                         │
│  VLAN works here! ✓                     │
└─────────────────────────────────────────┘
       │
     Router  ← VLANs STOP here
       │
┌──────▼──────────────────────────────────┐
│    Layer 2 Domain (Remote Site)         │
│                                         │
│  VLAN doesn't extend here ✗             │
└─────────────────────────────────────────┘

With VXLAN:
┌─────────────────┐                 ┌─────────────────┐
│   Site 1        │                 │   Site 2        │
│   VTEP1         │                 │   VTEP2         │
│   VNI: 5000     │                 │   VNI: 5000     │
└────────┬────────┘                 └────────┬────────┘
         │                                   │
         └──────── IP Network (WAN) ─────────┘
                  (Routed, L3)
         
Same VNI (5000) spans both sites! ✓
Hosts think they're on same Ethernet segment
```

**This is the killer feature:** Create virtual Layer 2 networks that span Layer 3 infrastructure.

---

### Problem 3: Network Infrastructure Independence

```
VLANs require switch configuration:

To add VLAN 500:
  1. Log into Switch 1, configure VLAN 500
  2. Log into Switch 2, configure VLAN 500
  3. Log into Switch 3, configure VLAN 500
  ...
  20. Test connectivity
  
  Manual, slow, error-prone


VXLAN requires NO switch configuration:

To add VNI 500:
  1. Configure VTEPs on hosts (automated)
  2. Done
  
  Switches just route IP packets (they already do this)
  No switch reconfiguration needed
  Automation-friendly
```

---

### Problem 4: Cloud Multi-Tenancy

```
AWS/Azure/GCP scenario:

Customer A: Wants network 10.0.0.0/16
Customer B: Also wants network 10.0.0.0/16 (same IPs!)
Customer C: Also wants network 10.0.0.0/16

With VLANs:
  - IP overlap is a nightmare
  - Limited to 4,096 customers
  - Complex routing/NAT required

With VXLAN:
  Customer A: VNI 1000, network 10.0.0.0/16
  Customer B: VNI 2000, network 10.0.0.0/16  
  Customer C: VNI 3000, network 10.0.0.0/16
  
  ✓ Complete isolation (different VNIs)
  ✓ Same IP space OK (different overlays)
  ✓ Scales to millions of customers
  ✓ No routing complexity
```

---

### Problem 5: VM/Pod Mobility

```
Scenario: VM needs to migrate from Host1 to Host2

With VLANs (same subnet required):
  Host1 and Host2 must be on same VLAN
  = Same Layer 2 domain
  = Same subnet
  = Limited to single datacenter/rack
  
  VM IP: 10.1.1.50
  Host1 in subnet 10.1.1.0/24 ✓
  Host2 in subnet 10.1.1.0/24 ✓
  Migration works ✓
  
  BUT:
  Host3 in different datacenter (10.2.1.0/24) ✗
  Cannot migrate there ✗

With VXLAN:
  Hosts can be anywhere with IP connectivity
  
  VM IP: 10.1.1.50, VNI: 5000
  Host1 underlay IP: 192.168.1.10 ✓
  Host2 underlay IP: 192.168.2.20 (different subnet) ✓
  Host3 underlay IP: 10.50.100.30 (different datacenter) ✓
  
  VXLAN makes them all look like same Ethernet segment
  VM can migrate anywhere ✓
```

---

## Technical Deep Dive: Why VXLAN Can Cross Routers

### What Routers See

**With VLAN:**
```
Frame arrives at router:
  [Ethernet: dst=router MAC | VLAN=100 | IP | Data]

Router processing:
  1. Strip Ethernet header (including VLAN tag)
  2. Look at IP header
  3. Route based on destination IP
  4. Create NEW Ethernet header for next hop
  5. Forward
  
  [Ethernet: dst=next_hop MAC | IP | Data]
                                 ↑
                        VLAN tag is GONE
```

**With VXLAN:**
```
Packet arrives at router:
  [Outer Eth | Outer IP: 192.168.1.10→192.168.1.20 | UDP:4789 | VXLAN | Inner Frame]

Router processing:
  1. Strip outer Ethernet header
  2. Look at outer IP header
  3. Route based on destination IP (192.168.1.20)
  4. Create NEW outer Ethernet header for next hop
  5. Forward entire payload (including VXLAN + inner frame)
  
  [New Outer Eth | Outer IP: 192.168.1.10→192.168.1.20 | UDP:4789 | VXLAN | Inner Frame]
                                                                              ↑
                                                               Original frame PRESERVED
```

**The router has no idea there's a Layer 2 network inside!**
It just sees a UDP packet on port 4789 and routes it like any other UDP traffic.

---

## When VLANs Are Still Better

### Use VLANs when:

**1. Simple, single-site network**
```
✓ All servers in one building
✓ < 4,096 segments needed
✓ Network team comfortable with VLANs
✓ No need for multi-datacenter
✓ No VM/container migration requirements
✓ Performance critical (no encap overhead)
```

**2. Hardware requirements**
```
Some network hardware (load balancers, firewalls) 
works better with VLANs than with overlays
```

**3. Regulatory/compliance**
```
Some environments require traffic to stay on specific 
physical infrastructure (no overlay tunneling allowed)
```

**4. Troubleshooting simplicity**
```
VLANs are easier to troubleshoot:
  - tcpdump shows actual traffic
  - Switch port mirroring works normally
  - No encapsulation to decode
```

---

## When VXLAN Is Essential

### Use VXLAN when:

**1. Cloud/multi-tenant environments**
```
✓ > 4,096 isolated networks needed
✓ Tenants want same IP addressing
✓ Automated provisioning required
✓ Switch configuration overhead too high
```

**2. Multi-datacenter**
```
✓ Layer 2 needs to span routed network
✓ VMs/containers migrate between sites
✓ WAN between datacenters
✓ Different IP subnets at each site
```

**3. Overlay networking**
```
✓ Kubernetes/container platforms
✓ Don't want to manage switch VLANs
✓ Dynamic workload placement
✓ Software-defined networking (SDN)
```

**4. Infrastructure as code**
```
✓ Network provisioning via API
✓ No manual switch configuration
✓ GitOps/automation-friendly
✓ Self-service for developers
```

---

## The Bottom Line

**VLAN:**
- Layer 2 segmentation technology
- Works within a broadcast domain
- Stops at routers
- Simple, low overhead
- Great for traditional networks

**VXLAN:**
- Layer 2 **tunneling** technology
- Creates virtual Layer 2 over Layer 3
- Crosses routers freely
- More complex, some overhead
- Essential for cloud/modern infrastructure

**Analogy:**
```
VLAN is like putting colored tape on cables in your office
  - Each color = different network
  - Simple, visible, works in one location
  - Can't extend tape to remote office

VXLAN is like creating encrypted VPN tunnels
  - Carries your private network over public Internet
  - Works anywhere there's IP connectivity
  - More complex but way more powerful
```

**The real answer:**
VXLAN isn't "VLAN on steroids" - it's a completely different approach to networking that solves problems VLANs fundamentally cannot solve, most importantly: **creating Layer 2 networks that span Layer 3 infrastructure**.

The bigger ID space (24 bits vs 12 bits) is just a nice bonus.

---

## Hands-On Resources

> Want more? This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all networking and storage topics, see:
> **→ [Complete Networking & Storage Learning Resources](../00_NETWORKING_RESOURCES.md)**

**VXLAN Specification:**
- [RFC 7348 - Virtual eXtensible Local Area Network (VXLAN)](https://datatracker.ietf.org/doc/html/rfc7348) - Official IETF VXLAN specification
- [VXLAN Overview (IETF)](https://www.rfc-editor.org/rfc/rfc7348.html) - Detailed protocol documentation

**Linux VXLAN Configuration:**
- [Linux VXLAN Tutorial](https://vincent.bernat.ch/en/blog/2017-vxlan-linux) - Comprehensive guide to VXLAN on Linux
- [iproute2 VXLAN Examples](https://developers.redhat.com/blog/2018/10/22/introduction-to-linux-interfaces-for-virtual-networking#vxlan) - Practical configuration examples
