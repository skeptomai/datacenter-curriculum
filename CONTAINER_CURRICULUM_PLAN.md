# Container & Orchestration Curriculum: Research & Content Plan

**Scope:** 22 documents covering container fundamentals through Kubernetes production deployments
**Structure:** Top-level section (docs/04_containers/) with existing sections renumbered
**Created:** 2026-02-14

---

## Content Structure (Option B - Top-Level Section)

```
docs/04_containers/
├── README.md
├── 01_fundamentals/              (3 documents, ~2.5 hours)
│   ├── 01_cgroups_namespaces.md
│   ├── 02_union_filesystems.md
│   └── 03_container_vs_vm.md
├── 02_runtimes/                  (4 documents, ~3 hours)
│   ├── 01_runtime_landscape.md
│   ├── 02_docker_containerd.md
│   ├── 03_kata_gvisor.md
│   └── 04_runtime_comparison.md
├── 03_orchestration/             (6 documents, ~6 hours)
│   ├── 01_kubernetes_architecture.md
│   ├── 02_pods_workloads.md
│   ├── 03_services_networking.md
│   ├── 04_scheduling_resources.md
│   ├── 05_storage_volumes.md
│   └── 06_production_patterns.md
├── 04_networking/                (5 documents, ~5 hours)
│   ├── 01_cni_overview.md
│   ├── 02_calico_vs_cilium.md
│   ├── 03_ebpf_networking.md
│   ├── 04_service_mesh.md
│   └── 05_network_policies.md
└── 05_security/                  (4 documents, ~3.5 hours)
    ├── 01_image_security.md
    ├── 02_runtime_security.md
    ├── 03_pod_security.md
    └── 04_supply_chain.md

docs/05_specialized/              (renumbered from 03_specialized)
docs/06_reference/                (renumbered from 04_reference)
```

**Additional files:**
- `quick_start_containers.md` (2-3 hour overview)
- Update `00_START_HERE.md` with Path 5
- Update `README.md` with container topics

**Total: 22 core documents + 3 integration documents**

---

## Research Sources

### Official Specifications & Documentation

**OCI (Open Container Initiative)**
- Runtime Specification: https://github.com/opencontainers/runtime-spec
- Image Specification: https://github.com/opencontainers/image-spec
- Distribution Specification: https://github.com/opencontainers/distribution-spec
- Use for: Authoritative definitions of container standards

**Kubernetes**
- Official Documentation: https://kubernetes.io/docs/
- Concepts: https://kubernetes.io/docs/concepts/
- Reference: https://kubernetes.io/docs/reference/
- KEPs (Kubernetes Enhancement Proposals): https://github.com/kubernetes/enhancements
- Use for: K8s architecture, API objects, design decisions

**Linux Kernel**
- cgroups v2: https://docs.kernel.org/admin-guide/cgroup-v2.html
- Namespaces: https://man7.org/linux/man-pages/man7/namespaces.7.html
- Capabilities: https://man7.org/linux/man-pages/man7/capabilities.7.html
- Use for: Low-level container primitives

**Container Runtimes**
- containerd: https://containerd.io/docs/
- CRI-O: https://cri-o.io/
- Docker Engine: https://docs.docker.com/engine/
- runc: https://github.com/opencontainers/runc
- Use for: Runtime implementation details

**Container Networking**
- CNI Specification: https://github.com/containernetworking/cni/blob/main/SPEC.md
- Cilium: https://docs.cilium.io/
- Calico: https://docs.tigera.io/calico/latest/about/
- Istio: https://istio.io/latest/docs/
- Use for: Networking architecture and plugin details

**Secure Runtimes**
- Kata Containers: https://katacontainers.io/docs/
- gVisor: https://gvisor.dev/docs/
- Use for: VM-isolated container approaches

### Technical Books

**"Kubernetes in Action" (2nd Edition)** - Marko Lukša
- Comprehensive K8s coverage from basics to advanced
- Excellent for pod patterns and workload design
- Good production practices

**"Container Security"** - Liz Rice
- Deep dive into Linux container primitives
- Security boundaries and isolation
- Runtime security practices

**"Kubernetes Patterns"** - Bilgin Ibryam & Roland Huß
- Production deployment patterns
- Design principles for cloud-native apps
- Best practices catalog

**"Docker Deep Dive"** - Nigel Poulton
- Container fundamentals
- Image layering and registries
- Docker networking basics

**"Programming Kubernetes"** - Michael Hausenblas & Stefan Schimanski
- K8s API internals
- Controller patterns
- Extension mechanisms
- Use for: Deep technical understanding

### Research Papers & Whitepapers

