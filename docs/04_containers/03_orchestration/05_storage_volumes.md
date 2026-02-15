---
level: intermediate
estimated_time: 40 min
prerequisites:
  - 04_containers/03_orchestration/02_pods_workloads.md
  - 04_containers/01_fundamentals/02_union_filesystems.md
next_recommended:
  - 04_containers/03_orchestration/06_production_patterns.md
tags: [kubernetes, storage, volumes, persistent-volumes, storage-classes, csi]
---

# Storage and Volumes

## Learning Objectives

After reading this document, you will understand:
- Why containers need volumes for persistent data
- The different volume types and their use cases
- PersistentVolumes and PersistentVolumeClaims
- StorageClasses for dynamic provisioning
- StatefulSet storage patterns
- The Container Storage Interface (CSI)
- Volume snapshots and cloning

## Prerequisites

Before reading this, you should understand:
- Container union filesystems (ephemeral by default)
- Pods and StatefulSets
- Basic storage concepts (block vs file storage)

---

## 1. The Container Storage Problem

### Why Containers Need Volumes

Recall from `01_fundamentals/02_union_filesystems.md`:

```
Container filesystem is ephemeral:
  1. Container writes file to /data/myfile.txt
  2. Container crashes
  3. Kubernetes restarts container
  4. /data/myfile.txt is GONE (new container = new filesystem layers)

Problem: Databases, logs, uploads need to survive container restarts
```

### Pod Volumes

**Solution 1**: Volumes attached to pods (pod-lifetime storage).

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: two-containers
spec:
  volumes:
  - name: shared-data
    emptyDir: {}  # ← Volume lifetime = pod lifetime

  containers:
  - name: writer
    image: busybox
    command: ['sh', '-c', 'echo "hello" > /data/hello.txt; sleep 3600']
    volumeMounts:
    - name: shared-data
      mountPath: /data

  - name: reader
    image: busybox
    command: ['sh', '-c', 'cat /data/hello.txt; sleep 3600']
    volumeMounts:
    - name: shared-data
      mountPath: /data
```

**Behavior**:
```
1. Pod starts, emptyDir volume created
2. Writer container writes to /data/hello.txt
3. Reader container reads from /data/hello.txt (same volume!)
4. If writer container crashes and restarts, file survives
5. If POD is deleted, volume is DELETED
```

**Volume lifetime summary**:
```
Container filesystem: Container lifetime (ephemeral)
emptyDir volume: Pod lifetime (survives container restarts)
PersistentVolume: Cluster lifetime (survives pod deletion)
```

---

## 2. Volume Types

### 2.1 emptyDir (Temporary Storage)

**Use case**: Scratch space, cache, inter-container sharing.

```yaml
volumes:
- name: cache
  emptyDir: {}
```

**On disk by default** (node's filesystem):
```
Node disk: /var/lib/kubelet/pods/<pod-id>/volumes/kubernetes.io~empty-dir/cache
```

**In memory** (for sensitive data):
```yaml
volumes:
- name: cache
  emptyDir:
    medium: Memory  # ← Uses tmpfs (RAM)
    sizeLimit: 1Gi
```

**Important**: Memory-backed emptyDir counts against container memory limit.

### 2.2 hostPath (Node Storage)

**Use case**: Access node filesystem (use sparingly, breaks pod portability).

```yaml
volumes:
- name: docker-socket
  hostPath:
    path: /var/run/docker.sock  # ← Node's Docker socket
    type: Socket

- name: logs
  hostPath:
    path: /var/log
    type: Directory
```

**Type validation**:
```
DirectoryOrCreate: Create dir if doesn't exist
Directory: Must exist, must be dir
FileOrCreate: Create file if doesn't exist
File: Must exist, must be file
Socket: Must exist, must be Unix socket
```

**Dangers**:
- Pod reschedules to different node → Different hostPath
- Security risk (pod can access node files)
- Not portable (assumes specific node filesystem layout)

**Valid uses**:
- DaemonSets (log collectors, monitoring agents)
- Node filesystem access for system pods

### 2.3 configMap (Configuration Files)

**Use case**: Inject configuration files into pods.

```yaml
# Create ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  app.conf: |
    server {
      listen 80;
      server_name example.com;
    }
  api-key: "abc123"
