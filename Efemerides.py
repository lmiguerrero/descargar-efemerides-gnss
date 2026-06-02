import streamlit as st
from datetime import datetime, timedelta
import requests
import os
import shutil
import tempfile
import zipfile

# Configuración de página
st.set_page_config(
    page_title="Celeste",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS para el diseño de "Cuadrito" (Card) ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f4f7f9;
    }
    /* Estilo del contenedor principal (el cuadrito) */
    .main-card {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 1px solid #e0e6ed;
        margin-top: 20px;
    }
    .stButton>button {
        width: 100%;
        background-color: #007bff;
        color: white;
        border-radius: 8px;
        padding: 12px;
        font-weight: bold;
    }
    h1 {
        text-align: center;
        color: #1e293b;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Lógica de descarga (Se mantiene igual) ---
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
        return False

# --- Interfaz de Usuario ---

# Logo Superior
st.image("https://fupad.pythonanywhere.com/static/efemerides.jpg", use_column_width=True)

st.title("Celeste")

# Contenedor tipo "Cuadrito"
with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    st.subheader("Descargar Efemérides GNSS")
    
    date_range = st.date_input(
        "Seleccionar rango de fechas", 
        value=(datetime.today() - timedelta(days=7), datetime.today()), 
        max_value=datetime.today()
    )
    
    col1, col2 = st.columns(2)
    with col1:
        download_precise = st.checkbox("Efemérides Precisas JAX", value=True)
        download_rapid = st.checkbox("Efemérides Rápidas", value=False)
    with col2:
        download_gfz = st.checkbox("Efemérides Precisas GFZ", value=False)

    if st.button("🚀 Descargar Efemérides"):
        if not date_range or len(date_range) != 2:
            st.error("Selecciona un rango válido.")
        else:
            start_date, end_date = date_range
            delta = end_date - start_date
            total_days = delta.days + 1
            
            tmpdir = tempfile.mkdtemp()
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            
            files_found = 0
            for i in range(total_days):
                current_date = start_date + timedelta(days=i)
                gps_week, gps_day, day_of_year, year = calculate_gps_week_number(current_date)
                
                # URLs y lógicas de descarga simplificadas para el ejemplo
                # (Aquí iría tu lógica de 'download_files_for_date')
                # ...
                
                progress_bar.progress((i + 1) / total_days)
            
            st.success("¡Proceso completado!")
            # Botón de descarga del ZIP (implementación similar a la anterior)
            
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br><center><small>Celeste GNSS Tools v2.0</small></center>", unsafe_allow_html=True)
