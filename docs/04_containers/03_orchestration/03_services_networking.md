---
level: intermediate
estimated_time: 55 min
prerequisites:
  - 04_containers/03_orchestration/01_kubernetes_architecture.md
  - 04_containers/03_orchestration/02_pods_workloads.md
  - 01_foundations/02_datacenter_topology/01_modern_topology.md
next_recommended:
  - 04_containers/03_orchestration/04_scheduling_resources.md
tags: [kubernetes, services, networking, dns, ingress, load-balancing, cni]
---

# Services and Networking

## Learning Objectives

After reading this document, you will understand:
- Why pods need Services for stable networking
- The four Service types and when to use each
- How kube-proxy implements Services (iptables/IPVS)
- DNS-based service discovery
- How Ingress provides external HTTP(S) access
- The Container Network Interface (CNI) and overlay networks
- Network policies for pod-level firewalling

## Prerequisites

Before reading this, you should understand:
- Kubernetes architecture (control plane, nodes, kube-proxy)
- Pods and how they share network namespaces
- Basic datacenter networking concepts

---

## 1. The Service Discovery Problem

### Why Not Just Use Pod IPs?

```
Problem: Pods are ephemeral

Day 1:
  frontend pod → http://10.244.1.5:8080  (backend pod)
  ✓ Works

Day 2:
  Backend pod crashes, Deployment creates new pod
  New backend pod IP: 10.244.2.9
  Frontend still trying: http://10.244.1.5:8080
  ✗ Connection refused

Solution needed: Stable endpoint that tracks pod changes
```

### What Services Provide

A **Service** is a stable network abstraction over a set of pods:

```
┌──────────────────────────────────────────────┐
│ Service: "backend"                           │
│ ClusterIP: 10.96.100.50                      │
│ Port: 80                                     │
│                                              │
│ Selector: app=backend                        │
└──────────────┬───────────────────────────────┘
               │ Routes traffic to pods matching selector
               ↓
     ┌─────────┴─────────┬──────────────┐
     ↓                   ↓              ↓
┌─────────┐         ┌─────────┐    ┌─────────┐
│ Pod     │         │ Pod     │    │ Pod     │
│ app=    │         │ app=    │    │ app=    │
│ backend │         │ backend │    │ backend │
│ 10.244  │         │ 10.244  │    │ 10.244  │
│ .1.5    │         │ .2.9    │    │ .3.7    │
└─────────┘         └─────────┘    └─────────┘
```

**Key properties**:
1. **Stable IP**: Service ClusterIP never changes
2. **DNS name**: `backend.default.svc.cluster.local`
3. **Load balancing**: Distributes across healthy pods
4. **Dynamic updates**: Automatically tracks pod changes

---

## 2. Service Types

Kubernetes has four Service types, each for different use cases.

### 2.1 ClusterIP (Default)

**Use case**: Internal communication within the cluster.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  type: ClusterIP  # ← Default, can be omitted
  selector:
    app: backend
  ports:
  - port: 80         # Service port
    targetPort: 8080 # Container port
```

**Behavior**:
```
Service gets a ClusterIP from the service CIDR (e.g., 10.96.0.0/12)
  Service IP: 10.96.100.50

Pods can access via:
  - ClusterIP: http://10.96.100.50:80
  - DNS: http://backend:80 (same namespace)
  - DNS: http://backend.default.svc.cluster.local:80 (FQDN)

Traffic flow:
  Pod A → 10.96.100.50:80
       ↓ (kube-proxy iptables/IPVS)
  Random backend pod (10.244.1.5:8080, 10.244.2.9:8080, or 10.244.3.7:8080)
```

**ClusterIP is not routable outside the cluster** (no external access).

### 2.2 NodePort

**Use case**: Expose service on a port on every node (simple external access).

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  type: NodePort
  selector:
    app: frontend
  ports:
  - port: 80         # Service port (ClusterIP)
    targetPort: 8080 # Container port
    nodePort: 30080  # Port on every node (30000-32767)
```

