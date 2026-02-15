---
level: intermediate
estimated_time: 45 min
prerequisites:
  - 04_containers/01_fundamentals/01_cgroups_namespaces.md
  - 04_containers/02_runtimes/01_runtime_landscape.md
next_recommended:
  - 04_containers/03_orchestration/02_pods_workloads.md
tags: [kubernetes, orchestration, architecture, control-plane, etcd]
---

# Kubernetes Architecture

## Learning Objectives

After reading this document, you will understand:
- The control plane components and their responsibilities
- How etcd provides distributed consistency
- The node (worker) components and their roles
- The declarative model and reconciliation loops
- How all components interact to run containers
- Why Kubernetes is designed as it is

## Prerequisites

Before reading this, you should understand:
- Container fundamentals (cgroups, namespaces)
- The OCI runtime landscape and CRI
- Basic distributed systems concepts

---

## 1. The Orchestration Problem

### What Containers Don't Solve

Containers solve **single-host isolation**, but datacenter applications need:

```
Single Host (Docker)          Multi-Host (Kubernetes)
─────────────────────        ─────────────────────────
✓ Process isolation          ✓ Cluster scheduling
✓ Resource limits            ✓ Service discovery
✓ Filesystem layering        ✓ Load balancing
✗ High availability          ✓ Rolling updates
✗ Auto-scaling               ✓ Auto-scaling
✗ Multi-host networking      ✓ Cluster networking
✗ Service routing            ✓ DNS & ingress
```

**The orchestration problem**: How do you run 1,000 containers across 100 nodes, ensuring they're healthy, networked, and automatically rescheduled when nodes fail?

### Why Not Just Shell Scripts?

Consider the complexity:
1. **Placement**: Which node has capacity for this container?
2. **Networking**: How do containers on different nodes communicate?
3. **Storage**: How does storage follow containers across nodes?
4. **Health**: How do you detect and restart failed containers?
5. **Updates**: How do you update 100 containers without downtime?
6. **Scaling**: How do you add/remove replicas based on load?

**Kubernetes answer**: Declarative desired state with automatic reconciliation.

---

## 2. Kubernetes Architecture Overview

### High-Level View

