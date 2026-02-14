---
level: reference
estimated_time: 15 min
prerequisites: []
next_recommended: []
tags: [reference, acronyms, glossary, networking, terminology]
---

# Complete Acronym and Terminology Guide

## Core Overlay Networking

### VTEP - VXLAN Tunnel Endpoint
**Full Name:** VXLAN Tunnel Endpoint

**What it is:** 
A software or hardware component that performs VXLAN encapsulation and decapsulation. It's the "gateway" between the overlay network (VXLAN) and the underlay network (physical network).

**Where it lives:**
- Typically runs on each host/node
- Can be in the Linux kernel (most common)
- Can be in user-space (Open vSwitch)
- Can be in a hardware switch/NIC

**What it does:**
```
Outbound:
  - Takes packets from VMs/pods
  - Adds VXLAN header + UDP + IP
  - Sends to remote VTEP

Inbound:
  - Receives encapsulated packets
  - Removes VXLAN header + UDP + IP
  - Delivers to local VMs/pods
```

**Example:**
```
Host1 has VTEP at IP 192.168.1.10
Host2 has VTEP at IP 192.168.1.20

Pod on Host1 → VTEP1 encapsulates → Network → VTEP2 decapsulates → Pod on Host2
```

---

### VXLAN - Virtual Extensible LAN
**Full Name:** Virtual Extensible Local Area Network

**What it is:**
An overlay networking protocol that creates Layer 2 (Ethernet) networks over Layer 3 (IP) infrastructure.

**Key specs:**
- RFC 7348
- Uses UDP port 4789
- 24-bit VNI (16.7 million virtual networks)
- Adds 50 bytes overhead

**Solves:**
- VLAN limitation (4096 max) - VXLAN supports 16M networks
- Multi-tenancy in cloud environments
- Stretching L2 networks across L3 boundaries

---

### VNI - VXLAN Network Identifier
**Full Name:** VXLAN Network Identifier (also called VXLAN Network ID)

**What it is:**
A 24-bit field in the VXLAN header that identifies which virtual network a packet belongs to.

**Think of it as:**
Similar to VLAN ID, but 24 bits instead of 12 bits
- VLAN: 12 bits = 4,096 networks
- VNI: 24 bits = 16,777,216 networks

**Example:**
```
VNI 5000 = Production network
VNI 5001 = Development network  
VNI 5002 = Staging network

Pods in VNI 5000 cannot talk to pods in VNI 5001
(Unless explicitly bridged/routed)
```

---

### TLV - Type-Length-Value
**Full Name:** Type-Length-Value

**What it is:**
A data encoding format where each piece of information is encoded as:
- **Type:** What kind of data this is (e.g., security group, QoS level)
- **Length:** How many bytes the value occupies
- **Value:** The actual data

**Why it's useful:**
Allows extensibility - new types can be added without breaking old parsers.

**Example in Geneve:**
```
Option 1 (Security Group):
  Type: 0x01 (security group)
  Length: 4 bytes
  Value: 0x00003039 (security group ID 12345)

Option 2 (QoS):
  Type: 0x02 (QoS level)
  Length: 1 byte
  Value: 0x05 (priority level 5)

Parser reads Type, knows how many bytes to read (Length), extracts Value
```

**Real-world analogy:**
Like XML or JSON tags:
```
<security-group length="4">12345</security-group>
<qos-level length="1">5</qos-level>
```

---

### FDB - Forwarding Database
**Full Name:** Forwarding Database

**What it is:**
A table that maps MAC addresses to ports/destinations. In VXLAN context, it maps MAC addresses to remote VTEP IP addresses.

**Structure:**
```
VNI    MAC Address        Destination      Port   Age
5000   aa:bb:cc:dd:ee:ff  192.168.1.20    4789   120s
5000   11:22:33:44:55:66  192.168.1.30    4789   90s
```

**Traditional switch FDB:**
```
MAC Address        Port    Age
aa:bb:cc:dd:ee:ff  Port 1  120s
11:22:33:44:55:66  Port 2  90s

"If packet destined for aa:bb:cc:dd:ee:ff, send out Port 1"
```

**VXLAN FDB:**
```
MAC Address        VTEP IP        Age
aa:bb:cc:dd:ee:ff  192.168.1.20  120s

"If packet destined for aa:bb:cc:dd:ee:ff, encapsulate and send to VTEP at 192.168.1.20"
```

