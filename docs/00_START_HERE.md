# Datacenter Infrastructure: A Learning Guide

This guide consists of **59 documents** covering containers, virtualization, datacenter networking, and infrastructure development organized pedagogically to support structured learning rather than random exploration.

**What makes this different:** Instead of a reference manual, this is a structured curriculum with five learning paths designed around what you're actually working with. Each path includes explicit prerequisites, depth indicators (📖 Foundational → 📚 Intermediate → 🔬 Specialized), and a clear progression from fundamentals through production deployment.

**Most people start with containers** (Path 1) since they're ubiquitous in modern infrastructure. Infrastructure engineers building the underlying platform typically start with virtualization (Path 2). Network and storage engineers have dedicated paths for their domains. The paths are designed to stand alone or combine—senior engineers often complete multiple paths to build complete platform expertise.

---

## Learning Paths

**Choose based on what you're actually working with - all paths are equally valid:**

### Path 1: Container Platform Engineer 📦

**Best for:** Application developers, DevOps engineers, platform engineers
**You'll use this if:** Deploying apps, managing Kubernetes, building CI/CD pipelines

**Goal:** Master container technologies from fundamentals through Kubernetes production deployment

**Curriculum:**
1. **Foundations/Container Fundamentals**
   - [Linux Container Primitives](04_containers/01_fundamentals/01_cgroups_namespaces.md)
   - [Union Filesystems and Images](04_containers/01_fundamentals/02_union_filesystems.md)
   - [Container vs VM Comparison](04_containers/01_fundamentals/03_container_vs_vm.md)

2. **Container Runtimes**
   - [Container Runtime Landscape](04_containers/02_runtimes/01_runtime_landscape.md)
   - [Docker and containerd](04_containers/02_runtimes/02_docker_containerd.md)
   - [Kata Containers and gVisor](04_containers/02_runtimes/03_kata_gvisor.md)
   - [Runtime Comparison](04_containers/02_runtimes/04_runtime_comparison.md)

3. **Kubernetes Orchestration**
   - [Kubernetes Architecture](04_containers/03_orchestration/01_kubernetes_architecture.md)
   - [Pods and Workloads](04_containers/03_orchestration/02_pods_workloads.md)
   - [Services and Networking](04_containers/03_orchestration/03_services_networking.md)
   - [Scheduling and Resources](04_containers/03_orchestration/04_scheduling_resources.md)
   - [Storage and Volumes](04_containers/03_orchestration/05_storage_volumes.md)
   - [Production Patterns](04_containers/03_orchestration/06_production_patterns.md)

4. **Container Networking**
   - [CNI Deep Dive](04_containers/04_networking/01_cni_deep_dive.md)
   - [Calico vs Cilium](04_containers/04_networking/02_calico_vs_cilium.md)
   - [eBPF Networking](04_containers/04_networking/03_ebpf_networking.md)
   - [Service Mesh](04_containers/04_networking/04_service_mesh.md)
   - [Network Policies Advanced](04_containers/04_networking/05_network_policies_advanced.md)

5. **Container Security**
   - [Image Security](04_containers/05_security/01_image_security.md)
   - [Runtime Security](04_containers/05_security/02_runtime_security.md)
   - [Pod Security Standards](04_containers/05_security/03_pod_security.md)
   - [Supply Chain Security](04_containers/05_security/04_supply_chain.md)

**Curriculum depth:** 📖 Foundational → 📚 Intermediate → 🔬 Specialized
**Outcome:** Deploy and secure production Kubernetes clusters with deep understanding of container mechanics

**Quick Start Available:** [Container Quick Start](quick_start_containers.md)

---

### Path 2: Virtualization Engineer 🔧

**Best for:** Infrastructure engineers, hypervisor developers, cloud platform builders
**You'll use this if:** Building VM infrastructure, optimizing hypervisor performance, understanding cloud internals

**Goal:** Deep expertise in CPU/memory virtualization and hypervisor technologies

**Curriculum:**
1. **Foundations/Virtualization**
   - [The Ring-0 Problem](01_foundations/01_virtualization_basics/01_the_ring0_problem.md)
   - [Hardware Solution](01_foundations/01_virtualization_basics/02_hardware_solution.md)
   - [VM Exit Basics](01_foundations/01_virtualization_basics/03_vm_exit_basics.md)

