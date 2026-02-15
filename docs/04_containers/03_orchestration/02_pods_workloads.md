---
level: intermediate
estimated_time: 50 min
prerequisites:
  - 04_containers/03_orchestration/01_kubernetes_architecture.md
  - 04_containers/01_fundamentals/01_cgroups_namespaces.md
next_recommended:
  - 04_containers/03_orchestration/03_services_networking.md
tags: [kubernetes, pods, deployments, statefulsets, daemonsets, jobs]
---

# Pods and Workload Controllers

## Learning Objectives

After reading this document, you will understand:
- What a pod is and why it's the atomic unit
- How multiple containers share a pod's network namespace
- The different workload controllers and when to use each
- How Deployments manage rolling updates
- When to use StatefulSets vs Deployments
- DaemonSets, Jobs, and CronJobs use cases

## Prerequisites

Before reading this, you should understand:
- Kubernetes architecture and control plane components
- Container namespaces (especially network namespaces)
- Basic containerization concepts

---

## 1. The Pod: Kubernetes' Atomic Unit

### Why Not Just Containers?

Kubernetes could have used containers as its primitive, but pods solve real problems:

**Problem 1: Co-located containers**
```
Example: Web app + log shipper
- nginx container serves content
- fluentd container tails nginx logs
- Both need to access the same log file
- Both need to start/stop together
```

**Problem 2: Shared networking**
```
Example: App + sidecar proxy
- App listens on localhost:8080
- Envoy proxy listens on localhost:15001
- They communicate over localhost (no network traversal)
```

**Solution: The Pod**
A pod is one or more containers that:
- Share the same network namespace (same IP, localhost works)
- Share the same IPC namespace (can use shared memory)
- Can share volumes
- Are scheduled as a single unit (always co-located on same node)

### Pod Architecture

```
┌─────────────────────────────────────────────────┐
│ Pod: "frontend-abc123"                          │
│ IP: 10.244.1.5                                  │
│                                                 │
│ ┌─────────────────────┐  ┌──────────────────┐  │
│ │  nginx container    │  │ log-shipper      │  │
│ │  Port: 80           │  │ (sidecar)        │  │
│ │  /usr/share/nginx   │  │                  │  │
│ └─────────────────────┘  └──────────────────┘  │
│           ↓ ↓                      ↓            │
│  ┌────────────────────────────────────────┐    │
│  │  Shared Network Namespace              │    │
│  │  eth0: 10.244.1.5                      │    │
│  │  lo: 127.0.0.1 (localhost)             │    │
│  └────────────────────────────────────────┘    │
│                                                 │
│  ┌────────────────────────────────────────┐    │
│  │  Volume: logs (emptyDir)               │    │
│  │  /var/log/nginx → shared by both       │    │
│  └────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### Pause Container: The Hidden Infrastructure

**Every pod has a hidden container**: the "pause" container (also called "infra" container).

```
$ kubectl get pods -o wide
NAME           READY   STATUS    RESTARTS   AGE
frontend-abc   2/2     Running   0          1m

But on the node:
$ crictl ps
CONTAINER ID  NAME          STATE   POD ID      POD NAME
a1b2c3d4e5f6  nginx         Running 1234567890  frontend-abc
f6e5d4c3b2a1  log-shipper   Running 1234567890  frontend-abc
0987654321ab  POD           Running 1234567890  frontend-abc
              ↑ The pause container
```

**Why the pause container?**
1. **Holds the network namespace**: Created first, other containers join it
2. **Persists across container restarts**: If nginx crashes and restarts, network stays stable
3. **PID 1 reaping**: Handles zombie processes from other containers

**Connection to earlier concepts**:
Recall from `01_fundamentals/01_cgroups_namespaces.md`, namespaces are owned by a process. The pause container is that process for the pod's network namespace.

---

## 2. Pod Lifecycle

### Pod Phases

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌───────────┐
│ Pending │ →   │ Running │ →   │ Succeeded │
│         │     │         │     │  or       │
│         │     │         │     │ Failed    │
└─────────┘     └─────────┘     └───────────┘
```

1. **Pending**: Pod accepted by cluster, but container(s) not yet created
   - Reasons: Image pulling, scheduling, insufficient resources

2. **Running**: Pod bound to node, all containers created, at least one running

3. **Succeeded**: All containers terminated successfully (exit code 0)
   - Typical for Jobs

4. **Failed**: All containers terminated, at least one failed (non-zero exit)

5. **Unknown**: Can't determine pod state (node communication lost)

### Container States

Each container in a pod has its own state:

