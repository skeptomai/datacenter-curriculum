# Modern Datacenter Network Architecture

## Part 1: Link Speeds in Modern Datacenters

### Server Connectivity

```
Evolution of Server NICs:
┌──────────┬──────────────┬────────────────────┐
│ Year     │ Speed        │ Technology         │
├──────────┼──────────────┼────────────────────┤
│ 2010     │ 1 Gbps       │ Copper (1000BASE-T)│
│ 2012     │ 10 Gbps      │ SFP+ (fiber/copper)│
│ 2016     │ 25 Gbps      │ SFP28              │
│ 2018     │ 40 Gbps      │ QSFP+ (legacy)     │
│ 2020     │ 50 Gbps      │ SFP56 (less common)│
│ 2022     │ 100 Gbps     │ QSFP28 / QSFP56   │
│ 2024+    │ 200/400 Gbps │ QSFP-DD, OSFP     │
└──────────┴──────────────┴────────────────────┘

Current Standard (2024-2026):
─────────────────────────────
General compute servers: 25 Gbps (2x redundant)
Storage servers:         100 Gbps (2x redundant)
GPU/AI servers:          200-400 Gbps
```

---

### Typical Modern Server

```
Hyperscale Datacenter Server (2024):
┌───────────────────────────────────────────┐
│           Compute Server                  │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │ Dual-port NIC                      │  │
│  │ - Port 1: 25 Gbps → Leaf Switch A  │  │
│  │ - Port 2: 25 Gbps → Leaf Switch B  │  │
│  │ Total: 50 Gbps bandwidth           │  │
│  │ Redundant for HA                   │  │
│  └────────────────────────────────────┘  │
└───────────────────────────────────────────┘

Storage Server (2024):
┌───────────────────────────────────────────┐
│         Storage/NVMe Server               │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │ Dual-port NIC                      │  │
│  │ - Port 1: 100 Gbps → Leaf Switch A │  │
│  │ - Port 2: 100 Gbps → Leaf Switch B │  │
│  │ Total: 200 Gbps bandwidth          │  │
│  │ RDMA/RoCE capable                  │  │
│  └────────────────────────────────────┘  │
│                                           │
│  10x NVMe SSDs @ 7 GB/s each = 70 GB/s   │
│  Network: 200 Gbps = 25 GB/s             │
│  Network is bottleneck! (Need 400G soon) │
└───────────────────────────────────────────┘

GPU/AI Server (2024):
┌───────────────────────────────────────────┐
│            AI Training Server             │
│                                           │
│  8x NVIDIA H100 GPUs                      │
│  - NVLink between GPUs: 900 GB/s          │
│  - Need fast network for distributed      │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │ High-speed NIC                     │  │
│  │ - 8x 200 Gbps ports (1.6 Tbps!)    │  │
│  │ - Or 4x 400 Gbps ports             │  │
│  │ - InfiniBand or RoCE               │  │
│  └────────────────────────────────────┘  │
└───────────────────────────────────────────┘
```

---

### Switch Uplink Speeds

```
Leaf Switch (Top-of-Rack):
──────────────────────────
Downlinks (to servers): 32-64 ports × 25/100 Gbps
Uplinks (to spines):    4-16 ports × 100/400 Gbps

Example modern leaf:
  48 × 25G ports (servers) = 1.2 Tbps downlink
  8 × 100G ports (spines)  = 800 Gbps uplink
  Oversubscription: 1.5:1

Spine Switch:
─────────────
All ports are uplinks (to leaves) or core
Typical: 32-64 × 100/400 Gbps ports
No server connections

Example spine:
  32 × 400G ports = 12.8 Tbps capacity
  Connects to 32 leaf switches
```

---

## Part 2: The Old Model - Three-Tier Architecture

### Traditional Hierarchy (2000-2015)

