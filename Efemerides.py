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
import pyproj
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

# Función para calcular el día GPS
def gps_day_from_date(date):
    """
    Calcula la semana y el día GPS a partir de una fecha.
    """
    gps_start = datetime(1980, 1, 6)
    delta = date - gps_start
    gps_week = delta.days // 7
    gps_day = delta.days % 7
    return gps_week, gps_day

def build_brdc_url(date):
    """
    Construye la URL para descargar el archivo de efemérides BRDC de IGS.
    """
    try:
        year = date.strftime('%Y')
        doy = date.strftime('%j')
        base_url = f"https://igs.bkg.bund.de/root_ftp/IGS/BRDC/{year}/{doy}/"
        file_name = f"brdc{doy}0.{str(date.year)[2:]}n.gz"
        return base_url + file_name, file_name
    except Exception as e:
        st.error(f"Error al construir la URL de BRDC: {e}")
        return None, None

def build_precise_rapid_urls(date):
    """
    Construye las URLs para descargar efemérides precisas y rápidas.
    """
    try:
        gps_week, gps_day = gps_day_from_date(date)
        day_of_year = date.timetuple().tm_yday
        year = date.year
        
        precise_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/JAX0MGXFIN_{year}{day_of_year:03d}0000_01D_05M_ORB.SP3.gz"
        rapid_url = f"http://lox.ucsd.edu/pub/products/{gps_week}/igr{gps_week}{gps_day}.sp3.Z"
        
        return {
            "Precise": (precise_url, os.path.basename(precise_url)),
            "Rapid": (rapid_url, os.path.basename(rapid_url))
        }
    except Exception as e:
        st.error(f"Error al construir URLs de Precise/Rapid: {e}")
        return None

