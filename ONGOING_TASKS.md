# Ongoing Tasks & Future Enhancements

**Repository:** https://github.com/skeptomai/datacenter-curriculum
**Last Updated:** 2026-02-14

---

## 🎯 Immediate Next Steps

### 1. GitHub Repository Configuration
- [ ] **Add repository topics/tags** for discoverability:
  - virtualization
  - networking
  - datacenter
  - rdma
  - kvm
  - learning-resources
  - infrastructure
  - curriculum
  - educational

### 2. GitHub Pages Setup
- [ ] **Enable GitHub Pages** to host HTML documentation
  - Configure to serve from `/docs` or use GitHub Actions to build
  - Add custom domain (optional)
  - Enable HTTPS

### 3. Contributing Guidelines
- [ ] **Create CONTRIBUTING.md** with:
  - How to propose new content
  - Style guidelines for documentation
  - YAML frontmatter requirements
  - Pull request process
  - Code of conduct

### 4. Issue Templates
- [ ] **Create GitHub issue templates** for:
  - Content corrections/updates
  - New topic requests
  - Translation proposals
  - General questions

### 5. Automation
- [ ] **Add GitHub Actions workflow** to:
  - Auto-generate HTML on push
  - Validate YAML frontmatter
  - Check for broken links
  - Deploy to GitHub Pages

---

## 🚨 CRITICAL CONTENT GAP: Container & Orchestration Curriculum

**Priority:** HIGHEST - Major infrastructure category missing

### Current State
The curriculum has limited container coverage:
- Brief mentions in Firecracker docs (comparing microVMs to containers)
- Kata Containers referenced (1 paragraph)
- Some Kubernetes/pod references in networking contexts
- Network namespaces in overlay networking

### What's Missing: Complete Container Stack

This represents **20-25 hours of learning content** across a new major category:

#### Proposed Structure Option A: Specialized Section
```
03_specialized/06_containers/
├── 01_fundamentals/          (3 documents, ~2.5 hours)
│   ├── 01_cgroups_namespaces.md
│   ├── 02_union_filesystems.md
│   └── 03_container_vs_vm.md
├── 02_runtimes/              (4 documents, ~3 hours)
│   ├── 01_runtime_landscape.md
│   ├── 02_docker_containerd.md
│   ├── 03_kata_gvisor.md
│   └── 04_runtime_comparison.md
├── 03_orchestration/         (6 documents, ~6 hours)
│   ├── 01_kubernetes_architecture.md
│   ├── 02_pods_workloads.md
│   ├── 03_services_networking.md
│   ├── 04_scheduling_resources.md
│   ├── 05_storage_volumes.md
│   └── 06_production_patterns.md
├── 04_networking/            (5 documents, ~5 hours)
│   ├── 01_cni_overview.md
│   ├── 02_calico_vs_cilium.md
│   ├── 03_ebpf_networking.md
│   ├── 04_service_mesh.md
│   └── 05_network_policies.md
└── 05_security/              (4 documents, ~3.5 hours)
    ├── 01_image_security.md
    ├── 02_runtime_security.md
    ├── 03_pod_security.md
    └── 04_supply_chain.md
```

#### Proposed Structure Option B: Top-Level Section (Preferred)
```
docs/04_containers/           (New major section)
├── README.md
├── 01_fundamentals/
├── 02_runtimes/
├── 03_orchestration/
├── 04_networking/
└── 05_security/

docs/05_specialized/          (Renumber existing 03_specialized)
docs/06_reference/            (Renumber existing 04_reference)
```

### Topics to Cover

**Container Fundamentals:**
- Linux primitives: cgroups (v1/v2), namespaces (pid, net, mnt, uts, ipc, user)
- Capabilities, seccomp, AppArmor, SELinux
- Union filesystems: OverlayFS, AUFS, device mapper
- Container images: OCI spec, layers, registries, manifest
- Process isolation vs VM isolation (comparison with existing virt content)

**Container Runtimes:**
- Runtime hierarchy: CRI → containerd/CRI-O → runc/crun
- Docker architecture and evolution
- containerd deep dive
- Kata Containers (VM-isolated containers)
- gVisor (runsc) - userspace kernel
- Firecracker integration (links to existing 03_serverless content)
- Runtime comparison matrix

**Kubernetes Orchestration:**
- Control plane: API server, etcd, scheduler, controller manager
- Node components: kubelet, kube-proxy, container runtime
- Pod lifecycle and design patterns
- Workload resources: Deployments, StatefulSets, DaemonSets, Jobs, CronJobs
- Services: ClusterIP, NodePort, LoadBalancer, ExternalName
- Ingress and Gateway API
- ConfigMaps and Secrets
- Scheduling: affinity/anti-affinity, taints/tolerations, resource limits
- Storage: PersistentVolumes, StorageClasses, CSI drivers
- Production patterns: rolling updates, blue-green, canary

**Container Networking (Deep Integration with 02_intermediate/01_advanced_networking):**
- CNI specification and plugin architecture
- CNI plugins comparison: Calico, Cilium, Flannel, Weave
- eBPF-based networking (Cilium deep dive)
- Service mesh: Istio, Linkerd, architecture
- Network policies and micro-segmentation
- Service discovery and load balancing
- Integration with VXLAN overlays (cross-reference existing content)

**Container Security:**
- Image security: scanning, signing, trusted registries, admission controllers
- Runtime security: seccomp profiles, AppArmor/SELinux policies
- Pod Security Standards (Privileged, Baseline, Restricted)
- RBAC and service accounts
- Supply chain security: SBOM, SLSA, provenance
- Security monitoring and runtime detection

