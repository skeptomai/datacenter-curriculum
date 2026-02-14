---
level: intermediate
estimated_time: 50 min
prerequisites:
  - 02_intermediate/02_rdma/02_protocol_variants.md
next_recommended:
  - 02_intermediate/02_rdma/04_numa_considerations.md
tags: [networking, rdma, roce, dcb, pfc, ets, converged-ethernet]
---

# RoCE and Converged Ethernet Explained

## RoCE = RDMA over Converged Ethernet

**Breaking down the acronym:**
- **R**DMA (Remote Direct Memory Access)
- **o**ver
- **C**onverged **E**thernet

The key word is **"Converged"**!

---

## What Does "Converged" Mean?

**Converged Ethernet = Running multiple types of traffic on a single Ethernet network**

Specifically: **Storage + Data + Management** all on one network.

---

## The Historical Problem

### Before Convergence (2000s)

**Separate networks for different traffic types:**

```
Traditional Datacenter (circa 2005):

┌─────────────────────────────────────────────────┐
│                  Server                         │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  NIC 1   │  │  NIC 2   │  │  HBA     │    │
│  │(Ethernet)│  │(Ethernet)│  │(Fibre    │    │
│  │          │  │          │  │ Channel) │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
└───────┼─────────────┼─────────────┼───────────┘
        │             │             │
        ↓             ↓             ↓
┌───────────┐  ┌──────────┐  ┌──────────┐
│ Ethernet  │  │ Ethernet │  │ Fibre    │
│ Switch    │  │ Switch   │  │ Channel  │
│ (Data)    │  │ (Mgmt)   │  │ Switch   │
│           │  │          │  │ (Storage)│
└───────────┘  └──────────┘  └──────────┘
      ↓              ↓             ↓
  Application    Management    SAN Storage
  Traffic        Traffic       Traffic

Problems:
  ✗ 3 separate networks to manage
  ✗ 3 different switch infrastructures
  ✗ 3 NICs per server (expensive!)
  ✗ High complexity
  ✗ Port count explosion
  ✗ High power consumption
```

**Why separate networks?**

```
Storage (Fibre Channel):
  - Requires lossless delivery
  - Cannot tolerate packet loss
  - Dedicated Fibre Channel switches
  - Expensive ($$$)
  
Data (Ethernet):
  - Best-effort delivery
  - TCP handles packet loss
  - Standard Ethernet switches
  - Cheaper

Could NOT run both on same network!
Ethernet was lossy, storage needed lossless.
```

---

### After Convergence (Converged Ethernet)

**Single network for all traffic:**

```
Modern Datacenter (2010+):

┌─────────────────────────────────────────────────┐
│                  Server                         │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Converged NIC (CNA)                     │  │
│  │  - 10/25/100 Gbps Ethernet               │  │
│  │  - Supports multiple traffic classes     │  │
│  └────────────────┬─────────────────────────┘  │
└───────────────────┼────────────────────────────┘
                    │ Single cable!
                    ↓
           ┌────────────────┐
           │  Converged     │
           │  Ethernet      │
           │  Switch        │
           │  (DCB-capable) │
           └────┬───┬───┬───┘
                │   │   │
         ┌──────┘   │   └──────┐
         ↓          ↓          ↓
    Application  Storage  Management
    Traffic      Traffic  Traffic
    (lossy)      (lossless)(lossy)

Benefits:
  ✓ Single network infrastructure
  ✓ Single NIC per server
  ✓ Lower complexity
  ✓ Lower cost
  ✓ Easier management
```

---

## How Converged Ethernet Works

### Data Center Bridging (DCB)

**DCB = Set of IEEE standards enabling convergence**

```
Key DCB Standards:
┌─────────────────────────────────────────────────┐
│ IEEE 802.1Qbb - Priority Flow Control (PFC)    │
│   Enable lossless for specific traffic classes │
│                                                 │
│ IEEE 802.1Qaz - Enhanced Transmission Selection│
│   Bandwidth allocation per traffic class       │
│                                                 │
│ IEEE 802.1Qau - Congestion Notification        │
│   Feedback for rate limiting                   │
│                                                 │
│ IEEE 802.1AB - LLDP (Discovery)                │
│   Neighbor discovery and capability exchange   │
└─────────────────────────────────────────────────┘

Together: "Data Center Bridging" (DCB)
Enable: Converged Ethernet
```

---

### Traffic Classes and Priorities