**Behavior**:
```
Service gets:
  - ClusterIP: 10.96.100.51
  - NodePort: 30080 (on ALL nodes)

External client can access via ANY node:
  http://node1-ip:30080
  http://node2-ip:30080
  http://node3-ip:30080

Even if no pods run on node3, traffic to node3:30080 still works
  (forwarded to a node with backend pods)
```

**How it works**:
```
External client → node3:30080
   ↓ (iptables DNAT)
Service ClusterIP: 10.96.100.51:80
   ↓ (iptables DNAT again)
Random backend pod: 10.244.1.5:8080
```

**Limitations**:
- Only one service per port (limited to 30000-32767 range)
- Requires firewall rules for external access
- No built-in load balancing across nodes (client chooses node)

**When to use**: Development, on-prem clusters without load balancers, simple use cases.

### 2.3 LoadBalancer

**Use case**: Expose service via cloud provider's load balancer (production external access).

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  type: LoadBalancer
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 8080
```

**Behavior (on cloud providers)**:
```
1. Kubernetes requests a load balancer from cloud provider (AWS ELB, GCP LB, Azure LB)
2. Cloud provisions LB with public IP (e.g., 203.0.113.10)
3. LB routes to NodePorts on cluster nodes
4. NodePorts route to backend pods

External client → 203.0.113.10:80 (cloud LB)
  ↓ (LB distributes across nodes)
Node1:30080, Node2:30080, Node3:30080
  ↓ (NodePort → Service → Pods)
Backend pods
```

**Service gets**:
```
ClusterIP: 10.96.100.52
NodePort: 30080
External IP: 203.0.113.10 (from cloud LB)
```

**Limitations**:
- Requires cloud provider integration (doesn't work on bare metal without MetalLB)
- One cloud LB per service (expensive at scale)
- No HTTP routing (Layer 4 only, no path/host-based routing)

**When to use**: Simple external access on cloud, non-HTTP services (databases, etc.).

### 2.4 ExternalName

**Use case**: Create DNS alias to external service.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-db
spec:
  type: ExternalName
  externalName: db.example.com  # ← External DNS name
```

**Behavior**:
```
Pods query: external-db.default.svc.cluster.local
  ↓ (DNS CNAME record)
db.example.com
  ↓ (external DNS)
Real IP of external service
```

**No load balancing, no proxying** (just DNS).

**When to use**: Reference external services with Kubernetes DNS names (migrate from external to in-cluster without changing app config).

---

## 3. How kube-proxy Works

Recall from `03_orchestration/01_kubernetes_architecture.md`: kube-proxy runs on every node and implements Service networking.

### iptables Mode (Most Common)

**High-level**:
```
kube-proxy watches Services and Endpoints via API server
  ↓
For each Service, creates iptables rules
  ↓
Rules intercept traffic to ClusterIP and DNAT to backend pod IPs
```

**Example iptables rules** for Service `backend` (ClusterIP: 10.96.100.50, 3 backend pods):

```bash
# Intercept traffic to Service ClusterIP
-A KUBE-SERVICES -d 10.96.100.50/32 -p tcp --dport 80 -j KUBE-SVC-BACKEND

# Load balance across backends using statistic module
-A KUBE-SVC-BACKEND -m statistic --mode random --probability 0.333 -j KUBE-SEP-BACKEND1
-A KUBE-SVC-BACKEND -m statistic --mode random --probability 0.500 -j KUBE-SEP-BACKEND2
-A KUBE-SVC-BACKEND -j KUBE-SEP-BACKEND3

# DNAT to actual pod IPs
-A KUBE-SEP-BACKEND1 -p tcp -j DNAT --to-destination 10.244.1.5:8080
-A KUBE-SEP-BACKEND2 -p tcp -j DNAT --to-destination 10.244.2.9:8080
-A KUBE-SEP-BACKEND3 -p tcp -j DNAT --to-destination 10.244.3.7:8080
```

