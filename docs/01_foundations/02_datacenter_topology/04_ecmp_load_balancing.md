---
level: foundational
estimated_time: 50 min
prerequisites:
  - 01_foundations/02_datacenter_topology/03_3tier_vs_spine_leaf.md
next_recommended:
  - 02_intermediate/01_advanced_networking/01_vlan_vs_vxlan.md
  - 02_intermediate/02_rdma/01_rdma_fundamentals.md
tags: [networking, datacenter, ecmp, load-balancing, hashing]
---

# Spine-Leaf Topology and ECMP: Corrected

## Part 1: The Correct Spine-Leaf Topology

### Fixed Diagram

```
Spine-Leaf (Correct):
═════════════════════

     ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
     │Spine 1 │  │Spine 2 │  │Spine 3 │  │Spine 4 │  ← Spine layer
     └─┬─┬─┬─┬┘  └─┬─┬─┬─┬┘  └─┬─┬─┬─┬┘  └─┬─┬─┬─┬┘    (4 switches)
       │ │ │ │      │ │ │ │      │ │ │ │      │ │ │ │
       │ │ │ └──────┼─┼─┼──────┼─┼─┼──────┼─┼─┼────────┐
       │ │ └────────┼─┼─┼──────┼─┼─┼──────┼─┼─┼──────┐ │
       │ └──────────┼─┼─┼──────┼─┼─┼──────┼─┼─┼────┐ │ │
       └────────────┼─┼─┼──────┼─┼─┼──────┼─┼─┼──┐ │ │ │
                    │ │ │      │ │ │      │ │ │  │ │ │ │
     ┌──────────────┘ │ │      │ │ │      │ │ │  │ │ │ │
     │ ┌──────────────┘ │      │ │ │      │ │ │  │ │ │ │
     │ │ ┌──────────────┘      │ │ │      │ │ │  │ │ │ │
     │ │ │ ┌──────────────────┘ │ │      │ │ │  │ │ │ │
     │ │ │ │ ┌──────────────────┘ │      │ │ │  │ │ │ │
     │ │ │ │ │ ┌──────────────────┘      │ │ │  │ │ │ │
     │ │ │ │ │ │ ┌────────────────────────┘ │ │  │ │ │ │
     │ │ │ │ │ │ │ ┌────────────────────────┘ │  │ │ │ │
     │ │ │ │ │ │ │ │ ┌────────────────────────┘  │ │ │ │
     │ │ │ │ │ │ │ │ │ ┌────────────────────────────┘ │ │
     │ │ │ │ │ │ │ │ │ │ ┌────────────────────────────┘ │
     │ │ │ │ │ │ │ │ │ │ │ ┌────────────────────────────┘
     ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼
   ┌────────┐┌────────┐┌────────┐┌────────┐
   │ Leaf 1 ││ Leaf 2 ││ Leaf 3 ││ Leaf 4 │  ← Leaf layer
   └┬┬┬┬┬┬┬┬┘└┬┬┬┬┬┬┬┬┘└┬┬┬┬┬┬┬┬┘└┬┬┬┬┬┬┬┬┘    (4 switches)
    ││││││││  ││││││││  ││││││││  ││││││││
   [Servers] [Servers] [Servers] [Servers]

Key properties:
  - Leaf 1: ONE link to Spine 1, ONE to Spine 2, ONE to Spine 3, ONE to Spine 4
  - Leaf 2: ONE link to Spine 1, ONE to Spine 2, ONE to Spine 3, ONE to Spine 4
  - Leaf 3: ONE link to Spine 1, ONE to Spine 2, ONE to Spine 3, ONE to Spine 4
  - Leaf 4: ONE link to Spine 1, ONE to Spine 2, ONE to Spine 3, ONE to Spine 4
  
  Total: 4 leafs × 4 spines = 16 links between layers
  Each leaf has 4 uplinks (one to each spine)
  Each spine has 4 downlinks (one to each leaf)
```

---

### Connection Matrix