```
Three-Tier Network:
═══════════════════

                    ┌──────────────┐
                    │     Core     │  ← Core routers
                    │   Routers    │    (2-4 devices)
                    │              │    Very expensive
                    └───┬─────┬────┘
                        │     │
          ┌─────────────┘     └─────────────┐
          │                                  │
    ┌─────▼──────┐                    ┌─────▼──────┐
    │Aggregation │                    │Aggregation │  ← Agg switches
    │ Switch 1   │                    │ Switch 2   │    (10-20 devices)
    │(End-of-Row)│                    │(End-of-Row)│    L3 routing
    └┬──┬──┬──┬──┘                    └┬──┬──┬──┬──┘
     │  │  │  │                        │  │  │  │
     │  │  │  └─────┐    ┌─────────────┘  │  │  │
     │  │  │        │    │                │  │  │
  ┌──▼──▼──▼──┐  ┌─▼────▼──┐  ┌──────▼───▼──▼──▼──┐
  │  ToR 1    │  │  ToR 2  │  │     ToR 3          │  ← Access switches
  │ (Leaf)    │  │ (Leaf)  │  │    (Leaf)          │    (100s of devices)
  └┬─┬─┬─┬─┬─┬┘  └┬┬┬┬┬┬┬┬┘  └┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬─┘    L2 switching
   │ │ │ │ │ │    ││││││││    ││││││││││││││││││││
  [Servers  ]    [Servers]    [     Servers       ]
   (20-40)        (20-40)            (20-40)

Links:
  Server → ToR:      1-10 Gbps
  ToR → Aggregation: 10-40 Gbps (often 2-4 links)
  Agg → Core:        40-100 Gbps
```

---

### Problems with Three-Tier

**1. Oversubscription:**

```
Typical oversubscription:

ToR Switch:
  48 × 10G server ports   = 480 Gbps downlink
  4 × 10G uplinks to Agg  = 40 Gbps uplink
  
  Oversubscription: 480:40 = 12:1 (!!)
  
If all servers transmit simultaneously:
  Available per server: 40 Gbps / 48 = 833 Mbps
  Only 8% of server bandwidth!

Aggregation:
  20 ToRs × 40G uplinks   = 800 Gbps downlink
  4 × 40G to Core         = 160 Gbps uplink
  
  Oversubscription: 800:160 = 5:1
  
Total oversubscription: 12 × 5 = 60:1 (terrible!)
```

**2. Unpredictable Paths:**

```
Server A (Rack 1) → Server B (Rack 10):

Path depends on which aggregation switch:
  Via Agg 1: 4 hops (ToR1 → Agg1 → ToR10)
  Via Agg 2: 4 hops (ToR1 → Agg2 → ToR10)
  
Different paths, different latencies!
Hash-based selection = unpredictable
```

**3. Bottlenecks:**

```
"Hot spot" problem:

Rack 1 servers all talking to Rack 10:
  All traffic through same uplinks
  ToR1 → Agg bottleneck (40 Gbps)
  Even if Core has capacity!
  
East-West traffic (server-to-server) starved
```

**4. Poor for RDMA:**

```
RDMA needs:
  ✗ Lossless (PFC across multiple hops = pause storms)
  ✗ Low latency (3-tier adds hops)
  ✗ Predictable (hash-based = variable paths)
  ✗ High bandwidth (oversubscription kills it)
  
Three-tier terrible for RDMA!
```

---

## Part 3: Modern Model - Spine-Leaf (Clos) Architecture

### The Spine-Leaf Topology

