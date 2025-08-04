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

# Configuración de la página
st.set_page_config(
    page_title="Herramienta GNSS",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal de la aplicación
st.title("📡 Herramienta GNSS - Consulta y Descarga de Efemérides IGS")
st.markdown("---")

# Función para calcular el número de semana GPS y el día del año
def calculate_gps_week_number(date):
    """
    Calcula el número de semana y día GPS a partir de una fecha.
    """
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
    """
    Verifica si una URL es accesible.
    """
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def download_file(url, local_path):
    """
    Descarga un archivo desde una URL.
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

def download_efemerides(date, folder_path):
    """
    Descarga efemérides precisas y rápidas.
    """
    gps_week, gps_week_number, day_of_year, year = calculate_gps_week_number(date)
    
    # URLs de descarga basadas en tu código original de Python
    precise_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/JAX0MGXFIN_{year}{day_of_year:03d}0000_01D_05M_ORB.SP3.gz"
    rapid_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/igr{gps_week_number}.sp3.Z"
    
    files_to_download = [
        (precise_url, 'Precisas', 'gz'),
        (rapid_url, 'Rápidas', 'Z')
    ]
    
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

# ---- SIDEBAR INPUTS ----
st.sidebar.header("📥 Ingresar parámetros")

# Sección para descargar efemérides
st.sidebar.markdown("### 🗓️ Descargar Efemérides")
selected_date = st.sidebar.date_input("Seleccionar fecha", datetime.today())

# Lógica de descarga integrada en el botón
if st.sidebar.button("🔽 Descargar Efemérides"):
    with st.spinner("Descargando y procesando..."):
        tmpdir = tempfile.mkdtemp()
        download_status = download_efemerides(selected_date, tmpdir)
        
        st.subheader("Estado de la descarga:")
        
        # Muestra el resultado de la descarga en el cuerpo principal
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
                
        # Mensaje final
        st.info("Confío en que este programa le será de gran utilidad y cumpla con sus expectativas.")
        shutil.rmtree(tmpdir)


st.sidebar.markdown("---")

# Sección para buscar estaciones
st.sidebar.markdown("### 📍 Coordenadas para búsqueda de estaciones")
coord_format = st.sidebar.selectbox(
    "Formato de coordenadas",
    ["Decimal Geográficas", "Magna-SIRGAS (Este, Norte)"]
)

user_coord = None
if coord_format == "Decimal Geográficas":
    lat = st.sidebar.number_input("Latitud", format="%.8f", key="lat_input")
    lon = st.sidebar.number_input("Longitud", format="%.8f", key="lon_input")
    if lat != 0.0 or lon != 0.0:
        user_coord = (lat, lon)
else:
    este = st.sidebar.number_input("Este (X)", format="%.2f", key="este_input")
    norte = st.sidebar.number_input("Norte (Y)", format="%.2f", key="norte_input")
    if este != 0.0 or norte != 0.0:
        try:
            # Aquí se asume que si se ingresan coordenadas planas, se necesita pyproj para transformarlas
            # y que el usuario espera ver el punto convertido en el mapa.
            proj = pyproj.Transformer.from_crs("EPSG:3116", "EPSG:4326", always_xy=True)
            lon_decimal, lat_decimal = proj.transform(este, norte)
            user_coord = (lat_decimal, lon_decimal)
        except Exception as e:
            st.error(f"Error en la conversión de coordenadas: {e}")

num_estaciones = st.sidebar.slider("Número de estaciones cercanas", 1, 10, 5)

# ---- CONTENIDO PRINCIPAL ----
st.subheader("🗺️ Estaciones GNSS más cercanas")
st.markdown("Las estaciones cercanas se calculan con base en un conjunto de coordenadas de referencia.")

# Botón para generar el mapa
if st.button("🗺️ Generar Mapa"):
    # Carga de datos de las estaciones
    csv_url = "https://raw.githubusercontent.com/lmiguerrero/descargar-efemerides-gnss/main/Coordenadas.csv"
    try:
        df = pd.read_csv(csv_url)
        
        if user_coord is not None:
            # Lógica de cálculo de distancia y ordenamiento
            # Se usan las columnas 'Latitud' y 'Longitud' del CSV
            df["Distancia_km"] = df.apply(
                lambda row: geodesic(user_coord, (row['Latitud'], row['Longitud'])).kilometers, axis=1
            )
            df_sorted = df.sort_values("Distancia_km").head(num_estaciones)
            
            # Crear la tabla con los datos
            st.markdown("### 📌 Estaciones más cercanas:")
            
            # Formatear las columnas para la visualización
            table_data = []
            headers = ['Id', 'Nombre Municipio', 'Nombre Departamento', 'Norte', 'Este', 'Distancia']
            table_data.append(headers)

            for index, row in df_sorted.iterrows():
                # Construir la URL con el alias de la estación
                base_url = "https://www.colombiaenmapas.gov.co/?e=-70.73413803218989,4.446062377553575,-70.60178711055921,4.542923924561411,4686&b=igac&u=0&t=25&servicio=6&estacion="
                alias_link = f"[{row['Id']}]({base_url}{row['Id']})"

                # Formatear los valores
                norte = f"{row['Norte']:.3f}"
                este = f"{row['Este']:.3f}"
                distancia = f"{row['Distancia_km']:.2f} km"
                
                table_data.append([alias_link, row['Nombre Municipio'], row['Nombre Departamento'], norte, este, distancia])

            # Mostrar la tabla usando markdown con un formato simple
            markdown_table = "| " + " | ".join(headers) + " |\n"
            markdown_table += "|---" * len(headers) + "|\n"
            for row in table_data[1:]:
                markdown_table += "| " + " | ".join(row) + " |\n"
            st.markdown(markdown_table, unsafe_allow_html=True)

            # Código del mapa
            st.markdown("### 🗺️ Ver mapa de estaciones")
            
            # Mapea las columnas para pydeck
            station_map_data = pd.DataFrame({
                "lat": df_sorted["Latitud"], # Usar la columna Latitud del CSV
                "lon": df_sorted["Longitud"], # Usar la columna Longitud del CSV
                "name": df_sorted["Nombre Municipio"],
                "distance": df_sorted["Distancia_km"]
            })
            
            # Agrega la coordenada del usuario al mapa para que aparezca como un punto diferente
            user_point_df = pd.DataFrame({
                "lat": [user_coord[0]],
                "lon": [user_coord[1]],
                "name": ["Ubicación del Usuario"],
                "distance": [0.0]
            })

            # Crea la capa de puntos para las estaciones
            station_layer = pdk.Layer(
                "ScatterplotLayer",
                data=station_map_data,
                get_position=["lon", "lat"],
                get_radius=3000,
                get_fill_color=[255, 140, 0, 200],  # Color para las estaciones
                pickable=True,
                tooltip={"text": "{name}\nDistancia: {distance:.2f} km"}
            )
            
            # Crea la capa de puntos para la ubicación del usuario
            user_layer = pdk.Layer(
                "ScatterplotLayer",
                data=user_point_df,
                get_position=["lon", "lat"],
                get_radius=5000, # Un poco más grande para que se note
                get_fill_color=[255, 0, 0, 255], # Rojo brillante para la ubicación del usuario
                pickable=True,
                tooltip={"text": "{name}"}
            )

            # Configura el estado inicial de la vista del mapa
            view_state = pdk.ViewState(
                latitude=user_coord[0],
                longitude=user_coord[1],
                zoom=6,
                pitch=0 # Configurado para que la vista sea plana
            )
            
            # Muestra el mapa en la aplicación
            st.pydeck_chart(pdk.Deck(
                layers=[station_layer, user_layer], 
                initial_view_state=view_state,
                map_style="light", # Fondo de OpenStreetMap
                tooltip={"html": "<b>{name}</b><br/>Distancia: {distance:.2f} km", "style": {"color": "white"}}
            ))

        else:
            st.error("Por favor, ingresa una coordenada válida para generar el mapa.")

    except Exception as e:
        st.error(f"Error al cargar o procesar los datos de las estaciones: {e}")
        st.warning("Asegúrate de que la URL del archivo CSV es correcta y el formato es válido, y de que el archivo contiene las columnas 'Latitud' y 'Longitud'.")

st.markdown("---")
st.markdown("Luis Miguel Guerrero Ing Topográfico Universidad Distrital | Contacto: lmguerrerov@udistrital.edu.co")
