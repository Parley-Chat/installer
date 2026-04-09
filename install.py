import os, sys, platform, zipfile, subprocess, urllib.request, shutil, ipaddress, random, string

# Default mirror falls back to GitHub releases if MIRROR_BASE_URL is not set
MIRROR_BASE = os.environ.get("MIRROR_BASE_URL", "https://github.com/Parley-Chat/installer/releases/latest/download")
INTERNAL_PORT = 42836
DEFAULT_INSTALL_DIR = "/opt/parley-chat"

def system_env():
    # PyInstaller overrides LD_LIBRARY_PATH with its temp dir, which breaks system binaries
    # (e.g. openssl loads the wrong libcrypto.so). Restore the original value before any
    # subprocess call that invokes a system binary.
    env = os.environ.copy()
    orig = env.pop("LD_LIBRARY_PATH_ORIG", None)
    if orig is not None:
        env["LD_LIBRARY_PATH"] = orig
    else:
        env.pop("LD_LIBRARY_PATH", None)
    return env

_real_run = subprocess.run

def sysrun(*args, **kwargs):
    kwargs.setdefault("env", system_env())
    return _real_run(*args, **kwargs)

def get_arch():
    m = platform.machine().lower()
    if m in ("x86_64", "amd64"): return "x64"
    if m in ("aarch64", "arm64"): return "arm64"
    print(f"Unsupported architecture: {m}"); sys.exit(1)

def download(url, dest):
    filename = os.path.basename(dest)
    large = [False]
    def reporthook(count, block_size, total_size):
        if total_size < 1024 * 1024:
            return
        large[0] = True
        downloaded = min(count * block_size, total_size)
        pct = downloaded * 100 // total_size
        filled = pct * 25 // 100
        bar = "=" * filled + (">" if filled < 25 else "") + " " * max(24 - filled, 0)
        print(f"\r  Downloading {filename}... {pct:3d}% [{bar}] {downloaded/1048576:.1f}/{total_size/1048576:.1f} MB", end="", flush=True)
    print(f"  Downloading {filename}...", end="", flush=True)
    try:
        urllib.request.urlretrieve(url, dest, reporthook)
        print()
    except Exception as e:
        print(f"\n  Failed to download {url}: {e}"); sys.exit(1)

def ask(prompt, default=None):
    d = f" [{default}]" if default is not None else ""
    val = input(f"{prompt}{d}: ").strip()
    return val if val else default

def is_ip(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False

def random_prefix():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=20))

def install_openssl():
    if shutil.which("openssl"):
        return
    print("  openssl not found, installing...")
    install_package("openssl")

# Uses openssl CLI instead of the cryptography library to keep the installer binary small.
# Uses a temp config file for SAN support instead of -addext (works on all OpenSSL versions).
def gen_self_signed(cert_file, key_file, domain):
    import tempfile
    try:
        ip = ipaddress.ip_address(domain)
        san = f"IP:{ip}"
    except ValueError:
        san = f"DNS:{domain}"
    install_openssl()
    cfg = f"[req]\ndistinguished_name=req_dn\nx509_extensions=san_ext\nprompt=no\n[req_dn]\nCN={domain}\n[san_ext]\nsubjectAltName={san}\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cnf", delete=False) as f:
        f.write(cfg)
        cfg_path = f.name
    try:
        sysrun([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", key_file, "-out", cert_file,
            "-days", "3650", "-nodes", "-config", cfg_path
        ], check=True, capture_output=True)
    finally:
        os.unlink(cfg_path)

def nginx_installed():
    return (shutil.which("nginx") or os.path.exists("/usr/sbin/nginx") or os.path.exists("/usr/bin/nginx"))

