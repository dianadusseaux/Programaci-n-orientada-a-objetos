from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Paciente", page_icon="🏢", layout="wide")

DATA_FILE = "data/ventas_prediccion.csv"
MONEY_COLS = ["PRECIO_VENTA", "PRECIO_TOTAL", "PRECIO_LISTA_ACTUAL", "PRECIO_LISTA_DIA_VENTA", "DESCUENTOS"]

@st.cache_data
def read_csv(path, mtime):
    return pd.read_csv(path, low_memory=False)

def load_data():
    if "df" not in st.session_state:
        st.session_state.df = read_csv(DATA_FILE, Path(DATA_FILE).stat().st_mtime) if Path(DATA_FILE).exists() else pd.DataFrame()
    return st.session_state.df

def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
    st.session_state.df = df.copy()
    read_csv.clear()

def as_num(value):
    try:
        return float(str(value).replace(".", "").replace(",", "."))
    except (ValueError, TypeError):
        return 0.0

def options(df, col):
    if col not in df.columns:
        return []
    vals = df[col].dropna().astype(str).str.strip()
    return sorted(v for v in vals.unique().tolist() if v and v.lower() != "nan")

def money(value):
    if pd.isna(value):
        return "—"
    return f"{value:,.0f}".replace(",", ".")

df = load_data()
if df.empty:
    st.error("No se encontró el CSV o está vacío. Coloca ventas_prediccion.csv junto a app.py.")
    st.stop()

st.title("🏢 Gestión de ventas y departamentos")
st.caption(f"Fuente: {DATA_FILE} · {len(df):,} filas · {df.shape[1]} columnas")

with st.sidebar:
    st.header("Navegación")
    page = st.radio("Selecciona una página", [
        "Dashboard", "Ingreso de clientes", "Edición de departamentos", "Explorador y exportación"
    ])
    st.divider()
    st.caption("Los cambios se guardan en el CSV local de la aplicación.")

# Dates and numeric normalization for analysis only
work = df.copy()
for c in ["FechaCotizacion", "FECHA_RESERVA", "FechaReserva", "FechaFirmaPromesa", "FechaFirmaEscrituraCliente"]:
    if c in work:
        work[c] = pd.to_datetime(work[c], errors="coerce")
for c in MONEY_COLS:
    if c in work:
        work[c] = pd.to_numeric(work[c], errors="coerce")

if page == "Dashboard":
    st.header("Dashboard comercial")
    st.info("El archivo no contiene una columna explícita de estado (por ejemplo, 'Cotización', 'Vendida' o 'Escriturada'). "
            "Por ello, los indicadores se presentan como registros con fecha informada y operaciones distintas; "
            "no deben interpretarse como estados comerciales definitivos.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", f"{len(work):,}")
    c2.metric("Operaciones distintas", f"{work['idoperacion'].nunique():,}" if "idoperacion" in work else "—")
    c3.metric("Con fecha de cotización", f"{work['FechaCotizacion'].notna().sum():,}" if "FechaCotizacion" in work else "—")
    c4.metric("Con firma de escritura", f"{work['FechaFirmaEscrituraCliente'].notna().sum():,}" if "FechaFirmaEscrituraCliente" in work else "—")

    st.subheader("Filtros")
    f1, f2, f3 = st.columns(3)
    projects = options(work, "Proyecto")
    selected_projects = f1.multiselect("Proyecto", projects, default=projects)
    channels = options(work, "GRUPO_LLEGADA")
    selected_channels = f2.multiselect("Grupo de llegada", channels)
    years = sorted(work["FechaCotizacion"].dropna().dt.year.unique().tolist()) if "FechaCotizacion" in work else []
    selected_years = f3.multiselect("Año de cotización", years, default=years)
    filtered = work.copy()
    if selected_projects and "Proyecto" in filtered:
        filtered = filtered[filtered["Proyecto"].astype(str).isin(selected_projects)]
    if selected_channels and "GRUPO_LLEGADA" in filtered:
        filtered = filtered[filtered["GRUPO_LLEGADA"].astype(str).isin(selected_channels)]
    if selected_years and "FechaCotizacion" in filtered:
        filtered = filtered[filtered["FechaCotizacion"].dt.year.isin(selected_years)]

    k1, k2, k3 = st.columns(3)
    k1.metric("Registros filtrados", f"{len(filtered):,}")
    k2.metric("Precio venta promedio", money(filtered["PRECIO_VENTA"].mean()) if "PRECIO_VENTA" in filtered else "—")
    k3.metric("Descuento promedio", money(filtered["DESCUENTOS"].mean()) if "DESCUENTOS" in filtered else "—")

    left, right = st.columns(2)
    with left:
        st.subheader("Registros por proyecto")
        if "Proyecto" in filtered:
            st.bar_chart(filtered["Proyecto"].value_counts().head(15))
    with right:
        st.subheader("Registros por grupo de llegada")
        if "GRUPO_LLEGADA" in filtered:
            st.bar_chart(filtered["GRUPO_LLEGADA"].fillna("Sin dato").value_counts().head(12))

    if "FechaCotizacion" in filtered:
        st.subheader("Evolución mensual de cotizaciones registradas")
        monthly = filtered.dropna(subset=["FechaCotizacion"]).assign(Mes=lambda x: x["FechaCotizacion"].dt.to_period("M").astype(str)).groupby("Mes").size()
        if not monthly.empty:
            st.line_chart(monthly)
    st.subheader("Detalle de registros")
    show_cols = [c for c in ["idoperacion", "Proyecto", "Etapa", "Unidad", "FechaCotizacion", "PRECIO_VENTA", "GRUPO_LLEGADA", "MEDIO_LLEGADA"] if c in filtered]
    st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)

