import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gestión", page_icon="🏢", layout="wide")

st.title("👤 Ingreso de paciente")

#sidebar

with st.form("cliente_form"):
    nombre = st.text_input("Nombre")
    apellido = st.text_input("Apellido")
    email = st.text_input("Correo electrónico")
    telefono = st.text_input("Teléfono")
    direccion = st.text_input("Dirección")
    submitted = st.form_submit_button("Guardar")

    if submitted:
        st.success(f"Cliente {nombre} {apellido} guardado exitosamente")
        # Guardar los datos en un DataFrame
        st.write("Datos del cliente ingresados:")
        st.write({
            "Nombre": nombre,
            "Apellido": apellido,
            "Correo electrónico": email,
            "Teléfono": telefono,
            "Dirección": direccion
        })
