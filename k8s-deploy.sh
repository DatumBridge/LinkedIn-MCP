#!/usr/bin/env bash
set -euo pipefail

# Deploy linkedin-mcp to Kubernetes (default namespace: mcp-tools)
# Flow: build -> (optional push) -> secret -> apply -> rollout -> smoke

NAMESPACE="${NAMESPACE:-mcp-tools}"
IMAGE_REPO="${IMAGE_REPO:-linkedin-mcp}"
IMAGE_TAG="${IMAGE_TAG:-local}"
SKIP_BUILD=0
SKIP_PUSH=1
SKIP_SMOKE=0
CREATE_SECRET=1

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_PATH="${ROOT_DIR}/k8s/deployment.yaml"
ENV_FILE="${ROOT_DIR}/.env"

usage() {
  cat <<'EOF'
Usage:
  ./k8s-deploy.sh [options]

Options:
  --image-repo <repo>     Image repository (default: linkedin-mcp)
  --image-tag <tag>       Image tag (default: local)
  --namespace <ns>        Kubernetes namespace (default: mcp-tools)
  --skip-build            Skip docker build
  --push                  Push image to registry (default: skip push for local OrbStack)
  --skip-smoke            Skip in-cluster /health smoke check
  --skip-secret           Do not create/update secret from .env
  -h, --help              Show help

Examples:
  ./k8s-deploy.sh
  ./k8s-deploy.sh --image-repo docker.io/datumbridge/tools-linkedin-mcp --image-tag main --push
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image-repo) IMAGE_REPO="${2:-}"; shift 2 ;;
    --image-tag) IMAGE_TAG="${2:-}"; shift 2 ;;
    --namespace) NAMESPACE="${2:-}"; shift 2 ;;
    --skip-build) SKIP_BUILD=1; shift ;;
    --push) SKIP_PUSH=0; shift ;;
    --skip-smoke) SKIP_SMOKE=1; shift ;;
    --skip-secret) CREATE_SECRET=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

MCP_IMAGE="${IMAGE_REPO}:${IMAGE_TAG}"

echo "==============================================="
echo " Deploy linkedin-mcp on Kubernetes"
echo "==============================================="
echo "Namespace: ${NAMESPACE}"
echo "Image:     ${MCP_IMAGE}"

cd "${ROOT_DIR}"

if [[ ${SKIP_BUILD} -eq 0 ]]; then
  echo ""
  echo "[1/5] Building image..."
  docker build -t "${MCP_IMAGE}" .
else
  echo ""
  echo "[1/5] Skipping build (--skip-build)"
fi

if [[ ${SKIP_PUSH} -eq 0 ]]; then
  echo ""
  echo "[2/5] Pushing image..."
  docker push "${MCP_IMAGE}"
else
  echo ""
  echo "[2/5] Skipping push (local cluster / OrbStack)"
fi

echo ""
echo "[3/5] Ensuring namespace + secret..."
kubectl create namespace "${NAMESPACE}" 2>/dev/null || true

if [[ ${CREATE_SECRET} -eq 1 ]]; then
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Error: ${ENV_FILE} not found. Copy .env.example to .env and set LINKEDIN_CLIENT_ID/SECRET."
    exit 1
  fi
  # Extract only secret keys (never bake into image/manifest).
  TMP_ENV="$(mktemp)"
  trap 'rm -f "${TMP_ENV}"' EXIT
  grep -E '^(LINKEDIN_CLIENT_ID|LINKEDIN_CLIENT_SECRET|OAUTH_REDIRECT_URI|LINKEDIN_OAUTH_SCOPES|LINKEDIN_API_VERSION)=' \
    "${ENV_FILE}" | grep -v '^=*$' > "${TMP_ENV}" || true
  if [[ ! -s "${TMP_ENV}" ]]; then
    echo "Error: no LINKEDIN_CLIENT_ID/SECRET found in .env"
    exit 1
  fi
  kubectl -n "${NAMESPACE}" create secret generic linkedin-mcp-main-secret \
    --from-env-file="${TMP_ENV}" \
    --dry-run=client -o yaml | kubectl apply -f -
  echo "  - secret/linkedin-mcp-main-secret applied"
else
  echo "  - skipping secret (--skip-secret)"
fi

echo ""
echo "[4/5] Applying manifests..."
sed \
  -e "s|namespace: mcp-tools|namespace: ${NAMESPACE}|g" \
  -e "s|image: linkedin-mcp:local|image: ${MCP_IMAGE}|g" \
  "${MANIFEST_PATH}" | kubectl apply -f -

# Force restart when image tag is reused (e.g. :local) so new layers are picked up.
kubectl -n "${NAMESPACE}" patch deployment linkedin-mcp-main \
  --type merge \
  -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"datumbridge.io/deploy-stamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}}}}" \
  >/dev/null

echo ""
echo "[5/5] Waiting for rollout..."
kubectl -n "${NAMESPACE}" rollout status deploy/linkedin-mcp-main --timeout=300s

NODE_PORT="$(kubectl -n "${NAMESPACE}" get svc linkedin-mcp-main -o jsonpath='{.spec.ports[0].nodePort}')"
REDIRECT_URI="http://127.0.0.1:${NODE_PORT}/oauth/callback"

# Keep OAuth redirect aligned with NodePort for browser Test UI.
kubectl -n "${NAMESPACE}" patch secret linkedin-mcp-main-secret --type merge -p \
  "{\"stringData\":{\"OAUTH_REDIRECT_URI\":\"${REDIRECT_URI}\"}}" >/dev/null || true
kubectl -n "${NAMESPACE}" set env deployment/linkedin-mcp-main \
  "OAUTH_REDIRECT_URI=${REDIRECT_URI}" >/dev/null || true
kubectl -n "${NAMESPACE}" rollout status deploy/linkedin-mcp-main --timeout=180s

if [[ ${SKIP_SMOKE} -eq 0 ]]; then
  echo ""
  echo "Smoke: GET /health"
  kubectl -n "${NAMESPACE}" run linkedin-mcp-smoke --rm -i --restart=Never --image=curlimages/curl -- \
    curl -fsS "http://linkedin-mcp-main:8000/health"
  echo ""
  echo "Smoke: GET /test (UI enabled)"
  CODE="$(kubectl -n "${NAMESPACE}" run linkedin-mcp-smoke-ui --rm -i --restart=Never --image=curlimages/curl -- \
    curl -s -o /dev/null -w '%{http_code}' "http://linkedin-mcp-main:8000/test" || true)"
  echo "  /test HTTP ${CODE}"
fi

echo ""
echo "Done."
echo "  In-cluster:  http://linkedin-mcp-main.${NAMESPACE}.svc.cluster.local:8000"
echo "  MCP path:    http://linkedin-mcp-main.${NAMESPACE}.svc.cluster.local:8000/mcp/"
echo "  Test UI:     http://127.0.0.1:${NODE_PORT}/test"
echo "  OAuth cb:    ${REDIRECT_URI}"
echo "  Add that exact callback URL in LinkedIn Developer Portal → Auth."
echo "  Registry id: mcpServer=linkedin"
echo "  Docs:        docs/operations/manual-testing.md"
