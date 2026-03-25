# Parley Chat Installer

[🇮🇷 فارسی](README.fa.md) | [🇪🇸 Español](README.es-es.md)

Automated installer for [Parley Chat](https://github.com/Parley-Chat). Sets up the backend (Sova), frontend (Mura), nginx as an SSL reverse proxy, and systemd services in one command.

## Requirements

- Linux (x86_64 or arm64)
- Root access (`sudo`)
- `wget` or `curl`

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

## Using a Mirror

If GitHub is not accessible, you can point the installer to an alternative mirror:

```bash
wget https://your-mirror.com/install.sh -O install.sh
chmod +x install.sh
sudo MIRROR_BASE_URL="https://your-mirror.com" ./install.sh
```

The installer binary and all release files (Sova, Mura) will be fetched from the specified mirror.

## Installation Modes

When the installer runs, you will first be asked whether to **Install** or **Update**.

For a fresh install, you then choose:

**Recommended** asks only for your domain or IP address and SSL method, then sets everything up with sensible defaults.

**Custom** lets you configure the HTTPS port, install directory, instance password, thread count, voice calls, and more.

## SSL Options

| Option | When to use |
|--------|-------------|
| Self-signed | IP addresses, private/local instances, or anywhere behind a firewall |
| Let's Encrypt - HTTP | Public domain with port 80 open for the internet. Auto-renews. |
| Let's Encrypt - DNS | Public domain behind a firewall (e.g. Iranian servers). Requires adding a DNS TXT record. Must be renewed manually every 90 days. |

If you enter an IP address instead of a domain, self-signed is used automatically since Let's Encrypt requires a domain name.

## What Gets Installed

| Component | Description |
|-----------|-------------|
| `sova` | Backend binary |
| `mura/` | Frontend static files |
| `config.toml` | Sova configuration |
| `certs/` | Self-signed SSL certificate (10 year validity) |
| `nginx.conf` | nginx reverse proxy config |
| `parley-chat.service` | systemd service for Sova |
| `parley-chat-nginx.service` | systemd service for nginx |

Everything is installed to `/opt/parley-chat` by default (configurable in Custom mode).

## Updating

Run the same installer and choose **Update** from the menu:

```bash
sudo MIRROR_BASE_URL="https://your-mirror.com" ./install.sh
# or without a custom mirror:
sudo ./install.sh
```

The update downloads the latest Sova binary and Mura frontend, replaces them in place, and restarts the backend. Your `config.toml`, certificates, and data are untouched.

## After Installation

The instance will be accessible at `https://<your-domain>:<port>/` (default port: `42835`).

Your browser will show a certificate warning on the first visit since the certificate is self-signed. Click **Advanced → Proceed** to continue. This is expected and only needs to be done once per browser.

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
