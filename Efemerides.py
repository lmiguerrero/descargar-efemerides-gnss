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
import folium
from streamlit_folium import st_folium
import urllib.parse

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
    lat_deg = st.sidebar.number_input("Grados", min_value=-90, max_value=90, value=5, key="lat_deg_input")
    lat_min = st.sidebar.number_input("Minutos", min_value=0, max_value=59, value=20, key="lat_min_input")
    lat_sec = st.sidebar.number_input("Segundos (con decimales)", min_value=0.0, max_value=59.999999, value=18.430000, format="%.6f", key="lat_sec_input")
    
    st.sidebar.subheader("Longitud")
    lon_deg = st.sidebar.number_input("Grados", min_value=-180, max_value=180, value=-72, key="lon_deg_input")
    lon_min = st.sidebar.number_input("Minutos", min_value=0, max_value=59, value=23, key="lon_min_input")
    lon_sec = st.sidebar.number_input("Segundos (con decimales)", min_value=0.0, max_value=59.999999, value=37.750000, format="%.6f", key="lon_sec_input")
    
    lat_magnitude = abs(lat_deg) + lat_min / 60 + lat_sec / 3600
    lon_magnitude = abs(lon_deg) + lon_min / 60 + lon_sec / 3600
    
    if lat_deg < 0:
        lat = -lat_magnitude
    else:
        lat = lat_magnitude
        
    if lon_deg < 0:
        lon = -lon_magnitude
    else:
        lon = lon_magnitude
    
    if lat != 0.0 or lon != 0.0:
        user_coord = (lat, lon)
else:
    este = st.sidebar.number_input("Este (X)", format="%.2f", key="este_input")
    norte = st.sidebar.number_input("Norte (Y)", format="%.2f", key="norte_input")
    if este != 0.0 or norte != 0.0:
        try:
            proj = pyproj.Transformer.from_crs("EPSG:3116", "EPSG:4326", always_xy=True)
            lon_decimal, lat_decimal = proj.transform(este, norte)
            user_coord = (lat_decimal, lon_decimal)
        except Exception as e:
            st.error(f"Error en la conversión de coordenadas: {e}")

num_estaciones = st.sidebar.slider("Número de estaciones cercanas", 1, 10, 5)

MAP_STYLES = {
    "OpenStreetMap": "OpenStreetMap",
    "CartoDB Claro (Positron)": "CartoDB positron",
    "CartoDB Oscuro": "CartoDB dark_matter",
    "Satélite (Esri)": "Esri.WorldImagery",
}
selected_map_style_name = st.sidebar.selectbox("🗺️ Fondo del mapa", list(MAP_STYLES.keys()))
selected_map_style_value = MAP_STYLES[selected_map_style_name]

if "mostrar_mapa" not in st.session_state:
    st.session_state["mostrar_mapa"] = False
if "mapa_data" not in st.session_state:
    st.session_state["mapa_data"] = None

st.subheader("🗺️ Estaciones GNSS más cercanas")
if st.button("🗺️ Generar Mapa"):
    st.session_state["mapa_data"] = {
        "user_coord": user_coord,
        "num_estaciones": num_estaciones,
        "selected_map_style_value": selected_map_style_value
    }
    st.session_state["mostrar_mapa"] = True

if st.session_state["mostrar_mapa"] and st.session_state["mapa_data"]:
    mapa_data = st.session_state["mapa_data"]
    user_coord = mapa_data["user_coord"]
    num_estaciones = mapa_data["num_estaciones"]
    selected_map_style_value = mapa_data["selected_map_style_value"]

    csv_url = "https://raw.githubusercontent.com/lmiguerrero/descargar-efemerides-gnss/main/Coordenadas.csv"
    try:
        df = pd.read_csv(csv_url)
        if user_coord is not None:
            df["Distancia_km"] = df.apply(
                lambda row: geodesic(user_coord, (row['Latitud'], row['Longitud'])).kilometers, axis=1
            )
            df_sorted = df.sort_values("Distancia_km").head(num_estaciones)
            
            st.markdown("### 🗺️ Ver mapa de estaciones")
            
            with st.spinner("Generando mapa..."):
                m = folium.Map(location=[user_coord[0], user_coord[1]], zoom_start=6, tiles=selected_map_style_value)

                folium.Marker(
                    location=[user_coord[0], user_coord[1]],
                    popup="Ubicación del Usuario",
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(m)

                for index, row in df_sorted.iterrows():
                    igac_url = f"https://www.colombiaenmapas.gov.co/?e={row['Longitud'] - 0.1},{row['Latitud'] - 0.1},{row['Longitud'] + 0.1},{row['Latitud'] + 0.1},4686&b=igac&u=0&t=25&servicio=6&estacion={row['Id']}"
                    popup_html = f"""
                    <b>ID:</b> <a href="{igac_url}" target="_blank">{row['Id']}</a><br>
                    <b>Municipio:</b> {row['Nombre Municipio']}<br>
                    <b>Departamento:</b> {row['Nombre Departamento']}<br>
                    <b>Distancia:</b> {row['Distancia_km']:.2f} km
                    """
                    folium.Marker(
                        location=[row['Latitud'], row['Longitud']],
                        popup=popup_html,
                        icon=folium.Icon(color="orange", icon="cloud")
                    ).add_to(m)

                if not df_sorted.empty:
                    bounds = [[min(user_coord[0], df_sorted['Latitud'].min()), min(user_coord[1], df_sorted['Longitud'].min())], 
                              [max(user_coord[0], df_sorted['Latitud'].max()), max(user_coord[1], df_sorted['Longitud'].max())]]
                    m.fit_bounds(bounds)

                st_folium(m, width=1200, height=600)

            st.markdown("### 📋 Estaciones cercanas")
            
            st.markdown(
                f"""
                | ID | Nombre Municipio | Nombre Departamento | Distancia_km |
                | :--- | :--- | :--- | :--- |
                """
            )
            
            for index, row in df_sorted.iterrows():
                igac_url = f"https://www.colombiaenmapas.gov.co/?e={row['Longitud'] - 0.1},{row['Latitud'] - 0.1},{row['Longitud'] + 0.1},{row['Latitud'] + 0.1},4686&b=igac&u=0&t=25&servicio=6&estacion={row['Id']}"
                st.markdown(
                    f"| <a href='{igac_url}' target='_blank'>{row['Id']}</a> | {row['Nombre Municipio']} | {row['Nombre Departamento']} | {row['Distancia_km']:.2f} |",
                    unsafe_allow_html=True
                )
        else:
            st.error("Por favor, ingresa una coordenada válida para generar el mapa.")
            st.session_state["mostrar_mapa"] = False
    except Exception as e:
        st.error(f"Error al cargar o procesar los datos de las estaciones: {e}")
        st.session_state["mostrar_mapa"] = False

st.markdown("---")
st.markdown("### ¿Te gustaría dejar una sugerencia o comentario?")
st.markdown("---")
st.markdown("Luis Miguel Guerrero Ing Topográfico Universidad Distrital | Contacto: lmguerrerov@udistrital.edu.co")
