---
level: intermediate
estimated_time: 45 min
prerequisites:
  - 04_containers/01_fundamentals/02_union_filesystems.md
  - 04_containers/02_runtimes/01_runtime_landscape.md
next_recommended:
  - 04_containers/05_security/02_runtime_security.md
tags: [security, images, scanning, signing, vulnerabilities, supply-chain]
---

# Image Security: Scanning, Signing, and Trust

## Learning Objectives

After reading this document, you will understand:
- Container image vulnerabilities and attack surface
- Image scanning tools and how they work
- Image signing and verification (Sigstore, cosign)
- Trusted registries and admission control
- Base image selection best practices
- Multi-stage builds for minimal images
- Runtime image immutability

## Prerequisites

Before reading this, you should understand:
- Container image layers and union filesystems
- Container registries
- Basic security concepts

---

## 1. The Image Security Problem

### Images as Attack Surface

**Container image** = Application + Dependencies + OS libraries.

```
Example image (node:16):
  - Node.js 16 runtime
  - npm packages (1000+ dependencies)
  - Debian base OS (2000+ packages)
  - Total: ~3000+ software components

Each component could have vulnerabilities:
  - CVE-2023-XXXXX in openssl
  - CVE-2023-YYYYY in a npm package
  - CVE-2023-ZZZZZ in Debian libc
```

**Problem**: You're responsible for ALL vulnerabilities in your images.

### Common Vulnerabilities

**1. Base image vulnerabilities**:
```
FROM ubuntu:20.04
# Ubuntu 20.04 has 100+ known vulnerabilities if not updated

Better:
FROM ubuntu:20.04
RUN apt-get update && apt-get upgrade -y
```

**2. Application dependencies**:
```
package.json:
  "lodash": "4.17.11"  ← Has known vulnerabilities

Better:
  "lodash": "4.17.21"  ← Patched version
```

**3. Secrets in images**:
```dockerfile
# ✗ TERRIBLE:
ENV DATABASE_PASSWORD="secretpass123"

# Still bad (visible in layer history):
RUN echo "secret" > /app/secret.txt

# ✓ CORRECT: Use secrets management (not in image)
# Inject at runtime via Kubernetes Secrets
```

**4. Unnecessary packages**:
```dockerfile
# ✗ BAD: Full OS with compilers, shells, etc.
FROM ubuntu:20.04
RUN apt-get install -y gcc make curl wget git

# ✓ GOOD: Minimal base
FROM gcr.io/distroless/static:nonroot
COPY ./app /app
```

---

## 2. Image Scanning

### How Scanning Works

```
┌──────────────────────────────────────┐
│ Container Image                      │
│  ┌────────────────────────────────┐ │
│  │ Layer 1: Base OS               │ │
│  │   - ubuntu:20.04               │ │
│  │   - Packages: libc, openssl    │ │
│  ├────────────────────────────────┤ │
│  │ Layer 2: Application           │ │
│  │   - Node.js 16                 │ │
│  │   - npm packages               │ │
│  └────────────────────────────────┘ │
└────────────┬─────────────────────────┘
             ↓
    ┌────────────────────┐
    │ Image Scanner      │
    │ (Trivy/Clair/etc.) │
    └────────┬───────────┘
             ↓
    1. Extract layers
    2. Identify packages (dpkg, rpm, npm, pypi, etc.)
    3. Check against vulnerability database
       (National Vulnerability Database, vendor advisories)
    4. Report findings

┌──────────────────────────────────────┐
│ Scan Results                         │
│  CVE-2023-12345 (CRITICAL)           │
│    Package: openssl 1.1.1f           │
│    Fixed: openssl 1.1.1n             │
│                                      │
│  CVE-2023-67890 (HIGH)               │
│    Package: lodash 4.17.11           │
│    Fixed: lodash 4.17.21             │
└──────────────────────────────────────┘
```

### Scanning Tools

**1. Trivy** (most popular, open-source):
```bash
# Scan local image
trivy image nginx:1.21

# Scan image in registry
trivy image myregistry.io/myapp:v1.0

# Output formats
trivy image --format json nginx:1.21
trivy image --format sarif nginx:1.21  # For GitHub Security

# Severity filtering
trivy image --severity CRITICAL,HIGH nginx:1.21

# Ignore unfixed vulnerabilities
trivy image --ignore-unfixed nginx:1.21
```