def install_package(name):
    if shutil.which("apt-get"):
        sysrun(["apt-get", "update", "-qq"], capture_output=True)
        sysrun(["apt-get", "install", "-y", name], check=True, capture_output=True)
    elif shutil.which("dnf"):
        sysrun(["dnf", "install", "-y", name], check=True, capture_output=True)
    elif shutil.which("yum"):
        sysrun(["yum", "install", "-y", name], check=True, capture_output=True)
    elif shutil.which("pacman"):
        sysrun(["pacman", "-S", "--noconfirm", name], check=True, capture_output=True)
    else:
        print(f"  Could not detect package manager. Install {name} manually then re-run.")
        sys.exit(1)

def install_nginx():
    if nginx_installed():
        return
    print("  nginx not found, installing...")
    install_package("nginx")

def install_certbot():
    if shutil.which("certbot"):
        return
    print("  certbot not found, installing...")
    install_package("certbot")

def setup_renewal_cron():
    # Adds a twice-daily cron job to renew certificates.
    # Pre/post hooks stop and restart system nginx (port 80) so certbot standalone can bind to it.
    # Deploy hook restarts parley-chat-nginx to pick up the new certificate.
    cron_job = (
        "0 0,12 * * * /usr/bin/certbot renew --quiet"
        " --pre-hook \"systemctl stop nginx 2>/dev/null || true\""
        " --post-hook \"systemctl start nginx 2>/dev/null || true\""
        " --deploy-hook \"systemctl restart parley-chat-nginx\""
    )
    existing = sysrun(["crontab", "-l"], capture_output=True, text=True).stdout
    if "certbot renew" not in existing:
        sysrun(["crontab", "-"], input=existing.rstrip() + "\n" + cron_job + "\n", text=True, check=True)

def get_cert_http(domain, email):
    # Uses certbot standalone - port 80 must be free and reachable from the internet
    install_certbot()
    sysrun([
        "certbot", "certonly", "--standalone",
        "-d", domain,
        "--non-interactive", "--agree-tos",
        "-m", email
    ], check=True)
    setup_renewal_cron()
    return f"/etc/letsencrypt/live/{domain}/fullchain.pem", f"/etc/letsencrypt/live/{domain}/privkey.pem"

def get_cert_dns(domain, email):
    # Interactive - certbot will prompt to add a DNS TXT record
    install_certbot()
    print("\n  certbot will now ask you to add a DNS TXT record to your domain.")
    print("  Follow the instructions on screen and press Enter when the record is added.\n")
    sysrun([
        "certbot", "certonly", "--manual",
        "--preferred-challenges", "dns",
        "-d", domain,
        "--agree-tos",
        "-m", email
    ], check=True)
    return f"/etc/letsencrypt/live/{domain}/fullchain.pem", f"/etc/letsencrypt/live/{domain}/privkey.pem"

def setup_ssl(domain, install_dir):
    # Returns (cert_file, key_file, ssl_type)
    if is_ip(domain):
        # Let's Encrypt requires a domain name, not an IP
        print("  IP address detected - using self-signed certificate.")
        cert_file = f"{install_dir}/certs/cert.pem"
        key_file = f"{install_dir}/certs/key.pem"
        gen_self_signed(cert_file, key_file, domain)
        return cert_file, key_file, "self-signed"

    print("\nSSL Certificate:")
    print("[1] Self-signed (works everywhere, browser warning on first visit)")
    print("[2] Let's Encrypt - HTTP verification (port 80 must be open from internet, auto-renews)")
    print("[3] Let's Encrypt - DNS verification (works behind firewall, requires adding a DNS TXT record)\n")
    ssl_choice = input("> ").strip()

    if ssl_choice == "2":
        email = ask("Email address for Let's Encrypt notifications")
        cert_file, key_file = get_cert_http(domain, email)
        return cert_file, key_file, "letsencrypt-http"
    elif ssl_choice == "3":
        email = ask("Email address for Let's Encrypt notifications")
        cert_file, key_file = get_cert_dns(domain, email)
        return cert_file, key_file, "letsencrypt-dns"
    else:
        cert_file = f"{install_dir}/certs/cert.pem"
        key_file = f"{install_dir}/certs/key.pem"
        gen_self_signed(cert_file, key_file, domain)
        return cert_file, key_file, "self-signed"

