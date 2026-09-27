#!/usr/bin/env bash
# Runs ON THE VPS, piped over SSH by .github/workflows/deploy.yml (via
# `bash -s < this-file`). Kept as its own file rather than an inline
# heredoc in the workflow YAML so it can be read/edited/shellchecked
# like a normal shell script, with no YAML-indentation constraints.
set -e

APP_DIR="/var/www/ideal_Gifting/idealgifting-backend"
DEPLOY_KEY="$HOME/.ssh/github_deploy_ed25519"
SSH_CONFIG="$HOME/.ssh/config"
# GitHub's own published ed25519 host key (see
# https://docs.github.com/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints) -
# trusted directly rather than via ssh-keyscan, so verifying the
# VPS -> GitHub connection never depends on trust-on-first-use.
GITHUB_HOST_KEY='github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl'

echo "=== Ensuring VPS has a dedicated GitHub deploy key ==="
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [ ! -f "$DEPLOY_KEY" ]; then
  echo "No dedicated deploy key found at $DEPLOY_KEY - generating one (ed25519, no passphrase, for non-interactive use)."
  ssh-keygen -t ed25519 -f "$DEPLOY_KEY" -N "" -C "idealgifting-vps-deploy" -q
else
  echo "Reusing existing deploy key at $DEPLOY_KEY."
fi
chmod 600 "$DEPLOY_KEY"
chmod 644 "$DEPLOY_KEY.pub"

echo "=== VPS deploy public key (safe to share - add as a GitHub Deploy Key if not already registered) ==="
echo "-----BEGIN DEPLOY PUBLIC KEY-----"
cat "$DEPLOY_KEY.pub"
echo "-----END DEPLOY PUBLIC KEY-----"

if ! grep -qF "Host github.com" "$SSH_CONFIG" 2>/dev/null; then
  echo "Adding a github.com entry to $SSH_CONFIG"
  {
    echo ""
    echo "Host github.com"
    echo "    HostName github.com"
    echo "    User git"
    echo "    IdentityFile $DEPLOY_KEY"
    echo "    IdentitiesOnly yes"
  } >> "$SSH_CONFIG"
fi
chmod 600 "$SSH_CONFIG"

touch "$HOME/.ssh/known_hosts"
if ! grep -qF "$GITHUB_HOST_KEY" "$HOME/.ssh/known_hosts"; then
  echo "Trusting GitHub's official host key in known_hosts"
  echo "$GITHUB_HOST_KEY" >> "$HOME/.ssh/known_hosts"
fi
chmod 600 "$HOME/.ssh/known_hosts"

echo "=== Verifying VPS -> GitHub SSH authentication ==="
# github.com deliberately refuses a shell and always exits 1 on a
# successful auth handshake, so check the greeting text rather than the
# exit code.
if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
  echo "✅ GitHub SSH authentication succeeded."
else
  echo "❌ GitHub has not authenticated this deploy key yet."
  echo "    Add the PUBLIC key printed above under:"
  echo "    GitHub repo -> Settings -> Deploy keys -> Add deploy key (read-only is sufficient)."
  echo "    Then re-run this deployment."
  exit 1
fi

cd "$APP_DIR"

echo "=== Ensuring the repository uses SSH, not HTTPS, for the GitHub remote ==="
CURRENT_REMOTE="$(git remote get-url origin)"
echo "Current origin remote: $CURRENT_REMOTE"
case "$CURRENT_REMOTE" in
  https://github.com/*)
    OWNER_REPO="${CURRENT_REMOTE#https://github.com/}"
    OWNER_REPO="${OWNER_REPO%.git}"
    NEW_REMOTE="git@github.com:${OWNER_REPO}.git"
    echo "Switching origin to SSH: $NEW_REMOTE"
    git remote set-url origin "$NEW_REMOTE"
    ;;
  git@github.com:*)
    echo "Origin already uses SSH."
    ;;
  *)
    echo "Origin uses an unrecognized scheme - leaving it untouched: $CURRENT_REMOTE"
    ;;
esac

echo "=== Pulling latest code (fetch + fast-forward only - never a destructive reset) ==="
git fetch origin
git checkout main
git pull --ff-only origin main

DEPLOYED_COMMIT="$(git rev-parse HEAD)"
echo "Deployed commit: $DEPLOYED_COMMIT"

echo "=== Activating virtualenv ==="
source venv/bin/activate

echo "=== Installing requirements ==="
pip install -r requirements.txt

echo "=== Creating migrations ==="
python manage.py makemigrations

echo "=== Running migrations (non-interactive) ==="
python manage.py migrate --noinput

echo "=== Collecting static files (MEDIA_ROOT/user uploads are untouched by this) ==="
python manage.py collectstatic --noinput

# Independently-checkable proof of exactly what commit this process is
# running, read back by the /deploy-info/ Django view (served by
# Gunicorn directly, not dependent on Nginx's static-file routing) -
# not a secret, just a commit hash and a log line.
{
  echo "commit: $DEPLOYED_COMMIT"
  echo "deployed_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "orders/admin.py last touched by:"
  git log -1 --format="  %H %s" -- orders/admin.py
} > DEPLOYED_COMMIT.txt
echo "=== Wrote deploy marker: $(cat DEPLOYED_COMMIT.txt | tr '\n' ' ') ==="

echo "=== Restarting Gunicorn service ==="
systemctl restart idealgifting

echo "=== Reloading Nginx ==="
systemctl reload nginx

echo "=== Health check ==="
HEALTH_URL="https://api.idealgifting.in/api/products/"
ATTEMPT=1
MAX_ATTEMPTS=5
until curl -fsS -o /dev/null --max-time 10 "$HEALTH_URL"; do
  if [ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]; then
    echo "❌ Health check failed after $MAX_ATTEMPTS attempts against $HEALTH_URL"
    echo "   Inspect the service with: systemctl status idealgifting && journalctl -u idealgifting -n 100"
    exit 1
  fi
  echo "Health check attempt $ATTEMPT failed, retrying in 3s..."
  ATTEMPT=$((ATTEMPT + 1))
  sleep 3
done
echo "✅ Health check passed ($HEALTH_URL is responding)"

echo "✅ Ideal Gifting Deployment Successful"
