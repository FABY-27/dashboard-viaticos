import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# ----------------------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS CSS
# ----------------------------------------------------
st.set_page_config(page_title="Dashboard de Viáticos", layout="wide", initial_sidebar_state="expanded")

# Inyección de CSS para la personalización solicitada
st.markdown("""
<style>
    /* Fondo general blanco */
    .stApp {
        background-color: #FFFFFF;
    }

    /* Estilo del menú lateral (Sidebar) - Fondo azul claro y texto blanco */
    [data-testid="stSidebar"] {
        background-color: #4A90E2 !important; /* Azul Claro */
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important; /* Texto blanco en el sidebar */
    }
    
    /* Personalización de los inputs en el sidebar para que se lean bien */
    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div,
    .stDateInput input {
        background-color: #FFFFFF !important;
        color: #333333 !important; /* Texto oscuro dentro del input */
        border: none !important;
    }
    /* Estilo de las "píldoras" en el multiselect del sidebar */
    .stMultiSelect span[data-baseweb="tag"] {
        background-color: #2C3E50 !important;
        color: white !important;
    }

    /* Clase personalizada para crear el efecto de "Tarjetas" (Cards) con sombra */
    .custom-card {
        background-color: #F8FBFF; /* Azul muy muy claro/blanco azulado */
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1); /* Sombra suave y pequeña */
        margin-bottom: 20px;
    }
    
    /* Textos principales oscuros para contrastar con el fondo blanco */
    h1, h2, h3, h4, h5, h6, p, span {
        color: #2C3E50;
    }
    
    /* Título Ubiknos esquina superior derecha */
    .ubiknos-header {
        position: absolute;
        top: 0px;
        right: 20px;
        font-size: 24px;
        font-weight: bold;
        color: #4A90E2;
        letter-spacing: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. ENCABEZADO
# ----------------------------------------------------
st.markdown("<div class='ubiknos-header'>UBIKNOS</div>", unsafe_allow_html=True)

st.title("📊 Viáticos")
st.markdown("Plataforma automatizada para el control, validación y análisis de viáticos.")
st.markdown("---")

# ----------------------------------------------------
# 3. EXTRACCIÓN Y LIMPIEZA DE DATOS
# ----------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    sheet_url = "https://docs.google.com/spreadsheets/d/1shaXJ60_JQuxBEAgjzPEJJqqbIgcEavPRo_oeWvsX7Y/edit?usp=sharing"
    try:
        file_id = sheet_url.split("/d/")[1].split("/")[0]
        export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&sheet=Viaticos"
        df = pd.read_csv(export_url, header=1)
    except Exception as e:
        st.error(f"Error al cargar los datos. Detalles: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()

    while len(df.columns) <= 42:
        df[f'Col_Vacia_{len(df.columns)}'] = 0.0

    cols = list(df.columns)
    
    # KPIs Mapeados estrictamente por letra de columna (K=10, X=23, Y=24)
    cols[10] = 'MONTO DEPOSITADO'
    cols[23] = 'DIFERENCIA REAL' # NUEVO: Columna X que dice originalmente 'DIFERENCIA'
    cols[24] = 'SUMA VIATICOS VALIDADOS'

    # Mapeo de categorías: lo depositado (L a T)
    cols[11], cols[12], cols[13], cols[14], cols[15], cols[16], cols[17], cols[18], cols[19] = \
    'DEP_Gasolina', 'DEP_Casetas', 'DEP_Autobus', 'DEP_Hospedaje', 'DEP_Lavanderia', 'DEP_Comidas', 'DEP_Renta_Auto', 'DEP_Vuelos', 'DEP_Extra'

    # Mapeo de categorías: lo validado (AA a AQ)
    cols[26], cols[28], cols[30], cols[32], cols[34], cols[36], cols[38], cols[40], cols[42] = \
    'VAL_Gasolina', 'VAL_Casetas', 'VAL_Autobus', 'VAL_Hospedaje', 'VAL_Lavanderia', 'VAL_Comidas', 'VAL_Renta_Auto', 'VAL_Vuelos', 'VAL_Extra'

    df.columns = cols
    
    if 'FECHA SERVICIOS' in df.columns:
        df['FECHA SERVICIOS'] = pd.to_datetime(df['FECHA SERVICIOS'], errors='coerce')
        
    if 'TECNICO' in df.columns:
        df = df.dropna(subset=['TECNICO'])
        
    def clean_currency(val):
        if pd.isnull(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        if isinstance(val, str):
            val = val.replace('$', '').strip()
            if val in ['-', '', ' ']: return 0.0
            punctuations = re.findall(r'[.,]', val)
            if not punctuations:
                try: return float(val)
                except: return 0.0
            last_punct = punctuations[-1]
            if last_punct == ',':
                val = val.replace('.', '').replace(',', '.')
            elif last_punct == '.':
                val = val.replace(',', '')
            try: return float(val)
            except: return 0.0
        return 0.0

    # Lista de todas las columnas que deben ser numéricas/dinero (incluyendo DIFERENCIA REAL)
    numeric_cols = ['MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS', 'DIFERENCIA REAL',
                   'DEP_Gasolina', 'DEP_Casetas', 'DEP_Autobus', 'DEP_Hospedaje', 'DEP_Lavanderia', 'DEP_Comidas', 'DEP_Renta_Auto', 'DEP_Vuelos', 'DEP_Extra',
                   'VAL_Gasolina', 'VAL_Casetas', 'VAL_Autobus', 'VAL_Hospedaje', 'VAL_Lavanderia', 'VAL_Comidas', 'VAL_Renta_Auto', 'VAL_Vuelos', 'VAL_Extra']
                   
    for col in numeric_cols:
        df[col] = df[col].apply(clean_currency)
        
    # Calculo de la DIFERENCIA LOCAL (Col K - Col Y) para control interno
    df['DIFERENCIA'] = df['MONTO DEPOSITADO'] - df['SUMA VIATICOS VALIDADOS']
    
    if 'COMENTARIOS' in df.columns:
        df['COMENTARIOS'] = df['COMENTARIOS'].fillna("Sin comentarios").astype(str)
    else:
        df['COMENTARIOS'] = "Sin comentarios"

    return df

df = load_data()

if df.empty:
    st.stop()

# ----------------------------------------------------
# 4. FILTROS (SIDEBAR)
# ----------------------------------------------------
st.sidebar.markdown("## 🔍 Filtros de Búsqueda")

min_date = df['FECHA SERVICIOS'].min()
max_date = df['FECHA SERVICIOS'].max()

if pd.isnull(min_date) or pd.isnull(max_date):
    st.sidebar.warning("Hay fechas inválidas.")
    date_range = []
else:
    date_range = st.sidebar.date_input("Rango de Fechas:", [min_date.date(), max_date.date()], min_value=min_date.date(), max_value=max_date.date())

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
    df_filtered = df_filtered[(df_filtered['FECHA SERVICIOS'].dt.date >= start_date) & (df_filtered['FECHA SERVICIOS'].dt.date <= end_date)]

if selected_tecnicos:
    df_filtered = df_filtered[df_filtered['TECNICO'].isin(selected_tecnicos)]

if selected_localidades:
    df_filtered = df_filtered[df_filtered['LOCALIDAD'].isin(selected_localidades)]

if selected_servicios:
    df_filtered = df_filtered[df_filtered['SERVICIO'].isin(selected_servicios)]

# ----------------------------------------------------
# 5. TARJETAS DE INDICADORES (KPIs) CON CSS
# ----------------------------------------------------
st.markdown("### Resumen Global")

total_depositado = df_filtered['MONTO DEPOSITADO'].sum()
total_gastado = df_filtered['SUMA VIATICOS VALIDADOS'].sum()
total_diferencia_real = df_filtered['DIFERENCIA REAL'].sum() # Suma de la columna X
diferencia_total = total_depositado - total_gastado # K - Y para validación

# Estructura HTML actualizada con 4 tarjetas distribuidas al 25% cada una
kpi_html = f"""
<div style="display: flex; justify-content: space-between; gap: 15px; margin-bottom: 20px; flex-wrap: wrap;">
    <div class="custom-card" style="flex: 1; min-width: 200px; text-align: center;">
        <h4 style="margin:0; color:#555; font-size:15px;">Total Depositado</h4>
        <h2 style="margin:5px 0 0 0; color:#4C72B0; font-size:24px;">${total_depositado:,.2f}</h2>
    </div>
    <div class="custom-card" style="flex: 1; min-width: 200px; text-align: center;">
        <h4 style="margin:0; color:#555; font-size:15px;">Total Gastado</h4>
        <h2 style="margin:5px 0 0 0; color:#55A868; font-size:24px;">${total_gastado:,.2f}</h2>
    </div>
    <div class="custom-card" style="flex: 1; min-width: 200px; text-align: center;">
        <h4 style="margin:0; color:#555; font-size:15px;">Diferencia Neta</h4>
        <h2 style="margin:5px 0 0 0; color:{'#E74C3C' if diferencia_total < 0 else '#27AE60'}; font-size:24px;">${diferencia_total:,.2f}</h2>
    </div>
    <div class="custom-card" style="flex: 1; min-width: 200px; text-align: center; border: 1px solid #74B9FF;">
        <h4 style="margin:0; color:#2C3E50; font-size:15px; font-weight: bold;">Diferencia Real </h4>
        <h2 style="margin:5px 0 0 0; color:{'#E74C3C' if total_diferencia_real < 0 else '#27AE60'}; font-size:24px;">${total_diferencia_real:,.2f}</h2>
    </div>
</div>
"""
st.markdown(kpi_html, unsafe_allow_html=True)

# ----------------------------------------------------
# 6. GRÁFICOS DENTRO DE CONTENEDORES CON CLASE CSS
# ----------------------------------------------------
st.markdown("### Análisis Gráfico")
col_graf1, col_graf2 = st.columns(2)

cat_names = ["Gasolina", "Casetas", "Autobus", "Hospedaje", "Lavanderia", "Comidas", "Renta de Auto", "Vuelos", "Extra"]
dep_cols = ['DEP_Gasolina', 'DEP_Casetas', 'DEP_Autobus', 'DEP_Hospedaje', 'DEP_Lavanderia', 'DEP_Comidas', 'DEP_Renta_Auto', 'DEP_Vuelos', 'DEP_Extra']
val_cols = ['VAL_Gasolina', 'VAL_Casetas', 'VAL_Autobus', 'VAL_Hospedaje', 'VAL_Lavanderia', 'VAL_Comidas', 'VAL_Renta_Auto', 'VAL_Vuelos', 'VAL_Extra']

sum_deposit = [df_filtered[c].sum() for c in dep_cols]
sum_valid = [df_filtered[c].sum() for c in val_cols]

df_chart = pd.DataFrame({'Categoría': cat_names, 'Depositado': sum_deposit, 'Validado': sum_valid})

with col_graf1:
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("**Comparativo: Depositado vs Gastado**")
    fig_comp = go.Figure()
    
    fig_comp.add_trace(go.Bar(
        x=df_chart['Categoría'], 
        y=df_chart['Depositado'], 
        name='Depositado', 
        marker_color='#4C72B0', 
        texttemplate='$%{y:,.2f}', 
        textposition='outside',
        textfont=dict(color='black')
    ))
    fig_comp.add_trace(go.Bar(
        x=df_chart['Categoría'], 
        y=df_chart['Validado'], 
        name='Gastado Real', 
        marker_color='#55A868', 
        texttemplate='$%{y:,.2f}', 
        textposition='outside',
        textfont=dict(color='black')
    ))
    
    fig_comp.update_layout(
        barmode='group', 
        height=400, 
        margin=dict(l=0, r=0, t=30, b=0), 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='black'),
        legend=dict(font=dict(color='black'))
    )
    
    fig_comp.update_xaxes(tickfont=dict(color='black'), title_font=dict(color='black'))
    fig_comp.update_yaxes(tickprefix="$", showgrid=True, gridcolor='#E0E0E0', tickfont=dict(color='black'), title_font=dict(color='black'))
    
    st.plotly_chart(fig_comp, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_graf2:
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("**Distribución del Gasto Validado**")
    df_chart_pie = df_chart[df_chart['Validado'] > 0]
    
    if not df_chart_pie.empty:
        fig_pie = px.pie(df_chart_pie, names='Categoría', values='Validado', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        
        fig_pie.update_traces(
            textinfo='value+percent', 
            texttemplate='%{label}<br>$%{value:,.2f}<br>(%{percent})',
            textfont=dict(color='black')
        )
        fig_pie.update_layout(
            height=400, 
            margin=dict(l=0, r=0, t=30, b=0), 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='black'),
            legend=dict(font=dict(color='black'))
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No hay gastos validados.")
    st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 7. TABLA Y COMENTARIOS EN TARJETAS
# ----------------------------------------------------
st.markdown("### Tabla Detallada de Viáticos")
st.markdown("<div class='custom-card'>", unsafe_allow_html=True)

cols_to_show = ['TECNICO', 'LIDER DE CUENTA', 'SERVICIO', 'LOCALIDAD', 'MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS', 'DIFERENCIA', 'DIFERENCIA REAL']
cols_to_show = [c for c in cols_to_show if c in df_filtered.columns]
df_table = df_filtered[cols_to_show].copy()

def color_semaforo(val):
    if not isinstance(val, (int, float)): return ''
    if val > 0: return 'background-color: #d4edda; color: #155724;'
    elif val < 0: return 'background-color: #f8d7da; color: #721c24;'
    return ''

styled_df = df_table.style.map(color_semaforo, subset=['DIFERENCIA', 'DIFERENCIA REAL']).format({
    'MONTO DEPOSITADO': '${:,.2f}', 
    'SUMA VIATICOS VALIDADOS': '${:,.2f}', 
    'DIFERENCIA': '${:,.2f}',
    'DIFERENCIA REAL': '${:,.2f}'
})
st.dataframe(styled_df, use_container_width=True, hide_index=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("### 💬 Comentarios y Notas")
st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
if 'COMENTARIOS' in df_filtered.columns:
    tecnicos_filtrados = df_filtered['TECNICO'].unique().tolist()
    if tecnicos_filtrados:
        tecnico_comentario = st.selectbox("Selecciona un Técnico para ver sus comentarios detallados:", ["-- Selecciona un técnico --"] + tecnicos_filtrados)
        if tecnico_comentario != "-- Selecciona un técnico --":
            df_com = df_filtered[(df_filtered['TECNICO'] == tecnico_comentario) & (df_filtered['COMENTARIOS'].str.strip() != "") & (df_filtered['COMENTARIOS'] != "Sin comentarios")]
            if df_com.empty:
                st.info(f"El técnico {tecnico_comentario} no tiene comentarios.")
            else:
                for idx, row in df_com.iterrows():
                    fecha = row['FECHA SERVICIOS'].strftime('%Y-%m-%d') if pd.notnull(row.get('FECHA SERVICIOS')) else 'Sin fecha'
                    servicio = row.get('SERVICIO', 'Sin servicio')
                    st.markdown(f"**🗓 {fecha} | 🛠 Proyecto:** {servicio} <br>📝 {row['COMENTARIOS']}", unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