```

```yaml
# Use ConfigMap as volume
spec:
  volumes:
  - name: config
    configMap:
      name: app-config

  containers:
  - name: nginx
    volumeMounts:
    - name: config
      mountPath: /etc/nginx/conf.d
      readOnly: true
```

**Result**:
```
Container sees:
  /etc/nginx/conf.d/app.conf (contents from ConfigMap)
  /etc/nginx/conf.d/api-key (contents from ConfigMap)
```

**Select specific keys**:
```yaml
volumes:
- name: config
  configMap:
    name: app-config
    items:
    - key: app.conf
      path: nginx.conf  # ← Rename on mount
```

**Updates**: ConfigMap changes propagate to mounted volumes (eventually consistent, up to 60s delay).

### 2.4 secret (Sensitive Data)

**Use case**: Inject passwords, TLS certs, API keys (base64-encoded, not encrypted).

```yaml
# Create Secret
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=      # base64("admin")
  password: cGFzc3dvcmQ=  # base64("password")
```

```yaml
# Use Secret as volume
spec:
  volumes:
  - name: secrets
    secret:
      secretName: db-credentials

  containers:
  - name: app
    volumeMounts:
    - name: secrets
      mountPath: /secrets
      readOnly: true
```

**Result**:
```
Container sees:
  /secrets/username (contents: "admin", decoded)
  /secrets/password (contents: "password", decoded)
```

**Important**:
- Secrets are **not encrypted** at rest by default (enable encryption at rest in etcd)
- Secrets are **base64-encoded**, not encrypted (don't commit to git!)
- Consider external secret managers (Vault, AWS Secrets Manager, etc.)

### 2.5 downwardAPI (Pod Metadata)

**Use case**: Inject pod/container metadata as files.

```yaml
volumes:
- name: podinfo
  downwardAPI:
    items:
    - path: "labels"
      fieldRef:
        fieldPath: metadata.labels
    - path: "namespace"
      fieldRef:
        fieldPath: metadata.namespace
    - path: "cpu_limit"
      resourceFieldRef:
        containerName: app
        resource: limits.cpu
```

**Result**:
```
/podinfo/labels (file contents: app=frontend,tier=web)
/podinfo/namespace (file contents: production)
/podinfo/cpu_limit (file contents: 2)
```

**Use case**: App needs to know its own pod name, namespace, or labels.

### 2.6 persistentVolumeClaim (Persistent Storage)

**Use case**: Long-lived storage that survives pod deletion.

Covered in detail in Section 3.

---

## 3. Persistent Volumes

### Architecture Overview

```
┌──────────────────────────────────────────────┐
│ Pod                                          │
│  ┌────────────────────────────────────────┐ │
│  │ Container                              │ │
│  │  volumeMounts:                         │ │
│  │    - mountPath: /data                  │ │
│  └──────────────┬─────────────────────────┘ │
└─────────────────┼───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ PersistentVolumeClaim (PVC)                 │
│   "I need 10Gi of SSD storage"              │
└──────────────┬──────────────────────────────┘
               ↓ (binds to)
┌─────────────────────────────────────────────┐
│ PersistentVolume (PV)                       │
│   "Here's 10Gi of AWS EBS (gp3)"            │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│ Actual Storage (cloud disk, NFS, etc.)      │
└─────────────────────────────────────────────┘
```

**Why two objects (PV and PVC)**?
- **PV**: Cluster admin creates (represents actual storage)
- **PVC**: User requests storage (abstract request)
- **Decoupling**: Users don't need to know storage details

### 3.1 PersistentVolume (PV)

**Created by admins** (or dynamically provisioned). PV is PersistentVolume.

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-nfs-01
spec:
  capacity:
    storage: 10Gi
  accessModes:
  - ReadWriteMany  # ← Multiple pods can mount read-write
  persistentVolumeReclaimPolicy: Retain  # ← What happens when PVC is deleted
  nfs:
    server: nfs.example.com
    path: /exports/data
```

**Access Modes**:
```
ReadWriteOnce (RWO): Single node, read-write (most common for block storage)
ReadOnlyMany (ROX): Multiple nodes, read-only
ReadWriteMany (RWX): Multiple nodes, read-write (requires shared filesystem: NFS, CephFS)

Block storage (EBS, GCE PD): RWO only
File storage (NFS, CephFS, EFS): RWX supported
```

