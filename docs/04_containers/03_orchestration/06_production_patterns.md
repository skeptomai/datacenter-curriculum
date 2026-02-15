---
level: intermediate
estimated_time: 50 min
prerequisites:
  - 04_containers/03_orchestration/01_kubernetes_architecture.md
  - 04_containers/03_orchestration/02_pods_workloads.md
  - 04_containers/03_orchestration/03_services_networking.md
  - 04_containers/03_orchestration/04_scheduling_resources.md
  - 04_containers/03_orchestration/05_storage_volumes.md
next_recommended:
  - 04_containers/04_networking/01_cni_deep_dive.md
tags: [kubernetes, production, best-practices, reliability, security, observability]
---

# Production Patterns and Best Practices

## Learning Objectives

After reading this document, you will understand:
- High availability patterns for applications
- Rolling update strategies and deployment safety
- Health checking and graceful shutdown
- Resource management best practices
- Security hardening for production
- Observability and debugging techniques
- Disaster recovery and backup strategies

## Prerequisites

Before reading this, you should understand:
- All core Kubernetes concepts (architecture through storage)
- Pod lifecycle and workload controllers
- Services, networking, and scheduling

---

## 1. High Availability Patterns

### 1.1 Replica Distribution

**Anti-pattern**: All replicas on same node/zone.

```yaml
# BAD: No pod anti-affinity
spec:
  replicas: 3
  # All 3 pods might land on same node!
```

**Pattern**: Spread replicas across failure domains.

```yaml
# GOOD: Spread across zones
spec:
  replicas: 3
  template:
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

      # Also spread across nodes within zone
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway  # Prefer, don't require
        labelSelector:
          matchLabels:
            app: frontend
```

**topologySpreadConstraints** (better than anti-affinity for even distribution):

```yaml
topologySpreadConstraints:
- maxSkew: 1  # ← Max difference in pod count across zones
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: DoNotSchedule  # Hard requirement
  labelSelector:
    matchLabels:
      app: frontend
```

**Example**:
```
3 zones, 5 replicas, maxSkew: 1

Valid distributions:
  Zone A: 2 pods, Zone B: 2 pods, Zone C: 1 pod ✓ (max diff = 1)
  Zone A: 1 pod, Zone B: 2 pods, Zone C: 2 pods ✓

Invalid distributions:
  Zone A: 3 pods, Zone B: 1 pod, Zone C: 1 pod ✗ (max diff = 2)
```

### 1.2 PodDisruptionBudget (PDB)

**Problem**: Node maintenance can drain all replicas simultaneously.

```bash
# Without PDB:
kubectl drain node1 --ignore-daemonsets
# Evicts all pods on node1, including 5/5 frontend replicas
# → Service down!
```

**Solution**: PodDisruptionBudget ensures minimum availability during voluntary disruptions.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: frontend-pdb
spec:
  minAvailable: 2  # ← At least 2 pods must be available
  selector:
    matchLabels:
      app: frontend
```

**Alternative** (percentage):
```yaml
spec:
  maxUnavailable: 33%  # ← Max 33% down at once
  selector:
    matchLabels:
      app: frontend
```

**How it works**:
```
Deployment has 5 replicas
PDB: minAvailable: 2

Node drain attempts to evict 3 pods from node1:
  1. Evicts pod 1 (4 remain → ✓ meets minAvailable)
  2. Evicts pod 2 (3 remain → ✓ meets minAvailable)
  3. Evicts pod 3 (2 remain → ✓ meets minAvailable)
  4. New pods scheduled on other nodes
  5. Once new pods ready, drain continues

Without PDB, all 3 evicted immediately (only 2 remain → service degraded)
```

**Important**: PDB only protects against voluntary disruptions (kubectl drain, cluster autoscaler). It does NOT prevent involuntary disruptions (node crash, OOM killer).

### 1.3 Multi-Cluster and Multi-Region

**Single cluster limitations**:
- Single point of failure (control plane)
- Regional outage = total outage
- Blast radius for misconfigurations

**Multi-cluster patterns**:

**1. Active-Passive** (disaster recovery):
```
Primary cluster (us-east-1): Serves all traffic
Secondary cluster (us-west-2): Standby, synced data

