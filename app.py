import os
os.environ['PROJ_LIB'] = '/usr/share/proj'
os.environ['GDAL_DATA'] = '/usr/share/gdal'
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, Search, LocateControl, Fullscreen, MarkerCluster
from shapely.geometry import Point, Polygon, shape
from fpdf import FPDF
from datetime import datetime
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import base64
from io import BytesIO
import tempfile
import unicodedata
from streamlit_searchbox import st_searchbox

# Configuración de la página
st.set_page_config(page_title="Sistema de Continuidad", layout="wide")
st.title("🚨 Mapa de Continuidad del Negocio")

# Límites para optimización
MAX_MARKERS = 3000  # Máximo de marcadores en el mapa

# ---------- CONFIGURACIÓN DE MAPAS ----------
TILES = {
    "MapLibre": {
        "url": "https://api.maptiler.com/maps/streets/{z}/{x}/{y}.png?key=dhEAG0dMVs2vmsaHdReR",
        "attr": '<a href="https://www.maptiler.com/copyright/" target="_blank">© MapTiler</a>'
    },
    "OpenStreetMap": {
        "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": 'OpenStreetMap'
    }
}

# ---------- SEDES FIJAS ----------
SEDES_FIJAS = {
    "Colmédica Belaire": {
        "direccion": "Centro Comercial Belaire Plaza, Cl. 153 #6-65, Bogotá",
        "coordenadas": [4.729454000113993, -74.02444216931787],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Bulevar Niza": {
        "direccion": "Centro Comercial Bulevar Niza, Av. Calle 58 #127-59, Bogotá",
        "coordenadas": [4.712693239837536, -74.07140074602322],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Calle 185": {
        "direccion": "Centro Comercial Santafé, Cl. 185 #45-03, Bogotá",
        "coordenadas": [4.763543959141223, -74.04612616931786],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Cedritos": {
        "direccion": "Edificio HHC, Cl. 140 #11-45, Bogotá",
        "coordenadas": [4.718879348342116, -74.03609218650581],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Chapinero": {
        "direccion": "Cr. 7 #52-53, Chapinero, Bogotá",
        "coordenadas": [4.640908410923512, -74.06373898409286],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Colina Campestre": {
        "direccion": "Centro Comercial Sendero de la Colina, Cl. 151 #54-15, Bogotá",
        "coordenadas": [4.73397996072128, -74.05613864417634],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Centro Médico Colmédica Country Park": {
        "direccion": "Autopista Norte No 122 - 96, Bogotá",
        "coordenadas": [4.670067290638234, -74.05758327116473],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Metrópolis": {
        "direccion": "Centro Comercial Metrópolis, Av. Cra. 68 #75A-50, Bogotá",
        "coordenadas": [4.6812256618088615, -74.08315698409288],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Multiplaza": {
        "direccion": "Centro Comercial Multiplaza, Cl. 19A #72-57, Bogotá",
        "coordenadas": [4.652573284106405, -74.12629091534289],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Plaza Central": {
        "direccion": "Centro Comercial Plaza Central, Cra. 65 #11-50, Bogotá",
        "coordenadas": [4.633464230539147, -74.11621916981814],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Salitre Capital": {
        "direccion": "Capital Center II, Av. Cl. 26 #69C-03, Bogotá",
        "coordenadas": [4.660602588141229, -74.10864383068576],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Suba": {
        "direccion": "Alpaso Plaza, Av. Cl. 145 #103B-69, Bogotá",
        "coordenadas": [4.7499608085787575, -74.08737693178564],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Centro Médico Torre Santa Bárbara": {
        "direccion": "Autopista Norte No 122 - 96, Bogotá",
        "coordenadas": [4.70404406297091, -74.053790252428],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Unicentro Occidente": {
        "direccion": "Centro Comercial Unicentro Occidente, Cra. 111C #86-05, Bogotá",
        "coordenadas": [4.724354935414492, -74.11430016931786],
        "color": "blue",
        "icono": "hospital"
    },
    "Colmédica Usaquén": {
        "direccion": "Centro Comercial Usaquén, Cra. 7 #120-20, Bogotá",
        "coordenadas": [4.6985109910547695, -74.03076183068214],
        "color": "blue",
        "icono": "hospital"
    }
}

# ---------- FUNCIONES ----------
def remove_accents(input_str):
    """Elimina acentos de los caracteres"""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