---

### BUM - Broadcast, Unknown unicast, Multicast
**Full Name:** Broadcast, Unknown unicast, and Multicast

**What it is:**
Traffic types that need to be sent to multiple destinations (as opposed to unicast which goes to one specific destination).

**Breakdown:**

**Broadcast:**
```
Destination MAC: ff:ff:ff:ff:ff:ff
Example: ARP request "Who has 10.1.1.20?"
Must reach ALL devices in the network
```

**Unknown unicast:**
```
Destination MAC: aa:bb:cc:dd:ee:ff
But switch doesn't know which port/VTEP it's on
Must flood to all ports/VTEPs to find it
```

**Multicast:**
```
Destination MAC: 01:00:5e:xx:xx:xx (multicast MAC)
Example: OSPF routing updates, streaming video
Must reach multiple specific subscribers
```

**Challenge in overlays:**
How to efficiently deliver BUM traffic across VXLAN tunnel?
- Option 1: Multicast (efficient but needs network support)
- Option 2: Head-End Replication (works everywhere but CPU-intensive)
- Option 3: BGP EVPN (best of both)

---

## BGP and Routing

### BGP - Border Gateway Protocol
**Full Name:** Border Gateway Protocol

**What it is:**
The routing protocol of the Internet. Routes traffic between different autonomous systems (ASes).

**Types:**
- **eBGP** (External BGP): Between different ASes
- **iBGP** (Internal BGP): Within the same AS

**Why it's in this discussion:**
- Calico uses BGP to advertise pod routes
- BGP EVPN extends BGP to carry MAC addresses (for VXLAN)
- Route Reflectors solve BGP scaling problems

---

### AS - Autonomous System
**Full Name:** Autonomous System

**What it is:**
A collection of IP networks and routers under the control of one organization that presents a common routing policy to the Internet.

**Examples:**
- AS 15169 = Google
- AS 16509 = Amazon
- AS 32934 = Facebook
- AS 64512-65534 = Private use (like private IP addresses)

**ASN (Autonomous System Number):**
- 16-bit (original): 1-65535
- 32-bit (modern): 1-4294967295

**In Kubernetes context:**
```
Calico typically uses private AS numbers:
  AS 64512 for all nodes (iBGP)
  or AS 64512, 64513, 64514... (eBGP per rack)
```

---

### RR - Route Reflector
**Full Name:** Route Reflector (in BGP context)

**What it is:**
A BGP router that reflects (redistributes) routes between BGP clients, eliminating the need for full mesh iBGP.

**Problem it solves:**
```
Without RR (full mesh):
  100 routers = 4,950 BGP sessions

With RR:
  100 routers = ~200 sessions (2 RRs × 100 clients)
```

**Not to be confused with:**
Route Reflector in optical networking (different meaning - amplifies light signals)

---

### EVPN - Ethernet VPN
**Full Name:** Ethernet Virtual Private Network

**What it is:**
A BGP extension (RFC 7432) that allows BGP to carry Ethernet/MAC information, not just IP routes.

**Traditional BGP carries:**
```
"Route to 10.1.1.0/24 via next-hop 192.168.1.10"
(IP prefixes)
```

**BGP EVPN carries:**
```
"MAC aa:bb:cc:dd:ee:ff is at VTEP 192.168.1.10 for VNI 5000"
(MAC addresses + VTEP info)
```

**Benefits:**
- Eliminates flooding in VXLAN
- Faster convergence
- Better control plane
- Enables ARP suppression

---

### iBGP and eBGP
**Full Names:** 
- **iBGP:** Internal Border Gateway Protocol
- **eBGP:** External Border Gateway Protocol

**Difference:**

**eBGP:**
- Between different autonomous systems
- AS_PATH incremented on each hop
- Default administrative distance: 20
- Simpler rules

**iBGP:**
- Within the same autonomous system  
- AS_PATH not incremented
- Default administrative distance: 200
- Requires full mesh OR route reflectors OR confederations
- More complex loop prevention

**Example:**
```
     AS 65000              AS 65001
  ┌─────────────┐       ┌─────────────┐
  │  R1 ←iBGP→ R2 ←eBGP→ R3 ←iBGP→ R4 │
  │             │       │             │
  └─────────────┘       └─────────────┘
```

---

### MED - Multi-Exit Discriminator
**Full Name:** Multi-Exit Discriminator

