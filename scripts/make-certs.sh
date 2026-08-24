#!/usr/bin/env bash
# Generate a local certificate authority and an HTTPS server certificate.
#
#   ./scripts/make-certs.sh 192.168.4.25
#
# The CA is what your phone trusts. The server certificate is what Flask serves.
# If your computer's IP changes, re-run this with the new address: the CA is
# reused, so trusted devices keep working and only the server cert is replaced.

set -euo pipefail

# Git Bash / MSYS rewrites arguments that look like Unix paths, which mangles
# openssl's "/CN=..." subject strings into Windows paths. Harmless elsewhere.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"

IP="${1:-}"
if [[ -z "$IP" ]]; then
  echo "usage: $0 <lan-ip>   e.g. $0 192.168.4.25" >&2
  exit 1
fi

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/certs"
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

# --- Certificate authority (created once, then reused) ---
if [[ ! -f ca-key.pem || ! -f ca-cert.pem ]]; then
  echo "Creating a new local certificate authority..."
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout ca-key.pem -out ca-cert.pem \
    -days 3650 -sha256 \
    -subj "/CN=Home Inventory Local CA/O=Home Inventory" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" 2>/dev/null
  # iOS installs this one; .crt is the extension Safari recognises.
  cp ca-cert.pem ca-cert.crt
else
  echo "Reusing the existing certificate authority."
fi

# --- Server certificate for this IP ---
# iOS rejects server certificates valid for more than 825 days.
echo "Issuing a server certificate for $IP..."
openssl req -newkey rsa:2048 -nodes \
  -keyout server-key.pem -out server.csr \
  -subj "/CN=$IP/O=Home Inventory" 2>/dev/null

cat > server-ext.cnf <<EOF
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = IP:$IP, IP:127.0.0.1, DNS:localhost
EOF

openssl x509 -req -in server.csr \
  -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial \
  -out server-cert.pem -days 820 -sha256 \
  -extfile server-ext.cnf 2>/dev/null

rm -f server.csr server-ext.cnf

echo
echo "Done. Files in $CERT_DIR:"
echo "  ca-cert.crt     <- install this one on your phone"
echo "  server-cert.pem <- served by Flask"
echo "  server-key.pem  <- private, never share or commit"
