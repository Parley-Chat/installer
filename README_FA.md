# نصب‌کننده پارلی چت

[🇬🇧 English](README.md)

نصب‌کننده خودکار [پارلی چت](https://github.com/Parley-Chat) — بک‌اند (Sova)، فرانت‌اند (Mura)، nginx به عنوان ریورس پروکسی SSL، و سرویس‌های systemd را در یک دستور راه‌اندازی می‌کند.

## پیش‌نیازها

- لینوکس (x86_64 یا arm64)
- دسترسی روت (`sudo`)
- `wget` یا `curl`

اگر nginx نصب نباشد، به صورت خودکار نصب می‌شود.

## نصب سریع

```bash
wget https://github.com/Parley-Chat/installer/releases/latest/download/install.sh -O install.sh
chmod +x install.sh
sudo ./install.sh
```

یا با curl:

```bash
curl -fsSL https://github.com/Parley-Chat/installer/releases/latest/download/install.sh -o install.sh
chmod +x install.sh
sudo ./install.sh
```

## استفاده از آینه (Mirror)

اگر دسترسی به گیت‌هاب ندارید، می‌توانید از یک آینه جایگزین استفاده کنید:

```bash
wget https://آدرس-آینه.com/install.sh -O install.sh
chmod +x install.sh
sudo MIRROR_BASE_URL="https://آدرس-آینه.com" ./install.sh
```

نصب‌کننده و تمام فایل‌های مورد نیاز (Sova، Mura) از آینه مشخص‌شده دانلود می‌شوند.

## حالت‌های نصب

هنگام اجرا، ابتدا از شما پرسیده می‌شود که **نصب (Install)** یا **به‌روزرسانی (Update)** می‌خواهید.

برای نصب جدید، سپس یکی از حالت‌های زیر را انتخاب می‌کنید:

**Recommended (پیشنهادی)** — فقط دامنه یا آی‌پی سرور و نوع SSL را می‌پرسد و بقیه تنظیمات را با مقادیر پیش‌فرض انجام می‌دهد.

**Custom (سفارشی)** — امکان تنظیم پورت HTTPS، مسیر نصب، رمز instance، تعداد threads، تماس صوتی و موارد دیگر را می‌دهد.

## گزینه‌های SSL

| گزینه | کاربرد |
|-------|---------|
| خود-امضا (Self-signed) | آی‌پی، شبکه داخلی، یا هر جایی پشت فایروال |
| Let's Encrypt - HTTP | دامنه عمومی با پورت ۸۰ باز. تمدید خودکار دارد. |
| Let's Encrypt - DNS | دامنه عمومی پشت فایروال (مثل سرورهای ایرانی). نیاز به اضافه کردن یک رکورد TXT در DNS دارد. هر ۹۰ روز باید دستی تمدید شود. |

اگر به جای دامنه، آی‌پی وارد کنید، به صورت خودکار از گواهی خود-امضا استفاده می‌شود چون Let's Encrypt به دامنه نیاز دارد.

## چه چیزی نصب می‌شود

| فایل | توضیح |
|------|-------|
| `sova` | باینری بک‌اند |
| `mura/` | فایل‌های استاتیک فرانت‌اند |
| `config.toml` | تنظیمات Sova |
| `certs/` | گواهی SSL خود-امضا (اعتبار ۱۰ ساله) |
| `nginx.conf` | تنظیمات ریورس پروکسی nginx |
| `parley-chat.service` | سرویس systemd برای Sova |
| `parley-chat-nginx.service` | سرویس systemd برای nginx |

همه چیز به صورت پیش‌فرض در `/opt/parley-chat` نصب می‌شود (در حالت Custom قابل تغییر است).

## به‌روزرسانی

همان نصب‌کننده را اجرا کنید و از منو **Update** را انتخاب کنید:

```bash
sudo MIRROR_BASE_URL="https://آدرس-آینه.com" ./install.sh
# یا بدون آینه:
sudo ./install.sh
```

به‌روزرسانی، آخرین نسخه Sova و فرانت‌اند Mura را دانلود و جایگزین می‌کند و سرویس بک‌اند را ری‌استارت می‌کند. فایل `config.toml`، گواهی‌های SSL و داده‌های شما دست‌نخورده باقی می‌مانند.

## بعد از نصب

نمونه شما از طریق `https://<دامنه-یا-آی‌پی>:<پورت>/` قابل دسترس خواهد بود (پورت پیش‌فرض: `42835`).

در اولین بازدید، مرورگر شما یک هشدار گواهی نامعتبر نشان می‌دهد، چون گواهی SSL خود-امضا است. روی **Advanced ← Proceed** کلیک کنید تا ادامه دهید. این کار فقط یک بار لازم است.

## مدیریت سرویس‌ها

```bash
# بررسی وضعیت
systemctl status parley-chat
systemctl status parley-chat-nginx

# ری‌استارت
systemctl restart parley-chat
systemctl restart parley-chat-nginx

# توقف
systemctl stop parley-chat
systemctl stop parley-chat-nginx
```