### New Learning Path Required

**Path 5: Container Platform Engineer (20-25 hours)**
```
Prerequisites: 01_foundations/01_virtualization_basics (understand isolation concepts)
    ↓
04_containers/01_fundamentals (2.5h)
    ↓
04_containers/02_runtimes (3h)
    ↓
04_containers/03_orchestration (6h)
    ↓
04_containers/04_networking (5h) + 02_intermediate/01_advanced_networking
    ↓
04_containers/05_security (3.5h)
    ↓
Optional: 03_specialized/03_serverless (Kata/Firecracker integration)
```

### Integration Points with Existing Content

- **01_foundations/01_virtualization_basics** ← Container fundamentals build on isolation concepts
- **02_intermediate/01_advanced_networking** ← CNI integrates with VXLAN/overlays
- **02_intermediate/02_rdma** ← RDMA for distributed storage in K8s
- **03_specialized/02_overlay_networking** ← Cilium/Calico use VXLAN/BGP
- **03_specialized/03_serverless** ← Kata Containers/Firecracker connection

### Execution Plan Required

See **CONTAINER_CURRICULUM_PLAN.md** (to be created) for:
- Research phase (identifying authoritative sources)
- Content analysis and gap identification
- Curriculum design and prerequisites mapping
- Content creation workflow
- Review and integration process
- Estimated timeline and milestones

---

## 📚 Content Enhancements (From Original Plan)

### Interactive Features
- [ ] **Interactive HTML Navigation**
  - Add progress tracking to HTML version
  - Create interactive curriculum map
  - Add search functionality
  - Implement bookmarking system

### Learning Path Badges
- [ ] **Visual Progress Indicators**
  - Add visual progress indicators
  - Create completion certificates
  - Track time investment
  - Milestone achievements

### Content Updates
- [ ] **Keep Technology Info Current**
  - Update link speeds as standards evolve (25G → 100G → 400G)
  - Add examples as technology evolves
  - Update protocol versions (RDMA, VXLAN, etc.)
  - Refresh performance benchmarks

### Expand Specialized Topics
- [ ] **Add New Specialization Areas**
  - Security (encryption, attestation, isolation)
  - Observability (monitoring, tracing, metrics)
  - Container networking (CNI, service mesh)
  - GPU virtualization and passthrough
  - Disaggregated infrastructure

### Translation
- [ ] **Multi-language Support**
  - Translate to other languages
  - Maintain same structure across languages
  - Add language switcher to HTML version

---

## 🛠️ Technical Improvements

### Build System
- [ ] **Enhance Build Scripts**
  - Add makefile for common operations
  - Create dev container for consistent environment
  - Add validation scripts (link checker, YAML validator)

### Documentation Quality
- [ ] **Add More Diagrams**
  - Convert ASCII art to SVG/PNG where helpful
  - Add architecture diagrams
  - Create flowcharts for decision trees

### Testing & Validation
- [ ] **Create Test Suite**
  - Validate all cross-references work
  - Check YAML frontmatter consistency
  - Verify time estimates are reasonable
  - Test HTML generation on all platforms

---

## 🎓 Educational Features

### Hands-on Labs
- [ ] **Create Practical Exercises**
  - Lab environments (KVM setup, network simulation)
  - Step-by-step tutorials
  - Quiz questions at end of sections
  - Practice problems

### Video Content
- [ ] **Companion Videos** (if desired)
  - Record walkthroughs of complex topics
  - Create visual explanations of diagrams
  - Interview experts

### Community
- [ ] **Build Learning Community**
  - Set up discussion board (GitHub Discussions)
  - Create study group template
  - Office hours or Q&A sessions

---

## 📊 Analytics & Feedback

### Tracking
- [ ] **Add Analytics** (optional)
  - Track which paths are most popular
  - Monitor completion rates
  - Identify difficult sections

### Feedback Mechanism
- [ ] **Collect User Feedback**
  - Add feedback forms
  - Create user survey
  - Track issue patterns

---

## 🔄 Maintenance

### Regular Updates
- [ ] **Quarterly Review**
  - Check for outdated information
  - Update link speeds and standards
  - Refresh examples

### Community Contributions
- [ ] **Review and Merge PRs**
  - Monitor pull requests
  - Review contributed content
  - Update acknowledgments

---

## 💡 Future Ideas (Brainstorming)

- **Mobile-friendly version** with app
- **Spaced repetition system** for key concepts
- **Integration with learning platforms** (Coursera, edX)
- **Certification program** (unofficial)
- **Podcast series** covering each learning path
- **Jupyter notebooks** for interactive exploration
- **Docker-based lab environment** for hands-on practice
- **AI chatbot** to answer questions about content
- **Comparison tables** for technology selection
- **Real-world case studies** from production environments

---

## 📝 Notes

### Principles to Maintain
- Keep pedagogical structure (foundations → intermediate → specialized)
- Maintain explicit prerequisites
- Preserve time estimates
- Follow YAML frontmatter conventions
- Keep all original content in archive/

### When Adding New Content
1. Determine appropriate level (foundational/intermediate/specialized/reference)
2. Add YAML frontmatter with all required fields
3. Update relevant learning paths in 00_START_HERE.md
4. Add to appropriate directory README
5. Test HTML generation
6. Update REORGANIZATION_SUMMARY.md if structure changes

---

**Status Key:**
- [ ] Not started
- [x] Completed
- [~] In progress
- [-] Blocked/Deferred