**Converged Ethernet uses 802.1p priority classes:**

```
Ethernet Frame with Priority:
┌────────┬──────────┬─────────┬─────────┬─────┐
│Dst MAC │ Src MAC  │802.1Q   │EtherType│Data │
│(6 byte)│ (6 byte) │VLAN tag │         │     │
└────────┴──────────┴─────────┴─────────┴─────┘
                         ↑
                         │
            ┌────────────┴────────────┐
            │ 802.1Q Tag (4 bytes)    │
            │                         │
            │ Bits 13-15: PCP         │
            │ (Priority Code Point)   │
            │ = 3 bits = 8 priorities │
            └─────────────────────────┘

Priority Classes (0-7):
  0: Best effort (default)
  1: Background
  2: Spare
  3: Excellent effort
  4: Controlled load
  5: Video (< 100ms latency)
  6: Voice (< 10ms latency)
  7: Network control
```

---

**Typical Converged Ethernet mapping:**

```
Priority Class Assignment:
┌──────────┬─────────────┬─────────┬────────────┐
│ Priority │ Traffic Type│ Lossless│ Bandwidth  │
├──────────┼─────────────┼─────────┼────────────┤
│    0     │ Default     │ No      │ Best effort│
│          │ (TCP/IP)    │ (lossy) │            │
│          │             │         │            │
│    1     │ Background  │ No      │ 10%        │
│          │             │         │            │
│          │             │         │            │
│    3     │ RDMA/RoCE   │ YES     │ 50%        │
│          │ (storage)   │ (PFC)   │ guaranteed │
│          │             │         │            │
│    4     │ iSCSI       │ YES     │ 30%        │
│          │ (storage)   │ (PFC)   │ guaranteed │
│          │             │         │            │
│    5     │ FCoE        │ YES     │ 30%        │
│          │ (Fibre      │ (PFC)   │ guaranteed │
│          │  Channel    │         │            │
│          │  over       │         │            │
│          │  Ethernet)  │         │            │
│          │             │         │            │
│    7     │ Network     │ No      │ Reserved   │
│          │ Control     │         │            │
└──────────┴─────────────┴─────────┴────────────┘
```

---

### Priority Flow Control (PFC)

**PFC enables selective lossless:**

```
Traditional Ethernet PAUSE:
───────────────────────────
PAUSE frame:
  - Stops ALL traffic on link
  - No priority awareness
  - Not suitable for converged networks

If storage needs pause, data traffic also stops!


Priority Flow Control (PFC):
────────────────────────────
PFC frame:
  - Stops SPECIFIC priority classes
  - Other priorities continue
  - Perfect for converged networks

Example:
  Priority 3 (RDMA) queue full:
    → Send PFC PAUSE for priority 3 only
    → Priority 0 (TCP) continues flowing
    → Priority 5 (FCoE) continues flowing
```

---

**PFC Frame Format:**

```
┌────────────┬──────────┬──────────┬───────────┐
│ Dst MAC    │ Src MAC  │ EtherType│ PFC       │
│ 01:80:C2:  │          │ 0x8808   │ Opcode    │
│ 00:00:01   │          │          │           │
└────────────┴──────────┴──────────┴───────────┘
                                    ↓
                    ┌───────────────────────────┐
                    │ Priority Enable Vector    │
                    │ (8 bits, one per priority)│
                    │                           │
                    │ Bit 0: Pause priority 0?  │
                    │ Bit 1: Pause priority 1?  │
                    │ Bit 2: Pause priority 2?  │
                    │ Bit 3: Pause priority 3?  │ ← RDMA
                    │ ...                       │
                    └───────────────────────────┘

Example PFC frame:
  Priority Enable = 0b00001000 (bit 3 set)
  → PAUSE only priority 3 (RDMA)
  → All other priorities continue
```

---

### Enhanced Transmission Selection (ETS)

**ETS allocates bandwidth per priority:**

```
Without ETS:
────────────
All priorities share link fairly
No guarantees
Storage might get starved by data traffic


With ETS:
─────────
Configure bandwidth allocation:

10 Gbps link:
  Priority 0 (Data):    4 Gbps (40%)
  Priority 3 (RDMA):    5 Gbps (50%)
  Priority 5 (FCoE):    1 Gbps (10%)

Each priority guaranteed minimum bandwidth
Can borrow unused bandwidth from others

Configuration per egress port:
┌────────────────────────────────────────┐
│ Port 1 ETS Configuration:              │
│                                        │
│ Priority 0: 40% strict minimum         │
│ Priority 3: 50% strict minimum         │
│ Priority 5: 10% strict minimum         │
│                                        │
│ Algorithm: Weighted Round Robin        │
└────────────────────────────────────────┘
```

