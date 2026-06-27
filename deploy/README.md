# EA-Brain — Server Deployment

## Requirements
- Debian 12+ / Ubuntu 22.04+
- 4GB RAM (8GB+ recommended)
- 10GB free disk
- Git
- Internet connection (for cloning, installing deps, APIs)

## Quick Install

```bash
# 1. Clone the repository (or copy files)
git clone <your-repo> /opt/ea-brain
cd /opt/ea-brain

# 2. Run setup
sudo bash deploy/setup.sh

# 3. Configure API keys
sudo nano /opt/ea-brain/.env
# → Set at least OPENCODE_API_KEY or GROQ_API_KEY

# 4. Start
sudo systemctl restart ea-brain
```

> **Migrating from Baul?** The setup script automatically detects old `baul.service`, stops/disables it, and installs the new `ea-brain.service`.

## File Structure

```
/opt/ea-brain/
├── backend/          # Python/FastAPI backend code
├── frontend/         # React frontend code
├── brain/            # User data (notes, images, vectors)
│   ├── baul/         # Markdown notes + images
│   ├── inbox/        # Uploaded files pending conversion
│   ├── connections/  # Note connections
│   └── meta/         # Vector indices and metadata
├── deploy/           # Deployment scripts
├── requirements.txt  # Python dependencies
├── .env              # Configuration (API keys, paths)
└── .venv/            # Python virtual environment
```

## Useful Commands

```bash
# Service status
sudo systemctl status ea-brain

# View live logs
journalctl -u ea-brain -f

# Restart service
sudo systemctl restart ea-brain

# Update code and restart
sudo bash /opt/ea-brain/deploy/setup.sh --update

# View recent logs
journalctl -u ea-brain -n 50 --no-pager
```

## PostgreSQL (for future multi-user)

The setup creates the database role automatically. To connect:

```bash
sudo -u postgres psql -c "ALTER ROLE ea-brain PASSWORD 'your-secure-password';"
```

When multi-user is implemented, tables will live in `ea_brain_db`.

## Security

- Service runs as user `ea-brain` (unprivileged)
- `/opt/ea-brain/.env` has permissions 600 (readable only by ea-brain)
- Nginx reverse proxy recommended (config generated automatically)
- Images served with 7-day cache
- System logs do not contain API keys