**Output example**:
```
Total: 5 (CRITICAL: 2, HIGH: 3)

┌────────────┬─────────────────┬──────────┬─────────────┬───────────────┐
│  Library   │ Vulnerability   │ Severity │ Installed   │ Fixed Version │
├────────────┼─────────────────┼──────────┼─────────────┼───────────────┤
│ openssl    │ CVE-2023-12345  │ CRITICAL │ 1.1.1f      │ 1.1.1n        │
│ curl       │ CVE-2023-67890  │ HIGH     │ 7.68.0      │ 7.74.0        │
└────────────┴─────────────────┴──────────┴─────────────┴───────────────┘
```

**2. Clair** (CoreOS, used by Quay):
- Server-based (not CLI)
- Scans layers pushed to registry
- API-driven

**3. Grype** (Anchore):
```bash
grype myapp:latest
grype dir:.  # Scan local directory
```

**4. Snyk**:
```bash
snyk container test nginx:1.21
snyk container monitor nginx:1.21  # Continuous monitoring
```

### CI/CD Integration

**GitHub Actions example**:
```yaml
name: Scan Docker Image
on: [push]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Build image
      run: docker build -t myapp:${{ github.sha }} .

    - name: Scan image
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: myapp:${{ github.sha }}
        severity: 'CRITICAL,HIGH'
        exit-code: 1  # Fail pipeline if vulnerabilities found
```

**GitLab CI example**:
```yaml
container_scanning:
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - trivy image --exit-code 1 --severity CRITICAL,HIGH $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
```

---

## 3. Image Signing and Verification

### Why Sign Images?

**Problem without signing**:
```
Attacker compromises registry
  → Replaces myapp:v1.0 with malicious image
  → Kubernetes pulls malicious image
  → Cluster compromised

How do you know the image is authentic?
```

**Solution**: Cryptographic signatures.

```
Build time:
  1. Build image
  2. Sign image with private key
  3. Push image + signature to registry

Deploy time:
  1. Pull image from registry
  2. Verify signature with public key
  3. Only run if signature valid
```

### Sigstore and cosign

**Sigstore**: Keyless signing (no long-lived private keys).

**cosign**: CLI tool for signing/verifying.

**Install cosign**:
```bash
# Linux
wget https://github.com/sigstore/cosign/releases/download/v2.0.0/cosign-linux-amd64
chmod +x cosign-linux-amd64
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
```

**Sign an image** (keyless):
```bash
# Build image
docker build -t myregistry.io/myapp:v1.0 .
docker push myregistry.io/myapp:v1.0

# Sign (opens browser for OIDC auth)
cosign sign myregistry.io/myapp:v1.0

# Signature stored in registry at:
# myregistry.io/myapp:sha256-<hash>.sig
```

**Verify signature**:
```bash
cosign verify \
  --certificate-identity=user@example.com \
  --certificate-oidc-issuer=https://github.com/login/oauth \
  myregistry.io/myapp:v1.0

# Output if valid:
# Verification successful!

# Output if invalid/missing:
# Error: no matching signatures
```

**Sign with key pair** (traditional):
```bash
# Generate key pair
cosign generate-key-pair

# Sign
cosign sign --key cosign.key myregistry.io/myapp:v1.0

# Verify
cosign verify --key cosign.pub myregistry.io/myapp:v1.0
```

### Attestations (SBOM, provenance)

**SBOM (Software Bill of Materials)**: List of all components in image.

```bash
# Generate SBOM
syft myregistry.io/myapp:v1.0 -o json > sbom.json

# Attach SBOM to image
cosign attest --predicate sbom.json --key cosign.key myregistry.io/myapp:v1.0

# Verify and retrieve SBOM
cosign verify-attestation --key cosign.pub myregistry.io/myapp:v1.0
```

**Provenance**: How image was built (GitHub Actions run, commit hash, etc.).

```bash
# GitHub Actions generates provenance automatically
# Attach to image
cosign attest --predicate provenance.json --key cosign.key myregistry.io/myapp:v1.0
```

---

## 4. Admission Control

### Enforcing Image Policies

**Problem**: Prevent unsigned/vulnerable images from running.

