#!/bin/bash
#
# Setup Script for Harbor Auto-Scaling Metric Publisher
#
# This script:
# 1. Installs dependencies (boto3, redis)
# 2. Configures the metric publisher script
# 3. Sets up cron job to run every minute
# 4. Tests the script
#

set -e

echo "================================================"
echo "Harbor Auto-Scaling Metric Publisher Setup"
echo "================================================"
echo ""

# Check if running on backend server
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found. Please run this from the backend directory."
    exit 1
fi

# Source .env to get Redis URL
source .env

# Extract Redis host from REDIS_URL
REDIS_HOST=$(echo $REDIS_URL | sed -n 's|redis://\([^:]*\):.*|\1|p')
echo "Detected Redis host: $REDIS_HOST"

# Step 1: Install Python dependencies
echo ""
echo "[1/5] Installing Python dependencies..."
pip3 install boto3 redis --quiet || {
    echo "ERROR: Failed to install dependencies"
    exit 1
}
echo "✓ Dependencies installed"

# Step 2: Configure the script
echo ""
echo "[2/5] Configuring metric publisher..."

# Prompt for ASG name
read -p "Enter your Auto Scaling Group name [harbor-workers-asg]: " ASG_NAME
ASG_NAME=${ASG_NAME:-harbor-workers-asg}

# Prompt for AWS region
read -p "Enter AWS region [us-east-2]: " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-2}

# Create environment file for the script
cat > /home/ubuntu/harbor-metric-publisher.env << EOF
REDIS_HOST=$REDIS_HOST
REDIS_PORT=6379
REDIS_DB=0
ASG_NAME=$ASG_NAME
AWS_REGION=$AWS_REGION
EOF

echo "✓ Configuration saved to /home/ubuntu/harbor-metric-publisher.env"

# Step 3: Copy script to system location
echo ""
echo "[3/5] Installing script..."
sudo cp publish_queue_metric.py /usr/local/bin/publish_harbor_metric.py
sudo chmod +x /usr/local/bin/publish_harbor_metric.py
echo "✓ Script installed to /usr/local/bin/publish_harbor_metric.py"

# Step 4: Test the script
echo ""
echo "[4/5] Testing script..."
echo "Running test execution..."
export $(cat /home/ubuntu/harbor-metric-publisher.env | xargs)
python3 /usr/local/bin/publish_harbor_metric.py

if [ $? -eq 0 ]; then
    echo "✓ Script test successful!"
else
    echo "ERROR: Script test failed. Please check the error messages above."
    exit 1
fi

# Step 5: Setup cron job
echo ""
echo "[5/5] Setting up cron job..."

# Create wrapper script that sources environment variables
cat > /home/ubuntu/run_harbor_metric_publisher.sh << 'EOF'
#!/bin/bash
# Load environment variables
export $(cat /home/ubuntu/harbor-metric-publisher.env | grep -v '^#' | xargs)

# Run the metric publisher
/usr/local/bin/publish_harbor_metric.py >> /var/log/harbor-metric-publisher.log 2>&1
EOF

chmod +x /home/ubuntu/run_harbor_metric_publisher.sh

# Add to crontab (run every minute)
CRON_JOB="* * * * * /home/ubuntu/run_harbor_metric_publisher.sh"

# Check if cron job already exists
(crontab -l 2>/dev/null | grep -v "run_harbor_metric_publisher.sh"; echo "$CRON_JOB") | crontab -

echo "✓ Cron job installed (runs every minute)"

# Create log file
sudo touch /var/log/harbor-metric-publisher.log
sudo chown ubuntu:ubuntu /var/log/harbor-metric-publisher.log

echo ""
echo "================================================"
echo "✓ Setup Complete!"
echo "================================================"
echo ""
echo "Configuration:"
echo "  ASG Name: $ASG_NAME"
echo "  AWS Region: $AWS_REGION"
echo "  Redis Host: $REDIS_HOST"
echo ""
echo "The metric publisher will run every minute via cron."
echo ""
echo "Useful commands:"
echo "  - View logs: tail -f /var/log/harbor-metric-publisher.log"
echo "  - Test manually: /home/ubuntu/run_harbor_metric_publisher.sh"
echo "  - Edit config: nano /home/ubuntu/harbor-metric-publisher.env"
echo "  - View cron jobs: crontab -l"
echo ""
echo "Next steps:"
echo "  1. Wait 2-3 minutes for metrics to start appearing"
echo "  2. Check CloudWatch: Namespace 'Harbor/Workers', Metric 'QueueDepthPerWorker'"
echo "  3. Once verified, add Target Tracking policy to your ASG"
echo ""
echo "To check if it's working:"
echo "  tail -f /var/log/harbor-metric-publisher.log"
echo ""