If primary fails:
  → DNS/load balancer switches to secondary
  → RPO: Hours (data sync lag)
  → RTO: 15-60 minutes (manual failover)
```

**2. Active-Active** (high availability):
```
Multiple clusters across regions
Global load balancer routes to nearest healthy cluster

Benefits:
  - Survive regional outages
  - Reduced latency (route to nearest region)
  - Rolling updates per region (gradual rollout)

Challenges:
  - Data consistency (replicate databases cross-region)
  - Increased cost (redundant infrastructure)
```

**Tools**:
- **Argo CD**: GitOps, deploy to multiple clusters
- **Istio Multi-Cluster**: Service mesh across clusters
- **Submariner**: Cross-cluster pod networking

---

## 2. Deployment Safety

### 2.1 Rolling Update Strategy

**Default rolling update**:
```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 25%  # Max 25% down during update
      maxSurge: 25%        # Max 25% extra pods during update
```

**Conservative (safer)**:
```yaml
rollingUpdate:
  maxUnavailable: 0  # Zero downtime
  maxSurge: 1        # One extra pod at a time (slower)
```

**Aggressive (faster)**:
```yaml
rollingUpdate:
  maxUnavailable: 50%
  maxSurge: 50%
```

### 2.2 Readiness Gates (Advanced Health Checking)

**Problem**: Pod is "Ready" but load balancer hasn't registered it yet.

**Solution**: Custom readiness gates.

```yaml
spec:
  readinessGates:
  - conditionType: "example.com/load-balancer-ready"

  containers:
  - name: app
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
```

**External controller** sets the condition:
```bash
# When load balancer registers pod IP:
kubectl patch pod mypod --type=json -p='[{
  "op": "add",
  "path": "/status/conditions/-",
  "value": {
    "type": "example.com/load-balancer-ready",
    "status": "True"
  }
}]'
```

**Pod is only Ready when**:
- readinessProbe succeeds (app healthy)
- AND readinessGate condition is True (LB registered)

### 2.3 Progressive Delivery

**Canary Deployments** (gradual rollout):

```
1. Deploy new version to 5% of pods
2. Monitor metrics (error rate, latency)
3. If healthy, increase to 25%
4. Continue until 100% (or rollback)
```

**Implementation** (manual):
```yaml
# Canary Deployment (5% traffic)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-canary
spec:
  replicas: 1  # 5% of total (1/20)
  template:
    metadata:
      labels:
        app: frontend
        version: v2  # New version
    spec:
      containers:
      - name: app
        image: frontend:v2

---
# Main Deployment (95% traffic)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-main
spec:
  replicas: 19  # 95% of total
  template:
    metadata:
      labels:
        app: frontend
        version: v1  # Old version
    spec:
      containers:
      - name: app
        image: frontend:v1
```

**Service selects both** (label: app=frontend):
```
Traffic distribution:
  v1: 19 pods (95%)
  v2: 1 pod (5%)
```

**Better tools**:
- **Flagger**: Automated canary with metrics-based promotion
- **Argo Rollouts**: Advanced deployment strategies (blue-green, canary)
- **Istio**: Traffic shifting via service mesh

### 2.4 Blue-Green Deployments

**Pattern**: Run two identical environments, switch traffic instantly.

```yaml
# Blue (current production)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-blue
spec:
  replicas: 10
  template:
    metadata:
      labels:
        app: frontend
        color: blue
    spec:
      containers:
      - name: app
        image: frontend:v1

---
# Green (new version, not receiving traffic yet)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-green
spec:
  replicas: 10
  template:
    metadata:
      labels:
        app: frontend
        color: green
    spec:
      containers:
      - name: app
        image: frontend:v2

---
# Service points to blue
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  selector:
    app: frontend
    color: blue  # ← Switch to green when ready
  ports:
  - port: 80