2. **Intermediate/Complete Virtualization**
   - [Complete Evolution](02_intermediate/03_complete_virtualization/01_evolution_complete.md)
   - [Exit Minimization](02_intermediate/03_complete_virtualization/02_exit_minimization.md)
   - [Hardware Optimizations](02_intermediate/03_complete_virtualization/03_hardware_optimizations.md)
   - [Device Passthrough](02_intermediate/03_complete_virtualization/04_device_passthrough.md)

3. **Specialized/CPU & Memory**
   - [TLB, EPT, VPID Explained](05_specialized/04_cpu_memory/01_tlb_ept_explained.md)
   - [TLB Capacity Limits](05_specialized/04_cpu_memory/02_tlb_capacity_limits.md)

4. **Specialized/Serverless**
   - [Firecracker KVM Relationship](05_specialized/03_serverless/01_firecracker_relationship.md)
   - [Firecracker Deep Dive](05_specialized/03_serverless/02_firecracker_deep_dive.md)
   - [Firecracker virtio Devices](05_specialized/03_serverless/03_firecracker_virtio.md)

5. **Specialized/Compatibility** (Optional)
   - [KVM Compat Explained](05_specialized/05_compatibility/01_kvm_compat.md)
   - [CONFIG_COMPAT vs CONFIG_KVM_COMPAT](05_specialized/05_compatibility/02_compat_vs_kvm_compat.md)
   - [Real Examples with QEMU](05_specialized/05_compatibility/03_compat_examples.md)

**Curriculum depth:** 📖 Foundational → 📚 Intermediate → 🔬 Specialized
**Outcome:** Production-ready understanding of modern virtualization stack

---

### Path 3: Network Engineer 🌐

**Best for:** Network engineers, SREs, infrastructure architects
**You'll use this if:** Designing datacenter networks, troubleshooting connectivity, implementing SDN

**Goal:** Master datacenter networking from physical topology to software overlays

**Curriculum:**
1. **Foundations/Datacenter Topology**
   - [Modern Datacenter Network Topology](01_foundations/02_datacenter_topology/01_modern_topology.md)
   - [Spine-Leaf Server Hierarchy](01_foundations/02_datacenter_topology/02_server_hierarchy.md)
   - [3-Tier vs Spine-Leaf](01_foundations/02_datacenter_topology/03_3tier_vs_spine_leaf.md)
   - [ECMP Load Balancing](01_foundations/02_datacenter_topology/04_ecmp_load_balancing.md)

2. **Intermediate/Advanced Networking**
   - [VLAN vs VXLAN Comparison](02_intermediate/01_advanced_networking/01_vlan_vs_vxlan.md)
   - [Overlay Mechanics](02_intermediate/01_advanced_networking/02_overlay_mechanics.md)

3. **Intermediate/RDMA**
   - [RDMA Fundamentals](02_intermediate/02_rdma/01_rdma_fundamentals.md)
   - [Protocol Variants](02_intermediate/02_rdma/02_protocol_variants.md)
   - [Converged Ethernet](02_intermediate/02_rdma/03_converged_ethernet.md)
   - [NUMA Considerations](02_intermediate/02_rdma/04_numa_considerations.md)

4. **Specialized/Overlay Networking**
   - [VXLAN + BGP EVPN](05_specialized/02_overlay_networking/01_vxlan_geneve_bgp.md)
   - [BGP Communities & Route Reflectors](05_specialized/02_overlay_networking/02_bgp_communities_rr.md)
   - [RR Session Cardinality](05_specialized/02_overlay_networking/03_rr_session_cardinality.md)
   - [OVS Control vs Data Plane](05_specialized/02_overlay_networking/04_ovs_control_data.md)
   - [OVS Cilium Geneve](05_specialized/02_overlay_networking/05_ovs_cilium_geneve.md)
   - [OpenFlow Precompile Model](05_specialized/02_overlay_networking/06_openflow_precompile.md)
   - [Prepopulated vs Learning](05_specialized/02_overlay_networking/07_prepopulated_vs_learning.md)

