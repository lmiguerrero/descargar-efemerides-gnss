#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
from ftplib import FTP
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog

# Función para calcular el número de semana GPS y el número de semana GPS
def calculate_gps_week_number(date):
    date_format = "%d-%m-%Y"
    target_date = datetime.strptime(date, date_format)
    gps_start_date = datetime(1980, 1, 6)  # Fecha de inicio del sistema GPS
    days_since_start = (target_date - gps_start_date).days
    gps_week = days_since_start // 7  # Calcula el número de semana GPS
    gps_day_of_week = days_since_start % 7  # Calcula el día dentro de la semana GPS
    gps_week_number = gps_week * 10 + gps_day_of_week  # Calcula el número de semana GPS
    return gps_week, gps_week_number

# Función para descargar las efemérides desde el servidor FTP
def download_efemerides(date, file_path):
    gps_week, gps_week_number = calculate_gps_week_number(date)
    ftp_url = f"ftp://lox.ucsd.edu/pub/products/{gps_week}/igr{gps_week_number}.sp3.Z"
    ftp_host = "lox.ucsd.edu"
    ftp_path = f"/pub/products/{gps_week}/igr{gps_week_number}.sp3.Z"

    try:
        ftp = FTP(ftp_host)  # Conecta al servidor FTP
        ftp.login()  # Inicia sesión en el servidor FTP
        with open(file_path, 'wb') as local_file:
            ftp.retrbinary(f"RETR {ftp_path}", local_file.write)  # Descarga el archivo
        ftp.quit()  # Cierra la conexión FTP
        # Muestra un mensaje de éxito con el número de semana GPS calculado
        messagebox.showinfo("Descarga Completa", f"Efemérides descargadas como {file_path}\n\nSe han descargado las efemérides para el GPS Week Number calculado: {gps_week_number}")
    except Exception as e:
        # Muestra un mensaje de error si no se pudo descargar el archivo
        messagebox.showerror("Error", f"No se pudo descargar las efemérides. Error: {str(e)}")

# Función que inicia el proceso de descarga
def start_download():
    date = date_entry.get()  # Obtiene la fecha ingresada por el usuario
    # Abre un cuadro de diálogo para seleccionar la ubicación de guardado del archivo
    file_path = filedialog.asksaveasfilename(defaultextension=".sp3.Z", filetypes=[("SP3 files", "*.sp3.Z")])
    if file_path:
        download_efemerides(date, file_path)  # Llama a la función para descargar las efemérides

# Configuración de la interfaz gráfica
root = tk.Tk()
root.title("Descargar Efemérides GNSS")

# Etiqueta y campo de entrada para la fecha
tk.Label(root, text="Ingrese la fecha (DD-MM-YYYY):").pack(pady=10)
date_entry = tk.Entry(root)
date_entry.pack(pady=5)

# Botón para iniciar la descarga
download_button = tk.Button(root, text="Descargar", command=start_download)
download_button.pack(pady=20)

# Etiqueta con el nombre y título
tk.Label(root, text="Miguel Guerrero Ing Topográfico UD", font=("Arial", 8)).pack(pady=10)

# Inicia el bucle principal de la interfaz gráfica
root.mainloop()

