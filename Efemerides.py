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
import zipfile

# --- CSS para un diseño con Tarjetas, barra lateral y centrar banner ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f0f2f6; /* Un gris claro, más neutro */
    }
    /* Estilo de los títulos */
    .st-emotion-cache-10trblm h1, .st-emotion-cache-10trblm h2, .st-emotion-cache-10trblm h3 {
        color: #003366; /* Azul marino para los títulos */
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    /* Estilo de las tarjetas (contenedores) */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    div[data-testid="stVerticalBlock"] > div {
        border-radius: 10px;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1);
        transition: 0.3s;
        background-color: #ffffff;
        padding: 20px;
        margin-bottom: 20px;
    }
    /* Hover en las tarjetas */
    div[data-testid="stVerticalBlock"] > div:hover {
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
    }
    /* Estilo de los botones */
    .stButton>button {
        background-color: #007bff;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 24px;
        font-size: 16px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    /* Ajustar el ancho de la barra lateral */
    [data-testid="stSidebar"] {
        width: 350px;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] {
        width: 350px;
    }
    /* Centrar la imagen del banner */
    .stImage {
        text-align: center;
        margin-top: -30px; /* Ajusta este valor si necesitas más espacio arriba */
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.set_page_config(
    page_title="Celeste GNSS",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Banner (Imagen) ---
st.image("https://iili.io/FidmiBe.png")

def calculate_gps_week_number(date):
    date_format = "%Y-%m-%d"
    target_date = datetime.strptime(str(date), date_format)
    gps_start_date = datetime(1980, 1, 6)
    days_since_start = (target_date - gps_start_date).days
    gps_week = days_since_start // 7
    gps_day_of_week = days_since_start % 7
    day_of_year = target_date.timetuple().tm_yday
    year = target_date.year
    return gps_week, gps_day_of_week, day_of_year, year

def check_url(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def download_file(url, local_path):
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(local_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return True
    except Exception as e:
        st.error(f"Error al descargar {url}: {e}")
        return False

def download_files_for_date(date, folder_path, download_precise, download_rapid, download_gfz):
    gps_week, gps_day_of_week, day_of_year, year = calculate_gps_week_number(date)
    files_to_download = []
    
    gps_week_number = gps_week * 10 + gps_day_of_week

    if download_precise:
        precise_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/JAX0MGXFIN_{year}{day_of_year:03d}0000_01D_05M_ORB.SP3.gz"
        files_to_download.append((precise_url, f'Precisas JAX - {date}'))
    if download_rapid:
        rapid_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/igr{gps_week_number}.sp3.Z"
        files_to_download.append((rapid_url, f'Rápidas - {date}'))
    if download_gfz:
        gfz_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/GFZ0OPSRAP_{year}{day_of_year:03d}0000_01D_05M_ORB.SP3.gz"
        files_to_download.append((gfz_url, f'GFZ - {date}'))

    download_info = []
    for url, label in files_to_download:
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

# --- Barra lateral (Solo Efemérides) ---
st.sidebar.header("📥 Ingresar parámetros")
with st.sidebar.container():
    st.subheader("🗓️ Descargar Efemérides")
    date_range = st.date_input("Seleccionar rango de fechas", value=(datetime.today() - timedelta(days=7), datetime.today()), max_value=datetime.today())
    download_precise = st.checkbox("Descargar Efemérides Precisas JAX", value=True)
    download_rapid = st.checkbox("Descargar Efemérides Rápidas", value=False)
    download_gfz = st.checkbox("Descargar Efemérides Precisas GFZ", value=False)
    if st.button("🔽 Descargar Efemérides"):
        if not date_range or len(date_range) != 2:
            st.sidebar.warning("Por favor, selecciona un rango de fechas válido.")
        elif not download_precise and not download_rapid and not download_gfz:
            st.sidebar.warning("Por favor, selecciona al menos un tipo de efemérides para descargar.")
        else:
            start_date, end_date = date_range
            delta = end_date - start_date
            total_days = delta.days + 1
            
            tmpdir = tempfile.mkdtemp()
            all_download_status = []
            
            st.subheader("Estado de la descarga:")
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            
            for i in range(total_days):
                current_date = start_date + timedelta(days=i)
                status_text.text(f"Descargando efemérides para la fecha: {current_date.strftime('%Y-%m-%d')}...")
                
                download_status = download_files_for_date(current_date, tmpdir, download_precise, download_rapid, download_gfz)
                all_download_status.extend(download_status)
                
                progress = (i + 1) / total_days
                progress_bar.progress(progress)
            
            status_text.success("Descarga de efemérides finalizada. Comprimiendo archivos...")

            zip_filename = f"Efemérides_{start_date.strftime('%Y-%m-%d')}_a_{end_date.strftime('%Y-%m-%d')}.zip"
            zip_path = os.path.join(tmpdir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for item in os.listdir(tmpdir):
                    if item.endswith(('.gz', '.Z')):
                        zf.write(os.path.join(tmpdir, item), item)
            
            with open(zip_path, "rb") as fp:
                st.download_button(
                    label=f"📄 Descargar todos los archivos ({zip_filename})",
                    data=fp.read(),
                    file_name=zip_filename,
                    mime="application/zip"
                )

            shutil.rmtree(tmpdir)

st.sidebar.markdown("---")

# --- Contenedor para la entrada de coordenadas (Tarjeta en el área principal) ---
with st.container():
    st.subheader("📍 Coordenadas para búsqueda de estaciones")
    coord_format = st.selectbox("Formato de coordenadas", ["Grados, Minutos, Segundos", "Origen Nacional"])
    user_coord = None

    if coord_format == "Grados, Minutos, Segundos":
        st.subheader("Latitud")
        col1, col2, col3 = st.columns(3)
        with col1:
            lat_deg = st.number_input("Grados", min_value=-90, max_value=90, value=5, key="lat_deg_input")
        with col2:
            lat_min = st.number_input("Minutos", min_value=0, max_value=59, value=20, key="lat_min_input")
        with col3:
            lat_sec = st.number_input("Segundos (con decimales)", min_value=0.0, max_value=59.999999, value=18.430000, format="%.6f", key="lat_sec_input")
        
        st.subheader("Longitud")
        col4, col5, col6 = st.columns(3)
        with col4:
            lon_deg = st.number_input("Grados", min_value=-180, max_value=180, value=-72, key="lon_deg_input")
        with col5:
            lon_min = st.number_input("Minutos", min_value=0, max_value=59, value=23, key="lon_min_input")
        with col6:
            lon_sec = st.number_input("Segundos (con decimales)", min_value=0.0, max_value=59.999999, value=37.750000, format="%.6f", key="lon_sec_input")
        
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
        este = st.number_input("Este (X)", format="%.2f", key="este_input")
        norte = st.number_input("Norte (Y)", format="%.2f", key="norte_input")
        if este != 0.0 or norte != 0.0:
            try:
                proj = pyproj.Transformer.from_crs("EPSG:3116", "EPSG:4326", always_xy=True)
                lon_decimal, lat_decimal = proj.transform(este, norte)
                user_coord = (lat_decimal, lon_decimal)
            except Exception as e:
                st.error(f"Error en la conversión de coordenadas: {e}")

    num_estaciones = st.slider("Número de estaciones cercanas", 1, 10, 5)

    MAP_STYLES = {
        "OpenStreetMap": "OpenStreetMap",
        "CartoDB Claro (Positron)": "CartoDB positron",
        "CartoDB Oscuro": "CartoDB dark_matter",
        "Satélite (Esri)": "Esri.WorldImagery",
    }
    selected_map_style_name = st.selectbox("🗺️ Fondo del mapa", list(MAP_STYLES.keys()))
    selected_map_style_value = MAP_STYLES[selected_map_style_name]


# --- Contenedor para el mapa (Tarjeta) ---
if "mapa_data" not in st.session_state:
    st.session_state["mapa_data"] = None

with st.container():
    st.subheader("🗺️ Estaciones GNSS más cercanas")
    if st.button("🗺️ Generar Mapa"):
        st.session_state["mapa_data"] = {
            "user_coord": user_coord,
            "num_estaciones": num_estaciones,
            "selected_map_style_value": selected_map_style_value
        }

    if st.session_state["mapa_data"]:
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
                df_sorted = df.sort_values("Distancia_km").head(num_estaciones).copy()
                
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
                df_display = df_sorted[['Id', 'Nombre Municipio', 'Nombre Departamento', 'Distancia_km']].copy()
                df_display.rename(columns={'Distancia_km': 'Distancia (km)'}, inplace=True)
                st.dataframe(df_display, use_container_width=True)

            else:
                st.error("Por favor, ingresa una coordenada válida para generar el mapa.")
        except Exception as e:
            st.error(f"Error al cargar o procesar los datos de las estaciones: {e}")

# Un solo contenedor para las secciones finales (Tarjeta simple)
with st.container():
    st.markdown("### ¿Te gustaría dejar una sugerencia o comentario?")
    st.markdown("Luis Miguel Guerrero Ing Topográfico Universidad Distrital | Contacto: lmguerrerov@udistrital.edu.co | Apoyame: https://ko-fi.com/osirias" )
    st.info("¿Te es de utilidad la pagina? ¿Quieres hacer una donación por Nequi?")
    st.image("https://iili.io/FiCdWfj.jpg", width=300)
