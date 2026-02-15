---
level: intermediate
estimated_time: 55 min
prerequisites:
  - 02_intermediate/01_advanced_networking/01_vlan_vs_vxlan.md
next_recommended:
  - 05_specialized/02_overlay_networking/01_vxlan_geneve_bgp.md
  - 02_intermediate/02_rdma/01_rdma_fundamentals.md
tags: [networking, vxlan, geneve, overlay, tunneling, encapsulation]
---

# VXLAN and Geneve Deep Dive: L2 Overlay Mechanics

## L3 vs L2 Solutions: The Key Difference

### Why This Matters

**BGP/L3 (Calico in BGP mode):**
```
Pod gets IP: 10.244.1.50
BGP advertises: "Route to 10.244.1.50 via Node1 (192.168.1.10)"
Routing decision: Based on destination IP

Pod moves or restarts:
  - Old IP: 10.244.1.50 → Must withdraw route
  - New IP: 10.244.1.75 → Must advertise new route
  - Convergence time: 3-10 seconds (BGP timers)

Static addressing assumption:
  - Pod keeps same IP during its lifetime
  - IP changes = routing updates required
  - Works well for Kubernetes (IPs stable within pod lifecycle)
```

**VXLAN/Geneve (L2 Overlay):**
```
Pod has MAC: 02:42:0a:f4:01:32
Pod has IP: 10.244.1.50 (but overlay doesn't care!)

VXLAN forwards based on MAC address:
  - Learns "MAC 02:42:0a:f4:01:32 is behind VTEP1"
  - IP can change, MAC typically doesn't
  - Learning is dynamic (like physical switches)
  
Pod moves to different node:
  - MAC address typically stays same
  - VXLAN learns new location automatically
  - Convergence: milliseconds (on first packet)
  - No control plane updates required
```

**Key Insight:** L2 overlays provide **MAC address mobility** - the overlay network doesn't need to know about IP addresses at all. It's a "virtual Ethernet switch" spanning multiple hosts.

---

## VXLAN Forwarding Mechanics

### VTEP Architecture

Every host running VXLAN has a VTEP (VXLAN Tunnel Endpoint):

```
┌─────────────────────────────────────────────────────────┐
│                    Host / Node                          │
│                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │   Pod A    │  │   Pod B    │  │   Pod C    │       │
│  │ MAC: aa:11 │  │ MAC: bb:22 │  │ MAC: cc:33 │       │
│  │ IP: .1.10  │  │ IP: .1.11  │  │ IP: .1.12  │       │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘       │
│        │               │               │               │
│        └───────────────┼───────────────┘               │
│                        │                               │
│               ┌────────▼──────────┐                    │
│               │  Linux Bridge     │                    │
│               │  or OVS           │                    │
│               └────────┬──────────┘                    │
│                        │                               │
│               ┌────────▼──────────┐                    │
│               │  VXLAN Interface  │                    │
│               │  (vxlan0)         │                    │
│               │  VNI: 5000        │                    │
│               └────────┬──────────┘                    │
│                        │                               │
│               ┌────────▼──────────┐                    │
│               │   VTEP Logic      │                    │
│               │ (Kernel module    │                    │
│               │  or User-space)   │                    │
│               └────────┬──────────┘                    │
│                        │                               │
│         ┌──────────────┴──────────────┐               │
│         │                             │               │
│    ┌────▼─────┐                 ┌────▼─────┐         │
│    │   FDB    │                 │   ARP    │         │
│    │ (Forward │                 │  Cache   │         │
│    │  DB)     │                 │          │         │
│    └──────────┘                 └──────────┘         │
│                                                       │
│                 ┌────────────────┐                    │
│                 │ Physical NIC   │                    │
│                 │ (eth0)         │                    │
│                 │ IP: 192.168.1.10                    │
│                 └────────────────┘                    │
└─────────────────────────────────────────────────────┘
```

### The Forwarding Database (FDB)

The VTEP maintains a **forwarding database** mapping MAC addresses to remote VTEP IPs:

