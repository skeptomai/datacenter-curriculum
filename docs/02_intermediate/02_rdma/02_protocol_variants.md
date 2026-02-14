---
level: intermediate
estimated_time: 45 min
prerequisites:
  - 02_intermediate/02_rdma/01_rdma_fundamentals.md
next_recommended:
  - 02_intermediate/02_rdma/03_converged_ethernet.md
tags: [networking, rdma, roce, infiniband, iwarp, lossless]
---

# RDMA: L2 vs L3, and Lossless Requirements

## The Confusion

You're conflating two separate things:
1. **Layer (L2 vs L3)** - Can RDMA route across subnets?
2. **Lossless requirement** - Must prevent packet drops

These are independent!

---

## RDMA Variants: Different Layers

### RoCEv1 (RDMA over Converged Ethernet v1)

```
RoCEv1: L2 ONLY
───────────────

Protocol stack:
┌──────────────────────┐
│  RDMA Verbs          │
├──────────────────────┤
│  InfiniBand Transport│
├──────────────────────┤
│  Ethernet (L2)       │  ← No IP layer!
├──────────────────────┤
│  Physical            │
└──────────────────────┘

Packet format:
┌────────────┬─────────────┬──────────┐
│ Ethernet   │ InfiniBand  │ Data     │
│ Header     │ Headers     │          │
│ (14 bytes) │ (varies)    │          │
└────────────┴─────────────┴──────────┘

Limitations:
  ✗ Cannot route across subnets
  ✗ Single broadcast domain only
  ✗ Limited scalability
  
Why L2 only?
  Uses EtherType 0x8915 (InfiniBand over Ethernet)
  Switches forward based on MAC address only
  No IP addressing
```

---

### RoCEv2 (RDMA over Converged Ethernet v2)

```
RoCEv2: L3 ROUTABLE
───────────────────

Protocol stack:
┌──────────────────────┐
│  RDMA Verbs          │
├──────────────────────┤
│  InfiniBand Transport│
├──────────────────────┤
│  UDP                 │  ← Added UDP!
├──────────────────────┤
│  IP (IPv4/IPv6)      │  ← Added IP!
├──────────────────────┤
│  Ethernet (L2)       │
├──────────────────────┤
│  Physical            │
└──────────────────────┘

Packet format:
┌────────┬────────┬────────┬─────────────┬──────┐
│Ethernet│  IP    │  UDP   │ InfiniBand  │ Data │
│ Header │ Header │ Header │ Headers     │      │
│(14 B)  │(20 B)  │ (8 B)  │  (varies)   │      │
└────────┴────────┴────────┴─────────────┴──────┘

Benefits:
  ✓ Can route across subnets!
  ✓ Works with IP routers
  ✓ Scalable to large networks
  ✓ Can use ECN for congestion control
  
UDP port: 4791 (standard)
IP protocol: Can route like any IP packet!
```

---

### InfiniBand

```
InfiniBand: Its Own Network Stack
──────────────────────────────────

Not Ethernet at all!
Custom physical layer, link layer, network layer

Protocol stack:
┌──────────────────────┐
│  RDMA Verbs          │
├──────────────────────┤
│  InfiniBand Transport│
├──────────────────────┤
│  InfiniBand Network  │  ← Can route across subnets!
├──────────────────────┤
│  InfiniBand Link     │
├──────────────────────┤
│  InfiniBand Physical │
└──────────────────────┘

Uses:
  - InfiniBand switches (not Ethernet)
  - InfiniBand cables
  - Subnet Manager for routing
  - Can have multiple subnets with routing

Has routing: YES
Uses IP: NO (own addressing: LID = Local ID, GID = Global ID)
```

---

### iWARP (Internet Wide Area RDMA Protocol)

```
iWARP: RDMA Over TCP/IP
───────────────────────

Protocol stack:
┌──────────────────────┐
│  RDMA Verbs          │
├──────────────────────┤
│  RDMA Layer (MPA)    │
├──────────────────────┤
│  TCP                 │  ← Full TCP!
├──────────────────────┤
│  IP                  │
├──────────────────────┤
│  Ethernet            │
├──────────────────────┤
│  Physical            │
└──────────────────────┘

Features:
  ✓ Routable across WAN
  ✓ Uses TCP for reliability
  ✓ Can traverse NAT/firewalls
  ✓ Works over lossy networks (TCP handles retransmit)
  
Tradeoff:
  ✗ Higher latency (TCP overhead)
  ✗ More CPU usage (TCP processing)
  
Used for: Long-distance RDMA, less common in datacenters
```