elif page == "Ingreso de clientes":
    st.header("Ingreso de un nuevo cliente")
    st.write("Registra un nuevo contacto asociado a un proyecto y, opcionalmente, a una unidad.")
    with st.form("new_customer", clear_on_submit=True):
        a, b, c = st.columns(3)
        rut = a.text_input("RUT del cliente")
        nombre = b.text_input("Nombre / razón de compra")
        email = c.text_input("Correo electrónico (campo adicional)")
        d, e, f = st.columns(3)
        telefono = d.text_input("Teléfono (campo adicional)")
        proyecto = e.selectbox("Proyecto", options(df, "Proyecto") or ["Por definir"])
        razon = f.selectbox("Razón de compra", options(df, "RAZON_COMPRA") or ["No informado"])
        g, h, i = st.columns(3)
        unidad = g.selectbox("Unidad", ["Sin asignar"] + options(df, "Unidad"))
        grupo = h.selectbox("Grupo de llegada", options(df, "GRUPO_LLEGADA") or ["No informado"])
        medio = i.selectbox("Medio de llegada", options(df, "MEDIO_LLEGADA") or ["No informado"])
        j, k, l = st.columns(3)
        origen = j.selectbox("Origen de visita", options(df, "ORIGEN_VISITA") or ["No informado"])
        ingreso = k.selectbox("Tramo de ingreso", options(df, "INGRESO_RENTA") or ["No informado"])
        genero = l.selectbox("Género", ["No informado", "F", "M", "Otro"])
        fecha = st.date_input("Fecha de cotización")
        acepta = st.checkbox("Confirmo que los datos ingresados fueron proporcionados para fines de gestión comercial.")
        submitted = st.form_submit_button("Guardar nuevo cliente", type="primary")
    if submitted:
        if not rut.strip() or not nombre.strip():
            st.error("RUT y nombre/razón de compra son obligatorios.")
        elif not acepta:
            st.warning("Debes confirmar el uso de los datos antes de guardar.")
        else:
            new = {col: pd.NA for col in df.columns}
            new["idoperacion"] = int(pd.to_numeric(df.get("idoperacion"), errors="coerce").max() or 0) + 1
            mapping = {
                "RutCliente": rut.strip(), "RAZON_COMPRA": razon, "Proyecto": proyecto,
                "Unidad": "" if unidad == "Sin asignar" else unidad,
                "GRUPO_LLEGADA": grupo, "MEDIO_LLEGADA": medio, "ORIGEN_VISITA": origen,
                "INGRESO_RENTA": ingreso, "Genero": genero,
                "FechaCotizacion": fecha.isoformat(), "FECHA_RESERVA": pd.NA,
                "FechaReserva": pd.NA, "FechaFirmaPromesa": pd.NA,
                "FechaFirmaEscrituraCliente": pd.NA
            }
            for key, value in mapping.items():
                if key in new:
                    new[key] = value
            # Additional contact fields are retained if absent from the source schema.
            new["NombreCliente"] = nombre.strip()
            new["EmailCliente"] = email.strip()
            new["TelefonoCliente"] = telefono.strip()
            updated = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
            save_data(updated)
            st.success(f"Cliente guardado. ID de operación asignado: {new['idoperacion']}")
            st.rerun()

