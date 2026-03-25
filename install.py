import os, sys, platform, zipfile, subprocess, urllib.request, datetime, shutil, ipaddress, random
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# Default mirror falls back to GitHub releases if MIRROR_BASE_URL is not set
MIRROR_BASE = os.environ.get("MIRROR_BASE_URL", "https://github.com/Parley-Chat/installer/releases/latest/download")
INTERNAL_PORT = 42836
DEFAULT_INSTALL_DIR = "/opt/parley-chat"

def get_arch():
    m = platform.machine().lower()
    if m in ("x86_64", "amd64"): return "x64"
    if m in ("aarch64", "arm64"): return "arm64"
    print(f"Unsupported architecture: {m}"); sys.exit(1)

def download(url, dest):
    print(f"  Downloading {os.path.basename(dest)}...")
    try:
        urllib.request.urlretrieve(url, dest)
    except Exception as e:
        print(f"  Failed to download {url}: {e}"); sys.exit(1)

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

# Embedded and adapted from Sova's self_ssl.py - generates a self-signed cert for the given domain/IP
def gen_self_signed(cert_file, key_file, domain):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    with open(key_file, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    subject = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, domain)])
    try:
        ip = ipaddress.ip_address(domain)
        san = x509.SubjectAlternativeName([x509.IPAddress(ip)])
    except ValueError:
        san = x509.SubjectAlternativeName([x509.DNSName(domain)])
    cert = (x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))
        .add_extension(san, critical=False)
        .sign(key, hashes.SHA256(), default_backend()))
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

def install_package(name):
    if shutil.which("apt-get"):
        subprocess.run(["apt-get", "install", "-y", name], check=True, capture_output=True)
    elif shutil.which("dnf"):
        subprocess.run(["dnf", "install", "-y", name], check=True, capture_output=True)
    elif shutil.which("yum"):
        subprocess.run(["yum", "install", "-y", name], check=True, capture_output=True)
    elif shutil.which("pacman"):
        subprocess.run(["pacman", "-S", "--noconfirm", name], check=True, capture_output=True)
    else:
        print(f"  Could not detect package manager. Install {name} manually then re-run.")
        sys.exit(1)

def install_nginx():
    if shutil.which("nginx"):
        return
    print("  nginx not found, installing...")
    install_package("nginx")

def install_certbot():
    if shutil.which("certbot"):
        return
    print("  certbot not found, installing...")
    install_package("certbot")

def get_cert_http(domain, email):
    # Uses certbot standalone - port 80 must be free and reachable from the internet
    install_certbot()
    subprocess.run([
        "certbot", "certonly", "--standalone",
        "-d", domain,
        "--non-interactive", "--agree-tos",
        "-m", email,
        "--deploy-hook", "systemctl restart parley-chat-nginx"
    ], check=True)
    return f"/etc/letsencrypt/live/{domain}/fullchain.pem", f"/etc/letsencrypt/live/{domain}/privkey.pem"

