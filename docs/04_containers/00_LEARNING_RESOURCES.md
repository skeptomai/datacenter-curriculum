---
title: "Complete Container Learning Resources"
depth: reference
topic: "Containers"
---

# Complete Container Learning Resources 📚

**Comprehensive collection of external tutorials, code repositories, and hands-on labs**

This document provides a curated list of external resources to complement your learning. Each section corresponds to topics in the container curriculum and includes tutorials for hands-on practice and code repositories to study real implementations.

> 💡 **Using this guide:**
> - Resources are organized by topic matching the curriculum structure
> - Each resource includes difficulty level and what you'll learn
> - Code repositories marked with ⭐ are especially good for learning
> - Links are verified as of 2026-02-15

---

## Table of Contents

1. [Container Fundamentals](#1-container-fundamentals)
2. [Container Runtimes](#2-container-runtimes)
3. [Kubernetes Orchestration](#3-kubernetes-orchestration)
4. [Container Networking](#4-container-networking)
5. [Container Security](#5-container-security)
6. [Practice Environments](#6-practice-environments)
7. [Books and Long-Form Content](#7-books-and-long-form-content)

---

## 1. Container Fundamentals

### Tutorials & Guides

**Building Containers from Scratch:**
- **[Containers from Scratch](https://ericchiang.github.io/post/containers-from-scratch/)** (Eric Chiang)
  - Build a container in ~40 lines of C
  - Learn: Namespaces, pivot_root, basic isolation
  - Difficulty: Intermediate

- **[Linux Containers in 500 Lines of Code](https://blog.lizzie.io/linux-containers-in-500-loc.html)** (Lizzie Dixon)
  - Step-by-step container implementation
  - Learn: Namespaces, cgroups, mount points, networking
  - Difficulty: Intermediate

- **[Namespaces in Go](https://medium.com/@teddyking/namespaces-in-go-basics-e3f0fc1ff69a)** (Teddy King)
  - Series on implementing namespace isolation in Go
  - Learn: Each namespace type explained with code
  - Difficulty: Beginner to Intermediate

**Docker Getting Started:**
- **[Docker Official Tutorial](https://docs.docker.com/get-started/)**
  - Interactive hands-on with Docker
  - Learn: Images, containers, volumes, networking basics
  - Difficulty: Beginner

- **[Play with Docker](https://labs.play-with-docker.com/)**
  - Free browser-based Docker environment
  - No installation required
  - Difficulty: Beginner

### Code Repositories to Study

**Minimal Container Implementations** (⭐ Best for learning):

- **[bocker](https://github.com/p8952/bocker)** ⭐
  - Docker implemented in ~100 lines of bash
  - Shows core concepts without language complexity
  - Great for understanding what Docker actually does

- **[minc](https://github.com/mhiramat/minc)** ⭐
  - Minimal container implementation in C
  - ~1000 lines, very readable
  - Covers namespaces, cgroups, overlayfs

- **[contained.af](https://github.com/genuinetools/contained.af)** ⭐
  - Educational container runtime by Jessie Frazelle
  - Well-documented Go code
  - Shows modern best practices

**Namespace & cgroup Examples:**

- **[containers-from-scratch](https://github.com/lizrice/containers-from-scratch)** (Liz Rice)
  - Progressive examples building up container features
  - Each commit adds one feature
  - Excellent for step-by-step learning

- **[ns-exec](https://github.com/iffyio/ns-exec)**
  - Tool to execute commands in existing namespaces
  - Simple, focused codebase
  - Learn: Namespace manipulation

### Interactive Labs

- **[Katacoda: Container Fundamentals](https://www.katacoda.com/courses/container-runtimes)**
  - Free browser-based interactive scenarios
  - Covers namespaces, cgroups, and container internals

---

## 2. Container Runtimes

### Official Specifications

- **[OCI Runtime Specification](https://github.com/opencontainers/runtime-spec)**
  - Defines what a container runtime must do
  - Includes config.json format and runtime operations

- **[OCI Image Specification](https://github.com/opencontainers/image-spec)**
  - Container image format and distribution

- **[OCI Distribution Specification](https://github.com/opencontainers/distribution-spec)**
  - Registry API for pulling/pushing images

- **[CRI (Container Runtime Interface)](https://github.com/kubernetes/cri-api)**
  - Kubernetes runtime interface specification

### Production Runtime Implementations

**Low-level OCI Runtimes:**

- **[runc](https://github.com/opencontainers/runc)** ⭐
  - Reference OCI runtime implementation (Go)
  - Used by Docker, containerd, Podman
  - ~15k lines, well-structured
  - Learn: Complete OCI runtime implementation

- **[crun](https://github.com/containers/crun)** ⭐
  - Fast OCI runtime in C
  - 2-3x faster startup than runc
  - Learn: Performance-optimized implementation

- **[youki](https://github.com/containers/youki)** ⭐
  - OCI runtime in Rust
  - Modern, safe implementation
  - Learn: Systems programming in Rust

**High-level Container Managers:**

- **[containerd](https://github.com/containerd/containerd)**
  - Industry-standard high-level runtime
  - Used by Docker, Kubernetes
  - Learn: Image management, lifecycle orchestration

- **[CRI-O](https://github.com/cri-o/cri-o)**
  - Lightweight Kubernetes-specific runtime
  - Direct CRI implementation
  - Learn: Kubernetes runtime integration

- **[Podman](https://github.com/containers/podman)**
  - Daemonless container engine
  - Docker-compatible CLI
  - Learn: Rootless containers, systemd integration

**Specialized Runtimes:**

- **[gVisor (runsc)](https://github.com/google/gvisor)**
  - User-space kernel for containers
  - Enhanced isolation through syscall interception
  - Learn: Security-focused runtime design

- **[Kata Containers](https://github.com/kata-containers/kata-containers)**
  - Lightweight VMs as containers
  - Hardware-enforced isolation
  - Learn: VM/container hybrid approach

### Tutorials

- **[Building a Container Runtime](https://www.youtube.com/watch?v=_TsSmSu57Zo)** (Liz Rice)
  - Conference talk with live coding
  - Creates minimal runtime from scratch

- **[Implementing OCI Runtime Spec](https://github.com/opencontainers/runtime-spec/blob/main/implementations.md)**
  - Guide to implementing OCI runtime
  - Official documentation with examples

---

## 3. Kubernetes Orchestration

### Official Documentation & Tutorials

- **[Kubernetes Official Tutorials](https://kubernetes.io/docs/tutorials/)**
  - Comprehensive hands-on tutorials
  - Covers basics through advanced topics
  - Interactive and self-paced

- **[Kubernetes the Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)** ⭐
  - Build Kubernetes cluster from scratch (no automation)
  - Understand every component deeply
  - Difficulty: Advanced
  - Time: 8-12 hours

### Local Development Clusters

**Easy Setup (Recommended for Learning):**

- **[minikube](https://github.com/kubernetes/minikube)** ⭐
  - Full Kubernetes on laptop
  - Supports multiple container runtimes
  - Built-in addons (dashboard, metrics, ingress)

- **[kind (Kubernetes in Docker)](https://github.com/kubernetes-sigs/kind)** ⭐
  - Run K8s clusters in Docker containers
  - Fast, lightweight, ideal for testing
  - Used by Kubernetes CI/CD

- **[k3s](https://github.com/k3s-io/k3s)**
  - Lightweight Kubernetes (40MB binary)
  - Great for edge/IoT and learning
  - Production-ready but simpler

**Cloud-based Learning:**

- **[Play with Kubernetes](https://labs.play-with-k8s.com/)**
  - Free browser-based K8s environment
  - 4-hour sessions, no installation

- **[Katacoda: Kubernetes](https://www.katacoda.com/courses/kubernetes)**
  - Interactive scenarios in browser
  - Guided labs for specific topics

### Kubernetes Source Code

- **[Kubernetes](https://github.com/kubernetes/kubernetes)**
  - Full orchestration platform
  - Large codebase but well-organized
  - Start with: `staging/src/k8s.io/client-go/` (client library)

**Simpler K8s Components to Study:**

- **[kubernetes/sample-controller](https://github.com/kubernetes/sample-controller)**
  - Example custom controller
  - Learn: Controller pattern, informers, workqueues

- **[kubernetes-sigs/controller-runtime](https://github.com/kubernetes-sigs/controller-runtime)**
  - Framework for building controllers
  - Used by Operators

### Example Applications

- **[kubernetes/examples](https://github.com/kubernetes/examples)**
  - Official example workloads
  - Covers most K8s features

- **[GoogleCloudPlatform/microservices-demo](https://github.com/GoogleCloudPlatform/microservices-demo)**
  - 10-tier microservices app
  - Demonstrates services, deployments, monitoring

---

## 4. Container Networking

### CNI (Container Network Interface)

**Specifications & Documentation:**

- **[CNI Specification](https://github.com/containernetworking/cni/blob/main/SPEC.md)**
  - Official CNI plugin specification
  - Understand plugin API and lifecycle

**Reference Implementations:**

- **[CNI Plugins](https://github.com/containernetworking/plugins)** ⭐
  - Official reference plugins
  - Study: bridge, host-local, loopback, portmap
  - Start with: `plugins/main/bridge/` (most common)

**Writing CNI Plugins:**

- **[CNI Plugin Development Guide](https://www.cni.dev/docs/)**
  - Official guide to writing plugins

- **[Simple CNI Plugin Tutorial](https://www.altoros.com/blog/kubernetes-networking-writing-your-own-simple-cni-plug-in-with-bash/)**
  - Build basic CNI plugin in bash
  - Learn: CNI API, IPAM, routing

### Production Network Solutions

**Calico:**

- **[Project Calico](https://github.com/projectcalico/calico)**
  - Layer 3 networking with BGP
  - Network policy enforcement
  - Learn: BGP networking, eBPF dataplane

- **[Calico Getting Started](https://docs.tigera.io/calico/latest/getting-started/)**
  - Official tutorials and labs

**Cilium:**

- **[Cilium](https://github.com/cilium/cilium)** ⭐
  - eBPF-powered networking and security
  - Service mesh capabilities
  - Learn: eBPF networking, identity-based security

- **[Cilium Labs](https://github.com/cilium/cilium/tree/main/examples)**
  - Hands-on labs for Cilium features
  - Network policy, service mesh, observability

**Flannel:**

- **[Flannel](https://github.com/flannel-io/flannel)**
  - Simple overlay network
  - Good for learning basic concepts
  - Smaller, more approachable codebase

### eBPF (Extended Berkeley Packet Filter)

**Learning eBPF:**

- **[eBPF.io](https://ebpf.io/)**
  - Official eBPF website
  - Tutorials, documentation, use cases

- **[cilium/ebpf](https://github.com/cilium/ebpf)** ⭐
  - Pure Go eBPF library
  - Well-documented, easier to learn than C

- **[libbpf-bootstrap](https://github.com/libbpf/libbpf-bootstrap)**
  - Templates for eBPF programs in C
  - Minimal setup, good starting point

**eBPF Examples:**

- **[bpf-examples](https://github.com/xdp-project/bpf-examples)**
  - XDP (eXpress Data Path) examples
  - Packet processing at kernel level

- **[BPF Compiler Collection (bcc)](https://github.com/iovisor/bcc)**
  - Tools and examples for eBPF
  - Includes many networking examples

### Service Mesh

**Istio:**

- **[Istio](https://github.com/istio/istio)**
  - Full-featured service mesh
  - Learn: Envoy integration, mTLS, traffic management

- **[Istio Getting Started](https://istio.io/latest/docs/setup/getting-started/)**
  - Official hands-on tutorial

**Linkerd:**

- **[Linkerd2](https://github.com/linkerd/linkerd2)**
  - Lightweight Rust-based service mesh
  - Simpler than Istio, easier to understand

**Envoy:**

- **[Envoy Proxy](https://github.com/envoyproxy/envoy)**
  - L7 proxy used by Istio, Cilium
  - Large codebase but excellent docs

---

## 5. Container Security

### Vulnerability Scanning

**Image Scanners:**

- **[Trivy](https://github.com/aquasecurity/trivy)** ⭐
  - Comprehensive vulnerability scanner
  - Easy to use, great documentation
  - Tutorial: https://aquasecurity.github.io/trivy/

- **[Grype](https://github.com/anchore/grype)**
  - Vulnerability scanner from Anchore
  - Fast and accurate

- **[Clair](https://github.com/quay/clair)**
  - Container vulnerability analysis service
  - Used by Quay registry

### Runtime Security

**Falco (Runtime Threat Detection):**

- **[Falco](https://github.com/falcosecurity/falco)** ⭐
  - Runtime security using eBPF/kernel modules
  - Detects anomalous behavior
  - Getting Started: https://falco.org/docs/getting-started/

- **[Falco Rules](https://github.com/falcosecurity/rules)**
  - Detection rules repository
  - Learn what to monitor

**Seccomp, AppArmor, SELinux:**

- **[containers/common](https://github.com/containers/common/tree/main/pkg/seccomp)**
  - Default seccomp profiles for containers
  - Study which syscalls are allowed/denied

- **[Docker AppArmor Profile](https://github.com/moby/moby/tree/master/profiles/apparmor)**
  - Default AppArmor profile
  - Learn container confinement

### Supply Chain Security

**Sigstore (Image Signing):**

- **[cosign](https://github.com/sigstore/cosign)** ⭐
  - Container image signing and verification
  - Tutorial: https://docs.sigstore.dev/

- **[Rekor](https://github.com/sigstore/rekor)**
  - Transparency log for signatures
  - Immutable audit trail

**SBOM (Software Bill of Materials):**

- **[Syft](https://github.com/anchore/syft)**
  - Generate SBOMs from container images
  - Supports multiple formats (SPDX, CycloneDX)

### Policy Enforcement

**Admission Controllers:**

- **[OPA (Open Policy Agent)](https://github.com/open-policy-agent/opa)**
  - Policy engine using Rego language
  - Tutorial: https://www.openpolicyagent.org/docs/latest/kubernetes-tutorial/

- **[Gatekeeper](https://github.com/open-policy-agent/gatekeeper)**
  - OPA for Kubernetes admission control
  - CRD-based policy definitions

- **[Kyverno](https://github.com/kyverno/kyverno)**
  - Kubernetes-native policy engine
  - Simpler than OPA, uses YAML
  - Getting Started: https://kyverno.io/docs/introduction/

### Security Benchmarking

- **[kube-bench](https://github.com/aquasecurity/kube-bench)**
  - Check Kubernetes against CIS benchmarks
  - Automated security auditing

- **[docker-bench-security](https://github.com/docker/docker-bench-security)**
  - Security audit script for Docker
  - Checks CIS Docker benchmark

---

## 6. Practice Environments

### Free Interactive Labs

- **[Katacoda](https://www.katacoda.com/)** (being sunset, check alternatives)
  - Browser-based interactive scenarios
  - Kubernetes, Docker, networking labs

- **[Play with Docker](https://labs.play-with-docker.com/)**
  - Free 4-hour Docker instances
  - No installation required

- **[Play with Kubernetes](https://labs.play-with-k8s.com/)**
  - Free K8s cluster in browser
  - Great for quick testing

- **[Killercoda](https://killercoda.com/)**
  - Successor to Katacoda
  - Interactive learning scenarios

### Capture the Flag (CTF) & Challenges

- **[KubeCon CTF](https://controlplaneio.github.io/kubesec/)**
  - Kubernetes security challenges

- **[Kubernetes Goat](https://github.com/madhuakula/kubernetes-goat)**
  - Intentionally vulnerable K8s environment
  - Learn security through exploitation

### Local Lab Environments

- **[Vagrant + VirtualBox](https://www.vagrantup.com/)**
  - Reproducible dev environments
  - Can run multi-node clusters

- **[Lima](https://github.com/lima-vm/lima)**
  - Linux VMs on macOS
  - containerd integration

---

## 7. Books and Long-Form Content

### Books

**Container Fundamentals:**
- **"Container Security" by Liz Rice** (O'Reilly)
  - Comprehensive security coverage
  - Namespaces, capabilities, seccomp explained

**Kubernetes:**
- **"Kubernetes in Action" by Marko Lukša** (Manning)
  - Thorough K8s coverage from basics to advanced

- **"Programming Kubernetes" by Michael Hausenblas & Stefan Schimanski** (O'Reilly)
  - Building operators and controllers

- **"Kubernetes Patterns" by Bilgin Ibryam & Roland Huß** (O'Reilly)
  - Design patterns for cloud-native apps

**Networking:**
- **"Container Networking" by Michael Hausenblas** (O'Reilly)
  - From Docker networking to Kubernetes CNI

**eBPF:**
- **"Learning eBPF" by Liz Rice** (O'Reilly)
  - Comprehensive eBPF guide with examples

### Video Courses

- **[KodeKloud: Docker & Kubernetes](https://kodekloud.com/)**
  - Hands-on labs with certification prep
  - Interactive learning platform

- **[A Cloud Guru: Kubernetes Path](https://acloudguru.com/)**
  - Multiple K8s courses from beginner to expert

### Conference Talks (YouTube)

**Essential Viewing:**
- **Liz Rice's Container Talks**
  - "Containers from Scratch" (GOTO 2018)
  - "A Beginner's Guide to eBPF Programming" (Cloud Native Rejekts)

- **Kelsey Hightower's Kubernetes Talks**
  - "Kubernetes the Hard Way" demos
  - Architecture deep-dives

- **Cilium & eBPF Talks**
  - "eBPF - Rethinking the Linux Kernel" (Thomas Graf)
  - Cilium service mesh presentations

---

## 8. Community & Getting Help

### Forums & Chat

- **[Kubernetes Slack](https://kubernetes.slack.com/)**
  - Channels: #kubernetes-users, #kubernetes-novice

- **[CNCF Slack](https://cloud-native.slack.com/)**
  - Channels for specific projects (Cilium, Falco, etc.)

- **[Reddit: r/kubernetes](https://reddit.com/r/kubernetes)**
  - Community discussions and questions

- **[Stack Overflow](https://stackoverflow.com/questions/tagged/kubernetes)**
  - Technical Q&A with kubernetes, docker, containers tags

### Blogs & Newsletters

- **[CNCF Blog](https://www.cncf.io/blog/)**
  - Cloud-native ecosystem news

- **[Kubernetes Blog](https://kubernetes.io/blog/)**
  - Official project updates and tutorials

- **[Container Journal](https://containerjournal.com/)**
  - Industry news and best practices

---

## How to Use These Resources

### Suggested Learning Paths

**Path A: Hands-On First (Recommended for Beginners)**
1. Start with Docker Getting Started tutorial
2. Try Play with Docker for experimentation
3. Read curriculum fundamentals documents
4. Study bocker or minc source code
5. Move to Kubernetes tutorials

**Path B: Theory Then Practice**
1. Read curriculum documents first
2. Use resources here to validate understanding
3. Build/break things in practice environments
4. Study production implementations

**Path C: Code-First Learning**
1. Start with minimal implementations (bocker, minc)
2. Read curriculum to understand concepts
3. Study production code (runc, containerd)
4. Build your own tools

### Contributing

Found a great resource not listed here? Spotted a broken link?

- **Repository**: https://github.com/skeptomai/datacenter-curriculum
- **Open an issue** or submit a pull request
- See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines

---

**Last Updated**: 2026-02-15
**Maintained by**: The datacenter-curriculum project

> 💡 **Remember**: This is a reference guide. You don't need to complete every resource!
> Pick what matches your learning style and current goals. The curriculum documents provide
> the core knowledge - these resources offer different perspectives and hands-on practice.
