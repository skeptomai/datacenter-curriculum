---
level: intermediate
estimated_time: 45 min
prerequisites:
  - 04_containers/03_orchestration/01_kubernetes_architecture.md
  - 04_containers/03_orchestration/02_pods_workloads.md
next_recommended:
  - 04_containers/03_orchestration/05_storage_volumes.md
tags: [kubernetes, scheduling, resources, affinity, taints, tolerations, qos, limits]
---

# Scheduling and Resource Management

## Learning Objectives

After reading this document, you will understand:
- How the scheduler decides which node runs each pod
- Node selection with selectors, affinity, and anti-affinity
- Taints and tolerations for specialized nodes
- Resource requests, limits, and QoS classes
- Horizontal and Vertical Pod Autoscaling
- Cluster autoscaling and resource quotas
- Pod priority and preemption

## Prerequisites

Before reading this, you should understand:
- Kubernetes architecture (scheduler role)
- Pods and workload controllers
- Basic resource management concepts

---

## 1. The Scheduling Problem

### Why Scheduling Matters

```
Scenario: 100-node cluster, need to run a new pod

Questions:
1. Which nodes CAN run it? (feasibility)
   - Does the node have enough CPU/memory?
   - Does it have the right labels?
   - Are there any taints preventing it?

2. Which node is BEST? (optimization)
   - Spread pods across nodes for HA?
   - Pack pods tightly for resource efficiency?
   - Prefer nodes with underutilized resources?

Scheduler's job: Answer these in <100ms per pod
```

### Scheduling Workflow

```
┌─────────────────────────────────────────────┐
│ 1. Watch API: New pod needs scheduling     │
│    (pod.spec.nodeName is empty)             │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│ 2. Filtering Phase: Find viable nodes      │
│    - Check resources (CPU, memory)          │
│    - Check node selector                    │
│    - Check taints/tolerations               │
│    - Check affinity rules                   │
│    Result: Nodes that CAN run the pod       │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│ 3. Scoring Phase: Rank viable nodes        │
│    - Balance resource utilization           │
│    - Spread pods across zones               │
│    - Prefer affinity matches                │
│    Result: Scored list (0-100 per node)     │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│ 4. Binding: Assign pod to highest-scoring  │
│    Write pod.spec.nodeName to API server    │
└─────────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│ 5. kubelet on chosen node sees assignment  │
│    kubelet starts the pod                   │
└─────────────────────────────────────────────┘
```

---

## 2. Node Selection

### 2.1 Node Selector (Simple)

**Use case**: Run pods only on nodes with specific labels.

```yaml
# Label nodes first
$ kubectl label nodes node1 disktype=ssd
$ kubectl label nodes node2 disktype=ssd
$ kubectl label nodes node3 disktype=hdd

# Pod with node selector
apiVersion: v1
kind: Pod
metadata:
  name: db
spec:
  nodeSelector:
    disktype: ssd  # ← Only schedule on nodes with this label
  containers:
  - name: postgres
    image: postgres:13
```

**Filtering**:
```
Node1: disktype=ssd → ✓ Viable
Node2: disktype=ssd → ✓ Viable
Node3: disktype=hdd → ✗ Filtered out
Node4: (no label)   → ✗ Filtered out

Scheduler scores Node1 and Node2, chooses one
```

