---
level: specialized
estimated_time: 45 min
prerequisites:
  - 05_specialized/02_overlay_networking/04_ovs_control_data.md
next_recommended:
  - 05_specialized/02_overlay_networking/07_prepopulated_vs_learning.md
tags: [networking, openflow, sdn, flow-tables, compiler-model]
---

# OpenFlow and the Pre-Compiled Network Design

## Part 1: What is OpenFlow?

### The Core Abstraction

**OpenFlow is a protocol that separates the control plane from the data plane by providing a standard interface to program flow tables.**

**Traditional Switch:**
```
┌────────────────────────────────────────┐
│           Switch (Black Box)           │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  Control Plane (Proprietary)     │ │
│  │  - Spanning Tree Protocol        │ │
│  │  - MAC Learning                  │ │
│  │  - VLAN Config                   │ │
│  │  - Routing protocols             │ │
│  └──────────┬───────────────────────┘ │
│             │ Proprietary API          │
│  ┌──────────▼───────────────────────┐ │
│  │  Data Plane (ASIC)               │ │
│  │  - Packet forwarding             │ │
│  │  - TCAM lookup                   │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘

You can configure it (CLI, SNMP)
But you can't PROGRAM it
The switch decides how to forward
```

**OpenFlow Switch:**
```
┌────────────────────────────────────────┐
│        OpenFlow Switch                 │
│                                        │
│  Control Plane: REMOVED               │
│  (No MAC learning, no STP, nothing)    │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  Flow Tables (Programmable)      │ │
│  │  Table 0: [match] → [actions]    │ │
│  │  Table 1: [match] → [actions]    │ │
│  │  Table 2: [match] → [actions]    │ │
│  │  ...                              │ │
│  └──────────┬───────────────────────┘ │
│             │                          │
│  ┌──────────▼───────────────────────┐ │
│  │  Data Plane (ASIC/Software)      │ │
│  │  - Just execute flow actions     │ │
│  │  - No decisions, just follow     │ │
│  │    instructions                   │ │
│  └──────────────────────────────────┘ │
└────────────┬───────────────────────────┘
             │ OpenFlow Protocol
             │ (Standard, TCP port 6653)
      ┌──────▼──────┐
      │  Controller │  ← External "brain"
      │  (Software) │     Makes ALL decisions
      └─────────────┘     Programs flow tables
```

---

## Part 2: Flow Tables - The Core Data Structure

### Flow Table Structure

Each OpenFlow switch has one or more **flow tables**. Each table contains **flow entries**.

```
Flow Table:
┌─────────────────────────────────────────────────────────┐
│ Priority │ Match Fields        │ Actions       │ Stats │
├──────────┼────────────────────┼───────────────┼───────┤
│ 1000     │ in_port=1,         │ output:2      │ 1337  │
│          │ eth_dst=aa:bb:..   │               │ pkts  │
├──────────┼────────────────────┼───────────────┼───────┤
│ 900      │ eth_type=0x0800,   │ set_field:    │ 842   │
│          │ ip_dst=10.1.1.0/24 │   eth_dst=... │ pkts  │
│          │                    │ output:3      │       │
├──────────┼────────────────────┼───────────────┼───────┤
│ 100      │ *                  │ drop          │ 23    │
│          │ (catch-all)        │               │ pkts  │
└──────────┴────────────────────┴───────────────┴───────┘
```

---

### Match Fields (What to Look For)

OpenFlow can match on **40+ fields**:

