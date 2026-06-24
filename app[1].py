import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="Dashboard de Viáticos", layout="wide", initial_sidebar_state="expanded")

# Título Principal
st.title("📊 Dashboard Control de Viáticos")
st.markdown("Plataforma automatizada para el control, validación y análisis de viáticos.")

# ----------------------------------------------------
# 1. EXTRACCIÓN Y LIMPIEZA DE DATOS
# ----------------------------------------------------
@st.cache_data(ttl=600)  # TTL de 10 min para que se actualice sin recargar cada segundo
def load_data():
    # URL pública compartida
    sheet_url = "https://docs.google.com/spreadsheets/d/1shaXJ60_JQuxBEAgjzPEJJqqbIgcEavPRo_oeWvsX7Y/edit?usp=sharing"
    
    # Extraer el ID para construir la URL de exportación a CSV
    try:
        file_id = sheet_url.split("/d/")[1].split("/")[0]
        # Forzar la lectura de la pestaña 'Viaticos' como CSV
        export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&sheet=Viaticos"
        
        # Leemos el CSV. header=1 indica que la fila 2 contiene los encabezados (índice 1)
        df = pd.read_csv(export_url, header=1)
    except Exception as e:
        st.error(f"Error al cargar los datos desde Google Sheets. Revisa la URL o los permisos. Detalles: {e}")
        return pd.DataFrame()

    # Estandarizar nombres de columnas (eliminar espacios extra)
    df.columns = df.columns.str.strip()
    
    # Asegurarnos de que existe la columna 'FECHA SERVICIOS' para no romper el filtro
    if 'FECHA SERVICIOS' in df.columns:
        df['FECHA SERVICIOS'] = pd.to_datetime(df['FECHA SERVICIOS'], errors='coerce')
    else:
        st.error("No se encontró la columna 'FECHA SERVICIOS'. Revisa el archivo original.")
        return pd.DataFrame()
        
    # Filtrar filas vacías (donde TECNICO está vacío)
    if 'TECNICO' in df.columns:
        df = df.dropna(subset=['TECNICO'])
    
    # Limpieza de columnas monetarias (rellenar NaN con 0)
    monetary_columns = ['MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS']
    
    # Listas de categorías esperadas
    cat_deposit = ["Gasolina", "Casetas", "Autobus", "Hospedaje", "Lavanderia", "Comidas", "Renta de Auto", "Vuelos", "Extra"]
    cat_valid = ["GASOLINA_V", "CASETAS_V", "AUTOBUS_V", "HOSPEDAJE_V", "LAVANDERIA_V", "COMIDAS_V", "RENTA DE AUTO_V", "VUELOS_V", "EXTRA_V"]
    
    # Agregamos las columnas de categorías para limpiarlas
    all_numeric = monetary_columns + cat_deposit + cat_valid
    
    for col in all_numeric:
        if col in df.columns:
            # Convertir a numérico por si hay texto tipo "$100" o espacios
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            # Si la columna no existe en el sheet, la creamos con 0 para evitar errores en las gráficas
            df[col] = 0.0

    # Lógica de la columna DIFERENCIA: (MONTO DEPOSITADO - SUMA VIATICOS VALIDADOS)
    df['DIFERENCIA'] = df['MONTO DEPOSITADO'] - df['SUMA VIATICOS VALIDADOS']
    
    # Asegurar que COMENTARIOS sea texto
    if 'COMENTARIOS' in df.columns:
        df['COMENTARIOS'] = df['COMENTARIOS'].fillna("Sin comentarios").astype(str)
    else:
        df['COMENTARIOS'] = "Sin comentarios"

    return df

df = load_data()

if df.empty:
    st.stop()  # Detener ejecución si no hay datos

# ----------------------------------------------------
# 2. FILTROS (SIDEBAR)
# ----------------------------------------------------
st.sidebar.header("Filtros de Búsqueda")

# Filtro de Fechas
min_date = df['FECHA SERVICIOS'].min()
max_date = df['FECHA SERVICIOS'].max()

if pd.isnull(min_date) or pd.isnull(max_date):
    st.sidebar.warning("Hay fechas inválidas en el archivo.")
    date_range = []