```

**Cutover**:
```bash
# Test green deployment
curl http://frontend-green:80

# Switch traffic
kubectl patch service frontend -p '{"spec":{"selector":{"color":"green"}}}'

# If issues, instant rollback
kubectl patch service frontend -p '{"spec":{"selector":{"color":"blue"}}}'
```

**Advantages**:
- Instant cutover (no gradual rollout)
- Easy rollback (flip selector back)
- Test production environment before cutover

**Disadvantages**:
- Doubles resource usage during deployment
- Database migrations tricky (must be backward-compatible)

---

## 3. Health Checking Best Practices

### 3.1 Liveness vs Readiness vs Startup

```yaml
containers:
- name: app
  startupProbe:  # ← Slow-starting apps (120s allowed)
    httpGet:
      path: /healthz
      port: 8080
    failureThreshold: 30
    periodSeconds: 10
    # Total: 30 * 10 = 300s startup time allowed

  livenessProbe:  # ← Is container alive?
    httpGet:
      path: /healthz
      port: 8080
    initialDelaySeconds: 15  # Wait 15s after startup succeeds
    periodSeconds: 10
    timeoutSeconds: 1
    failureThreshold: 3  # Fail 3 times → restart

  readinessProbe:  # ← Ready for traffic?
    httpGet:
      path: /ready
      port: 8080
    periodSeconds: 5
    timeoutSeconds: 1
    failureThreshold: 1  # One failure → remove from endpoints
```

**Probe design guidelines**:

**Liveness** (`/healthz`):
- Check: "Can this container serve traffic?"
- Example: Database connection pool not deadlocked
- **Don't check**: External dependencies (will cause cascading failures)

**Readiness** (`/ready`):
- Check: "Is this container ready for traffic right now?"
- Example: Caches warmed, database reachable
- **Do check**: External dependencies (prevent traffic to unhealthy pod)

**Startup** (`/healthz` or `/startup`):
- Check: Same as liveness, but more lenient timing
- Use for: Apps with slow initialization (data loading, model loading)

### 3.2 Graceful Shutdown

**Problem**: Pod receives SIGTERM, but requests in-flight are dropped.

**Pattern**: Implement graceful shutdown.

```yaml
spec:
  terminationGracePeriodSeconds: 60  # Default 30s

  containers:
  - name: app
    lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "sleep 5"]  # Wait for endpoints update
```

**Shutdown sequence**:
```
T+0s: Pod marked for deletion
  → Endpoints controller removes pod from Service endpoints
  → kube-proxy updates iptables (takes ~1-5 seconds to propagate)

T+0s (simultaneously): preStop hook runs
  → sleep 5 (ensures iptables updated before shutdown starts)

T+5s: preStop completes
  → SIGTERM sent to container PID 1

T+5s-60s: Application graceful shutdown
  → Finish in-flight requests
  → Close database connections
  → Flush logs

T+60s: If still running, SIGKILL sent (forced termination)
```

**Application code** (example):
```go
func main() {
    srv := &http.Server{Addr: ":8080"}

    go func() {
        srv.ListenAndServe()
    }()

    // Wait for SIGTERM
    sigterm := make(chan os.Signal, 1)
    signal.Notify(sigterm, syscall.SIGTERM)
    <-sigterm

    // Graceful shutdown
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    srv.Shutdown(ctx)  // Stop accepting new requests, finish existing
}
```

---

## 4. Resource Management

### 4.1 Right-Sizing Requests and Limits

**Anti-pattern**: No requests/limits (BestEffort QoS).

```yaml
# BAD: No resources specified
spec:
  containers:
  - name: app
    image: myapp:1.0
```

**Problem**: Pod can consume all node resources, starve other pods.

**Pattern**: Set requests based on baseline, limits based on burst.

```yaml
# GOOD: Burstable QoS
spec:
  containers:
  - name: app
    resources:
      requests:
        cpu: "500m"     # Baseline: 0.5 CPU
        memory: "512Mi" # Baseline: 512Mi
      limits:
        cpu: "2"        # Burst: up to 2 CPUs
        memory: "2Gi"   # Burst: up to 2Gi (hard limit)
