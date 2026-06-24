import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO UBIKNOS
st.set_page_config(
    page_title="Ubiknos - Dashboard de Viáticos", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Inyectar CSS para personalizar colores de la interfaz (Estilo Ubiknos)
st.markdown("""
    <style>
    /* Color de fondo del sidebar */
    [data-testid="stSidebar"] {
        background-color: #f0f4f8;
    }
    /* Títulos y fuentes */
    h1, h2, h3 {
        color: #1A4B8F !important; /* Azul Marino Ubiknos */
    }
    /* Estilo para las métricas */
    [data-testid="stMetricValue"] {
        color: #1A4B8F;
    }
    </style>
    """, unsafe_allow_html=True)

# ----------------------------------------------------
# 2. ENCABEZADO CON LOGO
# ----------------------------------------------------
col_titulo, col_logo = st.columns([3, 1])

with col_titulo:
    st.title("Control de Viáticos")
    st.markdown("### Tecnología satelital para su tranquilidad")

with col_logo:
    # URL del logo que proporcionaste
    logo_url = "https://files.oaiusercontent.com/file-K1f69W70yOQz9Y1k5y6W0y9D?se=2024-10-24T16%3A01%3A24Z&sp=r&sv=24.10.01&sr=b&rscc=max-age%3D604800%2C%20immutable%2C%20private&rscd=attachment%3B%20filename%3D45860d5b-8664-469b-8703-9d48123bc2d1.webp&sig=6KAnfC%2BqY2oE8L%2BsB%2BM/vGvFp6f/P/P3V6A0K2z7F/k%3D"
    # Nota: Si la URL de arriba expira, asegúrate de guardar la imagen como 'logo.png' 
    # en tu carpeta de GitHub y usar: st.image("logo.png")
    st.image("https://ubiknos.com/wp-content/uploads/2023/04/logo-ubiknos.png", width=250) 

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
    cols[10], cols[24] = 'MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS'
    # Mapeo de columnas depositadas (L a T)
    for i, name in enumerate(['Gasolina', 'Casetas', 'Autobus', 'Hospedaje', 'Lavanderia', 'Comidas', 'Renta_Auto', 'Vuelos', 'Extra'], 11):
        cols[i] = f'DEP_{name}'
    # Mapeo de columnas validadas (AA a AQ saltando de 2 en 2)
    val_names = ['Gasolina', 'Casetas', 'Autobus', 'Hospedaje', 'Lavanderia', 'Comidas', 'Renta_Auto', 'Vuelos', 'Extra']
    for i, name in zip(range(26, 43, 2), val_names):
        cols[i] = f'VAL_{name}'

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

    numeric_cols = ['MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS'] + \
                   [f'DEP_{n}' for n in val_names] + [f'VAL_{n}' for n in val_names]
                   
    for col in numeric_cols:
        df[col] = df[col].apply(clean_currency)
        
    df['DIFERENCIA'] = df['MONTO DEPOSITADO'] - df['SUMA VIATICOS VALIDADOS']
    return df

df = load_data()
if df.empty: st.stop()

# ----------------------------------------------------
# 4. FILTROS (SIDEBAR)
# ----------------------------------------------------
st.sidebar.header("Filtros Ubiknos")
date_range = st.sidebar.date_input("Rango de Fechas:", [df['FECHA SERVICIOS'].min().date(), df['FECHA SERVICIOS'].max().date()])
selected_tecnicos = st.sidebar.multiselect("Técnico:", options=sorted(df['TECNICO'].unique()))
selected_servicios = st.sidebar.multiselect("Servicio:", options=sorted(df['SERVICIO'].dropna().unique()))

df_filtered = df.copy()
if len(date_range) == 2:
    df_filtered = df_filtered[(df_filtered['FECHA SERVICIOS'].dt.date >= date_range[0]) & (df_filtered['FECHA SERVICIOS'].dt.date <= date_range[1])]
if selected_tecnicos: df_filtered = df_filtered[df_filtered['TECNICO'].isin(selected_tecnicos)]
if selected_servicios: df_filtered = df_filtered[df_filtered['SERVICIO'].isin(selected_servicios)]

# ----------------------------------------------------
# 5. RESUMEN GLOBAL (KPIs)
# ----------------------------------------------------
st.markdown("### Resumen de Saldos")
total_dep = df_filtered['MONTO DEPOSITADO'].sum()
total_val = df_filtered['SUMA VIATICOS VALIDADOS'].sum()
dif_total = total_dep - total_val

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Total Depositado", f"${total_dep:,.2f}")
kpi2.metric("Total Gastado Real", f"${total_val:,.2f}")
kpi3.metric("Diferencia Neta", f"${dif_total:,.2f}", 
           delta="Favor Ubiknos" if dif_total > 0 else "Favor Técnico",
           delta_color="normal" if dif_total >= 0 else "inverse")

# ----------------------------------------------------
# 6. ANÁLISIS GRÁFICO (COLORES UBIKNOS)
# ----------------------------------------------------
st.markdown("---")
col_g1, col_g2 = st.columns(2)

cat_names = ["Gasolina", "Casetas", "Autobus", "Hospedaje", "Lavanderia", "Comidas", "Renta Auto", "Vuelos", "Extra"]
sum_dep = [df_filtered[f'DEP_{n}'].sum() for n in ["Gasolina", "Casetas", "Autobus", "Hospedaje", "Lavanderia", "Comidas", "Renta_Auto", "Vuelos", "Extra"]]
sum_val = [df_filtered[f'VAL_{n}'].sum() for n in ["Gasolina", "Casetas", "Autobus", "Hospedaje", "Lavanderia", "Comidas", "Renta_Auto", "Vuelos", "Extra"]]

with col_g1:
    st.markdown("**Comparativa de Gastos**")
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(x=cat_names, y=sum_dep, name='Depositado', marker_color='#7CB3E1')) # Azul Claro Ubiknos
    fig_comp.add_trace(go.Bar(x=cat_names, y=sum_val, name='Gastado Real', marker_color='#1A4B8F')) # Azul Marino Ubiknos
    fig_comp.update_layout(barmode='group', template='plotly_white', height=400)
    st.plotly_chart(fig_comp, use_container_width=True)