---

## Comparison Table

```
┌────────────┬─────────┬──────────┬───────────┬────────────┐
│ Variant    │ Layer   │ Routable │ Lossless  │ Retransmit │
│            │         │          │ Required? │            │
├────────────┼─────────┼──────────┼───────────┼────────────┤
│ RoCEv1     │ L2      │ No       │ YES       │ No         │
│            │         │ (L2 only)│ (PFC)     │            │
│            │         │          │           │            │
│ RoCEv2     │ L3      │ Yes      │ YES       │ No         │
│            │         │ (IP)     │ (PFC+ECN) │            │
│            │         │          │           │            │
│ InfiniBand │ L3-ish  │ Yes      │ YES       │ Yes        │
│            │ (custom)│ (own)    │ (built-in)│ (link-level│
│            │         │          │           │  only)     │
│            │         │          │           │            │
│ iWARP      │ L3      │ Yes      │ No        │ Yes        │
│            │         │ (IP)     │ (TCP does)│ (TCP)      │
└────────────┴─────────┴──────────┴───────────┴────────────┘
```

---

## Key Insight: Lossless ≠ L2 Only

**The lossless requirement is NOT because of L2!**

```
WHY lossless is needed:
  RDMA (most variants) have no transport-level retransmission
  If packet drops, connection fails
  
  InfiniBand: Has link-level retransmit (hop-by-hop)
  RoCE: No retransmit at all
  iWARP: Uses TCP retransmit
  
This is about RELIABILITY, not LAYER!
```

---

## RoCEv2 Example: L3 Routing with Lossless

**RoCEv2 can route across subnets but still needs lossless:**

```
Network topology:

Subnet 1: 10.0.1.0/24        Subnet 2: 10.0.2.0/24
┌──────────────────┐         ┌──────────────────┐
│  Host A          │         │  Host B          │
│  10.0.1.10       │         │  10.0.2.20       │
│  RDMA NIC        │         │  RDMA NIC        │
└────────┬─────────┘         └─────────┬────────┘
         │                             │
    ┌────▼─────┐       ┌──────────┐   │
    │ Switch 1 │───────│  Router  │───┤
    └──────────┘       └──────────┘   │
                                  ┌────▼─────┐
                                  │ Switch 2 │
                                  └──────────┘

RoCEv2 packet flow:
1. Host A creates packet:
   - Src IP: 10.0.1.10
   - Dst IP: 10.0.2.20
   - UDP port: 4791
   - InfiniBand headers + data

2. Switch 1: L2 forwarding to router

3. Router: L3 routing decision
   - Lookup 10.0.2.0/24 → interface to Switch 2
   - Decrement TTL
   - Forward

4. Switch 2: L2 forwarding to Host B

5. Host B receives packet, processes RDMA

This is L3 routing!
But still requires lossless (PFC/ECN) at each hop!
```

---

## Flow Control at Different Layers

### L2 Flow Control: PFC (Priority Flow Control)

```
Works at: Ethernet layer (L2)
Used by: RoCEv1, RoCEv2

Mechanism:
┌──────────────┐
│  Upstream    │
│  Device      │  Receives PAUSE frame
└──────┬───────┘
       │ PAUSE (priority 3)
       ↓
┌──────▼───────┐
│   Switch     │  Queue full, sends PAUSE
│   Port       │
└──────────────┘

PAUSE frame format (Ethernet):
┌────────────┬──────────┬──────────┬──────────┐
│ Dst MAC    │ Src MAC  │ EtherType│ PAUSE    │
│ (multicast)│          │ 0x8808   │ params   │
└────────────┴──────────┴──────────┴──────────┘

Scope: Single hop (L2 link)
       Cannot cross routers!

Problem with RoCEv2 routing:
  PFC only works hop-by-hop
  Each L2 link protected individually
  Router must also support PFC on each interface
```

---

### L3 Flow Control: ECN (Explicit Congestion Notification)

