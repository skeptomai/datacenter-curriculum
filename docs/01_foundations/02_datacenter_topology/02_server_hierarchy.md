---
level: foundational
estimated_time: 30 min
prerequisites:
  - 01_foundations/02_datacenter_topology/01_modern_topology.md
next_recommended:
  - 01_foundations/02_datacenter_topology/03_3tier_vs_spine_leaf.md
tags: [networking, datacenter, spine-leaf, hierarchy]
---

# Spine-Leaf: The Complete Hierarchy

## The Full Picture - Servers to Spines

### Correct Understanding

**A leaf is a TOP-OF-RACK SWITCH that aggregates multiple servers:**

```
Complete Topology:
══════════════════

                 ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
                 │Spine 1 │  │Spine 2 │  │Spine 3 │  │Spine 4 │
                 └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘
                     │           │           │           │
       ┌─────────────┼───────────┼───────────┼───────────┼──────┐
       │             │           │           │           │      │
       │   ┌─────────┼───────────┼───────────┼──────┐    │      │
       │   │         │           │           │      │    │      │
       │   │    ┌────┼───────────┼──────┐    │      │    │      │
       │   │    │    │           │      │    │      │    │      │
       ▼   ▼    ▼    ▼           ▼      ▼    ▼      ▼    ▼      ▼
    ┌────────┐┌────────┐      ┌────────┐  ┌────────┐  ┌────────┐
    │ Leaf 1 ││ Leaf 2 │ ...  │ Leaf 3 │  │ Leaf 4 │  │ Leaf N │  ← Leaf layer
    │  (ToR) ││  (ToR) │      │  (ToR) │  │  (ToR) │  │  (ToR) │    (switches!)
    └┬┬┬┬┬┬┬┬┘└┬┬┬┬┬┬┬┬┘      └┬┬┬┬┬┬┬┬┘  └┬┬┬┬┬┬┬┬┘  └┬┬┬┬┬┬┬┬┘
     ││││││││  ││││││││        ││││││││    ││││││││    ││││││││
     ││││││││  ││││││││        ││││││││    ││││││││    ││││││││
     ▼▼▼▼▼▼▼▼  ▼▼▼▼▼▼▼▼        ▼▼▼▼▼▼▼▼    ▼▼▼▼▼▼▼▼    ▼▼▼▼▼▼▼▼
    ┌────────┐┌────────┐      ┌────────┐  ┌────────┐  ┌────────┐
    │Server 1││Server 2│ ...  │Server 9│  │Server  │  │Server  │  ← Server layer
    │        ││        │      │        │  │   17   │  │   N    │    (hosts!)
    └────────┘└────────┘      └────────┘  └────────┘  └────────┘
    [  Rack 1 servers  ]      [ Rack 2 ]  [ Rack 3 ]  [ Rack N ]

Three layers:
  1. Servers (32-48 per rack)
  2. Leaf switches (1 per rack, aggregates servers)
  3. Spine switches (aggregate all leafs)
```

---

## Layer Breakdown

### Layer 1: Servers (The Actual Compute)

```
Physical servers in a rack:
┌─────────────────────────────────────────┐
│            Server Rack                  │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 1U Server 1                     │   │
│  │ - CPU, RAM, Disk                │   │
│  │ - NIC: 2×25G (dual-port)        │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │ 1U Server 2                     │   │
│  └─────────────────────────────────┘   │
│  ...                                    │
│  (30 more servers)                      │
│  ...                                    │
│  ┌─────────────────────────────────┐   │
│  │ 1U Server 32                    │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 2U Leaf Switch (Top-of-Rack)    │ ← │
│  │ - 48×25G server ports           │   │
│  │ - 8×100G spine uplinks          │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘

Connections:
  Each server's NIC → Leaf switch port
  32 servers × 2 ports = 64 connections
  But switches often have:
    - Port 1 → Leaf A
    - Port 2 → Leaf B (redundancy)
  
Typical: 32 servers per rack
```

---

### Layer 2: Leaf Switches (Top-of-Rack)

```
Leaf switch = Aggregation point for one rack

┌──────────────────────────────────────────┐
│        Leaf Switch (ToR)                 │
│                                          │
│  Downlink Ports (to servers):            │
│  ┌────────────────────────────────────┐  │
│  │ Port 1:  Server 1 (25G)            │  │
│  │ Port 2:  Server 2 (25G)            │  │
│  │ Port 3:  Server 3 (25G)            │  │
│  │ ...                                │  │
│  │ Port 32: Server 32 (25G)           │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Uplink Ports (to spines):               │
│  ┌────────────────────────────────────┐  │
│  │ Port 49: Spine 1 (100G)            │  │
│  │ Port 50: Spine 2 (100G)            │  │
│  │ Port 51: Spine 3 (100G)            │  │
│  │ Port 52: Spine 4 (100G)            │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘

Typical configuration:
  32-48 × 25G server-facing ports
  4-8 × 100G spine-facing ports
  
Example: Cisco Nexus 93180YC-FX
         Arista 7050X3
         Juniper QFX5120
```