```
Spine-Leaf (Two-Tier):
══════════════════════

     ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
     │Spine 1 │ │Spine 2 │ │Spine 3 │ │Spine 4 │  ← Spine layer
     │        │ │        │ │        │ │        │    (4-16 switches)
     └┬─┬─┬─┬─┘ └┬─┬─┬─┬─┘ └┬─┬─┬─┬─┘ └┬─┬─┬─┬─┘    All 100-400G
      │ │ │ │    │ │ │ │    │ │ │ │    │ │ │ │
      │ │ │ └────┼─┼─┼──────┼─┼─┼──────┼─┼─┼────┐
      │ │ └──────┼─┼─┼──────┼─┼─┼──────┼─┼─┼──┐ │
      │ └────────┼─┼─┼──────┼─┼─┼──────┼─┼─┼┐ │ │
      └──────────┼─┼─┼──────┼─┼─┼──────┼─┼┐│ │ │
    ┌────────────┼─┼─┼──────┼─┼─┼──────┼┐││ │ │
    │ ┌──────────┼─┼─┼──────┼─┼─┼──────┼┼┼│ │ │
    │ │ ┌────────┼─┼─┼──────┼─┼─┼──────┼┼┼┼ │ │
    │ │ │ ┌──────┼─┼─┼──────┼─┼─┼──────┼┼┼┼ │ │
    ▼ ▼ ▼ ▼      ▼ ▼ ▼      ▼ ▼ ▼      ▼▼▼▼ ▼ ▼
  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
  │ Leaf 1 │  │ Leaf 2 │  │ Leaf 3 │  │ Leaf 4 │  ← Leaf layer
  │  (ToR) │  │  (ToR) │  │  (ToR) │  │  (ToR) │    (100s of switches)
  └┬┬┬┬┬┬┬┬┘  └┬┬┬┬┬┬┬┬┘  └┬┬┬┬┬┬┬┬┘  └┬┬┬┬┬┬┬┬┘    25-100G down
   ││││││││    ││││││││    ││││││││    ││││││││     100-400G up
  [Servers]   [Servers]   [Servers]   [Servers]

Key properties:
  - Every leaf connects to EVERY spine
  - No leaf-to-leaf connections
  - All paths are equal length (2 hops)
  - Non-blocking (if designed right)
```

---

### Concrete Example

```
Example: 1024-server datacenter

Spine Layer:
────────────
4 spine switches
Each spine: 32 × 100G ports
  → Can connect to 32 leaf switches
Total spine capacity: 4 × 32 × 100G = 12.8 Tbps

Leaf Layer:
───────────
32 leaf switches
Each leaf:
  - 32 × 25G server ports (downlink)
  - 4 × 100G spine ports (uplink)
  
  Downlink capacity: 32 × 25G = 800 Gbps
  Uplink capacity:   4 × 100G = 400 Gbps
  Oversubscription: 800:400 = 2:1

Servers:
────────
32 servers per leaf
32 leafs × 32 servers = 1024 servers
Each server: 25 Gbps NIC

Bandwidth calculation:
──────────────────────
Server A (Leaf 1) → Server B (Leaf 2):

Available paths: 4 (via each spine)
Path capacity: 100 Gbps (spine link)
  
ECMP (Equal Cost Multi-Path) load balances:
  Traffic spread across 4 spines
  Effective bandwidth: 400 Gbps / 32 servers = 12.5 Gbps per flow
  
But server limited to 25 Gbps anyway
So: 12.5 Gbps effective (50% of server capacity)

For 2:1 oversubscription, this is expected!
```

---

## Part 4: Oversubscription in Modern Networks

### Typical Ratios

```
┌─────────────────────┬──────────────┬────────────────┐
│ Network Tier        │ Historic     │ Modern         │
│                     │ (3-tier)     │ (Spine-Leaf)   │
├─────────────────────┼──────────────┼────────────────┤
│ General Compute     │ 20:1 - 40:1  │ 2:1 - 3:1      │
│                     │              │                │
│ Storage/RDMA        │ 10:1 - 20:1  │ 1:1 - 1.5:1    │
│                     │              │ (non-blocking!)│
│                     │              │                │
│ AI/HPC              │ Not feasible │ 1:1            │
│                     │              │ (full bisection│
│                     │              │  bandwidth)    │
└─────────────────────┴──────────────┴────────────────┘
```

---

### Oversubscription Explained

**2:1 Oversubscription:**

```
Leaf switch example:
  32 servers × 25G = 800 Gbps aggregate
  4 uplinks × 100G = 400 Gbps to spine
  
Ratio: 800:400 = 2:1

What this means:
  If all 32 servers transmit to other racks:
    Available: 400 Gbps / 32 = 12.5 Gbps per server
    
  But if only half transmit off-rack:
    Available: 400 Gbps / 16 = 25 Gbps per server
    Full speed!

Why acceptable?
  Not all servers talk off-rack simultaneously
  Locality: Many flows stay within rack
  Bursty traffic: Average << peak
```

---

**1:1 Non-Blocking (RDMA/Storage):**