**Reclaim Policies**:
```
Retain: Keep PV after PVC deletion (manual cleanup)
Delete: Delete PV and underlying storage (default for dynamic provisioning)
Recycle: Deprecated (was: rm -rf /volume/*, reuse PV)
```

### 3.2 PersistentVolumeClaim (PVC)

**Created by users** (requests storage). PVC is PersistentVolumeClaim.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: fast-ssd  # ← Which StorageClass (optional)
```

**Binding**:
```
1. User creates PVC requesting 5Gi RWO
2. Kubernetes searches for PV matching:
   - Capacity >= 5Gi
   - AccessModes include RWO
   - StorageClassName matches (or both empty)
3. Binds PVC to PV (exclusive 1:1 binding)
4. PVC status: Bound
```

**Using PVC in pod**:
```yaml
spec:
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: my-pvc  # ← Reference PVC

  containers:
  - name: app
    volumeMounts:
    - name: data
      mountPath: /data
```

**Lifecycle**:
```
1. Admin creates PV (or StorageClass provisions dynamically)
2. User creates PVC
3. PVC binds to PV (status: Bound)
4. Pod uses PVC
5. Pod deleted → Volume still exists (data preserved)
6. PVC deleted → Reclaim policy determines PV fate
```

### 3.3 StorageClass (Dynamic Provisioning)

**Problem**: Admins manually creating PVs doesn't scale.

**Solution**: StorageClass automatically provisions PVs when PVC is created.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/aws-ebs  # ← CSI driver
parameters:
  type: gp3  # ← AWS EBS type
  iops: "3000"
  throughput: "125"
volumeBindingMode: WaitForFirstConsumer  # ← Delay provisioning until pod scheduled
reclaimPolicy: Delete
allowVolumeExpansion: true  # ← Can resize later
```

**Dynamic provisioning flow**:
```
1. User creates PVC with storageClassName: fast-ssd
2. No existing PV matches → StorageClass kicks in
3. Provisioner (aws-ebs CSI driver) creates cloud disk
4. Creates PV representing that disk
5. Binds PVC to new PV
6. Pod uses PVC (mounts cloud disk)
```

**Volume binding modes**:

**Immediate** (default):
```
1. PVC created
2. PV provisioned immediately
3. Later: Pod scheduled (might be on different AZ than volume!)
```

**WaitForFirstConsumer** (recommended):
```
1. PVC created, but not bound (status: Pending)
2. Pod referencing PVC is created
3. Scheduler chooses node
4. PV provisioned in same AZ as node
5. PVC bound to PV
6. Pod starts
```

**Common provisioners**:
```
AWS: ebs.csi.aws.com (EBS volumes)
GCP: pd.csi.storage.gke.io (Persistent Disks)
Azure: disk.csi.azure.com (Azure Disks)
On-prem: NFS, Ceph RBD, local-path
```

### 3.4 Volume Expansion

**Resize existing volume** (if StorageClass allows):

```yaml
# Original PVC
spec:
  resources:
    requests:
      storage: 10Gi

# Edit to expand
spec:
  resources:
    requests:
      storage: 50Gi  # ← Increase size
```

```bash
kubectl edit pvc my-pvc
# Change storage: 10Gi → 50Gi

# Kubernetes:
#   1. Resizes underlying cloud disk (EBS, GCE PD)
#   2. If pod is running, may require pod restart for filesystem resize
```

**Limitations**:
- Can only expand (not shrink)
- Requires `allowVolumeExpansion: true` in StorageClass
- Some volume types require pod restart

---

## 4. StatefulSet Storage Patterns

Recall from `02_pods_workloads.md`, StatefulSets provide stable storage via `volumeClaimTemplates`.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql
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

  volumeClaimTemplates:  # ← Creates PVC per pod
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 10Gi
```

**What happens**:
```
StatefulSet creates 3 pods:
  mysql-0 → PVC: data-mysql-0 → PV: pv-abc123 (10Gi disk)
  mysql-1 → PVC: data-mysql-1 → PV: pv-def456 (10Gi disk)
  mysql-2 → PVC: data-mysql-2 → PV: pv-ghi789 (10Gi disk)

If mysql-1 pod is deleted:
  → New mysql-1 pod created
  → Reattaches to SAME PVC (data-mysql-1)
  → Data preserved!

