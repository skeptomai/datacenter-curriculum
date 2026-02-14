# Pre-Populated Rules vs Dynamic Learning in SDN

## The Nuanced Answer

You're absolutely right to question this. The reality is more complex than "all pre-populated" or "all learned."

**Short answer:** It's a **hybrid approach** - some rules are pre-populated, some are learned dynamically.

---

## The Spectrum

```
Pure Learning              Hybrid                Pure Pre-Populated
(Traditional L2)           (Most SDN)            (Theoretical Extreme)
     │                         │                          │
     │                         │                          │
  ┌──▼──┐                 ┌───▼───┐                 ┌────▼────┐
  │ MAC │                 │  Core │                 │  Every  │
  │Learn│                 │  flows│                 │  path   │
  │ all │                 │  pre- │                 │  pre-   │
  │ at  │                 │  pop'd│                 │  comp'd │
  │ run │                 │       │                 │         │
  │ time│                 │ + MAC │                 │ No      │
  │     │                 │  learn│                 │ learn   │
  └─────┘                 │       │                 │ at all  │
                          │ + ARP │                 │         │
                          │  learn│                 │         │
                          └───────┘                 └─────────┘
                          
 Linux Bridge             OVN (reality)          Theoretical SDN
```

---

## What OVN Actually Does (Hybrid Model)

### Pre-Populated (Compile-Time)

**1. Logical Network Structure:**
```
Controller knows:
  - Which logical switches exist
  - Which logical routers exist
  - Which ports are on which switches
  - Which VMs are on which hosts
  
Pre-installs flows for:
  - Ingress pipeline (port security, ACLs)
  - Logical switch forwarding
  - Logical router forwarding
  - Tunnel encapsulation
```

**Example pre-installed flows:**
```bash
# Table 0: Ingress - identify logical port
table=0,priority=100,in_port=vnet0,actions=load:15→reg0,resubmit(,1)
table=0,priority=100,in_port=vnet1,actions=load:16→reg0,resubmit(,1)

# Table 1: Port security
table=1,priority=100,reg0=15,dl_src=aa:bb:cc:dd:ee:ff,actions=resubmit(,2)

# Table 2: ACLs (pre-computed from policy)
table=2,priority=1000,reg0=15,ip,nw_dst=10.0.2.0/24,tp_dst=5432,actions=resubmit(,3)

# Table 5: Logical switch forwarding (THIS is where learning happens)
# See below...

# Table 10: Logical router (pre-computed routes)
table=10,priority=100,ip,nw_dst=10.0.1.0/24,actions=dec_ttl,load:5→reg1,resubmit(,11)
table=10,priority=100,ip,nw_dst=10.0.2.0/24,actions=dec_ttl,load:6→reg1,resubmit(,11)
```

**These are STATIC** - installed by controller based on configuration.

---

### Dynamically Learned (Run-Time)

**2. MAC Address Learning:**

Even though OVN knows the topology, it doesn't necessarily know every MAC address. It uses the **OpenFlow "learn" action** for dynamic learning.

**The OpenFlow "learn" action:**
```bash
# Table 5: MAC learning flow (pre-installed)
table=5,priority=1,actions=learn(
  table=6,                    # Install learned flow in table 6
  hard_timeout=300,           # Expire after 5 minutes
  priority=100,               # Learned flow priority
  eth_dst=eth_src,            # Match: dst MAC = this packet's src MAC
  load:in_port→output_reg     # Action: output to this packet's input port
),resubmit(,6)

# This flow is ALWAYS HIT
# For every packet, it creates a dynamic flow in table 6
```

**What this does:**

```
Packet arrives:
  src_mac: aa:bb:cc:dd:ee:ff
  in_port: vnet0 (port 15)

"learn" action executes:
  Creates NEW flow in table 6:
    table=6,priority=100,eth_dst=aa:bb:cc:dd:ee:ff,actions=output:vnet0
    
  This flow expires in 300 seconds if unused
  Refreshed on every packet from that MAC
  
This is DYNAMIC MAC LEARNING!
Just like traditional switches
But implemented in OpenFlow
```

**After learning, table 6 looks like:**
```bash
# Dynamically learned entries (created by "learn" action)
table=6,priority=100,hard_timeout=300,eth_dst=aa:bb:cc:dd:ee:ff,actions=output:vnet0
table=6,priority=100,hard_timeout=300,eth_dst=11:22:33:44:55:66,actions=output:vnet1
table=6,priority=100,hard_timeout=300,eth_dst=ff:ee:dd:cc:bb:aa,actions=output:vnet2

# Default: unknown MAC
table=6,priority=0,actions=flood
```