```

**How to determine values**:
```bash
# Run app under load, measure actual usage
kubectl top pod myapp

# Use Vertical Pod Autoscaler (VPA) recommendations
kubectl get vpa myapp-vpa -o jsonpath='{.status.recommendation}'

# Historical data (Prometheus, Grafana)
# Look at 95th percentile CPU/memory over 30 days
```

**CPU vs Memory limits**:
```
CPU: Soft limit (throttled if exceeded, not killed)
  → Safe to set limit >> request (allow bursting)

Memory: Hard limit (OOMKilled if exceeded)
  → Set limit close to expected max (prevent memory leaks from killing node)
```

**Example**:
```yaml
# Web server (bursty CPU, steady memory)
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
  limits:
    cpu: "2"        # Allow 8x bursting
    memory: "512Mi" # Only 2x (prevent OOM)

# Database (steady CPU, bursty memory)
resources:
  requests:
    cpu: "2"
    memory: "4Gi"
  limits:
    cpu: "2"     # Guaranteed (don't throttle DB)
    memory: "8Gi" # Allow memory bursts
```

### 4.2 Resource Quotas by Namespace

**Pattern**: Prevent teams from over-consuming cluster resources.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
  namespace: team-a
spec:
  hard:
    requests.cpu: "50"
    requests.memory: "100Gi"
    limits.cpu: "100"
    limits.memory: "200Gi"
    persistentvolumeclaims: "20"
    services.loadbalancers: "2"
```

**LimitRange** (default resources):
```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: defaults
  namespace: team-a
spec:
  limits:
  - default:  # Default limits if not specified
      cpu: "1"
      memory: "1Gi"
    defaultRequest:  # Default requests if not specified
      cpu: "500m"
      memory: "512Mi"
    type: Container
```

---

## 5. Security Hardening

### 5.1 Pod Security Standards

**Three levels** (Kubernetes Pod Security Standards):

**1. Privileged** (unrestricted):
```yaml
# No restrictions (dangerous)
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: app
    securityContext:
      privileged: true  # Full host access
```

**2. Baseline** (minimally restrictive):
```yaml
# Disallow: privileged, hostNetwork, hostPID, hostIPC
apiVersion: v1
kind: Pod
spec:
  securityContext:
    runAsNonRoot: true  # Don't run as root
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

**3. Restricted** (hardened):
```yaml
# Everything from baseline, plus:
apiVersion: v1
kind: Pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000  # Specific non-root UID
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault  # Seccomp filtering
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true  # Immutable filesystem
      capabilities:
        drop:
        - ALL
    volumeMounts:
    - name: tmp
      mountPath: /tmp  # Writable tmpfs for temporary files
  volumes:
  - name: tmp
    emptyDir: {}
```

**Enforce namespace-wide** (Pod Security Admission):
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### 5.2 Network Policies (Zero Trust)

**Default deny all**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}  # All pods
  policyTypes:
  - Ingress
  - Egress
  # No rules → deny all
```

**Allow only necessary traffic**:
```yaml
# Frontend → Backend only
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080

---
# Backend → Database only (+ DNS)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Egress
  egress:
  - to:  # Database
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432

  - to:  # DNS (kube-dns)
    - namespaceSelector:
        matchLabels:
          name: kube-system
    - podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

### 5.3 Secret Management

**Anti-pattern**: Secrets in ConfigMaps or environment variables.

```yaml
# BAD: Plaintext in ConfigMap
apiVersion: v1
kind: ConfigMap
data:
  DB_PASSWORD: "mysecretpassword"  # ✗ Visible to all with access
```

**Better**: Kubernetes Secrets (base64, not encrypted by default).

```yaml
apiVersion: v1
kind: Secret
type: Opaque
data:
  password: bXlzZWNyZXRwYXNzd29yZA==  # base64("mysecretpassword")