```
Leaf switch example:
  32 servers × 100G = 3.2 Tbps aggregate
  32 uplinks × 100G = 3.2 Tbps to spine
  
Ratio: 3.2T:3.2T = 1:1

What this means:
  ALL servers can transmit at full speed
  To ANY destination
  Simultaneously
  No congestion!

Cost:
  Very expensive (many spine ports)
  Required for RDMA (lossless needs no congestion)
```

---

## Part 5: Why Spine-Leaf Enables RDMA

### Equal Cost Multi-Path (ECMP)

```
Server A (Leaf 1) → Server B (Leaf 10):

Four possible paths (via each spine):
  Path 1: Leaf1 → Spine1 → Leaf10
  Path 2: Leaf1 → Spine2 → Leaf10
  Path 3: Leaf1 → Spine3 → Leaf10
  Path 4: Leaf1 → Spine4 → Leaf10

All paths:
  ✓ Same length (2 hops)
  ✓ Same latency (~5 μs)
  ✓ Same bandwidth (100G)
  
Load balancing:
  Hash on 5-tuple (src IP, dst IP, src port, dst port, protocol)
  Deterministic: Same flow always uses same path
  Different flows spread across paths

Result:
  Predictable latency (critical for RDMA!)
  High aggregate bandwidth
  No reordering within flow
```

---

### Lossless Configuration

```
For RDMA (RoCE), configure PFC on all links:

Leaf switch config:
  All downlink ports (servers): PFC priority 3
  All uplink ports (spines):    PFC priority 3
  
Spine switch config:
  All ports (to leaves):        PFC priority 3

Effect:
  If Leaf10's queue fills (receiving too much):
    → Sends PFC PAUSE to upstream (spines)
    → Spines pause traffic to Leaf10
    → Spines queue fills
    → Sends PFC to source leaves
    → Source pauses RDMA transmission
    
  Backpressure propagates hop-by-hop
  No packet drops!

Only works because:
  ✓ Short paths (2 hops max)
  ✓ Predictable topology
  ✓ Low oversubscription
  ✓ Dedicated priority class
```

---

### Consistent Latency

```
Latency distribution (2-hop spine-leaf):

P50 (median):        5 μs    ← Most traffic
P99 (99th percentile): 6 μs  ← Some queuing
P99.9:               8 μs    ← Rare congestion

Compare to 3-tier:
  P50:   10 μs   (more hops)
  P99:   50 μs   (variable paths)
  P99.9: 500 μs  (congestion in aggregation)

RDMA loves spine-leaf!
Predictable, low latency
```

---

## Part 6: Traffic Patterns

### North-South vs East-West

```
North-South Traffic:
────────────────────
Client/Internet ←→ Datacenter

Traditional (2000s):
  Most traffic: North-South
  Users accessing web servers
  Servers mostly stateless

┌──────────────────────────────┐
│       Internet               │
└──────────┬───────────────────┘
           │ North
           ↓
      ┌────────┐
      │  Core  │
      └────┬───┘
           │
    ┌──────▼──────┐
    │ Aggregation │
    └──────┬──────┘
           │
      ┌────▼───┐
      │  ToR   │
      └────┬───┘
           │
      [Servers]

East-West Traffic:
──────────────────
Server ←→ Server (within datacenter)

Modern (2020s):
  Most traffic: East-West
  Distributed apps, microservices
  Storage replication, databases

     ┌────────┐
     │ Spine  │
     └┬──────┬┘
      │      │
  ┌───▼──┐┌──▼───┐
  │Leaf 1││Leaf 2│
  └──┬───┘└───┬──┘
     │        │
  [Server A][Server B]
     └────→───┘
    East-West flow
```

---

### Modern Traffic Patterns (2024)

```
Typical datacenter traffic breakdown:

┌────────────────────┬──────────────────────┐
│ Traffic Type       │ % of Total Bandwidth │
├────────────────────┼──────────────────────┤
│ East-West:         │ 75-80%               │
│  - Storage repl    │   30%                │
│  - DB queries      │   15%                │
│  - Cache sync      │   10%                │
│  - Microservices   │   20%                │
│                    │                      │
│ North-South:       │ 20-25%               │
│  - Client requests │   15%                │
│  - CDN egress      │   5%                 │
│  - Backup          │   5%                 │
└────────────────────┴──────────────────────┘

Why East-West dominates:
  - Data replication (3x copies)
  - Distributed databases (queries across nodes)
  - ML training (parameter sync)
  - Storage disaggregation (RDMA to NVMe-oF)

Spine-Leaf optimized for East-West!
```

