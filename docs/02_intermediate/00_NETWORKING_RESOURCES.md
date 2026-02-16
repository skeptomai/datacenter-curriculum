---
title: "Datacenter Networking & Storage Learning Resources"
depth: reference
topic: "Networking, Storage"
---

# Datacenter Networking & Storage Learning Resources 📚

**Comprehensive collection of external resources for datacenter networking, RDMA, and high-performance storage**

This document provides curated resources to complement your datacenter networking and storage learning. Covers spine-leaf architecture, RDMA, overlay networking, SDN, and distributed storage.

> 💡 **Using this guide:**
> - Resources organized by topic matching the networking/storage curriculum
> - Each resource includes difficulty level and learning focus
> - Code repositories marked with ⭐ are especially good for learning
> - Links verified as of 2026-02-15

---

## Table of Contents

1. [Datacenter Network Architecture](#1-datacenter-network-architecture)
2. [RDMA (Remote Direct Memory Access)](#2-rdma-remote-direct-memory-access)
3. [Overlay Networking](#3-overlay-networking)
4. [Software Defined Networking (SDN)](#4-software-defined-networking-sdn)
5. [High-Performance Storage](#5-high-performance-storage)
6. [Network Simulation and Testing](#6-network-simulation-and-testing)
7. [Books and Long-Form Content](#7-books-and-long-form-content)

---

## 1. Datacenter Network Architecture

### Spine-Leaf Architecture

**Tutorials and Guides:**
- **[Understanding Spine-Leaf Network Design](https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/white-paper-c11-737022.html)**
  - Cisco white paper on modern datacenter design
  - Scaling, redundancy, East-West traffic
  - Difficulty: Beginner to Intermediate

- **[Spine-Leaf vs 3-Tier Comparison](https://www.juniper.net/documentation/us/en/software/csrx/csrx-deployment/topics/concept/security-csrx-spine-leaf-overview.html)**
  - Juniper documentation
  - When to use each architecture

**ECMP (Equal-Cost Multi-Path):**
- **[ECMP Deep Dive](https://packetlife.net/blog/2010/oct/4/understanding-equal-cost-multi-path-routing/)**
  - How ECMP distributes traffic
  - Hash-based load balancing

- **[5-Tuple Hashing Explained](https://networkengineering.stackexchange.com/questions/30778/how-does-ecmp-work)**
  - Per-flow vs per-packet load balancing
  - Avoiding packet reordering

### BGP (Border Gateway Protocol)

**Specifications:**
- **[RFC 4271: BGP-4](https://datatracker.ietf.org/doc/html/rfc4271)** ⭐
  - Official BGP specification
  - Path selection, attributes

- **[RFC 7938: BGP EVPN](https://datatracker.ietf.org/doc/html/rfc7938)**
  - Ethernet VPN using BGP
  - Layer 2 over layer 3

**Tutorials:**
- **[BGP for Beginners](https://www.noction.com/blog/bgp-tutorial)**
  - BGP basics, AS numbers, peering

- **[BGP in the Datacenter](https://cumulusnetworks.com/blog/bgp-datacenter/)**
  - Using BGP for spine-leaf routing
  - Alternatives to traditional IGPs

**Route Reflectors:**
- **[BGP Route Reflectors Explained](https://www.cisco.com/c/en/us/support/docs/ip/border-gateway-protocol-bgp/13764-40.html)**
  - Scaling BGP without full mesh
  - Route reflector hierarchies

### Link Technologies

**100G/400G Ethernet:**
- **[IEEE 802.3 Standards](https://www.ieee802.org/3/)**
  - Official Ethernet standards
  - 100GBASE, 400GBASE specifications

- **[Understanding 100G Optics](https://www.fiber-optic-transceiver-module.com/100g-ethernet-migration-path.html)**
  - QSFP28, QSFP-DD transceivers
  - Fiber types and distances

---

## 2. RDMA (Remote Direct Memory Access)

### RDMA Fundamentals

**Specifications:**
- **[InfiniBand Architecture Specification](https://www.infinibandta.org/ibta-specifications-download/)**
  - Official InfiniBand spec (requires registration)
  - Queue pairs, verbs, transport

- **[RoCE (RDMA over Converged Ethernet)](https://www.roceinitiative.org/)**
  - RoCEv1 and RoCEv2 specifications
  - Lossless Ethernet requirements

- **[iWARP Specification](https://datatracker.ietf.org/doc/html/rfc5040)**
  - RFC 5040, 5041, 5042, 5043
  - RDMA over TCP/IP

**Tutorials:**
- **[Introduction to RDMA](https://www.rdmamojo.com/)** ⭐
  - Comprehensive RDMA programming tutorials
  - Example code in C
  - Covers verbs API

- **[RDMA Programming 101](https://insujang.github.io/2020-02-09/introduction-to-programming-infiniband/)**
  - Step-by-step RDMA programming
  - Queue pairs, memory registration, verbs

### RDMA Programming

**Code Repositories:**
- **[rdma-core](https://github.com/linux-rdma/rdma-core)** ⭐
  - Linux RDMA userspace libraries
  - libibverbs, librdmacm
  - Example programs in `libibverbs/examples/`

- **[perftest](https://github.com/linux-rdma/perftest)**
  - RDMA performance testing tools
  - ib_send_bw, ib_read_lat, etc.
  - Good examples of RDMA verbs usage

- **[qperf](https://github.com/linux-rdma/qperf)**
  - Network performance measurement
  - RDMA and TCP/IP benchmarking

**Tutorials:**
- **[RDMA Verbs API Tutorial](https://www.openfabrics.org/images/eventpresos/workshops2013/IBUG/2013_UserDay_Thurs_1700_Verbs-programming.pdf)**
  - OpenFabrics workshop slides
  - Comprehensive verbs programming

- **[RDMA CM (Connection Manager)](https://www.kernel.org/doc/html/latest/infiniband/core_locking.html)**
  - Linux kernel RDMA CM documentation
  - Connection establishment

### Lossless Ethernet (DCB)

**Specifications:**
- **[IEEE 802.1Qbb: Priority Flow Control (PFC)](https://1.ieee802.org/dcb/802-1qbb/)**
  - Pause frames for lossless Ethernet
  - Per-priority flow control

- **[IEEE 802.1Qaz: Enhanced Transmission Selection (ETS)](https://1.ieee802.org/dcb/802-1qaz/)**
  - Bandwidth allocation per priority
  - Traffic classes

**Tutorials:**
- **[Data Center Bridging (DCB) Explained](https://www.intel.com/content/www/us/en/support/articles/000005793/ethernet-products.html)**
  - Intel guide to DCB configuration
  - PFC, ETS, DCBX

- **[Configuring PFC for RoCE](https://enterprise-support.nvidia.com/s/article/howto-configure-pfc-on-connectx-4-connectx-5-adapter)**
  - NVIDIA Mellanox guide
  - Practical PFC setup

### RDMA in Linux

**Documentation:**
- **[Linux RDMA Documentation](https://www.kernel.org/doc/html/latest/infiniband/index.html)**
  - Kernel RDMA subsystem
  - Drivers, verbs, user_mad

**Tools:**
- **[rdma-utils](https://github.com/linux-rdma/rdma-core)**
  - Command-line tools: `ibv_devinfo`, `rdma link show`
  - Configuration and diagnostics

---

## 3. Overlay Networking

### VXLAN (Virtual Extensible LAN)

**Specifications:**
- **[RFC 7348: VXLAN](https://datatracker.ietf.org/doc/html/rfc7348)** ⭐
  - Official VXLAN specification
  - 24-bit VNI, UDP encapsulation

**Tutorials:**
- **[VXLAN Deep Dive](https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/white-paper-c11-729383.html)**
  - Cisco white paper
  - Flood and learn vs BGP EVPN

- **[Linux VXLAN Configuration](https://developers.redhat.com/blog/2018/10/22/introduction-to-linux-interfaces-for-virtual-networking#vxlan)**
  - Hands-on VXLAN setup
  - Using iproute2 tools

**Code Examples:**
- **[Linux Kernel VXLAN Driver](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/vxlan/)**
  - Kernel implementation to study
  - `vxlan_core.c`

### Geneve

**Specifications:**
- **[RFC 8926: Geneve](https://datatracker.ietf.org/doc/html/rfc8926)**
  - Generic Network Virtualization Encapsulation
  - Flexible TLV options

**Tutorials:**
- **[Geneve vs VXLAN](https://www.redhat.com/en/blog/what-geneve)**
  - Red Hat comparison
  - When to use each protocol

### BGP EVPN

**Specifications:**
- **[RFC 7432: BGP MPLS-Based Ethernet VPN](https://datatracker.ietf.org/doc/html/rfc7432)**
  - EVPN control plane
  - MAC/IP advertisement

**Tutorials:**
- **[BGP EVPN Overview](https://www.juniper.net/documentation/us/en/software/junos/evpn-vxlan/topics/concept/evpn-bgp-overview.html)**
  - Juniper documentation
  - EVPN with VXLAN data plane

---

## 4. Software Defined Networking (SDN)

### Open vSwitch (OVS)

**Official Resources:**
- **[Open vSwitch](https://www.openvswitch.org/)** ⭐
  - Production-grade virtual switch
  - OpenFlow, OVSDB

- **[OVS Source Code](https://github.com/openvswitch/ovs)**
  - Well-documented C code
  - Start with `vswitchd/` and `lib/`

**Documentation:**
- **[OVS Documentation](https://docs.openvswitch.org/en/latest/)**
  - Architecture, tutorials, FAQ
  - Comprehensive official docs

**Tutorials:**
- **[OVS Deep Dive](https://arthurchiao.art/blog/ovs-deep-dive-0-overview/)**
  - Multi-part series on OVS internals
  - Architecture, flow tables, kernel module

- **[OVS Hands-On Tutorial](https://github.com/openvswitch/ovs/blob/master/Documentation/tutorials/ovs-advanced.rst)**
  - Official OVS tutorial
  - OpenFlow, VXLAN, QoS

### OVN (Open Virtual Network)

- **[OVN](https://www.ovn.org/)**
  - Network virtualization for OVS
  - Logical switches, routers, load balancers

- **[OVN Architecture](https://www.ovn.org/support/dist-docs/ovn-architecture.7.html)**
  - Northbound/southbound databases
  - Distributed vs centralized

### OpenFlow

**Specifications:**
- **[OpenFlow 1.5 Specification](https://opennetworking.org/software-defined-standards/specifications/)**
  - Open Networking Foundation spec
  - Flow table pipeline

**Tutorials:**
- **[OpenFlow Tutorial](https://github.com/mininet/openflow-tutorial)**
  - Hands-on with Mininet
  - Writing OpenFlow controllers

### Network Testing with Mininet

- **[Mininet](http://mininet.org/)** ⭐
  - Network emulator for SDN testing
  - Create virtual networks on laptop

- **[Mininet Walkthrough](http://mininet.org/walkthrough/)**
  - Official tutorial
  - Custom topologies, OpenFlow controllers

---

## 5. High-Performance Storage

### NVMe-oF (NVMe over Fabrics)

**Specifications:**
- **[NVMe-oF Specification](https://nvmexpress.org/developers/nvme-specification/)**
  - NVMe over RDMA, TCP, FC
  - NVM Express organization

**Tutorials:**
- **[NVMe-oF Introduction](https://www.snia.org/educational-library/introduction-nvme-fabrics-2017)**
  - SNIA presentation
  - Architecture and use cases

- **[Linux NVMe-oF Setup](https://www.kernel.org/doc/html/latest/nvme/nvme-over-fabrics.html)**
  - Kernel documentation
  - Configuring targets and initiators

**Code:**
- **[Linux NVMe Driver](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/nvme)**
  - Kernel NVMe and NVMe-oF implementation
  - `host/` and `target/` directories

### Distributed Storage Systems

**Ceph:**
- **[Ceph](https://github.com/ceph/ceph)** ⭐
  - Distributed object/block/file storage
  - RADOS, RBD, CephFS

- **[Ceph Architecture](https://docs.ceph.com/en/latest/architecture/)**
  - CRUSH algorithm, OSDs, monitors
  - How Ceph achieves distribution

**GlusterFS:**
- **[GlusterFS](https://github.com/gluster/glusterfs)**
  - Distributed file system
  - Scale-out storage

**MinIO:**
- **[MinIO](https://github.com/minio/minio)**
  - High-performance object storage
  - S3-compatible API

### RDMA for Storage

**Tutorials:**
- **[RDMA Benefits for Storage](https://www.mellanox.com/related-docs/whitepapers/WP_RDMA_and_NVMe-oF.pdf)**
  - NVIDIA white paper
  - Why RDMA matters for storage

- **[NVMe-oF over RDMA Performance](https://nvmexpress.org/wp-content/uploads/NVMe-oF-Performance-with-100G-RoCE-LAB-REPORT.pdf)**
  - Performance benchmarks
  - RoCE for NVMe-oF

---

## 6. Network Simulation and Testing

### Network Emulators

**Mininet:**
- **[Mininet](http://mininet.org/)** ⭐
  - Create virtual networks on single machine
  - Test SDN controllers, topologies
  - Python API for custom scenarios

**GNS3:**
- **[GNS3](https://www.gns3.com/)**
  - Graphical network simulator
  - Real vendor images (Cisco, Juniper)
  - Complex topology testing

**Containerlab:**
- **[Containerlab](https://github.com/srl-labs/containerlab)** ⭐
  - Network lab automation with containers
  - Vendor network OS in containers
  - Fast topology deployment

### Traffic Generators

**iperf3:**
- **[iperf3](https://github.com/esnet/iperf)**
  - Network performance testing
  - TCP, UDP, SCTP

**TRex:**
- **[TRex](https://trex-tgn.cisco.com/)** ⭐
  - Realistic traffic generator
  - Stateful, stateless, DPDK-based
  - High packet rates

**pktgen:**
- **[pktgen](https://github.com/pktgen/Pktgen-DPDK)**
  - DPDK-based packet generator
  - Line-rate packet generation

### Packet Capture and Analysis

**tcpdump/Wireshark:**
- **[tcpdump](https://www.tcpdump.org/)**
  - Command-line packet capture
  - Essential debugging tool

- **[Wireshark](https://www.wireshark.org/)**
  - GUI packet analyzer
  - Protocol dissectors for VXLAN, RDMA, etc.

---

## 7. Books and Long-Form Content

### Essential Books

**Datacenter Networking:**
- **"Datacenter Networks" by Thomas A. Benson** (O'Reilly)
  - Modern datacenter network design
  - Spine-leaf, Clos topologies

- **"BGP in the Data Center" by Dinesh Dutt** (O'Reilly)
  - Using BGP for datacenter routing
  - Practical deployment guide

**RDMA:**
- **"RDMA Programming Manual"** (Mellanox/NVIDIA)
  - Comprehensive RDMA programming guide
  - Available as PDF from NVIDIA

- **"High Performance Datacenter Networks" by Dennis Abts & John Kim**
  - Network topology, routing, flow control
  - InfiniBand and Ethernet comparison

**Software Defined Networking:**
- **"Software Defined Networks: A Comprehensive Approach" by Paul Göransson & Chuck Black**
  - SDN architecture and protocols
  - OpenFlow, OVSDB

- **"SDN: Software Defined Networks" by Thomas D. Nadeau & Ken Gray** (O'Reilly)
  - Enterprise SDN deployment
  - OpenDaylight, ONOS

**Storage:**
- **"NVMe over Fabrics" by Ronen Kat (Editor)**
  - NVMe-oF architecture and implementation
  - Transport protocols (RDMA, TCP, FC)

### Conference Proceedings

- **SIGCOMM** (ACM Special Interest Group on Data Communication)
  - Leading networking research conference
  - Papers on datacenter networks

- **NSDI** (Networked Systems Design and Implementation)
  - USENIX conference
  - Practical systems research

### Online Courses

- **[Computer Networking (Stanford)](https://www.youtube.com/playlist?list=PLvFG2xYBrYAQCyz4Wx3NPoYJOFjvU7g2Z)**
  - Nick McKeown's course on YouTube
  - Networking fundamentals

### Blogs and Resources

- **[Cumulus Networks Blog](https://cumulusnetworks.com/blog/)**
  - Modern network automation
  - Linux-based networking

- **[NVIDIA Networking Blog](https://blogs.nvidia.com/blog/category/networking/)**
  - RDMA, InfiniBand, Ethernet

- **[Packet Pushers Podcast](https://packetpushers.net/)**
  - Network engineering podcast
  - Interviews and deep dives

---

## 8. Community and Getting Help

### Forums and Discussion

- **[/r/networking](https://reddit.com/r/networking)**
  - Reddit community for network engineers

- **[NetworkEngineering Stack Exchange](https://networkengineering.stackexchange.com/)**
  - Q&A for network professionals

### Mailing Lists

- **[RDMA Linux Mailing List](https://lore.kernel.org/linux-rdma/)**
  - Linux RDMA development

- **[OVS Discuss](https://mail.openvswitch.org/mailman/listinfo/ovs-discuss)**
  - Open vSwitch community

### Slack/Discord Communities

- **CNCF Slack** - Channels for network-related projects
- **Network to Code Slack** - Network automation community

---

## How to Use These Resources

### Suggested Learning Paths

**Path A: Datacenter Network Engineer**
1. Study spine-leaf architecture basics
2. Learn BGP fundamentals
3. Understand ECMP and load balancing
4. Experiment with Mininet for topology testing
5. Deep dive into overlay networking (VXLAN/Geneve)

**Path B: RDMA Specialist**
1. Read RDMA fundamentals tutorials
2. Study InfiniBand or RoCE specifications
3. Program simple RDMA applications using verbs
4. Learn about lossless Ethernet (PFC, ETS)
5. Benchmark RDMA performance with perftest

**Path C: SDN Developer**
1. Learn OVS architecture
2. Experiment with OpenFlow controllers
3. Study OVS source code
4. Build custom OVS/OVN solutions
5. Deploy in production with monitoring

**Path D: Storage Engineer**
1. Understand NVMe-oF architecture
2. Learn why RDMA benefits storage
3. Set up NVMe-oF targets and initiators
4. Benchmark storage performance
5. Deploy distributed storage (Ceph/GlusterFS)

---

## Contributing

Found a great resource not listed here? Spotted a broken link?

- **Repository**: https://github.com/skeptomai/datacenter-curriculum
- **Open an issue** or submit a pull request

---

**Last Updated**: 2026-02-15
**Maintained by**: The datacenter-curriculum project

> 💡 **Remember**: Pick resources matching your current focus and learning style. The curriculum
> documents provide core knowledge - these resources offer hands-on practice and alternative
> perspectives.