---

### Layer 3: Spine Switches (Aggregation Core)

```
Spine switch = Interconnects all leaf switches

┌──────────────────────────────────────────┐
│         Spine Switch                     │
│                                          │
│  All ports are leaf-facing:              │
│  ┌────────────────────────────────────┐  │
│  │ Port 1:  Leaf 1  (100G)            │  │
│  │ Port 2:  Leaf 2  (100G)            │  │
│  │ Port 3:  Leaf 3  (100G)            │  │
│  │ Port 4:  Leaf 4  (100G)            │  │
│  │ ...                                │  │
│  │ Port 32: Leaf 32 (100G)            │  │
│  └────────────────────────────────────┘  │
│                                          │
│  NO SERVER CONNECTIONS!                  │
│  Spines only talk to leafs               │
└──────────────────────────────────────────┘

Typical configuration:
  32-64 × 100/400G ports (all to leafs)
  
Example: Cisco Nexus 9500
         Arista 7500R3
         Juniper QFX10000
```

---

## Concrete Example: 1024-Server Datacenter

### Bill of Materials

```
Servers:
────────
1024 servers total
32 servers per rack
32 racks needed

Specification per server:
  2×25 Gbps NIC (dual-port for redundancy)
  Connects to 2 different leaf switches

Leaf Switches:
──────────────
32 leaf switches (1 per rack)

Each leaf:
  48 × 25G ports for servers
    → Can connect 48 servers
    → Using 32 ports (some spare capacity)
  
  4 × 100G ports for spines
    → Connects to 4 spine switches
    → 1 link per spine

Total downlink capacity per leaf:
  32 servers × 25G = 800 Gbps

Total uplink capacity per leaf:
  4 spines × 100G = 400 Gbps

Oversubscription: 800:400 = 2:1

Spine Switches:
───────────────
4 spine switches

Each spine:
  32 × 100G ports for leafs
    → Connects to all 32 leafs
    → 1 link per leaf

Total capacity per spine:
  32 leafs × 100G = 3.2 Tbps
```

---

### Physical Layout

```
Datacenter Floor:
═════════════════

Row 1:
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│Rack 1│ │Rack 2│ │Rack 3│ │Rack 4│ ...
│      │ │      │ │      │ │      │
│Leaf 1│ │Leaf 2│ │Leaf 3│ │Leaf 4│ ← Leaf at top of each rack
│      │ │      │ │      │ │      │
│32 Srv│ │32 Srv│ │32 Srv│ │32 Srv│ ← 32 servers below
└──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
   │        │        │        │
   └────────┴────────┴────────┴─────→ All connect to spines

Row 2:
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│Rack 5│ │Rack 6│ │Rack 7│ │Rack 8│ ...
│Leaf 5│ │Leaf 6│ │Leaf 7│ │Leaf 8│
│32 Srv│ │32 Srv│ │32 Srv│ │32 Srv│
└──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
   │        │        │        │
   └────────┴────────┴────────┴─────→ All connect to spines

... (8 rows total)

Spine Row (separate):
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Spine 1 │ │Spine 2 │ │Spine 3 │ │Spine 4 │
│        │ │        │ │        │ │        │
│ Cables │ │ Cables │ │ Cables │ │ Cables │
│   to   │ │   to   │ │   to   │ │   to   │
│  all   │ │  all   │ │  all   │ │  all   │
│  32    │ │  32    │ │  32    │ │  32    │
│ leafs  │ │ leafs  │ │ leafs  │ │ leafs  │
└────────┘ └────────┘ └────────┘ └────────┘

Total: 32 racks + 1 spine row
```

---

## Traffic Flows

### Intra-Rack (East-West within Rack)

```
Server 1 (Rack 1) → Server 2 (Rack 1):

┌────────┐                    ┌────────┐
│Server 1│                    │Server 2│
└───┬────┘                    └───▲────┘
    │                             │
    │ 25 Gbps                     │ 25 Gbps
    ↓                             │
┌───────────────────────────────────┐
│         Leaf 1 (ToR)              │
│  L2 switching (same VLAN)         │
└───────────────────────────────────┘

Hops: 1 (just through leaf)
Latency: ~1-2 μs
Bandwidth: 25 Gbps (full server speed)

No spine involved!
```