**Solution**: Admission webhooks (validate before pod creation).

### Policy Enforcement Tools

**1. Kyverno** (Kubernetes-native):
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-image-signature
spec:
  validationFailureAction: enforce  # Block unsigned images
  rules:
  - name: verify-signature
    match:
      any:
      - resources:
          kinds:
          - Pod
    verifyImages:
    - imageReferences:
      - "*"  # All images
      attestors:
      - count: 1
        entries:
        - keys:
            publicKeys: |-
              -----BEGIN PUBLIC KEY-----
              MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
              -----END PUBLIC KEY-----
```

**Effect**:
```
User tries: kubectl run test --image=unsigned:latest
  → Kyverno intercepts
  → Verifies signature
  → Signature missing/invalid
  → Pod creation DENIED

User tries: kubectl run test --image=signed:v1.0
  → Kyverno intercepts
  → Verifies signature
  → Signature valid
  → Pod creation ALLOWED
```

**2. OPA Gatekeeper** (more flexible, Rego language):
```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8srequiredsignature
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredSignature
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredsignature

        violation[{"msg": msg}] {
          # Check if image is from allowed registry
          container := input.review.object.spec.containers[_]
          not startswith(container.image, "myregistry.io/")
          msg := sprintf("Image must be from myregistry.io, got: %v", [container.image])
        }
```

**3. Admission controller for vulnerability scanning**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: block-critical-vulnerabilities
spec:
  validationFailureAction: enforce
  rules:
  - name: scan-image
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Image has CRITICAL vulnerabilities"
      pattern:
        spec:
          containers:
          - image: "*"
            # This would call external scanner (Trivy, etc.)
            # Real implementation needs webhook
```

---

## 5. Base Image Best Practices

### Choosing Base Images

**Size and security comparison**:

| Base Image          | Size  | Packages | CVEs  | Use Case           |
|---------------------|-------|----------|-------|--------------------|
| ubuntu:20.04        | 72 MB | ~2000    | ~100  | Development        |
| alpine:3.17         | 7 MB  | ~200     | ~10   | General apps       |
| distroless/static   | 2 MB  | ~20      | 0-2   | Go/Rust apps       |
| scratch             | 0 MB  | 0        | 0     | Static binaries    |

**1. scratch** (empty image):
```dockerfile
FROM scratch
COPY myapp /myapp
ENTRYPOINT ["/myapp"]

# No shell, no package manager, no debugging tools
# Perfect for static Go binaries
```

**2. distroless** (minimal, no shell):
```dockerfile
FROM golang:1.20 AS builder
WORKDIR /app
COPY . .
RUN go build -o myapp

FROM gcr.io/distroless/static:nonroot
COPY --from=builder /app/myapp /app
ENTRYPOINT ["/app"]

# Contains: glibc, CA certs, timezone data
# Missing: shell, package manager, most utilities
```

**3. Alpine** (small, musl libc):
```dockerfile
FROM alpine:3.17
RUN apk add --no-cache ca-certificates
COPY myapp /app
ENTRYPOINT ["/app"]

# 7 MB, apk package manager
# Good for most apps
```

**Trade-offs**:
```
scratch/distroless:
  ✓ Minimal attack surface
  ✓ No vulnerabilities
  ✗ Hard to debug (no shell)
  ✗ Can't install packages at runtime

Alpine:
  ✓ Small size
  ✓ Has shell (debugging easier)
  ✗ musl libc (not glibc, compatibility issues)
  ✗ More packages = more vulnerabilities

Ubuntu/Debian:
  ✓ Easy to use
  ✓ glibc (compatible)
  ✗ Large size
  ✗ Many vulnerabilities
```

### Multi-Stage Builds

**Goal**: Build image has tools, runtime image is minimal.

```dockerfile
# Stage 1: Build
FROM golang:1.20 AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o myapp

# Stage 2: Runtime
FROM gcr.io/distroless/static:nonroot
COPY --from=builder /app/myapp /app
ENTRYPOINT ["/app"]

# Result:
#   Builder stage: 800 MB (Go compiler, tools)
#   Final image: 2 MB (just binary)
```

**Benefits**:
- Smaller image (faster downloads, less storage)
- Fewer vulnerabilities (no build tools in production)
- Lower attack surface