```
Layer 1/2 (Ethernet):
  in_port:        Input port number
  eth_src:        Source MAC address
  eth_dst:        Destination MAC address
  eth_type:       EtherType (0x0800=IPv4, 0x0806=ARP, 0x86DD=IPv6)
  vlan_vid:       VLAN ID
  vlan_pcp:       VLAN priority

Layer 3 (IP):
  ip_proto:       IP protocol (6=TCP, 17=UDP, 1=ICMP)
  ip_src:         Source IP address (with mask)
  ip_dst:         Destination IP address (with mask)
  ip_dscp:        DSCP bits
  ip_ecn:         ECN bits
  ipv6_src:       IPv6 source
  ipv6_dst:       IPv6 destination

Layer 4 (TCP/UDP):
  tcp_src:        TCP source port
  tcp_dst:        TCP destination port
  tcp_flags:      TCP flags (SYN, ACK, FIN, etc.)
  udp_src:        UDP source port
  udp_dst:        UDP destination port

Tunnel/Virtual:
  tun_id:         Tunnel ID (VNI for VXLAN/Geneve)
  tun_src:        Tunnel source IP
  tun_dst:        Tunnel destination IP

Metadata (Internal):
  reg0-reg15:     General purpose registers (scratchpad)
  metadata:       64-bit metadata field
```

**Wildcards allowed:**
```
ip_dst=10.1.0.0/16    (match entire subnet)
eth_dst=01:00:00:00:00:00/01:00:00:00:00:00  (match multicast bit)
*                      (match anything)
```

---

### Actions (What to Do)

```
Basic Output:
  output:PORT             Send to port (1, 2, 3, ...)
  output:CONTROLLER       Send to controller
  output:ALL              Broadcast to all ports
  output:FLOOD            Flood (all ports except input)
  output:IN_PORT          Send back to input port

Modify Packet:
  set_field:VALUE→FIELD   Modify any field
    Examples:
      set_field:aa:bb:cc:dd:ee:ff→eth_dst
      set_field:10.1.1.1→ip_src
      set_field:80→tcp_dst

  push_vlan:ETHERTYPE     Add VLAN tag
  pop_vlan                Remove VLAN tag
  set_vlan_vid:VID        Set VLAN ID
  
  push_mpls:ETHERTYPE     Add MPLS label
  pop_mpls:ETHERTYPE      Remove MPLS label
  
  dec_ttl                 Decrement IP TTL
  
Group Actions:
  group:GROUP_ID          Execute group table entry
  
Metering:
  meter:METER_ID          Apply rate limiting

Special:
  drop                    Drop packet
  resubmit(,TABLE)        Re-process in another table
  
Registers/Metadata:
  load:VALUE→REG          Load value into register
  move:FIELD→FIELD        Copy between fields
```

---

### Multi-Table Pipeline

Modern OpenFlow (1.1+) supports **multiple tables** for complex pipelines:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Table 0  │───→│ Table 1  │───→│ Table 2  │───→│ Table 3  │
│ Ingress  │    │   ACL    │    │ Routing  │    │ Output   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │
     └───────────────┴───────────────┴───────────────┘
              goto-table, resubmit actions
```

**Example pipeline:**
```
Table 0: Port Security
  - Verify source MAC/IP (anti-spoofing)
  - Drop unauthorized packets
  - Tag with metadata (port ID)
  - goto table 1

Table 1: ACL/Firewall
  - Match on metadata + packet fields
  - Allow/deny based on policy
  - goto table 2

Table 2: Learning/Routing
  - Lookup destination
  - Decide output port
  - Load output port into register
  - goto table 3

Table 3: Output
  - Read register
  - Apply QoS
  - Output to port or tunnel
```

---

## Part 3: The Match-Action Paradigm

### How Packet Processing Works

```
Packet arrives:
┌─────────────────────────────────────┐
│ in_port=1                           │
│ eth_src=aa:bb:cc:dd:ee:ff          │
│ eth_dst=11:22:33:44:55:66          │
│ eth_type=0x0800 (IPv4)             │
│ ip_src=10.1.1.10                   │
│ ip_dst=10.2.2.20                   │
│ ip_proto=6 (TCP)                   │
│ tcp_src=45678                       │
│ tcp_dst=80                          │
└─────────────────────────────────────┘

Step 1: Start at Table 0
  Try to match flows in priority order
  
Flow 1 (priority 1000):
  Match: in_port=1, eth_type=0x0800, ip_dst=10.2.0.0/16
  Result: MATCH! ✓
  Actions:
    - load:5→reg0  (store datapath ID)
    - resubmit(,1)
    