**What it is:**
A BGP attribute used to influence inbound traffic from neighboring AS when there are multiple entry points.

**Use case:**
```
Your AS connects to ISP at two locations:
  Router A in New York
  Router B in Los Angeles

You prefer traffic for West Coast servers to enter via Los Angeles:
  Advertise West Coast routes with MED=100 from LA router
  Advertise West Coast routes with MED=200 from NY router
  
Lower MED = more preferred
```

**Important:**
- Only influences the neighboring AS
- Not carried beyond that AS
- Lower values preferred

---

## Network Technologies

### MTU - Maximum Transmission Unit
**Full Name:** Maximum Transmission Unit

**What it is:**
The largest packet size that can be transmitted on a network without fragmentation.

**Standard values:**
- Ethernet: 1500 bytes
- Jumbo frames: 9000 bytes
- Internet minimum: 576 bytes (IPv4), 1280 bytes (IPv6)

**VXLAN problem:**
```
Physical MTU: 1500 bytes
VXLAN overhead: 50 bytes
Overlay MTU: 1450 bytes (or physical must be 1550+)
```

**Solution options:**
1. Reduce overlay MTU to 1450
2. Increase physical MTU to 1550+ (jumbo frames)
3. Use Path MTU Discovery

---

### PMTUD - Path MTU Discovery
**Full Name:** Path MTU Discovery

**What it is:**
A technique to determine the maximum packet size that can traverse a network path without fragmentation.

**How it works:**
```
1. Send packet with DF (Don't Fragment) bit set
2. If too large, router sends ICMP "Packet Too Big" message
3. Sender reduces packet size
4. Repeat until packet gets through
5. Remember this MTU for the destination
```

**Problems:**
- Some networks block ICMP (breaks PMTUD)
- "PMTUD black hole" - packets silently dropped
- Modern solution: PLPMTUD (Packetization Layer PMTUD)

---

### ECMP - Equal-Cost Multi-Path
**Full Name:** Equal-Cost Multi-Path routing

**What it is:**
A routing strategy where traffic is distributed across multiple paths that have equal cost.

**Example:**
```
Router has 4 equal-cost paths to destination:
  - Path via Interface 1
  - Path via Interface 2  
  - Path via Interface 3
  - Path via Interface 4

Hash on (Src IP, Dst IP, Protocol, Src Port, Dst Port)
Distribute traffic across all 4 paths
```

**VXLAN benefit:**
Random UDP source port ensures good ECMP distribution:
```
Flow 1: UDP src port 50123 → Hash → Interface 1
Flow 2: UDP src port 51984 → Hash → Interface 3
Flow 3: UDP src port 49876 → Hash → Interface 2
```

---

### QoS - Quality of Service
**Full Name:** Quality of Service

**What it is:**
Mechanisms to prioritize certain traffic over others.

**Common mechanisms:**
- **DSCP** (DiffServ Code Point): IP header marking (0-63)
- **CoS** (Class of Service): Ethernet 802.1p (0-7)
- **Queuing**: Priority queues, weighted fair queuing
- **Rate limiting**: Police, shape traffic

**Example:**
```
Voice/Video: DSCP 46 (EF - Expedited Forwarding) - highest priority
Business data: DSCP 34 (AF41) - medium priority  
Best effort: DSCP 0 - lowest priority
```

---

### ToR - Top of Rack
**Full Name:** Top of Rack (switch)

**What it is:**
A network switch installed at the top of a server rack that connects all servers in that rack.

**Architecture:**
```
        ┌─────────┐
        │  Spine  │
        │ Switch  │
        └────┬────┘
             │
     ┌───────┴───────┐
     │               │
┌────▼────┐    ┌────▼────┐
│  ToR    │    │  ToR    │
│ Switch1 │    │ Switch2 │
└────┬────┘    └────┬────┘
     │               │
  ┌──┴──┐         ┌──┴──┐
  │  │  │         │  │  │
  S  S  S         S  S  S
(Servers)      (Servers)
```

**Why it matters:**
- Calico BGP can peer with ToR switches
- Efficient rack-level traffic
- Failure domain isolation

---

## Container and Virtualization

### CNI - Container Network Interface
**Full Name:** Container Network Interface

**What it is:**
A specification and libraries for configuring network interfaces in Linux containers.

**What it defines:**
- How container runtimes (Docker, containerd) call network plugins
- How plugins should configure networking
- JSON configuration format