1. **Waiting**: Not running yet (pulling image, waiting for init container)
2. **Running**: Executing normally
3. **Terminated**: Finished execution or was killed

### Init Containers

**Problem**: What if container A needs a database to be ready before starting?

**Solution**: Init containers run sequentially before main containers.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  initContainers:
  - name: wait-for-db
    image: busybox
    command: ['sh', '-c', 'until nslookup db-service; do sleep 2; done']

  containers:
  - name: app
    image: myapp:1.0
    # This only starts after init container succeeds
```

**Execution order**:
```
1. Pod created
2. Init container "wait-for-db" starts
3. Loops until db-service DNS resolves
4. Init container exits successfully (code 0)
5. Main container "app" starts
```

**Common init container uses**:
- Wait for dependencies (databases, APIs)
- Populate shared volumes (config, static files)
- Run schema migrations
- Delay startup for security scans

---

## 3. Workload Controllers

Pods are mortal. When they die, they're gone (not resurrected). **Workload controllers** manage pods' lifecycle.

### 3.1 ReplicaSet

**Goal**: Maintain a stable set of pod replicas.

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: frontend
spec:
  replicas: 3  # ← Desired count
  selector:
    matchLabels:
      app: frontend
  template:  # ← Pod template
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
```

**How it works**:
```
ReplicaSet controller watches pods matching selector
  Current: 2 pods with label app=frontend
  Desired: 3 replicas
  Action: Create 1 new pod from template

  Current: 4 pods with label app=frontend
  Desired: 3 replicas
  Action: Delete 1 pod (oldest first)
```

**Problem with ReplicaSets**: Updates require manual intervention.

```
# Update image version
kubectl edit replicaset frontend
# Change image: nginx:1.21 → nginx:1.22

# But existing pods don't update!
# You must manually delete them for new ones to spawn
kubectl delete pod frontend-abc frontend-def frontend-ghi
```

**Solution**: Don't use ReplicaSets directly. Use Deployments.

### 3.2 Deployment (Most Common)

**Goal**: Declarative updates for pods, with rollout/rollback.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 3
  strategy:
    type: RollingUpdate  # ← Key difference from ReplicaSet
    rollingUpdate:
      maxUnavailable: 1  # Max pods down during update
      maxSurge: 1        # Max extra pods during update
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
```

**Deployment → ReplicaSet → Pods**:
```
Deployment: frontend
    ↓ creates
ReplicaSet: frontend-789abc (image: nginx:1.21)
    ↓ creates
Pods: frontend-789abc-1, frontend-789abc-2, frontend-789abc-3
```

**Rolling update process**:
```
$ kubectl set image deployment/frontend nginx=nginx:1.22

Step 1: Create new ReplicaSet
  Deployment: frontend
      ↓ creates
  ReplicaSet: frontend-987def (image: nginx:1.22, replicas: 0)

Step 2: Scale up new, scale down old (gradually)
  Old ReplicaSet: 3 → 2 → 1 → 0
  New ReplicaSet: 0 → 1 → 2 → 3

  Time  Old  New  Total (max 4 due to maxSurge: 1)
  ────────────────────────────────────────────────
  T+0s   3    0     3
  T+2s   3    1     4  (maxSurge reached)
  T+5s   2    1     3  (old pod terminated)
  T+7s   2    2     4
  T+10s  1    2     3
  T+12s  1    3     4
  T+15s  0    3     3  (rollout complete)
```

**Key benefits**:
1. **Zero-downtime updates**: Old pods serve traffic until new ones are ready
2. **Rollback**: Old ReplicaSet kept (by default, last 10)
3. **Pause/resume**: Can halt rollout mid-way
4. **History**: See all revisions

**Rollback example**:
```bash
# Oops, version 1.22 has a bug
$ kubectl rollout undo deployment/frontend

# Goes back to previous ReplicaSet (nginx:1.21)
# Uses the same rolling update process
```

**Update strategies**:

1. **RollingUpdate** (default): Gradual replacement
   - Pros: Zero downtime, safe
   - Cons: Old and new versions coexist briefly

2. **Recreate**: Delete all old pods, then create new
   - Pros: Simple, no version coexistence
   - Cons: Downtime during update

```yaml
spec:
  strategy:
    type: Recreate  # All pods deleted, then recreated
```

### 3.3 StatefulSet

**Problem**: Deployments treat pods as interchangeable. But what about:
- Databases (each replica needs unique persistent storage)
- Clustered apps (Kafka, Zookeeper need stable network IDs)
- Apps that care about ordering (replica 0 must start before replica 1)

**Solution**: StatefulSet provides:
1. **Stable network identity**: Predictable DNS names
2. **Stable storage**: Each pod gets its own PersistentVolume
3. **Ordered deployment**: Pods created/deleted in sequence
4. **Ordered updates**: Rolling updates respect order

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql  # ← Required for stable network
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:  # ← Each pod gets unique PVC
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
```

