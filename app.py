import base64
import hashlib
import os
import random
import sqlite3
import string
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Instituto Nacional de Nahuizalco",
    page_icon="🎓",
    layout="centered",
)

# --- CARGAR LA FOTO AÉREA ORIGINAL (SIN TRANSPARENCIA, DE BORDE A BORDE) ---
banner_html = ""
if os.path.exists("48997.jpg"):
  with open("48997.jpg", "rb") as f:
    banner_b64 = base64.b64encode(f.read()).decode()
  banner_html = f"""
    <div style="width: 100vw; position: relative; left: 50%; right: 50%; margin-left: -50vw; margin-right: -50vw; margin-top: -60px; margin-bottom: 25px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <img src="data:image/jpeg;base64,{banner_b64}" style="width: 100%; height: auto; display: block;" />
    </div>
    """

# --- ESTILOS CSS PERSONALIZADOS (MODO OSCURO COMPATIBLE) ---
st.markdown(
    """
    <style>
    /* Fondo azul pastel sutil y elegante para toda la aplicación */
    .stApp {
        background-color: #eaf0f6 !important;
        color: #1e3d59 !important;
    }

    /* Forzar que los textos generales sean oscuros */
    html, body, [class*="st-"], p, span, label {
        color: #1e3d59 !important;
        font-size: 18px !important;
    }

    /* Excepción: Botones principales mantienen texto blanco */
    div.stButton > button, div.stButton > button * {
        color: white !important;
    }
    
    /* Contenedores tipo tarjeta */
    .admin-card {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        border-left: 6px solid #000080;
        margin-bottom: 20px;
        color: #1e3d59 !important;
    }

    /* Tarjetas especiales para las opiniones anónimas */
    .opinion-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #FFA500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        font-style: italic;
        color: #1e3d59 !important;
    }

    /* Botones principales en color #FFA500 (Naranja) */
    div.stButton > button {
        background-color: #FFA500 !important;
        font-size: 18px !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: none !important;
    }
    div.stButton > button:hover {
        background-color: #e59400 !important;
    }

    /* Efecto hover y pestaña activa en color #000080 (Azul marino) */
    .stTabs [data-baseweb="tab"]:hover {
        color: #000080 !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #000080 !important;
    }
    
    div[data-baseweb="tab-highlight"] {
        background-color: #000080 !important;
    }
    .stTabs [data-baseweb="tab-list"] div {
        background-color: #000080 !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# --- 1. BASE DE DATOS Y MIGRACIÓN DE TABLAS ---
def inicializar_base_datos():
  conexion = sqlite3.connect("sistema_usuarios.db")
  cursor = conexion.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            custom_id TEXT UNIQUE,
            usuario TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT DEFAULT 'alumno',
            docente TEXT,
            grado_seccion TEXT
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS opiniones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comentario TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  cursor.execute("PRAGMA table_info(usuarios)")
  columnas = [columna[1] for columna in cursor.fetchall()]

  if "custom_id" not in columnas:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN custom_id TEXT")
  if "rol" not in columnas:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT DEFAULT 'alumno'")
  if "docente" not in columnas:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN docente TEXT")
  if "grado_seccion" not in columnas:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN grado_seccion TEXT")

  conexion.commit()
  conexion.close()


inicializar_base_datos()


# --- 2. LÓGICA DE CONTRASEÑAS E ID PERSONALIZADO ---
def evaluar_contrasena(password):
  longitud = len(password)
  tiene_mayuscula = any(c.isupper() for c in password)
  tiene_minuscula = any(c.islower() for c in password)
  tiene_numero = any(c.isdigit() for c in password)
  tiene_especial = any(c in string.punctuation for c in password)

  if (
      longitud >= 12
      and tiene_mayuscula
      and tiene_minuscula
      and tiene_numero
      and tiene_especial
  ):
    return "muy confiable"
  elif longitud >= 8 and ((tiene_mayuscula and tiene_minuscula) or tiene_numero):
    return "poco confiable"
  else:
    return "no es confiable"


def generar_contrasena_segura(longitud=12):
  caracteres = string.ascii_letters + string.digits + string.punctuation
  while True:
    password = "".join(random.choice(caracteres) for _ in range(longitud))
    if evaluar_contrasena(password) == "muy confiable":
      return password


def generar_id_personalizado(nombre_completo, cursor):
  partes = nombre_completo.strip().split()
  if len(partes) >= 2:
    iniciales = (partes[0][0] + partes[-1][0]).upper()
  elif len(partes) == 1 and len(partes[0]) >= 2:
    iniciales = partes[0][:2].upper()
  else:
    iniciales = "IN"

  while True:
    digitos = "".join(random.choices(string.digits, k=4))
    custom_id = f"{iniciales}{digitos}"
    cursor.execute("SELECT id FROM usuarios WHERE custom_id = ?", (custom_id,))
    if not cursor.fetchone():
      return custom_id


# Listas oficiales
lista_docentes_global = [
    "Seleccione un docente...",
    "Victoria Salazar",
    "Rene Galdámez",
    "Rene Soriano",
    "Denis Alexis",
    "Sandra Farfán",
    "Erick Anaya",
    "Adela Flores",
    "Daysi Batres",
    "Celia Márquez",
    "Rene Chaves",
    "Carlos Roberto",
]

lista_grados_global = [
    "Seleccione un grado y sección...",
    "1° General A",
    "1° General B",
    "1° Administrativo contable",
    "1° Servicios Turísticos",
    "2° General A",
    "2° General B",
    "2° General C",
    "2° Administrativo Contable",
    "2° Servicios Turísticos",
    "3° Administrativo Contable",
    "3° Servicios Turísticos",
]


# Estado de sesión
if "usuario_logueado" not in st.session_state:
  st.session_state["usuario_logueado"] = None

if "indice_carrusel" not in st.session_state:
  st.session_state["indice_carrusel"] = 0


# --- 4. PÁGINA TRAS INICIAR SESIÓN (ADMIN, DOCENTE O ESTUDIANTE) ---
if st.session_state["usuario_logueado"]:
  st.markdown(banner_html, unsafe_allow_html=True)

  # --- PANEL DE ADMINISTRACIÓN ---
  if st.session_state["usuario_logueado"] == "ADMINISTRADOR":
    st.markdown(
        "<h1 style='text-align: center; color: #000080; font-size: 38px;'>🛠️"
        " Panel de Administración</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center;'>Bienvenido, Administrador. Gestiona"
        " usuarios, estudiantes, docentes y opiniones.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    busqueda = st.text_input(
        "🔍 Buscar por nombre, rol, docente o grado y sección",
        key="admin_search",
    )

    conexion = sqlite3.connect("sistema_usuarios.db")
    cursor = conexion.cursor()

    if busqueda:
      cursor.execute(
          """SELECT id, custom_id, rol, usuario, docente, grado_seccion FROM usuarios 
                     WHERE usuario LIKE ? OR rol LIKE ? OR docente LIKE ? OR grado_seccion LIKE ?""",
          (
              f"%{busqueda}%",
              f"%{busqueda}%",
              f"%{busqueda}%",
              f"%{busqueda}%",
          ),
      )
    else:
      cursor.execute(
          "SELECT id, custom_id, rol, usuario, docente, grado_seccion FROM"
          " usuarios"
      )

    registros = cursor.fetchall()

    st.subheader("📋 Lista de Registros en el Sistema")
    if registros:
      df = pd.DataFrame(
          registros,
          columns=[
              "ID Interno",
              "ID Único",
              "Rol",
              "Nombre Completo",
              "Docente Encargado",
              "Grado y Sección",
          ],
      )
      st.dataframe(df, use_container_width=True)

      st.markdown("---")
      col_adm1, col_adm2 = st.columns(2)

      with col_adm1:
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        st.subheader("✏️ Actualizar Registro")
        id_actualizar = st.selectbox(
            "Selecciona ID del usuario a modificar",
            options=[r[0] for r in registros],
            key="sel_act",
        )

        cursor.execute(
            "SELECT custom_id, rol, usuario, docente, grado_seccion FROM"
            " usuarios WHERE id = ?",
            (id_actualizar,),
        )
        datos_actuales = cursor.fetchone()

        st.info(
            f"🆔 ID Único: **{datos_actuales[0] if datos_actuales else 'Sin asignar'}** | 📌 Rol: **{datos_actuales[1].capitalize() if datos_actuales else ''}**"
        )

        nuevo_nombre = st.text_input(
            "Nombre completo",
            value=datos_actuales[2] if datos_actuales else "",
            key="up_nombre",
        )
        nuevo_rol = st.selectbox(
            "Rol",
            options=["alumno", "docente"],
            index=0 if datos_actuales[1] == "alumno" else 1,
            key="up_rol",
        )

        lista_docentes_admin = lista_docentes_global[1:]
        docente_actual = (
            datos_actuales[3]
            if datos_actuales and datos_actuales[3] in lista_docentes_admin
            else lista_docentes_admin[0]
        )
        nuevo_docente = st.selectbox(
            "Docente encargado",
            options=lista_docentes_admin,
            index=lista_docentes_admin.index(docente_actual),
            key="up_docente",
        )

        lista_grados_admin = lista_grados_global[1:]
        grado_actual = (
            datos_actuales[4]
            if datos_actuales and datos_actuales[4] in lista_grados_admin
            else lista_grados_admin[0]
        )
        nuevo_grado = st.selectbox(
            "Grado y sección",
            options=lista_grados_admin,
            index=lista_grados_admin.index(grado_actual),
            key="up_grado",
        )

        nueva_pass_admin = st.text_input(
            "Nueva contraseña (opcional)", type="password", key="up_pass"
        )

        if st.button("Guardar Cambios"):
          if not nuevo_nombre:
            st.warning("⚠️ El nombre completo no puede estar vacío.")
          else:
            if nueva_pass_admin:
              pass_h = hashlib.sha256(nueva_pass_admin.encode()).hexdigest()
              cursor.execute(
                  "UPDATE usuarios SET usuario = ?, rol = ?, docente = ?,"
                  " grado_seccion = ?, password = ? WHERE id = ?",
                  (
                      nuevo_nombre,
                      nuevo_rol,
                      nuevo_docente,
                      nuevo_grado,
                      pass_h,
                      id_actualizar,
                  ),
              )
            else:
              cursor.execute(
                  "UPDATE usuarios SET usuario = ?, rol = ?, docente = ?,"
                  " grado_seccion = ? WHERE id = ?",
                  (
                      nuevo_nombre,
                      nuevo_rol,
                      nuevo_docente,
                      nuevo_grado,
                      id_actualizar,
                  ),
              )
            conexion.commit()
            st.success("✅ ¡Registro actualizado exitosamente!")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

      with col_adm2:
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        st.subheader("🗑️ Eliminar Usuario")
        id_eliminar = st.selectbox(
            "Selecciona ID del usuario a eliminar",
            options=[r[0] for r in registros],
            key="sel_elim",
        )

        if st.button("Eliminar Registro", type="primary"):
          cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_eliminar,))
          conexion.commit()
          st.success("🗑️ ¡Usuario eliminado de la base de datos!")
          st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("💬 Moderación de Opiniones Anónimas")
    cursor.execute("SELECT id, comentario, fecha FROM opiniones ORDER BY id DESC")
    lista_opiniones = cursor.fetchall()

    if lista_opiniones:
      for op_id, op_text, op_fecha in lista_opiniones:
        col_op1, col_op2 = st.columns([4, 1])
        with col_op1:
          st.write(f"• **\"{op_text}\"** *(Publicado: {op_fecha})*")
        with col_op2:
          if st.button("Eliminar", key=f"del_op_{op_id}"):
            cursor.execute("DELETE FROM opiniones WHERE id = ?", (op_id,))
            conexion.commit()
            st.success("Opinión eliminada.")
            st.rerun()
    else:
      st.info("No hay opiniones registradas aún.")

    conexion.close()

    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
      if st.button("Cerrar Sesión de Administrador"):
        st.session_state["usuario_logueado"] = None
        st.rerun()

  else:
    # --- VERIFICAR ROL DEL USUARIO LOGUEADO (DOCENTE VS ALUMNO) ---
    conexion = sqlite3.connect("sistema_usuarios.db")
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT custom_id, usuario, rol, docente, grado_seccion FROM usuarios"
        " WHERE usuario = ?",
        (st.session_state["usuario_logueado"],),
    )
    perfil = cursor.fetchone()

    # Si es un usuario antiguo sin custom_id, generarlo
    if perfil and not perfil[0]:
      nuevo_id = generar_id_personalizado(perfil[1], cursor)
      cursor.execute(
          "UPDATE usuarios SET custom_id = ? WHERE usuario = ?",
          (nuevo_id, perfil[1]),
      )
      conexion.commit()
      cursor.execute(
          "SELECT custom_id, usuario, rol, docente, grado_seccion FROM"
          " usuarios WHERE usuario = ?",
          (st.session_state["usuario_logueado"],),
      )
      perfil = cursor.fetchone()

    if perfil:
      custom_id, nombre_usuario, rol_usuario, docente_asignado, grado_seccion = (
          perfil
      )

      col1, col2, col3 = st.columns([1, 2, 1])
      with col2:
        if os.path.exists("48874.jpg"):
          st.image("48874.jpg", width=280)

      st.markdown(
          "<h1 style='text-align: center; color: #1e3d59; font-size: 42px;'>¡Bienvenido"
          " al Portal!</h1>",
          unsafe_allow_html=True,
      )
      st.markdown(
          f"<h2 style='text-align: center; color: #000080;'>Portal de "
          f"<b>{rol_usuario.capitalize()}</b>: {nombre_usuario}</h2>",
          unsafe_allow_html=True,
      )

      # --- PERFIL DE DOCENTE ---
      if rol_usuario == "docente":
        st.markdown(
            f"""
                <div class='admin-card' style='max-width: 700px; margin: 0 auto;'>
                    <h3 style='color: #000080; text-align: center; margin-top: 0;'>👨‍🏫 Perfil Profesional del Docente</h3>
                    <hr style='margin: 10px 0;'>
                    <p><b>🆔 ID Personalizado:</b> {custom_id}</p>
                    <p><b>🎓 Nombre Completo:</b> {nombre_usuario}</p>
                    <p><b>🏫 Grado y Sección a Cargo:</b> {grado_seccion if grado_seccion else 'No asignado'}</p>
                </div>
                """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader(
            f"👥 Estudiantes del Grado y Sección: {grado_seccion}"
        )

        # Consultar estudiantes de este grado/sección
        cursor.execute(
            "SELECT custom_id, usuario, docente FROM usuarios WHERE rol ="
            " 'alumno' AND grado_seccion = ?",
            (grado_seccion,),
        )
        estudiantes_grado = cursor.fetchall()

        if estudiantes_grado:
          df_est = pd.DataFrame(
              estudiantes_grado,
              columns=[
                  "ID Único",
                  "Nombre del Estudiante",
                  "Docente Encargado",
              ],
          )
          st.dataframe(df_est, use_container_width=True)
        else:
          st.info(
              "ℹ️ Aún no hay estudiantes registrados en este grado y sección."
          )

      # --- PERFIL DE ESTUDIANTE / ALUMNO ---
      else:
        st.markdown(
            f"""
                <div class='admin-card' style='max-width: 600px; margin: 0 auto;'>
                    <h3 style='color: #000080; text-align: center; margin-top: 0;'>👤 Tu Perfil Personal</h3>
                    <hr style='margin: 10px 0;'>
                    <p><b>🆔 ID Personalizado:</b> {custom_id}</p>
                    <p><b>🎓 Nombre Completo:</b> {nombre_usuario}</p>
                    <p><b>👨‍🏫 Docente Encargado:</b> {docente_asignado if docente_asignado else 'No asignado'}</p>
                    <p><b>🏫 Grado y Sección:</b> {grado_seccion if grado_seccion else 'No asignado'}</p>
                </div>
                """,
            unsafe_allow_html=True,
        )

        # Cuadro de opinión anónima para estudiantes
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        st.subheader("💬 Danos tu opinión sobre el INNA")
        st.write(
            "¿Qué es lo que más te gusta de estudiar en el Instituto Nacional"
            " de Nahuizalco? Tu comentario aparecerá de forma **totalmente"
            " anónima** en la página de inicio:"
        )

        nueva_opinion = st.text_area(
            "Escribe aquí tu comentario positivo:",
            placeholder=(
                "Ejemplo: Me encanta la dedicación de los profesores y los"
                " nuevos talleres..."
            ),
            key="user_opinion",
        )

        if st.button("Enviar Opinión Anónima", type="primary"):
          if not nueva_opinion.strip():
            st.warning("⚠️ Por favor escribe un comentario antes de enviar.")
          else:
            cursor.execute(
                "INSERT INTO opiniones (comentario) VALUES (?)",
                (nueva_opinion.strip(),),
            )
            conexion.commit()
            st.success(
                "🎉 ¡Muchas gracias por tu opinión! Ya ha sido publicada de"
                " forma anónima."
            )
        st.markdown("</div>", unsafe_allow_html=True)

    conexion.close()

    st.markdown("<br>", unsafe_allow_html=True)
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
      if st.button("Cerrar Sesión"):
        st.session_state["usuario_logueado"] = None
        st.rerun()

else:
  # --- ENCABEZADO CON BANNER AÉREO ORIGINAL ---
  st.markdown(banner_html, unsafe_allow_html=True)

  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    if os.path.exists("48874.jpg"):
      st.image("48874.jpg", width=280)
    else:
      st.warning("⚠️ Logo '48874.jpg' no encontrado en la carpeta.")

  st.markdown(
      "<h1 style='text-align: center; color: #1e3d59; font-size: 52px; font-weight:"
      " bold;'>Instituto Nacional de Nahuizalco</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #575757;'>MINEDUCYT - Código:"
      " 10754 | Portal de Acceso Estudiantil y Docente</p>",
      unsafe_allow_html=True,
  )
  st.markdown("---")

  # --- NAVEGACIÓN POR PESTAÑAS ---
  menu = st.tabs([
      "🏠 Inicio / Bienvenida",
      "📚 Oferta Académica",
      "📝 Registro de Usuario",
      "🔑 Iniciar Sesión",
  ])

  # --- SECCIÓN 1: INICIO CON MURO DE OPINIONES ---
  with menu[0]:
    st.subheader("¡Bienvenidos al Portal Oficial!")
    st.write("""
        Este espacio está diseñado para la comunidad educativa del **Instituto Nacional de Nahuizalco**. 
        Aquí podrás gestionar tu cuenta institucional de manera segura mediante nuestro sistema inteligente de validación de credenciales.
    """)

    st.info(
        "💡 **Indicación:** ¡Conoce nuestra **nueva carrera** y los bachilleratos"
        " en la pestaña **Oferta Académica**! Si eres nuevo, regístrate en"
        " **Registro de Usuario**."
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🌟 Lo que nuestra comunidad dice del INNA")
    st.write(
        "Lee las experiencias y opiniones reales compartidas anónimamente por"
        " nuestros estudiantes:"
    )

    conexion = sqlite3.connect("sistema_usuarios.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT comentario FROM opiniones ORDER BY id DESC LIMIT 5")
    opiniones_muro = cursor.fetchall()
    conexion.close()

    if opiniones_muro:
      for op in opiniones_muro:
        st.markdown(
            f"""
                <div class="opinion-card">
                    <p style="margin: 0; color: #1e3d59;">“{op[0]}”</p>
                    <p style="margin-top: 5px; margin-bottom: 0; text-align: right; font-size: 14px; font-weight: bold; color: #000080;">— Estudiante del INNA (Anónimo)</p>
                </div>
                """,
            unsafe_allow_html=True,
        )
    else:
      st.markdown(
          """
            <div class="opinion-card">
                <p style="margin: 0; color: #1e3d59;">“Ser parte del Instituto Nacional de Nahuizalco es una experiencia increíble de crecimiento académico y valores.”</p>
                <p style="margin-top: 5px; margin-bottom: 0; text-align: right; font-size: 14px; font-weight: bold; color: #000080;">— Estudiante del INNA (Anónimo)</p>
            </div>
            """,
          unsafe_allow_html=True,
      )

  # --- SECCIÓN 2: OFERTA ACADÉMICA ---
  with menu[1]:
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1e3d59 0%, #000080 100%); padding: 25px; border-radius: 15px; color: white; text-align: center; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15); margin-bottom: 25px;">
            <h2 style="color: #FFA500; margin-bottom: 5px;">⚡ ¡APERTURAMOS NUEVA CARRERA! ⚡</h2>
            <h3 style="color: white; margin-top: 0;">Sistemas Eléctricos y Energías Renovables</h3>
            <p style="margin-bottom: 0; font-size: 16px;">¡Matrícula Abierta! Sé parte de una nueva generación de profesionales técnicos altamente capacitados.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if os.path.exists("electricos.jpg"):
      col_e1, col_e2, col_e3 = st.columns([1, 4, 1])
      with col_e2:
        st.image(
            "electricos.jpg",
            use_container_width=True,
            caption="Nueva Carrera - Sistemas Eléctricos y Energías Renovables",
        )
    else:
      st.warning(
          "⚠️ No se encontró la imagen 'electricos.jpg' en la carpeta del"
          " proyecto."
      )

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    st.subheader("📖 Folleto Institucional y Oferta Académica General")
    st.write(
        "Navega a través de las páginas de nuestro folleto oficial para"
        " conocer todos nuestros bachilleratos, misión, visión y contactos:"
    )

    imagenes_carrusel = [
        ("1.jpg", "Portada Informativa"),
        ("2.jpg", "Misión Institucional"),
        ("3.jpg", "Visión Institucional"),
        ("4.jpg", "Nuestra Oferta Académica General"),
        ("5.jpg", "Sobre Nosotros"),
        ("6.jpg", "Contáctanos"),
    ]

    total_imgs = len(imagenes_carrusel)

    col_prev, col_info, col_next = st.columns([1, 2, 1])

    with col_prev:
      if st.button("⬅️ Anterior"):
        st.session_state["indice_carrusel"] = (
            st.session_state["indice_carrusel"] - 1
        ) % total_imgs
        st.rerun()

    with col_info:
      idx = st.session_state["indice_carrusel"]
      st.markdown(
          f"<p style='text-align: center; font-weight: bold; color: #000080;'"
          f">Página {idx + 1} de {total_imgs}: {imagenes_carrusel[idx][1]}</p>",
          unsafe_allow_html=True,
      )

    with col_next:
      if st.button("Siguiente ➡️"):
        st.session_state["indice_carrusel"] = (
            st.session_state["indice_carrusel"] + 1
        ) % total_imgs
        st.rerun()

    img_actual, titulo_actual = imagenes_carrusel[idx]
    if os.path.exists(img_actual):
      col_img1, col_img2, col_img3 = st.columns([1, 4, 1])
      with col_img2:
        st.image(img_actual, use_container_width=True, caption=titulo_actual)
    else:
      st.warning(
          f"⚠️ No se encontró la imagen '{img_actual}' en la carpeta del"
          " proyecto."
      )

    st.markdown("---")
    st.write("🔍 **Acceso rápido a una página del folleto:**")
    cols_btn = st.columns(total_imgs)
    for i in range(total_imgs):
      with cols_btn[i]:
        if st.button(f"Pág. {i+1}", key=f"btn_p{i}"):
          st.session_state["indice_carrusel"] = i
          st.rerun()

  # --- SECCIÓN 3: REGISTRO CON OPCIÓN DE ALUMNO O DOCENTE ---
  with menu[2]:
    st.subheader("Registro de Nueva Cuenta")

    # Selector de Tipo de Usuario
    tipo_registro = st.radio(
        "¿Qué tipo de usuario eres?",
        ["Estudiante / Alumno", "Docente"],
        horizontal=True,
        key="tipo_reg",
    )

    st.markdown("---")

    # --- FORMULARIO DE ALUMNO ---
    if tipo_registro == "Estudiante / Alumno":
      nuevo_usuario_est = st.text_input(
          "Nombre completo del estudiante", key="reg_est_user"
      )
      docente_reg = st.selectbox(
          "Nombre de su Docente encargado",
          lista_docentes_global,
          key="reg_est_docente",
      )
      grado_reg = st.selectbox(
          "Grado y sección al que pertenece",
          lista_grados_global,
          key="reg_est_grado",
      )
      nuevo_pass_est = st.text_input(
          "Contraseña deseada", type="password", key="reg_est_pass"
      )

      aceptar_sugerencia_est = False
      sugerencia_est = ""

      if nuevo_pass_est:
        nivel = evaluar_contrasena(nuevo_pass_est)
        if nivel == "muy confiable":
          st.success("🟢 Nivel de contraseña: **Muy confiable**")
        elif nivel == "poco confiable":
          st.warning("🟡 Nivel de contraseña: **Poco confiable**")
        else:
          st.error("🔴 Nivel de contraseña: **No es confiable**")

        if nivel in ["no es confiable", "poco confiable"]:
          if (
              "sug_est" not in st.session_state
              or st.session_state.get("last_pass_est") != nuevo_pass_est
          ):
            st.session_state["sug_est"] = generar_contrasena_segura()
            st.session_state["last_pass_est"] = nuevo_pass_est

          sugerencia_est = st.session_state["sug_est"]
          st.info(f"💡 Sugerencia del sistema de seguridad: `{sugerencia_est}`")
          aceptar_sugerencia_est = st.checkbox(
              "Aceptar la contraseña sugerida por el sistema", key="chk_sug_est"
          )

      if st.button("Completar Registro de Estudiante", type="primary"):
        if (
            not nuevo_usuario_est
            or docente_reg == "Seleccione un docente..."
            or grado_reg == "Seleccione un grado y sección..."
            or not nuevo_pass_est
        ):
          st.warning(
              "⚠️ Todos los campos son obligatorios. Por favor completa tu"
              " nombre, docente, grado y contraseña."
          )
        else:
          conexion = sqlite3.connect("sistema_usuarios.db")
          cursor = conexion.cursor()
          cursor.execute(
              "SELECT * FROM usuarios WHERE usuario = ?", (nuevo_usuario_est,)
          )
          if cursor.fetchone():
            st.error(
                "❌ El estudiante ya se encuentra registrado en el sistema."
            )
          else:
            nivel = evaluar_contrasena(nuevo_pass_est)
            password_final = ""
            if nivel in ["no es confiable", "poco confiable"]:
              if aceptar_sugerencia_est:
                password_final = sugerencia_est
              else:
                st.error(
                    "❌ Tu contraseña es débil y no aceptaste la sugerencia."
                )
            else:
              password_final = nuevo_pass_est

            if password_final:
              custom_id = generar_id_personalizado(nuevo_usuario_est, cursor)
              pass_hash = hashlib.sha256(password_final.encode()).hexdigest()
              cursor.execute(
                  "INSERT INTO usuarios (custom_id, usuario, password, rol,"
                  " docente, grado_seccion) VALUES (?, ?, ?, 'alumno', ?, ?)",
                  (
                      custom_id,
                      nuevo_usuario_est,
                      pass_hash,
                      docente_reg,
                      grado_reg,
                  ),
              )
              conexion.commit()
              st.success(
                  f"🎉 ¡Registro exitoso! Tu ID único asignado es:"
                  f" **{custom_id}**. Ya puedes iniciar sesión."
              )
          conexion.close()

    # --- FORMULARIO DE DOCENTE ---
    else:
      docente_nombre_reg = st.selectbox(
          "Nombre completo del docente",
          lista_docentes_global,
          key="reg_doc_nombre",
      )
      grado_cargo_reg = st.selectbox(
          "Grado y Sección a cargo", lista_grados_global, key="reg_doc_grado"
      )
      nuevo_pass_doc = st.text_input(
          "Contraseña deseada", type="password", key="reg_doc_pass"
      )

      aceptar_sugerencia_doc = False
      sugerencia_doc = ""

      if nuevo_pass_doc:
        nivel = evaluar_contrasena(nuevo_pass_doc)
        if nivel == "muy confiable":
          st.success("🟢 Nivel de contraseña: **Muy confiable**")
        elif nivel == "poco confiable":
          st.warning("🟡 Nivel de contraseña: **Poco confiable**")
        else:
          st.error("🔴 Nivel de contraseña: **No es confiable**")

        if nivel in ["no es confiable", "poco confiable"]:
          if (
              "sug_doc" not in st.session_state
              or st.session_state.get("last_pass_doc") != nuevo_pass_doc
          ):
            st.session_state["sug_doc"] = generar_contrasena_segura()
            st.session_state["last_pass_doc"] = nuevo_pass_doc

          sugerencia_doc = st.session_state["sug_doc"]
          st.info(f"💡 Sugerencia del sistema de seguridad: `{sugerencia_doc}`")
          aceptar_sugerencia_doc = st.checkbox(
              "Aceptar la contraseña sugerida por el sistema", key="chk_sug_doc"
          )

      if st.button("Completar Registro de Docente", type="primary"):
        if (
            docente_nombre_reg == "Seleccione un docente..."
            or grado_cargo_reg == "Seleccione un grado y sección..."
            or not nuevo_pass_doc
        ):
          st.warning(
              "⚠️ Todos los campos son obligatorios. Por favor selecciona tu"
              " nombre, grado a cargo y contraseña."
          )
        else:
          conexion = sqlite3.connect("sistema_usuarios.db")
          cursor = conexion.cursor()
          cursor.execute(
              "SELECT * FROM usuarios WHERE usuario = ?", (docente_nombre_reg,)
          )
          if cursor.fetchone():
            st.error("❌ Este docente ya se encuentra registrado en el sistema.")
          else:
            nivel = evaluar_contrasena(nuevo_pass_doc)
            password_final = ""
            if nivel in ["no es confiable", "poco confiable"]:
              if aceptar_sugerencia_doc:
                password_final = sugerencia_doc
              else:
                st.error(
                    "❌ Tu contraseña es débil y no aceptaste la sugerencia."
                )
            else:
              password_final = nuevo_pass_doc

            if password_final:
              custom_id = generar_id_personalizado(docente_nombre_reg, cursor)
              pass_hash = hashlib.sha256(password_final.encode()).hexdigest()
              cursor.execute(
                  "INSERT INTO usuarios (custom_id, usuario, password, rol,"
                  " docente, grado_seccion) VALUES (?, ?, ?, 'docente', NULL,"
                  " ?)",
                  (
                      custom_id,
                      docente_nombre_reg,
                      pass_hash,
                      grado_cargo_reg,
                  ),
              )
              conexion.commit()
              st.success(
                  f"🎉 ¡Registro de docente exitoso! Tu ID único asignado es:"
                  f" **{custom_id}**. Ya puedes iniciar sesión."
              )
          conexion.close()

  # --- SECCIÓN 4: INICIO DE SESIÓN ---
  with menu[3]:
    st.subheader("Acceso al Sistema")
    user_log = st.text_input("Usuario / Nombre completo", key="login_user")
    pass_log = st.text_input("Contraseña", type="password", key="login_pass")

    if st.button("Ingresar al Portal", type="primary"):
      if not user_log or not pass_log:
        st.warning("⚠️ Ingresa tus credenciales de acceso.")
      else:
        if user_log == "ADMINISTRADOR" and pass_log == "INNA2026":
          st.balloons()
          st.session_state["usuario_logueado"] = "ADMINISTRADOR"
          st.rerun()
        else:
          pass_hash = hashlib.sha256(pass_log.encode()).hexdigest()
          conexion = sqlite3.connect("sistema_usuarios.db")
          cursor = conexion.cursor()
          cursor.execute(
              "SELECT * FROM usuarios WHERE usuario = ? AND password = ?",
              (user_log, pass_hash),
          )
          resultado = cursor.fetchone()
          conexion.close()

          if resultado:
            st.balloons()
            st.session_state["usuario_logueado"] = user_log
            st.rerun()
          else:
            st.error("❌ Usuario o contraseña incorrectos. Verifica tus datos.")

# --- PIE DE PÁGINA (FOOTER) ---
st.markdown("---")
if os.path.exists("48996.jpg"):
  st.image(
      "48996.jpg",
      use_container_width=True,
      caption="Comunidad Educativa - Instituto Nacional de Nahuizalco",
  )
else:
  st.warning("⚠️ Imagen de pie de página '48996.jpg' no encontrada.")

st.markdown(
    "<p style='text-align: center; color: #575757; font-size: 14px;'>© 2026"
    " Instituto Nacional de Nahuizalco - Todos los derechos reservados.</p>",
    unsafe_allow_html=True,
)