---
level: intermediate
estimated_time: 45 min
prerequisites:
  - 04_containers/05_security/02_runtime_security.md
  - 04_containers/03_orchestration/01_kubernetes_architecture.md
next_recommended:
  - 04_containers/05_security/04_supply_chain.md
tags: [security, pod-security-standards, rbac, service-accounts, admission]
---

# Pod Security: Standards, RBAC, and Access Control

## Learning Objectives

After reading this document, you will understand:
- Pod Security Standards (PSS: Privileged, Baseline, Restricted)
- Pod Security Admission (PSA) controller
- RBAC (Role-Based Access Control) fundamentals
- Service accounts and pod identity
- Admission controllers and policy enforcement
- Security best practices for multi-tenant clusters

## Prerequisites

Before reading this, you should understand:
- Runtime security concepts (seccomp, capabilities)
- Kubernetes architecture and API server
- Basic security concepts

---

## 1. Pod Security Standards

### The Three Levels

**Pod Security Standards** define three policies from permissive to restrictive:

**1. Privileged** - Unrestricted (allow everything)
**2. Baseline** - Minimally restrictive (blocks known privilege escalations)
**3. Restricted** - Heavily restricted (hardened, defense-in-depth)

### Baseline Policy

**Blocks common privilege escalations**:

```yaml
# ✗ BLOCKED by Baseline:
spec:
  hostNetwork: true           # Can't use host network
  hostPID: true              # Can't use host PID namespace
  hostIPC: true              # Can't use host IPC namespace

  containers:
  - securityContext:
      privileged: true        # Can't run privileged

  volumes:
  - hostPath:                 # Can't mount host paths
      path: /
```

**Baseline allows** (but Restricted blocks):
```yaml
# ✓ ALLOWED by Baseline:
spec:
  securityContext:
    runAsUser: 0              # Can run as root

  containers:
  - securityContext:
      readOnlyRootFilesystem: false  # Can have writable filesystem
      allowPrivilegeEscalation: true # Can escalate privileges
```

### Restricted Policy

**Requires defense-in-depth hardening**:

```yaml
# ✓ REQUIRED by Restricted:
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pod
spec:
  securityContext:
    runAsNonRoot: true        # MUST NOT run as root
    seccompProfile:
      type: RuntimeDefault    # MUST have seccomp

  containers:
  - name: app
    image: myapp:1.0
    securityContext:
      allowPrivilegeEscalation: false  # MUST be false
      runAsNonRoot: true                # MUST be true
      capabilities:
        drop:
        - ALL                            # MUST drop all
      seccompProfile:
        type: RuntimeDefault             # MUST have seccomp
```

**Restricted blocks**:
- Running as root
- Privilege escalation
- Any capabilities (must drop ALL)
- Writable filesystem (should be read-only)
- Host namespaces, paths, ports

### Pod Security Admission (PSA)

**Enforces Pod Security Standards** (built-in since Kubernetes 1.23).

**Enable per namespace**:
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

**Three modes**:
- **enforce**: Reject pods that violate policy
- **audit**: Allow but log violations
- **warn**: Allow but show warning to user

**Example**:
```bash
# Try to create privileged pod in restricted namespace
kubectl run test --image=nginx --privileged -n production

# Error:
# pods "test" is forbidden: violates PodSecurity "restricted:latest":
# privileged (container "test" must not set securityContext.privileged=true)
```

**Namespace exemptions**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: kube-system
  labels:
    pod-security.kubernetes.io/enforce: privileged  # Allow privileged (system pods)
```

**Global configuration** (admission controller):
```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: AdmissionConfiguration
plugins:
- name: PodSecurity
  configuration:
    apiVersion: pod-security.admission.config.k8s.io/v1
    kind: PodSecurityConfiguration
    defaults:
      enforce: "baseline"
      audit: "restricted"
      warn: "restricted"
    exemptions:
      usernames: []
      runtimeClasses: []
      namespaces: ["kube-system"]
```

---

## 2. RBAC (Role-Based Access Control)

### RBAC Model

```
┌──────────┐     ┌──────────────┐     ┌──────────┐
│ Subject  │ →   │ RoleBinding  │ →   │   Role   │
│ (User/SA)│     │              │     │ (Perms)  │
└──────────┘     └──────────────┘     └──────────┘
     ↓                                      ↓
  Who wants                           What can they
  to do something?                    do?
```

**Four RBAC objects**:
1. **Role**: Permissions within a namespace
2. **ClusterRole**: Permissions cluster-wide
3. **RoleBinding**: Binds Role to subjects
4. **ClusterRoleBinding**: Binds ClusterRole to subjects

### Roles

**Role** (namespace-scoped):
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: production
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
```

