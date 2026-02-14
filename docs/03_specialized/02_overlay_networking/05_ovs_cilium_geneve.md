---
level: specialized
estimated_time: 55 min
prerequisites:
  - 02_intermediate/01_advanced_networking/02_overlay_mechanics.md
  - 03_specialized/02_overlay_networking/04_ovs_control_data.md
next_recommended:
  - 03_specialized/02_overlay_networking/06_openflow_precompile.md
tags: [networking, ovs, cilium, geneve, kubernetes, ebpf]
---

# Geneve with Open vSwitch and Cilium: Deep Dive

## Part 1: Open vSwitch and Datacenter SDN

### What is Open vSwitch (OVS)?

**Open vSwitch** is a production-quality, multilayer virtual switch designed to enable network automation through programmatic extension while supporting standard management interfaces and protocols.

**Translation:** It's a software switch that runs on Linux that you can control programmatically.

---

### Traditional Switching vs Software Switching

#### Traditional Physical Switch

```
┌─────────────────────────────────────────────┐
│         Physical Switch (Hardware)           │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Control Plane (CPU)                │   │
│  │  - Learning MAC addresses           │   │
│  │  - Running STP                      │   │
│  │  - Management (CLI, SNMP)           │   │
│  └──────────────┬──────────────────────┘   │
│                 │                           │
│  ┌──────────────▼──────────────────────┐   │
│  │  Data Plane (ASIC)                  │   │
│  │  - Line-rate forwarding             │   │
│  │  - MAC table lookup                 │   │
│  │  - VLAN tagging                     │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  Port1  Port2  Port3  Port4  ...  Port48   │
└────┬─────┬─────┬─────┬──────────────┬──────┘
     │     │     │     │              │
   Server1 Server2 Server3         Server48
```

**Characteristics:**
- Fixed port count (24/48 ports)
- Hardware-based (ASIC)
- Configuration via CLI/SNMP
- Limited programmability

---

#### Software Switch (Linux Bridge)

```
┌──────────────────────────────────────────┐
│           Linux Host                     │
│                                          │
│  ┌───────────┐  ┌───────────┐           │
│  │   VM 1    │  │   VM 2    │           │
│  └─────┬─────┘  └─────┬─────┘           │
│        │ vnet0        │ vnet1            │
│        │              │                  │
│  ┌─────▼──────────────▼────────┐        │
│  │    Linux Bridge (br0)       │        │
│  │    - Simple L2 forwarding   │        │
│  │    - MAC learning           │        │
│  │    - Basic features         │        │
│  └────────────┬────────────────┘        │
│               │ eth0                     │
│               │                          │
└───────────────┼──────────────────────────┘
                │
          Physical Network
```

**Limitations:**
- Simple L2 forwarding only
- No advanced features (QoS, mirroring, tunneling)
- Not programmable
- Limited flow control

---

#### Open vSwitch

```
┌──────────────────────────────────────────────────────┐
│                  Linux Host                          │
│                                                      │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐       │
│  │   VM 1    │  │   VM 2    │  │   Pod A   │       │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘       │
│        │ vnet0        │ vnet1        │ veth0        │
│        │              │              │              │
│  ┌─────▼──────────────▼──────────────▼──────────┐  │
│  │          Open vSwitch Bridge                  │  │
│  │                                               │  │
│  │  Flow Tables (OpenFlow):                     │  │
│  │  ┌──────────────────────────────────────┐   │  │
│  │  │ Table 0: Port Security               │   │  │
│  │  ├──────────────────────────────────────┤   │  │
│  │  │ Table 1: MAC Learning                │   │  │
│  │  ├──────────────────────────────────────┤   │  │
│  │  │ Table 2: L2 Forwarding               │   │  │
│  │  ├──────────────────────────────────────┤   │  │
│  │  │ Table 3: L3 Routing                  │   │  │
│  │  ├──────────────────────────────────────┤   │  │
│  │  │ Table 4: Tunneling (VXLAN/Geneve)    │   │  │
│  │  └──────────────────────────────────────┘   │  │
│  │                                               │  │
│  │  Features:                                    │  │
│  │  - OpenFlow 1.0-1.5                          │  │
│  │  - VXLAN/Geneve/GRE tunnels                 │  │
│  │  - QoS (rate limiting, policing)            │  │
│  │  - Port mirroring (SPAN)                    │  │
│  │  - NetFlow/sFlow                            │  │
│  │  - ACLs                                      │  │
│  │  - Bond/LACP                                 │  │
│  └───────────────────┬───────────────────────────┘  │
│                      │ eth0                         │
│                      │                              │
└──────────────────────┼──────────────────────────────┘
                       │
                 Physical Network
```

**Key advantages:**
- Programmable via OpenFlow
- Advanced tunneling (VXLAN, Geneve, GRE)
- Per-flow QoS and ACLs
- Network virtualization
- Standard management (OVSDB)

---

### OVS Architecture