**Load balancing math**:
```
First rule: 33.3% chance → BACKEND1
Second rule (if first missed): 50% of remaining 66.7% = 33.3% → BACKEND2
Third rule (fallthrough): Remaining 33.3% → BACKEND3
```

**Session affinity (optional)**:
```yaml
spec:
  sessionAffinity: ClientIP  # Sticky sessions
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 3600  # Same client → same pod for 1 hour
```

iptables rule adds:
```bash
-A KUBE-SEP-BACKEND1 -m recent --name KUBE-SEP-BACKEND1 --set
-A KUBE-SEP-BACKEND1 -m recent --name KUBE-SEP-BACKEND1 --rcheck --seconds 3600 -j DNAT ...
```

**Limitations of iptables mode**:
- **Performance**: Linear rules (O(n) lookups for n services)
- **Large clusters**: >5000 services = >40000 iptables rules = slow
- **Load balancing**: Random only (no least-connections, etc.)

### IPVS Mode (Better for Large Clusters)

**Advantages**:
- **Performance**: Hash table lookups (O(1) for n services)
- **Load balancing algorithms**: rr (round-robin), lc (least-connection), dh (destination hash), sh (source hash)
- **Better throughput**: Kernel-level load balancing

**Enable IPVS**:
```yaml
# kube-proxy ConfigMap
kind: ConfigMap
metadata:
  name: kube-proxy-config
data:
  mode: "ipvs"
  ipvs:
    scheduler: "rr"  # Round-robin
```

**How it works**:
```
kube-proxy creates IPVS virtual servers for each Service ClusterIP
  ↓
Kernel IPVS distributes to real servers (backend pods)
  ↓
Much faster than iptables for large clusters
```

**View IPVS rules**:
```bash
$ ipvsadm -Ln
IP Virtual Server version 1.2.1 (size=4096)
Prot LocalAddress:Port Scheduler Flags
  -> RemoteAddress:Port           Forward Weight
TCP  10.96.100.50:80 rr
  -> 10.244.1.5:8080              Masq    1
  -> 10.244.2.9:8080              Masq    1
  -> 10.244.3.7:8080              Masq    1
```

**When to use IPVS**: Large clusters (>1000 services), need advanced load balancing.

---

## 4. DNS (Domain Name System) and Service Discovery

Kubernetes runs a DNS (Domain Name System) server (CoreDNS) in the cluster.

### DNS Records

**For Services**:
```
Service: backend (namespace: default)
  A record: backend.default.svc.cluster.local → 10.96.100.50
  Short names work within same namespace:
    backend → 10.96.100.50
    backend.default → 10.96.100.50
```

**For Pods** (optional, usually disabled):
```
Pod: 10.244.1.5 (namespace: default)
  A record: 10-244-1-5.default.pod.cluster.local → 10.244.1.5
```

**For StatefulSets**:
```
StatefulSet: mysql (namespace: default, service: mysql)
  mysql-0.mysql.default.svc.cluster.local → 10.244.1.5
  mysql-1.mysql.default.svc.cluster.local → 10.244.2.9
  mysql-2.mysql.default.svc.cluster.local → 10.244.3.7

  Also: mysql.default.svc.cluster.local → (all pod IPs, round-robin)
```

### How Pod DNS Works

**Pod DNS config** (injected by kubelet):
```bash
$ cat /etc/resolv.conf  # Inside a pod
nameserver 10.96.0.10     # ← CoreDNS ClusterIP
search default.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

**Resolution process**:
```
App queries: backend
  ↓
ndots:5 → Try as FQDN candidates first:
  1. backend.default.svc.cluster.local → ✓ Matches! Return 10.96.100.50
  (No need to try backend.svc.cluster.local, etc.)

App queries: google.com
  ↓
ndots:5 → Try FQDN candidates:
  1. google.com.default.svc.cluster.local → ✗
  2. google.com.svc.cluster.local → ✗
  3. google.com.cluster.local → ✗
  4. google.com (as-is) → ✓ External DNS returns IP