def download_and_extract_file(url, filename, is_compressed=True):
    """
    Descarga y extrae un archivo de una URL.
    """
    if url is None or filename is None:
        return None, None
    
    tmpdir = tempfile.mkdtemp()
    filepath = os.path.join(tmpdir, filename)
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            st.warning(f"No se pudo encontrar el archivo en la URL: {url}. Código de estado: {r.status_code}")
            return None, None
        
        with open(filepath, 'wb') as f:
            f.write(r.content)
            
        if is_compressed:
            extracted = filepath[:-len(os.path.splitext(filename)[1])]
            if filename.endswith('.gz'):
                with gzip.open(filepath, 'rb') as f_in, open(extracted, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            elif filename.endswith('.Z'):
                # .Z es un formato de compresión diferente, que puede no ser soportado nativamente
                # Aquí se simulará la descompresión para mantener la estructura
                extracted = filepath
                shutil.copyfile(filepath, extracted)
                st.warning("El formato .Z no se descomprime automáticamente. Descargue y use una herramienta externa.")
            else:
                extracted = filepath
                
            return extracted, os.path.basename(extracted)
        else:
            return filepath, filename
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión al intentar descargar el archivo: {e}")
        return None, None
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
        return None, None

# ---- SIDEBAR INPUTS ----
st.sidebar.header("📥 Ingresar parámetros")

# Sección para descargar efemérides
st.sidebar.markdown("### 🗓️ Descargar Efemérides")
selected_date = st.sidebar.date_input("Seleccionar fecha", datetime.today())
efemerides_type = st.sidebar.selectbox("Tipo de Efemérides", ["BRDC (IGS)", "Precise y Rapid (IGS)"])

# Lógica para mostrar la URL y el botón de descarga según el tipo seleccionado
if efemerides_type == "BRDC (IGS)":
    url, filename = build_brdc_url(selected_date)
    if url:
        st.sidebar.markdown(f"**URL del archivo:** [Abrir enlace]({url})")
    if st.sidebar.button("🔽 Descargar archivo BRDC"):
        if url:
            with st.spinner("Descargando y descomprimiendo..."):
                extracted_path, extracted_name = download_and_extract_file(url, filename)
                if extracted_path:
                    with open(extracted_path, "rb") as file:
                        st.download_button(
                            label=f"📄 Descargar {extracted_name}", 
                            data=file, 
                            file_name=extracted_name,
                            mime="application/octet-stream"
                        )
                    st.success("✅ Descarga y descompresión completada.")
                    shutil.rmtree(os.path.dirname(extracted_path))
                else:
                    st.error("No se pudo descargar o procesar el archivo. Revisa la fecha o intenta más tarde.")
        else:
            st.error("No se pudo construir la URL de descarga.")
            
elif efemerides_type == "Precise y Rapid (IGS)":
    urls_dict = build_precise_rapid_urls(selected_date)
    if urls_dict:
        st.sidebar.markdown(f"**URL de efemérides precisas:** [Abrir enlace]({urls_dict['Precise'][0]})")
        st.sidebar.markdown(f"**URL de efemérides rápidas:** [Abrir enlace]({urls_dict['Rapid'][0]})")
        if st.sidebar.button("🔽 Descargar archivos Precise y Rapid"):
            with st.spinner("Descargando y procesando..."):
                for name, (url, filename) in urls_dict.items():
                    extracted_path, extracted_name = download_and_extract_file(url, filename)
                    if extracted_path:
                        with open(extracted_path, "rb") as file:
                            st.download_button(
                                label=f"📄 Descargar {name} ({extracted_name})", 
                                data=file, 
                                file_name=extracted_name,
                                mime="application/octet-stream"
                            )
                        st.success(f"✅ Descarga de {name} completada.")
                        shutil.rmtree(os.path.dirname(extracted_path))
                    else:
                        st.error(f"No se pudo descargar {name}. Revisa la fecha o intenta más tarde.")


st.sidebar.markdown("---")

# Sección para buscar estaciones
st.sidebar.markdown("### 📍 Coordenadas para búsqueda de estaciones")
coord_format = st.sidebar.selectbox(
    "Formato de coordenadas",
    ["Decimal Geográficas", "Magna-SIRGAS (Este, Norte)"]
)

user_coord = None
if coord_format == "Decimal Geográficas":
    lat = st.sidebar.number_input("Latitud", format="%.8f")
    lon = st.sidebar.number_input("Longitud", format="%.8f")
    if lat != 0.0 or lon != 0.0:
        user_coord = (lat, lon)
else:
    este = st.sidebar.number_input("Este (X)", format="%.2f")
    norte = st.sidebar.number_input("Norte (Y)", format="%.2f")
    if este != 0.0 or norte != 0.0:
        try:
            proj = pyproj.Transformer.from_crs("EPSG:3116", "EPSG:4326", always_xy=True)
            lon_decimal, lat_decimal = proj.transform(este, norte)
            user_coord = (lat_decimal, lon_decimal)
        except Exception as e:
            st.error(f"Error en la conversión de coordenadas: {e}")

num_estaciones = st.sidebar.slider("Número de estaciones cercanas", 1, 10, 5)

# ---- CONTENIDO PRINCIPAL ----
st.subheader("🗺️ Estaciones GNSS más cercanas")
st.markdown("Las estaciones cercanas se calculan con base en un conjunto de coordenadas de referencia.")

# Carga de datos de las estaciones
csv_url = "https://raw.githubusercontent.com/lmiguerrero/descargar-efemerides-gnss/main/Coordenadas.csv"
try:
    df = pd.read_csv(csv_url)
    
    if user_coord is not None:
        # Lógica de cálculo de distancia y ordenamiento
        transformer_4326_to_3116 = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3116", always_xy=True)
        
        # Convertir coordenadas del CSV a Lat/Lon para el cálculo de distancia geodesic
        df['LatLon'] = df.apply(
            lambda row: transformer_4326_to_3116.transform(row['Este'], row['Norte'], direction='INVERSE'), axis=1
        )
        
        df["Distancia_km"] = df["LatLon"].apply(
            lambda x: geodesic(user_coord, (x[1], x[0])).kilometers
        )
        df_sorted = df.sort_values("Distancia_km").head(num_estaciones)

        st.markdown("### 📌 Estaciones más cercanas:")
        for idx, row in df_sorted.iterrows():
            nombre = row["Nombre Municipio"]
            dpto = row["Nombre Departamento"]
            lat, lon = row["LatLon"]
            dist = row["Distancia_km"]
            enlace = f"https://geoportal.igac.gov.co/sites/geoportal.igac.gov.co/files/archivos_gdb/GNSS/{nombre.replace(' ', '%20')}.zip"
            st.markdown(f"- **{nombre}, {dpto}** – {dist:.2f} km – [Descargar GNSS]({enlace})")

        # Mapa de estaciones
        st.markdown("### 🗺️ Ver mapa de estaciones")
        
        # Mapea las columnas para pydeck
        map_data = pd.DataFrame({
            "lat": df_sorted["LatLon"].apply(lambda x: x[1]),
            "lon": df_sorted["LatLon"].apply(lambda x: x[0]),
            "name": df_sorted["Nombre Municipio"],
            "distance": df_sorted["Distancia_km"]
        })

        # Agrega la coordenada del usuario al mapa
        map_data.loc[len(map_data)] = {
            "lat": user_coord[0],
            "lon": user_coord[1],
            "name": "Ubicación del Usuario",
            "distance": 0.0
        }

        # Crea la capa de puntos
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_data,
            get_position=["lon", "lat"],
            get_radius=3000,
            get_fill_color=[255, 140, 0, 200],
            pickable=True,
            tooltip={"text": "{name}\nDistancia: {distance:.2f} km"}
        )

        # Configura el estado inicial de la vista del mapa
        view_state = pdk.ViewState(
            latitude=user_coord[0],
            longitude=user_coord[1],
            zoom=6,
            pitch=45
        )
        
        # Muestra el mapa en la aplicación
        st.pydeck_chart(pdk.Deck(
            layers=[layer], 
            initial_view_state=view_state,
            tooltip={"html": "<b>{name}</b><br/>Distancia: {distance:.2f} km", "style": {"color": "white"}}
        ))

except Exception as e:
    st.error(f"Error al cargar o procesar los datos de las estaciones: {e}")
    st.warning("Asegúrate de que la URL del archivo CSV es correcta y el formato es válido.")

st.success("✅ Aplicación lista")
