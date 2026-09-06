# FCMS on Synology NAS — deployment

Everything runs on the NAS, nothing leaves the LAN except the outbound integrations
(SMS/LINE/Email/WhatsApp in CRM, social-media posting in Module 8).

## 1. NAS prerequisites (DSM 7.2+)
1. Package Center → install **Container Manager** (Docker).
2. File Station → create `/volume1/docker/fcms/` with sub-folders `data/`, `backups/`.
3. Control Panel → Task Scheduler is not needed; the `backup` container handles nightly dumps.

## 2. Get the code onto the NAS
```bash
ssh admin@<nas-ip>
cd /volume1/docker/fcms
git clone https://github.com/dr-patsama/fcms.git src     # use the PAT when prompted
cd src/deploy/synology
cp .env.example .env && vi .env                          # set passwords + SECRET_KEY
```

## 3. Start
```bash
sudo docker compose up -d --build
sudo docker compose logs -f api      # wait for "starting FCMS on :8000"
```
Then open **http://<nas-ip>:8000/login** → sign in as the admin from `.env`.
API docs: http://<nas-ip>:8000/docs   Orthanc: http://<nas-ip>:8042
Live boards (auto-updating, for wall screens): http://<nas-ip>:8000/board/opd · /board/embryo
Cycle plan / timeline: http://<nas-ip>:8000/timeline

## 4. GE Voluson Swift
DICOM → Send-to node: AE title `FCMS_ORTHANC`, host `<nas-ip>`, port `4242`.

## 5. Hierarchical login (RBAC)
15 roles with levels 10–100. `admin` (100) and `it_admin` (95) pass every check.
Module access per role is defined in `module1/backend/core/auth.py` (`SYSTEM_ROLES`).
Set `SEED_MODE=all` for one test account per role (`<role>@lifeclinic.com` / `SEED_DEMO_PASSWORD`).
MFA (TOTP) is mandatory for physician, embryologist, lab_supervisor, admin.

## 6. Update
```bash
cd /volume1/docker/fcms/src && git pull && cd deploy/synology
sudo docker compose up -d --build api          # migrations run automatically on start
```

## 7. Backup / restore
Nightly gzip dumps in `/volume1/docker/fcms/backups` (30 days). Add that folder to
**Hyper Backup**. Restore:
```bash
zcat backups/fcms_YYYYMMDD_0200.sql.gz | sudo docker exec -i fcms-db psql -U fcms_user fcms_db
```

## 8. Optional: friendly URL + HTTPS
DSM → Login Portal → Reverse Proxy: `https://fcms.<your-domain>` → `http://localhost:8000`,
with a Let's Encrypt cert from DSM. Add the URL to `CORS_ORIGINS`.