If StatefulSet is deleted:
  → Pods deleted
  → PVCs NOT deleted (manual cleanup required)
  → Prevents accidental data loss
```

**PVC lifecycle**:
```
StatefulSet created → PVCs created automatically
StatefulSet scaled up → New PVCs created for new pods
StatefulSet scaled down → PVCs kept (not deleted)
StatefulSet deleted → PVCs kept (not deleted)

Manual cleanup:
  kubectl delete pvc data-mysql-0 data-mysql-1 data-mysql-2
```

---

## 5. CSI (Container Storage Interface)

**Goal**: Standardize storage plugin interface (like CNI for networking). CSI is Container Storage Interface.

### Pre-CSI World

```
Kubernetes core had storage plugins for:
  - AWS EBS
  - GCE PD
  - Azure Disk
  - NFS
  - ... 20+ in-tree plugins

Problems:
  - Every storage vendor needed Kubernetes code changes
  - Slow release cycle for new features
  - Security/stability risks (vendor code in Kubernetes core)
```

### CSI Solution

```
┌─────────────────────────────────────────┐
│ Kubernetes (core)                       │
│   Knows: CSI interface only             │
└──────────────┬──────────────────────────┘
               ↓ (gRPC)
┌─────────────────────────────────────────┐
│ CSI Driver (vendor-provided)            │
│   Examples:                             │
│   - ebs.csi.aws.com                     │
│   - pd.csi.storage.gke.io               │
│   - rook-ceph                           │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ Actual Storage System                   │
│   (cloud API, Ceph cluster, etc.)       │
└─────────────────────────────────────────┘
```

**CSI operations**:
```
CreateVolume: Provision new storage
DeleteVolume: Delete storage
ControllerPublishVolume: Attach volume to node
NodeStageVolume: Mount volume to staging path
NodePublishVolume: Bind-mount to pod
VolumeSnapshot: Create snapshot (if supported)
```

**CSI driver components**:

1. **Controller Plugin** (Deployment/StatefulSet):
   - Runs once per cluster
   - Handles CreateVolume, DeleteVolume, Snapshot

2. **Node Plugin** (DaemonSet):
   - Runs on every node
   - Handles mount/unmount operations

**Example CSI driver** (AWS EBS):
```yaml
# Deployed as DaemonSet + Deployment
# DaemonSet (node plugin):
#   - Mounts EBS volumes to pods on this node
# Deployment (controller):
#   - Provisions/deletes EBS volumes via AWS API
```

**Migration from in-tree to CSI**:
```
Old (in-tree): kubernetes.io/aws-ebs
New (CSI): ebs.csi.aws.com

Kubernetes automatically migrates old volumes to CSI drivers
```

---

## 6. Volume Snapshots and Cloning

### Volume Snapshots

**Use case**: Backup volumes, pre-populate new volumes.

```yaml
# Create snapshot
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: db-snapshot-20240214
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: mysql-data
```

**Restore from snapshot**:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-data-restored
spec:
  dataSource:
    name: db-snapshot-20240214
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

**Workflow**:
```
1. Create VolumeSnapshot pointing to PVC
2. CSI driver creates cloud snapshot (EBS snapshot, GCE snapshot)
3. Create new PVC with dataSource: VolumeSnapshot
4. CSI driver creates volume from snapshot
5. New PVC bound to volume with snapshot data
```

### Volume Cloning

**Use case**: Clone existing PVC (without snapshot).

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cloned-data
spec:
  dataSource:
    name: original-data  # ← Source PVC
    kind: PersistentVolumeClaim
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

**Use cases**:
- Dev environments (clone prod data)
- Testing (clone database for isolated tests)
- Disaster recovery (quick restore)

---

## 7. Local Persistent Volumes

**Use case**: Use node's local disks (NVMe, SSD) for high performance.

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: local-pv-node1
spec:
  capacity:
    storage: 100Gi
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  local:
    path: /mnt/disks/ssd1  # ← Local path on node
  nodeAffinity:  # ← PV tied to specific node
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - node1
```

**Important constraints**:
- Pod **must** schedule on the node with the local volume
- If node fails, pod can't reschedule elsewhere (data loss risk)
- Use for performance-critical, replicated apps (Cassandra, etcd)

