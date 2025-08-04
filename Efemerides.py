import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from geopy.distance import geodesic
import requests
import os
import gzip
import shutil
import tempfile
import pydeck as pdk
import pyproj
import urllib.parse  # Importamos para codificar el texto para la URL

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Herramienta GNSS",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal de la aplicación
st.title("📡 Herramienta GNSS - Consulta y Descarga de Efemérides IGS")
st.markdown("---")

# Función para calcular la semana GPS y el día del año a partir de una fecha
def calculate_gps_week_number(date):
    """
    Calcula el número de la semana GPS, el día de la semana GPS,
    el día del año y el año a partir de una fecha determinada.
    """
    date_format = "%Y-%m-%d"
    target_date = datetime.strptime(str(date), date_format)
    gps_start_date = datetime(1980, 1, 6)
    days_since_start = (target_date - gps_start_date).days
    gps_week = days_since_start // 7
    gps_day_of_week = days_since_start % 7
    gps_week_number = gps_week * 10 + gps_day_of_week  # Formato GPS week-day
    day_of_year = target_date.timetuple().tm_yday
    year = target_date.year
    return gps_week, gps_week_number, day_of_year, year

def check_url(url):
    """
    Verifica si una URL está accesible enviando una petición HEAD.
    Retorna True si el código de estado es 200 (OK), de lo contrario, False.
    """
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def download_file(url, local_path):
    """
    Descarga un archivo desde una URL a una ruta local especificada.
    Muestra un mensaje de error si la descarga falla.
    """
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
    """
    Gestiona la descarga de efemérides según las opciones seleccionadas por el usuario.
    Construye las URLs de descarga para los diferentes tipos de efemérides (JAX, Rápidas, GFZ).
    """
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

# ---- INPUTS EN LA BARRA LATERAL (SIDEBAR) ----
st.sidebar.header("📥 Ingresar parámetros")

# Sección para descargar efemérides con casillas de verificación
st.sidebar.markdown("### 🗓️ Descargar Efemérides")
selected_date = st.sidebar.date_input("Seleccionar fecha", datetime.today())
download_precise = st.sidebar.checkbox("Descargar Efemérides Precisas JAX", value=True)
download_rapid = st.sidebar.checkbox("Descargar Efemérides Rápidas", value=False)
download_gfz = st.sidebar.checkbox("Descargar Efemérides Precisas GFZ", value=False)  # Nueva opción para GFZ

# Lógica de descarga que se activa con el botón
if st.sidebar.button("🔽 Descargar Efemérides"):
    if not download_precise and not download_rapid and not download_gfz:
        st.sidebar.warning("Por favor, selecciona al menos un tipo de efemérides para descargar.")
    else:
        with st.spinner("Descargando y procesando..."):
            tmpdir = tempfile.mkdtemp()
            download_status = download_efemerides(selected_date, tmpdir, download_precise, download_rapid, download_gfz)
            
            st.subheader("Estado de la descarga:")
            
            # Muestra el resultado de la descarga en el cuerpo principal de la aplicación
            for info in download_status:
                if info["status"] == "Descargado":
                    st.success(f"✅ {info['label']} ({info['filename']}) descargado.")
                    # Proporciona un botón de descarga para el archivo descargado
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
            
            # Mensaje final después de la descarga
            st.info("Confío en que este programa le será de gran utilidad y cumpla con sus expectativas.")
            shutil.rmtree(tmpdir)


st.sidebar.markdown("---")

# Sección para buscar estaciones GNSS cercanas
st.sidebar.markdown("### 📍 Coordenadas para búsqueda de estaciones")
coord_format = st.sidebar.selectbox(
    "Formato de coordenadas",
    ["Grados, Minutos, Segundos", "Origen Nacional"]
)