@st.cache_data(ttl=3600)
def load_data(uploaded_file):
    """Carga y limpia el archivo CSV optimizado"""
    try:
        # Lectura del archivo
        if uploaded_file.size > 10 * 1024 * 1024:  # Si pesa más de 10MB
            chunks = pd.read_csv(uploaded_file, chunksize=500)
            df = pd.concat(chunks)
        else:
            df = pd.read_csv(uploaded_file)

        # Validación de columnas
        required_cols = ["Nombre", "Dirección", "Sede asignada", "Teléfono", 
                        "Ciudad", "Subproceso", "Criticidad", "Latitud", "Longitud"]
        if not all(col in df.columns for col in required_cols):
            st.error("El archivo no tiene las columnas requeridas")
            return None
        
        # Limpieza de datos
        df = df.dropna(subset=["Latitud", "Longitud"])
        df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
        df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce")
        df = df.dropna(subset=["Latitud", "Longitud"])
        df = df[(df["Latitud"].between(-90, 90)) & (df["Longitud"].between(-180, 180))]
        
        # Muestra representativa si es muy grande
        if len(df) > MAX_MARKERS:
            st.info(f"🔍 Mostrando muestra de {MAX_MARKERS} de {len(df)} registros")
            return df.sample(MAX_MARKERS)
        return df
    
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return None

def crear_mapa_base(location=[4.5709, -74.2973], zoom_start=12, tile_provider="MapLibre"):
    """Crea mapa base optimizado"""
    m = folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles=TILES[tile_provider]["url"],
        attr=TILES[tile_provider]["attr"],
        control_scale=True,
        prefer_canvas=True
    )
    
    LocateControl(auto_start=False).add_to(m)
    Fullscreen().add_to(m)
    
    Draw(
        export=True,
        position="topleft",
        draw_options={
            'polyline': False,
            'rectangle': True,
            'polygon': True,
            'circle': True,
            'marker': False
        }
    ).add_to(m)
    
    return m

def aplicar_filtros(df, ciudad, criticidad, subproceso):
    """Aplica filtros al dataframe"""
    filtered_df = df.copy()
    
    if ciudad and ciudad != "Todas":
        filtered_df = filtered_df[filtered_df["Ciudad"] == ciudad]
    
    if criticidad and criticidad != "Todas":
        filtered_df = filtered_df[filtered_df["Criticidad"] == criticidad]
    
    if subproceso and subproceso != "Todos":
        filtered_df = filtered_df[filtered_df["Subproceso"] == subproceso]
    
    return filtered_df

def buscar_direccion_colombia(direccion):
    """Geocodificación optimizada"""
    try:
        geolocator = Nominatim(
            user_agent="continuidad_app",
            timeout=10,
            country_codes="co"
        )
        location = geolocator.geocode(f"{direccion}, Colombia", exactly_one=True)
        return location if location and "Colombia" in location.address else None
    except Exception:
        return None

def generar_reporte(zona_dibujada, df, sedes_fijas):
    """Genera reporte con geometrías simplificadas"""
    if not zona_dibujada or 'geometry' not in zona_dibujada:
        return None
    
    try:
        zona_shape = shape(zona_dibujada['geometry'])
        
        def round_coords(x, y):
            return (round(x, 5), round(y, 5))
        
        colaboradores_afectados = []
        for _, row in df.iterrows():
            punto = Point(round_coords(row["Longitud"], row["Latitud"]))
            if zona_shape.contains(punto):
                colaboradores_afectados.append(row)
        
        sedes_afectadas = []
        for nombre, datos in sedes_fijas.items():
            punto = Point(round_coords(datos["coordenadas"][1], datos["coordenadas"][0]))
            if zona_shape.contains(punto):
                sedes_afectadas.append({
                    "Nombre": nombre,
                    "Dirección": datos["direccion"],
                    "Coordenadas": datos["coordenadas"]
                })
        
        return {
            "total_colaboradores": len(colaboradores_afectados),
            "total_sedes": len(sedes_afectadas),
            "colaboradores_afectados": pd.DataFrame(colaboradores_afectados),
            "sedes_afectadas": pd.DataFrame(sedes_afectadas),
            "zona": zona_dibujada
        }
    
    except Exception as e:
        st.error(f"Error al generar reporte: {str(e)}")
        return None