```
┌─────────────────────────────────────────────────────┐
│                 User Space                          │
│                                                     │
│  ┌─────────────────┐      ┌──────────────────┐    │
│  │  ovs-vswitchd   │◄────►│   ovsdb-server   │    │
│  │  (Daemon)       │      │   (Database)     │    │
│  │                 │      │                  │    │
│  │ - Flow mgmt     │      │ - Bridge config  │    │
│  │ - OpenFlow      │      │ - Port config    │    │
│  │ - Slow path     │      │ - Controller IPs │    │
│  └────────┬────────┘      └──────────────────┘    │
│           │                                        │
│           │ Netlink                                │
├───────────┼────────────────────────────────────────┤
│           │              Kernel Space              │
│  ┌────────▼────────────────────────────┐          │
│  │   OVS Kernel Module                 │          │
│  │   (openvswitch.ko)                  │          │
│  │                                     │          │
│  │  ┌──────────────────────────────┐  │          │
│  │  │   Fast Path (Data Plane)     │  │          │
│  │  │   - Exact match cache        │  │          │
│  │  │   - Line-rate forwarding     │  │          │
│  │  │   - Tunneling                │  │          │
│  │  └──────────────────────────────┘  │          │
│  │                                     │          │
│  │  ┌──────────────────────────────┐  │          │
│  │  │   Slow Path (Upcalls)        │  │          │
│  │  │   - Miss cache → User space  │  │          │
│  │  │   - New flows → Learn        │  │          │
│  │  └──────────────────────────────┘  │          │
│  └─────────────────────────────────────┘          │
└───────────────────────────────────────────────────┘
```

**Components:**

**ovs-vswitchd:**
- Main OVS daemon
- Implements switching logic
- Handles OpenFlow protocol
- Manages slow path

**ovsdb-server:**
- Configuration database
- Stores bridge/port/controller config
- OVSDB protocol for management

**Kernel module:**
- Fast path for line-rate forwarding
- Exact-match cache
- Upcalls to user space on miss

---

### Software-Defined Networking (SDN)

#### The Big Idea

**Traditional Networking:**
```
Each switch is autonomous:
  ┌──────────┐
  │ Switch 1 │  ← Control Plane (makes decisions)
  │          │  ← Data Plane (forwards packets)
  └────┬─────┘
       │
  ┌────┴─────┐
  │ Switch 2 │  ← Control Plane (makes decisions)
  │          │  ← Data Plane (forwards packets)
  └──────────┘

Each switch:
  - Runs spanning tree
  - Learns MAC addresses
  - Makes independent decisions
  
Distributed decision-making
```

**SDN:**
```
Centralized control:
       ┌──────────────────┐
       │   SDN Controller │  ← Centralized Control Plane
       │   (Centralized)  │     (makes ALL decisions)
       └─────────┬────────┘
                 │
         ┌───────┼───────┐
         │       │       │
    ┌────▼───┐ ┌▼────┐ ┌▼────┐
    │Switch 1│ │SW 2 │ │SW 3 │  ← Data Plane only
    │  (FWD) │ │(FWD)│ │(FWD)│     (forward packets)
    └────────┘ └─────┘ └─────┘

Switches:
  - Just forward based on flow tables
  - Don't make decisions
  - Controller programs them
  
Centralized decision-making
```

---

#### OpenFlow Protocol

**The Language of SDN:**

Controller tells switch what to do via OpenFlow messages:

```
Flow Entry:
┌─────────────────────────────────────────────────┐
│ Match Fields:                                   │
│   in_port=1, eth_src=aa:bb:cc:dd:ee:ff         │
│   eth_type=0x0800, ip_dst=10.1.1.10            │
├─────────────────────────────────────────────────┤
│ Actions:                                        │
│   set_field:eth_dst=11:22:33:44:55:66          │
│   output:port=2                                 │
├─────────────────────────────────────────────────┤
│ Counters:                                       │
│   packets=1337, bytes=1337000                  │
└─────────────────────────────────────────────────┘

Translation:
  If packet arrives on port 1
  From MAC aa:bb:cc:dd:ee:ff
  Going to IP 10.1.1.10
  Then:
    Change destination MAC to 11:22:33:44:55:66
    Send out port 2
```

**OpenFlow gives controller full control:**
- Define arbitrary forwarding rules
- Modify packet headers
- Implement custom routing logic
- Create virtual networks

---

### Datacenter SDN Architecture

```
┌────────────────────────────────────────────────────┐
│              Management/Orchestration              │
│         (OpenStack, Kubernetes, vCenter)           │
└────────────────────┬───────────────────────────────┘
                     │ REST API
           ┌─────────▼──────────┐
           │  SDN Controller    │
           │  (OpenDaylight,    │
           │   ONOS, OVN)       │
           └─────────┬──────────┘
                     │ OpenFlow / OVSDB
      ┌──────────────┼──────────────┐
      │              │              │
┌─────▼─────┐  ┌────▼─────┐  ┌────▼─────┐
│  Host 1   │  │  Host 2  │  │  Host 3  │
│           │  │          │  │          │
│  ┌─────┐  │  │  ┌─────┐ │  │  ┌─────┐ │
│  │ OVS │  │  │  │ OVS │ │  │  │ OVS │ │
│  └──┬──┘  │  │  └──┬──┘ │  │  └──┬──┘ │
└─────┼─────┘  └─────┼────┘  └─────┼────┘
      │              │              │
      └──────────────┴──────────────┘
           Physical Network
```

