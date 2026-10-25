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

# --- ESTILOS CSS PERSONALIZADOS (#B0C4DE de fondo y #FFFF00 en el banner) ---
st.markdown(
    """
    <style>
    /* Fondo de pantalla general con el color #B0C4DE */
    .stApp {
        background-color: #B0C4DE !important;
        color: #1e3d59 !important;
    }

    /* Textos generales legibles y oscuros para accesibilidad */
    .stMarkdown p, .stMarkdown span, label, .stRadio label, .stCheckbox label {
        color: #1e3d59 !important;
        font-size: 18px !important;
    }

    /* GARANTIZAR ALTO CONTRASTE EN CAMPOS DE ENTRADA */
    input, textarea {
        background-color: #ffffff !important;
        color: #1e3d59 !important;
        border: 2px solid #000080 !important;
        border-radius: 8px !important;
        font-size: 18px !important;
    }

    /* ESTILO PARA EL BANNER DE NUEVA CARRERA CON COLOR #FFFF00 */
    .banner-carrera {
        background-color: #FFFF00 !important;
        border: 3px solid #000080 !important;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
        margin-bottom: 25px;
    }
    .banner-carrera h2 {
        color: #000080 !important;
        margin-bottom: 5px;
        font-weight: bold;
    }
    .banner-carrera h3 {
        color: #000080 !important;
        margin-top: 0;
        font-weight: bold;
    }
    .banner-carrera p {
        color: #1e3d59 !important;
        margin-bottom: 0;
        font-size: 18px !important;
        font-weight: 600;
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

    /* Botones principales en color #FFA500 (Naranja/Azafrán) */
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

  # Tabla para el buzón confidencial de sugerencias de estudiantes
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS sugerencias_privadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante TEXT NOT NULL,
            sugerencia TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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

  # --- PANEL DE ADMINISTRACIÓN GLOBAL (ALUMNOS Y DOCENTES) ---
  if st.session_state["usuario_logueado"] == "ADMINISTRADOR":
    st.markdown(
        "<h1 style='text-align: center; color: #000080; font-size: 38px;'>🛠️"
        " Panel de Administración</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center;'>Bienvenido, Administrador. Gestiona"
        " cuentas de estudiantes y docentes, opiniones públicas y buzón"
        " privado.</p>",
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

    st.subheader("📋 Lista General de Registros (Estudiantes y Docentes)")
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
        st.subheader("✏️ Actualizar Registro (Cualquier Rol)")
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
            f"🆔 ID Único: **{datos_actuales[0] if datos_actuales else 'Sin asignar'}** | 📌 Rol actual: **{datos_actuales[1].capitalize() if datos_actuales else ''}**"
        )

        nuevo_nombre = st.text_input(
            "Nombre completo",
            value=datos_actuales[2] if datos_actuales else "",
            key="up_nombre",
        )
        nuevo_rol = st.selectbox(
            "Rol en el sistema",
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
            "Docente encargado (para alumnos)",
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
            "Grado y sección (o a cargo)",
            options=lista_grados_admin,
            index=lista_grados_admin.index(grado_actual),
            key="up_grado",
        )

        nueva_pass_admin = st.text_input(
            "Nueva contraseña (opcional)", type="password", key="up_pass"
        )

        if st.button("Guardar Cambios de Usuario"):
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
        st.subheader("🗑️ Eliminar Registro")
        id_eliminar = st.selectbox(
            "Selecciona ID del usuario a eliminar",
            options=[r[0] for r in registros],
            key="sel_elim",
        )

        if st.button("Eliminar Registro del Sistema", type="primary"):
          cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_eliminar,))
          conexion.commit()
          st.success("🗑️ ¡Usuario eliminado de la base de datos!")
          st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🔒 Buzón de Sugerencias Privado (Estudiantes)")
    cursor.execute(
        "SELECT id, estudiante, sugerencia, fecha FROM sugerencias_privadas"
        " ORDER BY id DESC"
    )
    sugerencias_privadas = cursor.fetchall()

    if sugerencias_privadas:
      st.info(
          "📬 Estas sugerencias son confidenciales y solo pueden ser vistas"
          " por el administrador."
      )
      for sug_id, sug_est, sug_text, sug_fecha in sugerencias_privadas:
        col_sug1, col_sug2 = st.columns([4, 1])
        with col_sug1:
          st.write(
              f"• **Enviado por:** {sug_est} *(Fecha: {sug_fecha})*<br>💬"
              f" <i>\"{sug_text}\"</i>",
              unsafe_allow_html=True,
          )
        with col_sug2:
          if st.button("Eliminar Sugerencia", key=f"del_sug_{sug_id}"):
            cursor.execute(
                "DELETE FROM sugerencias_privadas WHERE id = ?", (sug_id,)
            )
            conexion.commit()
            st.success("Sugerencia privada eliminada.")
            st.rerun()
    else:
      st.info("No hay sugerencias privadas en el buzón actualmente.")

    st.markdown("---")
    st.subheader("💬 Moderación de Opiniones Públicas")
    cursor.execute("SELECT id, comentario, fecha FROM opiniones ORDER BY id DESC")
    lista_opiniones = cursor.fetchall()

    if lista_opiniones:
      for op_id, op_text, op_fecha in lista_opiniones:
        col_op1, col_op2 = st.columns([4, 1])
        with col_op1:
          st.write(f"• **\"{op_text}\"** *(Publicado: {op_fecha})*")
        with col_op2:
          if st.button("Eliminar Opinión", key=f"del_op_{op_id}"):
            cursor.execute("DELETE FROM opiniones WHERE id = ?", (op_id,))
            conexion.commit()
            st.success("Opinión pública eliminada.")
            st.rerun()
    else:
      st.info("No hay opiniones públicas registradas aún.")

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
                    <p><b>🏫 Grado y Sección a Cargo:</b> {grado_seccion if grado_seccion else 'No tiene grado a cargo (Docente por asignatura)'}</p>
                </div>
                """,
            unsafe_allow_html=True,
        )

        if grado_seccion:
          st.markdown("<br>", unsafe_allow_html=True)
          st.subheader(
              f"👥 Estudiantes de tu Grado y Sección a Cargo: {grado_seccion}"
          )

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

        # Buscador de estudiantes por grado y sección para docentes
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        st.subheader("🔍 Buscador de Estudiantes por Grado y Sección")
        st.write(
            "Selecciona cualquier grado y sección para consultar la lista de"
            " alumnos matriculados:"
        )

        grado_a_buscar = st.selectbox(
            "Elige un grado y sección para consultar",
            lista_grados_global,
            key="docente_buscador_grado",
        )

        if grado_a_buscar != "Seleccione un grado y sección...":
          cursor.execute(
              "SELECT custom_id, usuario, docente FROM usuarios WHERE rol ="
              " 'alumno' AND grado_seccion = ?",
              (grado_a_buscar,),
          )
          alumnos_busqueda = cursor.fetchall()

          if alumnos_busqueda:
            st.success(
                f"Mostrando estudiantes para: **{grado_a_buscar}**"
            )
            df_busqueda = pd.DataFrame(
                alumnos_busqueda,
                columns=[
                    "ID Único",
                    "Nombre del Estudiante",
                    "Docente Encargado",
                ],
            )
            st.dataframe(df_busqueda, use_container_width=True)
          else:
            st.info(f"No hay estudiantes registrados en **{grado_a_buscar}**.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Opinión anónima para docentes
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        st.subheader("💬 Tu opinión sobre trabajar en el INNA")
        st.write(
            "¿Qué es lo que más te gusta de formar parte del equipo docente del"
            " Instituto Nacional de Nahuizalco? Tu comentario aparecerá de"
            " forma **totalmente anónima** en la página de inicio:"
        )

        opinion_docente = st.text_area(
            "Escribe aquí tu experiencia o comentario positivo:",
            placeholder=(
                "Ejemplo: Me inspira ver el compromiso y deseo de superación"
                " de nuestros jóvenes..."
            ),
            key="doc_opinion_input",
        )

        if st.button("Enviar Opinión (Docente)", type="primary"):
          if not opinion_docente.strip():
            st.warning("⚠️ Por favor escribe un comentario antes de enviar.")
          else:
            cursor.execute(
                "INSERT INTO opiniones (comentario) VALUES (?)",
                (opinion_docente.strip(),),
            )
            conexion.commit()
            st.success(
                "🎉 ¡Muchas gracias por compartir tu experiencia! Ya ha sido"
                " publicada de forma anónima."
            )
        st.markdown("</div>", unsafe_allow_html=True)

      # --- PERFIL DE ESTUDIANTE / ALUMNO (CON BUZÓN PRIVADO Y OPINIÓN PÚBLICA) ---
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

        # 1. Cuadro de opinión pública
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        st.subheader("💬 Danos tu opinión sobre el INNA")
        st.write(
            "¿Qué es lo que más te gusta de estudiar en el Instituto Nacional"
            " de Nahuizalco? Tu comentario aparecerá de forma **totalmente"
            " anónima** en la página de inicio:"
        )

        nueva_opinion = st.text_area(
            "Escribe aquí tu comentario positivo público:",
            placeholder=(
                "Ejemplo: Me encanta la dedicación de los profesores y los"
                " nuevos talleres..."
            ),
            key="user_opinion",
        )

        if st.button("Enviar Opinión Pública", type="primary"):
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
                " forma anónima en el portal."
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # 2. Buzón de sugerencias privado (Solo visible para el administrador)
        space = st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='admin-card' style='border-left: 6px solid #FFA500;'>", unsafe_allow_html=True)
        st.subheader("🔒 Buzón Confidencial de Sugerencias")
        st.write(
            "¿Tienes alguna sugerencia, reporte o propuesta privada? Escríbela"
            " aquí. **Este mensaje es 100% seguro y confidencial**: solo podrá"
            " ser leído por el Administrador de la institución."
        )

        sugerencia_privada = st.text_area(
            "Escribe tu sugerencia privada:",
            placeholder=(
                "Ejemplo: Sugiero que se habiliten más recursos en la biblioteca"
                " o apoyo en..."
            ),
            key="user_sugerencia_privada",
        )

        if st.button("Enviar Sugerencia Confidencial", type="primary"):
          if not sugerencia_privada.strip():
            st.warning("⚠️ Por favor escribe una sugerencia antes de enviar.")
          else:
            cursor.execute(
                "INSERT INTO sugerencias_privadas (estudiante, sugerencia)"
                " VALUES (?, ?)",
                (nombre_usuario, sugerencia_privada.strip()),
            )
            conexion.commit()
            st.success(
                "🔒 ¡Tu sugerencia ha sido enviada de forma completamente"
                " confidencial al Administrador!"
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
      "<p style='text-align: center; color: #575757; font-size: 14px;'>MINEDUCYT -"
      " Código: 10754 | Portal de Acceso Estudiantil y Docente</p>",
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
        " nuestros estudiantes y docentes:"
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
                    <p style="margin-top: 5px; margin-bottom: 0; text-align: right; font-size: 14px; font-weight: bold; color: #000080;">— Comunidad INNA (Anónimo)</p>
                </div>
                """,
            unsafe_allow_html=True,
        )
    else:
      st.markdown(
          """
            <div class="opinion-card">
                <p style="margin: 0; color: #1e3d59;">“Ser parte del Instituto Nacional de Nahuizalco es una experiencia increíble de crecimiento académico y valores.”</p>
                <p style="margin-top: 5px; margin-bottom: 0; text-align: right; font-size: 14px; font-weight: bold; color: #000080;">— Comunidad INNA (Anónimo)</p>
            </div>
            """,
          unsafe_allow_html=True,
      )

  # --- SECCIÓN 2: OFERTA ACADÉMICA ---
  with menu[1]:
    st.markdown(
        """
        <div class="banner-carrera">
            <h2>⚡ ¡APERTURAMOS NUEVA CARRERA! ⚡</h2>
            <h3>Sistemas Eléctricos y Energías Renovables</h3>
            <p>¡Matrícula Abierta! Sé parte de una nueva generación de profesionales técnicos altamente capacitados.</p>
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

  # --- SECCIÓN 3: REGISTRO ---
  with menu[2]:
    st.subheader("Registro de Nueva Cuenta")

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
            not nuevo_usuario_est.strip()
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
          # Validar si ya existe el nombre completo
          cursor.execute(
              "SELECT * FROM usuarios WHERE LOWER(usuario) = LOWER(?)",
              (nuevo_usuario_est.strip(),),
          )
          if cursor.fetchone():
            st.error(
                "❌ Ya existe una cuenta registrada con este nombre y apellido."
                " No se permiten cuentas duplicadas."
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
              custom_id = generar_id_personalizado(
                  nuevo_usuario_est.strip(), cursor
              )
              pass_hash = hashlib.sha256(password_final.encode()).hexdigest()
              cursor.execute(
                  "INSERT INTO usuarios (custom_id, usuario, password, rol,"
                  " docente, grado_seccion) VALUES (?, ?, ?, 'alumno', ?, ?)",
                  (
                      custom_id,
                      nuevo_usuario_est.strip(),
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
      docente_nombre_reg = st.text_input(
          "Nombre completo del docente", key="reg_doc_nombre_libre"
      )

      tiene_grado = st.radio(
          "¿Tiene grado a su cargo?", ["No", "Sí"], horizontal=True, key="r_cargo"
      )

      grado_cargo_reg = None
      if tiene_grado == "Sí":
        grado_cargo_reg = st.selectbox(
            "Seleccione el Grado y Sección a cargo",
            lista_grados_global,
            key="reg_doc_grado",
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
        if not docente_nombre_reg.strip() or not nuevo_pass_doc or (
            tiene_grado == "Sí"
            and grado_cargo_reg == "Seleccione un grado y sección..."
        ):
          st.warning(
              "⚠️ Todos los campos obligatorios deben completarse. Por favor"
              " escribe tu nombre y contraseña."
          )
        else:
          conexion = sqlite3.connect("sistema_usuarios.db")
          cursor = conexion.cursor()
          # Validar si ya existe el nombre completo
          cursor.execute(
              "SELECT * FROM usuarios WHERE LOWER(usuario) = LOWER(?)",
              (docente_nombre_reg.strip(),),
          )
          if cursor.fetchone():
            st.error(
                "❌ Ya existe una cuenta registrada con este nombre y apellido."
                " No se permiten cuentas duplicadas."
            )
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
              custom_id = generar_id_personalizado(
                  docente_nombre_reg.strip(), cursor
              )
              pass_hash = hashlib.sha256(password_final.encode()).hexdigest()
              grado_final = (
                  grado_cargo_reg
                  if tiene_grado == "Sí"
                  and grado_cargo_reg != "Seleccione un grado y sección..."
                  else None
              )

              cursor.execute(
                  "INSERT INTO usuarios (custom_id, usuario, password, rol,"
                  " docente, grado_seccion) VALUES (?, ?, ?, 'docente', NULL,"
                  " ?)",
                  (
                      custom_id,
                      docente_nombre_reg.strip(),
                      pass_hash,
                      grado_final,
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
              (user_log.strip(), pass_hash),
          )
          resultado = cursor.fetchone()
          conexion.close()

          if resultado:
            st.balloons()
            st.session_state["usuario_logueado"] = resultado[2]
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