```
Visual representation of connections:

        Spine 1   Spine 2   Spine 3   Spine 4
Leaf 1:    ✓         ✓         ✓         ✓      (4 uplinks)
Leaf 2:    ✓         ✓         ✓         ✓      (4 uplinks)
Leaf 3:    ✓         ✓         ✓         ✓      (4 uplinks)
Leaf 4:    ✓         ✓         ✓         ✓      (4 uplinks)
         (4 down)  (4 down)  (4 down)  (4 down)

Each ✓ represents ONE physical link (e.g., 100 Gbps)

NOT multiple cables between same leaf-spine pair!
```

---

### Why This Topology?

**Every leaf must reach every spine:**

```
For Server A (Leaf 1) to reach Server B (Leaf 3):

Available paths:
  1. Leaf1 → Spine1 → Leaf3
  2. Leaf1 → Spine2 → Leaf3
  3. Leaf1 → Spine3 → Leaf3
  4. Leaf1 → Spine4 → Leaf3

Four equal-cost paths!
All 2 hops, all same bandwidth, all same latency

This is ECMP (Equal Cost Multi-Path)
```

---

## Part 2: ECMP (Equal Cost Multi-Path) Deep Dive

### What is ECMP?

**ECMP = Load balancing across multiple equal-cost paths**

```
Traditional routing:
────────────────────
Single "best" path to destination
  - Based on lowest metric (hop count, etc.)
  - All traffic uses same path
  - Other paths unused (wasted capacity)

Example:
  A → B has 4 possible paths
  Routing picks path 1 (lowest metric)
  All traffic uses path 1
  Paths 2, 3, 4 idle

ECMP routing:
─────────────
Multiple "best" paths with equal cost
  - All paths have same metric
  - Traffic distributed across all paths
  - Full utilization of available bandwidth

Example:
  A → B has 4 equal-cost paths
  Routing identifies all 4 as "best"
  Traffic spread across all 4 paths
  4x effective bandwidth!
```

---

### The 5-Tuple Hash

**ECMP uses flow-based hashing to select path:**

```
5-Tuple (Layer 3/4 information):
─────────────────────────────────

1. Source IP address      (32 or 128 bits)
2. Destination IP address (32 or 128 bits)
3. Source port           (16 bits)
4. Destination port      (16 bits)
5. Protocol              (8 bits: TCP=6, UDP=17, etc.)

Hash function:
  hash = crc32(src_ip || dst_ip || src_port || dst_port || protocol)
  
  OR more commonly:
  hash = (src_ip XOR dst_ip XOR src_port XOR dst_port XOR protocol)
  
Path selection:
  path_index = hash % num_paths
  
Example with 4 paths:
  hash = 0x12345678
  path = 0x12345678 % 4 = 0 (use Spine 1)
```

---

### Why 5-Tuple?

**Properties needed for good ECMP hashing:**

```
1. Deterministic:
   Same flow ALWAYS uses same path
   Why? Prevents packet reordering
   
   Flow: 10.0.1.5:12345 → 10.0.2.10:80 TCP
   First packet: hash → path 2
   Second packet: MUST use path 2 (same hash)
   
   If packets took different paths:
     → Different latencies
     → Arrive out of order
     → TCP sees as loss
     → Unnecessary retransmits

2. Uniform distribution:
   Different flows spread evenly across paths
   Why? Load balancing
   
   1000 flows:
     Path 1: ~250 flows
     Path 2: ~250 flows
     Path 3: ~250 flows
     Path 4: ~250 flows
     
   Good: All paths equally utilized
   Bad: All flows on path 1 (waste 75% capacity)

3. Stable under topology changes:
   Adding/removing path minimally affects flow mapping
   Why? Minimize disruption
   
   With 4 paths, flow hash to path 2
   Path 2 fails → 3 paths remain
   Re-hash: Hopefully still consistent path
```

---

### ECMP Example: Packet Flow