```

**Why ndots:5 matters**:
- Prevents external DNS queries for internal services
- But adds latency for external domains (multiple failed queries first)

**Optimization** (for external-heavy workloads):
```yaml
spec:
  dnsConfig:
    options:
    - name: ndots
      value: "1"  # Try as-is first for google.com
```

---

## 5. Ingress: HTTP(S) Routing

**Problem**: LoadBalancer Services are expensive (one cloud LB per service).

**Solution**: Ingress provides HTTP(S) routing to multiple services via a single entry point.

### Ingress Architecture

```
                 Internet
                     ↓
          ┌──────────────────┐
          │ Cloud Load       │
          │ Balancer         │
          │ (1 LB for all)   │
          └────────┬─────────┘
                   ↓
          ┌──────────────────┐
          │ Ingress          │
          │ Controller       │
          │ (nginx/traefik)  │
          └────────┬─────────┘
                   ↓
      ┌────────────┼────────────┐
      ↓            ↓            ↓
┌─────────┐  ┌─────────┐  ┌─────────┐
│ Service │  │ Service │  │ Service │
│ app1    │  │ app2    │  │ app3    │
└─────────┘  └─────────┘  └─────────┘
```

### Ingress Resource

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: main-ingress
spec:
  rules:
  - host: app1.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app1
            port:
              number: 80

  - host: app2.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: app2-api
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app2-web
            port:
              number: 80
```

**Routing logic**:
```
Request: http://app1.example.com/anything
  → Service: app1:80

Request: http://app2.example.com/api/users
  → Service: app2-api:80

Request: http://app2.example.com/home
  → Service: app2-web:80
```

### TLS/HTTPS

```yaml
spec:
  tls:
  - hosts:
    - app1.example.com
    secretName: app1-tls  # Secret contains cert + key

  rules:
  - host: app1.example.com
    ...
```

**Secret creation**:
```bash
kubectl create secret tls app1-tls \
  --cert=app1.crt \
  --key=app1.key
```

Ingress controller terminates TLS, proxies HTTP to backend services.

### Ingress Controllers

Ingress resources are useless without an **Ingress Controller** (implementation).

**Popular controllers**:
- **nginx-ingress**: Most common, battle-tested
- **Traefik**: Modern, native Kubernetes features
- **HAProxy**: High performance
- **Istio/Envoy**: Service mesh integration
- **Cloud-native**: AWS ALB Ingress, GCP Ingress

**Installation** (nginx example):
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
```

Creates:
- Deployment (nginx pods)
- Service type LoadBalancer (single cloud LB for all Ingress rules)

---

## 6. Container Networking (CNI)

Kubernetes networking requires a **CNI plugin** to:
1. Assign pod IPs
2. Enable pod-to-pod communication across nodes
3. (Optionally) enforce NetworkPolicies

### Kubernetes Networking Model

**Requirements**:
1. All pods can communicate with each other without NAT
2. All nodes can communicate with all pods without NAT
3. Pod sees its own IP as the same IP others see

**This is a flat network** (unlike Docker's bridge networks).

### How CNI Works

```
kubelet starts pod
  ↓
Calls CNI plugin: ADD operation
  ↓
CNI plugin:
  1. Creates veth pair (virtual ethernet)
  2. Attaches one end to pod network namespace
  3. Attaches other end to node network bridge/routing
  4. Assigns IP from pod CIDR
  5. Sets up routes (on-node and cross-node)
  6. Returns IP and routes to kubelet
```

**Example** (pod on node1 talking to pod on node2):

```
Pod A (10.244.1.5) on node1 → Pod B (10.244.2.9) on node2