**Container Isolation & Security**
- "My VM is Lighter (and Safer) than your Container" - Kata Containers architecture
- "gVisor: Building and Battle Testing a Userspace OS in Go" - Google's approach to container security

**Orchestration History**
- "Borg, Omega, and Kubernetes" - Google CACM 2016 (evolution of cluster management)
- "Large-scale cluster management at Google with Borg" - EuroSys 2015 (Borg architecture)

**Performance Studies**
- Container networking performance comparisons (academic papers)
- Storage overhead studies
- Security isolation benchmarks
- Use for: Understanding tradeoffs

### Industry Engineering Blogs

**Primary Sources:**
- CNCF Blog: https://www.cncf.io/blog/
- Kubernetes Blog: https://kubernetes.io/blog/
- Google Cloud Blog: https://cloud.google.com/blog (GKE, container internals)
- Red Hat Blog: https://www.redhat.com/en/blog (OpenShift, container tech)
- Cilium Blog: https://cilium.io/blog/ (eBPF networking)
- Isovalent Blog: https://isovalent.com/blog/ (eBPF deep dives)
- Aqua Security: https://blog.aquasec.com/ (container security research)

**Use for:** Real-world implementation details, performance insights, security best practices

### Source Code (Reference Only)

When implementation details are needed:
- runc: https://github.com/opencontainers/runc
- containerd: https://github.com/containerd/containerd
- Kubernetes components: https://github.com/kubernetes/kubernetes
- CNI plugins: https://github.com/containernetworking/plugins
- Cilium: https://github.com/cilium/cilium

**Use for:** Understanding low-level mechanics, not for general explanations

### Test Environment Tutorials

**For Examples & Validation:**

**Local Kubernetes:**
- minikube: https://minikube.sigs.k8s.io/docs/start/
- kind (Kubernetes in Docker): https://kind.sigs.k8s.io/
- k3s (lightweight): https://k3s.io/

**Container Runtimes:**
- Docker Desktop: https://docs.docker.com/get-docker/
- containerd + nerdctl: https://github.com/containerd/containerd/blob/main/docs/getting-started.md
- Podman: https://podman.io/getting-started/

**Kata Containers:**
- Installation guide: https://github.com/kata-containers/kata-containers/blob/main/docs/install/README.md

**gVisor:**
- Quick start: https://gvisor.dev/docs/user_guide/quick_start/docker/

---

## Topic Breakdown & Learning Objectives

### 01_fundamentals/ (3 documents)

**01_cgroups_namespaces.md**
- Linux process isolation primitives
- cgroups v1 vs v2 (resource limiting)
- 7 namespace types (pid, net, mnt, uts, ipc, user, cgroup)
- How containers use these primitives
- Security boundaries and limitations
- Integration: Links to 01_foundations/01_virtualization_basics (compare to VM isolation)

**02_union_filesystems.md**
- Copy-on-write filesystems
- OverlayFS mechanics (lower/upper/merged directories)
- Image layering (how layers stack)
- Storage drivers comparison (overlay2, devicemapper, etc.)
- Performance implications

**03_container_vs_vm.md**
- Isolation comparison (process vs hardware)
- Performance characteristics
- Security boundaries
- When to use each
- Hybrid approaches (Kata Containers preview)
- Integration: Deep cross-reference to existing VM content

### 02_runtimes/ (4 documents)

**01_runtime_landscape.md**
- Runtime hierarchy: CRI → high-level → low-level
- OCI runtime spec overview
- CRI (Container Runtime Interface)
- Runtime responsibilities at each layer

**02_docker_containerd.md**
- Docker architecture evolution
- containerd as standalone runtime
- containerd vs Docker Engine
- runc (reference OCI implementation)
- Alternative low-level runtimes (crun)

**03_kata_gvisor.md**
- Why stronger isolation is needed
- Kata Containers: containers in lightweight VMs
- gVisor: userspace kernel approach
- Performance vs security tradeoffs
- Integration: Links to 03_specialized/03_serverless (Firecracker)

**04_runtime_comparison.md**
- Decision matrix for runtime selection
- Performance benchmarks
- Security isolation levels
- Use case alignment
- Quick reference table

### 03_orchestration/ (6 documents)

**01_kubernetes_architecture.md**
- Control plane components (API server, etcd, scheduler, controller manager)
- Node components (kubelet, kube-proxy, container runtime)
- How components interact
- Request flow (kubectl → API → scheduler → kubelet)

**02_pods_workloads.md**
- Pod: fundamental unit
- Pod design patterns (sidecar, adapter, ambassador)
- Deployments (replica management, rolling updates)
- StatefulSets (stable network identity, ordered deployment)
- DaemonSets (one pod per node)
- Jobs and CronJobs

