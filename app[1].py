import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO
st.set_page_config(
    page_title="Ubiknos - Dashboard de Viáticos", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Inyectar CSS para dar una apariencia profesional y limpia
st.markdown("""
    <style>
    /* Color de fondo del sidebar */
    [data-testid="stSidebar"] {
        background-color: #f0f4f8;
    }
    /* Títulos principales */
    h1, h2, h3 {
        color: #1A4B8F !important; /* Azul Corporativo */
    }
    /* Estilo para los números de las métricas */
    [data-testid="stMetricValue"] {
        color: #1A4B8F;
    }
    </style>
    """, unsafe_allow_html=True)

# ----------------------------------------------------
# 2. ENCABEZADO PRINCIPAL (CON LOGO CORREGIDO)
# ----------------------------------------------------
col_titulo, col_logo = st.columns([3, 1])

with col_titulo:
    st.title("Control de Viáticos")
    st.markdown("### Tecnología satelital para su tranquilidad")

with col_logo:
    # Intentamos cargar desde una URL oficial alternativa. 
    # TIP PROFESIONAL: Si deseas asegurar que nunca falle, descarga tu logo, 
    # nómbralo 'logo.png', súbelo junto a este archivo a GitHub y cambia esta línea por: st.image("logo.png", width=220)
    try:
        st.image("https://ubiknos.com/wp-content/uploads/2023/04/logo-ubiknos.png", width=220)
    except:
        # Fallback de texto elegante en caso de que la web de origen bloquee la conexión
        st.markdown("<h2 style='text-align: right; color: #1A4B8F;'>UBIKNOS</h2>", unsafe_allow_html=True)

st.markdown("---")

# ----------------------------------------------------
# 3. EXTRACCIÓN Y LIMPIEZA DE DATOS (ESTRICTO POR COLUMNA)
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
    
    # Rellenar columnas faltantes en caso de celdas vacías al final
    while len(df.columns) <= 42:
        df[f'Col_Vacia_{len(df.columns)}'] = 0.0

    cols = list(df.columns)
    
    # Asignar nombres fijos por índice de columna exacto (K=10, Y=24)
    cols[10] = 'MONTO DEPOSITADO'
    cols[24] = 'SUMA VIATICOS VALIDADOS'

    # Mapeo de columnas de Lo Depositado (L a T)
    cat_names = ['Gasolina', 'Casetas', 'Autobus', 'Hospedaje', 'Lavanderia', 'Comidas', 'Renta_Auto', 'Vuelos', 'Extra']
    for i, name in enumerate(cat_names, 11):
        cols[i] = f'DEP_{name}'
        
    # Mapeo de columnas de Lo Validado (AA a AQ, saltando de 2 en 2)
    for i, name in zip(range(26, 43, 2), cat_names):
        cols[i] = f'VAL_{name}'

    df.columns = cols
    
    if 'FECHA SERVICIOS' in df.columns:
        df['FECHA SERVICIOS'] = pd.to_datetime(df['FECHA SERVICIOS'], errors='coerce')
    if 'TECNICO' in df.columns:
        df = df.dropna(subset=['TECNICO'])

    # Función inteligente para corregir formatos regionales de moneda ($1.200,50 vs $1,200.50)
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
                   
    for col in numeric_cols:
        df[col] = df[col].apply(clean_currency)
        
    df['DIFERENCIA'] = df['MONTO DEPOSITADO'] - df['SUMA VIATICOS VALIDADOS']
    
    if 'COMENTARIOS' in df.columns:
        df['COMENTARIOS'] = df['COMENTARIOS'].fillna("Sin comentarios").astype(str)
    else:
        df['COMENTARIOS'] = "Sin comentarios"
        
    return df

df = load_data()
if df.empty: st.stop()

# ----------------------------------------------------
# 4. FILTROS (BARRA LATERAL - SÓLO "UBIKNOS")
# ----------------------------------------------------
st.sidebar.header("Ubiknos") # Ajustado para que diga exactamente "Ubiknos"

date_range = st.sidebar.date_input("Rango de Fechas:", [df['FECHA SERVICIOS'].min().date(), df['FECHA SERVICIOS'].max().date()])
selected_tecnicos = st.sidebar.multiselect("Técnico:", options=sorted(df['TECNICO'].unique()))
selected_servicios = st.sidebar.multiselect("Servicio:", options=sorted(df['SERVICIO'].dropna().unique()))

df_filtered = df.copy()
if len(date_range) == 2:
    df_filtered = df_filtered[(df_filtered['FECHA SERVICIOS'].dt.date >= date_range[0]) & (df_filtered['FECHA SERVICIOS'].dt.date <= date_range[1])]
if selected_tecnicos: 
    df_filtered = df_filtered[df_filtered['TECNICO'].isin(selected_tecnicos)]
if selected_servicios: 
    df_filtered = df_filtered[df_filtered['SERVICIO'].isin(selected_servicios)]

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

delta_color = "normal" if dif_total >= 0 else "inverse"
kpi3.metric("Diferencia Neta", f"${dif_total:,.2f}", 
           delta="Favor Ubiknos" if dif_total > 0 else "Favor Técnico",
           delta_color=delta_color)

# ----------------------------------------------------
# 6. ANÁLISIS GRÁFICO (COLORES ANTERIORES Y TEXTOS VISIBLES)
# ----------------------------------------------------
st.markdown("---")
col_g1, col_g2 = st.columns(2)

cat_display_names = ["Gasolina", "Casetas", "Autobus", "Hospedaje", "Lavanderia", "Comidas", "Renta Auto", "Vuelos", "Extra"]
sum_dep = [df_filtered[f'DEP_{n}'].sum() for n in cat_names]
sum_val = [df_filtered[f'VAL_{n}'].sum() for n in cat_names]

df_chart = pd.DataFrame({
    'Categoría': cat_display_names,
    'Depositado': sum_dep,
    'Validado': sum_val
})

with col_g1:
    st.markdown("**Comparativo: Depositado vs Gastado por Categoría**")
    fig_comp = go.Figure()
    
    # Barras lado a lado con colores de alto contraste originales (Azul vs Verde) y etiquetas exteriores
    fig_comp.add_trace(go.Bar(
        x=df_chart['Categoría'], y=df_chart['Depositado'], name='Depositado', 
        marker_color='#4C72B0', texttemplate='$%{y:,.2f}', textposition='outside'
    ))
    fig_comp.add_trace(go.Bar(
        x=df_chart['Categoría'], y=df_chart['Validado'], name='Gastado Real', 
        marker_color='#55A868', texttemplate='$%{y:,.2f}', textposition='outside'
    ))
    
    fig_comp.update_layout(barmode='group', template='plotly_white', height=460, margin=dict(l=10, r=10, t=30, b=10))
    fig_comp.update_yaxes(tickprefix="$")
    st.plotly_chart(fig_comp, use_container_width=True)

with col_g2:
    st.markdown("**Distribución del Gasto Validado**")
    df_chart_pie = df_chart[df_chart['Validado'] > 0]
    
    if not df_chart_pie.empty:
        # Regresa a la paleta de colores variados Pastel original
        fig_pie = px.pie(
            df_chart_pie, names='Categoría', values='Validado', hole=0.4, 
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        # Textos visuales completos que muestran el nombre, los pesos exactos y el porcentaje
        fig_pie.update_traces(textinfo='value+percent', texttemplate='%{label}<br>$%{value:,.2f}<br>(%{percent})')
        fig_pie.update_layout(height=460, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No hay gastos validados en el filtro seleccionado.")

# ----------------------------------------------------
# 7. TABLA DETALLADA Y COMENTARIOS
# ----------------------------------------------------
st.markdown("---")
st.markdown("### Detalle de Movimientos")
df_t = df_filtered[['TECNICO', 'SERVICIO', 'LOCALIDAD', 'MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS', 'DIFERENCIA']]

st.dataframe(
    df_t.style.map(lambda x: 'background-color: #d4edda; color: #155724;' if x > 0 else ('background-color: #f8d7da; color: #721c24;' if x < 0 else ''), subset=['DIFERENCIA'])
    .format("${:,.2f}", subset=['MONTO DEPOSITADO', 'SUMA VIATICOS VALIDADOS', 'DIFERENCIA']),
    use_container_width=True, hide_index=True
)

st.markdown("---")
st.markdown("### 💬 Bitácora de Comentarios")
tec_sel = st.selectbox("Seleccionar técnico para ver notas:", ["-- Selecciona un técnico --"] + list(df_filtered['TECNICO'].unique()))
if tec_sel != "-- Selecciona un técnico --":
    notas = df_filtered.query(f"TECNICO == '{tec_sel}' and COMENTARIOS != 'Sin comentarios' and COMENTARIOS != ''")
    if notas.empty:
        st.info(f"El técnico {tec_sel} no tiene comentarios registrados.")
    else:
        for _, r in notas.iterrows():
            fecha_str = r['FECHA SERVICIOS'].strftime('%Y-%m-%d') if pd.notnull(r['FECHA SERVICIOS']) else 'Sin Fecha'
            st.info(f"**🗓 {fecha_str} | 🛠 Servicio/Proyecto: {r['SERVICIO']}**\n\n📝 {r['COMENTARIOS']}")
