# Parley Chat Instalador

[🇬🇧 English](README.md) | [🇮🇷 فارسی](README.fa.md)

Instalador automático para [Parley Chat](https://github.com/Parley-Chat). Configura el backend (Sova), el frontend (Mura), nginx como proxy inversa de SSL y los servicios de systemd con un solo comando.

## Requisitos

- Linux (x86_64 o arm64)
- Acceso root (`sudo`)
- `wget` o `curl`

nginx se instalará automáticamente si no está presente.

## Instalación Rápida

```bash
wget https://github.com/Parley-Chat/installer/releases/latest/download/install.sh -O install.sh
chmod +x install.sh
sudo ./install.sh
```

Con curl:

```bash
curl -fsSL https://github.com/Parley-Chat/installer/releases/latest/download/install.sh -o install.sh
chmod +x install.sh
sudo ./install.sh
```

## Usar un Espejo

Si GitHub no es accesible, puedes apuntar el instalador a un espejo alternativo:

```bash
wget https://tu-espejo.com/install.sh -O install.sh
chmod +x install.sh
sudo MIRROR_BASE_URL="https://tu-espejo.com" ./install.sh
```

El binario del instalador y todos los archivos (Sova, Mura) se descargarán desde el espejo especificado.

## Modos de Instalación

Cuando se ejecute el instalador, se te preguntará primero si deseas **Instalar (Install)** o **Actualizar (Update)**.

Para una instalación nueva, debes seleccionar:

**Recomendado (Recommended)** solo te pide tu dominio o dirección IP y el método SSL, y luego lo configura todo con unos valores predeterminados razonables.

**Personalizado (Custom)** te permite configurar el puerto HTTPS, directorio de instalación, contraseña de instancia, número de subprocesos, llamadas de voz y más.

## SSL Options

| Opción | Cuándo usar |
|--------|-------------|
| Autofirmado (Self-signed) | Direcciones IP, instancias privadas/locales o cualquier lugar protegido por un cortafuegos |
| Let's Encrypt - HTTP | Dominio público con puerto 80 abierto para Internet. Se renueva automáticamente. |
| Let's Encrypt - DNS | Dominio público protegido por cortafuegos (por ejemplo servidores iraníes). Requiere añadir un récord DNS TXT. Debe renovarse manualmente cada 90 días. |

Si introduces una dirección IP en lugar de un dominio, se utiliza automáticamente un certificado autofirmado, ya que Let's Encrypt requiere un nombre de dominio.

## Qué se Instala

| Componente | Descripción |
|------------|-------------|
| `sova` | Binario del backend |
| `mura/` | Archivos estáticos del frontend |
| `config.toml` | Configuración de Sova |
| `certs/` | Certificado SSL autofirmado (10 años de validez) |
| `nginx.conf` | Configuración de la proxy inversa de nginx |
| `parley-chat.service` | Servicio systemd para Sova |
| `parley-chat-nginx.service` | Servicio systemd para Nginx |

Por defecto, todo se instala en `/opt/parley-chat` (configurable en el modo Custom).

## Actualizaciónes

Ejecuta el mismo instalador y selecciona **Actualizar (Update)** en el menú:

```bash
sudo MIRROR_BASE_URL="https://tu-espejo.com" ./install.sh
# o sin el espejo:
sudo ./install.sh
```

La actualización descarga la última versión del binario de Sova y del frontend de Mura, los sustituye en el lugar y reinicia el backend. Tu archivo `config.toml`, los certificados y los datos no son afectados.

## Después de la Instalación

La instancia será accesible en `https://<tu-dominio>:<puerto>/` (puerto predeterminado: `42835`).

Tu navegador mostrará una advertencia sobre el certificado la primera vez que visites la página, ya que hay un certificado autofirmado. Haz clic en **Avanzado → Continuar** para seguir adelante. Esto es normal y solo hay que hacerlo una vez por navegador.

## Gestión de Servicios

```bash
# Comprobar estado
systemctl status parley-chat
systemctl status parley-chat-nginx

# Reiniciar
systemctl restart parley-chat
systemctl restart parley-chat-nginx

# Detener
systemctl stop parley-chat
systemctl stop parley-chat-nginx
```