**Local volume provisioner** (automates local PV creation):
```
Scans nodes for local disks
  ↓
Creates PersistentVolume for each disk
  ↓
User creates PVC with storageClassName: local-storage
  ↓
PVC binds to local PV
  ↓
Pod scheduled on node with local PV (via nodeAffinity)
```

---

## Quick Reference

### Volume Types Comparison

| Type              | Lifetime        | Shared Across Pods | Use Case                          |
|-------------------|-----------------|---------------------|-----------------------------------|
| emptyDir          | Pod             | Yes (same pod)      | Temp files, cache                 |
| hostPath          | Node            | No (node-specific)  | Access node filesystem (DaemonSet)|
| configMap         | Cluster         | Yes                 | Configuration files               |
| secret            | Cluster         | Yes                 | Sensitive data (creds, certs)     |
| persistentVolumeClaim | Cluster   | Depends on PV       | Databases, user uploads           |
| nfs               | External        | Yes                 | Shared files across pods          |
| local             | Node            | No (node-local)     | High-performance, replicated apps |

### Access Modes

```
RWO (ReadWriteOnce): Single node, read-write (EBS, GCE PD)
ROX (ReadOnlyMany): Multiple nodes, read-only
RWX (ReadWriteMany): Multiple nodes, read-write (NFS, EFS, CephFS)
```

### Common Commands

```bash
# PersistentVolumes
kubectl get pv
kubectl describe pv pv-name

# PersistentVolumeClaims
kubectl get pvc
kubectl describe pvc my-pvc
kubectl delete pvc my-pvc  # Warning: May delete underlying storage!

# StorageClasses
kubectl get storageclass
kubectl describe storageclass fast-ssd

# Volume Snapshots
kubectl get volumesnapshot
kubectl get volumesnapshotcontent

# Expand PVC
kubectl edit pvc my-pvc  # Change storage: 10Gi → 50Gi

# Check PVC usage in pod
kubectl exec -it mypod -- df -h
```

### Troubleshooting

```bash
# PVC stuck in Pending
kubectl describe pvc my-pvc  # Check Events
  # Common issues:
  # - No PV matches (wrong size, access mode, storage class)
  # - StorageClass provisioner not installed
  # - Quota exceeded

# Pod stuck in Pending (volume attachment)
kubectl describe pod mypod
  # Common issues:
  # - Volume in different AZ than node
  # - Volume already attached to another node (RWO)
  # - CSI driver not running

# Check CSI driver pods
kubectl get pods -n kube-system | grep csi
```

---

## Summary

**Container storage** is ephemeral by default:
- **emptyDir**: Survives container restarts (pod lifetime)
- **PersistentVolumes**: Survive pod deletion (cluster lifetime)

**PersistentVolume architecture**:
- **PV**: Actual storage resource
- **PVC**: User's storage request
- **StorageClass**: Automatic PV provisioning

**Key concepts**:
- **Access modes**: RWO (single node), RWX (multiple nodes)
- **Reclaim policies**: Retain, Delete
- **Dynamic provisioning**: StorageClass automates PV creation
- **CSI**: Standard plugin interface for storage vendors

**StatefulSets**:
- `volumeClaimTemplates` create PVC per pod
- PVCs survive pod deletion (data preserved)

**Advanced features**:
- **Volume snapshots**: Backup and restore
- **Volume cloning**: Duplicate PVCs
- **Local volumes**: High-performance node-local storage

**Next**: Now that we understand all the core concepts, we'll explore production patterns and best practices.

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all container topics, see:
> **→ [Complete Container Learning Resources](../00_LEARNING_RESOURCES.md)** 📚

- **[Persistent Volume Examples](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)** - Official documentation with practical examples
- **[CSI Drivers List](https://kubernetes-csi.github.io/docs/drivers.html)** - Directory of Container Storage Interface drivers for various storage backends
- **[Local Path Provisioner](https://github.com/rancher/local-path-provisioner)** - Simple local storage provisioner for development clusters

---

## Related Documents

- **Previous**: `03_orchestration/04_scheduling_resources.md` - Resource management
- **Next**: `03_orchestration/06_production_patterns.md` - Production best practices
- **Foundation**: `01_fundamentals/02_union_filesystems.md` - Why container filesystems are ephemeral
- **Related**: `02_pods_workloads.md` - StatefulSet volumeClaimTemplates