def get_cert_dns(domain, email):
    # Interactive - certbot will prompt to add a DNS TXT record
    install_certbot()
    print("\n  certbot will now ask you to add a DNS TXT record to your domain.")
    print("  Follow the instructions on screen and press Enter when the record is added.\n")
    subprocess.run([
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

def write_nginx_conf(conf_path, cert_file, key_file, external_port, sova_host, internal_port):
    # Adapted from Sova's nginx.conf, using sova_host:internal_port instead of Docker service name
    with open(conf_path, "w") as f:
        f.write(f"""events {{
    worker_connections 1024;
}}

http {{
    server {{
        listen {external_port} ssl http2;

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
        }}
    }}
}}""")

def write_sova_config(path, sova_host, internal_port, instance_password, invite, threads, calls):
    with open(path, "w") as f:
        f.write(f"""version=6

uri_prefix=""
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
    frontend_directory="./mura"
[max_members]
    encrypted_channels=100
    max_channels=50
[data_dir]
    pfps="./data/pfps"
    attachments="./data/attachments"
    database="./data/parley-chat.db"
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

def do_install():
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

    external_port = random.randint(10000, 49151)
    internal_port = INTERNAL_PORT
    sova_host = "127.0.0.1"
    install_dir = DEFAULT_INSTALL_DIR
    instance_password = ""
    invite = ""
    threads = 32
    calls = True

    if custom:
        external_port = int(ask("nginx HTTPS port", str(external_port)))
        internal_port = int(ask("Sova internal port", str(internal_port)))
        sova_host = ask("Sova bind host", sova_host)
        install_dir = ask("Install directory", DEFAULT_INSTALL_DIR)
        instance_password = ask("Instance password (empty = none)", "")
        invite = ask("Auto-invite channel ID (empty = none)", "")
        threads = int(ask("Threads", "32"))
        calls = ask("Enable voice calls? [Y/n]", "y").lower() != "n"

    arch = get_arch()
    nginx_conf = f"{install_dir}/nginx.conf"

    print(f"\nInstalling to {install_dir} on port {external_port}...\n")
    for d in [install_dir, f"{install_dir}/certs", f"{install_dir}/data/pfps", f"{install_dir}/data/attachments"]:
        os.makedirs(d, exist_ok=True)

    download(f"{MIRROR_BASE}/sova-linux-{arch}", f"{install_dir}/sova")
    os.chmod(f"{install_dir}/sova", 0o755)

    mura_zip = f"{install_dir}/mura.zip"
    download(f"{MIRROR_BASE}/mura.zip", mura_zip)
    print("  Extracting frontend...")
    os.makedirs(f"{install_dir}/mura", exist_ok=True)
    with zipfile.ZipFile(mura_zip, "r") as z:
        z.extractall(f"{install_dir}/mura")
    os.remove(mura_zip)

    print("  Setting up SSL...")
    cert_file, key_file, ssl_type = setup_ssl(domain, install_dir)

    print("  Writing config...")
    write_sova_config(f"{install_dir}/config.toml", sova_host, internal_port, instance_password, invite, threads, calls)

    print("  Setting up nginx...")
    install_nginx()
    write_nginx_conf(nginx_conf, cert_file, key_file, external_port, sova_host, internal_port)

    print("  Writing systemd services...")
    write_service("parley-chat", "Parley Chat", install_dir, f"{install_dir}/sova")
    write_service("parley-chat-nginx", "Parley Chat nginx", install_dir, f"/usr/sbin/nginx -c {nginx_conf} -g 'daemon off;'")

    print("  Starting services...")
    subprocess.run(["systemctl", "daemon-reload"])
    for svc in ["parley-chat", "parley-chat-nginx"]:
        subprocess.run(["systemctl", "enable", svc])
        subprocess.run(["systemctl", "start", svc])

    print(f"\nParley Chat is running at https://{domain}:{external_port}/")
    if ssl_type == "self-signed":
        print("Your browser will show a certificate warning - click Advanced -> Proceed to continue.")
    elif ssl_type == "letsencrypt-dns":
        print("Note: DNS-verified certificates must be renewed manually every 90 days.")
        print("To renew: certbot renew --manual --preferred-challenges dns")
        print("Then restart nginx: systemctl restart parley-chat-nginx")

def do_update():
    print()
    install_dir = ask("Install directory", DEFAULT_INSTALL_DIR)
    if not os.path.exists(f"{install_dir}/sova"):
        print(f"No installation found at {install_dir}."); sys.exit(1)

    arch = get_arch()

    print("\nUpdating Parley Chat...\n")
    subprocess.run(["systemctl", "stop", "parley-chat"])

    download(f"{MIRROR_BASE}/sova-linux-{arch}", f"{install_dir}/sova")
    os.chmod(f"{install_dir}/sova", 0o755)

    mura_zip = f"{install_dir}/mura.zip"
    download(f"{MIRROR_BASE}/mura.zip", mura_zip)
    print("  Extracting frontend...")
    shutil.rmtree(f"{install_dir}/mura", ignore_errors=True)
    os.makedirs(f"{install_dir}/mura", exist_ok=True)
    with zipfile.ZipFile(mura_zip, "r") as z:
        z.extractall(f"{install_dir}/mura")
    os.remove(mura_zip)

    subprocess.run(["systemctl", "start", "parley-chat"])
    print("\nParley Chat updated successfully.")

def main():
    print("\n=== Parley Chat Installer ===\n")
    if os.geteuid() != 0:
        print("Please run as root (sudo).")
        sys.exit(1)

    print("[I] Install")
    print("[U] Update\n")
    action = input("> ").strip().lower()
    if action == "i":
        do_install()
    elif action == "u":
        do_update()
    else:
        print("Invalid choice."); sys.exit(1)

if __name__ == "__main__":
    main()
