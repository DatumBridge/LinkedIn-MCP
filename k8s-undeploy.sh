#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-mcp-tools}"
DELETE_SECRET=0

usage() {
  cat <<'EOF'
Usage:
  ./k8s-undeploy.sh [--namespace mcp-tools] [--delete-secret]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace) NAMESPACE="${2:-}"; shift 2 ;;
    --delete-secret) DELETE_SECRET=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Undeploying linkedin-mcp-main from ${NAMESPACE}..."
kubectl -n "${NAMESPACE}" delete deploy,svc,cm -l app=linkedin-mcp-main --ignore-not-found
# Resources without app label
kubectl -n "${NAMESPACE}" delete deploy linkedin-mcp-main --ignore-not-found
kubectl -n "${NAMESPACE}" delete svc linkedin-mcp-main --ignore-not-found
kubectl -n "${NAMESPACE}" delete cm linkedin-mcp-main-config --ignore-not-found

if [[ ${DELETE_SECRET} -eq 1 ]]; then
  kubectl -n "${NAMESPACE}" delete secret linkedin-mcp-main-secret --ignore-not-found
fi

echo "Done."