**Curriculum depth:** 📖 Foundational → 📚 Intermediate → 🔬 Specialized
**Outcome:** Expert-level understanding of modern datacenter networks

---

### Path 4: Storage Engineer 💾

**Best for:** Storage specialists, performance engineers, distributed systems engineers
**You'll use this if:** Building storage infrastructure, optimizing I/O performance, deploying NVMe-oF

**Goal:** High-performance storage networking with RDMA

**Curriculum:**
1. **Foundations/Virtualization**
   - [The Ring-0 Problem](01_foundations/01_virtualization_basics/01_the_ring0_problem.md)
   - [Hardware Solution](01_foundations/01_virtualization_basics/02_hardware_solution.md)
   - [VM Exit Basics](01_foundations/01_virtualization_basics/03_vm_exit_basics.md)
   - **Why:** Understanding virtualization is essential for modern storage systems

2. **Foundations/Datacenter Topology**
   - [Modern Datacenter Network Topology](01_foundations/02_datacenter_topology/01_modern_topology.md)
   - [Spine-Leaf Server Hierarchy](01_foundations/02_datacenter_topology/02_server_hierarchy.md)
   - [3-Tier vs Spine-Leaf](01_foundations/02_datacenter_topology/03_3tier_vs_spine_leaf.md)
   - [ECMP Load Balancing](01_foundations/02_datacenter_topology/04_ecmp_load_balancing.md)

3. **Intermediate/RDMA**
   - [RDMA Fundamentals](02_intermediate/02_rdma/01_rdma_fundamentals.md)
   - [Protocol Variants](02_intermediate/02_rdma/02_protocol_variants.md)
   - [Converged Ethernet](02_intermediate/02_rdma/03_converged_ethernet.md)
   - [NUMA Considerations](02_intermediate/02_rdma/04_numa_considerations.md)

4. **Specialized/Storage**
   - [PFC, DCB, and Storage](05_specialized/01_storage/01_pfc_dcb_storage.md)

5. **Intermediate/Virtualization** (Optional)
   - [Device Passthrough](02_intermediate/03_complete_virtualization/04_device_passthrough.md)
   - **Why:** SR-IOV critical for storage performance

**Curriculum depth:** 📖 Foundational → 📚 Intermediate → 🔬 Specialized
**Outcome:** Deep understanding of storage networking and RDMA

---

### Path 5: Full Stack Platform Engineer 🎯

**Best for:** Senior engineers, architects, technical leads building complete platforms
**You'll use this if:** Designing end-to-end infrastructure, making technology decisions, leading platform teams

**Goal:** Complete datacenter infrastructure expertise across VMs and containers

**Approach:** Complete all foundational and intermediate topics, then select specialized areas

**Curriculum:**
1. Complete **Part 1: Foundations**
   - Virtualization basics
   - Datacenter topology
   - Container fundamentals

2. Complete **Part 2: Intermediate**
   - Advanced networking
   - RDMA
   - Complete virtualization
   - Container technologies

3. Select from **Part 3: Specialized** based on your focus
   - Storage, overlay networking, serverless, CPU/memory deep dives

4. Reference **Part 4** as needed

**Curriculum depth:** 📖 Foundational → 📚 Intermediate → 🔬 Specialized
**Outcome:** Architect and operate complete datacenter infrastructure with deep understanding of VMs, containers, networking, and storage

**Recommended approach:** Start with either Container (Path 1) or Virtualization (Path 2) based on immediate needs, then complete the other

---

## Detailed Curriculum

### **Part 1: FOUNDATIONS (Start Here)**

**Essential building blocks - can be read in any order based on your needs**

#### **1.1 Virtualization Fundamentals** 🔧

**Why learn this:** Essential for understanding how VMs work, cloud internals, and hypervisor performance

1. **[The Ring-0 Problem](01_foundations/01_virtualization_basics/01_the_ring0_problem.md)**
   - **What you'll learn:** Why virtualization is hard on x86
   - **Prerequisites:** None
   - **Next:** Hardware Solution

2. **[Hardware Solution (VT-x/AMD-V)](01_foundations/01_virtualization_basics/02_hardware_solution.md)**
   - **What you'll learn:** How hardware enables virtualization
   - **Prerequisites:** Ring-0 Problem
   - **Next:** VM Exit Basics