Step 2: Continue to Table 1
  Packet now has: reg0=5
  
Flow 2 (priority 900):
  Match: reg0=5, ip_proto=6, tcp_dst=80
  Result: MATCH! ✓
  Actions:
    - set_field:11:22:33:44:55:77→eth_dst (rewrite MAC)
    - output:2
    
Step 3: Execute output
  Packet sent to port 2 with modified MAC
```

**If no match:**
```
Table 0: No matches found
  → Table miss
  
Table miss action (configured):
  Option A: Send to controller (slow path)
  Option B: Drop packet
  Option C: Continue to next table
```

---

## Part 4: The "Pre-Compile" Model

### Traditional Networking (Distributed Intelligence)

```
Switch makes decisions at runtime:

Packet arrives: [dst MAC: aa:bb:cc:dd:ee:ff]

Switch thinks:
  1. Have I seen this MAC before?
  2. Check MAC table... (search)
  3. Not found? → Learn source MAC, flood packet
  4. Found? → Forward to port X

Every switch:
  - Runs learning algorithm
  - Makes independent decisions
  - Discovers topology (STP, LLDP)
  - Reacts to failures
  
Distributed, autonomous, reactive
```

---

### SDN "Pre-Compile" Model (Centralized Intelligence)

```
Controller pre-computes everything:

┌─────────────────────────────────────────────┐
│         Controller (Offline Computation)    │
│                                             │
│ Input: Network topology, policies          │
│                                             │
│ Computation (happens ONCE):                │
│  1. Build graph of network                 │
│  2. For each (src, dst) pair:              │
│     - Compute shortest path                │
│     - Generate flows for each switch       │
│  3. Consider failures:                     │
│     - Compute backup paths                 │
│     - Generate failure-recovery flows      │
│  4. Apply policies:                        │
│     - ACLs → flow matches                  │
│     - QoS → meter actions                  │
│                                             │
│ Output: Complete flow tables for each      │
│         switch in the network               │
└─────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    ┌───────┐   ┌───────┐   ┌───────┐
    │ SW 1  │   │ SW 2  │   │ SW 3  │
    │       │   │       │   │       │
    │ Flows │   │ Flows │   │ Flows │
    │ ready │   │ ready │   │ ready │
    └───────┘   └───────┘   └───────┘

Packet forwarding:
  - Switches just lookup flows (fast!)
  - No learning, no discovery
  - Pre-computed, deterministic
  - Centralized, proactive
```

---

### The Compilation Process (Detailed)

#### Example: Simple L2 Switch

**User Intent (High Level):**
```
"Create a switch with 4 ports that learns MACs"
```

**Controller Compiles (Low Level):**

```
Table 0: MAC Learning
┌──────────┬─────────────────────────────────┬───────────────────┐
│ Priority │ Match                           │ Actions           │
├──────────┼─────────────────────────────────┼───────────────────┤
│ 1        │ * (any packet)                  │ learn(            │
│          │                                 │   table=1,        │
│          │                                 │   eth_dst=eth_src,│
│          │                                 │   output=in_port  │
│          │                                 │ ),                │
│          │                                 │ resubmit(,1)      │
└──────────┴─────────────────────────────────┴───────────────────┘

Table 1: MAC Forwarding (populated dynamically by learn action)
┌──────────┬─────────────────────────────────┬───────────────────┐
│ Priority │ Match                           │ Actions           │
├──────────┼─────────────────────────────────┼───────────────────┤
│ 1000     │ eth_dst=aa:bb:cc:dd:ee:ff      │ output:1          │
│          │                                 │                   │
│ 1000     │ eth_dst=11:22:33:44:55:66      │ output:2          │
│          │                                 │                   │
│ 0        │ * (unknown destination)         │ flood             │
└──────────┴─────────────────────────────────┴───────────────────┘