def write_nginx_conf(conf_path, cert_file, key_file, domain, external_port, sova_host, internal_port):
    with open(conf_path, "w") as f:
        f.write(f"""events {{
    worker_connections 1024;
}}

http {{
    map $http_host $browser_authority {{
        default $http_host;
        ""      $host;
    }}
    server {{
        listen {external_port} ssl http2;
        server_name {domain};

        ssl_certificate {cert_file};
        ssl_certificate_key {key_file};
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        error_page 497 @handle_plain_http;
        location @handle_plain_http {{
            return 301 https://$host:{external_port}$request_uri;
        }}

        location / {{
            proxy_pass http://{sova_host}:{internal_port};
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "keep-alive";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache off;
            proxy_buffering off;
            proxy_read_timeout 24h;
            proxy_send_timeout 24h;
            client_max_body_size 64M;
            proxy_redirect ~^https?://[^/]+(.*)$ $scheme://$browser_authority$1;
        }}
    }}
}}""")

def write_sova_config(path, install_dir, sova_host, internal_port, instance_password, invite, threads, calls, uri_prefix):
    with open(path, "w") as f:
        f.write(f"""version=6

uri_prefix="{uri_prefix}"
[server]
    host="{sova_host}"
    port={internal_port}
    dev=false
    threads={threads}
    max_content_length=67108864
    proxy=true
[frontend]
    hosted=true
    excluded_frontend_root_paths=["README.md", "LICENSE.md", ".nojekyll", "400.html", "404.html", "405.html", "413.html", "415.html", "500.html", ".git", "quickrun.js"]
    frontend_directory="{install_dir}/mura"
[max_members]
    encrypted_channels=100
    max_channels=50
[data_dir]
    pfps="{install_dir}/data/pfps"
    attachments="{install_dir}/data/attachments"
    database="{install_dir}/data/parley-chat.db"
[max_file_size]
    pfps=1048576
    attachments=15728640
[messages]
    max_message_length=2000
    max_attachments=4
    signature_timestamp_window=60
[instance]
    password="{instance_password}"
    invite="{invite}"
    disable_channel_creation=false
    disable_channel_deletion=false
[calls]
    enabled={"true" if calls else "false"}
    stun_servers=["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302", "stun:stun2.l.google.com:19302", "stun:stun3.l.google.com:19302", "stun:stun4.l.google.com:19302", "stun:stun.ekiga.net:3478", "stun:stun.services.mozilla.com:3478", "stun:stun.stunprotocol.org:3478", "stun:stun.ideasip.com:3478", "stun:freestun.net:3478", "stun:stun.nextcloud.com:3478"]
    turn_servers=["turn:openrelay.metered.ca:80", "turn:openrelay.metered.ca:443"]
    turn_username="openrelayproject"
    turn_password="openrelayproject"
""")

