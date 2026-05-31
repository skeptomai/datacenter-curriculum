---
level: advanced
estimated_time: 50 min
prerequisites:
  - 04_containers/04_networking/02_calico_vs_cilium.md
  - 04_containers/04_networking/06_cni_selection_guide.md
  - 04_containers/05_security/03_pod_security.md
next_recommended:
  - 04_containers/05_security/01_image_security.md
tags: [security, compliance, fips, pci-dss, calico, wireguard, ipsec, k3s, encryption]
---

# Compliance in Kubernetes: FIPS 140-2/3 and PCI-DSS 4.0

**Learning Objectives:**
- Understand the FIPS 140-2 vs 140-3 distinction and its impact on CNI selection
- Map PCI-DSS 4.0 requirements to concrete Kubernetes controls
- Know when WireGuard is and is not acceptable for node-to-node encryption
- Configure Calico for a FIPS-compliant, PCI-auditable cluster

---

## Introduction

Most Kubernetes security documentation focuses on pod isolation and RBAC (Role-Based Access Control). But regulated environments — payment processing, healthcare, government — impose a different layer of constraints: the cryptographic primitives themselves must be validated by a recognized authority, and every network connection must be auditable.

This document covers the intersection of CNI (Container Network Interface) selection, node-to-node encryption, and compliance frameworks. It is particularly relevant for:
- Clusters processing payment card data (PCI-DSS 4.0 scope)
- US federal or FIPS-regulated deployments
- Environments running k3s or lightweight distributions that don't assume enterprise defaults

---

## 1. FIPS 140-2 vs FIPS 140-3: The Version That Matters

FIPS (Federal Information Processing Standard) 140 defines requirements for cryptographic modules. The US NIST (National Institute of Standards and Technology) certifies implementations.

**Timeline:**
```
FIPS 140-2  Issued 2001, deprecated for new certs → September 2026
FIPS 140-3  Issued 2019, current standard → ongoing

For Ubuntu 24.04 LTS:
  Canonical focuses certification on FIPS 140-3
  (FIPS 140-2 certifications for 24.04 packages are not being pursued)
```

**Why this matters for CNI selection:**

WireGuard uses ChaCha20-Poly1305 as its encryption primitive. This algorithm is not included in the set of NIST-approved algorithms under FIPS 140-2 and does not have a FIPS 140-3 validated implementation in the standard Linux kernel. As a result:

> **When Calico's FIPS mode is enabled, WireGuard is automatically disabled.** Calico's FIPS compliance mode switches to IPsec (via StrongSwan) backed by AES-GCM with FIPS-validated cryptographic modules.

```
Encryption option  | FIPS 140-2 | FIPS 140-3 | Performance
-------------------|------------|------------|------------
WireGuard          | ✗          | ✗          | Excellent (kernel, ChaCha20)
Calico IPsec       | ✓          | ✓          | Good (higher CPU than WireGuard)
mTLS (service mesh)| ✓ (TLS 1.2+)| ✓         | Medium (sidecar overhead)
```

---

## 2. The Three Encryption Layers

In a Kubernetes cluster running Calico in native (unencapsulated) BGP mode, pod-to-pod packets cross the physical wire as plaintext IP packets. Any compromised node or intermediate switch can read the traffic. Three distinct layers can address this:

### Layer 3: Calico Native WireGuard

The simplest path for non-FIPS clusters. Calico's Felix agent handles key exchange and tunnel management automatically.

```bash
# Enable WireGuard on all nodes (one command)
kubectl patch felixconfiguration default \
  --type='merge' \
  -p '{"spec":{"wireguardEnabled":true}}'
```

**How it works:**
```
Pod A (Node 1) ──► Felix ──► WireGuard kernel interface ──► encrypted UDP ──► Node 2 ──► Pod B
                             (ChaCha20-Poly1305 encryption)
```

**Trade-off:** WireGuard adds its own encapsulation header. You lose the zero-overhead benefit of native routing, but maintain L3 routing semantics (no VXLAN, no BGP changes needed).

**Requirements:** Linux kernel 5.6+ (WireGuard is upstream since 5.6; backported to 5.4 in some distros).

---

### Layer 3: Calico Native IPsec (FIPS-compliant path)

For environments requiring FIPS 140-2 or FIPS 140-3 compliance, Calico supports IPsec (Internet Protocol Security) via StrongSwan, using the host kernel's FIPS-validated crypto stack.