**03_services_networking.md**
- Service types (ClusterIP, NodePort, LoadBalancer, ExternalName)
- Service discovery (DNS)
- kube-proxy modes (iptables, ipvs, eBPF)
- Ingress and Gateway API
- Integration: Links to 02_intermediate networking content

**04_scheduling_resources.md**
- Scheduler algorithm
- Node affinity and anti-affinity
- Taints and tolerations
- Resource requests and limits
- Quality of Service (QoS) classes
- Topology spread constraints

**05_storage_volumes.md**
- Volume types (emptyDir, hostPath, configMap, secret)
- PersistentVolumes and PersistentVolumeClaims
- StorageClasses and dynamic provisioning
- CSI (Container Storage Interface)
- StatefulSet storage patterns
- Integration: Can reference RDMA storage backends from existing content

**06_production_patterns.md**
- Rolling updates and rollbacks
- Blue-green deployments
- Canary deployments
- Health checks (liveness, readiness, startup probes)
- Resource quotas and limits
- HorizontalPodAutoscaler
- Production readiness checklist

### 04_networking/ (5 documents)

**01_cni_overview.md**
- CNI specification
- Plugin architecture
- How CNI integrates with kubelet
- Network plugin categories (overlay, routed, etc.)

**02_calico_vs_cilium.md**
- Calico architecture (BGP-based)
- Cilium architecture (eBPF-based)
- Feature comparison
- Performance characteristics
- When to use each

**03_ebpf_networking.md**
- What is eBPF (extended Berkeley Packet Filter)
- eBPF in kernel networking
- How Cilium uses eBPF
- Performance benefits
- Observability capabilities

**04_service_mesh.md**
- Service mesh value proposition
- Istio architecture (control plane, data plane)
- Linkerd comparison
- Sidecar proxy pattern (Envoy)
- When you need a service mesh

**05_network_policies.md**
- NetworkPolicy API
- Default deny / allow patterns
- Ingress and egress rules
- Namespace-based isolation
- Micro-segmentation
- Integration: Links to VXLAN/overlay content from existing docs

### 05_security/ (4 documents)

**01_image_security.md**
- Image scanning (vulnerability detection)
- Image signing and verification
- Trusted registries
- Admission controllers (validating/mutating webhooks)
- Supply chain attacks on images

**02_runtime_security.md**
- seccomp profiles
- AppArmor and SELinux
- Runtime security tools
- Detecting container escapes
- Principle of least privilege

**03_pod_security.md**
- Pod Security Standards (Privileged, Baseline, Restricted)
- Security contexts (runAsNonRoot, capabilities, etc.)
- RBAC (Role-Based Access Control)
- Service accounts
- Network policies (cross-ref to 04_networking/05)

**04_supply_chain.md**
- SBOM (Software Bill of Materials)
- SLSA framework (Supply-chain Levels for Software Artifacts)
- Provenance and attestation
- Sigstore and cosign
- Policy enforcement (OPA/Gatekeeper)

---

## Integration with Existing Content

### Prerequisites Mapping

**Container Fundamentals** ← 01_foundations/01_virtualization_basics
- Builds on understanding of isolation concepts
- Compares process isolation to hardware virtualization

**Container Networking** ← 02_intermediate/01_advanced_networking
- CNI overlays use VXLAN (existing overlay networking content)
- Service mesh integrates with datacenter networking

**Kubernetes Storage** ← 02_intermediate/02_rdma
- Can use RDMA-backed storage for distributed systems
- NVMe-oF as CSI driver

**Kata Containers** ← 03_specialized/03_serverless
- Firecracker used as Kata runtime option
- Security isolation comparison

**Container Networking** ← 05_specialized/02_overlay_networking (renumbered)
- Cilium/Calico use BGP EVPN
- Deep integration with existing overlay content

### Cross-References to Add

**In existing documents:**
- 01_foundations/01_virtualization_basics/03_vm_exit_basics.md → Add note comparing to container syscall overhead
- 02_intermediate/01_advanced_networking/01_vlan_vs_vxlan.md → Add Kubernetes CNI as VXLAN use case
- 03_specialized/03_serverless/02_firecracker_deep_dive.md → Add Kata Containers integration section

**New learning path:**
- Path 5: Container Platform Engineer (20-25 hours)

---

## New Learning Path: Path 5

**Container Platform Engineer (20-25 hours)**

**Prerequisites:**
- Basic Linux knowledge (assumed)
- 01_foundations/01_virtualization_basics (1.5 hours) - understand isolation

