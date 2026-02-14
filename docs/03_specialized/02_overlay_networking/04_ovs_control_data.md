---
level: specialized
estimated_time: 50 min
prerequisites:
  - 02_intermediate/01_advanced_networking/02_overlay_mechanics.md
next_recommended:
  - 03_specialized/02_overlay_networking/05_ovs_cilium_geneve.md
tags: [networking, ovs, sdn, control-plane, data-plane, openflow]
---

# What Open vSwitch Actually Does: Control vs Data Plane

## The Confusion: Centralized vs Distributed

You're absolutely right to question this. Let me clarify the distinction:

**Control Plane:** CENTRALIZED (ovn-northd, databases)
**Data Plane:** DISTRIBUTED (OVS on each host)

---

## The Two Planes Explained

### Control Plane (Centralized)

```
┌─────────────────────────────────────────┐
│     Northbound Database (Central)       │
│  "I want logical switch 'web' with     │
│   ACL: allow web→db on port 5432"      │
└──────────────┬──────────────────────────┘
               │
      ┌────────▼────────┐
      │  ovn-northd     │  ← Central "compiler"
      │  (Controller)   │     Runs on 1-3 servers
      └────────┬────────┘
               │
               │ Computes flows for each host
               │
┌──────────────▼──────────────────────────┐
│     Southbound Database (Central)       │
│  "Host1: Install these OpenFlow rules" │
│  "Host2: Install these OpenFlow rules" │
│  "Host3: Install these OpenFlow rules" │
└─────────────────────────────────────────┘
```

**What happens here:**
1. User defines logical topology (northbound)
2. ovn-northd "compiles" it into concrete flows
3. Flows stored in southbound database
4. Each host downloads its flows

**This is centralized** - ovn-northd does the "thinking"

---

### Data Plane (Distributed)

```
Host 1:                Host 2:                Host 3:
┌──────────┐          ┌──────────┐          ┌──────────┐
│ VM1      │          │ VM3      │          │ VM4      │
└────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │
┌────▼─────────────────────▼─────────────────────▼────┐
│           OVS Flow Tables (Pre-programmed)          │
│                                                      │
│  Table 0: If from VM1, goto table 1                │
│  Table 1: If dst=VM4, tunnel to Host3              │
│  Table 2: If dst=VM3, output local port            │
│  ...                                                 │
│                                                      │
│  NO COMMUNICATION WITH CONTROLLER FOR FORWARDING!   │
└──────────────────────────────────────────────────────┘
```

**What happens here:**
1. Packet arrives at OVS
2. OVS looks up pre-installed flows (local decision)
3. OVS forwards based on flows
4. **No controller involvement**

**This is distributed** - each OVS makes independent forwarding decisions

---

## What OVS Actually Does

### OVS Components on Each Host