else:
    date_range = st.sidebar.date_input(
        "Rango de Fechas:",
        [min_date.date(), max_date.date()],
        min_value=min_date.date(),
        max_value=max_date.date()
    )

# Filtro Técnico
tecnicos = sorted(df['TECNICO'].dropna().unique().tolist())
selected_tecnicos = st.sidebar.multiselect("Seleccionar Técnico:", options=tecnicos, default=[])

# Filtro Localidad
if 'LOCALIDAD' in df.columns:
    localidades = sorted(df['LOCALIDAD'].dropna().unique().tolist())
    selected_localidades = st.sidebar.multiselect("Seleccionar Localidad:", options=localidades, default=[])
else:
    selected_localidades = []

# --- NUEVO: Filtro Servicio ---
if 'SERVICIO' in df.columns:
    servicios = sorted(df['SERVICIO'].dropna().unique().tolist())
    selected_servicios = st.sidebar.multiselect("Seleccionar Servicio:", options=servicios, default=[])
else:
    selected_servicios = []

# Aplicar filtros cruzados
df_filtered = df.copy()

if len(date_range) == 2:
    start_date, end_date = date_range
    df_filtered = df_filtered[(df_filtered['FECHA SERVICIOS'].dt.date >= start_date) & 
                              (df_filtered['FECHA SERVICIOS'].dt.date <= end_date)]

if selected_tecnicos:
    df_filtered = df_filtered[df_filtered['TECNICO'].isin(selected_tecnicos)]

if selected_localidades:
    df_filtered = df_filtered[df_filtered['LOCALIDAD'].isin(selected_localidades)]

# --- NUEVO: Aplicar filtro de Servicio ---
if selected_servicios:
    df_filtered = df_filtered[df_filtered['SERVICIO'].isin(selected_servicios)]

# ----------------------------------------------------
# 3. TARJETAS DE INDICADORES (KPIs)
# ----------------------------------------------------
st.markdown("### Resumen Global")

total_depositado = df_filtered['MONTO DEPOSITADO'].sum()
total_gastado = df_filtered['SUMA VIATICOS VALIDADOS'].sum()
diferencia_total = df_filtered['DIFERENCIA'].sum()

# Cálculos de Técnicos / Empresa
tecnicos_reembolsan = df_filtered[df_filtered['DIFERENCIA'] > 0]
num_tecnicos_reembolso = tecnicos_reembolsan['TECNICO'].nunique()

empresa_paga = df_filtered[df_filtered['DIFERENCIA'] < 0]['DIFERENCIA'].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Total Depositado", f"${total_depositado:,.2f}")
col2.metric("Total Gastado (Validado)", f"${total_gastado:,.2f}")
col3.metric("Diferencia Neta Total", f"${diferencia_total:,.2f}", 
            delta="A favor de Empresa" if diferencia_total > 0 else "Adeudo a Técnicos" if diferencia_total < 0 else "Equilibrado",
            delta_color="normal" if diferencia_total >= 0 else "inverse")

st.markdown("---")
col4, col5 = st.columns(2)
col4.metric("Técnicos con Saldo a Reembolsar (Dif > 0)", f"{num_tecnicos_reembolso} Técnicos")
col5.metric("Total a Pagar por la Empresa (Dif < 0)", f"${abs(empresa_paga):,.2f}")

st.markdown("---")

# ----------------------------------------------------
# 4. GRÁFICOS
# ----------------------------------------------------
st.markdown("### Análisis Gráfico")
col_graf1, col_graf2 = st.columns(2)

# Categorías definidas
cat_deposit = ["Gasolina", "Casetas", "Autobus", "Hospedaje", "Lavanderia", "Comidas", "Renta de Auto", "Vuelos", "Extra"]
cat_valid = ["GASOLINA_V", "CASETAS_V", "AUTOBUS_V", "HOSPEDAJE_V", "LAVANDERIA_V", "COMIDAS_V", "RENTA DE AUTO_V", "VUELOS_V", "EXTRA_V"]

# Acumular montos por categoría
sum_deposit = [df_filtered[c].sum() for c in cat_deposit]
sum_valid = [df_filtered[c].sum() for c in cat_valid]

df_chart = pd.DataFrame({
    'Categoría': cat_deposit,
    'Depositado': sum_deposit,
    'Validado (Gastado)': sum_valid
})