```
VNI   Inner MAC         Remote VTEP IP    Port  Age   Flags
───────────────────────────────────────────────────────────
5000  aa:11:22:33:44:55 192.168.1.20      4789  120s  
5000  bb:22:33:44:55:66 192.168.1.20      4789  90s   
5000  cc:33:44:55:66:77 192.168.1.30      4789  45s   
5000  dd:44:55:66:77:88 192.168.1.40      4789  200s  
5001  ee:55:66:77:88:99 192.168.1.25      4789  180s  
```

**You can view this on Linux:**
```bash
# Show VXLAN FDB entries
bridge fdb show dev vxlan0

Output:
aa:11:22:33:44:55 dst 192.168.1.20 self
bb:22:33:44:55:66 dst 192.168.1.20 self
00:00:00:00:00:00 dst 192.168.1.20 via eth0 self permanent
```

---

## VXLAN Learning Methods

### Method 1: Data-Plane Learning (Flood and Learn)

This is how traditional Ethernet switches work, adapted for overlays.

#### Initial State: Empty FDB

```
Host1 (VTEP1: 192.168.1.10):
  - Pod A (MAC: aa:aa:aa:aa:aa:aa, IP: 10.1.1.10)
  - FDB: Empty

Host2 (VTEP2: 192.168.1.20):
  - Pod B (MAC: bb:bb:bb:bb:bb:bb, IP: 10.1.1.20)
  - FDB: Empty
```

#### Step 1: Pod A Sends to Unknown Destination

```
Pod A wants to send to 10.1.1.20 (Pod B)

1. Pod A does ARP for 10.1.1.20
   ARP Request: "Who has 10.1.1.20? Tell aa:aa:aa:aa:aa:aa"
   
2. Frame arrives at VTEP1:
   Src MAC: aa:aa:aa:aa:aa:aa
   Dst MAC: ff:ff:ff:ff:ff:ff (broadcast)
```

#### Step 2: VTEP1 Processes Broadcast

```
VTEP1 Logic:

1. Learn source:
   "MAC aa:aa:aa:aa:aa:aa is LOCAL (directly connected)"
   Store in FDB: aa:aa:aa:aa:aa:aa → LOCAL
   
2. Check destination:
   Dst MAC: ff:ff:ff:ff:ff:ff (broadcast)
   → Must flood to all other VTEPs
   
3. Flood strategies:
   Option A: Multicast
   Option B: Head-End Replication (HER)
   Option C: Controller tells us where to send
```

#### Step 2a: Multicast-Based Flooding

```
VXLAN multicast group: 239.1.1.1 (configured per VNI)

VTEP1 encapsulates ARP request:
  Outer IP Src: 192.168.1.10 (VTEP1)
  Outer IP Dst: 239.1.1.1 (multicast group)
  Outer UDP: Port 4789
  VXLAN: VNI 5000
  Inner Frame: [ARP Request from aa:aa → broadcast]

Network delivers to all VTEPs in multicast group
  → VTEP2 (192.168.1.20) receives
  → VTEP3 (192.168.1.30) receives
  → Etc.
```

#### Step 2b: Head-End Replication (HER)

```
VTEP1 configuration lists all other VTEPs:
  VNI 5000 peers: [192.168.1.20, 192.168.1.30, 192.168.1.40]

VTEP1 creates SEPARATE encapsulated copies:
  Copy 1: Outer IP Dst = 192.168.1.20
  Copy 2: Outer IP Dst = 192.168.1.30  
  Copy 3: Outer IP Dst = 192.168.1.40
  
Sends each copy individually (unicast)

Inefficient but works without multicast support!
```

#### Step 3: VTEP2 Receives and Learns

```
VTEP2 receives encapsulated ARP request:

1. Decapsulate:
   Outer IP Src: 192.168.1.10 (note this!)
   Inner Src MAC: aa:aa:aa:aa:aa:aa (note this!)
   
2. LEARN source mapping:
   "MAC aa:aa:aa:aa:aa:aa is behind VTEP at 192.168.1.10"
   Store in FDB: aa:aa:aa:aa:aa:aa → 192.168.1.10
   
3. Deliver to local bridge:
   Forward ARP request to local pods
```

#### Step 4: Pod B Responds

