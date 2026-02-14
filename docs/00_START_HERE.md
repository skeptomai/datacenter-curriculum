# Datacenter Infrastructure: A Learning Guide

**Welcome to a comprehensive guide to modern datacenter infrastructure!**

This documentation set contains **37 high-quality documents** covering datacenter networking, RDMA, virtualization, and KVM development. These documents have been reorganized pedagogically to support structured learning rather than random exploration.

---

## How to Use This Guide

### Choose Your Entry Point Based on Your Background:

**🆕 New to datacenter infrastructure?**
→ Start with **[Part 1: Foundations](#part-1-foundations-start-here)** and read sequentially

**🌐 Know networking basics but not virtualization?**
→ Skip to **[Path 2: Network Engineer](#path-2-network-engineer)** or start with **[Part 2.1: Advanced Networking](#21-advanced-networking-concepts)**

**💻 Know virtualization basics but not datacenter networking?**
→ Skip to **[Part 2.3: Complete Virtualization](#23-complete-virtualization-understanding)** or start with **[Part 1.2: Datacenter Topology](#12-understanding-the-datacenter-topology)**

**🎯 Solving a specific problem?**
→ Jump to **[Part 4: Reference & Practical Guides](#part-4-reference--practical-guides)**

---

## Learning Paths

**Organized by priority: Virtualization → Networking → Storage** (as requested)

### Path 1: Virtualization Engineer 🎯 HIGHEST PRIORITY

**Goal:** Master modern virtualization from first principles to production deployment

**Curriculum:**
1. **Foundations/Virtualization** (1.5 hours)
   - [The Ring-0 Problem](01_foundations/01_virtualization_basics/01_the_ring0_problem.md) (20 min)
   - [Hardware Solution](01_foundations/01_virtualization_basics/02_hardware_solution.md) (30 min)
   - [VM Exit Basics](01_foundations/01_virtualization_basics/03_vm_exit_basics.md) (25 min)

2. **Intermediate/Complete Virtualization** (3 hours)
   - [Complete Evolution](02_intermediate/03_complete_virtualization/01_evolution_complete.md) (90 min)
   - [Exit Minimization](02_intermediate/03_complete_virtualization/02_exit_minimization.md) (40 min)
   - [Hardware Optimizations](02_intermediate/03_complete_virtualization/03_hardware_optimizations.md) (40 min)
   - [Device Passthrough](02_intermediate/03_complete_virtualization/04_device_passthrough.md) (50 min)

3. **Specialized/CPU & Memory** (2.5 hours)
   - [TLB, EPT, VPID Explained](03_specialized/04_cpu_memory/01_tlb_ept_explained.md) (90 min)
   - [TLB Capacity Limits](03_specialized/04_cpu_memory/02_tlb_capacity_limits.md) (50 min)

4. **Specialized/Serverless** (2.5 hours)
   - [Firecracker KVM Relationship](03_specialized/03_serverless/01_firecracker_relationship.md) (40 min)
   - [Firecracker Deep Dive](03_specialized/03_serverless/02_firecracker_deep_dive.md) (70 min)
   - [Firecracker virtio Devices](03_specialized/03_serverless/03_firecracker_virtio.md) (90 min)

5. **Specialized/Compatibility** (Optional, 2.5 hours)
   - [KVM Compat Explained](03_specialized/05_compatibility/01_kvm_compat.md) (70 min)
   - [CONFIG_COMPAT vs CONFIG_KVM_COMPAT](03_specialized/05_compatibility/02_compat_vs_kvm_compat.md) (50 min)
   - [Real Examples with QEMU](03_specialized/05_compatibility/03_compat_examples.md) (40 min)

**Total Time:** 15-20 hours
**Outcome:** Production-ready understanding of modern virtualization stack

---

### Path 2: Network Engineer

**Goal:** Master datacenter networking from physical topology to software overlays

**Curriculum:**
1. **Foundations/Datacenter Topology** (2 hours)
   - [Modern Datacenter Network Topology](01_foundations/02_datacenter_topology/01_modern_topology.md) (40 min)
   - [Spine-Leaf Server Hierarchy](01_foundations/02_datacenter_topology/02_server_hierarchy.md) (30 min)
   - [3-Tier vs Spine-Leaf](01_foundations/02_datacenter_topology/03_3tier_vs_spine_leaf.md) (30 min)
   - [ECMP Load Balancing](01_foundations/02_datacenter_topology/04_ecmp_load_balancing.md) (50 min)

2. **Intermediate/Advanced Networking** (1.5 hours)
   - [VLAN vs VXLAN Comparison](02_intermediate/01_advanced_networking/01_vlan_vs_vxlan.md) (40 min)
   - [Overlay Mechanics](02_intermediate/01_advanced_networking/02_overlay_mechanics.md) (55 min)

3. **Intermediate/RDMA** (2.5 hours)
   - [RDMA Fundamentals](02_intermediate/02_rdma/01_rdma_fundamentals.md) (35 min)
   - [Protocol Variants](02_intermediate/02_rdma/02_protocol_variants.md) (45 min)
   - [Converged Ethernet](02_intermediate/02_rdma/03_converged_ethernet.md) (50 min)
   - [NUMA Considerations](02_intermediate/02_rdma/04_numa_considerations.md) (40 min)

4. **Specialized/Overlay Networking** (5 hours)
   - [VXLAN + BGP EVPN](03_specialized/02_overlay_networking/01_vxlan_geneve_bgp.md) (90 min)
   - [BGP Communities & Route Reflectors](03_specialized/02_overlay_networking/02_bgp_communities_rr.md) (45 min)
   - [RR Session Cardinality](03_specialized/02_overlay_networking/03_rr_session_cardinality.md) (35 min)
   - [OVS Control vs Data Plane](03_specialized/02_overlay_networking/04_ovs_control_data.md) (50 min)
   - [OVS Cilium Geneve](03_specialized/02_overlay_networking/05_ovs_cilium_geneve.md) (55 min)
   - [OpenFlow Precompile Model](03_specialized/02_overlay_networking/06_openflow_precompile.md) (45 min)
   - [Prepopulated vs Learning](03_specialized/02_overlay_networking/07_prepopulated_vs_learning.md) (30 min)

**Total Time:** 12-16 hours
**Outcome:** Expert-level understanding of modern datacenter networks

---

### Path 3: Storage Engineer

**Goal:** Understand storage networking from RDMA to distributed systems

**Curriculum:**
1. **Foundations/Virtualization** (1.5 hours)
   - [The Ring-0 Problem](01_foundations/01_virtualization_basics/01_the_ring0_problem.md) (20 min)
   - [Hardware Solution](01_foundations/01_virtualization_basics/02_hardware_solution.md) (30 min)
   - [VM Exit Basics](01_foundations/01_virtualization_basics/03_vm_exit_basics.md) (25 min)
   - **Why:** Understanding virtualization is essential for modern storage systems

2. **Foundations/Datacenter Topology** (2 hours)
   - [Modern Datacenter Network Topology](01_foundations/02_datacenter_topology/01_modern_topology.md) (40 min)
   - [Spine-Leaf Server Hierarchy](01_foundations/02_datacenter_topology/02_server_hierarchy.md) (30 min)
   - [3-Tier vs Spine-Leaf](01_foundations/02_datacenter_topology/03_3tier_vs_spine_leaf.md) (30 min)
   - [ECMP Load Balancing](01_foundations/02_datacenter_topology/04_ecmp_load_balancing.md) (50 min)

3. **Intermediate/RDMA** (2.5 hours)
   - [RDMA Fundamentals](02_intermediate/02_rdma/01_rdma_fundamentals.md) (35 min)
   - [Protocol Variants](02_intermediate/02_rdma/02_protocol_variants.md) (45 min)
   - [Converged Ethernet](02_intermediate/02_rdma/03_converged_ethernet.md) (50 min)
   - [NUMA Considerations](02_intermediate/02_rdma/04_numa_considerations.md) (40 min)

4. **Specialized/Storage** (1 hour)
   - [PFC, DCB, and Storage](03_specialized/01_storage/01_pfc_dcb_storage.md) (55 min)

5. **Intermediate/Virtualization** (Optional, 3 hours)
   - [Device Passthrough](02_intermediate/03_complete_virtualization/04_device_passthrough.md) (50 min)
   - **Why:** SR-IOV critical for storage performance

**Total Time:** 10-14 hours
**Outcome:** Deep understanding of storage networking and RDMA

---

### Path 4: Full Stack (All Topics)

**Goal:** Comprehensive understanding of all datacenter infrastructure

**Approach:** Read Parts 1-3 sequentially, prioritizing Path 1 (virtualization) content first

**Curriculum:**
1. Complete **Part 1: Foundations** (3.5 hours)
2. Complete **Part 2: Intermediate** (9-12 hours)
3. Select from **Part 3: Specialized** based on interests (15-20 hours)
4. Reference **Part 4** as needed

**Total Time:** 30-40 hours
**Outcome:** Expert-level knowledge across all datacenter technologies

---

## Detailed Curriculum

### **Part 1: FOUNDATIONS (Start Here)**

**Essential building blocks - read in order**
**Priority: Virtualization → Networking** (as requested)

#### **1.1 Virtualization Fundamentals** 🎯 HIGHEST PRIORITY

**Why start here:** Understanding virtualization is fundamental to modern infrastructure

1. **[The Ring-0 Problem](01_foundations/01_virtualization_basics/01_the_ring0_problem.md)** (20 min)
   - **What you'll learn:** Why virtualization is hard on x86
   - **Prerequisites:** None
   - **Next:** Hardware Solution

2. **[Hardware Solution (VT-x/AMD-V)](01_foundations/01_virtualization_basics/02_hardware_solution.md)** (30 min)
   - **What you'll learn:** How hardware enables virtualization
   - **Prerequisites:** Ring-0 Problem
   - **Next:** VM Exit Basics

3. **[VM Exit Basics](01_foundations/01_virtualization_basics/03_vm_exit_basics.md)** (25 min)
   - **What you'll learn:** The fundamental virtualization mechanism
   - **Prerequisites:** Hardware Solution
   - **Next:** Either complete virtualization OR datacenter topology

**Part 1.1 Total: ~1.5 hours**

---

#### **1.2 Understanding the Datacenter Topology**

**Why learn this:** Context for where VMs actually run

4. **[Modern Datacenter Network Topology](01_foundations/02_datacenter_topology/01_modern_topology.md)** (40 min)
   - **What you'll learn:** Link speeds, 3-tier vs spine-leaf, oversubscription
   - **Prerequisites:** None
   - **Next:** Server Hierarchy

5. **[Spine-Leaf Server Hierarchy](01_foundations/02_datacenter_topology/02_server_hierarchy.md)** (30 min)
   - **What you'll learn:** Three-layer structure (servers → leafs → spines)
   - **Prerequisites:** Modern Topology
   - **Next:** 3-Tier vs Spine-Leaf

6. **[3-Tier vs Spine-Leaf Differences](01_foundations/02_datacenter_topology/03_3tier_vs_spine_leaf.md)** (30 min)
   - **What you'll learn:** Why spine-leaf is fundamentally different
   - **Prerequisites:** Server Hierarchy
   - **Next:** ECMP Load Balancing

7. **[ECMP Load Balancing](01_foundations/02_datacenter_topology/04_ecmp_load_balancing.md)** (50 min)
   - **What you'll learn:** How traffic distributes across multiple paths
   - **Prerequisites:** 3-Tier vs Spine-Leaf
   - **Next:** Advanced networking concepts

**Part 1.2 Total: ~2 hours**

**Part 1 Complete Total: ~3.5 hours**
**Outcome:** Understand virtualization mechanics AND modern datacenter topology

---

### **Part 2: INTERMEDIATE CONCEPTS**

**Build on fundamentals - can be read somewhat independently**

#### **2.1 Advanced Networking Concepts**

8. **[VLAN vs VXLAN Comparison](02_intermediate/01_advanced_networking/01_vlan_vs_vxlan.md)** (40 min)
   - **What you'll learn:** Overlay networking for multi-tenancy
   - **Prerequisites:** Foundation networking
   - **Next:** Overlay Mechanics

9. **[Overlay Mechanics (VXLAN/Geneve)](02_intermediate/01_advanced_networking/02_overlay_mechanics.md)** (55 min)
   - **What you'll learn:** How overlays actually work
   - **Prerequisites:** VLAN vs VXLAN
   - **Next:** RDMA or specialized overlay networking

**Part 2.1 Total: ~1.5 hours**

---

#### **2.2 High-Performance Networking (RDMA)**

10. **[RDMA Fundamentals](02_intermediate/02_rdma/01_rdma_fundamentals.md)** (35 min)
    - **What you'll learn:** RDMA is a HOST optimization
    - **Prerequisites:** Foundation networking
    - **Next:** Protocol Variants

11. **[Protocol Variants (RoCEv2, iWARP, InfiniBand)](02_intermediate/02_rdma/02_protocol_variants.md)** (45 min)
    - **What you'll learn:** RDMA protocol differences
    - **Prerequisites:** RDMA Fundamentals
    - **Next:** Converged Ethernet

12. **[Converged Ethernet](02_intermediate/02_rdma/03_converged_ethernet.md)** (50 min)
    - **What you'll learn:** How to make Ethernet lossless
    - **Prerequisites:** Protocol Variants
    - **Next:** NUMA Considerations

13. **[NUMA Considerations](02_intermediate/02_rdma/04_numa_considerations.md)** (40 min)
    - **What you'll learn:** Hardware topology for RDMA performance
    - **Prerequisites:** Converged Ethernet
    - **Next:** Storage applications or complete virtualization

**Part 2.2 Total: ~2.5 hours**

---

#### **2.3 Complete Virtualization Understanding**

14. **[Complete Virtualization Evolution](02_intermediate/03_complete_virtualization/01_evolution_complete.md)** (90 min)
    - **What you'll learn:** All approaches (paravirt, KVM, virtio, SR-IOV)
    - **Prerequisites:** Foundation virtualization (Part 1.1)
    - **Next:** Exit Minimization

15. **[Exit Minimization Strategies](02_intermediate/03_complete_virtualization/02_exit_minimization.md)** (40 min)
    - **What you'll learn:** Performance optimization techniques
    - **Prerequisites:** Complete Evolution, VM Exit Basics
    - **Next:** Hardware Optimizations

16. **[Hardware Optimizations (VPID, Posted Interrupts)](02_intermediate/03_complete_virtualization/03_hardware_optimizations.md)** (40 min)
    - **What you'll learn:** Modern VT-x features
    - **Prerequisites:** Hardware Solution, Exit Minimization
    - **Next:** Device Passthrough

17. **[Device Passthrough (SR-IOV, VFIO, IOMMU)](02_intermediate/03_complete_virtualization/04_device_passthrough.md)** (50 min)
    - **What you'll learn:** Near-native I/O performance
    - **Prerequisites:** Hardware Optimizations
    - **Next:** Specialized topics

**Part 2.3 Total: ~3.5 hours**

**Part 2 Complete Total: ~7.5 hours**
**Outcome:** Deep understanding of modern networking, RDMA, and complete virtualization stack

---

### **Part 3: SPECIALIZED TOPICS**

**Pick based on your needs - order flexible**

#### **3.1 Storage & RDMA Applications**

18. **[PFC, DCB, and Storage](03_specialized/01_storage/01_pfc_dcb_storage.md)** (55 min)
    - **What you'll learn:** Why RDMA is critical for modern storage
    - **Prerequisites:** RDMA complete (Part 2.2)

---

#### **3.2 Advanced Networking Deep-Dives**

19. **[VXLAN + BGP EVPN Deep Dive](03_specialized/02_overlay_networking/01_vxlan_geneve_bgp.md)** (90 min)
    - **Prerequisites:** Advanced networking (Part 2.1)

20. **[BGP Communities vs Route Reflectors](03_specialized/02_overlay_networking/02_bgp_communities_rr.md)** (45 min)
    - **Prerequisites:** Doc #19

21. **[Route Reflector Session Cardinality](03_specialized/02_overlay_networking/03_rr_session_cardinality.md)** (35 min)
    - **Prerequisites:** Doc #20

22. **[OVS Control vs Data Plane](03_specialized/02_overlay_networking/04_ovs_control_data.md)** (50 min)
    - **Prerequisites:** Advanced networking

23. **[OVS Cilium Geneve](03_specialized/02_overlay_networking/05_ovs_cilium_geneve.md)** (55 min)
    - **Prerequisites:** Docs #9, #22

24. **[OpenFlow Precompile Model](03_specialized/02_overlay_networking/06_openflow_precompile.md)** (45 min)
    - **Prerequisites:** OVS knowledge

25. **[Prepopulated vs Learning](03_specialized/02_overlay_networking/07_prepopulated_vs_learning.md)** (30 min)
    - **Prerequisites:** Doc #24

---

#### **3.3 Microservices & Serverless**

26. **[Firecracker KVM Relationship](03_specialized/03_serverless/01_firecracker_relationship.md)** (40 min)
    - **What you'll learn:** What Firecracker is (not a hypervisor replacement)

27. **[Firecracker Deep Dive](03_specialized/03_serverless/02_firecracker_deep_dive.md)** (70 min)
    - **Prerequisites:** Doc #26

28. **[Firecracker virtio Devices](03_specialized/03_serverless/03_firecracker_virtio.md)** (90 min)
    - **Prerequisites:** Doc #27

---

#### **3.4 CPU & Memory Virtualization Deep-Dives**

29. **[TLB, EPT, VPID Explained](03_specialized/04_cpu_memory/01_tlb_ept_explained.md)** (90 min)
    - **Prerequisites:** Complete virtualization (Part 2.3)

30. **[TLB Capacity Limits](03_specialized/04_cpu_memory/02_tlb_capacity_limits.md)** (50 min)
    - **Prerequisites:** Doc #29

---

#### **3.5 Compatibility & Legacy Systems**

31. **[KVM Compat Explained](03_specialized/05_compatibility/01_kvm_compat.md)** (70 min)
    - **What you'll learn:** 32-bit/64-bit compatibility

32. **[CONFIG_COMPAT vs CONFIG_KVM_COMPAT](03_specialized/05_compatibility/02_compat_vs_kvm_compat.md)** (50 min)
    - **Prerequisites:** Doc #31

33. **[Real Examples with QEMU](03_specialized/05_compatibility/03_compat_examples.md)** (40 min)
    - **Prerequisites:** Doc #32

---

### **Part 4: REFERENCE & PRACTICAL GUIDES**

**Use as needed - not sequential reading**

#### **4.1 Development Environment Setup**

34. **[macOS Kernel Development Setup](04_reference/setup_guides/01_macos_case_sensitivity.md)**
    - **When:** Setting up Linux kernel development on macOS

35. **[External Drive for Kernel Work](04_reference/setup_guides/02_external_drive_setup.md)**
    - **When:** Choosing storage for kernel work

---

#### **4.2 Learning Resources**

36. **[Learning KVM Comprehensive Guide](04_reference/learning_resources/01_learning_kvm_guide.md)**
    - **When:** Starting KVM source code study

37. **[Networking Acronyms Glossary](04_reference/learning_resources/02_networking_acronyms.md)**
    - **When:** Need quick reference for acronyms

---

#### **4.3 Technology Selection**

38. **[Virtualization Technology Primer](04_reference/decision_frameworks/01_virtualization_primer.md)**
    - **When:** Choosing virtualization technology
    - **NOTE:** Read AFTER understanding fundamentals (Part 2.3)

---

## Quick Start Guides

For those who want rapid overviews before deep dives:

- **[Quick Start: Virtualization](quick_start_virtualization.md)** (2 hours) - Essential virtualization concepts
- **[Quick Start: Networking](quick_start_networking.md)** (2 hours) - Essential networking concepts
- **[Quick Start: Full Stack](quick_start_full_stack.md)** (5 hours) - Complete overview of all topics

---

## Document Metadata

All documents include YAML frontmatter with:
- **level:** foundational | intermediate | specialized | reference
- **estimated_time:** Reading time estimate
- **prerequisites:** What to read first
- **next_recommended:** Suggested next documents
- **tags:** Topical categorization

---

## Original Documents

All original documents are preserved in `original_docs/` for reference.

---

## Need Help?

- **Stuck on a concept?** Check prerequisites and read foundational documents first
- **Can't find something?** Use the [Networking Acronyms Glossary](04_reference/learning_resources/02_networking_acronyms.md)
- **Want to go deeper?** Each document has "Next Recommended" links

---

**Ready to begin? Start with [The Ring-0 Problem](01_foundations/01_virtualization_basics/01_the_ring0_problem.md)!** 🎯
