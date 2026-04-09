# Parley Chat Installer

[🇮🇷 فارسی](README.fa.md) | [🇪🇸 Español](README.es-es.md)

Automated installer for [Parley Chat](https://github.com/Parley-Chat). Sets up the backend (Sova), frontend (Mura), nginx as an SSL reverse proxy, and systemd services in one command.

## Requirements

- Linux (x86_64 or arm64)
- Root access (`sudo`)
- `wget` or `curl` (not needed for local installs)

nginx will be installed automatically if not already present.

## Quick Install

```bash
wget https://github.com/Parley-Chat/installer/releases/latest/download/install.sh -O install.sh
chmod +x install.sh
sudo ./install.sh
```

With curl:

```bash
curl -fsSL https://github.com/Parley-Chat/installer/releases/latest/download/install.sh -o install.sh
chmod +x install.sh
sudo ./install.sh
```

## Local Install (no internet required)

Download the release archive on any machine, transfer it to your server, extract and run:

```bash
tar xzf parley-install.tar.gz
chmod +x installer-linux-x64   # or installer-linux-arm64
sudo ./installer-linux-x64
```

The installer automatically detects `sova-linux-<arch>` and `mura.zip` in the same directory and uses them instead of downloading anything.

## Using a Mirror

If GitHub is not accessible, you can point the installer to an alternative mirror:

```bash
wget https://your-mirror.com/install.sh -O install.sh
chmod +x install.sh
sudo MIRROR_BASE_URL="https://your-mirror.com" ./install.sh
```

The installer binary and all release files (Sova, Mura) will be fetched from the specified mirror.

## Menu

When the installer runs, you choose from:

```
[I] Install
[U] Update
[M] Modify
[X] Uninstall
```

### Install

For a fresh install, you first choose:

**Recommended** asks only for your domain or IP address, URI prefix, optional instance password, and SSL method, then sets everything up with sensible defaults.

**Custom** lets you configure the HTTPS port, install directory, instance password, thread count, voice calls, and more.

At the end of installation you are asked whether to enable **auto-update** (see below).

### Update

Downloads the latest Sova binary and Mura frontend, replaces them in place, and restarts the backend. Your `config.toml`, certificates, and data are untouched.

Works in local mode too — place the new `sova-linux-<arch>` and `mura.zip` next to the installer before running.

### Modify

Post-install changes without reinstalling:

- **Renew SSL certificate** — re-run the SSL setup flow (same options as during install); updates `nginx.conf` and restarts nginx automatically
- **Enable / Disable auto-update** — toggle the daily update cron job

### Uninstall

Stops and disables all services, removes systemd unit files, and deletes the install directory.

## SSL Options

| Option | When to use |
|--------|-------------|
| Self-signed | IP addresses, private/local instances, or anywhere behind a firewall |
| Let's Encrypt - HTTP | Public domain with port 80 open for the internet. Auto-renews. |
| Let's Encrypt - DNS | Public domain behind a firewall (e.g. Iranian servers). Requires adding a DNS TXT record. Must be renewed manually every 90 days. |

If you enter an IP address instead of a domain, self-signed is used automatically since Let's Encrypt requires a domain name.

## Auto-Update

When installing (online mode only), the installer asks if you want automatic updates. If enabled, you choose the schedule:

| Option | Schedule |
|--------|----------|
| Every 5 minutes | `*/5 * * * *` |
| Every hour | `0 * * * *` |
| Daily at 3 AM | `0 3 * * *` |
| Daily at 4 AM | `0 4 * * *` |
| Custom | enter any cron expression |

The installer writes `auto-update.sh` in the install directory and registers a cron job. Each run fetches `version.txt` from the mirror and compares it to the locally saved `.version` file — it only downloads and restarts if a new version is available. Update output is logged to `/var/log/parley-chat-update.log`.

You can enable or disable auto-update at any time from the **Modify** menu.

## What Gets Installed

| Component | Description |
|-----------|-------------|
| `sova` | Backend binary |
| `mura/` | Frontend static files |
| `config.toml` | Sova configuration |
| `certs/` | Self-signed SSL certificate (10 year validity) |
| `nginx.conf` | nginx reverse proxy config |
| `auto-update.sh` | Auto-update script (if enabled) |
| `.install_info` | Saved settings used by the Modify menu |
| `parley-chat.service` | systemd service for Sova |
| `parley-chat-nginx.service` | systemd service for nginx |

Everything is installed to `/opt/parley-chat` by default (configurable in Custom mode).

## After Installation

The instance will be accessible at `https://<your-domain>:<port>/<uri-prefix>/`.

Your browser will show a certificate warning on the first visit if using a self-signed certificate. Click **Advanced → Proceed** to continue.

## Managing the Services

```bash
# Check status
systemctl status parley-chat
systemctl status parley-chat-nginx

# Restart
systemctl restart parley-chat
systemctl restart parley-chat-nginx

# Stop
systemctl stop parley-chat
systemctl stop parley-chat-nginx
```