**Flow:**
```
1. Container runtime (containerd) creates container
2. Calls CNI plugin: "Configure network for this container"
3. CNI plugin:
   - Creates veth pair
   - Configures IP address
   - Sets up routes
   - Returns result to runtime
4. Container has network connectivity
```

**Popular CNI plugins:**
- Calico
- Cilium
- Flannel
- Weave
- Canal (Calico + Flannel)

---

### CRI - Container Runtime Interface  
**Full Name:** Container Runtime Interface

**What it is:**
A plugin interface that enables Kubernetes to use different container runtimes without recompiling.

**Runtimes that implement CRI:**
- containerd
- CRI-O
- Docker (via dockershim, deprecated)

**Why it exists:**
Kubernetes originally only worked with Docker. CRI makes it runtime-agnostic.

---

### CSI - Container Storage Interface
**Full Name:** Container Storage Interface

**What it is:**
A standard for exposing storage systems to container orchestration platforms.

**What it enables:**
```
Kubernetes → CSI Driver → Storage System
  |            |              |
  |            |              ├─ AWS EBS
  |            |              ├─ GCP Persistent Disk
  |            |              ├─ Ceph
  |            |              └─ NFS
  |
  └─ Same K8s storage API for all!
```

**Operations:**
- CreateVolume
- DeleteVolume
- AttachVolume
- MountVolume
- SnapshotVolume

---

### OCI - Open Container Initiative
**Full Name:** Open Container Initiative

**What it is:**
An open governance structure for creating open industry standards around container formats and runtimes.

**Two main specifications:**

**1. Runtime Spec:**
How to run a container (runc implements this)

**2. Image Spec:**
How container images are formatted
```
OCI Image = Filesystem layers + Configuration JSON
```

**Goal:**
Ensure Docker, Podman, containerd can all work with same images and containers.

---

### PV/PVC - Persistent Volume / Persistent Volume Claim
**Full Names:** 
- **PV:** Persistent Volume
- **PVC:** Persistent Volume Claim

**What they are:**

**PV:**
A piece of storage in the cluster (like a disk)
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-1
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/data
```

**PVC:**
A request for storage by a user
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-claim
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

**Relationship:**
```
User creates PVC (request) → Kubernetes binds to PV (actual storage) → Pod uses PVC
```

---

### NUMA - Non-Uniform Memory Access
**Full Name:** Non-Uniform Memory Access

**What it is:**
A memory architecture where memory access time depends on memory location relative to a processor.

**Architecture:**
```
┌─────────┐      ┌─────────┐
│  CPU 0  │      │  CPU 1  │
└────┬────┘      └────┬────┘
     │                │
┌────▼────┐      ┌────▼────┐
│ Memory  │      │ Memory  │
│ Bank 0  │      │ Bank 1  │
└─────────┘      └─────────┘

CPU 0 accessing Bank 0: Fast (local)
CPU 0 accessing Bank 1: Slower (remote, crosses interconnect)
```

**Why it matters for VMs:**
Pin VM to NUMA node for best performance
```
VM with 4 vCPUs:
  Good: All vCPUs on same NUMA node
  Bad: vCPUs split across NUMA nodes (remote memory access)
```

**KVM NUMA awareness:**
```
<numa>
  <cell id='0' cpus='0-3' memory='4194304'/>
</numa>
```

---

## Protocol and Packet Terms

### ARP - Address Resolution Protocol
**Full Name:** Address Resolution Protocol

**What it is:**
Protocol to map IP addresses to MAC addresses on a local network.

**Flow:**
```
Host A (10.1.1.10) wants to talk to Host B (10.1.1.20)
Host A knows IP, needs MAC address

1. Host A broadcasts: "Who has 10.1.1.20? Tell 10.1.1.10"
   (Broadcast to ff:ff:ff:ff:ff:ff)