**Path:**
```
Start: 04_containers/01_fundamentals/ (2.5 hours)
  ↓
04_containers/02_runtimes/ (3 hours)
  ↓
04_containers/03_orchestration/ (6 hours)
  ↓
04_containers/04_networking/ (5 hours)
  + Read: 02_intermediate/01_advanced_networking/ (for VXLAN context)
  ↓
04_containers/05_security/ (3.5 hours)
  ↓
Optional: 05_specialized/03_serverless/ (Kata/Firecracker integration)
```

**Outcome:** Deploy and operate production Kubernetes clusters with understanding of underlying container mechanics, networking, and security.

---

## Quick Start Guide

**quick_start_containers.md (2-3 hours)**

**Structure:**
- Container fundamentals (30 min): cgroups, namespaces, images
- Docker/containerd basics (20 min): Running containers, image building
- Kubernetes essentials (60 min): Pods, deployments, services
- Networking overview (20 min): CNI, service mesh intro
- Security basics (20 min): Image scanning, pod security

**Purpose:** Rapid overview for developers familiar with VMs or experienced engineers needing container crash course.

---

## Content Creation Standards

**Every document must include:**
- YAML frontmatter (level, estimated_time, prerequisites, next_recommended, tags)
- Clear learning objectives (3-5 bullet points)
- Progressive complexity (simple concepts first)
- Minimum 2 diagrams (ASCII art)
- Practical examples (code snippets, configurations)
- "What You've Learned" summary
- "Next Steps" with cross-references
- Quick reference section (commands, key concepts)

**Quality standards:**
- Technical accuracy verified against official docs
- No assumptions beyond stated prerequisites
- Gender-neutral language
- Consistent terminology with existing curriculum
- Code examples tested (where applicable)

**Diagram standards:**
- ASCII art for architecture (matches existing style)
- Clear component relationships
- Minimal but sufficient detail

**Example quality:**
- Use recent versions (K8s 1.29+, containerd 1.7+)
- Include comments for non-obvious parts
- Provide context (what problem does this solve?)

---

## Document Template

```markdown
---
level: foundational | intermediate | specialized
estimated_time: XX min
prerequisites:
  - path/to/prerequisite.md
next_recommended:
  - path/to/next.md
tags: [containers, kubernetes, etc.]
---

# [Document Title]

**Learning Objectives:**
- Understand X
- Explain Y
- Apply Z

---

## Introduction

[What problem does this solve? Brief context.]

## Core Concepts

[Fundamental explanation, build from first principles]

### Diagram: [Component Architecture]

[ASCII art diagram]

## Deep Dive

[Implementation details, how it works]

## Practical Examples

[Code, configurations, real-world usage]

## Integration & Context

[How this fits in the stack, related technologies, cross-references]

## Quick Reference

[Key commands, decision matrix, common patterns]

---

## What You've Learned

✅ [Summary checklist]

## Next Steps

→ Continue: [Next recommended reading]
```

---

## Structural Changes Required

**Renumber existing directories:**
```bash
git mv docs/03_specialized docs/05_specialized
git mv docs/04_reference docs/06_reference
```

**Create new structure:**
```bash
mkdir -p docs/04_containers/{01_fundamentals,02_runtimes,03_orchestration,04_networking,05_security}
```

**Update files:**
- docs/00_START_HERE.md (add Path 5)
- README.md (update topics covered, stats)
- All links in 03_specialized → update to 05_specialized
- All links in 04_reference → update to 06_reference

---

## Success Criteria

**Quantitative:**
- 22 core documents created
- All YAML frontmatter complete
- 100% internal links valid
- HTML generation successful

**Qualitative:**
- Technical accuracy matches official docs
- Pedagogical quality matches existing content
- Clear learning progression
- Useful as standalone resource

---

## Content Creation Order

**Suggested sequence (not timeline-based):**

1. **Fundamentals** (3 docs) - Foundation for everything else
2. **Runtimes** (4 docs) - Builds on fundamentals
3. **Orchestration Part 1** (docs 1-3) - Core K8s concepts
4. **Orchestration Part 2** (docs 4-6) - Advanced K8s
5. **Networking** (5 docs) - Requires orchestration understanding
6. **Security** (4 docs) - Applies across all layers
7. **Integration** (quick start, Path 5, updates)

**Rationale:** Each section builds on previous, enabling progressive learning.

---

## Ready to Begin

**First steps:**
1. Start with OCI and Kubernetes official documentation
2. Read "Container Security" by Liz Rice for fundamentals
3. Review existing virtualization docs to ensure complementary coverage
4. Begin with 01_cgroups_namespaces.md (foundational document)