---

### ARP Learning

**3. ARP Response Learning:**

Similar to MAC learning, ARP responses can be learned:

```bash
# Learn ARP responses
table=7,priority=100,arp,actions=learn(
  table=8,
  hard_timeout=300,
  priority=100,
  nw_dst=arp_spa,           # Match: IP dst = ARP source protocol address
  actions=set_field:arp_sha→eth_dst,output:in_port
),resubmit(,8)
```

**What this does:**

```
ARP Response arrives:
  arp_spa: 10.0.1.10 (IP address)
  arp_sha: aa:bb:cc:dd:ee:ff (MAC address)
  in_port: vnet0

Creates flow:
  table=8,priority=100,ip,nw_dst=10.0.1.10,actions=set_field:aa:bb:cc:dd:ee:ff→eth_dst,output:vnet0
  
Future packets to 10.0.1.10:
  - Automatically get MAC rewritten
  - Output to correct port
  - No ARP needed!
```

---

## FIB (Forwarding Information Base) Composition

### What's in the FIB?

```
┌──────────────────────────────────────────────┐
│           Forwarding Information Base        │
├──────────────────────────────────────────────┤
│                                              │
│  STATIC (Pre-Populated by Controller):      │
│    - Logical topology flows                 │
│    - ACL/policy flows                       │
│    - Routing table entries                  │
│    - Tunnel encap/decap flows              │
│    - Default/catch-all flows                │
│                                              │
│  DYNAMIC (Learned at Runtime):              │
│    - MAC address → port mappings            │
│    - ARP cache (IP → MAC mappings)          │
│    - Unknown unicast handling               │
│    - Conntrack entries                      │
│                                              │
└──────────────────────────────────────────────┘
```

---

## Detailed Example: Packet Processing

### Scenario: VM1 sends to VM2 (first time)

**Setup:**
- VM1: MAC aa:aa:aa:aa:aa:aa, IP 10.0.1.10, on port vnet0
- VM2: MAC bb:bb:bb:bb:bb:bb, IP 10.0.1.20, on port vnet1
- Same logical switch (no routing needed)

---

**Step 1: VM1 sends ARP request for 10.0.1.20**

```
Packet: ARP request "Who has 10.0.1.20?"

Processing:

Table 0 (Ingress - STATIC):
  Match: in_port=vnet0 ✓
  Actions: load:15→reg0 (logical port 15), resubmit(,1)

Table 1 (Port Security - STATIC):
  Match: reg0=15, dl_src=aa:aa:aa:aa:aa:aa ✓
  Actions: resubmit(,2)

Table 5 (MAC Learning - STATIC rule, creates DYNAMIC entry):
  Match: * (all packets) ✓
  Actions:
    learn(table=6, eth_dst=aa:aa:aa:aa:aa:aa, output:vnet0)
    resubmit(,6)
  
  → Creates DYNAMIC flow in table 6:
      table=6,eth_dst=aa:aa:aa:aa:aa:aa,actions=output:vnet0

Table 6 (MAC Forwarding - checking DYNAMIC entries):
  Match: eth_dst=ff:ff:ff:ff:ff:ff (broadcast) 
  No match in learned entries ✗
  Falls through to default

Table 6 (Default - STATIC):
  Match: * (catch-all)
  Actions: flood (broadcast to all ports except input)
  
Packet broadcasted to vnet1, vnet2, etc.
```

---

**Step 2: VM2 receives ARP request, sends ARP reply**

```
Packet: ARP reply "10.0.1.20 is at bb:bb:bb:bb:bb:bb"

Processing:

Table 0 (Ingress - STATIC):
  Match: in_port=vnet1 ✓
  Actions: load:16→reg0, resubmit(,1)

Table 5 (MAC Learning - STATIC rule, creates DYNAMIC entry):
  Match: * ✓
  Actions:
    learn(table=6, eth_dst=bb:bb:bb:bb:bb:bb, output:vnet1)
    resubmit(,6)
  
  → Creates DYNAMIC flow in table 6:
      table=6,eth_dst=bb:bb:bb:bb:bb:bb,actions=output:vnet1

Table 6 (MAC Forwarding - checking DYNAMIC entries):
  Match: eth_dst=aa:aa:aa:aa:aa:aa ✓
  (This was learned in Step 1!)
  Actions: output:vnet0
  
Packet delivered to VM1!
```

---

**Step 3: VM1 sends actual data packet to VM2**