```yaml
# Calico Felix configuration for IPsec
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  ipsecMode: "ESP"
  ipsecIKEAlgorithm: "aes256gcm16-prfsha384-ecp384"
  ipsecESPAlgorithm: "aes256gcm16"
```

**How it works:**
```
Pod A (Node 1) ──► Felix ──► IPsec SA (Security Association) ──► AES-GCM encrypted ──► Node 2 ──► Pod B
                             StrongSwan key exchange via IKEv2
                             (uses host kernel FIPS crypto module)
```

**Trade-offs:**
- Higher CPU utilization than WireGuard (AES-GCM is slower than ChaCha20 without AES-NI hardware; modern x86 CPUs have AES-NI so the gap narrows)
- Operational overhead: SA (Security Association) lifecycle management, re-keying intervals
- Required for any FIPS-compliant deployment

---

### Layer 7: mTLS via Service Mesh

Instead of encrypting at the network layer, encrypt at the application layer using mutual TLS (mTLS). A service mesh (Istio, Linkerd, Cilium's sidecar-free mesh) injects proxies that encrypt all inter-service communication.

```
Pod A ──► Envoy proxy (mTLS client) ──► encrypted TLS 1.3 ──► Envoy proxy (mTLS server) ──► Pod B
          Certificate from SPIFFE/SPIRE                        Verifies workload identity
```

**Critical limitation:** mTLS only encrypts application-to-application traffic. Infrastructure traffic (kubelet metrics, kube-apiserver heartbeats, etcd replication) remains plaintext unless combined with a L3 encryption layer.

**PCI-DSS auditor preference:** mTLS provides cryptographic workload identity, which makes it easier to prove to a QSA (Qualified Security Assessor) that a compromised node cannot spoof a payment microservice. Best practice for PCI is to layer IPsec (seal the network) + mTLS (prove workload identity).

---

### Encryption Matrix

| Strategy | Encryption Layer | FIPS Compatible | CPU Overhead | Scope |
|---|---|---|---|---|
| Calico + WireGuard | L3 (Network) | ✗ | Low | All pod-to-pod traffic |
| Calico + IPsec | L3 (Network) | ✓ | Medium | All pod-to-pod traffic |
| Service Mesh mTLS | L7 (Application) | ✓ (TLS 1.2/1.3) | Medium–High | App-to-app only |
| IPsec + mTLS | L3 + L7 | ✓ | High | Full network seal + identity |

---

## 3. PCI-DSS 4.0 Requirements Mapped to Kubernetes

PCI-DSS (Payment Card Industry Data Security Standard) 4.0 governs any system that stores, processes, or transmits CHD (Cardholder Data). If your Kubernetes cluster handles payment data, the entire cluster falls into PCI scope unless workloads are isolated and documented.

Calico is the most direct tool for satisfying network-layer PCI requirements. Here's how the relevant requirements map:

### Requirement 1: Network Security Controls (Firewalling)

**Mandate:** Restrict inbound and outbound traffic to only what is necessary; block everything else.

**The problem with default Kubernetes:** By default, all pods in a cluster can reach all other pods. This flat network model fails PCI Requirement 1 immediately.

**Implementation:**

First, apply a global default-deny policy:
```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default-deny-all
spec:
  selector: all()
  types:
  - Ingress
  - Egress
  ingress: []  # No rules = deny all ingress
  egress: []   # No rules = deny all egress
```

Then explicitly allow only required paths. Example: allow frontend to reach backend on port 8443:
```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: payments
spec:
  selector: app == 'backend'
  ingress:
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'frontend'
    destination:
      ports: [8443]
```

**Why Calico is well-suited:** Calico's `GlobalNetworkPolicy` applies across namespaces, making it possible to enforce a consistent default-deny posture across the entire CDE (Cardholder Data Environment) without relying on per-namespace policies that can be forgotten.

---

### Requirement 4: Encrypting Data in Transit

**Mandate:** Protect cardholder data with strong cryptography during transmission. PCI 4.0 specifically scrutinizes shared cloud backplanes and bare-metal networks — not just public-facing TLS.

**Implementation for full-cluster sealing:**

```
Layer 1 (network):  Calico IPsec (AES-GCM, FIPS-validated)
                    → seals all node-to-node traffic regardless of app behavior

Layer 2 (app):      mTLS via Istio or Linkerd (TLS 1.2/1.3, FIPS ciphers)
                    → provides cryptographic workload identity
                    → preferred by QSAs for proving CHD containers can't be spoofed
```

For Ingress (external traffic entering the cluster):
```yaml
# Example: enforce TLS 1.2+ and FIPS cipher suite on Istio Ingress Gateway
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: payments-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - hosts: ["payments.example.com"]
    port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      minProtocolVersion: TLSV1_2
      cipherSuites:
      - ECDHE-RSA-AES256-GCM-SHA384
      - ECDHE-RSA-AES128-GCM-SHA256
```

---

### Requirement 10: Audit Logging and Continuous Monitoring

**Mandate:** Track and monitor all access to network resources. PCI-DSS 4.0 explicitly requires automated, real-time log review — manual inspection of static logs is no longer sufficient.

**The problem with default Kubernetes network logs:** Standard pod logs and kube-apiserver audit logs do not capture pod-to-pod network flows. A PCI auditor will ask for evidence that denied connection attempts to payment pods are being detected and alerted on in real time.

**Implementation:**

Configure Calico to emit policy action logs:
```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  flowLogsEnabled: true
  flowLogsFlushInterval: 15s
  denyActionOverride: "Log"  # Log all denied connections
```

For Calico Enterprise/Cloud, flow logs can be streamed directly to a SIEM (Security Information and Event Management) platform. For open-source Calico, export Felix logs via a log shipper (Fluentbit, Vector) to your SIEM:
```yaml
# DaemonSet snippet: ship Felix logs to SIEM
env:
- name: FLUENT_ELASTICSEARCH_HOST
  value: "siem.internal"
- name: LOG_LEVEL
  value: "info"
volumeMounts:
- name: calico-logs
  mountPath: /var/log/calico
```

---

## 4. k3s on Ubuntu 24.04: FIPS + PCI Specifics

k3s is a popular lightweight Kubernetes distribution that ships with Flannel as the default CNI. Running it in a FIPS + PCI context requires several deliberate overrides.

### Step 1: Enable Ubuntu FIPS Mode

Ubuntu 24.04 uses FIPS 140-3 (not 140-2 — see section 1). Canonical provides validated cryptographic packages via Ubuntu Pro:

```bash
sudo pro attach <YOUR_TOKEN>
sudo pro enable fips-updates
sudo reboot

# Verify FIPS is active at the kernel level
cat /proc/sys/crypto/fips_enabled   # Must return: 1
```

### Step 2: Use k3s-fips Binaries

The standard k3s binaries are compiled against the standard Go cryptographic library, which is not FIPS-validated. SUSE provides dedicated `k3s-fips` binaries compiled against BoringCrypto, a NIST-validated module:

```bash
# Install k3s-fips instead of standard k3s
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--fips" sh -
# Or download the k3s-fips binary directly from GitHub releases
```

> Any control plane component that handles CHD or cluster secrets (etcd, kube-apiserver) must invoke the FIPS binaries — standard k3s binaries will invalidate your PCI scope at audit.

### Step 3: Disable Flannel, Install Calico

k3s ships with Flannel enabled by default. Flannel has no NetworkPolicy support and no FIPS-compatible encryption. Disable it at node initialization:

```bash
# On first k3s server node
k3s server \
  --flannel-backend=none \
  --disable-network-policy \
  --cluster-cidr=10.244.0.0/16
```

Then install Calico using FIPS-compliant container images:
```bash
# Calico FIPS images are tagged with -fips suffix
kubectl apply -f https://docs.projectcalico.org/manifests/calico-fips.yaml
```

Enable Calico FIPS mode (this disables WireGuard, enables IPsec with FIPS crypto):
```bash
kubectl patch installation default \
  --type='merge' \
  -p '{"spec":{"fipsMode":"Enabled"}}'
```

### Step 4: PCI-DSS k3s-Specific Concerns

**Audit log persistence:** k3s defaults to SQLite for cluster state on single-node clusters. SQLite is a local, mutable file — a high-risk finding in a PCI audit. For multi-node HA clusters:

```bash
# Use external PostgreSQL or etcd for HA + audit durability
k3s server \
  --datastore-endpoint="postgres://user:pass@db.internal:5432/k3s"
```

Ship kube-apiserver audit logs and Calico flow logs off-node immediately:
```yaml
# k3s kube-apiserver audit policy (at /etc/rancher/k3s/audit-policy.yaml)
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: RequestResponse
  resources:
  - group: ""
    resources: ["pods", "secrets", "configmaps"]
- level: Metadata
  omitStages: ["RequestReceived"]
```

```bash
# Enable audit logging in k3s
k3s server \
  --kube-apiserver-arg="audit-log-path=/var/log/k3s-audit.log" \
  --kube-apiserver-arg="audit-policy-file=/etc/rancher/k3s/audit-policy.yaml" \
  --kube-apiserver-arg="audit-log-maxage=30"
```

---

## 5. Recommended Architecture for PCI + FIPS

For a cluster that must satisfy a QSA on PCI-DSS 4.0 while meeting FIPS 140-3:

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer                  Component              Standard           │
├─────────────────────────────────────────────────────────────────┤
│ Host OS               Ubuntu 24.04 Pro        FIPS 140-3        │
│                       (FIPS updates enabled)                    │
├─────────────────────────────────────────────────────────────────┤
│ Kubernetes             k3s-fips binaries       BoringCrypto      │
│ distribution           (BoringCrypto Go)       (NIST-validated) │
├─────────────────────────────────────────────────────────────────┤
│ CNI                   Calico FIPS images       FIPS 140-3        │
│                       (fipsMode: Enabled)                       │
├─────────────────────────────────────────────────────────────────┤
│ L3 encryption         Calico IPsec            FIPS 140-3 AES-GCM│
│                       (WireGuard disabled)                      │
├─────────────────────────────────────────────────────────────────┤
│ L7 encryption         Istio/Linkerd mTLS      TLS 1.2/1.3       │
│                       (FIPS cipher suites)    FIPS-approved     │
├─────────────────────────────────────────────────────────────────┤
│ Network policy        Calico GlobalNetworkPolicy  PCI Req 1     │
│                       Default-deny CDE                          │
├─────────────────────────────────────────────────────────────────┤
│ Audit & monitoring    Calico flow logs + k3s audit → SIEM       │
│                                                   PCI Req 10    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference

| PCI-DSS 4.0 Requirement | Kubernetes Control | Tool |
|---|---|---|
| Req 1: Network firewalling | GlobalNetworkPolicy default-deny | Calico |
| Req 4: Encrypt CHD in transit | IPsec (L3) + mTLS (L7) | Calico + Istio/Linkerd |
| Req 7: Restrict access | RBAC + NetworkPolicy | Kubernetes native + Calico |
| Req 10: Audit logging | Flow logs + API audit logs → SIEM | Calico + kube-apiserver |

| Compliance requirement | Use | Avoid |
|---|---|---|
| FIPS 140-2/3 network encryption | Calico IPsec | WireGuard |
| FIPS 140-3 on Ubuntu 24.04 | Ubuntu Pro + fips-updates | Standard kernel crypto |
| k3s FIPS compliance | k3s-fips binaries | Standard k3s install |
| PCI audit trail | External SIEM, off-node logs | Local SQLite logs |

---

## What You've Learned

✅ FIPS 140-2 is being sunset in 2026; Ubuntu 24.04 targets FIPS 140-3  
✅ WireGuard is not FIPS-validated — Calico disables it in FIPS mode in favor of IPsec  
✅ PCI-DSS 4.0 Requirements 1, 4, and 10 map directly to Calico + mTLS controls  
✅ k3s requires explicit opt-in for FIPS (k3s-fips binaries, Flannel replacement, FIPS images)  
✅ Layering IPsec (seal the wire) + mTLS (prove identity) satisfies both FIPS and PCI auditors  

---

## Next Steps

**Continue learning:**
→ [Pod Security Standards](03_pod_security.md) — RBAC and workload isolation  
→ [Runtime Security](02_runtime_security.md) — seccomp, AppArmor, and syscall filtering  
→ [CNI Selection Guide](../04_networking/06_cni_selection_guide.md) — choosing the right CNI for your constraints

**External references:**
- [Calico FIPS mode documentation](https://docs.tigera.io/calico/latest/operations/fips)
- [Ubuntu FIPS certification](https://ubuntu.com/security/fips)
- [PCI-DSS 4.0 Quick Reference](https://www.pcisecuritystandards.org)
- [k3s FIPS compliance (SUSE)](https://www.suse.com/c/rancher_blog/when-to-use-k3s-and-rke2/)
