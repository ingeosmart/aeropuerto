import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static
import plotly.express as px
import plotly.graph_objects as go
import os
from streamlit_plotly_events import plotly_events

# Configuración de la página
st.set_page_config(layout="wide", page_title="Dashboard de Inventario de Árboles")

# Definir una paleta de colores profesional
color_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

# Estilos CSS personalizados
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        color: #2c3e50;
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
    </style>
    """, unsafe_allow_html=True)

# Cargar y procesar los datos
@st.cache_data
def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'tree_data.csv')
    
    try:
        # Intenta leer el CSV con diferentes separadores
        for sep in [',', ';', '\t', ' ']:
            try:
                df = pd.read_csv(csv_path, sep=sep, engine='python')
                break
            except:
                continue
        
        if 'df' not in locals():
            raise Exception("No se pudo leer el archivo CSV con ningún separador común.")
        
        df['long'] = df['long'].str.replace(',', '.').astype(float)
        df['lat'] = df['lat'].str.replace(',', '.').astype(float)
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y %H:%M:%S,%f', errors='coerce')
        df['Etiquetas'] = df['NombreEtiqueta'].str.split(',')
        df['Cantidad_Etiquetas'] = df['Etiquetas'].apply(len)
        df['Fecha_DM'] = df['Fecha'].dt.strftime('%d/%m')
        return df
    
    except Exception as e:
        st.error(f"Error al cargar los datos: {str(e)}")
        st.error(f"Primeras filas del CSV:")
        try:
            with open(csv_path, 'r') as f:
                st.code(f.read(500))
        except:
            st.error("No se pudo leer el archivo CSV para mostrar las primeras filas.")
        return None

# Crear mapa con Folium
def create_map(df):
    m = folium.Map(location=[df['lat'].mean(), df['long'].mean()], zoom_start=14, tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri')
    
    for idx, row in df.iterrows():
        folium.CircleMarker(
            location=[row['lat'], row['long']],
            radius=6,
            popup=f"Etiqueta: {row['NombreEtiqueta']}<br>Cuadrícula: {row['cuadricula']}",
            tooltip=row['NombreEtiqueta'],
            color='black',
            fill=True,
            fillColor='green',
            fillOpacity=0.7
        ).add_to(m)
    
    return m

# Crear gráficos con Plotly
@st.cache_data
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
        xaxis_title='Cuadrícula',
        legend_title_text='',
        font=dict(family="Arial, sans-serif", size=12, color="#2c3e50")
    )
    
    # Gráfico de serie temporal
    df_temporal = df.groupby('Fecha_DM').size().reset_index(name='Cantidad')
    fig_temporal = px.line(df_temporal, x='Fecha_DM', y='Cantidad', 
                           title='Cantidad de árboles etiquetados por día')
    fig_temporal.update_traces(line_color="#2ca02c", mode='lines+markers')
    fig_temporal.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis_title='Cantidad de Árboles',
        xaxis_title='Fecha (Día/Mes)',
        font=dict(family="Arial, sans-serif", size=12, color="#2c3e50")
    )
    
    return fig_cuadricula, fig_temporal

# Función para aplicar filtros
def apply_filters(df, cuadricula_seleccionada, fecha_seleccionada):
    df_filtrado = df.copy()
    
    if cuadricula_seleccionada:
        df_filtrado = df_filtrado[df_filtrado['cuadricula'].isin(cuadricula_seleccionada)]
    
    if fecha_seleccionada:
        df_filtrado = df_filtrado[df_filtrado['Fecha_DM'] == fecha_seleccionada]
    
    return df_filtrado

# Aplicación principal de Streamlit
def main():
    st.title('Dashboard de Inventario de Etiquetas de Árboles')
    st.markdown("---")

    # Cargar datos
    df = load_data()
    
    if df is None:
        st.error("No se pudieron cargar los datos. Por favor, verifica el archivo CSV.")
        return

    # Inicializar variables de estado
    if 'cuadricula_seleccionada' not in st.session_state:
        st.session_state.cuadricula_seleccionada = []
    if 'fecha_seleccionada' not in st.session_state:
        st.session_state.fecha_seleccionada = None

    # Sidebar para filtros
    with st.sidebar:
        st.header('Filtros')
        st.session_state.cuadricula_seleccionada = st.multiselect('Seleccionar cuadrícula', df['cuadricula'].unique(), st.session_state.cuadricula_seleccionada)
        
        if st.button('Resetear Filtros', key='reset_filters'):
            st.session_state.cuadricula_seleccionada = []
            st.session_state.fecha_seleccionada = None
            st.rerun()

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
        st.dataframe(df_filtrado, height=350)

    st.markdown("---")
    st.subheader('Análisis de datos')
    
    fig_cuadricula, fig_temporal = create_charts(df_filtrado)
    
    col3, col4 = st.columns(2)
    
    with col3:
        selected_cuadricula = plotly_events(fig_cuadricula, click_event=True, override_height=450)
        if selected_cuadricula:
            st.session_state.cuadricula_seleccionada = [point['x'] for point in selected_cuadricula]
            st.rerun()
    
    with col4:
        selected_dates = plotly_events(fig_temporal, click_event=True, override_height=450)
        if selected_dates:
            st.session_state.fecha_seleccionada = selected_dates[0]['x']
            st.rerun()

if __name__ == "__main__":
    main()