```
┌─────────────────────────────────────────────────┐
│              Host / Hypervisor                  │
│                                                 │
│  ┌──────────┐  ┌──────────┐                   │
│  │   VM1    │  │   VM2    │                   │
│  └─────┬────┘  └─────┬────┘                   │
│        │ vnet0       │ vnet1                   │
│        │             │                         │
│  ┌─────▼─────────────▼──────────────────┐     │
│  │      Open vSwitch Bridge             │     │
│  │                                      │     │
│  │  ┌────────────────────────────────┐ │     │
│  │  │   Flow Tables (OpenFlow)       │ │     │
│  │  │                                │ │     │
│  │  │ Table 0: Ingress Pipeline      │ │     │
│  │  │   Priority 100:                │ │     │
│  │  │   match: in_port=vnet0         │ │     │
│  │  │   actions: load:15→reg0,       │ │     │
│  │  │            resubmit(,1)        │ │     │
│  │  │                                │ │     │
│  │  │ Table 1: ACL                   │ │     │
│  │  │   Priority 1000:               │ │     │
│  │  │   match: reg0=15,ip,          │ │     │
│  │  │          nw_dst=10.0.2.0/24   │ │     │
│  │  │   actions: resubmit(,2)        │ │     │
│  │  │                                │ │     │
│  │  │ Table 2: L2 Lookup             │ │     │
│  │  │   Priority 50:                 │ │     │
│  │  │   match: eth_dst=aa:bb:cc:..  │ │     │
│  │  │   actions: output:tunnel_port  │ │     │
│  │  │                                │ │     │
│  │  │ Table 3: Routing               │ │     │
│  │  │ Table 4: Output                │ │     │
│  │  │ ...                            │ │     │
│  │  └────────────────────────────────┘ │     │
│  │                                      │     │
│  │  ┌────────────────────────────────┐ │     │
│  │  │   Connection Tracking (Local)  │ │     │
│  │  │   - Track TCP connections      │ │     │
│  │  │   - Stateful firewall          │ │     │
│  │  └────────────────────────────────┘ │     │
│  └──────────────────────────────────────┘     │
│                                                │
│  ┌──────────────────────────────────────┐     │
│  │   ovn-controller (Local Agent)       │     │
│  │   - Reads Southbound DB              │     │
│  │   - Programs OVS flows               │     │
│  │   - Monitors local VMs               │     │
│  └──────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

---

## The Complete Flow: Control → Data Plane

### Step 1: User Creates Logical Network (Control Plane)

```
User: "Create logical switch 'web' with subnet 10.0.1.0/24"

Northbound DB stores:
  Logical Switch: web
    Subnet: 10.0.1.0/24
    Ports:
      - web-vm1 (on Host1)
      - web-vm2 (on Host1)
      - web-vm3 (on Host2)
```

### Step 2: Central Controller Compiles (Control Plane)

```
ovn-northd reads Northbound DB:
  "Logical switch 'web' has 3 ports across 2 hosts"

ovn-northd computes flows for each host:

For Host1:
  "If packet from web-vm1 (port 15):
     - Apply switch 'web' rules
     - If destination is web-vm2: output local port
     - If destination is web-vm3: tunnel to Host2"

For Host2:
  "If packet from web-vm3 (port 23):
     - Apply switch 'web' rules
     - If destination is web-vm1 or web-vm2: tunnel to Host1"

Stores in Southbound DB:
  Host1_flows: [flow1, flow2, flow3, ...]
  Host2_flows: [flow4, flow5, flow6, ...]
```

### Step 3: Local Agents Install Flows (Control Plane → Data Plane)

```
Host1:
  ovn-controller reads Southbound DB
  Sees: "Here are your flows"
  Programs OVS:
    $ ovs-ofctl add-flow br-int "table=0,priority=100,in_port=15,actions=..."
    $ ovs-ofctl add-flow br-int "table=1,priority=1000,reg0=15,ip,nw_dst=10.0.2.0/24,actions=..."
    ...

Host2:
  ovn-controller reads Southbound DB
  Sees: "Here are your flows"
  Programs OVS:
    $ ovs-ofctl add-flow br-int "table=0,priority=100,in_port=23,actions=..."
    ...

Now OVS has all flows installed LOCALLY
```

### Step 4: Packet Forwarding (Data Plane - FULLY DISTRIBUTED)

```
VM1 (Host1) sends packet to VM3 (Host2):

┌─────────────────────────────────────────────────────┐
│ Step 1: Packet enters OVS on Host1                 │
├─────────────────────────────────────────────────────┤
│ in_port: vnet0 (VM1)                               │
│ eth_dst: VM3's MAC                                  │
│ ip_dst: 10.0.1.30                                   │
└─────────────────────────────────────────────────────┘

OVS Flow Processing (Host1 - ALL LOCAL):

Table 0 (Ingress):
  Match: in_port=vnet0 ✓
  Actions: 
    - load:15→reg0  (store logical port 15 in register)
    - load:5→reg1   (store logical datapath 5)
    - resubmit(,1)  (goto table 1)

Table 1 (Port Security):
  Match: reg0=15 ✓
  Actions:
    - Check source MAC/IP (anti-spoofing)
    - resubmit(,2)