This implements traditional L2 learning!
But as OpenFlow rules
```

#### Example: OVN Logical Router

**User Intent (High Level):**
```yaml
Logical Router "router1":
  Interface to "web" network: 10.0.1.1/24
  Interface to "db" network:  10.0.2.1/24
  Route: 10.0.1.0/24 via local
  Route: 10.0.2.0/24 via local
```

**ovn-northd Compiles (Low Level):**

For each host, generates flows:

```
Host 1 Flows:

Table 0: Identify logical datapath
┌──────────┬──────────────────────────────┬────────────────────┐
│ Priority │ Match                        │ Actions            │
├──────────┼──────────────────────────────┼────────────────────┤
│ 100      │ in_port=vm1_port             │ load:5→reg1        │
│          │                              │ (datapath=web)     │
│          │                              │ resubmit(,1)       │
│          │                              │                    │
│ 100      │ in_port=vm2_port             │ load:6→reg1        │
│          │                              │ (datapath=db)      │
│          │                              │ resubmit(,1)       │
└──────────┴──────────────────────────────┴────────────────────┘

Table 10: Routing (for packets going to router)
┌──────────┬──────────────────────────────┬────────────────────┐
│ Priority │ Match                        │ Actions            │
├──────────┼──────────────────────────────┼────────────────────┤
│ 100      │ reg1=5 (from web),           │ load:10→reg1       │
│          │ ip_dst=10.0.2.0/24          │ (to router)        │
│          │                              │ resubmit(,11)      │
│          │                              │                    │
│ 100      │ reg1=6 (from db),            │ load:10→reg1       │
│          │ ip_dst=10.0.1.0/24          │ (to router)        │
│          │                              │ resubmit(,11)      │
└──────────┴──────────────────────────────┴────────────────────┘

Table 11: Router processing
┌──────────┬──────────────────────────────┬────────────────────┐
│ Priority │ Match                        │ Actions            │
├──────────┼──────────────────────────────┼────────────────────┤
│ 200      │ reg1=10 (router),            │ dec_ttl            │
│          │ ip_dst=10.0.1.0/24          │ load:5→reg1        │
│          │                              │ (to web)           │
│          │                              │ set_field:         │
│          │                              │   router_mac→      │
│          │                              │   eth_src          │
│          │                              │ resubmit(,12)      │
│          │                              │                    │
│ 200      │ reg1=10 (router),            │ dec_ttl            │
│          │ ip_dst=10.0.2.0/24          │ load:6→reg1        │
│          │                              │ (to db)            │
│          │                              │ set_field:         │
│          │                              │   router_mac→      │
│          │                              │   eth_src          │
│          │                              │ resubmit(,12)      │
└──────────┴──────────────────────────────┴────────────────────┘

Table 12: ARP resolution / Output
┌──────────┬──────────────────────────────┬────────────────────┐
│ Priority │ Match                        │ Actions            │
├──────────┼──────────────────────────────┼────────────────────┤
│ 100      │ reg1=5, ip_dst=10.0.1.10    │ set_field:vm1_mac  │
│          │                              │   →eth_dst         │
│          │                              │ output:vm1_port    │
│          │                              │                    │
│ 100      │ reg1=6, ip_dst=10.0.2.20    │ tunnel to Host2    │
│          │                              │ with Geneve        │
│          │                              │ options            │
└──────────┴──────────────────────────────┴────────────────────┘

This implements a complete router!
Routing, TTL decrement, MAC rewrite
All in OpenFlow rules
```

---

## Part 5: Reactive vs Proactive Flow Installation

### Reactive (Original OpenFlow Model)

```
First packet of flow arrives:
  1. Switch: No matching flow
  2. Switch: Send to controller (PACKET_IN)
  3. Controller: Compute path
  4. Controller: Install flows (FLOW_MOD)
  5. Controller: Forward packet (PACKET_OUT)
  
Subsequent packets:
  - Match installed flow
  - Forward at line rate
  
