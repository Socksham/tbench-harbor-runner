#!/bin/bash

#############################################
# NFS Client Setup Script
# Run this on each worker EC2 instance
#############################################

set -e  # Exit on any error

echo "=================================="
echo "NFS Client Setup for Harbor Worker"
echo "=================================="
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Configuration
SHARED_DIR="/shared/harbor-jobs"
NFS_SERVER_IP="${1:-}"

if [ -z "$NFS_SERVER_IP" ]; then
    echo "ERROR: NFS server IP not provided"
    echo ""
    echo "Usage: sudo ./setup_nfs_client.sh <NFS_SERVER_IP>"
    echo "Example: sudo ./setup_nfs_client.sh 10.0.1.100"
    exit 1
fi

echo "Configuration:"
echo "  - NFS Server: $NFS_SERVER_IP"
echo "  - Mount point: $SHARED_DIR"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "[1/5] Installing NFS client..."
apt-get update
apt-get install -y nfs-common

echo ""
echo "[2/5] Creating mount point: $SHARED_DIR"
mkdir -p $SHARED_DIR

echo ""
echo "[3/5] Testing NFS connection..."
if ! showmount -e $NFS_SERVER_IP &> /dev/null; then
    echo "ERROR: Cannot connect to NFS server at $NFS_SERVER_IP"
    echo "Please check:"
    echo "  1. NFS server is running"
    echo "  2. Security group allows NFS traffic (port 2049)"
    echo "  3. Server IP address is correct"
    exit 1
fi

echo "Available exports from $NFS_SERVER_IP:"
showmount -e $NFS_SERVER_IP

echo ""
echo "[4/5] Mounting NFS share..."
mount -t nfs $NFS_SERVER_IP:$SHARED_DIR $SHARED_DIR

echo ""
echo "[5/5] Adding to /etc/fstab for automatic mounting..."
# Backup fstab
cp /etc/fstab /etc/fstab.backup.$(date +%Y%m%d-%H%M%S)

# Add mount if not already present
FSTAB_LINE="$NFS_SERVER_IP:$SHARED_DIR $SHARED_DIR nfs defaults,_netdev 0 0"
if grep -q "$SHARED_DIR" /etc/fstab; then
    echo "Mount already exists in /etc/fstab, updating..."
    sed -i "\|$SHARED_DIR|c\\$FSTAB_LINE" /etc/fstab
else
    echo "Adding mount to /etc/fstab..."
    echo "$FSTAB_LINE" >> /etc/fstab
fi

echo ""
echo "✅ NFS Client setup complete!"
echo ""
echo "Verification:"
echo "  - Mount status:"
df -h | grep $SHARED_DIR || echo "    (Not mounted yet)"
mount | grep $SHARED_DIR

echo ""
echo "Testing write access..."
TEST_FILE="$SHARED_DIR/.write_test_$(date +%s)"
if touch $TEST_FILE 2>/dev/null; then
    echo "  ✅ Write access confirmed"
    rm -f $TEST_FILE
else
    echo "  ❌ Write access failed"
    echo "  Check NFS server permissions"
fi

echo ""
echo "Next steps:"
echo "  1. Proceed with worker deployment (setup_worker.sh)"
echo ""