Table 2 (ACL):
  Match: reg0=15, ip, nw_dst=10.0.1.0/24 ✓
  Actions:
    - Check policy (allow web→web)
    - resubmit(,3)

Table 3 (L2 Lookup):
  Match: eth_dst=VM3_MAC ✓
  Actions:
    - load:23→reg2  (destination is logical port 23)
    - resubmit(,4)

Table 4 (Destination Lookup):
  Match: reg2=23 ✓
  Actions:
    - Destination is remote (on Host2)
    - load:192.168.1.2→tun_dst (Host2 IP)
    - resubmit(,5)

Table 5 (Output):
  Match: tunnel destination set ✓
  Actions:
    - set_field:5→tun_id (VNI/datapath ID)
    - output:geneve_sys_6081

┌─────────────────────────────────────────────────────┐
│ Step 2: OVS encapsulates with Geneve               │
├─────────────────────────────────────────────────────┤
│ Outer IP: 192.168.1.1 → 192.168.1.2               │
│ Geneve VNI: 5                                       │
│ Geneve Options:                                     │
│   - Logical Datapath: 5                            │
│   - Logical Input Port: 15                         │
│   - Logical Output Port: 23                        │
│   - Pipeline Stage: 5 (output stage)               │
│ Inner Packet: [VM1 → VM3 original packet]         │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Step 3: Packet arrives at Host2                    │
├─────────────────────────────────────────────────────┤
│ OVS receives Geneve packet                         │
│ Decapsulates, reads options:                       │
│   - Datapath: 5                                    │
│   - Input Port: 15                                 │
│   - Output Port: 23                                │
│   - Stage: 5                                       │
└─────────────────────────────────────────────────────┘

OVS Flow Processing (Host2 - ALL LOCAL):

Table 0 (Geneve Ingress):
  Match: tun_id=5, from tunnel ✓
  Actions:
    - load:5→reg1   (logical datapath from tunnel)
    - load:15→reg0  (logical input port from option)
    - load:23→reg2  (logical output port from option)
    - load:5→reg3   (pipeline stage from option)
    - resubmit(,5)  (resume at stage 5)