with col_graf1:
    st.markdown("**Comparativo: Depositado vs Gastado por Categoría**")
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(x=df_chart['Categoría'], y=df_chart['Depositado'], name='Depositado', marker_color='#4C72B0'))
    fig_comp.add_trace(go.Bar(x=df_chart['Categoría'], y=df_chart['Validado (Gastado)'], name='Validado (Gastado)', marker_color='#55A868'))
    fig_comp.update_layout(barmode='group', template='plotly_white', height=400, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_comp, use_container_width=True)

with col_graf2:
    st.markdown("**Distribución del Gasto Validado**")
    # Filtrar solo categorías que tuvieron gasto para que la gráfica de pastel no se vea rara
    df_chart_pie = df_chart[df_chart['Validado (Gastado)'] > 0]
    if not df_chart_pie.empty:
        fig_pie = px.pie(df_chart_pie, names='Categoría', values='Validado (Gastado)', hole=0.4, 
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pie.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No hay gastos validados para mostrar en la distribución.")

st.markdown("---")

# ----------------------------------------------------
# 5. TABLA DETALLADA CON SEMÁFORO
# ----------------------------------------------------
st.markdown("### Tabla Detallada de Viáticos")

# Definir las columnas a mostrar
cols_to_show = ['TECNICO', 'LIDER DE CUENTA', 'SERVICIO', 'LOCALIDAD', 'MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS', 'DIFERENCIA']
# Solo seleccionar columnas que realmente existen en el DataFrame filtrado
cols_to_show = [c for c in cols_to_show if c in df_filtered.columns]

df_table = df_filtered[cols_to_show].copy()

# Función para aplicar formato estilo semáforo
def color_semaforo(val):
    if not isinstance(val, (int, float)):
        return ''
    if val > 0:
        return 'background-color: #d4edda; color: #155724;' # Verde suave (Sobró)
    elif val < 0:
        return 'background-color: #f8d7da; color: #721c24;' # Rojo suave (Deuda empresa)
    else:
        return ''

styled_df = df_table.style.map(color_semaforo, subset=['DIFERENCIA'])                           .format({
                              'MONTO DEPOSITADO': '${:,.2f}',
                              'SUMA VIATICOS VALIDADOS': '${:,.2f}',
                              'DIFERENCIA': '${:,.2f}'
                          })

st.dataframe(styled_df, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# 6. APARTADO INTERACTIVO DE COMENTARIOS
# ----------------------------------------------------
st.markdown("---")
st.markdown("### 💬 Comentarios y Notas por Técnico")

if 'COMENTARIOS' in df_filtered.columns:
    tecnicos_filtrados = df_filtered['TECNICO'].unique().tolist()
    
    # Si hay técnicos en pantalla, permitir ver comentarios
    if tecnicos_filtrados:
        tecnico_comentario = st.selectbox("Selecciona un Técnico para ver sus comentarios detallados:", ["-- Selecciona un técnico --"] + tecnicos_filtrados)
        
        if tecnico_comentario != "-- Selecciona un técnico --":
            df_com = df_filtered[(df_filtered['TECNICO'] == tecnico_comentario) & 
                                 (df_filtered['COMENTARIOS'].str.strip() != "") & 
                                 (df_filtered['COMENTARIOS'] != "Sin comentarios")]
            
            if df_com.empty:
                st.info(f"El técnico {tecnico_comentario} no tiene comentarios registrados en el rango seleccionado.")
            else:
                with st.expander(f"Ver comentarios de {tecnico_comentario}", expanded=True):
                    for idx, row in df_com.iterrows():
                        fecha = row['FECHA SERVICIOS'].strftime('%Y-%m-%d') if pd.notnull(row.get('FECHA SERVICIOS')) else 'Sin fecha'
                        servicio = row.get('SERVICIO', 'Sin servicio especificado')
                        st.markdown(f"**🗓 {fecha} | 🛠 Proyecto/Servicio:** {servicio}")
                        st.info(f"📝 {row['COMENTARIOS']}")
                        st.markdown("<br>", unsafe_allow_html=True)
else:
    st.warning("La columna de COMENTARIOS no se encontró en la base de datos.")
