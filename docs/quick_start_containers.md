---
level: foundational
estimated_time: 150 min
prerequisites: []
next_recommended:
  - 04_containers/01_fundamentals/01_cgroups_namespaces.md
tags: [quickstart, containers, docker, kubernetes, overview]
---

# Container Quick Start: 2.5-Hour Overview

## Purpose

Rapid introduction to container technology for experienced engineers familiar with VMs or traditional deployments. Covers fundamentals through Kubernetes basics.

**Time estimate**: 2.5 hours
**Audience**: Engineers new to containers, coming from VM/bare-metal background

---

## 1. Container Fundamentals (30 minutes)

### What are Containers?

**Containers** = Process isolation using Linux kernel primitives.

```
Traditional VM:
┌─────────────────────────────────┐
│ Virtual Machine                 │
│  ┌───────────────────────────┐ │
│  │ Guest OS (full kernel)    │ │
│  │  ┌─────────────────────┐  │ │
│  │  │ Application         │  │ │
│  │  └─────────────────────┘  │ │
│  └───────────────────────────┘ │
│  Hypervisor (KVM)               │
└─────────────────────────────────┘
  Host OS + Hardware

Container:
┌─────────────────────────────────┐
│  ┌─────────────────────────┐   │
│  │ Application             │   │
│  └─────────────────────────┘   │
│  Container Runtime (runc)       │
│  Host OS Kernel (shared)        │
└─────────────────────────────────┘
  Hardware

Key difference: Shared kernel vs separate kernel
```

### Core Technologies

**1. Namespaces** (isolation):
```
PID namespace: Process isolation
NET namespace: Network isolation
MNT namespace: Filesystem isolation
UTS namespace: Hostname isolation
IPC namespace: Inter-process communication isolation
USER namespace: User ID isolation
```

**Example**:
```bash
# Host sees process ID 12345
ps aux | grep myapp
# PID 12345

# Inside container sees same process as PID 1
docker exec container1 ps aux
# PID 1
```

**2. cgroups** (resource limits):
```bash
# Limit container to 1 CPU, 512MB memory
docker run --cpus=1 --memory=512m nginx

# Implemented via:
/sys/fs/cgroup/cpu/docker/container-id/cpu.cfs_quota_us
/sys/fs/cgroup/memory/docker/container-id/memory.limit_in_bytes
```

**3. Union Filesystems** (layered images):
```
Image layers (read-only):
  Layer 3: Application files ← Your code
  Layer 2: Node.js runtime
  Layer 1: Ubuntu base OS

Container layer (read-write):
  Layer 4: Runtime changes (logs, temp files)

Benefit: Share base layers across containers
```

### Containers vs VMs

| Feature          | Containers         | VMs                |
|------------------|--------------------|--------------------|
| Isolation        | Process-level      | Hardware-level     |
| Startup time     | Milliseconds       | Seconds-minutes    |
| Resource usage   | ~10 MB             | ~1 GB              |
| Security         | Shared kernel risk | Separate kernel    |
| Density          | 100s per host      | 10s per host       |

**When to use containers**: Microservices, stateless apps, CI/CD
**When to use VMs**: Different OS kernels, maximum isolation, legacy apps

---

## 2. Docker Basics (20 minutes)

### Images and Containers

**Image** = Template (like a VM template)
**Container** = Running instance of an image (like a running VM)

```bash
# Pull image from registry
docker pull nginx:1.21

# List images
docker images
# REPOSITORY   TAG    IMAGE ID     SIZE
# nginx        1.21   abc123...    133MB

# Run container
docker run -d --name web -p 8080:80 nginx:1.21
# -d: Detached (background)
# --name: Container name
# -p: Port mapping (host:container)

# List running containers
docker ps
# CONTAINER ID   IMAGE        PORTS
# def456...      nginx:1.21   0.0.0.0:8080->80/tcp

# Test
curl http://localhost:8080
# Welcome to nginx!

# View logs
docker logs web

# Execute command in container
docker exec -it web /bin/bash

# Stop and remove
docker stop web
docker rm web
```

### Building Images

**Dockerfile**:
```dockerfile
# Base image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Start command
CMD ["node", "server.js"]
```

**Build and run**:
```bash
# Build image
docker build -t myapp:v1.0 .

# Run
docker run -d -p 3000:3000 myapp:v1.0

# Test
curl http://localhost:3000
```

### Multi-Stage Builds (Best Practice)

```dockerfile
# Stage 1: Build
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Runtime
FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
CMD ["node", "dist/server.js"]

# Result: Builder stage 800MB, final image 80MB
```

---

## 3. Kubernetes Essentials (60 minutes)

### Architecture Overview

```
┌─────────────────────────────────────┐
│ Control Plane                        │
│  - API Server (kube-apiserver)       │
│  - etcd (key-value store)            │
│  - Scheduler (kube-scheduler)        │
│  - Controller Manager                │
└─────────────────────────────────────┘
              ↓ ↑
┌─────────────────────────────────────┐
│ Worker Nodes                         │
│  - kubelet (node agent)              │
│  - kube-proxy (networking)           │
│  - Container runtime (containerd)    │
│  - Pods (running containers)         │
└─────────────────────────────────────┘
```