---

## Part 7: Scaling Spine-Leaf

### Adding Capacity

**Horizontal scaling:**

```
Need more servers? Add leaf switches!

Original:
  4 spines × 32 ports = 128 possible leafs
  32 leafs deployed = 1024 servers
  
Expansion:
  Add 8 more leafs
  Connect each new leaf to all 4 spines
  
  Now: 40 leafs = 1280 servers
  
Still 2 hops for any-to-any!
No topology change!
```

**Vertical scaling:**

```
Need more bandwidth? Upgrade spine switches!

Original:
  4 spines × 32 ports × 100G = 12.8 Tbps
  
Upgrade:
  4 spines × 64 ports × 400G = 102 Tbps
  
Can support:
  102T / 800G per leaf = 127 leafs
  127 leafs × 32 servers = 4064 servers
```

---

### Multi-Tier Spine-Leaf (Super Spine)

**For very large datacenters:**

```
Three-tier spine-leaf (still Clos):

        ┌──────────┐┌──────────┐┌──────────┐
        │Super     ││Super     ││Super     │  ← Super Spine
        │Spine 1   ││Spine 2   ││Spine 3   │    (Pod interconnect)
        └┬─┬─┬─┬─┬─┘└┬─┬─┬─┬─┬─┘└┬─┬─┬─┬─┬─┘
         │ │ │ │ │   │ │ │ │ │   │ │ │ │ │
    ┌────┘ │ │ │ └───┼─┼─┼─┼─────┼─┼─┼─┼──────┐
    │  ┌───┘ │ └─────┼─┼─┼─┼─────┼─┼─┼─┼────┐ │
    │  │  ┌──┘       │ │ │ │     │ │ │ │  ┐ │ │
    ▼  ▼  ▼          ▼ ▼ ▼ ▼     ▼ ▼ ▼ ▼  ▼ ▼ ▼
   ┌──────┐         ┌──────┐   ┌──────┐ ┌──────┐
   │Spine │         │Spine │   │Spine │ │Spine │  ← Pod Spines
   │Pod 1 │         │Pod 1 │   │Pod 2 │ │Pod 3 │
   └┬─┬─┬─┘         └┬─┬─┬─┘   └┬─┬─┬─┘ └┬─┬─┬─┘
    │ │ │            │ │ │      │ │ │    │ │ │
  ┌─▼─▼─▼──┐       ┌▼─▼─▼┐    [Leafs]  [Leafs]
  │ Leafs  │       │Leafs│
  └────────┘       └─────┘
      │               │
  [Servers]       [Servers]

Pods:
  - Self-contained spine-leaf
  - 1024-4096 servers per pod
  - Full bandwidth within pod

Super Spine:
  - Connects pods together
  - Slightly more oversubscription (3:1 typical)
  - Inter-pod traffic less critical

Result: 10,000-100,000 servers in single datacenter
```

---

## Part 8: Real-World Examples

### Example 1: Cloud Provider (AWS/Azure/GCP scale)

```
Typical region (100,000 servers):

Pod Design (4096 servers):
───────────────────────────
16 spine switches (400G ports)
128 leaf switches (25G down, 400G up)
32 servers per leaf × 128 leafs = 4096 servers

Per Pod:
  Downlink: 128 leafs × 32 × 25G = 102 Tbps
  Uplink:   128 leafs × 16 × 400G = 819 Tbps
  Oversubscription: 1.25:1 (almost non-blocking!)

24 pods × 4096 servers = 98,304 servers

Super Spine: 32 switches (400G)
  Connects all 24 pods
  Inter-pod oversubscription: 3:1

Total bandwidth:
  Within pod: ~800 Tbps
  Cross-pod:  ~2 Pbps (2000 Tbps)
```

---

### Example 2: Storage Cluster (RDMA)