```
Packet: IP packet to 10.0.1.20

Processing:

Table 0: in_port=vnet0 → load:15→reg0, resubmit(,1)

Table 5 (MAC Learning):
  Refreshes MAC aa:aa:aa:aa:aa:aa → vnet0 (reset timeout)
  resubmit(,6)

Table 6 (MAC Forwarding - DYNAMIC entry from Step 2):
  Match: eth_dst=bb:bb:bb:bb:bb:bb ✓
  Actions: output:vnet1
  
Packet delivered directly to VM2!
NO flooding, NO controller query
```

---

## Why Hybrid? Why Not Pure Pre-Populated?

### Problem 1: MAC Addresses Change

```
Pure pre-populated approach:

VM boots with MAC aa:bb:cc:dd:ee:ff
Controller installs:
  table=0,eth_dst=aa:bb:cc:dd:ee:ff,actions=output:vnet0

VM restarts with DIFFERENT MAC (aa:bb:cc:dd:ee:01)
  → Old flow doesn't match
  → Packets dropped
  → Must notify controller
  → Controller updates flow
  → Delay: 1-10 seconds

With learning:
  VM boots with new MAC
  → First packet triggers learn action
  → Flow created automatically
  → Delay: ~1 millisecond
```

---

### Problem 2: Scale

```
Pure pre-populated:

Logical switch with 1000 VMs
  → Need 1000 flows for destination lookup
  
10 logical switches × 1000 VMs = 10,000 flows just for MAC forwarding

Add routing, ACLs, tunneling:
  → Hundreds of thousands of flows per host

With learning:
  → Only install flows for active VMs
  → Inactive VMs: no flow
  → Typical: 100-500 active flows
  → 100x reduction
```

---

### Problem 3: Dynamic Environments

```
Kubernetes scenario:

Pod created: 10.0.1.50
  Controller doesn't know immediately
  
Pure pre-populated:
  1. Pod boots
  2. Notify controller (via K8s API)
  3. Controller computes flows
  4. Controller installs flows
  5. Network works
  Time: 5-10 seconds

With learning:
  1. Pod boots
  2. Sends packet
  3. Learn action triggers
  4. Flow created
  5. Network works
  Time: 1 millisecond
```

---

## What Gets Pre-Populated vs Learned?

### Pre-Populated (Slow-Changing, Structural)

```
✓ Logical network topology
  - Which switches exist
  - Which routers exist
  - Port assignments

✓ Routing tables
  - Routes between subnets
  - Default routes
  - Static routes

✓ ACLs and security policies
  - Firewall rules
  - Security group rules
  - QoS policies

✓ Tunnel endpoints
  - Which hosts can tunnel to which
  - Tunnel encapsulation rules

✓ Default behaviors
  - Flood unknown unicast
  - Drop invalid packets
  - Rate limiting
```

---

### Learned (Fast-Changing, Ephemeral)

```
✓ MAC addresses
  - Which MAC on which port
  - Expires if no traffic

✓ ARP cache
  - IP → MAC mappings
  - Expires after timeout

✓ Connection tracking
  - Active TCP connections
  - UDP sessions
  - ICMP flows

✓ Load balancer state
  - Which backend served which connection
  - For connection affinity
```

---

## The OpenFlow "learn" Action in Detail

### Syntax

```bash
learn(
  table=TABLE_ID,           # Which table to install learned flow
  priority=PRIORITY,        # Priority of learned flow
  hard_timeout=SECONDS,     # Absolute expiration time
  idle_timeout=SECONDS,     # Expiration if no traffic
  cookie=VALUE,             # Cookie for tracking
  MATCH_SPEC,               # How to match (built from current packet)
  ACTION_SPEC               # What to do (built from current packet)
)
```

---

### Example: MAC Learning

```bash
table=0,actions=learn(
  table=1,                  # Install in table 1
  priority=100,             # Higher than default
  hard_timeout=300,         # Expire after 5 minutes
  eth_dst=eth_src,          # Match dst MAC = this packet's src MAC
  load:in_port→output_reg   # Action: output to this packet's input port
),resubmit(,1)
```

**Translation:**

```
For packet with:
  eth_src = aa:bb:cc:dd:ee:ff
  in_port = 5

Creates flow in table 1:
  table=1,priority=100,hard_timeout=300,
    eth_dst=aa:bb:cc:dd:ee:ff,
    actions=output:5
```

**English:**
"When you see a packet FROM a MAC address, create a flow so that packets TO that MAC address go to the port we just saw it on."

This is **exactly** what traditional switches do with their MAC learning!

---

### Example: ARP Learning