### Pods (Basic Unit)

**Pod** = One or more containers sharing network/storage.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.21
    ports:
    - containerPort: 80
```

```bash
# Create pod
kubectl apply -f pod.yaml

# List pods
kubectl get pods
# NAME        READY   STATUS    RESTARTS   AGE
# nginx-pod   1/1     Running   0          10s

# View logs
kubectl logs nginx-pod

# Execute command
kubectl exec -it nginx-pod -- /bin/bash

# Delete pod
kubectl delete pod nginx-pod
```

### Deployments (Production Use)

**Deployment** = Manages replica pods, rolling updates.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3  # ← 3 identical pods
  selector:
    matchLabels:
      app: nginx
  template:  # ← Pod template
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
```

```bash
# Create deployment
kubectl apply -f deployment.yaml

# List deployments
kubectl get deployments
# NAME               READY   UP-TO-DATE   AVAILABLE
# nginx-deployment   3/3     3            3

# List pods (3 created automatically)
kubectl get pods
# NAME                               READY   STATUS
# nginx-deployment-abc123-1          1/1     Running
# nginx-deployment-abc123-2          1/1     Running
# nginx-deployment-abc123-3          1/1     Running

# Scale up/down
kubectl scale deployment nginx-deployment --replicas=5

# Update image (rolling update)
kubectl set image deployment/nginx-deployment nginx=nginx:1.22

# Check rollout status
kubectl rollout status deployment/nginx-deployment

# Rollback
kubectl rollout undo deployment/nginx-deployment
```

### Services (Networking)

**Service** = Stable network endpoint for pods.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  type: LoadBalancer  # ← External access
  selector:
    app: nginx  # ← Matches pods with label app=nginx
  ports:
  - port: 80
    targetPort: 80
```

```bash
# Create service
kubectl apply -f service.yaml

# List services
kubectl get services
# NAME            TYPE           CLUSTER-IP      EXTERNAL-IP
# nginx-service   LoadBalancer   10.96.100.50    203.0.113.10

# Access service
curl http://203.0.113.10
# Welcome to nginx!
```

**Service types**:
- **ClusterIP**: Internal only (default)
- **NodePort**: Accessible on node IPs
- **LoadBalancer**: Cloud load balancer (AWS ELB, GCP LB)

### ConfigMaps and Secrets

**ConfigMap** (configuration):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  database_url: "postgres://db:5432/mydb"
  log_level: "info"
```

**Secret** (sensitive data):
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=  # base64("admin")
  password: cGFzcw==  # base64("pass")
```

**Use in pod**:
```yaml
spec:
  containers:
  - name: app
    image: myapp:1.0
    env:
    - name: DATABASE_URL
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: database_url
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: password
```

### Volumes (Storage)

**PersistentVolumeClaim**:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

**Use in pod**:
```yaml
spec:
  containers:
  - name: mysql
    image: mysql:8.0
    volumeMounts:
    - name: data
      mountPath: /var/lib/mysql
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: mysql-pvc
```

---

## 4. Container Networking Basics (20 minutes)

### Container Networking Model

**Kubernetes networking requirements**:
1. All pods can communicate with each other without NAT
2. All nodes can communicate with all pods without NAT
3. Pod sees its own IP as the same IP others see

**Implementation**: CNI plugins (Calico, Cilium, Flannel, etc.)

```
Pod A (10.244.0.5) on Node 1
  ↓ CNI creates veth pair
Host network namespace (Node 1)
  ↓ Overlay/routing (VXLAN or BGP)
Host network namespace (Node 2)
  ↓ CNI delivers packet
Pod B (10.244.1.10) on Node 2
```

### Service Discovery

**DNS-based**:
```bash
# In any pod, query service name
nslookup nginx-service

# Output:
# Name:   nginx-service.default.svc.cluster.local
# Address: 10.96.100.50

# Short names work within same namespace
curl http://nginx-service:80
```

### Network Policies (Firewall Rules)

**Default**: All pods can talk to all pods.

**NetworkPolicy** (restrict):
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
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
          app: frontend  # Only frontend can access backend
    ports:
    - protocol: TCP
      port: 8080
```

---

## 5. Security Basics (20 minutes)

### Image Security

**Best practices**:
```dockerfile
# ✓ Use minimal base images
FROM gcr.io/distroless/static:nonroot

# ✓ Don't run as root
USER 1000

# ✓ Read-only filesystem
# (Specify in Kubernetes pod spec)

# ✗ Don't include secrets
# Bad: ENV API_KEY="secret123"
```

**Scan images**:
```bash
# Trivy (vulnerability scanner)
trivy image myapp:v1.0

# Output:
# myapp:v1.0 (alpine 3.14.0)
# Total: 5 (CRITICAL: 2, HIGH: 3)
```

### Pod Security

