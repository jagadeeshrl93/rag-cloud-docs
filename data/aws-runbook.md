# AWS Infrastructure Runbook

## 1. IAM Credential Rotation

### When to rotate

- Every 90 days as standard policy
- Immediately if a key is suspected compromised
- When an engineer leaves the team

### Steps to rotate AWS access keys

1. Log in to the AWS Console and navigate to IAM
2. Select Users and choose the target user
3. Click the Security credentials tab
4. Under Access keys, click Create access key
5. Download the new key ID and secret immediately — you cannot retrieve the secret again
6. Update all services and applications using the old key with the new credentials
7. Test that all services are working correctly with the new key
8. Return to IAM, select the old key, click Deactivate
9. Monitor CloudWatch logs for any authentication errors for 24 hours
10. Once confirmed working, click Delete on the old key

### Rollback

If services break after rotation, reactivate the old key immediately via IAM console
and investigate which service was not updated before retrying.

---

## 2. EC2 Instance Troubleshooting

### Instance not reachable via SSH

**Check 1 — Security Group**

- Navigate to EC2 → Instances → select instance
- Check Security Groups → Inbound rules
- Port 22 must be open for your IP or 0.0.0.0/0 (not recommended for production)

**Check 2 — Instance state**

- Ensure instance state is "running" not "stopped" or "terminated"
- Check system status checks and instance status checks in the Status Checks tab

**Check 3 — Key pair**

- Confirm you are using the correct .pem file for the instance
- Run: chmod 400 your-key.pem before attempting SSH

**Check 4 — SSH command**

```bash
ssh -i your-key.pem ec2-user@your-public-ip
# For Ubuntu AMIs use: ubuntu@your-public-ip
# For Amazon Linux use: ec2-user@your-public-ip
```

### High CPU usage on EC2

1. SSH into the instance
2. Run top or htop to identify the process consuming CPU
3. Check CloudWatch metrics for historical CPU trend
4. If a runaway process, kill it with: kill -9 <PID>
5. If persistent, consider upgrading instance type via stop → change instance type → start

---

## 3. S3 Bucket Operations

### Making a bucket private after accidental public exposure

1. Go to S3 console → select the bucket
2. Permissions tab → Block public access → Edit
3. Enable all four Block Public Access settings
4. Save changes
5. Check Bucket Policy and remove any statements with "Principal": "\*"
6. Check ACL and remove any public grants
7. Enable S3 server access logging to audit future access

### Syncing files to S3

```bash
# sync local folder to S3 bucket
aws s3 sync ./local-folder s3://your-bucket-name/prefix/

# sync with deletion of files removed locally
aws s3 sync ./local-folder s3://your-bucket-name/prefix/ --delete

# dry run to preview changes
aws s3 sync ./local-folder s3://your-bucket-name/prefix/ --dryrun
```

### Recovering a deleted S3 object

- Only possible if versioning is enabled on the bucket
- Go to S3 → bucket → Show versions
- Find the object with the delete marker
- Delete the delete marker to restore the previous version

---

## 4. RDS Database Troubleshooting

### Cannot connect to RDS instance

**Check 1 — Security Group**

- RDS security group must allow inbound on port 5432 (PostgreSQL) or 3306 (MySQL)
- Source must be your EC2 instance security group or your IP

**Check 2 — VPC and subnet**

- RDS must be in the same VPC as the connecting EC2 instance
- Check that the subnet route table has correct routing

**Check 3 — Credentials**

- Test connection using psql or mysql client from the EC2 instance:

```bash
psql -h your-rds-endpoint -U your-username -d your-database
```

### RDS high CPU or slow queries

1. Enable Performance Insights in RDS console
2. Identify top SQL queries by load
3. Check for missing indexes using EXPLAIN ANALYZE on slow queries
4. Consider read replicas for read-heavy workloads
5. Review connection pooling — use PgBouncer for PostgreSQL

---

## 5. Kubernetes on EKS

### Pod stuck in CrashLoopBackOff

```bash
# check pod status
kubectl get pods -n your-namespace

# view pod logs
kubectl logs <pod-name> -n your-namespace

# view previous container logs if pod keeps restarting
kubectl logs <pod-name> -n your-namespace --previous

# describe pod for events
kubectl describe pod <pod-name> -n your-namespace
```

Common causes:

- Application error on startup — check logs for stack trace
- Missing environment variable or secret
- Insufficient memory — check resource limits
- Failing liveness probe — check probe configuration

### Node not joining the cluster

```bash
# check node status
kubectl get nodes

# describe a not-ready node
kubectl describe node <node-name>

# check kubelet logs on the node
sudo journalctl -u kubelet -f
```

Common fix: ensure --kubelet-timeout=30s is set in kubeadm config
for nodes on slow networks with delayed registration.

### Scaling a deployment

```bash
# scale manually
kubectl scale deployment your-deployment --replicas=5 -n your-namespace

# check rollout status
kubectl rollout status deployment/your-deployment -n your-namespace

# rollback if something goes wrong
kubectl rollout undo deployment/your-deployment -n your-namespace
```

---

## 6. CloudWatch Alerting

### Setting up a CPU alarm on EC2

1. Go to CloudWatch → Alarms → Create Alarm
2. Select metric → EC2 → Per-Instance Metrics → CPUUtilization
3. Set threshold: Greater than 80% for 2 consecutive periods of 5 minutes
4. Configure action: Send notification to SNS topic
5. Create SNS topic and add your email as subscriber
6. Confirm subscription via email

### Querying logs with CloudWatch Insights

```bash
# find all ERROR logs in the last hour
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 50

# count errors by type
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)
```

---

## 7. Cost Optimisation

### Identifying unused resources

- EC2: Look for instances with CPU < 5% over 2 weeks in CloudWatch
- RDS: Check DatabaseConnections metric — zero connections means unused
- EBS: Volumes with state "available" are not attached — consider deleting
- Elastic IPs: Unattached EIPs are charged — release unused ones

### Right-sizing EC2 instances

1. Install AWS Compute Optimizer
2. Review recommendations in the Compute Optimizer console
3. Stop the instance
4. Actions → Instance Settings → Change Instance Type
5. Start the instance and verify application behaviour

### Reserved Instance planning

- Analyse 3 months of On-Demand usage in Cost Explorer
- Purchase Reserved Instances for stable baseline workloads
- Use Savings Plans for flexible compute across instance types