```
1000-server Ceph cluster:

Requirements:
  - Lossless (RDMA/RoCE)
  - 1:1 oversubscription
  - 100 Gbps per server

Design:
───────
8 spine switches (400G)
32 leaf switches (100G down, 400G up)
32 servers per leaf

Each leaf:
  32 servers × 100G = 3.2 Tbps down
  8 spines × 400G   = 3.2 Tbps up
  Ratio: 1:1 (non-blocking!)

Configuration:
  - PFC priority 3 enabled all ports
  - ECN/DCQCN for congestion control
  - Jumbo frames (9000 byte MTU)

Performance:
  Any server → any server: 100 Gbps
  Aggregate: 3.2 Tbps per rack
  Total cluster: 100 Tbps
```

---

### Example 3: AI Training Cluster

```
256 GPU servers (2048 GPUs total):

Each server: 8× H100 GPUs
  GPU-GPU (NVLink): 900 GB/s intra-server
  Network needed: 400 Gbps per server

Design:
───────
16 spine switches (51.2T ports)
  Each: 128 × 400G ports
  
8 leaf switches per rack
  32 servers × 400G down = 12.8 Tbps
  16 uplinks × 400G = 6.4 Tbps up
  Oversubscription: 2:1

But uses InfiniBand (not Ethernet):
  - Native lossless
  - Credit-based flow control
  - Lower latency than RoCE

Bandwidth:
  Per server: 400 Gbps (3200 Gbps with 8-way)
  Total cluster: 102 Tbps
  Required for model parallelism!
```

---

## Part 9: Comparison Summary

```
┌──────────────────┬─────────────────┬──────────────────┐
│ Aspect           │ 3-Tier (Old)    │ Spine-Leaf (New) │
├──────────────────┼─────────────────┼──────────────────┤
│ Hops             │ 3-5             │ 2 (always)       │
│                  │                 │                  │
│ Latency          │ 10-50 μs        │ 2-5 μs           │
│                  │ (variable)      │ (consistent)     │
│                  │                 │                  │
│ Oversubscription │ 20:1 - 60:1     │ 1:1 - 3:1        │
│                  │                 │                  │
│ Bandwidth        │ 1-10 Gbps       │ 25-400 Gbps      │
│ per server       │                 │                  │
│                  │                 │                  │
│ Path count       │ 2-4             │ 4-16+ (ECMP)     │
│                  │ (limited)       │                  │
│                  │                 │                  │
│ RDMA support     │ Poor            │ Excellent        │
│                  │ (lossy, variable)│ (lossless, fast) │
│                  │                 │                  │
│ Scalability      │ Complex         │ Simple           │
│                  │ (core upgrades) │ (add leafs)      │
│                  │                 │                  │
│ East-West        │ Bottlenecks     │ Optimized        │
│ traffic          │                 │                  │
│                  │                 │                  │
│ Cost (2024)      │ Lower upfront   │ Higher upfront   │
│                  │ but limited     │ but better TCO   │
└──────────────────┴─────────────────┴──────────────────┘
```

---

## Summary: Your Questions Answered

### 1. Link Speeds

**Modern datacenters (2024):**
- Servers: 25-100 Gbps (compute), 100-400 Gbps (storage/AI)
- Leaf-Spine: 100-400 Gbps
- Future: 800G/1.6T emerging

---

### 2. Oversubscription

**Historical:** 20:1 to 60:1 (terrible!)  
**Modern general compute:** 2:1 to 3:1 (acceptable)  
**Storage/RDMA:** 1:1 (non-blocking, required)  
**AI/HPC:** 1:1 (full bisection bandwidth)

---

### 3. Topology Evolution

**Old (3-tier):**
- Access → Aggregation → Core
- 3-5 hops, variable latency
- High oversubscription
- Complex to scale

**New (Spine-Leaf):**
- Leaf → Spine (2 hops always)
- Predictable latency (2-5 μs)
- Low oversubscription (1:1 to 3:1)
- Easy to scale (add leafs)

---

### 4. Why It Enables RDMA

✓ **Low oversubscription** - No congestion  
✓ **Equal-cost paths** - Predictable latency  
✓ **Short paths** - PFC works (2 hops)  
✓ **High bandwidth** - 100-400G everywhere  
✓ **Lossless config** - PFC + ECN throughout

**The spine-leaf topology is what makes modern storage disaggregation, RDMA, and cloud-scale infrastructure possible!**