---

## Coexistence: Lossless and Lossy Together

### How They Share the Network

```
┌─────────────────────────────────────────────────┐
│            Converged Ethernet Switch            │
│                                                 │
│  ┌────────────────────────────────────────────┐│
│  │ Ingress Port 1                             ││
│  │                                            ││
│  │ ┌─────────────────────────────────────┐   ││
│  │ │ Classifier (looks at 802.1p PCP)    │   ││
│  │ └──┬────────────────┬─────────────────┘   ││
│  │    │                │                      ││
│  │ ┌──▼──────┐    ┌───▼──────┐              ││
│  │ │ Queue 0 │    │ Queue 3  │              ││
│  │ │(Priority│    │(Priority │              ││
│  │ │   0)    │    │   3)     │              ││
│  │ │         │    │          │              ││
│  │ │ Lossy   │    │ Lossless │              ││
│  │ │ (TCP/IP)│    │ (RDMA)   │              ││
│  │ │         │    │          │              ││
│  │ │ Tail    │    │ PFC      │              ││
│  │ │ Drop    │    │ Enabled  │              ││
│  │ └────┬────┘    └────┬─────┘              ││
│  │      │              │                     ││
│  │      └──────┬───────┘                     ││
│  │             │                             ││
│  │      ┌──────▼──────┐                      ││
│  │      │ ETS Scheduler│ (bandwidth sharing) ││
│  │      └──────┬──────┘                      ││
│  │             │                             ││
│  │      ┌──────▼──────┐                      ││
│  │      │ Egress Port │                      ││
│  │      └─────────────┘                      ││
│  └────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘

Process:
1. Packet arrives
2. Classify by priority (read 802.1p)
3. Enqueue in appropriate queue
4. If lossless queue fills → Send PFC
5. Schedule packets using ETS (bandwidth allocation)
6. Transmit
```

---

### Example: Mixed Traffic Flow

```
Scenario: Server sending both web traffic and storage

Application Layer:
┌────────────────┐  ┌────────────────┐
│ Web Server     │  │ Storage Client │
│ (HTTP)         │  │ (RoCE)         │
└────────┬───────┘  └───────┬────────┘
         │                  │
         ↓ TCP              ↓ RDMA verbs
┌────────────────┐  ┌────────────────┐
│ TCP/IP Stack   │  │ RDMA Library   │
│ Priority: 0    │  │ Priority: 3    │
└────────┬───────┘  └───────┬────────┘
         │                  │
         └──────────┬───────┘
                    ↓
         ┌──────────────────┐
         │  Converged NIC   │
         │                  │
         │ Tags packets:    │
         │ - HTTP: PCP=0    │
         │ - RDMA: PCP=3    │
         └────────┬─────────┘
                  │
         ┌────────▼─────────┐
         │      Switch      │
         │                  │
         │ Queue 0 (PCP=0): │ ← HTTP (lossy)
         │  ▓▓▓░░░░░        │   Can drop
         │                  │
         │ Queue 3 (PCP=3): │ ← RDMA (lossless)
         │  ▓▓▓▓▓▓▓▓        │   PFC protects
         │    ↓ PFC PAUSE   │   Never drops
         └──────────────────┘

If Queue 3 fills:
  - Send PFC PAUSE for priority 3
  - Sender stops RDMA traffic
  - HTTP (priority 0) continues!
  - Queue 3 drains
  - Send PFC RESUME
  - RDMA traffic resumes
```

---

## Real-World Converged Ethernet Example

### Configuration

```
Typical datacenter switch configuration:

interface Ethernet1/1
  description Server Port
  
  # Enable DCB
  dcb priority-flow-control mode on
  
  # PFC on priority 3 (RDMA)
  dcb priority-flow-control priority 3 on
  
  # PFC off for other priorities (TCP/IP)
  dcb priority-flow-control priority 0 off
  dcb priority-flow-control priority 1 off
  
  # Bandwidth allocation (ETS)
  qos bandwidth percent 40 10 0 50
  #                     ↑  ↑  ↑ ↑
  #   Priority:         0  1  2 3
  #   TCP/IP gets 40%, RDMA gets 50%
  
  # Trust incoming priority tags
  qos trust cos
```