**Limitations**: All-or-nothing (can't express "prefer SSD, but HDD is okay").

### 2.2 Node Affinity (Flexible)

**Use case**: Express complex node preferences with required/preferred rules.

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:  # ← Hard requirement
        nodeSelectorTerms:
        - matchExpressions:
          - key: disktype
            operator: In
            values:
            - ssd
            - nvme

      preferredDuringSchedulingIgnoredDuringExecution:  # ← Soft preference
      - weight: 80  # Higher weight = stronger preference
        preference:
          matchExpressions:
          - key: zone
            operator: In
            values:
            - us-east-1a

      - weight: 20
        preference:
          matchExpressions:
          - key: instance-type
            operator: In
            values:
            - m5.2xlarge
```

**Meaning**:
```
MUST: disktype=ssd OR disktype=nvme
PREFER (80 points): zone=us-east-1a
PREFER (20 points): instance-type=m5.2xlarge

Scoring:
  Node1 (disktype=ssd, zone=us-east-1a, instance=m5.2xlarge) → 100 points
  Node2 (disktype=ssd, zone=us-east-1a, instance=m5.xlarge)  → 80 points
  Node3 (disktype=ssd, zone=us-east-1b, instance=m5.2xlarge) → 20 points
  Node4 (disktype=hdd, zone=us-east-1a, instance=m5.2xlarge) → Filtered (required not met)
```

**Operators**:
- `In`: Label value in specified list
- `NotIn`: Label value not in list
- `Exists`: Label key exists (any value)
- `DoesNotExist`: Label key doesn't exist
- `Gt`: Greater than (for numeric labels)
- `Lt`: Less than

**Example** (prefer nodes with less than 50% CPU allocated):
```yaml
- weight: 100
  preference:
    matchExpressions:
    - key: cpu-percent-allocated
      operator: Lt
      values:
      - "50"
```

### 2.3 Pod Affinity (Co-locate Pods)

**Use case**: Run pods on the same node (or zone) as other pods.

```yaml
# Backend pod should run near cache pod for low latency
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - cache
        topologyKey: kubernetes.io/hostname  # ← Same node
```

**Topology key** defines "nearness":
- `kubernetes.io/hostname`: Same node
- `topology.kubernetes.io/zone`: Same availability zone
- `topology.kubernetes.io/region`: Same region

**Example** (run backend in same zone as cache):
```yaml
topologyKey: topology.kubernetes.io/zone

If cache pod is on node in us-east-1a:
  → Backend must also be in us-east-1a zone
  → But can be on different node within that zone
```

### 2.4 Pod Anti-Affinity (Spread Pods)

**Use case**: DON'T run pods on the same node/zone (high availability).

```yaml
# Frontend replicas should spread across zones
spec:
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app
              operator: In
              values:
              - frontend
          topologyKey: topology.kubernetes.io/zone
```

**Effect**:
```
3 frontend pods, 3 zones (us-east-1a, 1b, 1c)

Scheduler spreads:
  frontend-1 → us-east-1a
  frontend-2 → us-east-1b
  frontend-3 → us-east-1c

If zone fails, other zones still serve traffic
```

**Required vs preferred**:
```yaml
# Required: Hard rule (pod won't schedule if can't be met)
requiredDuringSchedulingIgnoredDuringExecution:
  - labelSelector: ...
    topologyKey: kubernetes.io/hostname

# Preferred: Soft rule (scheduler tries, but not guaranteed)
preferredDuringSchedulingIgnoredDuringExecution:
  - weight: 100
    podAffinityTerm:
      labelSelector: ...
      topologyKey: kubernetes.io/hostname
```

**Use case matrix**:
```
Pod Affinity: Cache + App on same node (low latency)
Pod Anti-Affinity: Replicas spread across zones (high availability)
```

---

## 3. Taints and Tolerations

**Use case**: Reserve nodes for specific workloads.

### Taints (on nodes)

**Taint** = "This node repels pods (unless they tolerate this taint)"

```bash
# Taint a node (GPU workloads only)
kubectl taint nodes node1 gpu=true:NoSchedule

# Taint effects:
# - NoSchedule: Don't schedule new pods (existing pods stay)
# - PreferNoSchedule: Avoid scheduling (soft)
# - NoExecute: Evict existing pods that don't tolerate
```

**Result**: Normal pods won't schedule on node1.

### Tolerations (on pods)

**Toleration** = "This pod tolerates specific taints"

```yaml
spec:
  tolerations:
  - key: gpu
    operator: Equal
    value: "true"
    effect: NoSchedule

  containers:
  - name: ml-training
    image: tensorflow:latest
```

**Result**: This pod CAN schedule on node1 (tolerates the gpu taint).

### Common Use Cases

**1. Dedicated nodes for specific teams**:
```bash
kubectl taint nodes node10-node20 team=platform:NoSchedule

# Platform team pods tolerate this, other teams can't use these nodes
```

**2. Isolate GPU/specialized hardware**:
```bash
kubectl taint nodes gpu-node1 nvidia.com/gpu=present:NoSchedule

# Only GPU workloads (with toleration) use expensive GPU nodes
```

**3. Node maintenance**:
```bash
kubectl taint nodes node5 maintenance=true:NoExecute

# Evicts all pods that don't tolerate maintenance
# Prevents new pods from scheduling
```

**4. Automatic taints** (Kubernetes adds these):
```
node.kubernetes.io/not-ready:NoExecute       # Node not ready
node.kubernetes.io/unreachable:NoExecute     # Node unreachable
node.kubernetes.io/disk-pressure:NoSchedule  # Low disk space
node.kubernetes.io/memory-pressure:NoSchedule # Low memory
node.kubernetes.io/network-unavailable:NoSchedule # Network issue
```

**Toleration operators**:
```yaml
# Exact match
- key: gpu
  operator: Equal
  value: "true"
  effect: NoSchedule

# Key exists (any value)
- key: gpu
  operator: Exists
  effect: NoSchedule

# Tolerate all taints (dangerous!)
- operator: Exists
```

---

## 4. Resource Requests and Limits

Recall from `02_pods_workloads.md`, pods specify resource requirements.

### Requests (Guaranteed Resources)

```yaml
spec:
  containers:
  - name: app
    resources:
      requests:
        cpu: "500m"     # 0.5 CPU cores
        memory: "512Mi"
```

**Scheduler uses requests**:
```
Node has: 4 CPUs, 16Gi memory
Running pods requested: 2 CPUs, 8Gi memory
Allocatable: 2 CPUs, 8Gi memory

New pod requests: 1 CPU, 4Gi → ✓ Fits
New pod requests: 3 CPUs, 4Gi → ✗ Doesn't fit (CPU)
```

**Important**: Requests don't limit usage, they're just scheduling input.

### Limits (Maximum Resources)

```yaml
spec:
  containers:
  - name: app
    resources:
      limits:
        cpu: "1000m"  # 1 CPU core max
        memory: "1Gi" # 1Gi max
```

**Enforcement** (via cgroups, recall `01_fundamentals/01_cgroups_namespaces.md`):
```
CPU limit: Throttled if exceeded (container slows down)
Memory limit: OOMKilled if exceeded (container killed and restarted)
```

### QoS (Quality of Service) Classes

Kubernetes assigns QoS (Quality of Service) based on requests/limits:

**1. Guaranteed** (highest priority):
```yaml
# ALL containers have requests == limits for CPU AND memory
resources:
  requests:
    cpu: "1"
    memory: "1Gi"
  limits:
    cpu: "1"
    memory: "1Gi"
```

**2. Burstable** (medium priority):
```yaml
# At least one container has requests < limits (or only requests)
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "2"
    memory: "2Gi"
```

**3. BestEffort** (lowest priority):
```yaml
# NO requests or limits specified
resources: {}
```

**Eviction order** (when node runs out of resources):
```
1. BestEffort pods evicted first
2. Burstable pods evicted next (those exceeding requests)
3. Guaranteed pods evicted last (only if necessary)
```

**When to use each**:
```
Guaranteed: Critical services (databases, control plane components)
Burstable: Most apps (allow bursting, but have baseline)
BestEffort: Low-priority batch jobs, experimentation
```

---

## 5. Autoscaling

### 5.1 Horizontal Pod Autoscaler (HPA)

**Goal**: Scale number of pod replicas based on metrics (HPA is Horizontal Pod Autoscaler).

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # ← Target 70% CPU
```

**How it works**:
```
Every 15 seconds (default):
  1. HPA controller queries metrics (from metrics-server)
  2. Calculates current utilization
  3. Compares to target
  4. Scales replicas up or down

Example:
  Current: 3 replicas, average 90% CPU utilization
  Target: 70% CPU
  Calculation: 3 * (90 / 70) = 3.86 → Round up to 4 replicas
  Action: Scale Deployment to 4 replicas
```

**Multiple metrics**:
```yaml
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      type: Utilization
      averageUtilization: 70

- type: Resource
  resource:
    name: memory
    target:
      type: AverageValue
      averageValue: 1Gi

# Scale based on whichever metric requires MORE replicas
```

**Custom metrics** (e.g., HTTP requests/sec):
```yaml
- type: Pods
  pods:
    metric:
      name: http_requests_per_second
    target:
      type: AverageValue
      averageValue: "1000"  # Target 1000 RPS per pod
```

**Cooldown periods**:
```yaml
behavior:
  scaleDown:
    stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
    policies:
    - type: Percent
      value: 50  # Scale down max 50% at once
      periodSeconds: 60

  scaleUp:
    stabilizationWindowSeconds: 0  # Scale up immediately
    policies:
    - type: Pods
      value: 4  # Add max 4 pods at once
      periodSeconds: 60
```

**Prerequisites**:
```bash
# Install metrics-server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify
kubectl top nodes
kubectl top pods
```

### 5.2 Vertical Pod Autoscaler (VPA)

**Goal**: Automatically adjust pod resource requests/limits (VPA is Vertical Pod Autoscaler).

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: backend-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  updatePolicy:
    updateMode: "Auto"  # Or "Recreate", "Initial", "Off"
```

**How it works**:
```
VPA watches actual resource usage
  ↓
Calculates optimal requests/limits
  ↓
Updates pod specs (requires pod restart!)

Example:
  Initial: requests.cpu=500m, limits.cpu=1000m
  Observed: Pod consistently uses 200m CPU
  VPA action: Lower requests to 250m (saves cluster resources)
```

**Update modes**:
- **Off**: Only recommend, don't apply
- **Initial**: Set requests on pod creation only
- **Recreate**: Delete and recreate pods with new requests
- **Auto**: Update pods in-place (requires feature gate)

**Important**: VPA requires pod restart (disruptive for stateful apps).

**HPA vs VPA**:
```
HPA: Scales replicas (horizontal scaling)
VPA: Adjusts resource requests (vertical scaling)

Don't use both on same metric (conflict)
  ✓ HPA on CPU + VPA on memory → OK
  ✗ HPA on CPU + VPA on CPU → Conflict
```

### 5.3 Cluster Autoscaler

**Goal**: Add/remove nodes based on pending pods.

```
Cluster Autoscaler watches for:
  - Pending pods (no node has capacity) → Add nodes
  - Underutilized nodes (all pods can fit elsewhere) → Remove nodes
```

**Configuration** (cloud-provider specific):
```yaml
# AWS example
spec:
  minSize: 2
  maxSize: 20
  desiredCapacity: 5
```

**Scale up trigger**:
```
Pod can't schedule (no node has enough CPU/memory)
  ↓
Cluster Autoscaler requests new node from cloud provider
  ↓
Node joins cluster after ~5 minutes
  ↓
Scheduler places pending pod on new node
```

**Scale down trigger**:
```
Node is underutilized (<50% resources requested) for 10 min
  ↓
AND all pods can fit on other nodes
  ↓
Cluster Autoscaler cordons node (no new pods)
  ↓
Evicts pods gracefully
  ↓
Deletes node from cloud provider
```

**Prevents scale-down** if node has:
- Pods with local storage
- Pods not managed by controller (raw pods)
- Pods with PodDisruptionBudget that would be violated

---

## 6. Resource Quotas and Limit Ranges

### Resource Quotas (Namespace Level)

**Goal**: Limit total resources per namespace.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
  namespace: team-a
spec:
  hard:
    requests.cpu: "20"      # Max 20 CPUs requested
    requests.memory: "40Gi" # Max 40Gi memory requested
    limits.cpu: "40"        # Max 40 CPUs total limits
    limits.memory: "80Gi"   # Max 80Gi memory total limits
    pods: "50"              # Max 50 pods
    services: "10"          # Max 10 services
```

**Enforcement**:
```
Team A has used: 18 CPUs, 35Gi memory

New pod requests: 3 CPUs, 2Gi → ✗ Rejected (exceeds CPU quota)
New pod requests: 1 CPU, 2Gi → ✓ Allowed (within quota)
```

### Limit Ranges (Per-Pod/Container Constraints)

**Goal**: Enforce min/max/default resources per pod/container.

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: defaults
  namespace: team-a
spec:
  limits:
  - max:
      cpu: "4"
      memory: "8Gi"
    min:
      cpu: "100m"
      memory: "64Mi"
    default:  # If not specified
      cpu: "500m"
      memory: "512Mi"
    defaultRequest:  # If not specified
      cpu: "250m"
      memory: "256Mi"
    type: Container
```

**Effect**:
```
Pod with no resources specified:
  → Gets default: requests.cpu=250m, limits.cpu=500m

Pod with requests.cpu=50m:
  → ✗ Rejected (below min 100m)

Pod with limits.cpu=8:
  → ✗ Rejected (above max 4)
```

---

## 7. Pod Priority and Preemption

**Goal**: Some pods are more important (evict lower priority pods if needed).

### Priority Classes

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000  # ← Higher number = higher priority
globalDefault: false
description: "Critical production services"
```

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 1000
globalDefault: false
description: "Batch jobs, can be preempted"
```

### Using Priority Classes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-app
spec:
  priorityClassName: high-priority  # ← Reference priority class
  containers:
  - name: app
    image: critical:1.0
```

### Preemption

**Scenario**:
```
Cluster is full (no resources available)
High-priority pod needs to schedule

Scheduler:
  1. Finds nodes where evicting lower-priority pods would make room
  2. Evicts those pods (graceful termination)
  3. Schedules high-priority pod
```

**Example**:
```
Node: 4 CPUs total, 4 CPUs allocated

Running pods:
  - batch-job (priority 1000, 2 CPUs)
  - analytics (priority 1000, 2 CPUs)

New pod arrives:
  - web-app (priority 1000000, 2 CPUs)

Action:
  1. Evict batch-job (2 CPUs freed)
  2. Schedule web-app
  3. batch-job becomes pending (will schedule when resources available)
```

**System priorities** (built-in):
```
system-node-critical: 2000001000  (kubelet, kube-proxy)
system-cluster-critical: 2000000000  (CoreDNS, metrics-server)
```

**Use cases**:
- Production services > batch jobs
- Customer-facing > internal tools
- Real-time > analytics

---

## Quick Reference

### Scheduling Decision Factors

```
Filtering (eliminates nodes):
  1. Sufficient resources (CPU, memory, disk)
  2. Node selector matches
  3. Taints tolerated
  4. Required affinity rules satisfied

Scoring (ranks remaining nodes):
  1. Balanced resource allocation
  2. Preferred affinity rules
  3. Spread pods for HA
  4. Image locality (node already has image)
```

### Common Commands

```bash
# Check why pod isn't scheduling
kubectl describe pod pending-pod  # Look at Events

# View node resources
kubectl describe nodes | grep -A 5 "Allocated resources"
kubectl top nodes

# Manually schedule (bypass scheduler)
kubectl run test --image=nginx --overrides='{"spec":{"nodeName":"node1"}}'

# Drain node (evict all pods)
kubectl drain node1 --ignore-daemonsets

# Uncordon node (allow scheduling again)
kubectl uncordon node1

# Check HPA status
kubectl get hpa
kubectl describe hpa frontend-hpa

# Check resource quotas
kubectl get resourcequota -n team-a
kubectl describe resourcequota team-quota -n team-a
```

### Resource Units

```
CPU:
  1 = 1 CPU core
  500m = 0.5 cores (milli-cores)
  100m = 0.1 cores (minimum practical value)

Memory:
  1Gi = 1 gibibyte (1024^3 bytes)
  1G = 1 gigabyte (1000^3 bytes)
  Common: Mi (mebibyte), Gi (gibibyte)
```

---

## Summary

**Scheduling** places pods on nodes:
- **Filtering**: Eliminate unsuitable nodes
- **Scoring**: Rank viable nodes

**Node selection**:
- **Node selector**: Simple label matching
- **Node affinity**: Flexible required/preferred rules
- **Pod affinity**: Co-locate pods
- **Pod anti-affinity**: Spread pods

**Taints/Tolerations**:
- **Taints**: Reserve nodes for specific workloads
- **Tolerations**: Allow pods to use tainted nodes

**Resources**:
- **Requests**: Minimum guaranteed (scheduler uses this)
- **Limits**: Maximum allowed (cgroups enforce this)
- **QoS classes**: Guaranteed > Burstable > BestEffort

**Autoscaling**:
- **HPA**: Scale replicas based on metrics
- **VPA**: Adjust resource requests (requires restart)
- **Cluster Autoscaler**: Add/remove nodes

**Resource management**:
- **ResourceQuota**: Namespace-level limits
- **LimitRange**: Per-pod/container constraints
- **PriorityClass**: Evict lower-priority pods if needed

**Next**: Now that pods are scheduled and running, we'll explore how they persist data: **Storage and Volumes**.

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all container topics, see:
> **→ [Complete Container Learning Resources](../00_LEARNING_RESOURCES.md)** 📚

- **[Resource Management Best Practices](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)** - Official guide to setting resource requests and limits
- **[Vertical Pod Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)** - Automatically adjust resource requests based on actual usage
- **[Horizontal Pod Autoscaler](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)** - Scale workloads based on CPU, memory, or custom metrics

---

## Related Documents

- **Previous**: `03_orchestration/03_services_networking.md` - Pod networking
- **Next**: `03_orchestration/05_storage_volumes.md` - Persistent storage
- **Foundation**: `01_fundamentals/01_cgroups_namespaces.md` - How cgroups enforce limits
- **Related**: `02_pods_workloads.md` - Resource requests/limits in pod specs