Problems:
  ✗ First packet high latency (10-100ms)
  ✗ Controller in critical path
  ✗ Controller can be overwhelmed
  ✗ Doesn't scale to large networks
```

**Packet flow:**
```
Time 0: First packet arrives
  Switch → Controller: PACKET_IN
  
Time 10ms: Controller responds
  Controller → Switch: FLOW_MOD (install flow)
  Controller → Switch: PACKET_OUT (forward packet)
  
Time 10.1ms: Flow installed
  Subsequent packets: Fast path
  
Problem: 10ms delay for first packet
```

---

### Proactive (Modern SDN, OVN Model)

```
At network startup:
  1. Controller computes ALL flows
  2. Controller installs flows on ALL switches
  3. Switches ready before first packet
  
When packet arrives:
  - Matching flow already present
  - Forward immediately
  - No controller involvement
  
Benefits:
  ✓ Zero first-packet latency
  ✓ Controller NOT in critical path
  ✓ Predictable performance
  ✓ Scales better
```

**Packet flow:**
```
Time -infinity: Controller pre-installs flows
  Controller → Switch: FLOW_MOD (thousands of flows)
  
Time 0: First packet arrives
  Switch: Flow match found
  Switch: Forward immediately
  Latency: <1μs
  
Time 1ms: Second packet arrives
  Switch: Flow match found
  Switch: Forward immediately
  Latency: <1μs
  
Controller never involved in forwarding!
```

---

## Part 6: Real OpenFlow Commands

### Installing a Flow

```bash
# Using ovs-ofctl (OpenFlow client)

# Simple L2 forwarding rule
ovs-ofctl add-flow br0 \
  "priority=1000,in_port=1,eth_dst=aa:bb:cc:dd:ee:ff,actions=output:2"

# L3 routing with IP rewrite
ovs-ofctl add-flow br0 \
  "table=0,priority=100,ip,nw_dst=10.1.1.0/24,actions=mod_nw_dst:10.2.2.20,output:3"

# Multi-table pipeline
ovs-ofctl add-flow br0 \
  "table=0,priority=100,in_port=1,actions=load:5->NXM_NX_REG0[],resubmit(,1)"

ovs-ofctl add-flow br0 \
  "table=1,priority=100,reg0=5,ip,actions=output:2"

# Geneve encapsulation
ovs-ofctl add-flow br0 \
  "table=5,priority=100,reg0=15,reg2=23,actions=\
   set_field:192.168.1.2->tun_dst,\
   set_field:5->tun_id,\
   load:15->NXM_NX_TUN_METADATA0[],\
   load:23->NXM_NX_TUN_METADATA1[],\
   output:geneve_sys_6081"
```

### Viewing Flows

```bash
# Show all flows
ovs-ofctl dump-flows br0

# Output:
cookie=0x0, duration=123.456s, table=0, n_packets=1337, n_bytes=133700,
  priority=1000,in_port=1,eth_dst=aa:bb:cc:dd:ee:ff actions=output:2

cookie=0x0, duration=98.765s, table=0, n_packets=842, n_bytes=84200,
  priority=100,ip,nw_dst=10.1.1.0/24 actions=mod_nw_dst:10.2.2.20,output:3

# Show flow stats
ovs-ofctl dump-flows br0 table=0

# Show specific match
ovs-ofctl dump-flows br0 "ip,nw_dst=10.1.1.10"
```

### Deleting Flows

```bash
# Delete specific flow
ovs-ofctl del-flows br0 "priority=1000,in_port=1"

# Delete all flows in table
ovs-ofctl del-flows br0 table=5

# Delete all flows (flush)
ovs-ofctl del-flows br0
```

---

## Part 7: Performance Implications

### Traditional Switch (MAC Learning)

```
Packet processing:
  1. Receive packet (hardware)
  2. Parse headers (hardware ASIC)
  3. Hash on dst MAC (hardware)
  4. Lookup in CAM table (hardware, parallel)
  5. Output decision (hardware)
  6. Transmit (hardware)
  