def generar_graficas(reporte):
    """Genera gráficas para el reporte"""
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
    
    if not reporte["sedes_afectadas"].empty:
        reporte["sedes_afectadas"]["Nombre"].value_counts().plot(
            kind='bar', ax=ax[0], color='salmon')
        ax[0].set_title('Sedes Afectadas', fontsize=10)
        ax[0].tick_params(axis='x', rotation=45, labelsize=8)
    
    if not reporte["colaboradores_afectados"].empty:
        reporte["colaboradores_afectados"]["Criticidad"].value_counts().plot(
            kind='pie', ax=ax[1], autopct='%1.1f%%', textprops={'fontsize': 8})
        ax[1].set_title('Distribución por Criticidad', fontsize=10)
    
    if not reporte["colaboradores_afectados"].empty:
        reporte["colaboradores_afectados"]["Subproceso"].value_counts().head(5).plot(
            kind='barh', ax=ax[2], color='lightgreen')
        ax[2].set_title('Top 5 Subprocesos Afectados', fontsize=10)
    
    plt.tight_layout()
    return fig

def generar_graficas_pdf(reporte):
    """Genera gráficas optimizadas para PDF"""
    figuras = []
    
    if not reporte["sedes_afectadas"].empty:
        fig1, ax1 = plt.subplots(figsize=(8, 4))
        reporte["sedes_afectadas"]["Nombre"].value_counts().plot(
            kind='bar', ax=ax1, color='salmon')
        ax1.set_title('Sedes Afectadas', fontsize=12)
        ax1.tick_params(axis='x', rotation=45, labelsize=10)
        plt.tight_layout()
        figuras.append(fig1)
    
    if not reporte["colaboradores_afectados"].empty:
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        reporte["colaboradores_afectados"]["Criticidad"].value_counts().plot(
            kind='pie', ax=ax2, autopct='%1.1f%%', textprops={'fontsize': 10})
        ax2.set_title('Distribución por Criticidad', fontsize=12)
        plt.tight_layout()
        figuras.append(fig2)
    
    if not reporte["colaboradores_afectados"].empty:
        fig3, ax3 = plt.subplots(figsize=(8, 4))
        reporte["colaboradores_afectados"]["Subproceso"].value_counts().head(5).plot(
            kind='barh', ax=ax3, color='lightgreen')
        ax3.set_title('Top 5 Subprocesos Afectados', fontsize=12)
        ax3.tick_params(axis='both', labelsize=10)
        plt.tight_layout()
        figuras.append(fig3)
    
    return figuras

def crear_pdf(reporte, tipo_evento, descripcion_emergencia=""):
    """Crea un PDF con el reporte de emergencia"""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="REPORTE DE EMERGENCIA - COLMÉDICA", ln=1, align='C')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1)
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Información del Evento", ln=1)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Tipo de evento: {remove_accents(tipo_evento)}", ln=1)
        
        descripcion_simple = remove_accents(descripcion_emergencia)
        pdf.multi_cell(0, 10, txt=f"Descripción: {descripcion_simple}")
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Resumen de la Emergencia", ln=1)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Total colaboradores afectados: {reporte['total_colaboradores']}", ln=1)
        pdf.cell(200, 10, txt=f"Total sedes afectadas: {reporte['total_sedes']}", ln=1)
        
        if 'emergencia_location' in st.session_state:
            ubicacion_simple = remove_accents(st.session_state.emergencia_location['address'])
            pdf.cell(200, 10, txt=f"Ubicación: {ubicacion_simple}", ln=1)
        pdf.ln(10)
        
        figuras_pdf = generar_graficas_pdf(reporte)
        
        temp_files = []
        try:
            for fig in figuras_pdf:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmpfile:
                    fig.savefig(tmpfile.name, dpi=150, bbox_inches='tight')
                    temp_files.append(tmpfile.name)
                plt.close(fig)
            
            for temp_file in temp_files:
                pdf.add_page()
                pdf.image(temp_file, x=10, w=190)
        finally:
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
        if not reporte["sedes_afectadas"].empty:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt="Sedes Afectadas", ln=1)
            pdf.set_font("Arial", size=10)
            
            for _, row in reporte["sedes_afectadas"].iterrows():
                nombre_simple = remove_accents(row['Nombre'])
                direccion_simple = remove_accents(row['Dirección'])
                pdf.multi_cell(0, 6, txt=f"- {nombre_simple}: {direccion_simple}")
                pdf.ln(2)
        
        if not reporte["colaboradores_afectados"].empty:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt="Colaboradores Afectados (primeros 50)", ln=1)
            pdf.set_font("Arial", size=8)
            
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(60, 6, "Nombre", 1, 0, 'C', True)
            pdf.cell(50, 6, "Sede", 1, 0, 'C', True)
            pdf.cell(50, 6, "Subproceso", 1, 0, 'C', True)
            pdf.cell(30, 6, "Criticidad", 1, 1, 'C', True)
            
            pdf.set_fill_color(255, 255, 255)
            for _, row in reporte["colaboradores_afectados"].head(50).iterrows():
                nombre_simple = remove_accents(row['Nombre'])[:25]
                sede_simple = remove_accents(row['Sede asignada'])[:20]
                subproceso_simple = remove_accents(row['Subproceso'])[:20]
                
                pdf.cell(60, 6, txt=nombre_simple, border=1)
                pdf.cell(50, 6, txt=sede_simple, border=1)
                pdf.cell(50, 6, txt=subproceso_simple, border=1)
                pdf.cell(30, 6, txt=str(row['Criticidad']), border=1, ln=1)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            pdf.output(tmp_pdf.name)
            tmp_pdf.seek(0)
            pdf_bytes = tmp_pdf.read()
        
        return pdf_bytes
    
    except Exception as e:
        st.error(f"Error al generar el PDF: {str(e)}")
        return None