**Benefits:**
1. **Centralized policy** - Define once, deploy everywhere
2. **Network automation** - API-driven provisioning
3. **Multi-tenancy** - Isolated virtual networks
4. **Visibility** - Central view of all traffic
5. **Agility** - Change network without touching switches

---

## OVN (Open Virtual Network)

### What is OVN?

**OVN = Open Virtual Network**

Built on top of OVS to provide **distributed virtual networking** for cloud environments.

**Think of it as:**
- AWS VPC / Azure VNet / GCP VPC
- But open-source
- For private cloud / Kubernetes

---

### OVN Architecture

```
┌───────────────────────────────────────────────────┐
│          Cloud Management System (CMS)            │
│        (OpenStack, Kubernetes, etc.)              │
└──────────────────┬────────────────────────────────┘
                   │ CMS Plugin
         ┌─────────▼──────────┐
         │   OVN Northbound   │  ← Logical network definition
         │      Database      │     (Virtual switches, routers)
         └─────────┬──────────┘
                   │
         ┌─────────▼──────────┐
         │   ovn-northd       │  ← Translates logical → physical
         │   (Controller)     │
         └─────────┬──────────┘
                   │
         ┌─────────▼──────────┐
         │   OVN Southbound   │  ← Physical network flows
         │      Database      │     (Per-hypervisor flows)
         └─────────┬──────────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
┌─────▼─────┐┌────▼─────┐┌────▼─────┐
│  Host 1   ││  Host 2  ││  Host 3  │
│           ││          ││          │
│ ovn-ctrl  ││ ovn-ctrl ││ ovn-ctrl │  ← Local agent
│     ↓     ││     ↓    ││     ↓    │
│   OVS     ││   OVS    ││   OVS    │
└───────────┘└──────────┘└──────────┘
```

**Components:**

**Northbound DB:**
- Logical network definition
- What the user wants
- Virtual switches, routers, ACLs
- High-level abstractions

**ovn-northd:**
- Central brain
- Translates logical → physical
- Computes flows for each host

**Southbound DB:**
- Physical network flows
- How to implement logical network
- OpenFlow rules for each OVS

**ovn-controller:**
- Local agent on each host
- Reads Southbound DB
- Programs local OVS
- Implements tunnels

---

### OVN Logical Topology

```
User defines logical networks:

┌────────────────────────────────────────────────┐
│         Logical Network (Tenant A)             │
│                                                │
│  ┌──────────────────────────────────────┐     │
│  │    Logical Switch "web"              │     │
│  │    Subnet: 10.0.1.0/24               │     │
│  │                                      │     │
│  │  [VM1]  [VM2]  [VM3]                │     │
│  └──────────────┬───────────────────────┘     │
│                 │                             │
│  ┌──────────────▼───────────────────────┐     │
│  │    Logical Router "router1"          │     │
│  └──────────────┬───────────────────────┘     │
│                 │                             │
│  ┌──────────────▼───────────────────────┐     │
│  │    Logical Switch "db"               │     │
│  │    Subnet: 10.0.2.0/24               │     │
│  │                                      │     │
│  │  [VM4]  [VM5]                        │     │
│  └──────────────────────────────────────┘     │
└────────────────────────────────────────────────┘

This is stored in Northbound DB
```

---

### OVN Physical Realization

```
OVN translates to physical implementation:

Host 1:                Host 2:                Host 3:
┌──────────┐          ┌──────────┐          ┌──────────┐
│  VM1     │          │  VM3     │          │  VM4     │
│ (web)    │          │ (web)    │          │ (db)     │
└────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │
┌────▼─────────────────────▼─────────────────────▼────┐
│         Geneve Tunnels with Options                 │
│                                                      │
│  Geneve Header + Options:                           │
│    - Logical Datapath ID: 5 (web switch)           │
│    - Logical Datapath ID: 6 (db switch)            │
│    - Logical Datapath ID: 10 (router1)             │
│    - Pipeline Stage: 0-15                          │
│    - Conntrack Zone: 1-65535                       │
└──────────────────────────────────────────────────────┘

Physical network sees:
  Geneve packets between hosts
  But OVN creates illusion of logical switches/routers!
```

---

### How OVN Uses Geneve Options

#### Option 1: Logical Datapath ID

**Purpose:** Identify which logical switch/router packet is traversing

```
Geneve Option:
  Class: 0x0101 (OVS/OVN)
  Type: 0x00 (Logical Datapath)
  Data: 32-bit datapath ID

Example:
  Datapath ID 5 = Logical Switch "web"
  Datapath ID 6 = Logical Switch "db"
  Datapath ID 10 = Logical Router "router1"

Receiving host reads option:
  "This packet is on logical switch 5 (web)"
  Applies rules for that logical switch
```

