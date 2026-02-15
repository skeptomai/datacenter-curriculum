---
level: specialized
estimated_time: 50 min
prerequisites:
  - 04_containers/05_security/01_image_security.md
  - 04_containers/05_security/03_pod_security.md
next_recommended:
  - quick_start_containers.md
tags: [security, supply-chain, sbom, slsa, sigstore, provenance, attestation]
---

# Supply Chain Security: SBOM, SLSA, and Provenance

## Learning Objectives

After reading this document, you will understand:
- Supply chain attack vectors and risks
- SBOM (Software Bill of Materials) generation and usage
- SLSA framework for build provenance
- Sigstore ecosystem (cosign, Fulcio, Rekor)
- In-toto attestations and policies
- Policy enforcement with OPA/Gatekeeper
- End-to-end supply chain security

## Prerequisites

Before reading this, you should understand:
- Image security and signing basics
- Container registries and image distribution
- Admission controllers and policy enforcement

---

## 1. Supply Chain Attack Vectors

### The Software Supply Chain

```
┌─────────────────────────────────────────────────┐
│ Developer writes code                            │
└────────────┬────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────┐
│ Dependencies fetched (npm, pip, maven)          │
│ ← ATTACK: Compromised package                   │
└────────────┬────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────┐
│ CI/CD builds container image                    │
│ ← ATTACK: Compromised build environment         │
└────────────┬────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────┐
│ Image pushed to registry                        │
│ ← ATTACK: Compromised registry                  │
└────────────┬────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────┐
│ Kubernetes pulls and runs image                 │
│ ← ATTACK: MITM, unsigned image                  │
└─────────────────────────────────────────────────┘
```

### Real-World Attacks

**1. SolarWinds (2020)**:
- Build system compromised
- Malicious code injected into builds
- Affected 18,000+ organizations

**2. codecov (2021)**:
- Docker image compromised
- Exfiltrated environment variables (secrets)
- Affected hundreds of companies

**3. ua-parser-js (2021)**:
- npm package compromised
- Cryptocurrency miner injected
- 8+ million downloads per week

### Defense Strategy

**Zero-trust supply chain**:
1. **Know what's in your images** (SBOM)
2. **Verify build integrity** (SLSA provenance)
3. **Sign and verify** (Sigstore)
4. **Enforce policies** (admission control)
5. **Monitor runtime** (detect anomalies)

---

## 2. SBOM (Software Bill of Materials)

### What is an SBOM?

**SBOM** = Comprehensive list of all software components.

```
Container image: myapp:v1.0

SBOM:
  - alpine:3.17 (base image)
    - musl-libc 1.2.3
    - busybox 1.35.0
    - ca-certificates 20230506
  - Node.js 18.16.0
  - npm packages (1,234 total):
    - express 4.18.2
      - accepts 1.3.8
      - body-parser 1.20.1
      - ...
```

**Why SBOMs matter**:
```
Vulnerability discovered in log4j 2.15.0

Without SBOM:
  "Do we use log4j?" → Search code, guess
  Takes hours/days

With SBOM:
  $ grep "log4j" sbom.json
  "log4j-core": "2.15.0"  ← FOUND! Vulnerable
  Action: Patch immediately
```

### Generating SBOMs