3. **[VM Exit Basics](01_foundations/01_virtualization_basics/03_vm_exit_basics.md)**
   - **What you'll learn:** The fundamental virtualization mechanism
   - **Prerequisites:** Hardware Solution
   - **Next:** Either complete virtualization OR datacenter topology

---

#### **1.2 Understanding the Datacenter Topology** 🌐

**Why learn this:** Essential for understanding modern datacenter networks, applies to both VM and container infrastructure

4. **[Modern Datacenter Network Topology](01_foundations/02_datacenter_topology/01_modern_topology.md)**
   - **What you'll learn:** Link speeds, 3-tier vs spine-leaf, oversubscription
   - **Prerequisites:** None
   - **Next:** Server Hierarchy

5. **[Spine-Leaf Server Hierarchy](01_foundations/02_datacenter_topology/02_server_hierarchy.md)**
   - **What you'll learn:** Three-layer structure (servers → leafs → spines)
   - **Prerequisites:** Modern Topology
   - **Next:** 3-Tier vs Spine-Leaf

6. **[3-Tier vs Spine-Leaf Differences](01_foundations/02_datacenter_topology/03_3tier_vs_spine_leaf.md)**
   - **What you'll learn:** Why spine-leaf is fundamentally different
   - **Prerequisites:** Server Hierarchy
   - **Next:** ECMP Load Balancing

7. **[ECMP Load Balancing](01_foundations/02_datacenter_topology/04_ecmp_load_balancing.md)**
   - **What you'll learn:** How traffic distributes across multiple paths
   - **Prerequisites:** 3-Tier vs Spine-Leaf
   - **Next:** Advanced networking concepts

---

#### **1.3 Container Fundamentals** 📦

**Why learn this:** Modern infrastructure relies on containers alongside VMs

8. **[Linux Container Primitives](04_containers/01_fundamentals/01_cgroups_namespaces.md)**
   - **What you'll learn:** cgroups, namespaces, container isolation
   - **Prerequisites:** None
   - **Next:** Union Filesystems

9. **[Union Filesystems and Images](04_containers/01_fundamentals/02_union_filesystems.md)**
   - **What you'll learn:** Container images, layers, OverlayFS
   - **Prerequisites:** Linux Container Primitives
   - **Next:** Container vs VM Comparison

10. **[Container vs VM Comparison](04_containers/01_fundamentals/03_container_vs_vm.md)**
    - **What you'll learn:** When to use containers vs VMs
    - **Prerequisites:** Union Filesystems, virtualization basics
    - **Next:** Container runtimes or continue with VM track

**Outcome:** Understand virtualization mechanics, modern datacenter topology, AND container fundamentals

---

### **Part 2: INTERMEDIATE CONCEPTS**

**Build on fundamentals - can be read somewhat independently**

#### **2.1 Advanced Networking Concepts**

8. **[VLAN vs VXLAN Comparison](02_intermediate/01_advanced_networking/01_vlan_vs_vxlan.md)**
   - **What you'll learn:** Overlay networking for multi-tenancy
   - **Prerequisites:** Foundation networking
   - **Next:** Overlay Mechanics

9. **[Overlay Mechanics (VXLAN/Geneve)](02_intermediate/01_advanced_networking/02_overlay_mechanics.md)**
   - **What you'll learn:** How overlays actually work
   - **Prerequisites:** VLAN vs VXLAN
   - **Next:** RDMA or specialized overlay networking

---

#### **2.2 High-Performance Networking (RDMA)**

10. **[RDMA Fundamentals](02_intermediate/02_rdma/01_rdma_fundamentals.md)**
    - **What you'll learn:** RDMA is a HOST optimization
    - **Prerequisites:** Foundation networking
    - **Next:** Protocol Variants

11. **[Protocol Variants (RoCEv2, iWARP, InfiniBand)](02_intermediate/02_rdma/02_protocol_variants.md)**
    - **What you'll learn:** RDMA protocol differences
    - **Prerequisites:** RDMA Fundamentals
    - **Next:** Converged Ethernet