---

#### Option 2: Logical Input/Output Ports

**Purpose:** Track which logical port packet entered/exited

```
Geneve Options:
  Logical Input Port: 15 (VM1's port)
  Logical Output Port: 23 (VM3's port)

Receiving host knows:
  "Packet came from VM1 (port 15)"
  "Destined for VM3 (port 23)"
  
Applies port-specific policies:
  - Security groups
  - QoS
  - ACLs
```

---

#### Option 3: Logical Pipeline Stage

**Purpose:** Track position in distributed pipeline

```
OVN has multi-stage packet pipeline:
  Stage 0: Port security (ingress)
  Stage 1: Pre-ACL
  Stage 2: ACL
  Stage 3: QoS
  Stage 4: Load balancing
  Stage 5: Stateful processing
  ...
  Stage 15: Output

Geneve Option:
  Pipeline Stage: 4
  
Meaning: "I'm at load balancing stage"

Receiving host continues from stage 4:
  Doesn't re-process stages 0-3
  Stateful pipeline across multiple hosts!
```

---

#### Option 4: Connection Tracking State

**Purpose:** Distributed stateful firewall

```
Geneve Option:
  Conntrack Zone: 1234
  Conntrack State: ESTABLISHED

Host 1: VM1 initiates connection
  Creates conntrack entry in zone 1234
  Marks as NEW
  
Sends to Host 2 with Geneve option:
  Zone: 1234
  State: NEW
  
Host 2: VM3 receives
  Reads Geneve option
  Knows connection state
  Applies stateful firewall rules
  
Return traffic:
  Zone: 1234
  State: ESTABLISHED
  
Stateful firewall WITHOUT centralized state!
```

---

### Complete OVN Packet Flow Example

```
Scenario: VM1 (Host 1) sends packet to VM4 (Host 3)
  VM1 in "web" logical switch (10.0.1.10)
  VM4 in "db" logical switch (10.0.2.10)
  Must traverse logical router

Step 1: VM1 sends packet
┌─────────────────────────────────────────┐
│ Eth: src=VM1_MAC, dst=router_MAC       │
│ IP:  src=10.0.1.10, dst=10.0.2.10      │
│ Data                                    │
└─────────────────────────────────────────┘

Step 2: OVS on Host 1 processes
  - Match: From VM1 (logical port 15)
  - Lookup: Datapath 5 (web switch)
  - Action: Route to datapath 10 (router)
  - Stage: 0 → 1 → 2 → ... → 5 (routing)
  
Step 3: Routing decision
  - Destination: 10.0.2.10 → datapath 6 (db switch)
  - Next hop: VM4 (logical port 42)
  - Rewrite: dst_mac = VM4_MAC
  
Step 4: Determine physical location
  - VM4 is on Host 3
  - Need to tunnel
  
Step 5: Encapsulate with Geneve + Options
┌─────────────────────────────────────────────────┐
│ Outer Ethernet: Host1_MAC → Host3_MAC          │
├─────────────────────────────────────────────────┤
│ Outer IP: 192.168.1.1 → 192.168.1.3           │
├─────────────────────────────────────────────────┤
│ UDP: 6081                                       │
├─────────────────────────────────────────────────┤
│ Geneve Header:                                  │
│   VNI: 0 (OVN doesn't use VNI)                 │
├─────────────────────────────────────────────────┤
│ Geneve Options:                                 │
│   [Option 1]                                    │
│     Class: 0x0101 (OVN)                        │
│     Type: 0x00 (Logical Datapath)              │
│     Data: Datapath ID = 6 (db switch)          │
│   [Option 2]                                    │
│     Class: 0x0101 (OVN)                        │
│     Type: 0x01 (Logical Input Port)            │
│     Data: Port = 15 (VM1)                      │
│   [Option 3]                                    │
│     Class: 0x0101 (OVN)                        │
│     Type: 0x02 (Logical Output Port)           │
│     Data: Port = 42 (VM4)                      │
│   [Option 4]                                    │
│     Class: 0x0101 (OVN)                        │
│     Type: 0x03 (Pipeline Stage)                │
│     Data: Stage = 8 (post-routing)             │
│   [Option 5]                                    │
│     Class: 0x0101 (OVN)                        │
│     Type: 0x04 (Conntrack Zone)                │
│     Data: Zone = 5, State = NEW                │
├─────────────────────────────────────────────────┤
│ Inner Ethernet: router_MAC → VM4_MAC           │
├─────────────────────────────────────────────────┤
│ Inner IP: 10.0.1.10 → 10.0.2.10                │
├─────────────────────────────────────────────────┤
│ Inner TCP/Data                                  │
└─────────────────────────────────────────────────┘

Step 6: Host 3 receives
  - Decapsulates Geneve
  - Reads options:
    - Datapath 6 (db switch)
    - From port 15 (VM1)
    - To port 42 (VM4)
    - Stage 8 (post-routing)
    - Conntrack: NEW connection
    
  - Resumes pipeline at stage 8
  - Applies db switch ACLs
  - Delivers to VM4

Step 7: VM4 receives original packet
┌─────────────────────────────────────────┐
│ Eth: src=router_MAC, dst=VM4_MAC       │
│ IP:  src=10.0.1.10, dst=10.0.2.10      │
│ Data                                    │
└─────────────────────────────────────────┘

From VM4's perspective: 
  Looks like normal routed packet!
  No idea it traversed physical network
```

