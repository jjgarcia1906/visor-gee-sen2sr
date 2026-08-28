#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
visualizador_gee.py — Visualizador rápido de escenas Sentinel-2 con Google Earth Engine.
Consulta coordenadas o GeoJSON, genera miniaturas e IDs INSTANTÁNEOS (GEE los renderiza en su nube).

USO:
    1. Abrir CMD (no Git Bash)
    2. set PYTHONPATH=
    3. python visualizador_gee.py
    4. Se abre en http://localhost:8502

Cada tarjeta muestra: fecha · % nubes · granulo MGRS · ID (clic para copiar).
El ID se pega en la app SEN2SR (campo "ID de escena") para descargar/super-resolver esa escena exacta.
"""

import os
import ee

# ── CONFIG ──────────────────────────────────────────────────────────
PROJECT_ID = "jjgarcia1906"   # tu proyecto GEE
COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"

import streamlit as st
st.set_page_config(page_title="🛰️ Visor GEE Sentinel-2", layout="wide")

# ══════════════════════════════════════════════
#  TEMA VISUAL (celeste + verde oscuro) — igual que la app SEN2SR
# ══════════════════════════════════════════════
st.markdown("""
<style>
.stApp {
    background: linear-gradient(160deg, #eaf6ff 0%, #f0fbf5 100%);
}
h1 {
    color: #0b5d3b !important;
    font-weight: 800 !important;
}
h2, h3 {
    color: #0f766e !important;
}
[data-testid="stCaptionContainer"] p {
    color: #3b5b73;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #e8f7ff 0%, #e7f6ee 100%);
    border-right: 1px solid #cfe6f2;
}
/* ── Botones ── */
.stButton > button {
    background: linear-gradient(90deg, #12a5b0 0%, #0b7a6e 100%);
    color: white;
    font-weight: 600;
    border: none;
    border-radius: 10px;
    padding: 0.6rem 1.2rem;
    transition: 0.2s;
    box-shadow: 0 3px 10px rgba(11, 122, 110, .25);
}
.stButton > button:hover {
    background: linear-gradient(90deg, #0f8790 0%, #095e55 100%);
    color: white;
    transform: translateY(-1px);
    box-shadow: 0 5px 16px rgba(11, 122, 110, .35);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #0b8a45 0%, #0b5d3b 100%);
    font-size: 1.05rem;
    font-weight: 700;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(90deg, #0a7839 0%, #094d31 100%);
}
/* ── Inputs / radio / slider / uploader ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
    border: 1px solid #bcdde8;
    border-radius: 8px;
    background: #ffffff;
}
[data-testid="stSelectbox"] > div > div {
    border: 1px solid #bcdde8;
    border-radius: 8px;
}
[data-testid="stSlider"] [role="slider"] {
    background: #0b7a6e;
}
[data-baseweb="tag"] {
    background-color: #dceff5 !important;
}
[data-testid="stFileUploader"] {
    border: 1px dashed #12a5b0;
    border-radius: 8px;
    background: #f4fbfe;
}
details {
    border: 1px solid #cfe6f2 !important;
    border-radius: 10px;
    background: #ffffffcc;
}
/* tarjetas de escena */
div[class*="stMarkdown"] div div {
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

st.title("🛰️ Visor rápido de escenas — Google Earth Engine")
st.caption("Miniaturas renderizadas en la nube de GEE → instantáneo. Copia el ID y pégalo en la app SEN2SR.")


@st.cache_resource
def iniciar_gee():
    import json as _j
    proj = "jjgarcia1906"

    # 1) Service account JSON file (VPS deployment)
    sa_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gee_sa.json")
    if os.path.exists(sa_path):
        with open(sa_path) as f:
            sa = _j.load(f)
        creds = ee.ServiceAccountCredentials(sa["client_email"], sa_path)
        ee.Initialize(creds, project=proj)
        return True

    # 2) Streamlit secrets (Streamlit Cloud)
    try:
        gaa = st.secrets.get("GEE_SERVICE_ACCOUNT") or st.secrets.get("gee_service_account") or ""
        gkey = st.secrets.get("GEE_PRIVATE_KEY") or st.secrets.get("gee_private_key") or ""
        if gaa and gkey:
            import tempfile
            d = {"type": "service_account",
                 "client_email": gaa,
                 "private_key": (gkey.replace("\\n", "\n")),
                 "token_uri": "https://oauth2.googleapis.com/token"}
            p = os.path.join(tempfile.gettempdir(), "gee_sa.json")
            with open(p, "w") as f:
                _j.dump(d, f)
            creds = ee.ServiceAccountCredentials(gaa, p)
            ee.Initialize(creds, project=proj)
            return True
    except Exception:
        pass

    # 3) Fallback: local credentials
    ee.Initialize(project=proj)
    return True


iniciar_gee()


# ── Entrada ─────────────────────────────────────────────────────────
st.subheader("① Definir zona")
modo = st.radio("Formato", ["Coordenadas (lat, lon)", "UTM 18S", "Archivo GeoJSON"], horizontal=True)

lat = lon = None
geom = None
if modo.startswith("Coordenadas"):
    c1, c2 = st.columns(2)
    lat = c1.number_input("Latitud", value=-3.75, format="%.5f")
    lon = c2.number_input("Longitud", value=-73.25, format="%.5f")
    geom = ee.Geometry.Point([lon, lat])
elif modo.startswith("UTM"):
    c1, c2 = st.columns(2)
    eas = c1.number_input("Easting (X)", value=694347.0, format="%.2f")
    nor = c2.number_input("Northing (Y)", value=9585311.0, format="%.2f")
    try:
        from pyproj import Transformer
        tr = Transformer.from_crs("EPSG:32718", "EPSG:4326", always_xy=True)
        lon, lat = tr.transform(eas, nor)
        st.caption(f"→ Lat {lat:.5f}, Lon {lon:.5f}")
        geom = ee.Geometry.Point([lon, lat])
    except Exception as e:
        st.error(f"Conversión UTM: {e}")
else:
    archivo = st.file_uploader("GeoJSON", type=["geojson", "json"])
    buffer_m = st.number_input("Buffer exterior (m)", value=50, min_value=0, max_value=2000)
    if archivo is not None:
        import json as _json
        gj = _json.loads(archivo.read())
        # extraer todas las coords de polygons/multipolygons
        import sys
        coords = []
        feats = gj.get("features", [gj])
        for feat in feats:
            g = (feat or {}).get("geometry") or {}
            t = g.get("type"); c = g.get("coordinates") or []
            if t == "Polygon":
                coords += c[0]
            elif t == "MultiPolygon":
                for p in c:
                    coords += p[0]
        if coords:
            lons = [p[0] for p in coords]; lats = [p[1] for p in coords]
            # buffer en grados aprox
            deg = buffer_m / 111132.92
            geom = ee.Geometry.Polygon(
                [[min(lons) - deg, min(lats) - deg],
                 [max(lons) + deg, min(lats) - deg],
                 [max(lons) + deg, max(lats) + deg],
                 [min(lons) - deg, max(lats) + deg]])
            lat = (min(lats) + max(lats)) / 2
            lon = (min(lons) + max(lons)) / 2

# ── Rango de fechas ────────────────────────────────────────────────
st.subheader("② Período")
from datetime import date, datetime
c1, c2 = st.columns(2)
f_in = c1.date_input("Fecha inicio", value=date(date.today().year, 7, 15))
f_fin = c2.date_input("Fecha fin", value=date.today())
cloud_max = st.slider("Máx % de nubes", 0, 100, 100, help="Filtra escenas con nubes ≤ valor. 100 = mostrar todas.")

st.subheader("③ Generar")
if st.button("🔍 Buscar escenas", type="primary") and geom is not None:
    nubes_field = "CLOUD_COVERAGE_ASSESSMENT"
    col = (ee.ImageCollection(COLLECTION)
           .filterBounds(geom)
           .filterDate(str(f_in), str(f_fin)))
    if cloud_max < 100:
        col = col.filter(ee.Filter.lte(nubes_field, cloud_max))

    lista = col.sort("system:time_start", False).toList(col.size())
    n = lista.size().getInfo()
    st.write(f"**{n} escena(s) encontrada(s) en el período**")

    # región fija para el thumbnail (3 km de lado aprox) alrededor del centro
    try:
        ctr = geom.centroid().coordinates().getInfo()
        clon, clat = ctr[0], ctr[1]
        d = 0.02  # ~2.2 km
        regi = ee.Geometry.Polygon([[clon - d, clat - d], [clon + d, clat - d],
                                    [clon + d, clat + d], [clon - d, clat + d]])
    except Exception:
        regi = geom

    cc = st.columns(3)
    idx = 0
    # Obtener TODOS los metadatos de una vez (más rápido; GEE ya los envía juntos)
    for i in range(n):
        img = ee.Image(lista.get(i))
        try:
            info = img.getInfo()  # UNA sola llamada a GEE
            props = info.get("properties", {}) or {}
            ts = props.get("system:time_start", "")
            fecha = str(ts)[:10] if ts else ""
            if str(ts).isdigit():
                fecha = datetime.fromtimestamp(int(ts) / 1000).strftime("%Y-%m-%d")
            sat = props.get("SPACECRAFT_ID") or "S2"
            tile = props.get("MGRS_TILE") or ""
            nubes = props.get(nubes_field)
            nub_txt = "%.0f%%" % nubes if nubes is not None else "n/d"
            id_largo = info.get("id", "") or ""
            id_short = id_largo.split("/")[-1]
            id_copy = id_short
            # thumbnail solo cuando hace falta (server-side render)
            rgb = img.select(["B4", "B3", "B2"])
            thumb = rgb.getThumbURL({
                "min": 0, "max": 3000, "gamma": 1.4,
                "dimensions": 420, "format": "png", "region": regi,
            })
            badge = "ok" if nubes is not None and nubes <= 20 else ("warn" if nubes is not None and nubes <= 50 else "mal")
            c = cc[idx % 3]
            with c:
                st.markdown(
                    f"""<div style="border:1.5px solid #7cc4d6;border-radius:12px;padding:10px;margin-bottom:12px;
                    background:#ffffff;box-shadow:0 2px 10px rgba(18,165,176,.15)">
                    <b style="color:#0b5d3b">📅 {fecha}</b> &nbsp;
                    <span style="background:#c9ecd4;color:#094d31;border-radius:8px;padding:2px 8px;font-weight:bold">{nub_txt}</span><br>
                    <img src="{thumb}" style="width:100%;border-radius:6px" alt="{fecha}"><br>
                    <small>🛰️ {sat} · Granulo {tile or 'n/d'}</small><br>
                    <code style="font-size:10px;background:#f1f5f9;padding:2px 4px;word-break:break-all">{id_copy}</code>
                    </div>""",
                    unsafe_allow_html=True,
                )
                idx += 1
        except Exception as e:
            st.caption(f"⚠️ escena {i}: {str(e)[:60]}")

else:
    if st.session_state.get("_visto", None):
        st.info("Define la zona y pulsa el botón.")

st.caption("\n\nConsejo: pega el ID gris de una tarjeta en la app SEN2SR (campo 'ID de escena') para super-resolver ESA escena.")