**Syft** (Anchore's SBOM tool):
```bash
# Generate SBOM
syft myapp:v1.0 -o json > sbom.json

# Different formats
syft myapp:v1.0 -o cyclonedx-json > sbom-cyclonedx.json  # CycloneDX
syft myapp:v1.0 -o spdx-json > sbom-spdx.json            # SPDX
syft myapp:v1.0 -o table                                 # Human-readable
```

**Output (SPDX JSON)**:
```json
{
  "spdxVersion": "SPDX-2.3",
  "dataLicense": "CC0-1.0",
  "SPDXID": "SPDXRef-DOCUMENT",
  "name": "myapp:v1.0",
  "packages": [
    {
      "SPDXID": "SPDXRef-Package-alpine",
      "name": "alpine",
      "versionInfo": "3.17",
      "downloadLocation": "NOASSERTION",
      "filesAnalyzed": false
    },
    {
      "SPDXID": "SPDXRef-Package-express",
      "name": "express",
      "versionInfo": "4.18.2",
      "externalRefs": [
        {
          "referenceCategory": "PACKAGE-MANAGER",
          "referenceType": "purl",
          "referenceLocator": "pkg:npm/express@4.18.2"
        }
      ]
    }
  ]
}
```

### SBOM in CI/CD

**GitHub Actions**:
```yaml
name: Generate SBOM
on: [push]

jobs:
  sbom:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Build image
      run: docker build -t myapp:${{ github.sha }} .

    - name: Generate SBOM
      uses: anchore/sbom-action@v0
      with:
        image: myapp:${{ github.sha }}
        format: spdx-json
        output-file: sbom.spdx.json

    - name: Upload SBOM
      uses: actions/upload-artifact@v3
      with:
        name: sbom
        path: sbom.spdx.json

    - name: Attach SBOM to image
      run: |
        cosign attach sbom --sbom sbom.spdx.json myapp:${{ github.sha }}
```

### Using SBOMs

**Query for vulnerabilities**:
```bash
# Generate SBOM
syft myapp:v1.0 -o json > sbom.json

# Scan SBOM for vulnerabilities
grype sbom:sbom.json

# Output
NAME       INSTALLED  VULNERABILITY   SEVERITY
log4j-core 2.15.0     CVE-2021-45046  CRITICAL
express    4.17.0     CVE-2022-24999  HIGH
```

**Check for specific component**:
```bash
# Is this image affected by log4j?
jq '.artifacts[] | select(.name == "log4j-core")' sbom.json

# Output (if present):
{
  "name": "log4j-core",
  "version": "2.15.0",
  "type": "java-archive"
}
```

---

## 3. SLSA (Supply-chain Levels for Software Artifacts)

### SLSA Framework

**SLSA** (pronounced "salsa"): Framework for ensuring build integrity.

**Four levels** (L0 = nothing, L4 = maximum):

| Level | Requirements                                    |
|-------|-------------------------------------------------|
| L1    | Build process documented                        |
| L2    | Version control + hosted build service          |
| L3    | Hardened build platform, provenance available   |
| L4    | Two-party review + hermetic, reproducible builds|

### SLSA Provenance

**Provenance** = Metadata about how software was built.

```json
{
  "_type": "https://in-toto.io/Statement/v0.1",
  "subject": [
    {
      "name": "myregistry.io/myapp",
      "digest": {
        "sha256": "a1b2c3d4..."
      }
    }
  ],
  "predicateType": "https://slsa.dev/provenance/v0.2",
  "predicate": {
    "builder": {
      "id": "https://github.com/Attestations/GitHubActionsWorkflow@v1"
    },
    "buildType": "https://github.com/Attestations/GitHubActionsWorkflow@v1",
    "invocation": {
      "configSource": {
        "uri": "https://github.com/myorg/myrepo",
        "digest": {"sha1": "abc123..."},
        "entryPoint": ".github/workflows/build.yml"
      }
    },
    "metadata": {
      "buildStartedOn": "2024-02-14T10:00:00Z",
      "buildFinishedOn": "2024-02-14T10:15:00Z"
    },
    "materials": [
      {
        "uri": "git+https://github.com/myorg/myrepo",
        "digest": {"sha1": "def456..."}
      },
      {
        "uri": "pkg:docker/node@18.16.0",
        "digest": {"sha256": "ghi789..."}
      }
    ]
  }
}
```

**What provenance tells you**:
- **Who** built it (GitHub Actions)
- **When** it was built (timestamp)
- **From what source** (git commit hash)
- **What inputs** (base images, dependencies)

### Generating Provenance

**GitHub Actions** (automatic with SLSA workflow):
```yaml
name: Build with SLSA
on: [push]

permissions:
  id-token: write   # Required for OIDC
  contents: read
  packages: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Build image
      run: docker build -t myapp:${{ github.sha }} .

    - name: Generate provenance
      uses: slsa-framework/slsa-github-generator@v1.9.0
      with:
        image: myapp:${{ github.sha }}

    - name: Sign with cosign
      run: |
        cosign sign myapp:${{ github.sha }} --yes
        cosign attest --predicate provenance.json --type slsaprovenance myapp:${{ github.sha }}
```

### Verifying Provenance

```bash
# Verify provenance exists
cosign verify-attestation \
  --type slsaprovenance \
  --certificate-identity-regexp='https://github.com/myorg/myrepo' \
  --certificate-oidc-issuer='https://token.actions.githubusercontent.com' \
  myapp:v1.0

# Extract and inspect
cosign verify-attestation myapp:v1.0 | jq '.payload | @base64d | fromjson'

# Verify it was built from specific commit
cosign verify-attestation myapp:v1.0 | \
  jq -r '.payload | @base64d | fromjson | .predicate.materials[0].digest.sha1'
# Output: abc123...  (git commit)
```

---

## 4. Sigstore Ecosystem

### Sigstore Components

```
┌─────────────────────────────────────────────────┐
│ Fulcio (Certificate Authority)                   │
│ - Issues short-lived certificates               │
│ - Uses OIDC for identity (GitHub, Google, etc.) │
└────────────┬────────────────────────────────────┘
             ↓ Issues cert
┌─────────────────────────────────────────────────┐
│ cosign (CLI tool)                                │
│ - Signs images/artifacts                        │
│ - Attaches signatures to registry               │
└────────────┬────────────────────────────────────┘
             ↓ Writes to
┌─────────────────────────────────────────────────┐
│ Rekor (Transparency Log)                         │
│ - Immutable, append-only log                    │
│ - Publicly auditable                            │
└─────────────────────────────────────────────────┘
```

### Keyless Signing with Fulcio

**Traditional signing**:
```
Problem: Long-lived private keys
  - Must be stored securely
  - Can be stolen
  - Hard to rotate
```

**Keyless signing (Fulcio)**:
```
1. Developer runs: cosign sign myapp:v1.0
2. cosign opens browser for OIDC auth (GitHub/Google)
3. User authenticates (proves identity)
4. Fulcio issues short-lived certificate (valid 10 minutes)
5. cosign signs image with ephemeral key
6. Signature + certificate uploaded to registry
7. Entry written to Rekor (transparency log)

No long-lived keys stored!
```

**Verifying keyless signature**:
```bash
cosign verify \
  --certificate-identity=user@example.com \
  --certificate-oidc-issuer=https://github.com/login/oauth \
  myapp:v1.0

# Verification checks:
#  1. Signature valid for image digest
#  2. Certificate issued by Fulcio
#  3. Certificate identity matches expected
#  4. Entry exists in Rekor transparency log
```

### Rekor Transparency Log

**Purpose**: Publicly auditable log of all signatures.

**Why it matters**:
```
Without transparency log:
  Attacker compromises Fulcio
  Issues fake certificate
  Signs malicious image
  No one knows

With Rekor:
  All signatures publicly logged
  Can detect backdating
  Can audit certificate issuance
  Compromises detectable
```

**Query Rekor**:
```bash
# Search for signatures of an image
rekor-cli search --artifact myapp:v1.0

# Get entry details
rekor-cli get --uuid <uuid>
```

---

## 5. Policy Enforcement

### OPA Gatekeeper

**Open Policy Agent (OPA)**: Policy engine using Rego language.

**Gatekeeper**: Kubernetes-native OPA integration.

**Example policy**: Require signed images.

**ConstraintTemplate**:
```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8srequireimagesignature
spec:
  crd:
    spec:
      names:
        kind: K8sRequireImageSignature
      validation:
        openAPIV3Schema:
          type: object
          properties:
            publicKey:
              type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequireimagesignature

        import future.keywords.in

        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not is_signed(container.image)
          msg := sprintf("Image %v is not signed", [container.image])
        }

        is_signed(image) {
          # External data provider checks signature
          # (simplified - actual implementation more complex)
          data.inventory.signed_images[image]
        }
```

**Constraint** (use template):
```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequireImageSignature
metadata:
  name: require-signatures
spec:
  match:
    kinds:
    - apiGroups: [""]
      kinds: ["Pod"]
    namespaces:
    - production
  parameters:
    publicKey: |
      -----BEGIN PUBLIC KEY-----
      MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
      -----END PUBLIC KEY-----
```

**Effect**:
```bash
# Try to create pod with unsigned image
kubectl run test --image=unsigned:latest -n production

# Error:
# Error from server (Forbidden): admission webhook "validation.gatekeeper.sh" denied:
# [require-signatures] Image unsigned:latest is not signed
```

### Kyverno Policies

**Kyverno**: Kubernetes-native policy engine (simpler than OPA).

**Verify image signatures**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: check-image-signature
spec:
  validationFailureAction: enforce
  rules:
  - name: verify-signature
    match:
      any:
      - resources:
          kinds:
          - Pod
    verifyImages:
    - imageReferences:
      - "myregistry.io/*"
      attestors:
      - entries:
        - keyless:
            subject: "https://github.com/myorg/*"
            issuer: "https://token.actions.githubusercontent.com"
            rekor:
              url: https://rekor.sigstore.dev
```

**Check SLSA provenance**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: check-slsa-provenance
spec:
  validationFailureAction: enforce
  rules:
  - name: verify-slsa
    match:
      any:
      - resources:
          kinds:
          - Pod
    verifyImages:
    - imageReferences:
      - "myregistry.io/*"
      attestations:
      - predicateType: https://slsa.dev/provenance/v0.2
        conditions:
        - all:
          - key: "{{ builder.id }}"
            operator: Equals
            value: "https://github.com/Attestations/GitHubActionsWorkflow@v1"
          - key: "{{ invocation.configSource.uri }}"
            operator: Equals
            value: "https://github.com/myorg/myrepo"
```

---

## 6. End-to-End Supply Chain Security

### Complete Workflow

**1. Development**:
```
Developer commits code to GitHub
  → Branch protection requires code review
  → All commits signed with GPG
```

**2. Build**:
```yaml
# GitHub Actions with SLSA L3
- Hermetic build (no network access during build)
- All inputs pinned (base images, dependencies)
- Provenance generated automatically
- SBOM generated
- Image signed with Sigstore keyless signing
```

**3. Registry**:
```
Image pushed to registry
  → Signature pushed as separate layer
  → SBOM attached as attestation
  → Provenance attached as attestation
  → Entry written to Rekor transparency log
```

**4. Deployment**:
```yaml
# Kyverno policy enforces:
- Image must be signed (keyless, from GitHub Actions)
- Image must have SLSA provenance (from approved repo)
- Image must have SBOM
- No CRITICAL vulnerabilities in SBOM
```

**5. Runtime**:
```
- Falco monitors for anomalous behavior
- Pod Security Admission enforces Restricted policy
- Read-only root filesystem
- Network policies isolate pods
```

### Verification at Deployment

**Admission controller checks**:
```
Pod creation request arrives
  ↓
Verify signature (keyless)
  → Certificate identity matches expected
  → Signature valid
  → Entry in Rekor
  ↓
Verify SLSA provenance
  → Built by GitHub Actions
  → From approved repository
  → From specific commit
  ↓
Check SBOM
  → No CRITICAL vulnerabilities
  → No forbidden packages
  ↓
Allow pod creation
```

---

## Quick Reference

### SBOM Generation

```bash
# Syft (generate SBOM)
syft myapp:v1.0 -o spdx-json > sbom.json
syft myapp:v1.0 -o cyclonedx-json > sbom.json

# Attach SBOM to image
cosign attach sbom --sbom sbom.json myapp:v1.0

# Verify and retrieve SBOM
cosign verify-attestation --type spdx myapp:v1.0
```

### SLSA Provenance

```bash
# Generate (GitHub Actions does this automatically)
# Attach provenance
cosign attest --predicate provenance.json --type slsaprovenance myapp:v1.0

# Verify provenance
cosign verify-attestation --type slsaprovenance myapp:v1.0
```

### Sigstore

```bash
# Sign (keyless)
cosign sign myapp:v1.0

# Verify (keyless)
cosign verify \
  --certificate-identity=user@example.com \
  --certificate-oidc-issuer=https://github.com/login/oauth \
  myapp:v1.0

# Query Rekor
rekor-cli search --artifact myapp:v1.0
```

### Policy Tools

```bash
# OPA Gatekeeper
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml

# Kyverno
kubectl create -f https://github.com/kyverno/kyverno/releases/download/v1.10.0/install.yaml
```

---

## Summary

**Supply chain attacks** target the build and distribution process:
- Compromised dependencies
- Compromised build systems
- Compromised registries

**SBOM** (Software Bill of Materials):
- Lists all components in an image
- Enables vulnerability tracking
- Required for compliance (NTIA, EO 14028)

**SLSA provenance**:
- Proves how software was built
- Four levels (L1-L4)
- Prevents tampering with build process

**Sigstore ecosystem**:
- **Fulcio**: Short-lived certificates (keyless signing)
- **Rekor**: Transparency log (public audit trail)
- **cosign**: CLI for signing and verification

**Policy enforcement**:
- OPA Gatekeeper (Rego language, powerful)
- Kyverno (Kubernetes-native, easier)
- Enforce: signatures, provenance, SBOM, vulnerabilities

**End-to-end security**:
1. Signed commits
2. Hermetic builds with provenance
3. SBOM generation
4. Keyless signing
5. Policy enforcement at deployment
6. Runtime monitoring

**Next**: Review everything learned with a **quick start guide** for containers.

---

## Related Documents

- **Previous**: `05_security/03_pod_security.md` - Pod Security Standards
- **Next**: `quick_start_containers.md` - Container quick start
- **Foundation**: `05_security/01_image_security.md` - Image signing basics
- **Related**: All security documents (comprehensive supply chain requires all layers)