```
Pod B receives ARP request, sends ARP reply:
  ARP Reply: "10.1.1.20 is at bb:bb:bb:bb:bb:bb"
  
  Ethernet frame:
    Src MAC: bb:bb:bb:bb:bb:bb
    Dst MAC: aa:aa:aa:aa:aa:aa (KNOWN destination!)
```

#### Step 5: VTEP2 Has Learned Destination

```
VTEP2 receives ARP reply from Pod B:

1. Learn source (Pod B):
   bb:bb:bb:bb:bb:bb → LOCAL
   
2. Check destination (Pod A):
   aa:aa:aa:aa:aa:aa → Look up in FDB
   FDB says: "192.168.1.10" (learned in Step 3!)
   
3. Encapsulate directly to VTEP1:
   Outer IP Src: 192.168.1.20
   Outer IP Dst: 192.168.1.10 (UNICAST, no flooding!)
   VXLAN VNI: 5000
   Inner Frame: [ARP Reply bb:bb → aa:aa]
```

#### Step 6: VTEP1 Receives and Completes Learning

```
VTEP1 receives encapsulated ARP reply:

1. Decapsulate:
   Outer IP Src: 192.168.1.20
   Inner Src MAC: bb:bb:bb:bb:bb:bb
   
2. LEARN source mapping:
   "MAC bb:bb:bb:bb:bb:bb is behind VTEP at 192.168.1.20"
   Store in FDB: bb:bb:bb:bb:bb:bb → 192.168.1.20
   
3. Deliver ARP reply to Pod A
```

#### Step 7: Data Flow (Learned State)

```
Now both VTEPs have learned the mapping:

VTEP1 FDB:
  aa:aa:aa:aa:aa:aa → LOCAL
  bb:bb:bb:bb:bb:bb → 192.168.1.20

VTEP2 FDB:
  bb:bb:bb:bb:bb:bb → LOCAL
  aa:aa:aa:aa:aa:aa → 192.168.1.10

Subsequent traffic is UNICAST:
  Pod A → Pod B: Direct encap to 192.168.1.20
  Pod B → Pod A: Direct encap to 192.168.1.10
  
No more flooding!
```

#### Aging and Refresh

```
FDB entries have timers:
  - Default: 300 seconds (5 minutes)
  - Refreshed on each packet from that MAC
  - Expires if no traffic
  
Pod A sends packet to Pod B:
  VTEP1 FDB: bb:bb → 192.168.1.20 (age reset to 0)
  VTEP2 learns: aa:aa → 192.168.1.10 (age reset to 0)

After 5 minutes of silence:
  Entries expire
  Next packet triggers learning again
```

---

### Method 2: Control-Plane Learning (BGP EVPN)

Modern approach: Use BGP to distribute MAC address information.

#### BGP EVPN (Ethernet VPN) Overview

```
Instead of flooding to learn MACs,
use BGP to advertise MAC addresses!

Each VTEP is a BGP speaker:
  - Advertises local MAC addresses
  - Learns remote MAC addresses from BGP
  - Populates FDB from BGP updates
```

#### EVPN Route Types

```
Type 2: MAC/IP Advertisement Route
  - Advertises MAC address
  - Associated IP address (optional)
  - VTEP IP (next hop)
  - VNI (in BGP extended community)

Type 3: Inclusive Multicast Route
  - Advertises VTEP's existence
  - Used for BUM traffic
  - Lists VTEP IP for flooding
```

#### Example: Pod Boots Up

```
Host1, Pod A boots:
  MAC: aa:aa:aa:aa:aa:aa
  IP: 10.1.1.10
  
VTEP1 (192.168.1.10) generates BGP EVPN Type 2 route:
  MAC: aa:aa:aa:aa:aa:aa
  IP: 10.1.1.10
  Next-hop: 192.168.1.10 (VTEP1 IP)
  Extended Community: VNI 5000
  Route Distinguisher: 192.168.1.10:5000

BGP advertises to route reflector:
  VTEP1 → RR: "I have MAC aa:aa:aa:aa:aa:aa for VNI 5000"
  
Route reflector reflects to all other VTEPs:
  RR → VTEP2, VTEP3, VTEP4, ...: Type 2 route
```