def get_table_download_link(df, filename="reporte.csv"):
    """Genera un enlace para descargar un dataframe como CSV"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Descargar archivo CSV</a>'
    return href

# ---------- INTERFAZ ----------
with st.sidebar:
    st.header("⚙️ Configuración")
    tile_provider = st.selectbox("Seleccionar tipo de mapa", list(TILES.keys()), index=0)
    
    st.header("🔍 Filtros")
    archivo = st.file_uploader("📄 Subir CSV de colaboradores", type="csv")
    
    if archivo and 'df' in st.session_state:
        df = st.session_state.df
        ciudades = ["Todas"] + sorted(df["Ciudad"].unique().tolist())
        criticidades = ["Todas"] + sorted(df["Criticidad"].unique().tolist())
        subprocesos = ["Todos"] + sorted(df["Subproceso"].unique().tolist())
        
        ciudad = st.selectbox("Ciudad", ciudades, index=0)
        criticidad = st.selectbox("Criticidad", criticidades, index=0)
        subproceso = st.selectbox("Subproceso", subprocesos, index=0)
    
    with st.sidebar.expander("🔍 BUSCAR DIRECCIÓN EN COLOMBIA", expanded=True):
        direccion = st_searchbox(
            lambda searchterm: [loc.address for loc in 
                             Nominatim(user_agent="autocomplete").geocode(
                                 f"{searchterm}, Colombia", 
                                 exactly_one=False, 
                                 limit=5
                             )] if searchterm and len(searchterm) > 3 else [],
            label="🔍 Buscar dirección:",
            placeholder="Ej: Carrera 15 #32-41, Bogotá",
            key="direccion_autocomplete"
        )
        
        if st.button("📍 Buscar ubicación"):
            if direccion:
                with st.spinner("Buscando..."):
                    location = buscar_direccion_colombia(direccion)
                    if location:
                        st.session_state.emergencia_location = {
                            "coords": [location.latitude, location.longitude],
                            "address": location.address
                        }
                        st.success(f"✅ Ubicación encontrada!")
                    else:
                        st.error("Dirección no encontrada")

# Mapa principal
m = crear_mapa_base(tile_provider=tile_provider)

# Mostrar sedes fijas
for nombre, datos in SEDES_FIJAS.items():
    folium.Marker(
        location=datos["coordenadas"],
        popup=f"<b>{nombre}</b><br>{datos['direccion']}",
        icon=folium.Icon(color=datos["color"], icon=datos["icono"], prefix='fa')
    ).add_to(m)

# Procesar archivo subido
if archivo:
    df = load_data(archivo)
    
    if df is not None:
        st.session_state.df = df
        df_filtrado = aplicar_filtros(df, ciudad, criticidad, subproceso)
        
        marker_cluster = MarkerCluster(
            name="Colaboradores",
            max_cluster_radius=50,
            disable_clustering_at_zoom=14
        ).add_to(m)
        
        for _, row in df_filtrado.iterrows():
            folium.Marker(
                location=[row["Latitud"], row["Longitud"]],
                popup=f"<b>{row['Nombre']}</b><br>Sede: {row['Sede asignada']}<br>Subproceso: {row['Subproceso']}<br>Criticidad: {row['Criticidad']}",
                icon=folium.Icon(icon='user', prefix='fa', color='lightblue')
            ).add_to(marker_cluster)
        
        if hasattr(st.session_state, 'emergencia_location'):
            folium.Marker(
                location=st.session_state.emergencia_location["coords"],
                popup=f"🚨 EMERGENCIA\n{st.session_state.emergencia_location['address']}",
                icon=folium.Icon(color='red', icon='exclamation-triangle', prefix='fa')
            ).add_to(m)
            m.location = st.session_state.emergencia_location["coords"]

# Mostrar mapa
mapa_interactivo = st_folium(m, width=1200, height=600, key="mapa_principal")

# Generar reporte si se dibuja una zona
if mapa_interactivo.get("last_active_drawing"):
    zona_dibujada = mapa_interactivo["last_active_drawing"]
    if archivo and df is not None:
        reporte = generar_reporte(zona_dibujada, df_filtrado, SEDES_FIJAS)
        
        if reporte:
            st.session_state.reporte_emergencia = reporte
            st.success(f"Zona de emergencia identificada con {reporte['total_colaboradores']} colaboradores y {reporte['total_sedes']} sedes afectadas")

# Mostrar reporte si existe
if 'reporte_emergencia' in st.session_state:
    reporte = st.session_state.reporte_emergencia
    
    st.subheader("📝 Reporte de Emergencia")
    
    tipo_evento = st.selectbox(
        "Tipo de Emergencia",
        options=[
            "Evento Social (Marchas, Protestas)",
            "Evento Climático (Inundaciones, Derrumbe)",
            "Evento de Tráfico (Accidentes, Bloqueos)",
            "Falla de Infraestructura",
            "Otro"
        ],
        index=0
    )
    
    descripcion_emergencia = st.text_area(
        "✍️ Describa el evento de emergencia:",
        placeholder="Ej: Inundación en la zona norte de Bogotá afectando vías principales...",
        height=100
    )
    
    col1, col2 = st.columns(2)
    col1.metric("Total Colaboradores Afectados", reporte["total_colaboradores"])
    col2.metric("Total Sedes Afectadas", reporte["total_sedes"])
    
    st.subheader("📊 Estadísticas de la Emergencia")
    fig_emergencia = generar_graficas(reporte)
    st.pyplot(fig_emergencia)
    
    if not reporte["sedes_afectadas"].empty:
        st.subheader("🏥 Sedes Afectadas")
        st.dataframe(reporte["sedes_afectadas"][["Nombre", "Dirección"]], height=200)
    
    if not reporte["colaboradores_afectados"].empty:
        st.subheader("👥 Colaboradores Afectados")
        st.dataframe(reporte["colaboradores_afectados"][["Nombre", "Sede asignada", "Subproceso", "Criticidad"]], height=300)
        st.markdown(get_table_download_link(reporte["colaboradores_afectados"], "colaboradores_afectados.csv"), unsafe_allow_html=True)
    
    st.subheader("📤 Exportar Reporte")
    if st.button("🖨️ Generar PDF del Reporte"):
        with st.spinner("Generando PDF..."):
            try:
                pdf_bytes = crear_pdf(reporte, tipo_evento, descripcion_emergencia)
                
                if pdf_bytes:
                    st.download_button(
                        label="⬇️ Descargar PDF",
                        data=pdf_bytes,
                        file_name=f"reporte_emergencia_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"Error al generar el PDF: {str(e)}")

# Dashboard general
if archivo and df is not None:
    st.subheader("📊 Dashboard General")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Colaboradores", len(df))
    col2.metric("Sedes Únicas", df["Sede asignada"].nunique())
    col3.metric("Ciudades", df["Ciudad"].nunique())
    
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    df["Ciudad"].value_counts().head(5).plot(kind='bar', ax=ax[0], color='skyblue')
    ax[0].set_title('Top 5 Ciudades')
    df["Sede asignada"].value_counts().head(5).plot(kind='bar', ax=ax[1], color='lightgreen')
    ax[1].set_title('Top 5 Sedes')
    st.pyplot(fig)
