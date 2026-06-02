import streamlit as st
from datetime import datetime, timedelta
import requests
import os
import shutil
import tempfile
import zipfile

st.set_page_config(
    page_title="Celeste",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f4f7f9;
    }
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
        font-weight: 600;
    }
    h1 {
        text-align: center;
        color: #1e293b;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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


col_logo1, col_logo2, col_logo3 = st.columns([1, 1, 1])
with col_logo2:
    st.image("https://fupad.pythonanywhere.com/static/efemerides.jpg", width=250)

st.title("Celeste")

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

    if st.button("Descargar Efemérides"):
        if not date_range or len(date_range) != 2:
            st.error("Selecciona un rango válido.")
        elif not download_precise and not download_rapid and not download_gfz:
            st.warning("Selecciona al menos un tipo de efemérides para descargar.")
        else:
            start_date, end_date = date_range
            delta = end_date - start_date
            total_days = delta.days + 1
            
            tmpdir = tempfile.mkdtemp()
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            
            all_download_status = []
            
            for i in range(total_days):
                current_date = start_date + timedelta(days=i)
                status_text.text(f"Descargando datos para: {current_date.strftime('%Y-%m-%d')}...")
                
                download_status = download_files_for_date(current_date, tmpdir, download_precise, download_rapid, download_gfz)
                all_download_status.extend(download_status)
                
                progress_bar.progress((i + 1) / total_days)
            
            status_text.success("Descarga finalizada. Preparando archivo...")
            
            zip_filename = f"Efemerides_{start_date.strftime('%Y-%m-%d')}_a_{end_date.strftime('%Y-%m-%d')}.zip"
            zip_path = os.path.join(tmpdir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for item in os.listdir(tmpdir):
                    if item.endswith(('.gz', '.Z')):
                        zf.write(os.path.join(tmpdir, item), item)
            
            with open(zip_path, "rb") as fp:
                st.download_button(
                    label=f"Guardar archivo ZIP ({zip_filename})",
                    data=fp.read(),
                    file_name=zip_filename,
                    mime="application/zip"
                )
            
            shutil.rmtree(tmpdir)
            
    st.markdown('</div>', unsafe_allow_html=True)
