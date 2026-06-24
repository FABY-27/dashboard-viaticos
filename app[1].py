import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# ----------------------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS CSS
# ----------------------------------------------------
st.set_page_config(page_title="Dashboard Ubiknos", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Fondo general de la aplicación: Blanco */
    .stApp {
        background-color: #FFFFFF;
    }

    /* Menú lateral (Sidebar): Azul claro con letras blancas */
    [data-testid="stSidebar"] {
        background-color: #4A90E2 !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div,
    .stDateInput input {
        background-color: #FFFFFF !important;
        color: #333333 !important;
    }

    /* TARJETAS NEGRAS (Resumen y Gráficos) */
    .black-card {
        background-color: #000000 !important;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;
        color: #FFFFFF !important;
    }
    .black-card h2, .black-card h4, .black-card p {
        color: #FFFFFF !important;
    }

    /* TARJETAS CLARAS (Tablas y Comentarios) */
    .light-card {
        background-color: #F8FBFF;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
        border: 1px solid #E1E8F0;
    }

    /* Título Ubiknos esquina superior derecha */
    .ubiknos-header {
        position: absolute;
        top: -50px;
        right: 10px;
        font-size: 28px;
        font-weight: bold;
        color: #1A4B8F;
        letter-spacing: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. CARGA Y LIMPIEZA DE DATOS (Mismo motor anterior)
# ----------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    sheet_url = "https://docs.google.com/spreadsheets/d/1shaXJ60_JQuxBEAgjzPEJJqqbIgcEavPRo_oeWvsX7Y/edit?usp=sharing"
    try:
        file_id = sheet_url.split("/d/")[1].split("/")[0]
        export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&sheet=Viaticos"
        df = pd.read_csv(export_url, header=1)
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    while len(df.columns) <= 42:
        df[f'Col_{len(df.columns)}'] = 0.0

    cols = list(df.columns)
    cols[10] = 'MONTO DEPOSITADO'
    cols[24] = 'SUMA VIATICOS VALIDADOS'
    
    cat_names = ['Gasolina', 'Casetas', 'Autobus', 'Hospedaje', 'Lavanderia', 'Comidas', 'Renta_Auto', 'Vuelos', 'Extra']
    for i, name in enumerate(cat_names, 11): cols[i] = f'DEP_{name}'
    for i, name in zip(range(26, 43, 2), cat_names): cols[i] = f'VAL_{name}'
    
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
                   [f'DEP_{n}' for n in cat_names] + [f'VAL_{n}' for n in cat_names]
    for col in numeric_cols: df[col] = df[col].apply(clean_currency)
    df['DIFERENCIA'] = df['MONTO DEPOSITADO'] - df['SUMA VIATICOS VALIDADOS']
    if 'COMENTARIOS' in df.columns: df['COMENTARIOS'] = df['COMENTARIOS'].fillna("").astype(str)
    return df

df = load_data()
if df.empty: st.stop()

# ----------------------------------------------------
# 3. FILTROS (SIDEBAR)
# ----------------------------------------------------
st.sidebar.markdown("# Ubiknos")
min_d, max_d = df['FECHA SERVICIOS'].min(), df['FECHA SERVICIOS'].max()
date_range = st.sidebar.date_input("Rango de Fechas:", [min_d.date(), max_d.date()])
sel_tec = st.sidebar.multiselect("Técnico:", options=sorted(df['TECNICO'].unique()))
sel_ser = st.sidebar.multiselect("Servicio:", options=sorted(df['SERVICIO'].dropna().unique()))

df_filtered = df.copy()
if len(date_range) == 2:
    df_filtered = df_filtered[(df_filtered['FECHA SERVICIOS'].dt.date >= date_range[0]) & (df_filtered['FECHA SERVICIOS'].dt.date <= date_range[1])]
if sel_tec: df_filtered = df_filtered[df_filtered['TECNICO'].isin(sel_tec)]
if sel_ser: df_filtered = df_filtered[df_filtered['SERVICIO'].isin(sel_ser)]

# ----------------------------------------------------
# 4. DASHBOARD - RESUMEN GLOBAL (FONDO NEGRO)
# ----------------------------------------------------
# Texto Ubiknos arriba a la derecha
st.markdown("<div class='ubiknos-header'>UBIKNOS</div>", unsafe_allow_html=True)

st.title("📊 Control de Viáticos")
st.markdown("---")

st.markdown("### Resumen Global")
total_dep = df_filtered['MONTO DEPOSITADO'].sum()
total_val = df_filtered['SUMA VIATICOS VALIDADOS'].sum()
dif_total = total_dep - total_val

kpi_html = f"""
<div style="display: flex; justify-content: space-between; gap: 20px; margin-bottom: 25px;">
    <div class="black-card" style="flex: 1; text-align: center;">
        <p style="margin:0; font-size:16px; opacity:0.8;">Total Depositado</p>
        <h2 style="margin:5px 0 0 0;">${total_dep:,.2f}</h2>
    </div>
    <div class="black-card" style="flex: 1; text-align: center;">
        <p style="margin:0; font-size:16px; opacity:0.8;">Total Gastado Real</p>
        <h2 style="margin:5px 0 0 0;">${total_val:,.2f}</h2>
    </div>
    <div class="black-card" style="flex: 1; text-align: center;">
        <p style="margin:0; font-size:16px; opacity:0.8;">Diferencia Neta</p>
        <h2 style="margin:5px 0 0 0; color:{'#FF4B4B' if dif_total < 0 else '#00FF7F'} !important;">${dif_total:,.2f}</h2>
    </div>
</div>
"""
st.markdown(kpi_html, unsafe_allow_html=True)

# ----------------------------------------------------
# 5. ANÁLISIS GRÁFICO (FONDO NEGRO / LETRAS BLANCAS)
# ----------------------------------------------------
st.markdown("### Análisis Gráfico")
col_g1, col_g2 = st.columns(2)

cat_names = ["Gasolina", "Casetas", "Autobus", "Hospedaje", "Lavanderia", "Comidas", "Renta Auto", "Vuelos", "Extra"]
sum_dep = [df_filtered[f'DEP_{n.replace(" ", "_")}'].sum() for n in cat_names]
sum_val = [df_filtered[f'VAL_{n.replace(" ", "_")}'].sum() for n in cat_names]

with col_g1:
    st.markdown("<div class='black-card'>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-weight:bold;'>Comparativo: Depositado vs Gastado</p>", unsafe_allow_html=True)
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=cat_names, y=sum_dep, name='Depositado', marker_color='#00D4FF', texttemplate='$%{y:,.0f}', textposition='outside'))
    fig_bar.add_trace(go.Bar(x=cat_names, y=sum_val, name='Gastado Real', marker_color='#00FF7F', texttemplate='$%{y:,.0f}', textposition='outside'))
    
    fig_bar.update_layout(
        barmode='group', height=400, margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_bar.update_xaxes(showgrid=False, color="white")
    fig_bar.update_yaxes(showgrid=True, gridcolor="#333333", color="white", tickprefix="$")
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_g2:
    st.markdown("<div class='black-card'>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-weight:bold;'>Distribución del Gasto Validado</p>", unsafe_allow_html=True)
    pie_data = pd.DataFrame({'Cat': cat_names, 'Val': sum_val}).query('Val > 0')
    if not pie_data.empty:
        fig_pie = px.pie(pie_data, names='Cat', values='Val', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_pie.update_traces(textinfo='value+percent', texttemplate='%{label}<br>$%{value:,.0f}<br>(%{percent})')
        fig_pie.update_layout(
            height=400, margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white")
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.markdown("<p style='text-align:center; padding:150px 0;'>Sin datos para mostrar</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 6. TABLA Y COMENTARIOS (FONDOS CLAROS)
# ----------------------------------------------------
st.markdown("### Detalle de Movimientos")
st.markdown("<div class='light-card'>", unsafe_allow_html=True)
df_t = df_filtered[['TECNICO', 'SERVICIO', 'LOCALIDAD', 'MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS', 'DIFERENCIA']]
st.dataframe(
    df_t.style.map(lambda x: 'background-color: #d4edda' if x > 0 else ('background-color: #f8d7da' if x < 0 else ''), subset=['DIFERENCIA'])
    .format("${:,.2f}", subset=['MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS', 'DIFERENCIA']),
    use_container_width=True, hide_index=True
)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("### 💬 Comentarios")
st.markdown("<div class='light-card'>", unsafe_allow_html=True)
tec_sel = st.selectbox("Seleccionar técnico para ver notas:", ["-- Selecciona --"] + list(df_filtered['TECNICO'].unique()))
if tec_sel != "-- Selecciona --":
    notas = df_filtered.query(f"TECNICO == '{tec_sel}' and COMENTARIOS != ''")
    if notas.empty: st.info("Sin comentarios.")
    else:
        for _, r in notas.iterrows():
            st.write(f"**{r['FECHA SERVICIOS'].date()} - {r['SERVICIO']}:** {r['COMENTARIOS']}")
st.markdown("</div>", unsafe_allow_html=True)