```
Server A (Leaf 1) sends to Server B (Leaf 3):

Packet details:
  Src IP: 10.0.1.5 (Server A)
  Dst IP: 10.0.3.10 (Server B)
  Src Port: 54321 (ephemeral)
  Dst Port: 443 (HTTPS)
  Protocol: TCP (6)

Leaf 1 performs ECMP:
  1. Extract 5-tuple from packet:
     (10.0.1.5, 10.0.3.10, 54321, 443, 6)
  
  2. Compute hash:
     hash = crc32(10.0.1.5 || 10.0.3.10 || 54321 || 443 || 6)
     hash = 0xA3F12C8B
  
  3. Select path:
     num_paths = 4 (4 spines available)
     path_index = 0xA3F12C8B % 4 = 3
     
     Use Spine 4!
  
  4. Forward packet:
     Leaf 1 → Spine 4 → Leaf 3 → Server B

All subsequent packets in this flow:
  Same 5-tuple → Same hash → Same path (Spine 4)
  No reordering!

Different flow (new connection):
  Src Port: 54322 (different!)
  5-tuple changes
  hash = 0x7B3A5F21
  path_index = 0x7B3A5F21 % 4 = 1
  
  Use Spine 2!
  
  Load spreads across spines naturally
```

---

### ECMP Hash Calculation at Switch

```
Hardware hashing (ASIC):
────────────────────────

Packet arrives at Leaf 1:
┌──────────────────────────────────────────┐
│ Ethernet Header                          │
│ IP Header:                               │
│   Src: 10.0.1.5                          │
│   Dst: 10.0.3.10                         │
│   Protocol: 6 (TCP)                      │
│ TCP Header:                              │
│   Src Port: 54321                        │
│   Dst Port: 443                          │
│ Payload: ...                             │
└──────────────────────────────────────────┘

Switch ASIC extracts fields:
  → src_ip    = 0x0A000105
  → dst_ip    = 0x0A00030A
  → src_port  = 0xD431
  → dst_port  = 0x01BB
  → protocol  = 0x06

Hash computation (parallel hardware):
  Step 1: XOR all fields
    0x0A000105 XOR
    0x0A00030A XOR
    0x0000D431 XOR
    0x000001BB XOR
    0x00000006
    = 0x0A00D62F
  
  Step 2: Additional mixing (implementation-specific)
    hash = rotate(hash, 13) XOR hash
    (ensures better distribution)
  
  Step 3: Modulo num_paths
    final = hash % 4
    = 3

Time: ~10 nanoseconds (in hardware)!
```

---

## Part 3: ECMP Load Distribution

### Perfect Distribution (Large Number of Flows)

```
Scenario: 1000 concurrent TCP connections

Each connection = unique 5-tuple (different src_port)
  
Hash distribution (statistical):
  Spine 1: 247 flows (24.7%)
  Spine 2: 251 flows (25.1%)
  Spine 3: 255 flows (25.5%)
  Spine 4: 247 flows (24.7%)
  
Nearly perfect 25% each!

Bandwidth utilization:
  If each flow averages 100 Mbps:
    Spine 1: 247 × 100M = 24.7 Gbps
    Spine 2: 251 × 100M = 25.1 Gbps
    Spine 3: 255 × 100M = 25.5 Gbps
    Spine 4: 247 × 100M = 24.7 Gbps
  
  Total: 100 Gbps evenly distributed!
```

---

### Imperfect Distribution (Small Number of Flows)

```
Scenario: 4 elephant flows (large, long-lived)

Flow 1: 10.0.1.5:1000 → 10.0.2.10:80
  hash % 4 = 0 → Spine 1
  Bandwidth: 25 Gbps

Flow 2: 10.0.1.5:2000 → 10.0.2.10:80
  hash % 4 = 0 → Spine 1 (collision!)
  Bandwidth: 25 Gbps

Flow 3: 10.0.1.5:3000 → 10.0.2.10:80
  hash % 4 = 2 → Spine 3
  Bandwidth: 25 Gbps

Flow 4: 10.0.1.5:4000 → 10.0.2.10:80
  hash % 4 = 3 → Spine 4
  Bandwidth: 25 Gbps

Result:
  Spine 1: 50 Gbps (2 flows) ← Overloaded!
  Spine 2: 0 Gbps (0 flows)  ← Idle
  Spine 3: 25 Gbps (1 flow)
  Spine 4: 25 Gbps (1 flow)

Problem: Hash collision!
  Two large flows hashed to same path
  Imbalance occurs

Reality: With many flows, rarely a problem
         Datacenter has thousands of flows
```

---