```

**Best**: External secret managers.

**1. Sealed Secrets** (encrypt secrets in git):
```bash
# Encrypt secret
kubeseal -o yaml < secret.yaml > sealed-secret.yaml

# Safe to commit sealed-secret.yaml to git
# Controller in cluster decrypts at runtime
```

**2. External Secrets Operator** (fetch from AWS Secrets Manager, Vault, etc.):
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-secret
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
  target:
    name: db-credentials  # Creates Kubernetes Secret
  data:
  - secretKey: password
    remoteRef:
      key: prod/db/password  # Fetches from AWS Secrets Manager
```

**3. Vault Agent Injector** (sidecar injects secrets):
```yaml
annotations:
  vault.hashicorp.com/agent-inject: "true"
  vault.hashicorp.com/role: "myapp"
  vault.hashicorp.com/agent-inject-secret-db-creds: "database/creds/readonly"
```

---

## 6. Observability

### 6.1 Structured Logging

**Anti-pattern**: Unstructured logs.

```
2024-02-14 10:30:45 ERROR Failed to connect to database host=db.example.com
```

**Pattern**: Structured JSON logs.

```json
{
  "timestamp": "2024-02-14T10:30:45Z",
  "level": "ERROR",
  "message": "Failed to connect to database",
  "error": "connection refused",
  "host": "db.example.com",
  "retry_count": 3,
  "trace_id": "abc123"
}
```

**Benefits**:
- Easy to parse (log aggregators like Elasticsearch, Loki)
- Filter by fields (show me all errors for trace_id=abc123)
- Correlate with metrics/traces

### 6.2 Metrics (Prometheus)

**Application metrics** (expose /metrics endpoint):

```go
// Golang example
import "github.com/prometheus/client_golang/prometheus"

var (
    httpRequestsTotal = prometheus.NewCounterVec(
        prometheus.CounterOpts{
            Name: "http_requests_total",
            Help: "Total HTTP requests",
        },
        []string{"method", "status"},
    )
)

func handler(w http.ResponseWriter, r *http.Request) {
    // ... handle request ...
    httpRequestsTotal.WithLabelValues(r.Method, "200").Inc()
}
```

**ServiceMonitor** (Prometheus Operator):
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: myapp
spec:
  selector:
    matchLabels:
      app: myapp
  endpoints:
  - port: metrics
    interval: 30s
```

**Key metrics** (RED method):
- **R**ate: Requests per second
- **E**rrors: Error rate
- **D**uration: Latency (p50, p95, p99)

**Alerts**:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: myapp-alerts
spec:
  groups:
  - name: myapp
    rules:
    - alert: HighErrorRate
      expr: |
        sum(rate(http_requests_total{status=~"5.."}[5m]))
        / sum(rate(http_requests_total[5m])) > 0.05
      for: 5m
      annotations:
        summary: "Error rate > 5% for 5 minutes"
```

### 6.3 Distributed Tracing

**Problem**: Request spans multiple microservices, hard to debug.

**Solution**: Distributed tracing (Jaeger, Zipkin, Tempo).

```
Frontend → Backend → Database
  ↓          ↓          ↓
Span1      Span2      Span3
         (parent)

Trace ID: abc123 links all spans
```

**OpenTelemetry** (standard):
```go
import "go.opentelemetry.io/otel"

func handler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    tracer := otel.Tracer("myapp")

    ctx, span := tracer.Start(ctx, "handleRequest")
    defer span.End()

    // Call backend (propagates trace context)
    backendCall(ctx)
}
```

**View in Jaeger**:
```
Trace abc123:
  Frontend (200ms)
    → Backend (150ms)
      → Database (100ms)  ← Slow query identified!
```

---

## 7. Disaster Recovery

### 7.1 Backup Strategy

**What to backup**:
1. **etcd**: Cluster state (critical!)
2. **PersistentVolumes**: Application data
3. **Kubernetes manifests**: Git is your backup (GitOps)