12. **[Converged Ethernet](02_intermediate/02_rdma/03_converged_ethernet.md)**
    - **What you'll learn:** How to make Ethernet lossless
    - **Prerequisites:** Protocol Variants
    - **Next:** NUMA Considerations

13. **[NUMA Considerations](02_intermediate/02_rdma/04_numa_considerations.md)**
    - **What you'll learn:** Hardware topology for RDMA performance
    - **Prerequisites:** Converged Ethernet
    - **Next:** Storage applications or complete virtualization

---

#### **2.3 Complete Virtualization Understanding**

14. **[Complete Virtualization Evolution](02_intermediate/03_complete_virtualization/01_evolution_complete.md)**
    - **What you'll learn:** All approaches (paravirt, KVM, virtio, SR-IOV)
    - **Prerequisites:** Foundation virtualization (Part 1.1)
    - **Next:** Exit Minimization

15. **[Exit Minimization Strategies](02_intermediate/03_complete_virtualization/02_exit_minimization.md)**
    - **What you'll learn:** Performance optimization techniques
    - **Prerequisites:** Complete Evolution, VM Exit Basics
    - **Next:** Hardware Optimizations

16. **[Hardware Optimizations (VPID, Posted Interrupts)](02_intermediate/03_complete_virtualization/03_hardware_optimizations.md)**
    - **What you'll learn:** Modern VT-x features
    - **Prerequisites:** Hardware Solution, Exit Minimization
    - **Next:** Device Passthrough

17. **[Device Passthrough (SR-IOV, VFIO, IOMMU)](02_intermediate/03_complete_virtualization/04_device_passthrough.md)**
    - **What you'll learn:** Near-native I/O performance
    - **Prerequisites:** Hardware Optimizations
    - **Next:** Specialized topics

---

#### **2.4 Container Technologies**

18. **[Container Runtime Landscape](04_containers/02_runtimes/01_runtime_landscape.md)**
    - **What you'll learn:** OCI/CRI standards, runtime ecosystem overview
    - **Prerequisites:** Container fundamentals (Part 1.3)
    - **Next:** Docker and containerd

19. **[Docker and containerd Architecture](04_containers/02_runtimes/02_docker_containerd.md)**
    - **What you'll learn:** How Docker works, containerd role, runc
    - **Prerequisites:** Container Runtime Landscape
    - **Next:** Secure runtimes

20. **[Kata Containers and gVisor](04_containers/02_runtimes/03_kata_gvisor.md)**
    - **What you'll learn:** VM-isolated containers, userspace kernels
    - **Prerequisites:** Docker and containerd, virtualization knowledge
    - **Next:** Runtime comparison

21. **[Runtime Comparison and Selection](04_containers/02_runtimes/04_runtime_comparison.md)**
    - **What you'll learn:** When to use each runtime, tradeoffs
    - **Prerequisites:** All runtime documents
    - **Next:** Kubernetes orchestration

22. **[Kubernetes Architecture](04_containers/03_orchestration/01_kubernetes_architecture.md)**
    - **What you'll learn:** Control plane, worker nodes, reconciliation
    - **Prerequisites:** Container runtimes
    - **Next:** Pods and Workloads

23. **[Pods and Workloads](04_containers/03_orchestration/02_pods_workloads.md)**
    - **What you'll learn:** Pods, Deployments, StatefulSets, DaemonSets
    - **Prerequisites:** Kubernetes Architecture
    - **Next:** Services and Networking

24. **[Kubernetes Services and Networking](04_containers/03_orchestration/03_services_networking.md)**
    - **What you'll learn:** Services, kube-proxy, DNS, Ingress
    - **Prerequisites:** Pods and Workloads
    - **Next:** Scheduling and Resources

25. **[Scheduling and Resources](04_containers/03_orchestration/04_scheduling_resources.md)**
    - **What you'll learn:** Scheduler, affinity, autoscaling, QoS
    - **Prerequisites:** Services and Networking
    - **Next:** Storage and Volumes

26. **[Storage and Volumes](04_containers/03_orchestration/05_storage_volumes.md)**
    - **What you'll learn:** PersistentVolumes, StorageClasses, CSI
    - **Prerequisites:** Scheduling and Resources
    - **Next:** Production Patterns