```bash
table=5,arp,actions=learn(
  table=10,
  priority=100,
  hard_timeout=300,
  eth_type=0x0800,          # Match IPv4 packets
  nw_dst=arp_spa,           # Match IP dst = ARP source IP
  actions=set_field:arp_sha→eth_dst,  # Set dst MAC from ARP
  actions=load:in_port→output_reg     # Output to source port
),normal
```

**For ARP response:**
```
arp_spa = 10.0.1.50 (sender IP)
arp_sha = aa:bb:cc:dd:ee:ff (sender MAC)
in_port = 3

Creates flow in table 10:
  table=10,priority=100,hard_timeout=300,
    eth_type=0x0800,nw_dst=10.0.1.50,
    actions=set_field:aa:bb:cc:dd:ee:ff→eth_dst,output:3
```

**English:**
"When you see an ARP response from IP X with MAC Y on port Z, create a flow so that packets to IP X get MAC Y and go to port Z."

---

## Real OVN Flow Examples

Let's look at actual OVN flows from a running system:

```bash
$ ovs-ofctl dump-flows br-int

# STATIC (pre-installed by ovn-controller):
cookie=0x1234, table=0, priority=100, in_port="vm1"
  actions=load:0x1→NXM_NX_REG0[],resubmit(,1)

cookie=0x1234, table=16, priority=100, metadata=0x5, dl_dst=01:00:00:00:00:00/01:00:00:00:00:00
  actions=flood

# DYNAMIC (created by learn action at runtime):
cookie=0x0, table=71, hard_timeout=300, priority=100, vlan_tci=0x0000/0x1000, dl_dst=aa:bb:cc:dd:ee:ff
  actions=load:0x1→NXM_NX_REG15[],resubmit(,37)

cookie=0x0, table=71, hard_timeout=300, priority=100, vlan_tci=0x0000/0x1000, dl_dst=11:22:33:44:55:66
  actions=load:0x2→NXM_NX_REG15[],resubmit(,37)
```

Notice:
- Static flows have `cookie=0x1234` (set by ovn-controller)
- Dynamic flows have `cookie=0x0` (created by learn)
- Dynamic flows have `hard_timeout=300`

---

## Pure Pre-Populated (Theoretical)

**Could you do PURE pre-populated with NO learning?**

Yes, theoretically:

```
Requirements:
  1. Controller knows EVERY MAC address
  2. Controller notified immediately of ANY change
  3. Controller can update flows in <1ms
  4. Perfect synchronization

Reality:
  - MAC addresses can be spoofed
  - VMs can change MACs
  - Delays in notification
  - Flow updates take 10-1000ms
  - Race conditions

Practical? NO
Used in practice? NO
```

---

## Summary Table

```
┌────────────────────────┬──────────────┬─────────────────┐
│ Aspect                 │ Pre-Populated│ Learned         │
├────────────────────────┼──────────────┼─────────────────┤
│ Logical topology       │ ✓            │                 │
│ Routing tables         │ ✓            │                 │
│ ACLs/policies          │ ✓            │                 │
│ Tunnel endpoints       │ ✓            │                 │
│ MAC addresses          │              │ ✓               │
│ ARP cache              │              │ ✓               │
│ Connection tracking    │              │ ✓               │
│ Unknown handling       │ ✓            │                 │
│                        │              │                 │
│ Update frequency       │ Minutes/hours│ Milliseconds    │
│ Source                 │ Controller   │ Data plane      │
│ Expiration             │ Never/manual │ Timeout-based   │
│ Scale                  │ All possible │ Only active     │
└────────────────────────┴──────────────┴─────────────────┘
```

---

## The Answer to Your Question

**"So there's no learning, just a rules-based FIB that is pre-populated?"**

**Answer:** Not quite. It's a **hybrid FIB**:

1. **Structure is pre-populated** (topology, routing, policies)
2. **MAC addresses are learned** (dynamic, timeout-based)
3. **ARP is learned** (dynamic, timeout-based)
4. **Conntrack is dynamic** (per-connection state)

**Best analogy:**
- Pre-populated = The "compiled code" (routing logic, policies)
- Learned = The "cache" (MAC addresses, ARP, recently-used paths)

The **learning still happens**, but it's implemented **as OpenFlow rules** (using the "learn" action) rather than in fixed switch hardware.

**So:** Rules-based? Yes. Pre-populated? Partially. No learning? No - there IS learning, just implemented differently.

The innovation isn't "no learning" - it's "**programmable learning**" - you can define HOW the switch learns, not just that it learns.