with col_g2:
    st.markdown("**Distribución por Categoría**")
    pie_data = pd.DataFrame({'Cat': cat_names, 'Val': sum_val}).query('Val > 0')
    # Paleta de azules degradados
    ubiknos_palette = ['#1A4B8F', '#4A7BB7', '#7CB3E1', '#A6C9E8', '#D1E3F3']
    fig_pie = px.pie(pie_data, names='Cat', values='Val', hole=0.4, color_discrete_sequence=ubiknos_palette)
    fig_pie.update_traces(textinfo='value+percent', texttemplate='$%{value:,.0f}<br>%{percent}')
    st.plotly_chart(fig_pie, use_container_width=True)

# ----------------------------------------------------
# 7. TABLA Y COMENTARIOS
# ----------------------------------------------------
st.markdown("### Detalle de Movimientos")
df_t = df_filtered[['TECNICO', 'SERVICIO', 'LOCALIDAD', 'MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS', 'DIFERENCIA']]

# Formato condicional
st.dataframe(
    df_t.style.map(lambda x: 'background-color: #d4edda' if x > 0 else ('background-color: #f8d7da' if x < 0 else ''), subset=['DIFERENCIA'])
    .format("${:,.2f}", subset=['MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS', 'DIFERENCIA']),
    use_container_width=True, hide_index=True
)

st.markdown("---")
st.markdown("### 💬 Bitácora de Comentarios")
tec_sel = st.selectbox("Seleccionar técnico para ver notas:", ["--"] + list(df_filtered['TECNICO'].unique()))
if tec_sel != "--":
    notas = df_filtered.query(f"TECNICO == '{tec_sel}' and COMENTARIOS != 'Sin comentarios'")
    for _, r in notas.iterrows():
        st.info(f"**{r['FECHA SERVICIOS'].date()} - {r['SERVICIO']}:** {r['COMENTARIOS']}")