---

### Inter-Rack (East-West across Racks)

```
Server 1 (Rack 1) → Server 10 (Rack 2):

┌────────┐                              ┌────────┐
│Server 1│                              │Server10│
└───┬────┘                              └───▲────┘
    │                                       │
    │ 25 Gbps                               │ 25 Gbps
    ↓                                       │
┌────────┐                              ┌────────┐
│ Leaf 1 │                              │ Leaf 2 │
└───┬────┘                              └───▲────┘
    │                                       │
    │ ECMP hash selects spine               │
    │ (e.g., Spine 2)                       │
    │ 100 Gbps                              │ 100 Gbps
    ↓                                       │
         ┌────────┐
         │Spine 2 │
         └────────┘

Hops: 3 (leaf → spine → leaf)
Latency: ~5 μs
Bandwidth: Up to 25 Gbps (server limited)
          OR limited by oversubscription

Path selection: ECMP based on 5-tuple
```

---

### North-South (Internet Traffic)

```
External Client → Server 1:

    Internet
       │
       ↓
  ┌─────────┐
  │ Border  │  ← Edge routers
  │ Routers │
  └────┬────┘
       │
       │ Connects to spines or separate core
       │
       ↓
  ┌────────┐
  │Spine 1 │
  └───┬────┘
      │ 100 Gbps
      ↓
  ┌────────┐
  │ Leaf 1 │
  └───┬────┘
      │ 25 Gbps
      ↓
  ┌────────┐
  │Server 1│
  └────────┘

Hops: 4+ (border → spine → leaf → server)
```

---

## Scaling Dimensions

### Horizontal Scaling (Add More Servers)

```
Option 1: Fill existing racks
─────────────────────────────
Current: 32 servers per rack × 32 racks = 1024 servers
         Using 32 of 48 ports per leaf

Add servers:
  Add 16 more servers per rack
  Now using 48 of 48 ports per leaf
  Total: 48 × 32 = 1536 servers

No network changes needed!


Option 2: Add more racks
────────────────────────
Current: 32 racks (leafs)

Add racks:
  Add Rack 33 with Leaf 33
  Connect Leaf 33 to all 4 spines
  Add 32 servers to Rack 33
  
  Total: 33 racks × 32 servers = 1056 servers

Limitation:
  Spine switches have 32 ports
  Can only support 32 leafs max!
  
To exceed 32 racks:
  Need bigger spine switches (64 ports)
  OR add more spine switches
  OR move to multi-tier (super spine)
```

---

### Vertical Scaling (More Bandwidth)

```
Upgrade server NICs:
────────────────────
Old: 25 Gbps per server
New: 100 Gbps per server

Impact:
  Leaf ports: Need 100G capable (expensive!)
  Oversubscription increases:
    48 servers × 100G = 4.8 Tbps down
    4 uplinks × 100G = 400 Gbps up
    Ratio: 4.8T:400G = 12:1 (too high!)
  
Solution:
  Upgrade spine links to 400G
  48 × 100G = 4.8 Tbps down
  4 × 400G = 1.6 Tbps up  
  Ratio: 3:1 (acceptable)


Add more spine uplinks:
───────────────────────
Old: 4 × 100G uplinks (400 Gbps)
New: 8 × 100G uplinks (800 Gbps)

Requires:
  More spine switches (8 instead of 4)
  OR spines with more ports
  
Benefit:
  32 × 25G = 800 Gbps down
  8 × 100G = 800 Gbps up
  Ratio: 1:1 (non-blocking!)
```

---

## Summary: Your Question Answered

**Q: Is a server a leaf, or is a leaf still an aggregator switch?**

**A: Leaf is an AGGREGATOR SWITCH (Top-of-Rack)**

The hierarchy is:
1. **Servers** (32-48 per rack) - The actual compute hosts
2. **Leaf switches** (1 per rack) - Aggregate servers, connect to spines
3. **Spine switches** (4-16 total) - Aggregate leafs, interconnect all racks

**Servers connect TO leafs, servers are NOT leafs!**

Think of it as:
- **Access layer:** Servers (the endpoints)
- **Aggregation layer:** Leaf switches (Top-of-Rack)
- **Core layer:** Spine switches (datacenter-wide)

The "spine-leaf" terminology refers to the **switch-to-switch topology**, not server-to-switch. It's still a 3-layer architecture (servers, leafs, spines), but the leafs and spines form a 2-tier non-blocking fabric for inter-rack traffic.