#### Remote VTEP Processes Route

```
VTEP2 receives BGP EVPN Type 2 route:

1. Extract information:
   MAC: aa:aa:aa:aa:aa:aa
   VNI: 5000
   Remote VTEP: 192.168.1.10
   
2. Program FDB:
   "For VNI 5000, MAC aa:aa:aa:aa:aa:aa is at 192.168.1.10"
   
   $ bridge fdb show dev vxlan0
   aa:aa:aa:aa:aa:aa dst 192.168.1.10 self

3. Program ARP cache (optional):
   IP: 10.1.1.10
   MAC: aa:aa:aa:aa:aa:aa
   
   $ ip neigh show
   10.1.1.10 dev vxlan0 lladdr aa:aa:aa:aa:aa:aa PERMANENT
```

#### Advantages of BGP EVPN

```
✓ No flooding for learning
  - BGP distributes MAC info proactively
  - Immediate knowledge of all MACs
  
✓ Faster convergence
  - BGP update ~1 second
  - Data-plane learning: first packet flooded
  
✓ Better control
  - Policies can filter MACs
  - Route reflectors scale well
  
✓ ARP suppression
  - VTEP can respond to ARP locally
  - No need to send ARP across network

✗ More complex
  - Requires BGP infrastructure
  - Additional protocol to manage
```

#### BGP EVPN Packet Flow

```
Pod A (10.1.1.10) wants to reach Pod B (10.1.1.20):

WITHOUT EVPN (traditional):
  1. Pod A sends ARP for 10.1.1.20
  2. VTEP1 floods ARP to all VTEPs
  3. VTEP2 delivers to Pod B
  4. Pod B responds
  5. VTEP learns mapping
  6. Data flows

WITH EVPN:
  1. VTEP1 already knows from BGP:
     10.1.1.20 → MAC bb:bb:bb:bb:bb:bb → VTEP 192.168.1.20
  
  2. Pod A sends ARP for 10.1.1.20
  
  3. VTEP1 responds LOCALLY:
     "10.1.1.20 is at bb:bb:bb:bb:bb:bb"
     (ARP suppression - never hits network!)
  
  4. Pod A sends data to bb:bb:bb:bb:bb:bb
  
  5. VTEP1 encapsulates directly to 192.168.1.20
     (No flooding, instant unicast)
```

---

### Method 3: Controller-Based Learning

Used by SDN controllers (VMware NSX, OpenStack Neutron, etc.)

```
Centralized controller maintains mapping:
  
  Controller Database:
  ┌──────────────┬─────────────────┬──────────────┐
  │ MAC          │ VNI             │ VTEP IP      │
  ├──────────────┼─────────────────┼──────────────┤
  │ aa:aa:aa:aa  │ 5000            │ 192.168.1.10 │
  │ bb:bb:bb:bb  │ 5000            │ 192.168.1.20 │
  │ cc:cc:cc:cc  │ 5001            │ 192.168.1.30 │
  └──────────────┴─────────────────┴──────────────┘

When VM/Pod boots:
  1. Hypervisor/Host notifies controller
  2. Controller updates database
  3. Controller pushes FDB entries to VTEPs
  
When VM/Pod moves:
  1. Old host notifies controller (VM gone)
  2. New host notifies controller (VM arrived)
  3. Controller updates ALL VTEPs
  4. Convergence: seconds (controller processing time)
```

---

## BUM Traffic Handling

**BUM = Broadcast, Unknown unicast, Multicast**

### Challenge

```
Pod A sends broadcast (e.g., ARP):
  - Must reach ALL pods in the VNI
  - Could be on ANY host
  - Need efficient distribution
```

### Solution 1: Multicast

```
Configuration:
  VNI 5000 → Multicast group 239.1.1.1
  
All VTEPs for VNI 5000 join multicast group:
  VTEP1, VTEP2, VTEP3 → Join 239.1.1.1
  
Broadcast from Pod A:
  VTEP1 encapsulates with:
    Outer Dst IP: 239.1.1.1 (multicast)
    
  Network delivers to all group members:
    VTEP1, VTEP2, VTEP3 all receive (including sender!)
    
  Each VTEP decapsulates and delivers locally
```

