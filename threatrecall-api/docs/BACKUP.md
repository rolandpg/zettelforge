# Backup and Disaster Recovery

## Velero Setup

### Prerequisites

```bash
# Install Velero CLI
wget https://github.com/vmware-tanzu/velero/releases/download/v1.12.0/velero-v1.12.0-linux-amd64.tar.gz
tar -xzf velero-v1.12.0-linux-amd64.tar.gz
sudo mv velero-v1.12.0-linux-amd64/velero /usr/local/bin/
```

### Install Velero on Cluster

```bash
# For AWS S3
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket threatrecall-backups \
  --backup-location-config region=us-east-1 \
  --snapshot-location-config region=us-east-1 \
  --secret-file ./credentials-velero

# For local MinIO (homelab)
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket velero \
  --backup-location-config region=minio,s3ForcePathStyle=true,s3Url=http://minio.minio-system:9000 \
  --secret-file ./minio-credentials
```

### Backup Strategy

**Daily Automated Backups:**
- Schedule: 2:00 AM daily
- Retention: 30 days
- Includes: PVCs, Secrets, ConfigMaps
- Pre/post hooks for data consistency

**Manual Backup:**
```bash
# Create on-demand backup
velero backup create threatrecall-manual-$(date +%Y%m%d) \
  --include-namespaces threatrecall-production \
  --selector app=threatrecall-api \
  --wait
```

### Disaster Recovery

**Scenario 1: Accidental Data Deletion**
```bash
# List available backups
velero backup get

# Restore from backup
velero restore create --from-backup threatrecall-daily-20240406020000

# Verify restoration
kubectl get pods -n threatrecall-production
```

**Scenario 2: Complete Cluster Loss**
```bash
# On new cluster
velero install --provider aws --bucket threatrecall-backups ...

# Restore everything
velero restore create --from-backup threatrecall-daily-latest
```

**Scenario 3: Point-in-Time Recovery**
```bash
# Restore to specific time
velero backup get | grep threatrecall-daily
velero restore create --from-backup threatrecall-daily-20240405020000
```

### Verify Backups

```bash
# Check backup status
velero backup get
velero backup describe threatrecall-daily-20240406020000

# Verify backup contents
velero backup logs threatrecall-daily-20240406020000
```

### Maintenance

```bash
# Delete old backups manually
velero backup delete threatrecall-daily-20240301020000

# Clean up expired backups
velero backup delete --all --confirm
```

## Data Integrity

The backup includes:
- **Persistent Volume**: All memory notes and embeddings
- **Secrets**: API keys and Vault tokens
- **ConfigMaps**: Application configuration

Note: LanceDB data is included in the PVC backup. Ensure no writes during backup (pre-hook handles this).