---

### Why Geneve Options Are Essential for OVN

**Without options (plain VXLAN):**
```
Problem 1: Can't do distributed routing
  - Need to know which logical network
  - Need to track pipeline stage
  - Would require centralized state

Problem 2: Can't do stateful firewalls
  - No way to carry conntrack state
  - Would need connection tracking on every host
  - Or centralized firewall (bottleneck)

Problem 3: Can't implement logical topology
  - Just have VNI (network ID)
  - No port information
  - No pipeline state
  - Can't distribute processing
```

**With Geneve options:**
```
✓ Distributed routing (carry datapath ID)
✓ Distributed stateful firewall (carry conntrack)
✓ Distributed pipeline (carry stage)
✓ Complete logical topology (carry port info)
✓ No centralized bottleneck
✓ Scalable to thousands of hosts
```

**Key insight:** Geneve options let OVN implement **stateful, distributed virtual networking** without centralized state. Each packet carries all the context needed for distributed processing.

---

## Part 2: Cilium and eBPF

### What is eBPF?

**eBPF = extended Berkeley Packet Filter**

**Simple explanation:** A way to run sandboxed programs inside the Linux kernel without changing kernel source code or loading kernel modules.

---

### Traditional Kernel Networking

```
┌───────────────────────────────────────────────┐
│              User Space                       │
│                                               │
│  Application → socket() → send() → recv()     │
└───────────────────┬───────────────────────────┘
                    │ System call
┌───────────────────▼───────────────────────────┐
│              Kernel Space                     │
│                                               │
│  ┌─────────────────────────────────────┐     │
│  │     Netfilter / iptables            │     │
│  │  ┌────────────────────────────┐     │     │
│  │  │ 10,000 iptables rules      │     │     │
│  │  │ (linear scan, slow)        │     │     │
│  │  └────────────────────────────┘     │     │
│  └─────────────────────────────────────┘     │
│                    ↓                          │
│  ┌─────────────────────────────────────┐     │
│  │     Network Stack                   │     │
│  │  - TCP/IP processing                │     │
│  │  - Routing decisions                │     │
│  │  - Connection tracking              │     │
│  └─────────────────────────────────────┘     │
│                    ↓                          │
│  ┌─────────────────────────────────────┐     │
│  │     Driver                          │     │
│  └─────────────────────────────────────┘     │
└───────────────────┬───────────────────────────┘
                    │
              ┌─────▼─────┐
              │    NIC    │
              └───────────┘

Problems:
  - iptables slow (10K+ rules)
  - Can't easily add new features
  - Kernel modules risky (crash kernel)
  - No visibility into decisions
```

---

### eBPF Kernel Networking

```
┌───────────────────────────────────────────────┐
│              User Space                       │
│                                               │
│  Cilium Agent:                                │
│    - Compiles eBPF programs (C → BPF)         │
│    - Loads into kernel                        │
│    - Manages BPF maps (shared state)          │
└───────────────────┬───────────────────────────┘
                    │
┌───────────────────▼───────────────────────────┐
│              Kernel Space                     │
│                                               │
│  ┌─────────────────────────────────────┐     │
│  │     eBPF Programs (JIT compiled)    │     │
│  │                                     │     │
│  │  [XDP @ NIC]  ← Earliest point      │     │
│  │    - DDoS protection                │     │
│  │    - Load balancing                 │     │
│  │                                     │     │
│  │  [tc @ Device] ← Network device     │     │
│  │    - Policy enforcement             │     │
│  │    - Routing decisions              │     │
│  │    - Connection tracking            │     │
│  │    - Service load balancing         │     │
│  │                                     │     │
│  │  [Socket ops] ← Socket level        │     │
│  │    - Service discovery              │     │
│  │    - Transparent proxy              │     │
│  └─────────────────────────────────────┘     │
│                                               │
│  ┌─────────────────────────────────────┐     │
│  │     eBPF Maps (shared state)        │     │
│  │    - Service endpoints              │     │
│  │    - Policy rules                   │     │
│  │    - Connection tracking            │     │
│  │    - Identity mappings              │     │
│  └─────────────────────────────────────┘     │
│                                               │
│  Traditional Network Stack (mostly bypassed) │
└───────────────────┬───────────────────────────┘
                    │
              ┌─────▼─────┐
              │    NIC    │
              └───────────┘

Benefits:
  - Programmable kernel networking
  - Line-rate performance (JIT to native code)
  - Safe (verified by kernel)
  - No kernel modules needed
  - Rich visibility
```