Speed: Line rate (100% wire speed)
Latency: 1-5 microseconds
Throughput: 148.8 Mpps @ 100Gbps (64-byte packets)

Everything in hardware!
```

---

### Software OpenFlow Switch (OVS)

**Fast Path (Flow cached in kernel):**
```
Packet processing:
  1. Receive packet (NIC)
  2. Interrupt to kernel
  3. OVS kernel module
  4. Exact-match cache lookup (hash table)
  5. Execute cached actions
  6. Transmit (NIC)
  
Speed: 1-10 Mpps (single core)
Latency: 10-50 microseconds
Throughput: ~10% of line rate for small packets

Still fast! Most time in network stack
```

**Slow Path (Cache miss → user space):**
```
Packet processing:
  1. Receive packet (NIC)
  2. Kernel OVS module
  3. Cache miss
  4. Upcall to ovs-vswitchd (context switch)
  5. User-space flow table lookup
  6. Install flow in kernel cache
  7. Return to kernel
  8. Forward packet
  
Speed: ~20,000 pps
Latency: 100-500 microseconds
Throughput: Terrible

Only happens once per flow!
```

---

### Hardware OpenFlow Switch

```
Modern switches (Broadcom Trident, Mellanox Spectrum):
  - OpenFlow flows compiled to TCAM/ASIC
  - Hardware performs lookups
  - Line-rate performance
  
Speed: Line rate
Latency: 1-5 microseconds
Throughput: 100% wire speed

Limitations:
  - TCAM size limited (4K-32K flows)
  - Not all OpenFlow features in hardware
  - Complex flows fall back to software
```

---

## Part 8: The "Compiler" Analogy

### Programming Language Analogy

```
High-Level Language (Python):
  result = compute_path(source, destination)
  
  - Human-readable
  - Abstract concepts
  - Platform-independent
  
↓ Compiler

Assembly/Machine Code:
  MOV EAX, [source]
  ADD EAX, [destination]
  MOV [result], EAX
  
  - Machine-executable
  - Concrete operations
  - Platform-specific
```

---

### SDN "Compiler" Analogy

```
High-Level Intent (Northbound):
  "Allow web servers to talk to database on port 5432"
  
  - Human-readable
  - Business logic
  - Infrastructure-independent
  
↓ SDN Controller (Compiler)

OpenFlow Rules (Southbound):
  priority=100,ip,nw_src=10.0.1.0/24,nw_dst=10.0.2.0/24,
    tcp_dst=5432,actions=output:2
  
  priority=100,ip,nw_src=10.0.2.0/24,nw_dst=10.0.1.0/24,
    tcp_src=5432,actions=output:1
  
  - Switch-executable
  - Concrete match-action
  - Hardware-specific
```

---

### The Compilation Process

```
┌─────────────────────────────────────────────┐
│ Step 1: High-Level Intent                  │
├─────────────────────────────────────────────┤
│ Logical Topology:                          │
│   Switch "web" (ports: vm1, vm2, vm3)      │
│   Switch "db" (ports: vm4, vm5)            │
│   Router between them                       │
│   Policy: Allow web→db on port 5432        │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  Controller Logic   │
        │  (ovn-northd)       │
        └──────────┬──────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ Step 2: Intermediate Representation        │
├─────────────────────────────────────────────┤
│ Logical flows (datapath-centric):          │
│   Datapath 5 (web switch):                 │
│     Input from vm1 → load port_id          │
│     Match dst in db network → route        │
│   Datapath 10 (router):                    │
│     Match web→db, port 5432 → allow        │
│     Decrement TTL, rewrite MAC             │
│   Datapath 6 (db switch):                  │
│     Match from router → forward to vm4     │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  Physical Compiler  │
        │  (ovn-northd)       │
        └──────────┬──────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ Step 3: Physical OpenFlow                  │