**Pod naming**:
```
Deployment pods: frontend-789abc-1, frontend-789abc-2 (random)
StatefulSet pods: mysql-0, mysql-1, mysql-2 (ordinal index)
```

**DNS names**:
```
mysql-0.mysql.default.svc.cluster.local
mysql-1.mysql.default.svc.cluster.local
mysql-2.mysql.default.svc.cluster.local
  ↑      ↑       ↑        ↑
  pod  service namespace cluster
```

**Startup/shutdown order**:
```
Startup:  mysql-0 → mysql-1 → mysql-2  (wait for previous to be ready)
Shutdown: mysql-2 → mysql-1 → mysql-0  (reverse order)

Update:   mysql-2 → mysql-1 → mysql-0  (reverse, one at a time)
```

**PersistentVolumes**:
```
mysql-0 → PVC: data-mysql-0 → PV: volume-abc123
mysql-1 → PVC: data-mysql-1 → PV: volume-def456
mysql-2 → PVC: data-mysql-2 → PV: volume-ghi789

If mysql-1 pod is deleted and recreated:
  → New pod still gets PVC: data-mysql-1 (same data!)
```

**When to use StatefulSet**:
- Databases (MySQL, PostgreSQL, MongoDB)
- Distributed systems (Kafka, Cassandra, Elasticsearch)
- Apps requiring stable hostnames
- Apps requiring persistent, pod-specific storage

**When NOT to use StatefulSet**:
- Stateless apps (use Deployment instead)
- Apps that can use shared storage (use Deployment + RWX volume)
- Apps that don't care about pod names/order

### 3.4 DaemonSet

**Goal**: Run one pod per node (or subset of nodes).

**Use cases**:
- **Log collectors**: fluentd/logstash on every node
- **Monitoring agents**: Prometheus node-exporter
- **Network plugins**: CNI agents (Calico, Cilium)
- **Storage plugins**: CSI node drivers

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      containers:
      - name: node-exporter
        image: prom/node-exporter:latest
        ports:
        - containerPort: 9100
```

**Behavior**:
```
Cluster has 5 nodes → DaemonSet creates 5 pods (one per node)
Add a 6th node → DaemonSet automatically creates a 6th pod
Remove a node → DaemonSet removes the pod from that node
```

**Node selection**:
```yaml
spec:
  template:
    spec:
      nodeSelector:
        disktype: ssd  # Only run on SSD nodes

      # Or use node affinity for complex rules
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/os
                operator: In
                values:
                - linux
```

**Updating DaemonSets**:
```yaml
spec:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1  # Update one node at a time
```

### 3.5 Job

**Goal**: Run a task to completion, then stop.

**Use cases**:
- Batch processing
- Database migrations
- Report generation
- ETL jobs

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: batch-job
spec:
  completions: 5      # Run 5 successful pods total
  parallelism: 2      # Run 2 at a time
  backoffLimit: 3     # Retry failed pods up to 3 times
  template:
    spec:
      restartPolicy: Never  # Jobs can't use Always
      containers:
      - name: worker
        image: batch-processor:1.0
        command: ["./process-batch.sh"]
```

**Execution**:
```
T+0s: Start pod 1, pod 2 (parallelism: 2)
T+5s: Pod 1 succeeds (1/5 completions)
T+5s: Start pod 3
T+8s: Pod 2 succeeds (2/5 completions)
T+8s: Start pod 4
T+12s: Pod 3 succeeds (3/5 completions)
T+12s: Start pod 5
T+15s: Pod 4 succeeds (4/5 completions)
T+20s: Pod 5 succeeds (5/5 completions)
T+20s: Job complete! All pods left running (check logs later)
```

**Cleanup**:
```yaml
spec:
  ttlSecondsAfterFinished: 3600  # Delete job 1 hour after completion
```

**Restart policies**:
```
Deployment/StatefulSet: restartPolicy: Always (default)
Job:                    restartPolicy: OnFailure or Never
```

### 3.6 CronJob

**Goal**: Run Jobs on a schedule (like cron).

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-backup
spec:
  schedule: "0 2 * * *"  # 2 AM daily (cron format)
  jobTemplate:  # ← Creates Jobs, which create Pods
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: backup
            image: backup-tool:1.0
            command: ["./backup.sh"]