elif page == "Edición de departamentos":
    st.header("Edición de registros de departamentos")
    st.caption("El CSV contiene unidades vinculadas a operaciones. Selecciona un registro para editar sus datos de identificación, proyecto y precio.")
    if "idoperacion" not in df:
        st.error("No existe la columna idoperacion.")
    else:
        labels = []
        for idx, row in df.iterrows():
            labels.append(f"Fila {idx} · Op. {row.get('idoperacion', '')} · {row.get('Proyecto', '')} · Unidad {row.get('Unidad', '')}")
        selected_label = st.selectbox("Registro a editar", labels)
        idx = labels.index(selected_label)
        row = df.iloc[idx]
        with st.form("edit_department"):
            x1, x2, x3 = st.columns(3)
            proyecto = x1.text_input("Proyecto", str(row.get("Proyecto", "") if pd.notna(row.get("Proyecto")) else ""))
            etapa = x2.text_input("Etapa", str(row.get("Etapa", "") if pd.notna(row.get("Etapa")) else ""))
            unidad = x3.text_input("Unidad", str(row.get("Unidad", "") if pd.notna(row.get("Unidad")) else ""))
            y1, y2, y3 = st.columns(3)
            id_unidad = y1.text_input("ID unidad Cubit", str(row.get("ID_unidad_cubit", "") if pd.notna(row.get("ID_unidad_cubit")) else ""))
            precio_lista = y2.number_input("Precio lista actual", min_value=0.0, value=float(row.get("PRECIO_LISTA_ACTUAL", 0) or 0), step=100000.0)
            precio_venta = y3.number_input("Precio de venta", min_value=0.0, value=float(row.get("PRECIO_VENTA", 0) or 0), step=100000.0)
            z1, z2 = st.columns(2)
            etapa_unidad = z1.selectbox("Etapa comercial", ["No especificada", "En comercialización", "Reservada", "Vendida", "Escriturada"],
                                        index=0)
            activo = z2.checkbox("Unidad activa para comercialización", value=True)
            confirm = st.checkbox("Confirmo que deseo actualizar este registro.")
            save = st.form_submit_button("Guardar cambios", type="primary")
        if save:
            if not confirm:
                st.warning("Confirma la actualización para continuar.")
            else:
                updated = df.copy()
                for col, val in {"Proyecto": proyecto, "Etapa": etapa, "Unidad": unidad,
                                "ID_unidad_cubit": id_unidad, "PRECIO_LISTA_ACTUAL": precio_lista,
                                "PRECIO_VENTA": precio_venta, "EtapaComercial": etapa_unidad,
                                "UnidadActiva": activo}.items():
                    updated.loc[updated.index[idx], col] = val
                save_data(updated)
                st.success("Registro actualizado correctamente.")
                st.rerun()
        st.subheader("Registro seleccionado")
        st.dataframe(df.iloc[[idx]], use_container_width=True)

else:
    st.header("Explorador y exportación")
    st.write("Consulta registros y descarga la base actualizada.")
    search = st.text_input("Buscar por operación, RUT, proyecto o unidad")
    view = df.copy()
    if search.strip():
        mask = pd.Series(False, index=view.index)
        for col in ["idoperacion", "RutCliente", "Proyecto", "Unidad", "ID_unidad_cubit"]:
            if col in view:
                mask |= view[col].astype(str).str.contains(search.strip(), case=False, na=False)
        view = view[mask]
    st.caption(f"{len(view):,} registros encontrados")
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.download_button("Descargar CSV actualizado", data=df.to_csv(index=False).encode("utf-8-sig"),
                                file_name="ventas_departamentos_actualizado.csv", mime="text/csv")
    st.warning("La aplicación guarda los cambios en el archivo CSV local. Mantén una copia de respaldo antes de editar datos reales.")
