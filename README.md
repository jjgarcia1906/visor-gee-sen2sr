# Visor GEE — Sentinel-2 (SEN2SR)

Visor rápido de escenas Sentinel-2 usando **Google Earth Engine**.
Miniaturas renderizadas en la nube de GEE → consulta instantánea de escenas
(fecha, % de nubes, granulo MGRS, ID) para elegir cuál procesar con la app SEN2SR.

## Cómo correrlo en local
```bash
pip install -r requirements.txt
unset PYTHONPATH  # Windows/MSYS: evita conflictos de numpy
streamlit run app.py
```
Se abre en http://localhost:8502

## Desplegarlo en Streamlit Community Cloud (gratis)

1. Sube esta carpeta a un **repositorio de GitHub** (público o privado).
2. Entra a https://share.streamlit.io y crea una app apuntando a ese repo
   (archivo principal: `app.py`).
3. Configura los **Secrets** (⚙️ Settings → Secrets) con el service account de GEE:

```toml
GEE_PROJECT = "ee-jjgarcia1906"
GEE_SERVICE_ACCOUNT = "tu-proyecto@appspot.gserviceaccount.com"
GEE_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
... claves del archivo JSON de tu service account ...
-----END PRIVATE KEY-----"""
```

### Cómo obtener el service account de GEE
1. https://code.earthengine.google.com → ⚙️ Settings → Service accounts → Create Service Account
2. Copia el **email** del service account
3. Google Cloud Console → IAM & Admin → Service Accounts → Keys → Add Key → JSON
4. Usa el `client_email` y la `private_key` del archivo JSON descargado en los Secrets de arriba.

> ⚠️ **NO subas el archivo JSON del service account al repositorio.** Va solo en los Secrets.