27. **[Production Patterns](04_containers/03_orchestration/06_production_patterns.md)**
    - **What you'll learn:** HA, deployment safety, observability
    - **Prerequisites:** Storage and Volumes
    - **Next:** Container networking deep dive

28. **[CNI Deep Dive](04_containers/04_networking/01_cni_deep_dive.md)**
    - **What you'll learn:** CNI specification, plugin implementation
    - **Prerequisites:** Kubernetes networking basics
    - **Next:** Calico vs Cilium

29. **[Calico vs Cilium](04_containers/04_networking/02_calico_vs_cilium.md)**
    - **What you'll learn:** BGP vs eBPF networking architectures
    - **Prerequisites:** CNI Deep Dive, datacenter networking knowledge
    - **Next:** eBPF Networking

30. **[eBPF Networking](04_containers/04_networking/03_ebpf_networking.md)**
    - **What you'll learn:** XDP, TC, eBPF maps, high-performance networking
    - **Prerequisites:** Calico vs Cilium
    - **Next:** Service Mesh

31. **[Service Mesh (Istio, Linkerd)](04_containers/04_networking/04_service_mesh.md)**
    - **What you'll learn:** mTLS, traffic management, observability
    - **Prerequisites:** Kubernetes networking
    - **Next:** Network Policies

32. **[Network Policies Advanced](04_containers/04_networking/05_network_policies_advanced.md)**
    - **What you'll learn:** Multi-tenancy, egress control, L7 policies
    - **Prerequisites:** Service Mesh
    - **Next:** Container security

33. **[Image Security](04_containers/05_security/01_image_security.md)**
    - **What you'll learn:** Scanning, signing, admission control
    - **Prerequisites:** Container runtimes
    - **Next:** Runtime Security

34. **[Runtime Security](04_containers/05_security/02_runtime_security.md)**
    - **What you'll learn:** seccomp, AppArmor, Falco, capabilities
    - **Prerequisites:** Image Security
    - **Next:** Pod Security

35. **[Pod Security Standards](04_containers/05_security/03_pod_security.md)**
    - **What you'll learn:** PSS, RBAC, service accounts
    - **Prerequisites:** Runtime Security
    - **Next:** Supply Chain Security

36. **[Supply Chain Security](04_containers/05_security/04_supply_chain.md)**
    - **What you'll learn:** SBOM, SLSA, Sigstore, provenance
    - **Prerequisites:** Pod Security
    - **Next:** Specialized topics or production deployment

**Outcome:** Deep understanding of modern networking, RDMA, complete virtualization stack, AND container technologies

---

### **Part 3: SPECIALIZED TOPICS**

**Pick based on your needs - order flexible**

#### **3.1 Storage & RDMA Applications**

37. **[PFC, DCB, and Storage](05_specialized/01_storage/01_pfc_dcb_storage.md)**
    - **What you'll learn:** Why RDMA is critical for modern storage
    - **Prerequisites:** RDMA complete (Part 2.2)

---

#### **3.2 Advanced Networking Deep-Dives**

38. **[VXLAN + BGP EVPN Deep Dive](05_specialized/02_overlay_networking/01_vxlan_geneve_bgp.md)**
    - **Prerequisites:** Advanced networking (Part 2.1)

39. **[BGP Communities vs Route Reflectors](05_specialized/02_overlay_networking/02_bgp_communities_rr.md)**
    - **Prerequisites:** Doc #38

40. **[Route Reflector Session Cardinality](05_specialized/02_overlay_networking/03_rr_session_cardinality.md)**
    - **Prerequisites:** Doc #39

41. **[OVS Control vs Data Plane](05_specialized/02_overlay_networking/04_ovs_control_data.md)**
    - **Prerequisites:** Advanced networking

42. **[OVS Cilium Geneve](05_specialized/02_overlay_networking/05_ovs_cilium_geneve.md)**
    - **Prerequisites:** Overlay mechanics, Kubernetes networking

43. **[OpenFlow Precompile Model](05_specialized/02_overlay_networking/06_openflow_precompile.md)**
    - **Prerequisites:** OVS knowledge

44. **[Prepopulated vs Learning](05_specialized/02_overlay_networking/07_prepopulated_vs_learning.md)**
    - **Prerequisites:** Doc #43