### The "Elephant vs Mice" Problem

```
Datacenter traffic pattern:

┌────────────────────┬──────────┬──────────────┐
│ Flow Type          │ % of     │ % of         │
│                    │ Flows    │ Bandwidth    │
├────────────────────┼──────────┼──────────────┤
│ Mice (< 10 MB)     │ 95%      │ 20%          │
│ - Web requests     │          │              │
│ - RPC calls        │          │              │
│ - Short transfers  │          │              │
│                    │          │              │
│ Elephants (> 1 GB) │ 5%       │ 80%          │
│ - Storage repl     │          │              │
│ - Backups          │          │              │
│ - Large transfers  │          │              │
└────────────────────┴──────────┴──────────────┘

ECMP handles mice well:
  Many small flows → Good statistical distribution
  
ECMP handles elephants poorly:
  Few large flows → Hash collisions possible
  One elephant can saturate a path

Solutions:
  - Flowlet switching (break elephant into flowlets)
  - Adaptive routing (monitor path utilization)
  - Weighted ECMP (use path capacity in hash)
```

---

## Part 4: ECMP and RDMA

### Why ECMP Works Well for RDMA

**RDMA characteristics:**

```
Many concurrent flows:
  Distributed storage: 100s of flows per server
  Each flow: 4KB - 4MB (not elephants)
  Good statistical distribution

Example: Ceph OSD with 100 concurrent clients
  Each client: Unique (IP, port) pair
  100 different 5-tuples
  Hash distributes across 4 spines
  Each spine: ~25 clients
  
  Perfect load balancing!
```

---

### ECMP and PFC Interaction

**Important consideration:**

```
Scenario: PFC triggered on one path

Leaf 1 → Spine 2 → Leaf 3 (congested)
  ↓
Leaf 3 queue full (receiving too much)
  ↓
Leaf 3 sends PFC PAUSE to Spine 2
  ↓
Spine 2 pauses traffic to Leaf 3
  ↓
Spine 2 queue fills
  ↓
Spine 2 sends PFC to Leaf 1

But only for traffic going to Spine 2!

Leaf 1 still sends via Spine 1, 3, 4:
  - Other flows unaffected
  - Only flows hashed to Spine 2 paused
  - 75% of flows continue!

This is why ECMP + PFC works:
  Congestion isolated per-path
  Not global backpressure
```

---

### ECMP Path Failure Handling

```
Scenario: Spine 2 fails

Before failure:
  4 paths available
  hash % 4 → Uses all 4 spines

After failure:
  3 paths available
  hash % 3 → Different distribution!

Example flow:
  5-tuple hash = 0x1234
  
  Before: 0x1234 % 4 = 0 (Spine 1)
  After:  0x1234 % 3 = 1 (Spine 2, but failed!)
         Rehash or use next available
  
  Result: Flow might change path
          Causes packet reordering
          TCP handles it (slight slowdown)

Better approach: Consistent hashing
  Minimizes flow disruption on topology change
  Many modern switches support this
```

---

## Part 5: ECMP Variants

### Standard ECMP (Per-Flow)

```
What we've described so far:
  Hash on 5-tuple
  All packets in flow use same path
  Flow-level granularity

Pros:
  ✓ No packet reordering within flow
  ✓ Simple to implement
  ✓ Works well for most traffic

Cons:
  ✗ Hash collisions (elephant flows)
  ✗ Path utilization imbalance possible
```

---

### Weighted ECMP

```
Use path capacity/utilization in decision:

Instead of:
  path = hash % num_paths

Use:
  Assign weights based on:
    - Link capacity (100G vs 400G)
    - Current utilization
    - Queue depth
  
  Select path proportional to weight

Example:
  Spine 1: 100G, 50% utilized → weight 50
  Spine 2: 100G, 80% utilized → weight 20
  Spine 3: 400G, 30% utilized → weight 280
  Spine 4: 100G, 60% utilized → weight 40
  
  Total weight: 390
  
  New flow:
    hash = 0x5678
    scaled = (hash × 390) >> 32
    
    If scaled < 50:    Use Spine 1
    If scaled < 70:    Use Spine 2  
    If scaled < 350:   Use Spine 3 (70% of traffic!)
    Else:              Use Spine 4

Result: Spine 3 (400G) gets more traffic
        Load balanced by capacity
```

