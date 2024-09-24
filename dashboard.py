import pandas as pd
import numpy as np
import streamlit as st
import folium
from streamlit_folium import folium_static
import plotly.express as px
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events
import os

# Configuración de la página
st.set_page_config(layout="wide", page_title="Dashboard de Inventario de Árboles")

# Paleta de colores personalizada
color_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

# Estilos CSS y JavaScript personalizados
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    h1, h2, h3 {
        color: #2c3e50;
        margin-bottom: 1rem;
    }
    .stButton > button {
        color: #ffffff;
        background-color: #2c3e50;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
    }
    .stButton > button:hover {
        background-color: #34495e;
    }
    .element-container {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .plotly-graph-div {
        margin: 0 auto;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
    }
    .stDataFrame {
        font-size: 0.8rem;
    }
    .modebar {
        display: none !important;
    }
</style>

<script>
    function hideModebar() {
        var modebars = document.querySelectorAll('.modebar');
        modebars.forEach(function(bar) {
            bar.style.display = 'none';
        });
    }
    
    // Run on load
    hideModebar();
    
    // Run every 100ms for a while to catch any delayed rendering
    var interval = setInterval(hideModebar, 100);
    setTimeout(function() { clearInterval(interval); }, 10000);
</script>
""", unsafe_allow_html=True)

# Cargar y procesar los datos
@st.cache_data
def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'tree_data.csv')
    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
        df['long'] = pd.to_numeric(df['long'].str.replace(',', '.'), errors='coerce')
        df['lat'] = pd.to_numeric(df['lat'].str.replace(',', '.'), errors='coerce')
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
        df['Etiquetas'] = df['NombreEtiqueta'].str.split(',')
        df['Cantidad_Etiquetas'] = df['Etiquetas'].apply(len)
        df['Fecha_DM'] = df['Fecha'].dt.strftime('%d/%m')
        df = df.dropna(subset=['lat', 'long'])
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos: {str(e)}")
        return None

# Crear mapa con Folium
def create_map(df):
    if df.empty:
        return folium.Map(location=[0, 0], zoom_start=2)
    
    center_lat = df['lat'].mean()
    center_long = df['long'].mean()
    m = folium.Map(location=[center_lat, center_long], zoom_start=14, tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri')
    
    for idx, row in df.iterrows():
        folium.CircleMarker(
            location=[row['lat'], row['long']],
            radius=6,
            popup=f"Etiqueta: {row['NombreEtiqueta']}<br>Cuadrícula: {row['cuadricula']}<br>Fecha: {row['Fecha'].strftime('%d/%m/%Y')}",
            tooltip=row['NombreEtiqueta'],
            color='black',
            fill=True,
            fillColor='green',
            fillOpacity=0.7
        ).add_to(m)
    return m

# Crear gráficos con Plotly
def create_charts(df):
    # Gráfico de barras: Cantidad de árboles por cuadrícula
    cuadricula_counts = df['cuadricula'].value_counts().reset_index()
    cuadricula_counts.columns = ['Cuadrícula', 'Cantidad']
    fig_cuadricula = px.bar(cuadricula_counts, 
                            x='Cuadrícula', 
                            y='Cantidad',
                            title='Cantidad de árboles por cuadrícula',
                            color='Cuadrícula',
                            color_discrete_sequence=color_palette)
    fig_cuadricula.update_traces(texttemplate='%{y}', textposition='outside')
    fig_cuadricula.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis_title='Cantidad de Árboles',
        showlegend=False,
        height=400,
        xaxis_title='',
        margin=dict(l=50, r=20, t=50, b=50)
    )
    
    # Gráfico de serie temporal
    df_temporal = df.groupby('Fecha_DM').size().reset_index(name='Cantidad')
    fig_temporal = px.line(df_temporal, x='Fecha_DM', y='Cantidad', 
                           title='Cantidad de árboles etiquetados por día',
                           color_discrete_sequence=['#2ca02c'])
    fig_temporal.update_traces(mode='lines+markers', marker=dict(size=8))
    fig_temporal.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis_title='Cantidad de Árboles',
        xaxis_title='Fecha (Día/Mes)',
        showlegend=False,
        height=400,
        margin=dict(l=50, r=20, t=50, b=50)
    )
    fig_temporal.add_trace(go.Scatter(
        x=df_temporal['Fecha_DM'],
        y=df_temporal['Cantidad'],
        mode='text',
        text=df_temporal['Cantidad'],
        textposition='top center',
        showlegend=False
    ))
    
    # Configurar ambos gráficos para ocultar la barra de herramientas
    for fig in [fig_cuadricula, fig_temporal]:
        fig.update_layout(modebar_remove=['all'])
    
    return fig_cuadricula, fig_temporal

# Función para aplicar filtros
def apply_filters(df, cuadricula_seleccionada, fecha_seleccionada):
    df_filtrado = df.copy()
    if cuadricula_seleccionada:
        df_filtrado = df_filtrado[df_filtrado['cuadricula'].isin(cuadricula_seleccionada)]
    if fecha_seleccionada:
        df_filtrado = df_filtrado[df_filtrado['Fecha_DM'] == fecha_seleccionada]
    return df_filtrado

# Función para resetear filtros
def reset_filters():
    st.session_state.cuadricula_seleccionada = []
    st.session_state.fecha_seleccionada = None
    st.rerun()

# Aplicación principal de Streamlit
def main():
    st.title('Dashboard de Inventario de Etiquetas de Árboles')
    
    # Cargar datos
    df = load_data()
    if df is None or df.empty:
        st.error("No se pudieron cargar los datos o el conjunto de datos está vacío. Por favor, verifica el archivo CSV.")
        return

    # Inicializar variables de estado
    if 'cuadricula_seleccionada' not in st.session_state:
        st.session_state.cuadricula_seleccionada = []
    if 'fecha_seleccionada' not in st.session_state:
        st.session_state.fecha_seleccionada = None

    # Botón para resetear filtros (arriba)
    if st.button('Resetear Filtros', key='reset_top'):
        reset_filters()

    # Aplicar filtros
    df_filtrado = apply_filters(df, st.session_state.cuadricula_seleccionada, st.session_state.fecha_seleccionada)

    # Layout en columnas
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader('Mapa de árboles etiquetados')
        m = create_map(df_filtrado)
        folium_static(m, width=700, height=500)

    with col2:
        st.metric(label="Total de árboles etiquetados", value=len(df_filtrado))
        st.subheader('Datos de árboles etiquetados')
        st.dataframe(df_filtrado[['NombreEtiqueta', 'cuadricula', 'Fecha', 'Operador']], height=350)

    st.markdown("---")
    st.subheader('Análisis de datos')
    
    fig_cuadricula, fig_temporal = create_charts(df_filtrado)
    
    col3, col4 = st.columns(2)
    
    with col3:
        selected_cuadricula = plotly_events(fig_cuadricula, click_event=True, override_height="450px")
        if selected_cuadricula:
            st.session_state.cuadricula_seleccionada = [selected_cuadricula[0]['x']]
            st.rerun()

    with col4:
        selected_date = plotly_events(fig_temporal, click_event=True, override_height="450px")
        if selected_date:
            st.session_state.fecha_seleccionada = selected_date[0]['x']
            st.rerun()

    # Botón para resetear filtros (abajo)
    if st.button('Resetear Filtros', key='reset_bottom'):
        reset_filters()

if __name__ == "__main__":
    main()
