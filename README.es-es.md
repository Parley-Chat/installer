# Parley Chat Instalador

[🇬🇧 English](README.md) | [🇮🇷 فارسی](README.fa.md)

Instalador automático para [Parley Chat](https://github.com/Parley-Chat). Configura el backend (Sova), el frontend (Mura), nginx como proxy inversa de SSL y los servicios de systemd con un solo comando.

## Requisitos

- Linux (x86_64 o arm64)
- Acceso root (`sudo`)
- `wget` o `curl` (no es necesario para instalaciones locales)

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

## Instalación Local (no requiere internet)

Descarga el paquete en cualquier equipo, transfiérelo a tu servidor, extráelo y ejecútalo:

```bash
tar xzf parley-install.tar.gz
chmod +x installer-linux-x64   # o installer-linux-arm64
sudo ./installer-linux-x64
```

El instalador automáticamente detecta los archivos `sova-linux-<arch>` y `mura.zip` en el mismo directorio y los utiliza en lugar de descargar algo.

## Usar un Espejo

Si GitHub no es accesible, puedes apuntar el instalador a un espejo alternativo:

```bash
wget https://tu-espejo.com/install.sh -O install.sh
chmod +x install.sh
sudo MIRROR_BASE_URL="https://tu-espejo.com" ./install.sh
```

El binario del instalador y todos los archivos (Sova, Mura) se descargarán desde el espejo especificado.

## Menu

Al ejecutar el instalador, puedes elegir entre:

```
[I] Install   — Instalar
[U] Update    — Actualizar
[M] Modify    — Modificar
[X] Uninstall — Desinstalar
```

## Instalar (Install)

Para una instalación nueva, debes primero seleccionar:

**Recomendado (Recommended)** solo te pide tu dominio o dirección IP, prefijo URI, contraseña opcional de la instancia y el método SSL, luego se configura todo con unos valores predeterminados razonables.

**Personalizado (Custom)** te permite configurar el puerto HTTPS, directorio de instalación, contraseña de instancia, número de subprocesos, llamadas de voz y más.

Al finalizar la instalación, se te preguntará si activar la **actualización automática** (ver más abajo).

### Actualizar (Update)

Descarga la última versión del binario de Sova y frontend de Mura, los sustituye en el lugar y reinicia el backend. Tu archivo `config.toml`, los certificados y los datos no son afectados.

También funciona en modo local: coloca los nuevos archivos `sova-linux-<arch>` y `mura.zip` junto al instalador antes de ejecutarlo.

### Modificar (Modify)

Cambios posteriores a la instalación sin necesidad de reinstalar:

- **Renovar certificado SSL**: vuelve a ejecutar el proceso de configuración de SSL (con las mismas opciones que durante la instalación); actualiza `nginx.conf` y reinicia nginx automáticamente
- **Habilitar/deshabilitar la actualización automática**: activa o desactiva la tarea cron de actualización diaria

### Desinstalar (Uninstall)

Detiene y deshabilita todos los servicios, elimina los archivos de unidad de systemd y borra el directorio de instalación.

## SSL Options

| Opción | Cuándo usar |
|--------|-------------|
| Autofirmado (Self-signed) | Direcciones IP, instancias privadas/locales o cualquier lugar protegido por un cortafuegos |
| Let's Encrypt - HTTP | Dominio público con puerto 80 abierto para Internet. Se renueva automáticamente. |
| Let's Encrypt - DNS | Dominio público protegido por cortafuegos (por ejemplo servidores iraníes). Requiere añadir un récord DNS TXT. Debe renovarse manualmente cada 90 días. |

Si introduces una dirección IP en lugar de un dominio, se utiliza automáticamente un certificado autofirmado, ya que Let's Encrypt requiere un nombre de dominio.

## Actualización Automática

Al instalar (solo en modo en línea), el instalador te pregunta si deseas recibir actualizaciones automáticas. Si se activa, puedes elegir la frecuencia:

| Opción | Frecuencia |
| ------ | ---------- |
| Cada 5 minutos | `*/5 * * * *` |
| Cada hora | `0 * * * *` |
| Diariamente a las 3 AM | `0 3 * * *` |
| Diariamente a las 4 AM | `0 4 * * *` |
| Personalizado | introduce cualquier expresión cron |

El instalador crea el archivo `auto-update.sh` en el directorio de instalación y configura una trabajo cron. Cada ejecución obtiene el archivo `version.txt` del espejo y lo compara con el archivo `.version` local, solo descarga y reinicia si hay una nueva versión disponible. El resultado de la actualización se registra en `/var/log/parley-chat-update.log`.

Puedes activar o desactivar la actualización automática en cualquier momento desde el menú **Modificar**.

## Qué se Instala

| Componente | Descripción |
|------------|-------------|
| `sova` | Binario del backend |
| `mura/` | Archivos estáticos del frontend |
| `config.toml` | Configuración de Sova |
| `certs/` | Certificado SSL autofirmado (10 años de validez) |
| `nginx.conf` | Configuración de la proxy inversa de nginx |
| `auto-update.sh` | Script de actualización automática (si habilitado) |
| `.install_info` | Ajustes guardados que utiliza el menú Modificar |
| `parley-chat.service` | Servicio systemd para Sova |
| `parley-chat-nginx.service` | Servicio systemd para Nginx |

Por defecto, todo se instala en `/opt/parley-chat` (configurable en el modo Custom).

## Después de la Instalación

La instancia será accesible en `https://<tu-dominio>:<puerto>/<prefijo-uri>/`

Tu navegador mostrará una advertencia sobre el certificado la primera vez que visites la página, si estas usando un certificado autofirmado. Haz clic en **Avanzado → Continuar** para seguir adelante.

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