def write_service(name, description, working_dir, exec_start):
    with open(f"/etc/systemd/system/{name}.service", "w") as f:
        f.write(f"""[Unit]
Description={description}
After=network.target

[Service]
Type=simple
WorkingDirectory={working_dir}
ExecStart={exec_start}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")

def installer_dir():
    # Returns the directory containing the installer binary/script
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def is_local_mode():
    # Local mode: sova binary and mura.zip are present next to the installer
    d = installer_dir()
    arch = get_arch()
    return os.path.exists(f"{d}/sova-linux-{arch}") and os.path.exists(f"{d}/mura.zip")

def get_or_copy(url, dest, local_src):
    # Use local file if it exists, otherwise download from mirror
    if local_src and os.path.exists(local_src):
        print(f"  Copying {os.path.basename(dest)} from local archive...")
        shutil.copy2(local_src, dest)
    else:
        download(url, dest)

def read_install_info(install_dir):
    path = f"{install_dir}/.install_info"
    if not os.path.exists(path):
        return {}
    info = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                info[k] = v
    return info

def write_install_info(install_dir, info):
    with open(f"{install_dir}/.install_info", "w") as f:
        for k, v in info.items():
            f.write(f"{k}={v}\n")

def save_installed_version(install_dir, mirror):
    # Fetches version.txt from the mirror and saves it to .version
    try:
        with urllib.request.urlopen(f"{mirror}/version.txt") as r:
            version = r.read().decode().strip()
        with open(f"{install_dir}/.version", "w") as f:
            f.write(version + "\n")
    except Exception:
        pass

def write_auto_update_script(install_dir, mirror, arch):
    # Writes a self-contained shell script that checks for a new version and updates if needed
    script_path = f"{install_dir}/auto-update.sh"
    with open(script_path, "w") as f:
        f.write(f"""#!/bin/bash
set -e
MIRROR="{mirror}"
ARCH="{arch}"
INSTALL_DIR="{install_dir}"
VERSION_FILE="$INSTALL_DIR/.version"
if command -v wget &>/dev/null; then
    REMOTE_VERSION=$(wget -qO- "$MIRROR/version.txt" 2>/dev/null || true)
elif command -v curl &>/dev/null; then
    REMOTE_VERSION=$(curl -fsSL "$MIRROR/version.txt" 2>/dev/null || true)
else
    echo "Neither wget nor curl found"; exit 1
fi
LOCAL_VERSION=$(cat "$VERSION_FILE" 2>/dev/null || true)
if [ -z "$REMOTE_VERSION" ] || [ "$LOCAL_VERSION" = "$REMOTE_VERSION" ]; then
    exit 0
fi
echo "Updating from $LOCAL_VERSION to $REMOTE_VERSION"
systemctl stop parley-chat
if command -v wget &>/dev/null; then
    wget -q -O "$INSTALL_DIR/sova.new" "$MIRROR/sova-linux-$ARCH"
    wget -q -O "$INSTALL_DIR/mura.zip" "$MIRROR/mura.zip"
else
    curl -fsSL "$MIRROR/sova-linux-$ARCH" -o "$INSTALL_DIR/sova.new"
    curl -fsSL "$MIRROR/mura.zip" -o "$INSTALL_DIR/mura.zip"
fi
chmod +x "$INSTALL_DIR/sova.new"
mv "$INSTALL_DIR/sova.new" "$INSTALL_DIR/sova"
rm -rf "$INSTALL_DIR/mura"
mkdir -p "$INSTALL_DIR/mura"
unzip -q "$INSTALL_DIR/mura.zip" -d "$INSTALL_DIR/mura"
rm "$INSTALL_DIR/mura.zip"
echo "$REMOTE_VERSION" > "$VERSION_FILE"
systemctl start parley-chat
""")
    os.chmod(script_path, 0o755)
    return script_path

def ask_auto_update_schedule():
    # Returns (cron_expr, label) for the chosen update schedule
    print("\nAuto-update schedule:")
    print("[1] Every 5 minutes")
    print("[2] Every hour")
    print("[3] Daily at 3 AM")
    print("[4] Daily at 4 AM")
    print("[5] Custom (enter cron expression)\n")
    choice = input("> ").strip()
    if choice == "1": return "*/5 * * * *", "every 5 minutes"
    if choice == "2": return "0 * * * *", "every hour"
    if choice == "4": return "0 4 * * *", "daily at 4 AM"
    if choice == "5":
        expr = ask("Cron expression (e.g. '0 2 * * *' for daily at 2 AM)")
        return expr, f"on schedule '{expr}'"
    return "0 3 * * *", "daily at 3 AM"

def setup_auto_update_cron(script_path, cron_expr):
    # Installs the update cron job with the given schedule
    cron_job = f"{cron_expr} {script_path} >> /var/log/parley-chat-update.log 2>&1"
    existing = sysrun(["crontab", "-l"], capture_output=True, text=True).stdout
    if script_path not in existing:
        sysrun(["crontab", "-"], input=existing.rstrip() + "\n" + cron_job + "\n", text=True, check=True)

def remove_auto_update_cron(install_dir):
    script_path = f"{install_dir}/auto-update.sh"
    existing = sysrun(["crontab", "-l"], capture_output=True, text=True).stdout
    lines = [l for l in existing.splitlines() if script_path not in l]
    sysrun(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)

def do_install():
    local = is_local_mode()
    if local:
        print("\n[Local mode] Using bundled files from archive.\n")

    print("\n[R] Recommended - quick setup with defaults")
    print("[C] Custom      - configure everything\n")
    mode = input("> ").strip().lower()
    if mode not in ("r", "c"):
        print("Invalid choice."); sys.exit(1)
    custom = (mode == "c")

    print()
    domain = ask("Domain or IP address")
    if not domain:
        print("Domain/IP is required."); sys.exit(1)

    uri_prefix = random_prefix()
    uri_prefix = ask("URI path prefix", uri_prefix)

    external_port = random.randint(10000, 49151)
    internal_port = INTERNAL_PORT
    use_nginx = True
    sova_host = "127.0.0.1"
    install_dir = DEFAULT_INSTALL_DIR
    instance_password = ""
    invite = ""
    threads = 32
    calls = False

    if custom:
        use_nginx = ask("Use built-in nginx reverse proxy? [Y/n]", "y").lower() != "n"
        sova_host = "127.0.0.1" if use_nginx else "0.0.0.0"
        if use_nginx:
            external_port = int(ask("nginx HTTPS port", str(external_port)))
            internal_port = int(ask("Sova internal port", str(internal_port)))
            sova_host = ask("Sova bind host", sova_host)
        else:
            external_port = int(ask("Sova port", str(external_port)))
            sova_host = ask("Sova bind host", sova_host)
        install_dir = ask("Install directory", DEFAULT_INSTALL_DIR)
        instance_password = ask("Instance password (empty = none)", "")
        invite = ask("Auto-invite channel ID (empty = none)", "")
        threads = int(ask("Threads", "32"))
        calls = ask("Enable voice calls? [y/N]", "n").lower() == "y"
    else:
        instance_password = ask("Instance password (empty = none)", "")

    # Auto-update is only available when a mirror is reachable (not local mode)
    auto_update = False
    if not local:
        auto_update = ask("Enable automatic daily updates? [y/N]", "n").lower() == "y"

    arch = get_arch()

    print(f"\nInstalling to {install_dir} on port {external_port}...\n")
    for d in [install_dir, f"{install_dir}/certs", f"{install_dir}/data/pfps", f"{install_dir}/data/attachments"]:
        os.makedirs(d, exist_ok=True)

    local_dir = installer_dir() if local else None
    get_or_copy(f"{MIRROR_BASE}/sova-linux-{arch}", f"{install_dir}/sova", local_dir and f"{local_dir}/sova-linux-{arch}")
    os.chmod(f"{install_dir}/sova", 0o755)

    mura_zip = f"{install_dir}/mura.zip"
    get_or_copy(f"{MIRROR_BASE}/mura.zip", mura_zip, local_dir and f"{local_dir}/mura.zip")
    print("  Extracting frontend...")
    os.makedirs(f"{install_dir}/mura", exist_ok=True)
    with zipfile.ZipFile(mura_zip, "r") as z:
        z.extractall(f"{install_dir}/mura")
    os.remove(mura_zip)

    sova_port = internal_port if use_nginx else external_port

    if use_nginx:
        print("  Setting up SSL...")
        cert_file, key_file, ssl_type = setup_ssl(domain, install_dir)

    print("  Writing config...")
    write_sova_config(f"{install_dir}/config.toml", install_dir, sova_host, sova_port, instance_password, invite, threads, calls, uri_prefix)

    print("  Writing systemd service...")
    write_service("parley-chat", "Parley Chat", install_dir, f"{install_dir}/sova")

    if use_nginx:
        nginx_conf = f"{install_dir}/nginx.conf"
        print("  Setting up nginx...")
        install_nginx()
        write_nginx_conf(nginx_conf, cert_file, key_file, domain, external_port, sova_host, internal_port)
        write_service("parley-chat-nginx", "Parley Chat nginx", install_dir, f"/usr/sbin/nginx -c {nginx_conf} -g 'daemon off;'")

    auto_update_schedule = "0 3 * * *"
    auto_update_schedule_label = "daily at 3 AM"
    if not local:
        save_installed_version(install_dir, MIRROR_BASE)

    if auto_update:
        print("  Setting up auto-update...")
        auto_update_schedule, auto_update_schedule_label = ask_auto_update_schedule()
        script_path = write_auto_update_script(install_dir, MIRROR_BASE, arch)
        setup_auto_update_cron(script_path, auto_update_schedule)

    write_install_info(install_dir, {
        "domain": domain,
        "external_port": str(external_port),
        "internal_port": str(internal_port),
        "sova_host": sova_host,
        "use_nginx": str(use_nginx).lower(),
        "ssl_type": ssl_type if use_nginx else "none",
        "mirror": MIRROR_BASE,
        "auto_update": str(auto_update).lower(),
        "auto_update_schedule": auto_update_schedule,
    })

    print("  Starting services...")
    sysrun(["systemctl", "daemon-reload"])
    services = ["parley-chat", "parley-chat-nginx"] if use_nginx else ["parley-chat"]
    for svc in services:
        sysrun(["systemctl", "enable", svc])
        sysrun(["systemctl", "start", svc])

    if use_nginx:
        print(f"\nParley Chat is running at https://{domain}:{external_port}/{uri_prefix}/")
        if ssl_type == "self-signed":
            print("Your browser will show a certificate warning - click Advanced -> Proceed to continue.")
        elif ssl_type == "letsencrypt-dns":
            print("Note: DNS-verified certificates must be renewed manually every 90 days.")
            print("To renew: certbot renew --manual --preferred-challenges dns")
            print("Then restart nginx: systemctl restart parley-chat-nginx")
    else:
        print(f"\nParley Chat backend is running on {sova_host}:{external_port}/")
        print("Point your external reverse proxy to this address.")
        print("Make sure your proxy sets X-Forwarded-Proto and X-Real-IP headers.")

    if auto_update:
        print(f"Auto-update is enabled and will run {auto_update_schedule_label}.")

def do_update():
    local = is_local_mode()
    if local:
        print("\n[Local mode] Using bundled files from archive.\n")

    print()
    install_dir = ask("Install directory", DEFAULT_INSTALL_DIR)
    if not os.path.exists(f"{install_dir}/sova"):
        print(f"No installation found at {install_dir}."); sys.exit(1)

    arch = get_arch()

    print("\nUpdating Parley Chat...\n")
    sysrun(["systemctl", "stop", "parley-chat"])

    local_dir = installer_dir() if local else None
    get_or_copy(f"{MIRROR_BASE}/sova-linux-{arch}", f"{install_dir}/sova", local_dir and f"{local_dir}/sova-linux-{arch}")
    os.chmod(f"{install_dir}/sova", 0o755)

    mura_zip = f"{install_dir}/mura.zip"
    get_or_copy(f"{MIRROR_BASE}/mura.zip", mura_zip, local_dir and f"{local_dir}/mura.zip")
    print("  Extracting frontend...")
    shutil.rmtree(f"{install_dir}/mura", ignore_errors=True)
    os.makedirs(f"{install_dir}/mura", exist_ok=True)
    with zipfile.ZipFile(mura_zip, "r") as z:
        z.extractall(f"{install_dir}/mura")
    os.remove(mura_zip)

    if not local:
        save_installed_version(install_dir, MIRROR_BASE)

    sysrun(["systemctl", "start", "parley-chat"])
    print("\nParley Chat updated successfully.")

def do_uninstall():
    print()
    install_dir = ask("Install directory", DEFAULT_INSTALL_DIR)
    if not os.path.exists(f"{install_dir}/sova"):
        print(f"No installation found at {install_dir}."); sys.exit(1)

    confirm = ask(f"This will permanently remove {install_dir} and all its contents. Type 'yes' to confirm")
    if confirm != "yes":
        print("Cancelled."); sys.exit(0)

    print("\nUninstalling Parley Chat...\n")

    for svc in ["parley-chat-nginx", "parley-chat"]:
        sysrun(["systemctl", "stop", svc], capture_output=True)
        sysrun(["systemctl", "disable", svc], capture_output=True)

    for f in ["/etc/systemd/system/parley-chat.service", "/etc/systemd/system/parley-chat-nginx.service"]:
        if os.path.exists(f):
            os.remove(f)

    sysrun(["systemctl", "daemon-reload"])
    shutil.rmtree(install_dir)

    print("Parley Chat has been uninstalled.")
    print("Note: if a certbot renewal cron job was added, remove it manually with: crontab -e")

def do_modify():
    print()
    install_dir = ask("Install directory", DEFAULT_INSTALL_DIR)
    if not os.path.exists(f"{install_dir}/sova"):
        print(f"No installation found at {install_dir}."); sys.exit(1)

    info = read_install_info(install_dir)
    use_nginx = info.get("use_nginx", "true") == "true"
    auto_update_enabled = info.get("auto_update", "false") == "true"

    print("\n[C] Renew SSL certificate")
    print(f"[A] {'Disable' if auto_update_enabled else 'Enable'} auto-update")
    print()
    choice = input("> ").strip().lower()

    if choice == "c":
        if not use_nginx:
            print("nginx is not in use - no certificate to renew."); sys.exit(1)
        domain = info.get("domain") or ask("Domain or IP address")
        cert_file, key_file, ssl_type = setup_ssl(domain, install_dir)
        nginx_conf = f"{install_dir}/nginx.conf"
        external_port = int(info.get("external_port", 443))
        sova_host = info.get("sova_host", "127.0.0.1")
        internal_port = int(info.get("internal_port", str(INTERNAL_PORT)))
        write_nginx_conf(nginx_conf, cert_file, key_file, domain, external_port, sova_host, internal_port)
        sysrun(["systemctl", "restart", "parley-chat-nginx"])
        info["ssl_type"] = ssl_type
        write_install_info(install_dir, info)
        print("\nCertificate updated and nginx restarted.")
    elif choice == "a":
        if auto_update_enabled:
            remove_auto_update_cron(install_dir)
            info["auto_update"] = "false"
            write_install_info(install_dir, info)
            print("\nAuto-update disabled.")
        else:
            arch = get_arch()
            mirror = info.get("mirror", MIRROR_BASE)
            cron_expr, schedule_label = ask_auto_update_schedule()
            script_path = write_auto_update_script(install_dir, mirror, arch)
            setup_auto_update_cron(script_path, cron_expr)
            info["auto_update"] = "true"
            info["auto_update_schedule"] = cron_expr
            write_install_info(install_dir, info)
            print(f"\nAuto-update enabled ({schedule_label}).")
    else:
        print("Invalid choice."); sys.exit(1)

def main():
    print("\n=== Parley Chat Installer ===\n")
    if os.geteuid() != 0:
        print("Please run as root (sudo).")
        sys.exit(1)

    print("[I] Install")
    print("[U] Update")
    print("[M] Modify")
    print("[X] Uninstall\n")
    action = input("> ").strip().lower()
    if action == "i":
        do_install()
    elif action == "u":
        do_update()
    elif action == "m":
        do_modify()
    elif action == "x":
        do_uninstall()
    else:
        print("Invalid choice."); sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