**Linux Configuration:**
```bash
# Create VXLAN interface with multicast
ip link add vxlan0 type vxlan \
  id 5000 \
  dev eth0 \
  group 239.1.1.1 \
  dstport 4789

# VTEP automatically joins multicast group
```

**Pros:**
- Efficient (one packet on the wire per link)
- Native network feature
- Scales well

**Cons:**
- Requires multicast-capable network
- Many cloud providers don't support multicast
- Multicast routing complexity

### Solution 2: Head-End Replication (HER)

```
Static list of all VTEPs:
  VNI 5000 peers: [192.168.1.20, 192.168.1.30, 192.168.1.40]
  
Broadcast from Pod A:
  VTEP1 creates separate copy to each peer:
    Copy 1: Outer Dst IP = 192.168.1.20
    Copy 2: Outer Dst IP = 192.168.1.30
    Copy 3: Outer Dst IP = 192.168.1.40
  
  Sends N unicast packets (N = number of peers)
```

**Linux Configuration:**
```bash
# Create VXLAN with unicast mode
ip link add vxlan0 type vxlan \
  id 5000 \
  dev eth0 \
  dstport 4789 \
  nolearning

# Manually add FDB entries for flooding
bridge fdb append 00:00:00:00:00:00 dev vxlan0 dst 192.168.1.20
bridge fdb append 00:00:00:00:00:00 dev vxlan0 dst 192.168.1.30
bridge fdb append 00:00:00:00:00:00 dev vxlan0 dst 192.168.1.40

# 00:00:00:00:00:00 = default entry for unknown/broadcast
```

**Pros:**
- Works everywhere (no multicast required)
- Simple configuration

**Cons:**
- Inefficient (N packets for N peers)
- Sender bandwidth bottleneck
- Doesn't scale well (>100 peers)

### Solution 3: BGP EVPN Ingress Replication

```
BGP EVPN Type 3 route advertises VTEP capabilities:

VTEP1 sends Type 3:
  "I am VTEP 192.168.1.10 for VNI 5000"
  
All other VTEPs learn:
  "For VNI 5000, replicate BUM traffic to 192.168.1.10"
  
Dynamic peer list (vs static HER):
  - VTEPs automatically learn peers from BGP
  - Add/remove VTEPs: BGP updates handle it
  - No manual FDB configuration
```

---

## Geneve Differences

### Geneve vs VXLAN Forwarding

**VXLAN:** Always Ethernet in Ethernet
```
Outer [Eth | IP | UDP | VXLAN] Inner [Eth | IP | TCP | Data]
                                      ^^^^^^^^^
                                      Always present
```

**Geneve:** Flexible inner protocol
```
Protocol Type = 0x6558 (Transparent Ethernet):
  Outer [Eth | IP | UDP | Geneve] Inner [Eth | IP | TCP | Data]
                                        ^^^^^^^^^^^^
  
Protocol Type = 0x0800 (IPv4):
  Outer [Eth | IP | UDP | Geneve] Inner [IP | TCP | Data]
                                        ^^^^^^^
                                        No inner Ethernet!
                                        Saves 14 bytes
```

### Geneve Learning with Options

```
Standard FDB (like VXLAN):
  VNI   MAC            VTEP IP
  5000  aa:aa:aa:aa    192.168.1.20

Enhanced with Geneve options:
  VNI   MAC            VTEP IP       Security-Group  QoS
  5000  aa:aa:aa:aa    192.168.1.20  sg-12345        high
  5000  bb:bb:bb:bb    192.168.1.30  sg-67890        low

Forwarding decision can include metadata!
```

### Example: Security Group Option

```
Pod A (security-group: web) sends to Pod B:

Geneve encapsulation includes option:
  Option Class: 0x0100 (vendor-specific)
  Option Type: 0x01 (security group)
  Data: 12345 (web group ID)

VTEP2 receives and checks:
  1. Decapsulate
  2. Extract security group: 12345
  3. Check policy: "group 12345 can talk to local pods?"
  4. If yes: deliver
     If no: drop
  
Policy enforcement in the overlay!
```

---

## Linux Kernel Implementation