```
Works at: IP layer (L3)
Used by: RoCEv2 (with DCQCN)

Mechanism:
┌──────────────┐
│  Sender      │  Receives ECN echo, slows down
└──────┬───────┘
       ↑ ECN echo
       │
┌──────▼───────┐
│  Receiver    │  Sends ECN echo back
└──────▲───────┘
       │ Packet with ECN mark
       │
┌──────┴───────┐
│   Switch     │  Marks packet (sets ECN bits)
│  (congested) │
└──────────────┘

ECN uses IP header bits:
┌─────────────────────────────────────┐
│  IP Header (20 bytes)               │
│  ...                                │
│  TOS/DSCP byte:                     │
│    Bits 6-7: ECN bits               │
│      00: Not ECN-capable            │
│      01: ECN-capable (ECT)          │
│      10: ECN-capable (ECT)          │
│      11: Congestion Experienced (CE)│
└─────────────────────────────────────┘

Scope: End-to-end (L3)
       Works across routers!

Perfect for RoCEv2 routing!
```

---

## Combining PFC and ECN for RoCEv2

**Modern RoCEv2 deployments use BOTH:**

```
PFC:
  - Hop-by-hop backpressure
  - Prevents buffer overflow at switches
  - L2 mechanism (per link)
  - Fast reaction (microseconds)
  
ECN/DCQCN:
  - End-to-end congestion signaling
  - Rate limiting at source
  - L3 mechanism (across routers)
  - Slower reaction (milliseconds)

Together:
  PFC: Emergency brake (prevent immediate drop)
  ECN: Cruise control (prevent congestion)
  
Example:
  Normal operation: ECN controls rate
  Sudden burst: PFC stops overflow
  Then ECN reduces source rate
  PFC releases
```

---

## Why Most RDMA Variants Need Lossless

### The Core Issue: No Reliable Transport

```
TCP (has reliable transport):
──────────────────────────────
Sender:
  1. Send packet seq=100
  2. Start timer
  3. If no ACK, retransmit
  4. Keep buffer until ACKed
  
Receiver:
  1. Receive seq=100
  2. Send ACK
  3. If seq=101 missing, detect gap
  4. Request retransmit

Buffer management: Sender keeps sent data
Retransmission: Automatic
Reordering: Handled
Loss tolerance: High

RoCE (no reliable transport):
──────────────────────────────
Sender:
  1. Send packet
  2. No timer!
  3. No buffer!
  4. Assume it arrives
  
Receiver:
  1. Receive packet, DMA to memory
  2. If missing packet: ??? 
  3. No way to request retransmit
  4. Connection is corrupt!

Why no retransmit?
  - Buffering sender-side data adds latency
  - Retransmit logic adds complexity
  - Defeats low-latency goal
  - Works only if network is LOSSLESS
```

---

### InfiniBand: The Exception

```
InfiniBand HAS retransmission:
───────────────────────────────

But it's LINK-LEVEL (hop-by-hop):

┌──────┐     ┌──────┐     ┌──────┐
│ Host │─────│  SW  │─────│ Host │
└──────┘     └──────┘     └──────┘
    └──────────┘└──────────┘
      Link 1      Link 2

Each link:
  - Sender buffers packets
  - Receiver ACKs
  - Retransmit if no ACK
  - Separate per link

Benefits:
  ✓ Can tolerate link-level errors
  ✓ Don't need PFC/ECN

Tradeoffs:
  ✗ More complex hardware
  ✗ Slightly higher latency
  ✗ InfiniBand-specific switches required
```

---

## Summary: Your Question Answered

**"So RDMA is L2 only, must control frame transmission?"**

**NO and YES:**

1. **RDMA is NOT L2 only:**
   - RoCEv1: L2 only ✓
   - RoCEv2: L3 routable (IP) ✓
   - InfiniBand: L3-ish (own routing) ✓
   - iWARP: L3 over TCP/IP ✓

2. **RDMA DOES need flow control (usually):**
   - NOT because it's L2
   - BECAUSE it lacks retransmission
   - To prevent packet loss (fatal for RoCE)

3. **Flow control mechanisms:**
   - PFC: L2 mechanism (PAUSE frames)
   - ECN: L3 mechanism (IP bits)
   - RoCEv2 can use BOTH
   - Works across routers with ECN

**The key insight:**

```
Lossless requirement ≠ L2 only

RoCEv2 example:
  ✓ Routes across subnets (L3)
  ✓ Still needs lossless (PFC + ECN)
  
Reason: No transport-layer retransmission
Not reason: L2 limitation
```

**Modern datacenters use RoCEv2 (L3 routable) with lossless Ethernet (PFC + ECN) for scalable, low-latency RDMA across routed networks.**