2. Host B responds: "10.1.1.20 is at MAC aa:bb:cc:dd:ee:ff"
   (Unicast to Host A's MAC)

3. Host A caches: 10.1.1.20 → aa:bb:cc:dd:ee:ff
   (ARP table)

4. Host A can now send packets to Host B
```

**In VXLAN:**
ARP requests must traverse the overlay (BUM traffic)

**With BGP EVPN:**
VTEPs can suppress ARP (answer locally without traversing network)

---

### DHCP - Dynamic Host Configuration Protocol
**Full Name:** Dynamic Host Configuration Protocol

**What it is:**
Protocol for automatically assigning IP addresses and network configuration to devices.

**DORA process:**
```
1. Discover: Client broadcasts "I need an IP"
2. Offer: Server responds "Here's 10.1.1.100"
3. Request: Client broadcasts "I accept 10.1.1.100"
4. Acknowledge: Server confirms "10.1.1.100 is yours"
```

**In containers:**
Usually not used (IPs assigned by CNI plugin directly)

---

### TSO/GSO - TCP Segmentation Offload / Generic Segmentation Offload
**Full Names:**
- **TSO:** TCP Segmentation Offload
- **GSO:** Generic Segmentation Offload

**What they are:**
Features that let the NIC handle packet segmentation instead of the CPU.

**Without TSO/GSO:**
```
Application sends 64KB of data:

CPU creates 44 packets:
  - 44 TCP headers
  - 44 IP headers  
  - 44 Ethernet headers
  - Split data into 1460-byte chunks

CPU intensive!
```

**With TSO/GSO:**
```
Application sends 64KB of data:

CPU creates ONE large packet:
  - 1 TCP header
  - 1 IP header
  - 1 Ethernet header
  - 64KB data

Passes to NIC
NIC splits into 44 packets (hardware does it fast!)
```

**VXLAN TSO:**
Modern NICs can do TSO even with VXLAN encapsulation
```
CPU: Large inner packet
NIC: Segments, then encapsulates each segment
```

---

### RSS - Receive Side Scaling
**Full Name:** Receive Side Scaling

**What it is:**
A NIC feature that distributes received packets across multiple CPU cores.

**Without RSS:**
```
All packets arrive on CPU 0
  - CPU 0: 100% busy
  - CPU 1-7: Idle
  - Bottleneck!
```

**With RSS:**
```
NIC hashes on (Src IP, Dst IP, Src Port, Dst Port)
Routes packets to different queues:
  - Flow 1 → Queue 0 → CPU 0
  - Flow 2 → Queue 1 → CPU 1
  - Flow 3 → Queue 2 → CPU 2
  
Load balanced across CPUs!
```

---

### DSCP - Differentiated Services Code Point
**Full Name:** Differentiated Services Code Point

**What it is:**
A 6-bit field in the IP header used to classify and prioritize packets.

**Location in IP header:**
```
IP Header:
  [Version|IHL|DSCP|ECN|Total Length|...]
              ^^^^
           6 bits (0-63)
```

**Common values:**
```
DSCP  Name   Meaning
0     BE     Best Effort (default)
46    EF     Expedited Forwarding (VoIP)
34    AF41   Assured Forwarding (important data)
48    CS6    Class Selector 6 (network control)
```

**Routers read DSCP:**
```
Packet arrives with DSCP=46 (EF)
Router puts in high-priority queue
Gets forwarded before DSCP=0 packets
```

---

### ICMP - Internet Control Message Protocol  
**Full Name:** Internet Control Message Protocol

**What it is:**
A network layer protocol for error messages and operational information.

**Common uses:**
```
Type 8:  Echo Request (ping)
Type 0:  Echo Reply (ping response)
Type 3:  Destination Unreachable
Type 11: Time Exceeded (traceroute)
Type 12: Parameter Problem

ICMPv6 additionally handles:
  - Neighbor Discovery (replaces ARP)
  - Router Advertisement
```

**PMTUD use:**
```
Type 3, Code 4: Fragmentation needed but DF set
Carries MTU information
```

---

## Storage Terms

### iSCSI - Internet Small Computer Systems Interface
**Full Name:** Internet Small Computer Systems Interface

**What it is:**
A protocol for accessing block storage over IP networks.

**How it works:**
```
Server (Initiator) ←─ iSCSI/IP/Ethernet ─→ Storage Array (Target)

Server sees storage as local disk (e.g., /dev/sdb)
Actually stored on remote array over network
```

**vs NFS:**
- iSCSI: Block-level storage
- NFS: File-level storage

---

### LVM - Logical Volume Manager
**Full Name:** Logical Volume Manager

**What it is:**
A Linux device mapper that provides logical volume management.

**Hierarchy:**
```
Physical Volumes (PV): /dev/sda, /dev/sdb
      ↓
Volume Group (VG): Pools PVs together
      ↓
Logical Volumes (LV): Virtual partitions
      ↓
Filesystem: ext4, xfs, etc.
```

**Benefits:**
- Resize volumes dynamically
- Snapshots
- Spanning disks
- Migration

---

### RAID - Redundant Array of Independent Disks
**Full Name:** Redundant Array of Independent Disks

**What it is:**
Technology to combine multiple disks for redundancy and/or performance.

**Common levels:**
```
RAID 0: Striping (performance, no redundancy)
RAID 1: Mirroring (redundancy, 50% capacity)
RAID 5: Striping + parity (good balance)
RAID 6: Striping + double parity (better redundancy)
RAID 10: Mirroring + striping (best performance + redundancy)
```

---

## Miscellaneous

### SDN - Software-Defined Networking
**Full Name:** Software-Defined Networking

**What it is:**
An approach where network control plane is separated from forwarding plane and is directly programmable.

**Traditional networking:**
```
Each switch: Control plane + Forwarding plane together
Distributed decision making
```

**SDN:**
```
Centralized controller: Control plane (makes decisions)
       ↓
Switches: Forwarding plane only (follow instructions)

OpenFlow, etc.
```

---

### NFV - Network Functions Virtualization
**Full Name:** Network Functions Virtualization

**What it is:**
Moving network functions (firewalls, load balancers, etc.) from dedicated hardware to software running on commodity servers.

**Traditional:**
```
Hardware firewall → Hardware load balancer → Hardware router
Expensive, inflexible
```

**NFV:**
```
VMs/Containers running:
  - Virtual firewall
  - Virtual load balancer  
  - Virtual router
  
On commodity x86 servers
```

---

### SLA - Service Level Agreement
**Full Name:** Service Level Agreement

**What it is:**
A contract defining expected service levels.

**Example metrics:**
```
Uptime: 99.9% (43.8 minutes downtime/month)
Latency: <50ms 95th percentile
Packet loss: <0.1%
Support response: <1 hour
```

---

### MTU and MSS

### MSS - Maximum Segment Size
**Full Name:** Maximum Segment Size

**What it is:**
The largest amount of data in a single TCP segment (not including TCP/IP headers).

**Relationship to MTU:**
```
MTU: 1500 bytes (Ethernet frame)
  - Ethernet header: 14 bytes
  - IP header: 20 bytes
  - TCP header: 20 bytes
  = MSS: 1460 bytes

MTU = MSS + IP header + TCP header
1500 = 1460 + 20 + 20
```

**TCP negotiates MSS:**
```
During TCP handshake:
  SYN: "My MSS is 1460"
  SYN-ACK: "My MSS is 1460"
  
Both sides use minimum (1460)
```

---

## Summary Tables

### Network Layers (OSI Model)

```
Layer 7: Application  (HTTP, DNS, SSH)
Layer 6: Presentation (SSL/TLS, encryption)
Layer 5: Session      (session management)
Layer 4: Transport    (TCP, UDP) ← MSS lives here
Layer 3: Network      (IP, ICMP) ← MTU, DSCP, BGP
Layer 2: Data Link    (Ethernet, MAC) ← VXLAN operates here
Layer 1: Physical     (cables, signals)
```

### Common Port Numbers

```
Port   Protocol     Use
22     SSH          Secure shell
53     DNS          Domain name resolution
80     HTTP         Web traffic
443    HTTPS        Secure web traffic
179    BGP          BGP sessions
4789   VXLAN        VXLAN tunnel
6081   Geneve       Geneve tunnel
8472   Flannel      Flannel VXLAN (custom)
```

### Address Space Sizes

```
MAC address:    48 bits = 281 trillion addresses
IPv4 address:   32 bits = 4.3 billion addresses
IPv6 address:  128 bits = 340 undecillion addresses
VLAN ID:        12 bits = 4,096 VLANs
VNI:            24 bits = 16.7 million VNIs
AS Number:      32 bits = 4.3 billion ASes
```

### Packet Overhead Summary

```
Ethernet header:     14 bytes
IP header:           20 bytes (IPv4), 40 bytes (IPv6)
TCP header:          20 bytes (minimum)
UDP header:           8 bytes
VXLAN header:         8 bytes
Geneve header:        8 bytes (minimum)

Total VXLAN overhead (IPv4):
  14 + 20 + 8 + 8 = 50 bytes
```

This should clear up all the acronyms! Let me know if you need any clarifications.
