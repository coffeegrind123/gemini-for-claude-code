# Configuration Security Guide

## 🔐 Secure Configuration Storage

The Claude Code Multi-Provider Proxy now stores configuration files in secure, standard system locations **outside** the repository to protect your API keys and sensitive data.

## 📍 Configuration Locations

### Linux / macOS
```
~/.config/gemini-code/
├── config.env          # Environment variables
├── config.json         # JSON configuration  
├── config.yml          # YAML configuration
└── logs/               # Log files
```

### Windows
```
%USERPROFILE%\AppData\Local\gemini-code\
├── config.env          # Environment variables
├── config.json         # JSON configuration
├── config.yml          # YAML configuration
└── logs\               # Log files
```

### XDG Compliance
If you have `XDG_CONFIG_HOME` set, configuration will be stored in:
```
$XDG_CONFIG_HOME/gemini-code/
```

## 🚨 Why This Matters

### Before (Insecure)
```bash
# Config stored in repository
gemini-code/
├── .env                # ❌ API keys in repo!
├── server.py
└── ...

# Problems:
# - API keys could be committed to git
# - Running from different locations creates multiple configs
# - Sharing repo exposes secrets
# - No permission control
```

### After (Secure)
```bash
# Config stored in user directory
~/.config/gemini-code/
├── config.env          # ✅ Secure, outside repo
└── logs/

# Repository (clean)
gemini-code/
├── server.py           # ✅ No secrets
├── .gitignore          # ✅ Ignores any accidental configs
└── ...

# Benefits:
# - API keys never in repository
# - Works from any location
# - User-only permissions
# - Standard system locations
```

## 🔄 Migration

The system automatically migrates old configurations:

```bash
claude-proxy config
# 🔄 Migrating configuration from repository to secure location...
# ✅ Configuration migrated to: ~/.config/gemini-code/config.env
# Remove old config file from repository? (y/n): y
# ✅ Old config file removed from repository
```

## 🛡️ Security Features

### 1. **User-Only Permissions**
```bash
# Config directory has restricted permissions
ls -la ~/.config/gemini-code/
# drwx------  3 user user  96 Nov 15 10:30 .
```

### 2. **Repository Protection**
```bash
# .gitignore prevents accidental commits
cat .gitignore
# .env
# config.*
# *.env
```

### 3. **Multi-Location Safety**
```bash
# Works from anywhere, same config
cd ~/projects/my-app && claude-proxy start
cd ~/scripts && claude-proxy start
# Both use ~/.config/gemini-code/config.env
```


## 🔍 Verification

### Check Config Location
```bash
claude-proxy config
# Config will be stored in: ~/.config/gemini-code
```

### Verify No Secrets in Repo
```bash
# Check repository for any config files
find . -name "*.env" -o -name "config.*"
# Should return nothing or only examples
```

### Check File Permissions
```bash
ls -la ~/.config/gemini-code/
# Should show user-only permissions (700)
```

## 🚨 Emergency: Remove Secrets from Git

If you accidentally committed secrets:

### 1. Remove from Current Commit
```bash
git rm --cached .env config.*
git commit -m "Remove configuration files"
```

### 2. Remove from History (Nuclear Option)
```bash
# WARNING: This rewrites history
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env config.*' \
  --prune-empty --tag-name-filter cat -- --all

git push --force --all
```

### 3. Rotate API Keys
```bash
# 1. Get new API key from Google AI Studio
# 2. Update configuration
claude-proxy config
# 3. Revoke old API key
```

## 🔧 Advanced Configuration Security

### Environment Variable Override
```bash
# Most secure: Use environment variables
export GEMINI_API_KEY="your-secret-key"
claude-proxy start
# Config files will not override env vars
```


### Kubernetes Secrets
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: claude-proxy
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: gemini-api-key
              key: key
```

## ✅ Best Practices Checklist

- [ ] Configuration stored outside repository
- [ ] No `.env` files in git
- [ ] API keys in environment variables (production)
- [ ] File permissions set to user-only
- [ ] Old repository configs removed
- [ ] `.gitignore` updated
- [ ] Team trained on new config location
- [ ] CI/CD updated to use env vars
- [ ] Documentation updated

## 🆘 Troubleshooting

### Can't Find Config
```bash
# Check if config directory exists
ls -la ~/.config/gemini-code/

# Recreate if missing
claude-proxy config
```

### Permission Denied
```bash
# Fix permissions
chmod 700 ~/.config/gemini-code/
chmod 600 ~/.config/gemini-code/config.*
```

### Multiple Configs
```bash
# Check for old configs in repo
find . -name "*.env" -type f

# Remove old configs
rm -f .env config.*
```

Remember: **Your API keys should never be in a git repository!** 🔐