---

### eBPF Safety and Verification

**Traditional kernel module:**
```
Kernel module can:
  - Crash kernel (oops!)
  - Access any memory
  - Infinite loops
  - Security vulnerabilities

Loading requires root
Extremely dangerous
```

**eBPF program:**
```
Before loading, kernel verifier checks:
  ✓ No infinite loops (bounded execution)
  ✓ No invalid memory access
  ✓ No unsafe pointer arithmetic
  ✓ All code paths return
  ✓ Stack limits respected
  
If verification passes:
  Program is SAFE
  Cannot crash kernel
  JIT compiled to native code
  Runs at near-native speed

If verification fails:
  Rejected
  Never runs
```

---

### What is Cilium?

**Cilium** is a Kubernetes CNI that uses eBPF for networking, security, and observability.

**Key features:**
- eBPF-based networking (no iptables!)
- Identity-based security
- L7 policy enforcement (HTTP, gRPC, Kafka)
- Service mesh without sidecars
- Advanced observability (Hubble)

---

### Cilium Architecture

```
┌───────────────────────────────────────────────────┐
│              Kubernetes Cluster                   │
│                                                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │ Pod A   │  │ Pod B   │  │ Pod C   │          │
│  │Identity:│  │Identity:│  │Identity:│          │
│  │  1234   │  │  5678   │  │  9012   │          │
│  └────┬────┘  └────┬────┘  └────┬────┘          │
│       │ veth       │ veth       │ veth           │
│       │            │            │                │
│  ┌────▼────────────▼────────────▼───────────┐   │
│  │         Linux Network Namespace          │   │
│  │                                           │   │
│  │  eBPF programs attached to veth:         │   │
│  │                                           │   │
│  │  [bpf_lxc] @ veth (per-pod):            │   │
│  │    - Identity-based policy              │   │
│  │    - L3/L4 enforcement                  │   │
│  │    - Connection tracking                │   │
│  │                                           │   │
│  │  [bpf_netdev] @ physical device:        │   │
│  │    - Routing                            │   │
│  │    - Tunneling (VXLAN/Geneve)          │   │
│  │    - Service load balancing             │   │
│  │                                           │   │
│  │  [bpf_host] @ host network:             │   │
│  │    - Host firewall                      │   │
│  │    - NodePort handling                  │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
│  ┌───────────────────────────────────────────┐   │
│  │        Cilium Agent (User Space)          │   │
│  │                                           │   │
│  │  - Compiles eBPF programs                │   │
│  │  - Manages identity store                │   │
│  │  - Syncs with Kubernetes API             │   │
│  │  - Populates eBPF maps                   │   │
│  │  - Implements policy                     │   │
│  └───────────────────────────────────────────┘   │
└───────────────────────────────────────────────────┘
```

---

### Cilium's Identity-Based Security

**Traditional security (IP-based):**
```
Problem: IPs change constantly in Kubernetes
  Pod restarts → New IP
  Rolling update → New IPs
  Scaling → New IPs
  
iptables rules:
  ALLOW 10.244.1.50 → 10.244.2.100 port 80
  
Pod restarts with new IP:
  Rules broken!
  Must update iptables
  Race conditions
  Eventual consistency issues
```

**Cilium security (identity-based):**
```
Each pod gets cryptographic identity:
  frontend pod → Identity 1000
  backend pod → Identity 2000
  database pod → Identity 3000
  
Policy:
  ALLOW identity 1000 → identity 2000 port 80
  ALLOW identity 2000 → identity 3000 port 5432
  
Pod restarts:
  IP changes but identity stays same
  Rules still work!
  No updates needed
```

---

### How Cilium Uses Geneve

**Cilium supports multiple datapaths:**
1. **Direct routing** (no encapsulation, like Calico)
2. **VXLAN** (simple overlay)
3. **Geneve** (overlay with metadata)

**When using Geneve, Cilium carries:**

#### Option 1: Security Identity

```
Geneve Option:
  Class: 0x0104 (Cilium)
  Type: 0x01 (Security Identity)
  Data: 32-bit identity
  
Example:
  Identity 1000 = frontend pods
  
Packet from frontend pod:
  Geneve header + identity option (1000)
  
Receiving node reads identity:
  "This packet is from frontend (1000)"
  Applies policies for identity 1000
  No need to look up source IP!
```

---

#### Option 2: Source Security Identity (for policy)

```
Network policy:
  "Allow frontend (1000) → backend (2000)"
  
Packet arrives with Geneve option:
  Source Identity: 1000
  
eBPF program checks:
  if (source_identity == 1000 && local_pod_identity == 2000)
    → ALLOW
  else
    → DROP
    
Fast, identity-based enforcement
No IP lookup required
```

---

#### Option 3: Encrypted Overlay Identity

```
With WireGuard encryption:
  Geneve carries encrypted identity
  Enables encrypted pod-to-pod communication
  
Option contains:
  Encrypted identity
  Encryption metadata
  
Both encryption AND identity-based policy!
```