```

**Schedule format** (standard cron):
```
* * * * *
│ │ │ │ │
│ │ │ │ └── Day of week (0-6, 0=Sunday)
│ │ │ └──── Month (1-12)
│ │ └────── Day of month (1-31)
│ └──────── Hour (0-23)
└────────── Minute (0-59)

Examples:
"0 2 * * *"        → 2:00 AM daily
"*/15 * * * *"     → Every 15 minutes
"0 0 * * 0"        → Midnight every Sunday
"0 9-17 * * 1-5"   → Every hour from 9 AM-5 PM, Monday-Friday
```

**Concurrency control**:
```yaml
spec:
  concurrencyPolicy: Forbid  # Skip new run if previous still running
  # Or: Allow (default), Replace (kill old, start new)
```

**History**:
```yaml
spec:
  successfulJobsHistoryLimit: 3  # Keep last 3 successful jobs
  failedJobsHistoryLimit: 1      # Keep last 1 failed job
```

---

## 4. Workload Comparison

| Controller    | Replicas | Ordering | Stable Network | Stable Storage | Use Case                          |
|---------------|----------|----------|----------------|----------------|-----------------------------------|
| ReplicaSet    | Yes      | No       | No             | No             | Rarely used directly              |
| Deployment    | Yes      | No       | No             | No             | Stateless apps (most common)      |
| StatefulSet   | Yes      | Yes      | Yes            | Yes            | Databases, clustered apps         |
| DaemonSet     | One/node | No       | No             | No             | Logging, monitoring, node agents  |
| Job           | N times  | No       | No             | No             | Batch processing, one-off tasks   |
| CronJob       | Scheduled| No       | No             | No             | Scheduled batch jobs              |

---

## 5. Pod Specifications Deep Dive

### Resource Requests and Limits

```yaml
spec:
  containers:
  - name: app
    resources:
      requests:  # ← Minimum guaranteed
        cpu: "500m"     # 0.5 CPU cores
        memory: "512Mi" # 512 MiB
      limits:    # ← Maximum allowed
        cpu: "1000m"    # 1 CPU core
        memory: "1Gi"   # 1 GiB
```

**How requests affect scheduling**:
```
Node has 4 CPU cores, 8Gi memory
Running pods requested: 2 cores, 4Gi

New pod requests: 1 core, 2Gi
  Remaining: 2 cores, 4Gi → Fits! Pod scheduled here

New pod requests: 3 cores, 2Gi
  Remaining: 2 cores, 4Gi → Doesn't fit (CPU), try another node
```

**How limits are enforced**:
- **CPU**: Throttled (won't get more than limit, but won't crash)
- **Memory**: OOMKilled if exceeded (pod restarted)

**Connection to cgroups**:
Recall from `01_fundamentals/01_cgroups_namespaces.md`, kubelet configures cgroups:
```bash
# CPU limit
/sys/fs/cgroup/cpu/kubepods/pod-abc123/cpu.cfs_quota_us = 100000
/sys/fs/cgroup/cpu/kubepods/pod-abc123/cpu.cfs_period_us = 100000
# Result: 1 CPU core (100000/100000)

# Memory limit
/sys/fs/cgroup/memory/kubepods/pod-abc123/memory.limit_in_bytes = 1073741824
# Result: 1Gi
```

### Health Checks

**Three probe types**:

1. **Liveness Probe**: Is the container alive?
   - If fails: kubelet restarts container

2. **Readiness Probe**: Is the container ready for traffic?
   - If fails: Remove from service endpoints (no traffic)

3. **Startup Probe**: Has the container finished starting?
   - If fails: kubelet restarts container
   - Delays liveness/readiness until startup succeeds (for slow-starting apps)

**Example**:
```yaml
spec:
  containers:
  - name: app
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 15
      periodSeconds: 10
      timeoutSeconds: 1
      failureThreshold: 3  # Fail 3 times before restart

    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      periodSeconds: 5
      successThreshold: 1  # One success = ready

    startupProbe:  # For apps that take 60+ seconds to start
      httpGet:
        path: /healthz
        port: 8080
      failureThreshold: 30
      periodSeconds: 10
      # Gives 300 seconds (30 * 10) to start
```

**Probe methods**:
```yaml
# HTTP GET
httpGet:
  path: /health
  port: 8080

# TCP Socket
tcpSocket:
  port: 3306

# Exec command
exec:
  command:
  - cat
  - /tmp/healthy
```

### Lifecycle Hooks

**PostStart**: Runs immediately after container starts
```yaml
lifecycle:
  postStart:
    exec:
      command: ["/bin/sh", "-c", "echo Hello > /tmp/ready"]