```
┌─────────────────────────────────────────────────────────┐
│                    Control Plane                         │
│  ┌──────────┐  ┌──────┐  ┌───────────┐  ┌────────────┐ │
│  │ API      │  │ etcd │  │ Scheduler │  │ Controller │ │
│  │ Server   │  │      │  │           │  │ Manager    │ │
│  └──────────┘  └──────┘  └───────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────┘
                          ↓ ↑
          ┌───────────────────────────────────┐
          │         Cluster Network           │
          └───────────────────────────────────┘
                          ↓ ↑
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Worker Node   │   │   Worker Node   │   │   Worker Node   │
│  ┌───────────┐  │   │  ┌───────────┐  │   │  ┌───────────┐  │
│  │  kubelet  │  │   │  │  kubelet  │  │   │  │  kubelet  │  │
│  ├───────────┤  │   │  ├───────────┤  │   │  ├───────────┤  │
│  │ kube-proxy│  │   │  │ kube-proxy│  │   │  │ kube-proxy│  │
│  ├───────────┤  │   │  ├───────────┤  │   │  ├───────────┤  │
│  │Container  │  │   │  │Container  │  │   │  │Container  │  │
│  │Runtime    │  │   │  │Runtime    │  │   │  │Runtime    │  │
│  └───────────┘  │   │  └───────────┘  │   │  └───────────┘  │
│     Pods...     │   │     Pods...     │   │     Pods...     │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

### Key Design Principles

1. **Declarative, not imperative**: You declare "I want 3 replicas", not "start container A, then B, then C"
2. **Eventual consistency**: Controllers continuously work toward desired state
3. **Self-healing**: Crashed containers are automatically restarted
4. **API-driven**: Everything goes through the API server (no back channels)
5. **Modular**: Each component has a single responsibility

---

## 3. Control Plane Components

The control plane makes global decisions about the cluster (scheduling, detecting failures, etc.).

### 3.1 API Server (kube-apiserver)

**Role**: The front door to Kubernetes. ALL interactions go through it.

```
kubectl → API Server → etcd
kubelet → API Server → etcd
Controller → API Server → etcd
```

**Responsibilities**:
1. **Authentication & authorization**: Is this user/component allowed?
2. **Admission control**: Should this request be modified or rejected?
3. **Validation**: Is this a valid Kubernetes object?
4. **etcd interface**: The ONLY component that talks to etcd
5. **Watch mechanism**: Clients can watch for object changes

**Why it's central**:
- Single source of truth for cluster state
- Enforces security policies before persisting anything
- Provides consistent API versioning (v1, v1beta1, etc.)

**Example interaction** (creating a deployment):
```
1. kubectl apply -f deployment.yaml
2. API Server authenticates request
3. API Server validates YAML structure
4. Admission controllers may modify (add default values, inject sidecars)
5. API Server writes to etcd
6. API Server returns success to kubectl
7. Controller Manager watches API, sees new Deployment
8. Deployment controller creates ReplicaSet
9. ReplicaSet controller creates Pods
10. Scheduler watches API, sees unscheduled Pods
11. Scheduler assigns Pods to nodes
12. kubelet watches API, sees new Pods for its node
13. kubelet tells container runtime to start containers
```

### 3.2 etcd

**Role**: Distributed key-value store holding all cluster state.

**What it stores**:
- Pods, Services, ConfigMaps, Secrets
- Node registrations
- Cluster configuration
- Essentially: everything you see with `kubectl get`

**Why etcd specifically**:
1. **Consistency**: Uses Raft consensus algorithm
2. **Reliability**: Survives minority node failures (quorum-based)
3. **Watch API**: Clients can subscribe to key changes
4. **Performance**: Handles thousands of writes/sec

**Raft quorum requirements**:
```
Cluster Size    Quorum    Tolerated Failures
────────────────────────────────────────────
1 node          1         0  (don't use in prod!)
3 nodes         2         1  (minimum for HA)
5 nodes         3         2  (recommended for prod)
7 nodes         4         3  (large clusters)
```

**Critical**: If etcd goes down, the cluster can't change state (existing pods keep running, but no new scheduling/updates).

### 3.3 Scheduler (kube-scheduler)

**Role**: Decides which node runs each pod.

**Scheduling process**:
1. **Filtering**: Which nodes CAN run this pod?
   - Does the node have enough CPU/memory?
   - Does it match the pod's node selector?
   - Does it have the required labels?
   - Are there taints the pod doesn't tolerate?

2. **Scoring**: Of the viable nodes, which is BEST?
   - Spread pods across nodes for HA
   - Balance resource utilization
   - Prefer nodes with fewer pods
   - Consider pod affinity/anti-affinity

3. **Binding**: Write the node assignment to the API server

**Example scoring**:
```
Pod requests: 500m CPU, 1Gi memory

Node A: 2 CPU available, 4Gi memory available → Score: 80
Node B: 500m CPU available, 1Gi memory available → Score: 50 (tight fit)
Node C: 8 CPU available, 16Gi memory available → Score: 95 (best fit)

Scheduler chooses Node C (highest score)
```

**What the scheduler DOESN'T do**:
- Start containers (that's kubelet's job)
- Monitor pod health (that's controller's job)
- Create networking (that's CNI's job)

It ONLY decides placement.

### 3.4 Controller Manager (kube-controller-manager)

**Role**: Runs multiple controllers that reconcile desired vs actual state.

**Key controllers**:

1. **Node Controller**:
   - Monitors node health
   - Marks nodes as NotReady if they stop heartbeating
   - Evicts pods from unhealthy nodes

2. **Replication Controller** (actually ReplicaSet controller):
   - Ensures desired number of pod replicas are running
   - If pod dies, creates a replacement
   - If too many pods, deletes extras

3. **Endpoints Controller**:
   - Populates Endpoints objects (which pods back which services)
   - Updates endpoints when pods come/go

4. **Service Account & Token Controllers**:
   - Create default service accounts for namespaces
   - Generate API access tokens

**The reconciliation loop pattern**:
```go
for {
    desired := getDesiredState()  // Read from API server
    actual := getActualState()    // Read from API server

    if desired != actual {
        takeAction()  // Create/delete/update via API server
    }

    sleep(reconciliationPeriod)
}
```

**Example**: ReplicaSet controller ensuring 3 replicas:
```
Desired: 3 replicas
Actual: 2 replicas running

Action: Create 1 new pod
Write pod spec to API server
Scheduler assigns it to a node
kubelet starts the container
```

### 3.5 Cloud Controller Manager (Optional)

**Role**: Integrates with cloud provider APIs (AWS, GCP, Azure).

**Responsibilities**:
- Node lifecycle: Register cloud instances as Kubernetes nodes
- Load balancers: Create cloud LBs for LoadBalancer services
- Routes: Configure cloud network routes for pod networking
- Storage: Provision cloud volumes (EBS, GCE PD, etc.)

**Why it's separate**: Allows cloud-specific code to live outside core Kubernetes.

---

## 4. Worker Node Components

Worker nodes run the actual application containers.

### 4.1 kubelet

**Role**: The "node agent" that runs on every worker node.

**Responsibilities**:
1. **Pod lifecycle**: Start/stop containers based on API server state
2. **Health checking**: Run liveness/readiness probes
3. **Resource reporting**: Report node capacity to API server
4. **Volume management**: Mount/unmount volumes for pods
5. **Container runtime interface**: Talk to containerd/CRI-O via CRI

**How it works**:
```
1. Watch API server for pods assigned to this node
2. For each new pod:
   a. Pull container images
   b. Create pod network namespace
   c. Call CNI to set up networking
   d. Mount volumes
   e. Tell container runtime to start containers
3. Continuously monitor container health
4. Report pod status back to API server
```

**Critical**: kubelet is the bridge between Kubernetes abstractions (pods) and container reality (namespaces, cgroups, runc).

**Connection to earlier concepts**:
Recall from `04_containers/01_fundamentals/01_cgroups_namespaces.md`:
- kubelet uses namespaces to isolate pod containers
- kubelet configures cgroups for resource limits
- kubelet is what actually calls `runc create` (via containerd)

### 4.2 kube-proxy

**Role**: Implements Kubernetes Service networking.

**What Services need**:
```
Service "frontend" → 10.96.0.10:80
Backend pods:
  - 10.244.1.5:8080 (node1)
  - 10.244.2.8:8080 (node2)
  - 10.244.3.2:8080 (node3)

Problem: How do packets to 10.96.0.10:80 reach the backend pods?
```

**kube-proxy solutions** (modes):

1. **iptables mode** (most common):
   - Creates iptables rules for each service
   - DNAT rewrites destination IP to a random backend pod
   - Example rules:
     ```
     -A KUBE-SERVICES -d 10.96.0.10/32 -p tcp --dport 80 -j KUBE-SVC-FRONTEND
     -A KUBE-SVC-FRONTEND -m statistic --mode random --probability 0.33 -j KUBE-SEP-POD1
     -A KUBE-SVC-FRONTEND -m statistic --mode random --probability 0.50 -j KUBE-SEP-POD2
     -A KUBE-SVC-FRONTEND -j KUBE-SEP-POD3
     -A KUBE-SEP-POD1 -j DNAT --to-destination 10.244.1.5:8080
     ```

2. **IPVS mode** (better performance for >1000 services):
   - Uses Linux IPVS for load balancing
   - Lower latency, higher throughput
   - Better load balancing algorithms (least-conn, locality, etc.)

3. **userspace mode** (legacy, slow):
   - kube-proxy itself proxies connections
   - Not used in modern clusters

**What kube-proxy DOESN'T do**:
- Route traffic between nodes (that's CNI's job)
- Implement network policies (that's CNI's job)
- Provide external load balancing (that's ingress/cloud LB)

### 4.3 Container Runtime

**Role**: Actually run the containers (as discussed in the runtimes section).

**Interface**: Kubernetes uses CRI (Container Runtime Interface) to talk to:
- containerd (most common)
- CRI-O (Red Hat/OpenShift)
- Docker (deprecated in K8s 1.24+, use containerd directly)

**Recall from `02_runtimes/01_runtime_landscape.md`**:
```
kubelet → [CRI] → containerd → [OCI] → runc → Linux namespaces/cgroups
```

---

## 5. Networking Components (CNI Plugins)

Kubernetes networking requires a **Container Network Interface (CNI)** plugin.

**CNI responsibilities**:
1. Assign IP addresses to pods
2. Enable pod-to-pod communication across nodes
3. (Optionally) Implement NetworkPolicies

**Common CNI plugins**:
- **Calico**: Popular, supports network policies, uses BGP
- **Flannel**: Simple, overlay-based (VXLAN)
- **Cilium**: eBPF-based, high performance (see `02_specialized/03_advanced_networking/03_ovs_cilium_geneve_explained.md`)
- **Weave**: Easy to set up, encrypted overlay option

**Why CNI is separate**: Networking is complex and environment-specific (on-prem vs cloud, overlay vs BGP, etc.).

---

## 6. The Declarative Model

### Desired State vs Actual State

**Traditional imperative approach**:
```bash
ssh node1 "docker run nginx"
ssh node2 "docker run nginx"
ssh node3 "docker run nginx"
# What if node2 dies? You need to manually ssh node4 and restart
```

**Kubernetes declarative approach**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 3  # ← Desired state
  template:
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
```

**Kubernetes reconciliation**:
```
You: "I want 3 nginx pods"
K8s: "I see only 2 running. Creating 1 more."
K8s: "I see 4 running. Deleting 1."
K8s: "I see all 3 healthy. No action needed."
```

### The Watch Mechanism

Controllers don't poll; they **watch** the API server for changes.

```
Controller → API Server: "Tell me when Deployments change"
API Server: [opens long-lived HTTP connection]

[User creates Deployment]
API Server → Controller: "New Deployment object: {...}"
Controller: [reconciles state]

[User deletes Deployment]
API Server → Controller: "Deployment deleted"
Controller: [deletes associated ReplicaSets and Pods]
```

**Advantages**:
- Near-instant reaction to changes (no polling delay)
- Scales to thousands of objects (no repeated API queries)
- API server can notify multiple watchers simultaneously

---

## 7. Example: Complete Flow for `kubectl apply`

Let's trace creating a deployment through the entire system:

```
1. User runs: kubectl apply -f deployment.yaml

2. kubectl:
   - Parses YAML
   - Sends POST to API server: /apis/apps/v1/deployments

3. API Server:
   - Authenticates request (is this user valid?)
   - Authorizes request (can this user create deployments?)
   - Validates YAML (is this a valid Deployment?)
   - Runs admission controllers (webhooks may modify/reject)
   - Writes Deployment object to etcd
   - Returns success to kubectl

4. Deployment Controller (watching Deployments):
   - Sees new Deployment via watch stream
   - Reads spec.replicas: 3
   - Creates a ReplicaSet with 3 replicas
   - Writes ReplicaSet to API server

5. ReplicaSet Controller (watching ReplicaSets):
   - Sees new ReplicaSet
   - Reads spec.replicas: 3
   - Creates 3 Pod objects (unscheduled)
   - Writes Pods to API server

6. Scheduler (watching unscheduled Pods):
   - Sees 3 new Pods with spec.nodeName: ""
   - Filters viable nodes (enough resources, etc.)
   - Scores nodes (best fit)
   - Assigns each Pod to a node
   - Writes nodeName to each Pod's spec

7. kubelet on node1 (watching Pods for node1):
   - Sees new Pod assigned to node1
   - Pulls container images
   - Calls CNI to set up pod networking
   - Calls container runtime (containerd) to start containers
   - Reports pod status (Running) to API server

8. kubelet on node2 and node3:
   - [Same process for their assigned pods]

9. Endpoints Controller (watching Pods and Services):
   - If there's a Service selecting these pods
   - Updates Endpoints object with pod IPs

10. kube-proxy on all nodes (watching Services and Endpoints):
    - Sees updated Endpoints
    - Updates iptables rules to route service traffic to pod IPs
```

**Total time**: Usually 1-3 seconds from `kubectl apply` to containers running.

---

## 8. High Availability and Failure Modes

### Control Plane HA

**Critical components to replicate**:
- **etcd**: Must be odd-numbered (3, 5, 7) for quorum
- **API server**: Can run many instances (stateless, load-balanced)
- **Scheduler**: Multiple can run, but only one is active (leader election)
- **Controller Manager**: Multiple can run, but only one is active (leader election)

**Typical HA setup**:
```
Load Balancer (HAProxy/cloud LB)
        ↓
┌───────────────┬───────────────┬───────────────┐
│ Control Plane 1 │ Control Plane 2 │ Control Plane 3 │
│  - API Server   │  - API Server   │  - API Server   │
│  - etcd         │  - etcd         │  - etcd         │
│  - Scheduler (L)│  - Scheduler    │  - Scheduler    │
│  - Controller(L)│  - Controller   │  - Controller   │
└───────────────┴───────────────┴───────────────┘
         (L) = Leader-elected (only one active)
```

### Worker Node Failures

**What happens when a node dies**:

```
Time  Event
────────────────────────────────────────────────────────
T+0s  Node stops sending heartbeats to API server
T+40s Node marked NotReady (default node-monitor-grace-period)
T+5m  Pods evicted from node (default pod-eviction-timeout)
T+5m  ReplicaSet controller sees fewer pods than desired
T+5m  ReplicaSet creates replacement pods
T+5m  Scheduler assigns new pods to healthy nodes
T+5m  kubelets start new pods
```

**Grace periods prevent thrashing**:
- Don't immediately kill pods for brief network hiccups
- But 5 minutes means 5 minutes of downtime for stateless apps

**Solutions**:
- **PodDisruptionBudgets**: Ensure minimum replicas during maintenance
- **Pod anti-affinity**: Spread replicas across nodes
- **Readiness probes**: Don't route traffic to pods that aren't ready

---

## 9. Comparison to Other Orchestrators

### Kubernetes vs Docker Swarm

| Feature              | Kubernetes          | Docker Swarm        |
|----------------------|---------------------|---------------------|
| Complexity           | High                | Low                 |
| Ecosystem            | Huge                | Small               |
| Auto-scaling         | Built-in (HPA, VPA) | Manual              |
| Storage              | Flexible (CSI)      | Basic volumes       |
| Networking           | Pluggable (CNI)     | Overlay only        |
| Multi-cloud          | Excellent           | Limited             |
| Learning curve       | Steep               | Gentle              |

**When to use Swarm**: Small teams, simple apps, already using Docker.
**When to use Kubernetes**: Everything else (it won).

### Kubernetes vs Nomad (HashiCorp)

| Feature              | Kubernetes          | Nomad               |
|----------------------|---------------------|---------------------|
| Workloads            | Containers (mainly) | Containers, VMs, binaries |
| Complexity           | High                | Medium              |
| Ecosystem            | Huge                | Small               |
| Multi-region         | Requires federation | Native              |
| Resource model       | Pods                | Tasks in groups     |

**When to use Nomad**: Multi-region, mixed workloads, simpler operations.

---

## 10. Why Kubernetes Won

Despite its complexity, Kubernetes became the standard because:

1. **Cloud-native**: Born from Google's Borg/Omega experience
2. **Extensibility**: CRI, CNI, CSI allow pluggable components
3. **Ecosystem**: Helm, operators, service meshes, monitoring
4. **Declarative**: Infrastructure-as-code friendly
5. **Community**: CNCF governance, multi-vendor support
6. **Abstraction**: Works across clouds (no vendor lock-in)

**But**: Kubernetes is **not** simple. It's powerful and flexible at the cost of complexity.

---

## Quick Reference

### Control Plane Components

| Component           | Role                                  | Stateful? | HA Method         |
|---------------------|---------------------------------------|-----------|-------------------|
| API Server          | Front door, REST API, auth            | No        | Load balanced     |
| etcd                | Distributed state storage             | Yes       | Raft quorum (3/5) |
| Scheduler           | Pod → node placement                  | No        | Leader election   |
| Controller Manager  | Reconciliation loops                  | No        | Leader election   |
| Cloud Controller    | Cloud provider integration            | No        | Leader election   |

### Node Components

| Component           | Role                                  | Runs on          |
|---------------------|---------------------------------------|------------------|
| kubelet             | Pod lifecycle, talks to runtime       | Every node       |
| kube-proxy          | Service networking (iptables/IPVS)    | Every node       |
| Container Runtime   | Actually run containers (containerd)  | Every node       |
| CNI Plugin          | Pod networking, IP assignment         | Every node       |

### Key Concepts

- **Declarative**: Describe desired state, not steps to get there
- **Reconciliation**: Controllers continuously drive toward desired state
- **Watch API**: Efficient notification of changes (not polling)
- **CRI/CNI/CSI**: Pluggable interfaces for runtime/network/storage

### Common Commands

```bash
# View cluster components
kubectl get nodes                    # Worker nodes
kubectl get componentstatuses        # Control plane health (deprecated)
kubectl cluster-info                 # Control plane endpoints

# View component logs (if running as pods)
kubectl logs -n kube-system kube-apiserver-node1
kubectl logs -n kube-system kube-scheduler-node1
kubectl logs -n kube-system kube-controller-manager-node1

# View node component logs (systemd)
journalctl -u kubelet
journalctl -u containerd
```

---

## Summary

Kubernetes is a **declarative orchestration system** that:

1. **Separates concerns**: Control plane makes decisions, worker nodes execute
2. **Uses distributed consensus**: etcd ensures all components see consistent state
3. **Runs reconciliation loops**: Controllers continuously fix drift
4. **Abstracts infrastructure**: Same API works across clouds and on-prem
5. **Scales through modularity**: Pluggable networking, storage, runtimes

**The cost**: Kubernetes is complex, with many moving parts. But this complexity enables running planet-scale applications across heterogeneous infrastructure.

**Next**: Now that you understand the architecture, we'll explore the fundamental unit of Kubernetes: the **pod** and various workload types.

---

## Related Documents

- **Previous**: `02_runtimes/01_runtime_landscape.md` - How Kubernetes uses CRI
- **Next**: `03_orchestration/02_pods_workloads.md` - Pods, Deployments, StatefulSets
- **Related**: `01_foundations/02_datacenter_topology/01_modern_topology.md` - Physical infrastructure Kubernetes runs on
- **Deep dive**: Coming in `03_orchestration/03_services_networking.md` - How kube-proxy and CNI work together