---

### Flowlet Switching

```
Problem: One elephant flow saturates path

Solution: Break flow into "flowlets"

Flowlet = Burst of packets separated by idle time

Example elephant flow:
  1 GB transfer
  
Traditional ECMP:
  All 1 GB uses same path (hash once)
  Can overload that path

Flowlet switching:
  Detect idle gaps (> 100 μs)
  Re-hash after each gap
  Different bursts can use different paths
  
  Burst 1 (100 MB): hash % 4 = 0 → Spine 1
  [gap]
  Burst 2 (100 MB): hash % 4 = 2 → Spine 3
  [gap]
  Burst 3 (100 MB): hash % 4 = 1 → Spine 2
  
  Elephant distributed across paths!

Challenge: Must avoid reordering
  Only re-hash after sufficient gap
  Gap ensures earlier packets delivered
```

---

### Adaptive Routing (Letflow, Hula, etc.)

```
Problem: Static hash doesn't adapt to congestion

Solution: Monitor path conditions, route dynamically

Letflow example:
  Each switch monitors:
    - Queue depth per egress port
    - Utilization per path
  
  For new flow:
    Don't just hash
    Pick LEAST loaded path
  
  Example:
    Spine 1: Queue 50% full
    Spine 2: Queue 80% full
    Spine 3: Queue 30% full ← Pick this!
    Spine 4: Queue 60% full
  
  Result: Better load balancing
          Adapts to traffic patterns

Challenge: Packet reordering possible
          Must be careful with flow tracking
```

---

## Part 6: ECMP Configuration Example

### Leaf Switch Configuration

```
Cisco Nexus (example):

# Enable ECMP globally
feature ecmp

# Configure ECMP hash
hardware access-list tcam region racl 0
hardware access-list tcam region e-racl 256

# Hash on 5-tuple (default)
ip load-sharing method src-dst-ip-port

# Alternative: Hash on more fields (better distribution)
ip load-sharing method src-dst-ip-l4port-vlan

# Set maximum ECMP paths
maximum-paths 64

# Per-interface
interface Ethernet1/1
  description uplink-to-spine-1
  no switchport
  ip address 10.1.1.1/31
  no shutdown

interface Ethernet1/2
  description uplink-to-spine-2
  ip address 10.1.2.1/31
  no shutdown

[... repeat for all spine uplinks]

# Routing (all spines equal cost)
router bgp 65001
  neighbor 10.1.1.0 remote-as 65000
  neighbor 10.1.2.0 remote-as 65000
  neighbor 10.1.3.0 remote-as 65000
  neighbor 10.1.4.0 remote-as 65000
  
  address-family ipv4 unicast
    maximum-paths 64
    
# BGP advertises same route from all spines
# Equal cost → ECMP across all 4 paths
```

---

## Summary: Your Corrections and ECMP

### Topology Correction

**You were right:**
- Each leaf has ONE link to each spine
- NOT multiple links to same spine
- 4 leafs × 4 spines = 16 total links
- Creates 4 equal-cost paths for any leaf-to-leaf traffic

---

### ECMP Role

**Load balancing mechanism:**

1. **5-tuple hash:**
   - Source IP
   - Destination IP
   - Source port
   - Destination port
   - Protocol

2. **Per-flow granularity:**
   - Same flow → same path (no reordering)
   - Different flows → distributed across paths

3. **Statistical distribution:**
   - Many flows → ~25% per path
   - Few flows → possible imbalance

4. **Works well with RDMA:**
   - Many concurrent flows
   - Small-medium size (not elephants)
   - Good distribution naturally

---

### Why It Matters

**ECMP enables:**
- ✓ Full utilization of all spine links
- ✓ 4x effective bandwidth (vs single path)
- ✓ Fault tolerance (lose 1 spine = 75% capacity remains)
- ✓ Predictable latency (all paths equal)
- ✓ Perfect for RDMA lossless traffic

**Without ECMP:** Would need to choose single spine per destination, wasting 75% of infrastructure!