Packet journey:
1. Pod A sends packet: src=10.244.1.5, dst=10.244.2.9
2. Leaves pod netns via veth pair
3. Node1 routing table: 10.244.2.0/24 via node2
4. Packet encapsulated (overlay) or routed (BGP) to node2
5. Node2 receives packet, decapsulates (if overlay)
6. Node2 routing table: 10.244.2.9 via local veth
7. Packet enters Pod B netns
```

### CNI Plugins Overview

**Overlay networks** (encapsulation):

1. **Flannel**: Simple, VXLAN overlay
   - Pros: Easy setup, works anywhere
   - Cons: Performance overhead (encapsulation), no NetworkPolicy

2. **Weave**: VXLAN with optional encryption
   - Pros: Easy, encrypted option
   - Cons: Performance overhead

**Routing-based** (no encapsulation):

3. **Calico**: BGP-based routing, NetworkPolicy support
   - Pros: No encap overhead, rich policies, scales well
   - Cons: Requires BGP support (some clouds don't allow it)

4. **Cilium**: eBPF-based, modern, high-performance
   - Pros: Extremely fast, L7 policies, observability
   - Cons: Requires recent kernel (4.19+)
   - See: `02_specialized/03_advanced_networking/03_ovs_cilium_geneve_explained.md`

**Cloud-native**:

5. **AWS VPC CNI**: Uses ENIs (Elastic Network Interfaces)
   - Pros: Native AWS networking, no overlay
   - Cons: AWS-only, limited IPs per node

6. **Azure CNI, GCP CNI**: Similar cloud-native approaches

**Comparison**:

| Plugin  | Type    | Encap | NetworkPolicy | Performance | Complexity |
|---------|---------|-------|---------------|-------------|------------|
| Flannel | Overlay | VXLAN | No            | Good        | Low        |
| Calico  | Routing | None  | Yes           | Excellent   | Medium     |
| Cilium  | eBPF    | None* | Yes (L7)      | Best        | High       |
| Weave   | Overlay | VXLAN | Yes           | Good        | Low        |

(*Cilium can use VXLAN if needed, but direct routing preferred)

**Connection to earlier networking concepts**:
Recall from `02_intermediate/01_advanced_networking/02_overlay_mechanics.md`:
- Flannel/Weave use VXLAN encapsulation (same as datacenter overlays)
- Adds 50-byte overhead per packet
- Calico's BGP approach is like spine-leaf BGP routing

---

## 7. Network Policies

**Problem**: By default, all pods can talk to all pods (no isolation).

**Solution**: NetworkPolicies define pod-level firewall rules.

### Default Allow All

```
Without NetworkPolicies:
  Pod A → Pod B ✓
  Pod A → Pod C ✓
  Pod B → Pod C ✓
  External → Pod A ✓ (if Service exposes it)
```

### Deny All Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: production
spec:
  podSelector: {}  # Applies to all pods in namespace
  policyTypes:
  - Ingress
  # No ingress rules → deny all
```

**Effect**:
```
Pod A → Pod B ✗ (denied)
Pod A → Pod C ✗ (denied)
```

### Allow Specific Traffic

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend  # ← Apply to backend pods
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend  # ← Allow from frontend pods
    ports:
    - protocol: TCP
      port: 8080
```

**Effect**:
```
Frontend pod → Backend pod:8080 ✓ (allowed)
Database pod → Backend pod:8080 ✗ (denied)
Frontend pod → Backend pod:5432 ✗ (denied, wrong port)
```

### Namespace Selectors

```yaml
spec:
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          team: platform  # Allow from pods in namespaces with label team=platform
```

### Egress Policies

```yaml
spec:
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432

  - to:  # Allow DNS
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
```

**Effect**: Pods can only talk to database:5432 and DNS (nothing else, not even internet).

### Important: NetworkPolicy is Additive

```
If NO NetworkPolicies select a pod → Allow all
If ANY NetworkPolicy selects a pod → Default deny, only allow what's specified

Multiple NetworkPolicies on same pod → OR'd together (union)
```

**Requires CNI support**: Calico, Cilium, Weave (Flannel doesn't support).

---

## 8. Headless Services

**Problem**: Service load balances across pods. What if you need ALL pod IPs (e.g., for clustered apps like Cassandra)?

**Solution**: Headless Service (ClusterIP: None).

```yaml
apiVersion: v1
kind: Service
metadata:
  name: cassandra