user_coord = None
if coord_format == "Grados, Minutos, Segundos":
    st.sidebar.markdown("---")
    st.sidebar.subheader("Latitud")
    lat_deg = st.sidebar.number_input("Grados", min_value=-90, max_value=90, value=0, key="lat_deg_input")
    lat_min = st.sidebar.number_input("Minutos", min_value=0, max_value=59, value=0, key="lat_min_input")
    lat_sec = st.sidebar.number_input("Segundos (con decimales)", min_value=0.0, max_value=59.999999, value=0.0, format="%.6f", key="lat_sec_input")
    
    st.sidebar.subheader("Longitud")
    lon_deg = st.sidebar.number_input("Grados", min_value=-180, max_value=180, value=0, key="lon_deg_input")
    lon_min = st.sidebar.number_input("Minutos", min_value=0, max_value=59, value=0, key="lon_min_input")
    lon_sec = st.sidebar.number_input("Segundos (con decimales)", min_value=0.0, max_value=59.999999, value=0.0, format="%.6f", key="lon_sec_input")
    
    # Conversión de grados, minutos y segundos a grados decimales
    lat = lat_deg + lat_min / 60 + lat_sec / 3600
    lon = lon_deg + lon_min / 60 + lon_sec / 3600

    if lat != 0.0 or lon != 0.0:
        user_coord = (lat, lon)
else:
    este = st.sidebar.number_input("Este (X)", format="%.2f", key="este_input")
    norte = st.sidebar.number_input("Norte (Y)", format="%.2f", key="norte_input")
    if este != 0.0 or norte != 0.0:
        try:
            # Transformación de coordenadas de Origen Nacional (EPSG:3116) a WGS84 (EPSG:4326)
            proj = pyproj.Transformer.from_crs("EPSG:3116", "EPSG:4326", always_xy=True)
            lon_decimal, lat_decimal = proj.transform(este, norte)
            user_coord = (lat_decimal, lon_decimal)
        except Exception as e:
            st.error(f"Error en la conversión de coordenadas: {e}")

num_estaciones = st.sidebar.slider("Número de estaciones cercanas", 1, 10, 5)

# Opciones de fondo de mapa para pydeck
# Diccionario que separa los estilos de mapas nativos y los que usan TileLayer
MAP_STYLES_NATIVE = {
    "Fondo Claro (Predeterminado)": "light",
    "Fondo Oscuro": "dark",
    "Satélite": "satellite",
    "Carreteras": "road"
}

MAP_STYLES_TILES = {
    "CartoDB Claro (Positron)": "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
    "CartoDB Oscuro (Dark Matter)": "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png",
    "Satélite (Esri)": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "Relieve (Stamen)": "https://stamen-tiles.a.ssl.fastly.net/terrain-background/{z}/{x}/{y}.png",
    "Mapas de Carreteras (OpenStreetMap)": "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
}

# Unimos ambos diccionarios para el selectbox
MAP_STYLES = {**MAP_STYLES_NATIVE, **MAP_STYLES_TILES}

# Selector de fondo de mapa en la barra lateral
selected_map_style_name = st.sidebar.selectbox("🗺️ Fondo del mapa", list(MAP_STYLES.keys()), index=0)
selected_map_style_value = MAP_STYLES[selected_map_style_name]


# ---- CONTENIDO PRINCIPAL ----
st.subheader("🗺️ Estaciones GNSS más cercanas")
st.markdown("Las estaciones cercanas se calculan con base en un conjunto de coordenadas de referencia.")