---

### Traffic Flow

```
Server sends mix of traffic:

┌─────────────────────────────────────────────┐
│ Same 100 Gbps NIC:                          │
│                                             │
│ Application 1: HTTP server                  │
│   → TCP/IP stack                            │
│   → Tagged PCP=0                            │
│   → 40 Gbps average                         │
│   → Lossy (drops acceptable)                │
│                                             │
│ Application 2: Distributed storage          │
│   → RDMA stack                              │
│   → Tagged PCP=3                            │
│   → 50 Gbps average                         │
│   → Lossless (PFC protected)                │
│                                             │
│ Application 3: Management                   │
│   → SSH, monitoring                         │
│   → Tagged PCP=0 (default)                  │
│   → 1 Gbps                                  │
│   → Lossy                                   │
└─────────────────────────────────────────────┘
              ↓ Single cable
┌─────────────────────────────────────────────┐
│           Switch processes:                 │
│                                             │
│ PCP=0 (HTTP+Mgmt): Queue 0 (lossy)         │
│   - 41 Gbps total                           │
│   - Tail drop if queue full                 │
│   - Normal TCP behavior                     │
│                                             │
│ PCP=3 (RDMA):      Queue 3 (lossless)      │
│   - 50 Gbps                                 │
│   - PFC if queue fills                      │
│   - NEVER drops packets                     │
└─────────────────────────────────────────────┘
```

---

## Beyond Storage: What Else Converges?

**Modern Converged Ethernet carries:**

```
┌────────────────┬──────────┬───────────────────┐
│ Traffic Type   │ Priority │ Lossless?         │
├────────────────┼──────────┼───────────────────┤
│ Data (TCP/IP)  │ 0        │ No (best effort)  │
│ Web, apps, etc │          │                   │
│                │          │                   │
│ RoCE (RDMA)    │ 3        │ Yes (PFC)         │
│ Storage        │          │                   │
│                │          │                   │
│ iSCSI          │ 4        │ Yes (PFC)         │
│ Storage        │          │                   │
│                │          │                   │
│ FCoE           │ 5        │ Yes (PFC)         │
│ (Fibre Channel│          │                   │
│  over Ethernet)│          │                   │
│                │          │                   │
│ VoIP           │ 6        │ No (but priority) │
│                │          │                   │
│ Control plane  │ 7        │ No                │
│ (BGP, LLDP)    │          │                   │
└────────────────┴──────────┴───────────────────┘

All on one Ethernet network!
Different QoS for each!
```

---

## Benefits of Convergence

```
Before (separate networks):
───────────────────────────
2x Ethernet NICs:    $400
1x FC HBA:           $800
3x cables:           $300
3x switch ports:     Complexity
Power:               3x NICs
Management:          3x complexity
Total:               $1500 + complexity

After (converged):
──────────────────
1x Converged NIC:    $600
1x cable:            $100  
1x switch port:      Simple
Power:               1x NIC
Management:          1x complexity
Total:               $700 + simplicity

Savings: ~50% cost, much simpler
```

---

## Challenges

```
DCB Configuration Complexity:
─────────────────────────────
✗ Must configure PFC correctly
✗ Must match priorities across network
✗ Misconfiguration = dropped RDMA packets
✗ Debugging is harder (mixed traffic)

PFC Issues:
───────────
✗ Head-of-line blocking possible
✗ Pause storms can occur
✗ Deadlock scenarios exist

Solution: Modern networks use ECN instead of PFC
          Or PFC + ECN together
```

---

## Summary: Your Question Answered

**"Are we talking about converged Ethernet, i.e., the ability to carry different types of traffic including standard TCP and RDMA?"**

**YES! Exactly right!**

**RoCE = RDMA over Converged Ethernet**

**"Converged" means:**
- ✓ Storage (RDMA, iSCSI, FCoE) + Data (TCP/IP) on same network
- ✓ Lossless + lossy traffic coexisting
- ✓ Single NIC, single cable, single switch infrastructure
- ✓ Different priority classes with different QoS
- ✓ PFC for lossless classes, tail drop for lossy classes

**How it works:**
- 802.1p priority classes (8 levels)
- Priority Flow Control (per-priority PAUSE)
- Enhanced Transmission Selection (bandwidth allocation)
- All standardized in Data Center Bridging (DCB)

**The revolution:** Eliminated need for separate Fibre Channel network for storage. Everything over Ethernet!