---

## 6. Runtime Image Immutability

### Read-Only Root Filesystem

**Principle**: Prevent attackers from modifying container filesystem.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  containers:
  - name: app
    image: myapp:1.0
    securityContext:
      readOnlyRootFilesystem: true  # ← Prevent writes

    # App needs /tmp for temporary files
    volumeMounts:
    - name: tmp
      mountPath: /tmp

  volumes:
  - name: tmp
    emptyDir: {}
```

**Effect**:
```
Attacker compromises container
  → Tries: echo "malware" > /usr/bin/malware
  → Error: read-only filesystem
  → Can't persist malware

Legitimate writes to /tmp still work (mounted emptyDir)
```

### Immutable Image Tags

**Anti-pattern**: Using `latest` tag.
```yaml
# ✗ BAD:
image: myapp:latest

Problems:
  - What version is "latest"? Unknown
  - "latest" changes (no reproducibility)
  - Can't rollback (which "latest" was it?)
```

**Best practice**: Use digest or specific version.
```yaml
# ✓ GOOD:
image: myapp:v1.2.3

# ✓ BETTER: Use digest (immutable)
image: myapp@sha256:a1b2c3d4e5f6...
```

**Combining tag + digest**:
```yaml
image: myapp:v1.2.3@sha256:a1b2c3d4e5f6...
# Human-readable tag + immutable digest
```

**Automatic digest pinning** (Kyverno):
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-digest
spec:
  rules:
  - name: resolve-digest
    match:
      resources:
        kinds:
        - Pod
    mutate:
      foreach:
      - list: "request.object.spec.containers"
        patchStrategicMerge:
          spec:
            containers:
            - image: "{{ element.image }}@{{ lookup.image.digest }}"
```

---

## Quick Reference

### Image Security Checklist

```
✓ Scan images for vulnerabilities (Trivy, Grype)
✓ Use minimal base images (distroless, Alpine, scratch)
✓ Multi-stage builds (separate build and runtime)
✓ Sign images (cosign)
✓ Verify signatures (admission control)
✓ Pin image versions (no :latest, use digests)
✓ Read-only root filesystem (securityContext)
✓ No secrets in images (use Kubernetes Secrets)
✓ Regular base image updates (rebuild monthly)
```

### Common Commands

```bash
# Trivy scanning
trivy image --severity CRITICAL,HIGH myapp:v1.0
trivy image --ignore-unfixed myapp:v1.0
trivy image --format json myapp:v1.0

# cosign signing
cosign generate-key-pair
cosign sign --key cosign.key myapp:v1.0
cosign verify --key cosign.pub myapp:v1.0

# Generate SBOM
syft myapp:v1.0 -o json
cosign attest --predicate sbom.json --key cosign.key myapp:v1.0

# Get image digest
docker inspect myapp:v1.0 --format='{{.RepoDigests}}'

# Pull by digest
docker pull myapp@sha256:a1b2c3d4...
```

---

## Summary

**Container images** have a large attack surface:
- Base OS packages (100s-1000s)
- Application dependencies (100s-1000s)
- Potential for embedded secrets

**Image scanning** detects vulnerabilities:
- Tools: Trivy, Grype, Snyk, Clair
- Integrate into CI/CD (fail on CRITICAL/HIGH)
- Scan registries continuously

**Image signing** proves authenticity:
- cosign for signing/verification
- Sigstore for keyless signing
- SBOM and provenance attestations

**Admission control** enforces policies:
- Kyverno, OPA Gatekeeper
- Block unsigned images
- Block images with vulnerabilities

**Best practices**:
- Minimal base images (distroless, Alpine, scratch)
- Multi-stage builds (separate build and runtime)
- Read-only root filesystem
- Pin image versions (digests, not :latest)
- No secrets in images

**Next**: Now that images are secure, we'll cover **runtime security**: what happens when containers are actually running.

---

## Related Documents

- **Previous**: `04_networking/05_network_policies_advanced.md` - Network isolation
- **Next**: `05_security/02_runtime_security.md` - Runtime security
- **Foundation**: `01_fundamentals/02_union_filesystems.md` - How image layers work
- **Related**: `03_orchestration/06_production_patterns.md` - Security hardening