```

**PreStop**: Runs before container is terminated
```yaml
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "nginx -s quit"]  # Graceful shutdown
```

**Termination flow**:
```
1. Pod marked for deletion
2. PreStop hook runs (if defined)
3. SIGTERM sent to container PID 1
4. Wait up to terminationGracePeriodSeconds (default 30s)
5. SIGKILL if still running
```

---

## 6. Advanced Patterns

### Sidecar Pattern

Main container + helper containers sharing pod resources.

```yaml
spec:
  containers:
  - name: app
    image: myapp:1.0
    ports:
    - containerPort: 8080

  - name: log-shipper  # ← Sidecar
    image: fluentd:latest
    volumeMounts:
    - name: logs
      mountPath: /var/log

  volumes:
  - name: logs
    emptyDir: {}
```

**Other sidecar uses**:
- Service mesh (Istio/Linkerd inject envoy proxy sidecar)
- Secret rotation (fetch secrets from vault)
- Configuration hot-reload

### Ambassador Pattern

Sidecar proxies connections to external services.

```yaml
spec:
  containers:
  - name: app
    image: myapp:1.0
    env:
    - name: DB_HOST
      value: "localhost"  # ← Talks to sidecar, not real DB

  - name: db-proxy  # ← Ambassador
    image: cloud-sql-proxy:latest
    command:
    - /cloud_sql_proxy
    - -instances=project:region:instance=tcp:5432
```

**Benefits**:
- App code doesn't handle auth/TLS
- Easy to change backends (just update proxy config)

### Adapter Pattern

Sidecar transforms/adapts output for external systems.

```yaml
spec:
  containers:
  - name: app
    image: legacy-app:1.0
    # Outputs logs in custom format

  - name: log-adapter  # ← Adapter
    image: log-formatter:1.0
    # Reads custom format, outputs JSON for log aggregator
```

---

## Quick Reference

### Controller Selection

```
Stateless app, need rolling updates → Deployment
Stateful app, need stable IDs/storage → StatefulSet
One pod per node → DaemonSet
One-time task → Job
Scheduled task → CronJob
```

### Common kubectl Commands

```bash
# Deployments
kubectl create deployment nginx --image=nginx:1.21 --replicas=3
kubectl scale deployment/nginx --replicas=5
kubectl set image deployment/nginx nginx=nginx:1.22
kubectl rollout status deployment/nginx
kubectl rollout undo deployment/nginx
kubectl rollout history deployment/nginx

# StatefulSets
kubectl scale statefulset/mysql --replicas=5
kubectl delete pod mysql-2  # Recreated with same name

# DaemonSets
kubectl get daemonsets -n kube-system

# Jobs
kubectl create job test --image=busybox -- echo "hello"
kubectl wait --for=condition=complete job/test
kubectl logs job/test

# CronJobs
kubectl create cronjob backup --schedule="0 2 * * *" --image=backup:1.0 -- ./backup.sh
kubectl get cronjobs
kubectl get jobs  # See jobs created by CronJob
```

### Pod Troubleshooting

```bash
kubectl get pod frontend-abc -o wide  # See which node
kubectl describe pod frontend-abc     # Events, conditions
kubectl logs frontend-abc              # Container logs
kubectl logs frontend-abc -c sidecar   # Specific container
kubectl logs frontend-abc --previous   # Crashed container logs
kubectl exec -it frontend-abc -- /bin/bash  # Shell into container
kubectl debug frontend-abc --image=busybox  # Ephemeral debug container
```

---

## Summary

**Pods** are Kubernetes' atomic unit because:
- Containers often need to be co-located and share resources
- Network namespace sharing enables localhost communication
- Volumes enable file sharing between containers

**Workload controllers** manage pods' lifecycle:
- **Deployment**: Stateless apps, rolling updates (use this by default)
- **StatefulSet**: Stateful apps needing stable identity/storage
- **DaemonSet**: One pod per node (monitoring, logging)
- **Job**: Run to completion
- **CronJob**: Scheduled jobs

**Key pod features**:
- Resource requests/limits (prevent resource starvation)
- Health probes (detect and recover from failures)
- Lifecycle hooks (graceful startup/shutdown)

**Next**: Now that you understand workloads, we'll explore how pods communicate: **Services and Networking**.

---

## Related Documents

- **Previous**: `03_orchestration/01_kubernetes_architecture.md` - Control plane components
- **Next**: `03_orchestration/03_services_networking.md` - How pods discover and communicate
- **Foundation**: `01_fundamentals/01_cgroups_namespaces.md` - How pods use namespaces and cgroups
- **Related**: `02_runtimes/02_docker_containerd.md` - How kubelet actually starts containers
