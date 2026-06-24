import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# Configuración de la página
st.set_page_config(page_title="Dashboard de Viáticos", layout="wide", initial_sidebar_state="expanded")

# Título Principal
st.title("📊 Dashboard Control de Viáticos")
st.markdown("Plataforma automatizada para el control, validación y análisis de viáticos.")

# ----------------------------------------------------
# 1. EXTRACCIÓN Y LIMPIEZA DE DATOS (POR LETRA DE COLUMNA)
# ----------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    sheet_url = "https://docs.google.com/spreadsheets/d/1shaXJ60_JQuxBEAgjzPEJJqqbIgcEavPRo_oeWvsX7Y/edit?usp=sharing"
    try:
        file_id = sheet_url.split("/d/")[1].split("/")[0]
        export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&sheet=Viaticos"
        # Leemos el CSV. header=1 indica que la fila 2 contiene los encabezados
        df = pd.read_csv(export_url, header=1)
    except Exception as e:
        st.error(f"Error al cargar los datos. Detalles: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()

    # Nos aseguramos de que el CSV tenga la cantidad de columnas suficientes (Hasta AQ que es el índice 42)
    # Si Sheets cortó las columnas vacías al final, las rellenamos.
    while len(df.columns) <= 42:
        df[f'Col_Vacia_{len(df.columns)}'] = 0.0

    # ASIGNACIÓN ESTRICTA POR LETRA DE COLUMNA (Índice Base 0 -> A=0, B=1...)
    cols = list(df.columns)
    
    # KPIs Principales
    cols[10] = 'MONTO DEPOSITADO'           # COLUMNA K
    cols[24] = 'SUMA VIATICOS VALIDADOS'    # COLUMNA Y

    # Categorías: LO DEPOSITADO
    cols[11] = 'DEP_Gasolina'       # L
    cols[12] = 'DEP_Casetas'        # M
    cols[13] = 'DEP_Autobus'        # N
    cols[14] = 'DEP_Hospedaje'      # O
    cols[15] = 'DEP_Lavanderia'     # P
    cols[16] = 'DEP_Comidas'        # Q
    cols[17] = 'DEP_Renta_Auto'     # R
    cols[18] = 'DEP_Vuelos'         # S
    cols[19] = 'DEP_Extra'          # T

    # Categorías: LO VALIDADO (GASTADO REAL)
    cols[26] = 'VAL_Gasolina'       # AA
    cols[28] = 'VAL_Casetas'        # AC
    cols[30] = 'VAL_Autobus'        # AE
    cols[32] = 'VAL_Hospedaje'      # AG
    cols[34] = 'VAL_Lavanderia'     # AI
    cols[36] = 'VAL_Comidas'        # AK
    cols[38] = 'VAL_Renta_Auto'     # AM
    cols[40] = 'VAL_Vuelos'         # AO
    cols[42] = 'VAL_Extra'          # AQ

    # Aplicamos los nuevos nombres de columnas exactos al Dataframe
    df.columns = cols
    
    # Limpieza de fechas
    if 'FECHA SERVICIOS' in df.columns:
        df['FECHA SERVICIOS'] = pd.to_datetime(df['FECHA SERVICIOS'], errors='coerce')
        
    if 'TECNICO' in df.columns:
        df = df.dropna(subset=['TECNICO'])
        
    # Función HIPER-ESTRICTA e INTELIGENTE para limpieza de formato regional ($2.475,00 vs $2,475.00)
    def clean_currency(val):
        if pd.isnull(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        if isinstance(val, str):
            val = val.replace('$', '').strip()
            if val in ['-', '', ' ']: return 0.0
            
            # Buscar separadores (puntos y comas)
            punctuations = re.findall(r'[.,]', val)
            if not punctuations:
                try: return float(val)
                except: return 0.0
                
            last_punct = punctuations[-1]
            
            if last_punct == ',':
                # Formato $2.475,00 o $980,00 (Coma es decimal)
                val = val.replace('.', '') # Eliminar punto de miles
                val = val.replace(',', '.') # Coma a punto decimal
            elif last_punct == '.':
                # Formato $2,475.00 o 3307.50 (Punto es decimal)
                val = val.replace(',', '') # Eliminar coma de miles
                
            try: return float(val)
            except: return 0.0
        return 0.0

    # Lista de todas las columnas que deben ser numéricas/dinero
    numeric_cols = ['MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS',
                   'DEP_Gasolina', 'DEP_Casetas', 'DEP_Autobus', 'DEP_Hospedaje', 'DEP_Lavanderia', 'DEP_Comidas', 'DEP_Renta_Auto', 'DEP_Vuelos', 'DEP_Extra',
                   'VAL_Gasolina', 'VAL_Casetas', 'VAL_Autobus', 'VAL_Hospedaje', 'VAL_Lavanderia', 'VAL_Comidas', 'VAL_Renta_Auto', 'VAL_Vuelos', 'VAL_Extra']
                   
    for col in numeric_cols:
        df[col] = df[col].apply(clean_currency)
        
    # Calculo de la DIFERENCIA EXACTA (Col K - Col Y)
    df['DIFERENCIA'] = df['MONTO DEPOSITADO'] - df['SUMA VIATICOS VALIDADOS']
    
    # Limpieza de comentarios
    if 'COMENTARIOS' in df.columns:
        df['COMENTARIOS'] = df['COMENTARIOS'].fillna("Sin comentarios").astype(str)
    else:
        df['COMENTARIOS'] = "Sin comentarios"

    return df

df = load_data()

if df.empty:
    st.stop()  # Detener ejecución si no hay datos procesables

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

# Filtros Dropdown
tecnicos = sorted(df['TECNICO'].dropna().unique().tolist())
selected_tecnicos = st.sidebar.multiselect("Seleccionar Técnico:", options=tecnicos, default=[])

if 'LOCALIDAD' in df.columns:
    localidades = sorted(df['LOCALIDAD'].dropna().unique().tolist())
    selected_localidades = st.sidebar.multiselect("Seleccionar Localidad:", options=localidades, default=[])
else:
    selected_localidades = []

if 'SERVICIO' in df.columns:
    servicios = sorted(df['SERVICIO'].dropna().unique().tolist())
    selected_servicios = st.sidebar.multiselect("Seleccionar Servicio:", options=servicios, default=[])
else:
    selected_servicios = []

# Aplicar filtros
df_filtered = df.copy()

if len(date_range) == 2:
    start_date, end_date = date_range
    df_filtered = df_filtered[(df_filtered['FECHA SERVICIOS'].dt.date >= start_date) & 
                              (df_filtered['FECHA SERVICIOS'].dt.date <= end_date)]

if selected_tecnicos:
    df_filtered = df_filtered[df_filtered['TECNICO'].isin(selected_tecnicos)]

if selected_localidades:
    df_filtered = df_filtered[df_filtered['LOCALIDAD'].isin(selected_localidades)]

if selected_servicios:
    df_filtered = df_filtered[df_filtered['SERVICIO'].isin(selected_servicios)]

# ----------------------------------------------------
# 3. TARJETAS DE INDICADORES (KPIs)
# ----------------------------------------------------
st.markdown("### Resumen Global")

total_depositado = df_filtered['MONTO DEPOSITADO'].sum()
total_gastado = df_filtered['SUMA VIATICOS VALIDADOS'].sum()
diferencia_total = total_depositado - total_gastado # K - Y

# Solo mostramos las 3 columnas solicitadas
col1, col2, col3 = st.columns(3)
col1.metric("Total Depositado (Col K)", f"${total_depositado:,.2f}")
col2.metric("Total Gastado Validado (Col Y)", f"${total_gastado:,.2f}")

# Color automático de la diferencia
delta_color = "normal" if diferencia_total >= 0 else "inverse"
col3.metric("Diferencia Neta Total", f"${diferencia_total:,.2f}", 
            delta="A favor empresa" if diferencia_total > 0 else "Adeudo a técnico" if diferencia_total < 0 else "Equilibrado",
            delta_color=delta_color)

st.markdown("---")

# ----------------------------------------------------
# 4. GRÁFICOS
# ----------------------------------------------------
st.markdown("### Análisis Gráfico")
col_graf1, col_graf2 = st.columns(2)

# Etiquetas para la gráfica
cat_names = ["Gasolina", "Casetas", "Autobus", "Hospedaje", "Lavanderia", "Comidas", "Renta de Auto", "Vuelos", "Extra"]

# Extraer sumas usando los nombres fijos que creamos por columna exacta
dep_cols = ['DEP_Gasolina', 'DEP_Casetas', 'DEP_Autobus', 'DEP_Hospedaje', 'DEP_Lavanderia', 'DEP_Comidas', 'DEP_Renta_Auto', 'DEP_Vuelos', 'DEP_Extra']
val_cols = ['VAL_Gasolina', 'VAL_Casetas', 'VAL_Autobus', 'VAL_Hospedaje', 'VAL_Lavanderia', 'VAL_Comidas', 'VAL_Renta_Auto', 'VAL_Vuelos', 'VAL_Extra']

sum_deposit = [df_filtered[c].sum() for c in dep_cols]
sum_valid = [df_filtered[c].sum() for c in val_cols]

df_chart = pd.DataFrame({
    'Categoría': cat_names,
    'Depositado': sum_deposit,
    'Validado': sum_valid
})

with col_graf1:
    st.markdown("**Comparativo: Depositado vs Gastado por Categoría**")
    fig_comp = go.Figure()
    # Gráfica expresada en PESOS
    fig_comp.add_trace(go.Bar(x=df_chart['Categoría'], y=df_chart['Depositado'], name='Depositado', 
                              marker_color='#4C72B0', texttemplate='$%{y:,.2f}', textposition='outside'))
    fig_comp.add_trace(go.Bar(x=df_chart['Categoría'], y=df_chart['Validado'], name='Gastado Real', 
                              marker_color='#55A868', texttemplate='$%{y:,.2f}', textposition='outside'))
    fig_comp.update_layout(barmode='group', template='plotly_white', height=450, margin=dict(l=0, r=0, t=30, b=0))
    fig_comp.update_yaxes(tickprefix="$") # Eje Y en formato Moneda
    st.plotly_chart(fig_comp, use_container_width=True)

with col_graf2:
    st.markdown("**Distribución del Gasto Validado**")
    df_chart_pie = df_chart[df_chart['Validado'] > 0]
    
    if not df_chart_pie.empty:
        fig_pie = px.pie(df_chart_pie, names='Categoría', values='Validado', hole=0.4, 
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        # Ajuste para que muestre el valor en pesos Y el porcentaje
        fig_pie.update_traces(textinfo='value+percent', texttemplate='%{label}<br>$%{value:,.2f}<br>(%{percent})')
        fig_pie.update_layout(height=450, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No hay gastos validados en el filtro seleccionado.")

st.markdown("---")

# ----------------------------------------------------
# 5. TABLA DETALLADA CON SEMÁFORO
# ----------------------------------------------------
st.markdown("### Tabla Detallada de Viáticos")

cols_to_show = ['TECNICO', 'LIDER DE CUENTA', 'SERVICIO', 'LOCALIDAD', 'MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS', 'DIFERENCIA']
cols_to_show = [c for c in cols_to_show if c in df_filtered.columns]

df_table = df_filtered[cols_to_show].copy()

# Semáforo: Verde si el número es positivo, Rojo si es negativo
def color_semaforo(val):
    if not isinstance(val, (int, float)):
        return ''
    if val > 0:
        return 'background-color: #d4edda; color: #155724;' # Verde
    elif val < 0:
        return 'background-color: #f8d7da; color: #721c24;' # Rojo
    else:
        return ''

styled_df = df_table.style.map(color_semaforo, subset=['DIFERENCIA']) \
                          .format({
                              'MONTO DEPOSITADO': '${:,.2f}',
                              'SUMA VIATICOS VALIDADOS': '${:,.2f}',
                              'DIFERENCIA': '${:,.2f}'
                          })

st.dataframe(styled_df, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# 6. COMENTARIOS
# ----------------------------------------------------
st.markdown("---")
st.markdown("### 💬 Comentarios y Notas por Técnico")

if 'COMENTARIOS' in df_filtered.columns:
    tecnicos_filtrados = df_filtered['TECNICO'].unique().tolist()
    
    if tecnicos_filtrados:
        tecnico_comentario = st.selectbox("Selecciona un Técnico para ver sus comentarios detallados:", ["-- Selecciona un técnico --"] + tecnicos_filtrados)
        
        if tecnico_comentario != "-- Selecciona un técnico --":
            df_com = df_filtered[(df_filtered['TECNICO'] == tecnico_comentario) & 
                                 (df_filtered['COMENTARIOS'].str.strip() != "") & 
                                 (df_filtered['COMENTARIOS'] != "Sin comentarios")]
            
            if df_com.empty:
                st.info(f"El técnico {tecnico_comentario} no tiene comentarios en este rango de fechas.")
            else:
                with st.expander(f"Ver comentarios de {tecnico_comentario}", expanded=True):
                    for idx, row in df_com.iterrows():
                        fecha = row['FECHA SERVICIOS'].strftime('%Y-%m-%d') if pd.notnull(row.get('FECHA SERVICIOS')) else 'Sin fecha'
                        servicio = row.get('SERVICIO', 'Sin servicio')
                        st.markdown(f"**🗓 {fecha} | 🛠 Proyecto:** {servicio}")
                        st.info(f"📝 {row['COMENTARIOS']}")
                        st.markdown("<br>", unsafe_allow_html=True)