---

### Cilium eBPF Programs

#### Program 1: Per-Pod Policy Enforcement

```c
// Simplified eBPF program attached to pod's veth

SEC("tc")
int handle_ingress(struct __sk_buff *skb) {
    // Extract packet info
    void *data = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;
    
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return TC_ACT_SHOT; // Drop
    
    // For Geneve packets, extract identity from option
    u32 src_identity = extract_geneve_identity(skb);
    
    // Get destination pod identity
    u32 dst_identity = get_local_identity();
    
    // Lookup policy
    struct policy_key key = {
        .src_identity = src_identity,
        .dst_identity = dst_identity,
        .dport = get_dport(skb),
    };
    
    struct policy_entry *policy = 
        bpf_map_lookup_elem(&policy_map, &key);
    
    if (policy && policy->action == ALLOW) {
        // L7 policy check (HTTP, gRPC, etc.)
        if (needs_l7_check(policy)) {
            return check_l7_policy(skb, policy);
        }
        return TC_ACT_OK; // Allow
    }
    
    return TC_ACT_SHOT; // Drop
}
```

**This runs for EVERY packet at kernel level!**
- No context switches
- No iptables traversal
- Direct policy enforcement
- Line-rate performance

---

#### Program 2: Service Load Balancing (kube-proxy replacement)

```c
// Simplified eBPF program for service load balancing

SEC("tc")
int handle_service(struct __sk_buff *skb) {
    // Check if destination is a service IP
    u32 service_ip = get_dest_ip(skb);
    
    struct service_info *svc = 
        bpf_map_lookup_elem(&services_map, &service_ip);
    
    if (!svc)
        return TC_ACT_OK; // Not a service, pass through
    
    // Load balance across endpoints
    u32 hash = get_packet_hash(skb);
    u32 endpoint_idx = hash % svc->num_endpoints;
    
    struct endpoint *ep = 
        &svc->endpoints[endpoint_idx];
    
    // DNAT: Rewrite destination
    set_dest_ip(skb, ep->ip);
    set_dest_port(skb, ep->port);
    
    // Update conntrack for reverse NAT
    struct ct_entry ct = {
        .orig_service_ip = service_ip,
        .orig_service_port = get_dest_port(skb),
        .backend_ip = ep->ip,
        .backend_port = ep->port,
    };
    bpf_map_update_elem(&conntrack_map, &ct_key, &ct, BPF_ANY);
    
    return TC_ACT_OK;
}
```

**Replaces kube-proxy entirely!**
- No iptables rules
- Per-packet load balancing
- Faster than iptables (40-50% improvement)
- Scales to thousands of services

---

#### Program 3: L7 Protocol Parsing (HTTP)

```c
// Simplified HTTP parser in eBPF

SEC("tc")
int parse_http(struct __sk_buff *skb) {
    // Read HTTP method
    char method[8];
    bpf_skb_load_bytes(skb, tcp_payload_offset, method, 7);
    
    // Check if GET/POST/PUT/DELETE
    if (is_http_method(method)) {
        // Extract path
        char path[128];
        extract_http_path(skb, path, sizeof(path));
        
        // L7 policy check
        struct l7_policy_key key = {
            .src_identity = get_src_identity(skb),
            .http_method = parse_method(method),
            .http_path = hash_path(path),
        };
        
        struct l7_policy *policy = 
            bpf_map_lookup_elem(&l7_policy_map, &key);
        
        if (policy && policy->action == DENY) {
            // Drop at L7 level
            return TC_ACT_SHOT;
        }
        
        // Record metrics
        update_http_metrics(skb, method, path);
    }
    
    return TC_ACT_OK;
}
```

**This is revolutionary:**
- Parse HTTP at kernel level!
- L7 policy enforcement without proxy
- No sidecar overhead
- Visibility into HTTP traffic

---

### Cilium + Geneve: Complete Flow