### VXLAN Device Creation

```bash
# Create VXLAN interface
ip link add vxlan0 type vxlan \
  id 5000 \              # VNI
  dev eth0 \             # Physical device
  local 192.168.1.10 \   # Local VTEP IP
  dstport 4789           # VXLAN port

# Options:
  learning \             # Enable MAC learning (default)
  nolearning \           # Disable (use static FDB)
  proxy \                # Enable ARP proxy
  l2miss \               # Notify on L2 miss
  l3miss \               # Notify on L3 miss
  ageing 300 \           # FDB aging time (seconds)
  group 239.1.1.1 \      # Multicast group
  ttl 64                 # Outer IP TTL
```

### FDB Management

```bash
# View FDB
bridge fdb show dev vxlan0

# Add static entry
bridge fdb add aa:bb:cc:dd:ee:ff dev vxlan0 dst 192.168.1.20

# Add default entry (for flooding)
bridge fdb append 00:00:00:00:00:00 dev vxlan0 dst 192.168.1.20

# Delete entry
bridge fdb del aa:bb:cc:dd:ee:ff dev vxlan0

# Flush all learned entries
bridge fdb flush dev vxlan0
```

### Packet Flow in Kernel

```
Outbound (Pod → Network):

1. Pod generates packet:
   [Eth: aa:aa → bb:bb | IP: 10.1.1.10 → 10.1.1.20 | TCP | Data]

2. Packet enters veth pair, routed to bridge:
   Bridge determines: "bb:bb is on vxlan0"

3. VXLAN device (vxlan0) receives:
   Kernel checks FDB: "bb:bb → dst 192.168.1.20"

4. Kernel encapsulates:
   - Allocates new skb (socket buffer)
   - Adds VXLAN header (VNI: 5000)
   - Adds UDP header (src port: random, dst: 4789)
   - Adds IP header (src: 192.168.1.10, dst: 192.168.1.20)
   - Adds Ethernet header

5. Passes to physical NIC (eth0)

6. NIC transmits to network


Inbound (Network → Pod):

1. NIC receives packet:
   [Eth | IP(192.168.1.20→192.168.1.10) | UDP(4789) | VXLAN(5000) | Inner...]

2. Kernel IP stack processes:
   Destination port: 4789 → VXLAN handler

3. VXLAN module processes:
   - Validates VXLAN header
   - Checks VNI: 5000 → Maps to vxlan0 device
   - Extracts inner frame
   - Learns source: Inner src MAC → Outer src IP

4. VXLAN device (vxlan0) receives inner frame:
   Delivers to bridge

5. Bridge forwards to correct veth/pod
```

---

## Performance Characteristics

### CPU Overhead

**Encapsulation/Decapsulation Cost:**
```
Modern CPUs (per packet):
  Encapsulation: ~50-100 CPU cycles
  Decapsulation: ~50-100 CPU cycles
  
At 10Gbps with 1500-byte packets:
  PPS: ~800,000 packets/second
  CPU cycles: 800K × 100 = 80M cycles/sec
  On 2GHz CPU: ~4% of one core
  
Actually measured: 5-10% CPU overhead vs native
```

**Factors:**
- Checksum calculation (can offload to NIC)
- Memory allocation for encap header
- FDB lookups (hash table: O(1))
- Routing table lookups

### Hardware Offload

Modern NICs support VXLAN offload:

```
Without Offload:
  CPU calculates checksums
  CPU does segmentation (TSO/GSO)
  CPU reassembly

With Offload (e.g., Intel X710, Mellanox ConnectX):
  NIC calculates outer/inner checksums
  NIC does VXLAN-aware TSO/GSO
  NIC strips VXLAN header on receive
  
Result: Near-native performance
```

**Check offload support:**
```bash
ethtool -k eth0 | grep vxlan

tx-udp_tnl-segmentation: on
tx-udp_tnl-csum-segmentation: on
rx-vxlan-hw: on
```

### Memory Overhead

**FDB Size:**
```
Per entry: ~100 bytes (including kernel structures)

For 10,000 MACs:
  FDB size: 10,000 × 100 bytes = ~1 MB
  
Negligible in modern systems
```

