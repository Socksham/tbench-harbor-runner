#!/bin/bash

#############################################
# NFS Server Setup Script
# Run this on the machine that will host the shared storage
# (typically the Backend API server or a dedicated storage server)
#############################################

set -e  # Exit on any error

echo "=================================="
echo "NFS Server Setup for Harbor Runner"
echo "=================================="
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Configuration
SHARED_DIR="/shared/harbor-jobs"
SUBNET="*"  # Adjust to your VPC subnet, or use * for all

echo "This script will:"
echo "  1. Install NFS server"
echo "  2. Create shared directory: $SHARED_DIR"
echo "  3. Configure NFS exports"
echo "  4. Start NFS server"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "[1/5] Installing NFS server..."
apt-get update
apt-get install -y nfs-kernel-server

echo ""
echo "[2/5] Creating shared directory: $SHARED_DIR"
mkdir -p $SHARED_DIR
mkdir -p $SHARED_DIR/jobs
mkdir -p $SHARED_DIR/uploads

# Set permissions to allow worker processes to write
chown -R nobody:nogroup $SHARED_DIR
chmod -R 777 $SHARED_DIR

echo ""
echo "[3/5] Configuring NFS exports..."
# Backup existing exports
if [ -f /etc/exports ]; then
    cp /etc/exports /etc/exports.backup.$(date +%Y%m%d-%H%M%S)
fi

# Add export configuration
# Options explained:
#   rw: Read-write access
#   sync: Synchronous writes (safer but slower)
#   no_subtree_check: Improves reliability for shared directories
#   no_root_squash: Allow root on clients to access as root (needed for Docker)
EXPORT_LINE="$SHARED_DIR $SUBNET(rw,sync,no_subtree_check,no_root_squash)"

if grep -q "^$SHARED_DIR " /etc/exports; then
    echo "Export already exists in /etc/exports, updating..."
    sed -i "s|^$SHARED_DIR .*|$EXPORT_LINE|" /etc/exports
else
    echo "Adding new export to /etc/exports..."
    echo "$EXPORT_LINE" >> /etc/exports
fi

echo ""
echo "[4/5] Applying NFS configuration..."
exportfs -ra

echo ""
echo "[5/5] Starting NFS server..."
systemctl enable nfs-kernel-server
systemctl restart nfs-kernel-server

echo ""
echo "✅ NFS Server setup complete!"
echo ""
echo "Configuration:"
echo "  - Shared directory: $SHARED_DIR"
echo "  - Allowed subnet: $SUBNET"
echo "  - NFS exports:"
cat /etc/exports | grep -v "^#" | grep -v "^$"
echo ""
echo "To verify NFS server is running:"
echo "  systemctl status nfs-kernel-server"
echo "  showmount -e localhost"
echo ""
echo "Next steps:"
echo "  1. Note this server's IP address"
echo "  2. Run setup_nfs_client.sh on each worker machine"
echo "  3. Update backend .env to use: JOBS_DIR=$SHARED_DIR/jobs"
echo ""