**ClusterRole** (cluster-wide):
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list"]
```

**Common verbs**:
- `get`: Read single resource
- `list`: List all resources
- `watch`: Watch for changes
- `create`: Create new resource
- `update`: Modify resource
- `patch`: Partial update
- `delete`: Delete resource
- `*`: All verbs (dangerous!)

### RoleBindings

**RoleBinding** (grant Role to user):
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: production
subjects:
- kind: User
  name: alice
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

**Effect**: User `alice` can read pods in `production` namespace.

**ClusterRoleBinding** (cluster-wide):
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-secrets-global
subjects:
- kind: Group
  name: secret-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

### Common Patterns

**1. Developer role** (full access to namespace):
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer
  namespace: dev
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["*"]
  verbs: ["*"]
```

**2. Read-only role**:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: viewer
  namespace: production
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
```

**3. CI/CD role** (deploy only):
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployer
  namespace: production
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["services"]
  verbs: ["get", "list", "create", "update", "patch"]
```

**4. Logs viewer**:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: log-reader
  namespace: production
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list"]
```

---

## 3. Service Accounts

### What are Service Accounts?

**Service Account** = Identity for pods (like user accounts for humans).

**Every pod has a service account**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  serviceAccountName: myapp-sa  # Which identity this pod has
  containers:
  - name: app
    image: myapp:1.0
```

**Default service account** (if not specified):
```
namespace: default
serviceAccount: default

Every namespace has a "default" service account
```

### Creating Service Accounts

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: production
```

**Grant permissions** (via RoleBinding):
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: myapp-sa-binding
  namespace: production
subjects:
- kind: ServiceAccount
  name: myapp-sa
  namespace: production
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

**Use in pod**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  namespace: production
spec:
  serviceAccountName: myapp-sa
  containers:
  - name: app
    image: myapp:1.0
```

### How Pods Use Service Accounts

**Kubernetes mounts token automatically**:
```
Inside pod:
  /var/run/secrets/kubernetes.io/serviceaccount/
    token       ← JWT token for authentication
    ca.crt      ← CA certificate
    namespace   ← Current namespace
```

**Application code** (calling Kubernetes API):
```python
import requests

# Read token
with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as f:
    token = f.read()

# Call Kubernetes API
headers = {'Authorization': f'Bearer {token}'}
response = requests.get(
    'https://kubernetes.default.svc/api/v1/namespaces/production/pods',
    headers=headers,
    verify='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
)

# If myapp-sa has permissions, this succeeds
# Otherwise: 403 Forbidden
```

### Disabling Auto-Mount

**Security best practice**: Don't mount tokens if app doesn't need them.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  automountServiceAccountToken: false  # Don't mount token
  containers:
  - name: app
    image: myapp:1.0
```

**Or disable for service account**:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
automountServiceAccountToken: false
```

---

## 4. Admission Controllers

### What are Admission Controllers?

**Admission controllers** intercept requests to Kubernetes API before persistence.

```
kubectl create pod
    ↓
API Server receives request
    ↓
Authentication (who are you?)
    ↓
Authorization (can you do this?) ← RBAC
    ↓
Admission Control (is this allowed?)  ← Admission Controllers
    ↓
    ├─ MutatingAdmissionWebhook (modify request)
    └─ ValidatingAdmissionWebhook (accept/reject)
    ↓
Persist to etcd
```

### Built-in Admission Controllers

**Common built-in controllers**:
- **PodSecurity**: Enforce Pod Security Standards
- **NamespaceLifecycle**: Prevent creation in terminating namespaces
- **LimitRanger**: Enforce LimitRange constraints
- **ResourceQuota**: Enforce ResourceQuota constraints
- **ServiceAccount**: Auto-add default SA if not specified

**Enable admission controllers**:
```bash
kube-apiserver \
  --enable-admission-plugins=PodSecurity,NamespaceLifecycle,LimitRanger,ResourceQuota
```

### Admission Webhooks

**External admission controllers** (custom logic).

**Mutating webhook** (modify resources):
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: pod-injector
webhooks:
- name: injector.example.com
  clientConfig:
    service:
      name: injector-service
      namespace: default
      path: /mutate
  rules:
  - operations: ["CREATE"]
    apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
```

**Example**: Inject sidecar container into every pod.

**Validating webhook** (reject invalid resources):
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: image-policy
webhooks:
- name: validate.images.example.com
  clientConfig:
    service:
      name: image-validator
      namespace: default
      path: /validate
  rules:
  - operations: ["CREATE", "UPDATE"]
    apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
```