### Latency

```
Encapsulation/Decapsulation latency:
  Typical: 10-50 microseconds
  Modern hardware offload: <5 microseconds
  
Compared to end-to-end latency (ms), usually negligible
```

---

## VXLAN vs Geneve Performance

```
Minimal packet (no options):
  VXLAN: 50 bytes overhead
  Geneve: 50 bytes overhead
  Performance: Identical

With Geneve options:
  Geneve: 50 + option bytes overhead
  More CPU to parse options
  Typically: 5-10% slower than VXLAN
  
But: Future NICs will offload Geneve options
Hardware support improving rapidly
```

---

## Real-World Example: Flannel VXLAN

### Flannel VXLAN Configuration

```yaml
# Flannel ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: kube-flannel-cfg
data:
  net-conf.json: |
    {
      "Network": "10.244.0.0/16",
      "Backend": {
        "Type": "vxlan",
        "VNI": 1,
        "Port": 8472,
        "DirectRouting": false
      }
    }
```

### Resulting Linux Configuration

```bash
# Flannel creates:
ip link show flannel.1

flannel.1@NONE: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1450
    link/ether 8a:63:5e:7c:3a:8d brd ff:ff:ff:ff:ff:ff
    vxlan id 1 local 192.168.1.10 dev eth0 srcport 0 0 dstport 8472

# Bridge for pod connectivity
ip link show cni0

cni0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1450
    link/ether 0a:58:0a:f4:01:01 brd ff:ff:ff:ff:ff:ff
```

### FDB Population

```bash
# Flannel populates FDB via Kubernetes watch:

# Watch Kubernetes nodes
# When new node appears with pod CIDR:
#   - Extract node IP
#   - Add FDB entry

bridge fdb show dev flannel.1

# Node2: 10.244.1.0/24 → 192.168.1.20
00:00:00:00:00:00 dst 192.168.1.20 via eth0 self permanent

# Node3: 10.244.2.0/24 → 192.168.1.30  
00:00:00:00:00:00 dst 192.168.1.30 via eth0 self permanent
```

### Packet Flow Example

```
Pod on Node1 (10.244.0.5) → Pod on Node2 (10.244.1.10):

1. Pod generates IP packet
   [IP: 10.244.0.5 → 10.244.1.10 | TCP | Data]

2. Pod network namespace routing:
   ip route: 10.244.1.0/24 via 10.244.0.1 dev eth0
   (10.244.0.1 is cni0 bridge)

3. Packet arrives at cni0 bridge

4. Bridge routing decision:
   Destination: 10.244.1.10
   Next hop: flannel.1 interface

5. flannel.1 (VXLAN) encapsulates:
   FDB lookup: 10.244.1.0/24 → 192.168.1.20
   (Flannel uses /24 subnet forwarding, not MAC)
   
   Encap:
     Outer Src: 192.168.1.10
     Outer Dst: 192.168.1.20
     UDP Port: 8472
     VNI: 1
     Inner: [Original IP packet]

6. Send via eth0 to Node2

7. Node2 receives, VXLAN decapsulates

8. Delivers to cni0 → pod network namespace
```

---

## Key Takeaways

1. **L2 Overlays provide MAC mobility**
   - IPs can change, MACs typically don't
   - Dynamic learning vs static BGP routes
   - Better for ephemeral workloads

2. **Learning Methods:**
   - Data-plane (flood-and-learn): Simple, works everywhere
   - Control-plane (BGP EVPN): Efficient, no flooding
   - Controller-based: Centralized, policy-rich

3. **BUM Traffic:**
   - Multicast: Efficient but needs network support
   - HER: Works everywhere but doesn't scale
   - BGP EVPN: Best of both worlds

4. **Performance:**
   - 5-10% CPU overhead typical
   - Hardware offload → near-native performance
   - Geneve slightly slower but more flexible

5. **Geneve advantages:**
   - Extensible metadata (security, QoS)
   - IP-only encap option (save 14 bytes)
   - Future of overlays

The key insight: **VXLAN/Geneve are "virtual wires"** that make a distributed system look like one big Ethernet switch, with all the dynamic learning properties that implies.