Table 5 (Output - resumed):
  Match: reg2=23 ✓
  Actions:
    - output:vnet1  (VM3's local port)

┌─────────────────────────────────────────────────────┐
│ Step 4: VM3 receives packet                        │
├─────────────────────────────────────────────────────┤
│ Original packet delivered!                          │
└─────────────────────────────────────────────────────┘

CRITICAL OBSERVATION:
  - NO communication with ovn-northd
  - NO communication with databases
  - ALL decisions made from LOCAL flow tables
  - 100% distributed forwarding
```

---

## What Geneve Options Enable

### Without Geneve Options (Theoretical)

```
Packet arrives at Host2:
  OVS sees: "Geneve packet, VNI 5"
  
Problems:
  ✗ Which logical port did it come from? (Don't know)
  ✗ Where in the pipeline should I resume? (Don't know)
  ✗ What was the original output port? (Don't know)
  ✗ What connection tracking zone? (Don't know)

OVS would need to:
  - Query central controller: "Where did this packet come from?"
  - Controller responds: "Port 15, resume at stage 5"
  - Massive performance bottleneck
  - Central controller becomes single point of failure
  
Result: DOESN'T SCALE
```

### With Geneve Options (Actual OVN)

```
Packet arrives at Host2:
  OVS sees: "Geneve packet with options"
  
Reads options:
  ✓ Input port: 15
  ✓ Output port: 23
  ✓ Datapath: 5
  ✓ Pipeline stage: 5
  ✓ Conntrack zone: 1234
  
OVS can immediately:
  ✓ Resume pipeline at correct stage
  ✓ Apply correct ACLs
  ✓ Use correct conntrack zone
  ✓ Deliver to correct local port
  
Result: SCALES TO THOUSANDS OF HOSTS
```

---

## The Key Insight

### Centralized Control, Distributed Data

```
┌────────────────────────────────────────────────┐
│         CONTROL PLANE (Centralized)            │
│                                                │
│  ovn-northd (runs once, computes all flows)   │
│      ↓                                         │
│  Southbound DB (stores flows for each host)   │
└─────────────────┬──────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
    ┌────▼────┐       ┌───▼────┐
    │ Host1   │       │ Host2  │
    │         │       │        │
    │  OVS    │       │  OVS   │
    └─────────┘       └────────┘
    
    DATA PLANE (Distributed)
    - Each OVS has complete local flows
    - Forward based on local tables
    - Use Geneve options for context
    - NO runtime dependency on controller
```

**Analogy:**

**Traditional networking (fully distributed):**
```
Each router runs BGP, OSPF
Makes independent decisions
No central coordination
```

**Traditional SDN (centralized data plane - BAD):**
```
Controller makes EVERY forwarding decision
Switches ask controller for each packet
Doesn't scale
```

**OVN (hybrid - GOOD):**
```
Controller computes flows ONCE
Installs them on all switches
Switches forward independently
Scales well
```

---

## When Does OVS Talk to the Controller?

### Ongoing Communication

```
ovn-controller (on each host) periodically:
  - Monitors Southbound DB for changes
  - Watches for new VMs/ports
  - Updates flows when topology changes
  
Frequency: Every few seconds
Purpose: Sync configuration, not forwarding
```

### Flow Installation

```
New VM boots on Host1:
  1. ovn-controller notices (via libvirt)
  2. Updates Northbound DB: "New port on logical switch"
  3. ovn-northd recomputes flows
  4. Updates Southbound DB
  5. All ovn-controllers read changes
  6. Each OVS installs new flows
  
This takes: 1-5 seconds
But existing traffic: Unaffected
```

### Slow Path (Rare)

```
Packet arrives with unknown destination:
  OVS flow miss → upcall to ovs-vswitchd
  ovs-vswitchd might consult controller
  Or just drop/flood
  
This is RARE:
  - Only for first packet of new destination
  - Or misconfigured flows
  - Normal operation: All flows pre-installed
```

---

## OVS Performance Characteristics

### Fast Path (Normal Operation)

```
Packet processing:
  1. Arrives at NIC
  2. OVS kernel module
  3. Exact-match cache lookup
  4. Forward based on cached action
  
Speed: Line rate (10-40 Gbps)
Latency: <10 microseconds
CPU: <5% per 10Gbps
```

### Slow Path (Rare)

```
Cache miss:
  1. Upcall to user space (ovs-vswitchd)
  2. Flow table lookup
  3. Install flow in cache
  4. Return to kernel
  5. Forward packet
  
Speed: ~20,000 packets/sec
Latency: 100-500 microseconds
Only happens once per flow
```

---

## Summary: What OVS Actually Does

**At System Start:**
1. ovn-controller connects to Southbound DB
2. Downloads all flows for this host
3. Programs OVS with OpenFlow commands
4. OVS now has complete forwarding rules

**During Packet Forwarding:**
1. Packet arrives
2. OVS matches against local flow tables
3. Executes actions (forward, tunnel, drop)
4. Uses Geneve options for distributed context
5. **NO controller interaction**

**On Topology Change:**
1. ovn-controller notices change
2. Queries Southbound DB for new flows
3. Adds/removes flows in OVS
4. Packet forwarding continues (existing flows still work)

**The Magic:**
- Control plane IS centralized (ovn-northd computes)
- Data plane IS distributed (OVS forwards independently)
- Geneve options carry context between hosts
- Scales to thousands of hosts and millions of flows

**Best Analogy:**

Think of ovn-northd like a **compiler**:
- You write high-level code (logical networks)
- Compiler translates to machine code (OpenFlow rules)
- Each CPU runs its own machine code independently
- No runtime dependency on compiler

OVN is the same:
- You define logical topology
- ovn-northd compiles to OpenFlow
- Each OVS runs its OpenFlow independently
- No runtime dependency on ovn-northd

The Geneve options are like **function parameters** - they carry the context needed for distributed execution.