**Security context**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000

  containers:
  - name: app
    image: myapp:1.0
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

**What this does**:
- Runs as non-root user (UID 1000)
- Can't escalate to root
- Filesystem is read-only
- Drops all Linux capabilities (no privileged operations)

### RBAC (Access Control)

**Role** (permissions):
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: production
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
```

**RoleBinding** (grant permissions):
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: production
subjects:
- kind: User
  name: alice
roleRef:
  kind: Role
  name: pod-reader
```

**Effect**: User `alice` can read pods in `production` namespace.

---

## 6. Common Workflows (20 minutes)

### Development Workflow

```bash
# 1. Write code
vim app.js

# 2. Build image
docker build -t myapp:dev .

# 3. Run locally
docker run -p 3000:3000 myapp:dev

# 4. Test
curl http://localhost:3000

# 5. Push to registry
docker tag myapp:dev myregistry.io/myapp:v1.0
docker push myregistry.io/myapp:v1.0

# 6. Deploy to Kubernetes
kubectl set image deployment/myapp app=myregistry.io/myapp:v1.0
```

### Debugging Pods

```bash
# View pod details
kubectl describe pod myapp-abc123

# View logs
kubectl logs myapp-abc123

# Previous container logs (if crashed)
kubectl logs myapp-abc123 --previous

# Execute shell
kubectl exec -it myapp-abc123 -- /bin/sh

# Port forward (local access)
kubectl port-forward myapp-abc123 8080:80
# Now access http://localhost:8080

# View events
kubectl get events --sort-by='.lastTimestamp'
```

### Troubleshooting Common Issues

**Pod stuck in Pending**:
```bash
kubectl describe pod myapp-abc123
# Look for: Insufficient cpu, Insufficient memory
# Solution: Add more nodes or reduce resource requests
```

**Pod stuck in ImagePullBackOff**:
```bash
kubectl describe pod myapp-abc123
# Look for: Failed to pull image, authentication required
# Solution: Check image name, registry credentials
```

**Pod CrashLoopBackOff**:
```bash
kubectl logs myapp-abc123 --previous
# Look for: Application errors
# Solution: Fix application bug
```

---

## Quick Commands Reference

### Docker

```bash
docker pull <image>              # Download image
docker images                    # List images
docker run -d -p 8080:80 <image> # Run container
docker ps                        # List running containers
docker logs <container>          # View logs
docker exec -it <container> sh   # Shell into container
docker stop <container>          # Stop container
docker rm <container>            # Remove container
docker build -t <name> .         # Build image
```

### Kubernetes

```bash
kubectl get pods                 # List pods
kubectl get deployments          # List deployments
kubectl get services             # List services
kubectl apply -f <file.yaml>     # Create/update resources
kubectl delete -f <file.yaml>    # Delete resources
kubectl logs <pod>               # View logs
kubectl exec -it <pod> -- sh     # Shell into pod
kubectl describe pod <pod>       # Pod details
kubectl scale deployment <name> --replicas=5  # Scale
kubectl rollout status deployment/<name>      # Rollout status
```

---

## Next Steps

**Completed**: Container fundamentals, Docker basics, Kubernetes essentials, networking, and security.

**Deep dive paths**:

1. **Container Fundamentals** → `04_containers/01_fundamentals/`
   - cgroups and namespaces deep dive
   - Union filesystems
   - Container vs VM architecture

2. **Container Runtimes** → `04_containers/02_runtimes/`
   - OCI runtime landscape
   - containerd and Docker architecture
   - Kata Containers and gVisor

3. **Kubernetes Orchestration** → `04_containers/03_orchestration/`
   - Kubernetes architecture
   - Advanced workloads (StatefulSets, DaemonSets)
   - Services and networking
   - Storage and volumes
   - Production patterns

4. **Container Networking** → `04_containers/04_networking/`
   - CNI deep dive
   - Calico vs Cilium
   - eBPF networking
   - Service mesh (Istio, Linkerd)

5. **Container Security** → `04_containers/05_security/`
   - Image security and scanning
   - Runtime security (seccomp, AppArmor)
   - Pod Security Standards
   - Supply chain security

**Full learning path** (20-25 hours): See `00_START_HERE.md` Path 5: Container Platform Engineer.

---

## Key Takeaways

**Containers**:
- Process isolation (not hardware isolation like VMs)
- Fast startup, low overhead
- Share kernel (security consideration)

**Docker**:
- Build images with Dockerfile
- Run containers from images
- Multi-stage builds reduce size

**Kubernetes**:
- Pods: Basic unit (1+ containers)
- Deployments: Manage replica pods
- Services: Stable network endpoints
- ConfigMaps/Secrets: Configuration
- PVCs: Persistent storage

**Security**:
- Scan images for vulnerabilities
- Run as non-root
- Read-only filesystems
- RBAC for access control

**Networking**:
- Flat network (all pods can communicate)
- Services provide stable IPs
- NetworkPolicies for isolation

**This quick start provides a foundation**. For production use, study the detailed documentation in `04_containers/`.