```
Scenario: Frontend pod (Identity 1000) → Backend pod (Identity 2000)
  Frontend on Node 1
  Backend on Node 2
  Using Geneve overlay

Step 1: Frontend sends HTTP request
┌────────────────────────────────────┐
│ GET /api/users HTTP/1.1            │
│ Eth: src=frontend_MAC, dst=gw_MAC  │
│ IP: src=10.244.1.10, dst=10.244.2.20│
└────────────────────────────────────┘

Step 2: eBPF @ frontend veth (egress)
  Program: bpf_lxc
  - Identify source: Identity 1000 (frontend)
  - Lookup destination: 10.244.2.20 → Identity 2000 (backend)
  - Policy check:
      src=1000, dst=2000, port=80 → ALLOW
  - L7 policy check:
      Identity 1000 → 2000, GET /api/users → ALLOW
  - Decision: Route to Node 2

Step 3: Encapsulate with Geneve
┌─────────────────────────────────────────┐
│ Outer Eth: Node1_MAC → Node2_MAC       │
├─────────────────────────────────────────┤
│ Outer IP: 192.168.1.1 → 192.168.1.2    │
├─────────────────────────────────────────┤
│ UDP: 6081                               │
├─────────────────────────────────────────┤
│ Geneve Header                           │
│   VNI: 5000 (cluster VNI)              │
├─────────────────────────────────────────┤
│ Geneve Options:                         │
│   [Option 1 - Cilium Identity]         │
│     Class: 0x0104 (Cilium)             │
│     Type: 0x01 (Security Identity)     │
│     Data: 1000 (frontend identity)     │
├─────────────────────────────────────────┤
│ Inner Eth: frontend_MAC → backend_MAC  │
├─────────────────────────────────────────┤
│ Inner IP: 10.244.1.10 → 10.244.2.20    │
├─────────────────────────────────────────┤
│ Inner TCP: port 80                     │
├─────────────────────────────────────────┤
│ Inner HTTP: GET /api/users             │
└─────────────────────────────────────────┘

Step 4: Node 2 receives, eBPF @ physical device
  Program: bpf_netdev
  - Decapsulates Geneve
  - Extracts options:
      Source Identity: 1000
  - Stores in skb metadata for next program

Step 5: eBPF @ backend veth (ingress)
  Program: bpf_lxc
  - Reads identity from metadata: 1000
  - Local pod identity: 2000
  - Policy check:
      src=1000, dst=2000, port=80 → ALLOW
  - L7 policy:
      Identity 1000 → 2000, GET /api/users → ALLOW
  - Decision: ALLOW
  - Update metrics

Step 6: Backend pod receives
┌────────────────────────────────────┐
│ GET /api/users HTTP/1.1            │
│ (Appears to come directly from     │
│  frontend, no proxy in between!)   │
└────────────────────────────────────┘
```

---

### Cilium vs OVN Comparison

```
┌────────────────────────┬────────────────┬─────────────────┐
│ Feature                │ OVN            │ Cilium          │
├────────────────────────┼────────────────┼─────────────────┤
│ Data Plane             │ OVS (kernel)   │ eBPF (kernel)   │
│                        │                │                 │
│ Control Plane          │ Centralized    │ Distributed     │
│                        │ (ovn-northd)   │ (per-node agent)│
│                        │                │                 │
│ Geneve Use             │ Heavy          │ Optional        │
│                        │ (core feature) │ (one option)    │
│                        │                │                 │
│ Geneve Options         │ Many:          │ Few:            │
│                        │ - Datapath ID  │ - Identity      │
│                        │ - Ports        │                 │
│                        │ - Pipeline     │                 │
│                        │ - Conntrack    │                 │
│                        │                │                 │
│ Stateful Firewall      │ Distributed    │ Distributed     │
│                        │ (via Geneve)   │ (via eBPF maps) │
│                        │                │                 │
│ L7 Policy              │ Limited        │ Native (HTTP,   │
│                        │                │ gRPC, Kafka)    │
│                        │                │                 │
│ Service Load Balancing │ Via OVS flows  │ Via eBPF        │
│                        │                │ (kube-proxy     │
│                        │                │  replacement)   │
│                        │                │                 │
│ Identity Model         │ None (IP-based)│ Yes (crypto ID) │
│                        │                │                 │
│ Performance            │ Good           │ Better          │
│                        │ (~20K PPS)     │ (~30K PPS)      │
│                        │                │                 │
│ Complexity             │ Higher         │ Medium          │
│                        │ (many          │ (new tech)      │
│                        │  components)   │                 │
│                        │                │                 │
│ Maturity               │ Very mature    │ Mature          │
│                        │ (10+ years)    │ (5+ years)      │
│                        │                │                 │
│ Use Cases              │ OpenStack      │ Kubernetes      │
│                        │ VMs            │ Cloud-native    │
│                        │ Traditional    │ Modern          │
└────────────────────────┴────────────────┴─────────────────┘
```

---

## Summary

### OVN (Open vSwitch + Geneve)

**What it does:**
- Implements distributed virtual networking
- Creates logical switches and routers
- Spans multiple hosts

**How Geneve helps:**
- Carries logical network context (datapath ID)
- Carries pipeline state (which processing stage)
- Carries connection state (stateful firewall)
- Enables distributed processing without centralized state

**Best for:**
- OpenStack deployments
- VM-based virtualization
- Traditional datacenter SDN

---

### Cilium (eBPF + Geneve)

**What it does:**
- Kubernetes networking via eBPF
- Identity-based security
- L7 policy enforcement
- Service mesh without sidecars

**How Geneve helps:**
- Carries pod identity (for policy enforcement)
- Enables identity-based security across nodes
- Simpler than OVN's use (fewer options)

**Best for:**
- Kubernetes clusters
- Cloud-native applications
- High-performance networking
- Advanced observability

---

### The Common Thread

Both use Geneve to solve the same fundamental problem:
**How do you implement distributed networking features without centralized state?**

**Answer:** Carry the necessary context in the packet itself (via Geneve options)

- OVN: Carries logical topology context
- Cilium: Carries security identity

This enables **stateful, distributed processing** at scale.