**Example**: Reject pods with unsigned images.

---

## 5. Multi-Tenancy Patterns

### Namespace Isolation

**Hard multi-tenancy** (strong isolation):
```
Tenant A → Namespace: tenant-a
  - RBAC: Users can only access tenant-a
  - NetworkPolicy: Can't access other namespaces
  - ResourceQuota: Limited resources
  - PodSecurity: Restricted policy enforced

Tenant B → Namespace: tenant-b
  - Same isolation
```

**RBAC setup**:
```yaml
# Tenant A users can only access tenant-a namespace
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-admin
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-users
roleRef:
  kind: ClusterRole
  name: admin  # Pre-defined ClusterRole

---
# Prevent cross-namespace access
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: no-cross-namespace
rules: []  # No cluster-wide permissions

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tenant-a-no-cluster
subjects:
- kind: Group
  name: tenant-a-users
roleRef:
  kind: ClusterRole
  name: no-cross-namespace
```

**NetworkPolicy isolation** (covered in networking docs):
```yaml
# Default deny all (per namespace)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

**ResourceQuota**:
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-a-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "50"
    requests.memory: "100Gi"
    pods: "100"
```

### Hierarchical Namespaces

**HNC (Hierarchical Namespace Controller)** allows parent-child namespaces:

```
org-a (parent)
  ├─ org-a-dev (child, inherits policies)
  ├─ org-a-staging (child)
  └─ org-a-prod (child)
```

**Benefits**:
- Policies defined once in parent, inherited by children
- Resource quotas can be distributed
- Easier management for large organizations

---

## Quick Reference

### Pod Security Standards

| Level      | Host Namespaces | Privileged | Root | Capabilities | seccomp        |
|------------|-----------------|------------|------|--------------|----------------|
| Privileged | ✓ Allowed       | ✓ Allowed  | ✓    | ✓ Any        | ✓ Any          |
| Baseline   | ✗ Blocked       | ✗ Blocked  | ✓    | ✓ Some       | ✓ Any          |
| Restricted | ✗ Blocked       | ✗ Blocked  | ✗    | ✗ Drop ALL   | ✓ RuntimeDefault|

### RBAC Quick Commands

```bash
# Create service account
kubectl create serviceaccount myapp-sa -n production

# Create role
kubectl create role pod-reader --verb=get,list --resource=pods -n production

# Create rolebinding
kubectl create rolebinding myapp-binding \
  --role=pod-reader \
  --serviceaccount=production:myapp-sa \
  -n production

# Check permissions
kubectl auth can-i list pods --as=system:serviceaccount:production:myapp-sa -n production

# Get effective permissions
kubectl describe rolebinding myapp-binding -n production
```

### Common RBAC Patterns

```yaml
# Admin (full access to namespace)
kind: RoleBinding
roleRef:
  kind: ClusterRole
  name: admin

# Edit (create/update resources, can't modify RBAC)
kind: RoleBinding
roleRef:
  kind: ClusterRole
  name: edit

# View (read-only)
kind: RoleBinding
roleRef:
  kind: ClusterRole
  name: view
```

---

## Summary

**Pod Security Standards (PSS)** provide three policy levels:
- Privileged: Unrestricted (development only)
- Baseline: Blocks obvious escalations
- Restricted: Defense-in-depth hardening (production)

**Pod Security Admission (PSA)** enforces standards:
- Per-namespace labels
- Three modes: enforce, audit, warn
- Built-in since Kubernetes 1.23

**RBAC** controls who can do what:
- Roles define permissions
- RoleBindings grant permissions to users/groups/service accounts
- Namespace-scoped (Role) or cluster-wide (ClusterRole)

**Service Accounts** provide pod identity:
- Every pod has a service account
- Token mounted automatically
- Used to call Kubernetes API with permissions

**Admission Controllers** enforce policies:
- Intercept requests before persistence
- Built-in (PodSecurity, LimitRanger, ResourceQuota)
- Webhooks for custom policies

**Multi-tenancy** uses:
- Namespace isolation
- RBAC for access control
- NetworkPolicy for network isolation
- ResourceQuota for resource limits

**Next**: We've covered runtime and pod security. Now we'll explore **supply chain security**: SBOM, SLSA, and provenance.

---

## Related Documents

- **Previous**: `05_security/02_runtime_security.md` - Runtime security
- **Next**: `05_security/04_supply_chain.md` - Supply chain security
- **Foundation**: `03_orchestration/01_kubernetes_architecture.md` - API server and RBAC
- **Related**: `03_orchestration/06_production_patterns.md` - Pod Security Standards enforcement