├─────────────────────────────────────────────┤
│ Host1 flows:                                │
│   table=0,in_port=1,actions=load:15→reg0   │
│   table=5,reg0=15,ip_dst=10.0.2.0/24,      │
│     tcp_dst=5432,actions=load:10→reg1      │
│   table=10,reg1=10,actions=dec_ttl,        │
│     set_field:new_mac→eth_src,resubmit(,11)│
│   table=20,reg2=23,actions=tunnel_to_host2 │
│                                             │
│ Host2 flows:                                │
│   table=0,tun_id=6,actions=load:6→reg1     │
│   table=15,reg1=6,ip_dst=10.0.2.10,        │
│     actions=output:vm4_port                 │
└─────────────────────────────────────────────┘
```

---

## Part 9: Why This Model Wins

### Benefits of Pre-Compiled Flows

**1. Performance:**
```
Reactive:
  First packet: 10-100ms (controller query)
  Subsequent: <1μs (flow cached)
  
Proactive:
  ALL packets: <1μs (flows pre-installed)
  
No "first packet penalty"
```

**2. Reliability:**
```
Reactive:
  Controller failure → Can't install new flows
  Controller overload → Dropped packets
  
Proactive:
  Controller failure → Forwarding continues!
  Controller just for config changes
  
Control plane failure doesn't affect data plane
```

**3. Predictability:**
```
Reactive:
  Performance varies (first packet slow)
  Depends on controller load
  
Proactive:
  Consistent performance
  Deterministic behavior
  
Better for real-time applications
```

**4. Scalability:**
```
Reactive:
  Controller sees every new flow
  Becomes bottleneck at ~10K flows/sec
  
Proactive:
  Controller computes offline
  Can handle millions of flows
  
Scales to datacenter-size networks
```

---

### Drawbacks of Pre-Compiled Flows

**1. Flow Table Size:**
```
Need flows for ALL possible paths
  - Web subnet (256 IPs) → DB subnet (256 IPs)
  - = 65,536 flows just for this!
  
TCAM limits:
  - Hardware: 4K-32K flows
  - Software: Millions of flows
  
Must use wildcards, summarization
```

**2. Adaptability:**
```
Topology change requires recompilation:
  - Link failure detected
  - Controller recomputes flows
  - Pushes new flows to switches
  - Takes 1-10 seconds
  
Slower to adapt than distributed protocols
```

**3. State Synchronization:**
```
Controller must know full topology:
  - Which VMs on which hosts
  - Which hosts reachable via which paths
  - Current policy state
  
Complex state management
```

---

## Part 10: Modern Hybrid Approaches

### Combining Reactive and Proactive

```
OVN approach:
  Proactive:
    - Common flows pre-installed
    - Known VM-to-VM paths
    - Default policies
  
  Reactive:
    - Unknown destinations → learn
    - Dynamic ARP responses
    - Rare edge cases
  
Best of both worlds
```

### Using Geneve to Reduce Flow Count

```
Without Geneve:
  Need flow for each (src_ip, dst_ip, port) tuple
  Millions of flows!

With Geneve:
  Single flow: "If Geneve option says datapath 5, output to tunnel"
  Options carry the details
  Thousands of flows
  
Geneve options as "compression" for flow state
```

---

## Summary

**OpenFlow is:**
- A protocol to program flow tables
- Match-action paradigm
- Separates control from data plane

**Pre-compiled model:**
- Controller computes ALL flows upfront
- Installs on switches before traffic
- Switches forward without controller
- Like compiled code vs interpreted code

**Key insight:**
```
Traditional: Switches are intelligent, distributed
SDN: Switches are dumb, centralized intelligence

Traditional: Discover and react
SDN: Compute and install

Traditional: Runtime decisions
SDN: Compile-time decisions
```

**The compilation stack:**
```
User Intent (Logical)
     ↓
Controller Logic (Compilation)
     ↓
OpenFlow Flows (Machine Code)
     ↓
Switch Execution (Hardware)
```

This is why SDN is revolutionary - it makes networks **programmable** in the same way compilers made computers programmable. You write high-level intent, the "compiler" (controller) translates to low-level flows, and the "CPU" (switches) execute them.
