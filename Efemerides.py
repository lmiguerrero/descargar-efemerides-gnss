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

# Título principal
st.set_page_config(page_title="GNSS Tool - Efemérides y Estaciones Cercanas", layout="centered")
st.title("📡 Herramienta GNSS - Consulta y Descarga de Efemérides IGS")

st.markdown("---")

# Función para calcular el nombre del archivo SP3 y el día GPS
def gps_day_from_date(date):
    gps_start = datetime(1980, 1, 6)
    delta = date - gps_start
    gps_week = delta.days // 7
    gps_day = delta.days % 7
    return gps_week, gps_day

def build_igs_url(date):
    gps_week, gps_day = gps_day_from_date(date)
    year = date.strftime('%Y')
    doy = date.strftime('%j')
    base_url = f"https://igs.bkg.bund.de/root_ftp/IGS/BRDC/{year}/{doy}/"
    file_name = f"brdc{doy}0.{str(date.year)[2:]}n.gz"
    return base_url + file_name, file_name

def download_and_extract_sp3(url, filename):
    tmpdir = tempfile.mkdtemp()
    filepath = os.path.join(tmpdir, filename)
    r = requests.get(url)
    if r.status_code != 200:
        return None, None
    with open(filepath, 'wb') as f:
        f.write(r.content)
    extracted = filepath[:-3]
    with gzip.open(filepath, 'rb') as f_in, open(extracted, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    return extracted, filename[:-3]

# ---- SIDEBAR INPUTS ----
st.sidebar.header("📥 Ingresar parámetros")

# Fecha para efemérides
selected_date = st.sidebar.date_input("Seleccionar fecha para efemérides IGS", datetime.today())

# Coordenadas
st.sidebar.markdown("### 📍 Coordenadas para búsqueda de estaciones")
coord_format = st.sidebar.selectbox("Formato de coordenadas", ["Decimal Geográficas", "Magna-SIRGAS (Este, Norte)"])

if coord_format == "Decimal Geográficas":
    lat = st.sidebar.number_input("Latitud", format="%.8f")
    lon = st.sidebar.number_input("Longitud", format="%.8f")
    user_coord = (lat, lon)
else:
    este = st.sidebar.number_input("Este (X)", format="%.2f")
    norte = st.sidebar.number_input("Norte (Y)", format="%.2f")
    import pyproj
    proj = pyproj.Transformer.from_crs("EPSG:3116", "EPSG:4326", always_xy=True)
    lon, lat = proj.transform(este, norte)
    user_coord = (lat, lon)

num_estaciones = st.sidebar.slider("Número de estaciones cercanas", 1, 10, 5)

# ---- EFEMÉRIDES ----
st.subheader("📥 Descargar Efemérides SP3 (IGS)")

url, filename = build_igs_url(selected_date)
st.markdown(f"**URL del archivo comprimido (.gz):** [Abrir enlace]({url})")

if st.button("🔽 Descargar y descomprimir archivo .sp3"):
    with st.spinner("Descargando y descomprimiendo..."):
        extracted_path, extracted_name = download_and_extract_sp3(url, filename)
        if extracted_path:
            with open(extracted_path, "rb") as file:
                st.download_button(label="📄 Descargar archivo SP3", data=file, file_name=extracted_name)
        else:
            st.error("No se pudo descargar el archivo. Revisa la fecha o intenta más tarde.")

# ---- ESTACIONES CERCANAS ----
st.subheader("🗺️ Estaciones GNSS más cercanas")

st.markdown("Las estaciones cercanas se calculan con base en un conjunto de coordenadas de referencia.")

csv_url = "https://raw.githubusercontent.com/lmiguerrero/descargar-efemerides-gnss/main/Coordenadas.csv"
df = pd.read_csv(csv_url)

df["Coord"] = list(zip(df["Norte"], df["Este"]))
df["LatLon"] = df["Coord"].apply(lambda x: pyproj.Transformer.from_crs("EPSG:3116", "EPSG:4326", always_xy=True).transform(x[1], x[0]))
df["Distancia_km"] = df["LatLon"].apply(lambda x: geodesic(user_coord, (x[1], x[0])).kilometers)
df_sorted = df.sort_values("Distancia_km").head(num_estaciones)

st.markdown("### 📌 Estaciones más cercanas:")

for idx, row in df_sorted.iterrows():
    nombre = row["Nombre Municipio"]
    dpto = row["Nombre Departamento"]
    lat, lon = row["LatLon"]
    dist = row["Distancia_km"]
    enlace = f"https://geoportal.igac.gov.co/sites/geoportal.igac.gov.co/files/archivos_gdb/GNSS/{nombre.replace(' ', '%20')}.zip"
    st.markdown(f"- **{nombre}, {dpto}** – {dist:.2f} km – [Descargar GNSS]({enlace})")

# Mapa (opcional)
st.markdown("### 🗺️ Ver mapa de estaciones")
import pydeck as pdk

layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_sorted,
    get_position="LatLon",
    get_radius=3000,
    get_fill_color=[180, 0, 200, 140],
    pickable=True,
)

view_state = pdk.ViewState(latitude=user_coord[0], longitude=user_coord[1], zoom=6)
st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))

st.success("✅ Aplicación lista")