# Botón para generar el mapa y la tabla
if st.button("🗺️ Generar Mapa"):
    # Carga de datos de las estaciones desde un archivo CSV
    csv_url = "https://raw.githubusercontent.com/lmiguerrero/descargar-efemerides-gnss/main/Coordenadas.csv"
    try:
        df = pd.read_csv(csv_url)
        
        if user_coord is not None:
            # Lógica para calcular la distancia y ordenar las estaciones
            df["Distancia_km"] = df.apply(
                lambda row: geodesic(user_coord, (row['Latitud'], row['Longitud'])).kilometers, axis=1
            )
            df_sorted = df.sort_values("Distancia_km").head(num_estaciones)
            
            # Crea la tabla con las estaciones más cercanas
            st.markdown("### 📌 Estaciones más cercanas:")
            
            # Formatea las columnas para la visualización en la tabla
            table_data = []
            headers = ['Id', 'Nombre Municipio', 'Nombre Departamento', 'Norte', 'Este', 'Distancia']
            table_data.append(headers)

            for index, row in df_sorted.iterrows():
                # Construye la URL con el alias de la estación para el mapa
                base_url = "https://www.colombiaenmapas.gov.co/?e=-70.73413803218989,4.446062377553575,-70.6017871105921,4.542923924561411,4686&b=igac&u=0&t=25&servicio=6&estacion="
                alias_link = f"[{row['Id']}]({base_url}{row['Id']})"

                # Formatea los valores de las coordenadas y la distancia
                norte = f"{row['Norte']:.3f}"
                este = f"{row['Este']:.3f}"
                distancia = f"{row['Distancia_km']:.2f} km"
                
                table_data.append([alias_link, row['Nombre Municipio'], row['Nombre Departamento'], norte, este, distancia])

            # Muestra la tabla usando Markdown
            markdown_table = "| " + " | ".join(headers) + " |\n"
            markdown_table += "|---" * len(headers) + "|\n"
            for row in table_data[1:]:
                markdown_table += "| " + " | ".join(row) + " |\n"
            st.markdown(markdown_table, unsafe_allow_html=True)

            # Código para generar el mapa interactivo
            st.markdown("### 🗺️ Ver mapa de estaciones")
            
            # Mapea las columnas para el formato de pydeck
            station_map_data = pd.DataFrame({
                "lat": df_sorted["Latitud"],
                "lon": df_sorted["Longitud"],
                "name": df_sorted["Nombre Municipio"],
                "id": df_sorted["Id"],
                "department": df_sorted["Nombre Departamento"],
                "distance": df_sorted["Distancia_km"]
            })
            
            # Agrega la coordenada del usuario al mapa como un punto de color diferente
            user_point_df = pd.DataFrame({
                "lat": [user_coord[0]],
                "lon": [user_coord[1]],
                "name": ["Ubicación del Usuario"],
                "distance": [0.0]
            })

            # Creamos las capas
            layers = []
            
            # Lógica para determinar el estilo del mapa y agregar la capa de fondo
            map_style_to_use = None
            if selected_map_style_name in MAP_STYLES_NATIVE:
                # Si es un estilo nativo de Pydeck, lo usamos directamente en el map_style del Deck
                map_style_to_use = selected_map_style_value
            elif selected_map_style_name in MAP_STYLES_TILES:
                # Si es un estilo de servidor de azulejos, creamos una capa TileLayer
                tile_layer = pdk.Layer(
                    "TileLayer",
                    data=selected_map_style_value
                )
                layers.append(tile_layer)

            # Agregamos las capas de puntos y etiquetas a la lista
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=station_map_data,
                get_position=["lon", "lat"],
                get_radius=3000,
                get_fill_color=[255, 140, 0, 200],
                pickable=True,
                tooltip={
                    "html": "<b>ID:</b> {id}<br/><b>Municipio:</b> {name}<br/><b>Departamento:</b> {department}",
                    "style": {"color": "white"}
                }
            ))

            layers.append(pdk.Layer(
                "TextLayer",
                data=station_map_data,
                get_position=["lon", "lat"],
                get_text="id",
                get_color=[0, 0, 0, 255],
                get_size=10,
                get_alignment_baseline="'bottom'",
                get_pixel_offset=[0, -10],
            ))
            
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=user_point_df,
                get_position=["lon", "lat"],
                get_radius=5000,
                get_fill_color=[255, 0, 0, 150],
                pickable=True,
                tooltip={"text": "{name}"}
            ))

            # Configura el estado inicial de la vista del mapa, centrado en el usuario
            view_state = pdk.ViewState(
                latitude=user_coord[0],
                longitude=user_coord[1],
                zoom=6,
                pitch=0
            )

            # Muestra el mapa en la aplicación
            st.pydeck_chart(pdk.Deck(
                layers=layers, 
                initial_view_state=view_state,
                map_style=map_style_to_use
            ))

        else:
            st.error("Por favor, ingresa una coordenada válida para generar el mapa.")

    except Exception as e:
        st.error(f"Error al cargar o procesar los datos de las estaciones: {e}")
        st.warning("Asegúrate de que la URL del archivo CSV es correcta y el formato es válido, y de que el archivo contiene las columnas 'Latitud' y 'Longitud'.")

st.markdown("---")
# Sección de sugerencias con enlace 'mailto'
st.markdown("### 💬 Dejar una sugerencia")
st.markdown("Haz clic en el siguiente enlace para enviarme un correo electrónico con tus sugerencias.")

st.markdown("---")
st.markdown("Luis Miguel Guerrero Ing Topográfico Universidad Distrital | Contacto: lmguerrerov@udistrital.edu.co")
