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
import urllib.parse # Importamos para codificar el texto para la URL

# Configuració de la pàgina
st.set_page_config(
    page_title="Herramienta GNSS",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Títol principal de l'aplicació
st.title("📡 Herramienta GNSS - Consulta y Descarga de Efemérides IGS")
st.markdown("---")

# Funció per calcular el número de setmana GPS i el dia de l'any
def calculate_gps_week_number(date):
    """
    Calcula el número de setmana i dia GPS a partir d'una data.
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
    Verifica si una URL és accessible.
    """
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def download_file(url, local_path):
    """
    Descàrrega un fitxer des d'una URL.
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

def download_efemerides(date, folder_path, download_precise, download_rapid):
    """
    Descàrrega efemèrides precises i ràpides segons la selecció.
    """
    gps_week, gps_week_number, day_of_year, year = calculate_gps_week_number(date)
    
    files_to_download = []
    if download_precise:
        precise_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/JAX0MGXFIN_{year}{day_of_year:03d}0000_01D_05M_ORB.SP3.gz"
        files_to_download.append((precise_url, 'Precisas', 'gz'))
    
    if download_rapid:
        rapid_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/igr{gps_week_number}.sp3.Z"
        files_to_download.append((rapid_url, 'Rápidas', 'Z'))
    
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

# Secció per descarregar efemèrides amb checkboxes
st.sidebar.markdown("### 🗓️ Descargar Efemérides")
selected_date = st.sidebar.date_input("Seleccionar fecha", datetime.today())
download_precise = st.sidebar.checkbox("Descargar Efemérides Precisas JAX", value=True)
download_rapid = st.sidebar.checkbox("Descargar Efemérides Rápidas", value=False)

# Lògica de descàrrega integrada en el botó
if st.sidebar.button("🔽 Descargar Efemérides"):
    if not download_precise and not download_rapid:
        st.sidebar.warning("Por favor, selecciona al menos un tipo de efemérides para descargar.")
    else:
        with st.spinner("Descargando y procesando..."):
            tmpdir = tempfile.mkdtemp()
            download_status = download_efemerides(selected_date, tmpdir, download_precise, download_rapid)
            
            st.subheader("Estado de la descarga:")
            
            # Mostra el resultat de la descàrrega en el cos principal
            for info in download_status:
                if info["status"] == "Descargado":
                    st.success(f"✅ {info['label']} ({info['filename']}) descargado.")
                    # Proporciona un botó de descàrrega per al fitxer descarregat
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
            
            # Missatge final
            st.info("Confío en que este programa le será de gran utilidad y cumpla con sus expectativas.")
            shutil.rmtree(tmpdir)


st.sidebar.markdown("---")

# Secció per cercar estacions
st.sidebar.markdown("### 📍 Coordenadas para búsqueda de estaciones")
coord_format = st.sidebar.selectbox(
    "Formato de coordenadas",
    ["Decimal Geográficas", "Origen Nacional"] # Nombre cambiado
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
            proj = pyproj.Transformer.from_crs("EPSG:3116", "EPSG:4326", always_xy=True)
            lon_decimal, lat_decimal = proj.transform(este, norte)
            user_coord = (lat_decimal, lon_decimal)
        except Exception as e:
            st.error(f"Error en la conversión de coordenadas: {e}")

num_estaciones = st.sidebar.slider("Número de estaciones cercanas", 1, 10, 5)

# ---- CONTINGUT PRINCIPAL ----
st.subheader("🗺️ Estaciones GNSS más cercanas")
st.markdown("Las estaciones cercanas se calculan con base en un conjunto de coordenadas de referencia.")

# Botó per generar el mapa
if st.button("🗺️ Generar Mapa"):
    # Càrrega de dades de les estacions
    csv_url = "https://raw.githubusercontent.com/lmiguerrero/descargar-efemerides-gnss/main/Coordenadas.csv"
    try:
        df = pd.read_csv(csv_url)
        
        if user_coord is not None:
            # Lògica de càlcul de distància i ordenament
            # S'utilitzen les columnes 'Latitud' i 'Longitud' del CSV
            df["Distancia_km"] = df.apply(
                lambda row: geodesic(user_coord, (row['Latitud'], row['Longitud'])).kilometers, axis=1
            )
            df_sorted = df.sort_values("Distancia_km").head(num_estaciones)
            
            # Crea la taula amb les dades
            st.markdown("### 📌 Estaciones más cercanas:")
            
            # Formata les columnes per a la visualització
            table_data = []
            headers = ['Id', 'Nombre Municipio', 'Nombre Departamento', 'Norte', 'Este', 'Distancia']
            table_data.append(headers)

            for index, row in df_sorted.iterrows():
                # Construeix la URL amb l'àlies de l'estació
                base_url = "https://www.colombiaenmapas.gov.co/?e=-70.73413803218989,4.446062377553575,-70.60178711055921,4.542923924561411,4686&b=igac&u=0&t=25&servicio=6&estacion="
                alias_link = f"[{row['Id']}]({base_url}{row['Id']})"

                # Formata els valors
                norte = f"{row['Norte']:.3f}"
                este = f"{row['Este']:.3f}"
                distancia = f"{row['Distancia_km']:.2f} km"
                
                table_data.append([alias_link, row['Nombre Municipio'], row['Nombre Departamento'], norte, este, distancia])

            # Mostra la taula usant markdown amb un format simple
            markdown_table = "| " + " | ".join(headers) + " |\n"
            markdown_table += "|---" * len(headers) + "|\n"
            for row in table_data[1:]:
                markdown_table += "| " + " | ".join(row) + " |\n"
            st.markdown(markdown_table, unsafe_allow_html=True)

            # Codi del mapa
            st.markdown("### 🗺️ Ver mapa de estaciones")
            
            # Mapea las columnas para pydeck
            station_map_data = pd.DataFrame({
                "lat": df_sorted["Latitud"], # Usa la columna Latitud del CSV
                "lon": df_sorted["Longitud"], # Usa la columna Longitud del CSV
                "name": df_sorted["Nombre Municipio"],
                "id": df_sorted["Id"],
                "department": df_sorted["Nombre Departamento"],
                "distance": df_sorted["Distancia_km"]
            })
            
            # Agrega la coordenada del usuario al mapa para que aparezca como un punto diferente
            user_point_df = pd.DataFrame({
                "lat": [user_coord[0]],
                "lon": [user_coord[1]],
                "name": ["Ubicación del Usuario"],
                "distance": [0.0]
            })

            # Crea la capa de puntos para las estacions
            station_layer = pdk.Layer(
                "ScatterplotLayer",
                data=station_map_data,
                get_position=["lon", "lat"],
                get_radius=3000,
                get_fill_color=[255, 140, 0, 200],  # Color per a les estacions
                pickable=True,
                tooltip={
                    "html": "<b>ID:</b> {id}<br/><b>Municipio:</b> {name}<br/><b>Departamento:</b> {department}",
                    "style": {"color": "white"}
                }
            )

            # Crea la capa d'etiquetes de text per a les estacions
            text_layer = pdk.Layer(
                "TextLayer",
                data=station_map_data,
                get_position=["lon", "lat"],
                get_text="id",
                get_color=[0, 0, 0, 255], # Color negre per al text
                get_size=10,
                get_alignment_baseline="'bottom'",
                get_pixel_offset=[0, -10],
            )
            
            # Crea la capa de puntos para la ubicació de l'usuari amb transparència
            user_layer = pdk.Layer(
                "ScatterplotLayer",
                data=user_point_df,
                get_position=["lon", "lat"],
                get_radius=5000, # Una mica més gran perquè es noti
                get_fill_color=[255, 0, 0, 150], # Vermell brillant per a la ubicació de l'usuari, amb transparència
                pickable=True,
                tooltip={"text": "{name}"}
            )

            # Configura l'estat inicial de la vista del mapa
            view_state = pdk.ViewState(
                latitude=user_coord[0],
                longitude=user_coord[1],
                zoom=6,
                pitch=0 # Configurat perquè la vista sigui plana
            )
            
            # Mostra el mapa en l'aplicació
            st.pydeck_chart(pdk.Deck(
                layers=[station_layer, text_layer, user_layer], 
                initial_view_state=view_state,
                map_style="light" # Fons d'OpenStreetMap
            ))

        else:
            st.error("Por favor, ingresa una coordenada válida para generar el mapa.")

    except Exception as e:
        st.error(f"Error al cargar o procesar los datos de las estaciones: {e}")
        st.warning("Asegúrate de que la URL del archivo CSV es correcta y el formato es válido, y de que el archivo contiene las columnas 'Latitud' y 'Longitud'.")

st.markdown("---")
# Secció de suggeriments amb link mailto
st.markdown("### 💬 Dejar una sugerencia")
st.markdown("Haz clic en el siguiente enlace para enviarme un correo electrónico con tus sugerencias.")

st.markdown("---")
st.markdown("Luis Miguel Guerrero Ing Topográfico Universidad Distrital | Contacto: lmguerrerov@udistrital.edu.co")