---

#### **3.3 Microservices & Serverless**

45. **[Firecracker KVM Relationship](05_specialized/03_serverless/01_firecracker_relationship.md)**
    - **What you'll learn:** What Firecracker is (not a hypervisor replacement)

46. **[Firecracker Deep Dive](05_specialized/03_serverless/02_firecracker_deep_dive.md)**
    - **Prerequisites:** Doc #45

47. **[Firecracker virtio Devices](05_specialized/03_serverless/03_firecracker_virtio.md)**
    - **Prerequisites:** Doc #46

---

#### **3.4 CPU & Memory Virtualization Deep-Dives**

48. **[TLB, EPT, VPID Explained](05_specialized/04_cpu_memory/01_tlb_ept_explained.md)**
    - **Prerequisites:** Complete virtualization (Part 2.3)

49. **[TLB Capacity Limits](05_specialized/04_cpu_memory/02_tlb_capacity_limits.md)**
    - **Prerequisites:** Doc #48

---

#### **3.5 Compatibility & Legacy Systems**

50. **[KVM Compat Explained](05_specialized/05_compatibility/01_kvm_compat.md)**
    - **What you'll learn:** 32-bit/64-bit compatibility

51. **[CONFIG_COMPAT vs CONFIG_KVM_COMPAT](05_specialized/05_compatibility/02_compat_vs_kvm_compat.md)**
    - **Prerequisites:** Doc #50

52. **[Real Examples with QEMU](05_specialized/05_compatibility/03_compat_examples.md)**
    - **Prerequisites:** Doc #51

---

### **Part 4: REFERENCE & PRACTICAL GUIDES**

**Use as needed - not sequential reading**

#### **4.1 Development Environment Setup**

53. **[macOS Kernel Development Setup](06_reference/setup_guides/01_macos_case_sensitivity.md)**
    - **When:** Setting up Linux kernel development on macOS

54. **[External Drive for Kernel Work](06_reference/setup_guides/02_external_drive_setup.md)**
    - **When:** Choosing storage for kernel work

---

#### **4.2 Learning Resources**

55. **[Learning KVM Comprehensive Guide](06_reference/learning_resources/01_learning_kvm_guide.md)**
    - **When:** Starting KVM source code study

56. **[Networking Acronyms Glossary](06_reference/learning_resources/02_networking_acronyms.md)**
    - **When:** Need quick reference for acronyms

---

#### **4.3 Technology Selection**

57. **[Virtualization Technology Primer](06_reference/decision_frameworks/01_virtualization_primer.md)**
    - **When:** Choosing virtualization technology
    - **NOTE:** Read AFTER understanding fundamentals (Part 2.3)

---

## Quick Start Guides

For those who want rapid overviews before deep dives:

- **[Quick Start: Virtualization](quick_start_virtualization.md)** - Essential virtualization concepts
- **[Quick Start: Networking](quick_start_networking.md)** - Essential networking concepts
- **[Quick Start: Containers](quick_start_containers.md)** - Container fundamentals through Kubernetes
- **[Quick Start: Full Stack](quick_start_full_stack.md)** - Complete overview of all topics

---

## Document Metadata

All documents include YAML frontmatter with:
- **level:** foundational | intermediate | specialized | reference
- **estimated_time:** Individual document estimate (for reference, not path planning)
- **prerequisites:** What to read first
- **next_recommended:** Suggested next documents
- **tags:** Topical categorization

---

## Original Documents

All original documents are preserved in `original_docs/` for reference.

---

## Need Help?

- **Stuck on a concept?** Check prerequisites and read foundational documents first
- **Can't find something?** Use the [Networking Acronyms Glossary](06_reference/learning_resources/02_networking_acronyms.md)
- **Want to go deeper?** Each document has "Next Recommended" links

---

**Ready to begin?**
- **Virtualization track:** Start with [The Ring-0 Problem](01_foundations/01_virtualization_basics/01_the_ring0_problem.md) 🎯
- **Container track:** Start with [Linux Container Primitives](04_containers/01_fundamentals/01_cgroups_namespaces.md) 📦
- **Quick overview:** Try a [Quick Start Guide](#quick-start-guides)