**etcd backup** (manual):
```bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

**etcd backup** (automated with Velero):
```bash
# Install Velero
velero install --provider aws --bucket my-backup-bucket

# Create backup
velero backup create full-backup --include-namespaces=production

# Restore
velero restore create --from-backup full-backup
```

**PersistentVolume backups** (snapshots):
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: daily-backup
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: database-data
```

**Backup schedule** (CronJob):
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: velero-backup
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: velero/velero:latest
            command: ["velero", "backup", "create", "daily-$(date +%Y%m%d)"]
```

### 7.2 Disaster Recovery Testing

**Pattern**: Regularly test DR procedures.

```
Monthly DR drill:
  1. Delete test namespace
  2. Restore from backup
  3. Verify application works
  4. Document time to recovery (RTO)
  5. Identify gaps, improve runbooks
```

---

## Quick Reference

### Production Checklist

**High Availability**:
- [ ] Pod anti-affinity across zones
- [ ] PodDisruptionBudget configured
- [ ] Multiple replicas (>= 3)
- [ ] Multi-cluster for critical apps

**Deployment Safety**:
- [ ] Rolling update configured (maxUnavailable, maxSurge)
- [ ] Readiness probes prevent bad rollout
- [ ] Rollback tested
- [ ] Canary or blue-green for critical changes

**Health Checking**:
- [ ] Liveness probe (restart unhealthy pods)
- [ ] Readiness probe (remove from endpoints)
- [ ] Startup probe (for slow-starting apps)
- [ ] Graceful shutdown (preStop hook, terminationGracePeriodSeconds)

**Resources**:
- [ ] Requests set (scheduler can place pods)
- [ ] Limits set (prevent resource exhaustion)
- [ ] QoS class understood (Guaranteed > Burstable > BestEffort)
- [ ] ResourceQuota per namespace

**Security**:
- [ ] Pod Security Standards enforced (baseline or restricted)
- [ ] Network Policies (default deny)
- [ ] Secrets externalized (not in git)
- [ ] Non-root containers
- [ ] Read-only root filesystem

**Observability**:
- [ ] Structured logging (JSON)
- [ ] Metrics exposed (/metrics endpoint)
- [ ] Alerts configured (error rate, latency, saturation)
- [ ] Distributed tracing (for microservices)

**Disaster Recovery**:
- [ ] etcd backups automated
- [ ] PV snapshots scheduled
- [ ] GitOps (manifests in git)
- [ ] DR tested quarterly

---

## Summary

**High availability**:
- Spread replicas across zones (anti-affinity, topologySpreadConstraints)
- PodDisruptionBudget for graceful node maintenance
- Multi-cluster for critical applications

**Deployment safety**:
- Conservative rolling updates (maxUnavailable: 0)
- Readiness/liveness probes prevent bad deployments
- Progressive delivery (canary, blue-green)

**Health checking**:
- Startup probes for slow apps
- Liveness for deadlock detection
- Readiness for traffic readiness
- Graceful shutdown (preStop, terminationGracePeriodSeconds)

**Resource management**:
- Right-size requests/limits (use VPA recommendations)
- ResourceQuota per namespace
- LimitRange for defaults

**Security**:
- Pod Security Standards (restricted in production)
- Network Policies (default deny)
- External secret management (Vault, AWS Secrets Manager)

**Observability**:
- Structured logging (JSON)
- Metrics (Prometheus, RED method)
- Distributed tracing (OpenTelemetry)
- Alerts (error rate, latency)

**Disaster recovery**:
- Automated etcd backups
- PV snapshots
- GitOps (git is backup for manifests)
- Regular DR testing

**Next**: We've covered orchestration fundamentals. Now we'll dive deeper into container networking with the Container Network Interface (CNI).

---

## Related Documents

- **Previous**: `03_orchestration/05_storage_volumes.md` - Storage patterns
- **Next**: `04_networking/01_cni_deep_dive.md` - Deep dive into CNI
- **Foundation**: All orchestration documents (01-05)
- **Related**: `04_security/` section (coming next) - Security deep-dives