spec:
  clusterIP: None  # ← Headless
  selector:
    app: cassandra
  ports:
  - port: 9042
```

**DNS behavior**:
```
Normal Service:
  nslookup backend.default.svc.cluster.local
  → 10.96.100.50 (single ClusterIP)

Headless Service:
  nslookup cassandra.default.svc.cluster.local
  → 10.244.1.5, 10.244.2.9, 10.244.3.7 (all pod IPs)
```

**Use cases**:
- StatefulSets (stable pod DNS)
- Clustered databases (nodes need to discover each other)
- Client-side load balancing (app chooses which pod)

---

## Quick Reference

### Service Types

| Type         | ClusterIP | NodePort | External LB | Use Case                  |
|--------------|-----------|----------|-------------|---------------------------|
| ClusterIP    | ✓         | ✗        | ✗           | Internal communication    |
| NodePort     | ✓         | ✓        | ✗           | Dev, simple external      |
| LoadBalancer | ✓         | ✓        | ✓           | Production external       |
| ExternalName | ✗         | ✗        | ✗           | Alias to external service |

### Common kubectl Commands

```bash
# Services
kubectl expose deployment backend --port=80 --target-port=8080
kubectl get services
kubectl describe service backend
kubectl get endpoints backend  # See backend pod IPs

# DNS testing
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
  nslookup backend
  wget -O- http://backend:80

# Ingress
kubectl get ingress
kubectl describe ingress main-ingress

# Network Policies
kubectl get networkpolicies
kubectl describe networkpolicy deny-all
```

### DNS Names

```
Service: <service>.<namespace>.svc.cluster.local
StatefulSet pod: <pod>.<service>.<namespace>.svc.cluster.local

Same namespace shorthand: <service>
Cross namespace: <service>.<namespace>
```

### kube-proxy Modes

```bash
# Check current mode
kubectl get configmap kube-proxy -n kube-system -o yaml | grep mode

# View iptables rules
sudo iptables -t nat -L KUBE-SERVICES

# View IPVS rules
sudo ipvsadm -Ln
```

---

## Summary

**Services** provide stable networking for ephemeral pods:
- **ClusterIP**: Internal (default)
- **NodePort**: External via node ports
- **LoadBalancer**: External via cloud LB
- **ExternalName**: DNS alias

**kube-proxy** implements Services:
- **iptables mode**: Common, but slow at scale
- **IPVS mode**: Fast, scales to thousands of services

**DNS** enables service discovery:
- CoreDNS provides cluster DNS
- Services get DNS names automatically
- StatefulSets get per-pod DNS

**Ingress** provides HTTP(S) routing:
- Path/host-based routing to multiple services
- TLS termination
- Single entry point (cheaper than many LoadBalancers)

**CNI** provides pod networking:
- Assigns pod IPs
- Enables cross-node communication
- Overlay (Flannel, Weave) or routing (Calico, Cilium)

**NetworkPolicies** provide pod firewalling:
- Default: allow all
- Policies: deny by default, allow specific traffic
- Requires CNI support

**Next**: Now that pods can communicate, we'll explore how Kubernetes schedules them: **Scheduling and Resource Management**.

---

## Related Documents

- **Previous**: `03_orchestration/02_pods_workloads.md` - Pod fundamentals
- **Next**: `03_orchestration/04_scheduling_resources.md` - How pods are scheduled
- **Foundation**: `01_foundations/02_datacenter_topology/01_modern_topology.md` - Physical network context
- **Deep dive**: `02_intermediate/01_advanced_networking/02_overlay_mechanics.md` - VXLAN overlays
- **Advanced**: `02_specialized/03_advanced_networking/03_ovs_cilium_geneve_explained.md` - Modern CNI (Cilium)
