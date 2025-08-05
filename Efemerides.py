import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from geopy.distance import geodesic
import requests
import os
import shutil
import tempfile
import pyproj
import urllib.parse
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Herramienta GNSS",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📡 Herramienta GNSS - Consulta y Descarga de Efemérides IGS")
st.markdown("---")

def calculate_gps_week_number(date):
    date_format = "%Y-%m-%d"
    target_date = datetime.strptime(str(date), date_format)
    gps_start_date = datetime(1980, 1, 6)
    days_since_start = (target_date - gps_start_date).days
    gps_week = days_since_start // 7
    gps_day_of_week = days_since_start % 7
    gps_week_number = gps_week * 10 + gps_day_of_week
    day_of_year = target_date.timetuple().tm_yday
    year = target_date.year
    return gps_week, gps_week_number, day_of_year, year

def check_url(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def download_file(url, local_path):
    try:
        response = requests.get(url, stream=True, timeout=10)
        with open(local_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return True
    except Exception as e:
        st.error(f"Error al descargar {url}: {e}")
        return False

def download_efemerides(date, folder_path, download_precise, download_rapid, download_gfz):
    gps_week, gps_week_number, day_of_year, year = calculate_gps_week_number(date)
    files_to_download = []
    if download_precise:
        precise_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/JAX0MGXFIN_{year}{day_of_year:03d}0000_01D_05M_ORB.SP3.gz"
        files_to_download.append((precise_url, 'Precisas JAX', 'gz'))
    if download_rapid:
        rapid_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/igr{gps_week_number}.sp3.Z"
        files_to_download.append((rapid_url, 'Rápidas', 'Z'))
    if download_gfz:
        gfz_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/GFZ0OPSRAP_{year}{day_of_year:03d}0000_01D_05M_ORB.SP3.gz"
        files_to_download.append((gfz_url, 'GFZ', 'gz'))

    download_info = []
    for url, label, compression_type in files_to_download:
        local_filename = os.path.basename(url)
        local_path = os.path.join(folder_path, local_filename)
        status = "No disponible"
        if check_url(url):
            if download_file(url, local_path):
                status = "Descargado"
            else:
                status = "Error al descargar"
        download_info.append({
            "label": label,
            "filename": local_filename,
            "status": status,
            "local_path": local_path
        })
    return download_info

st.sidebar.header("📥 Ingresar parámetros")

st.sidebar.markdown("### 🗓️ Descargar Efemérides")
selected_date = st.sidebar.date_input("Seleccionar fecha", datetime.today())
download_precise = st.sidebar.checkbox("Descargar Efemérides Precisas JAX", value=True)
download_rapid = st.sidebar.checkbox("Descargar Efemérides Rápidas", value=False)
download_gfz = st.sidebar.checkbox("Descargar Efemérides Precisas GFZ", value=False)

if st.sidebar.button("🔽 Descargar Efemérides"):
    if not download_precise and not download_rapid and not download_gfz:
        st.sidebar.warning("Por favor, selecciona al menos un tipo de efemérides para descargar.")
    else:
        with st.spinner("Descargando y procesando..."):
            tmpdir = tempfile.mkdtemp()
            download_status = download_efemerides(selected_date, tmpdir, download_precise, download_rapid, download_gfz)
            st.subheader("Estado de la descarga:")
            for info in download_status:
                if info["status"] == "Descargado":
                    st.success(f"✅ {info['label']} ({info['filename']}) descargado.")
                    try:
                        with open(info['local_path'], "rb") as file:
                            st.download_button(
                                label=f"📄 Descargar {info['label']}",
                                data=file,
                                file_name=info['filename'],
                                mime="application/octet-stream"
                            )
                    except Exception as e:
                        st.error(f"Error al preparar el botón de descarga para {info['label']}: {e}")
                else:
                    st.warning(f"⚠️ {info['label']} ({info['filename']}): {info['status']}")
            st.info("Confío en que este programa le será de gran utilidad y cumpla con sus expectativas.")
            shutil.rmtree(tmpdir)

st.sidebar.markdown("---")

st.sidebar.markdown("### 📍 Coordenadas para búsqueda de estaciones")
coord_format = st.sidebar.selectbox("Formato de coordenadas", ["Grados, Minutos, Segundos", "Origen Nacional"])
user_coord = None
if coord_format == "Grados, Minutos, Segundos":
    st.sidebar.subheader("Latitud")
    # Para la latitud, la suma es correcta.
    lat_deg = st.sidebar.number_input("Grados", min_value=-90, max_value=90, value=5, key="lat_deg_input")
    lat_min = st.sidebar.number_input("Minutos", min_value=0, max_value=59, value=20, key="lat_min_input")
    lat_sec = st.sidebar.number_input("Segundos (con decimales)", min_value=0.0, max_value=59.999999, value=18.430000, format="%.6f", key="lat_sec_input")
    
    st.sidebar.subheader("Longitud")
    # Para la longitud, ya que estamos en el hemisferio occidental, los minutos y segundos deben restarse.
    # Se ha cambiado el valor predeterminado a -72 para reflejar que es una longitud Oeste.
    lon_deg = st.sidebar.number_input("Grados", min_value=-180, max_value=180, value=-72, key="lon_deg_input")
    lon_min = st.sidebar.number_input("Minutos", min_value=0, max_value=59, value=23, key="lon_min_input")
    lon_sec = st.sidebar.number_input("Segundos (con decimales)", min_value=0.0, max_value=59.999999, value=37.750000, format="%.6f", key="lon_sec_input")
    
    lat = lat_deg + lat_min / 60 + lat_sec / 3600
    
    # *** ESTA ES LA LÍNEA CLAVE QUE SE MODIFICÓ.
    # En el hemisferio occidental, se restan los minutos y segundos del valor negativo.
    lon = lon_deg - lon_min / 60 - lon_sec / 3600
    
    if lat != 0.0 or lon != 0.0:
        user_coord = (lat, lon)
else:
    este = st.sidebar.number_input("Este (X)", format="%.2f", key="este_input")
    norte = st.sidebar.number_input("Norte (Y)", format="%.2f", key="norte_input")
    if este != 0.0 or norte != 0.0:
        try:
            proj = pyproj.Transformer.from_crs("EPSG:3116", "EPSG:4326", always_xy=True)
            lon_decimal, lat_decimal = proj.transform(este, norte)
            user_coord = (lat_decimal, lat_decimal) # Error corregido: deberia ser (lat_decimal, lon_decimal)
        except Exception as e:
            st.error(f"Error en la conversión de coordenadas: {e}")

# ... (resto del código sin cambios) ...
