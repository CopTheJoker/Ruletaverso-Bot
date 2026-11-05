import os
import random
import sqlite3
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ---------------------------------------------------------
# Configuración Inicial y Variables de Entorno
# ---------------------------------------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CANAL_ANUNCIOS_ID = 1562600318242529372
CANAL_REPORTES_ID = 1565371246349123625

# 🛡️ Configuración de Roles para Comandos de Staff
ROLES_STAFF_IDS = [1344152033581596733, 1160777915504541697]
ROL_APROBADO_ID = 1158476282363908166

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="rv!", intents=intents)
bot.remove_command("help")

DB_NAME = "economia_rp.db"

# ---------------------------------------------------------
# Estadísticas Base por Raza (Tier F al S)
# ---------------------------------------------------------
ESTADISTICAS_RAZAS = {
    "Humano": {"energia": 50, "int": 10, "end": 10, "str": 10, "vel": 10, "pod": 10, "dex": 10},
    "Elfo": {"energia": 50, "int": 20, "end": 10, "str": 10, "vel": 15, "pod": 15, "dex": 20},
    "Enano": {"energia": 50, "int": 20, "end": 20, "str": 20, "vel": 10, "pod": 10, "dex": 10},
    "Mediano": {"energia": 50, "int": 20, "end": 10, "str": 15, "vel": 20, "pod": 15, "dex": 40},
    "Fantasma": {"energia": 50, "int": 50, "end": 0, "str": 0, "vel": 30, "pod": 40, "dex": 30},
    "Semi Humano": {"energia": 50, "int": 15, "end": 30, "str": 30, "vel": 30, "pod": 15, "dex": 30},
    "Eleton": {"energia": 50, "int": 30, "end": 15, "str": 15, "vel": 20, "pod": 80, "dex": 20},
    "Gigante": {"energia": 50, "int": 25, "end": 60, "str": 60, "vel": 35, "pod": 25, "dex": 35}
}

# ---------------------------------------------------------
# Base de Datos y Estructura Actualizada
# ---------------------------------------------------------
def inicializar_base_datos():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                ultimo_trabajo TEXT
            )
            """
        )
        
        cursor.execute("PRAGMA table_info(personajes)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        if not columnas:
            cursor.execute(
                """
                CREATE TABLE personajes (
                    user_id INTEGER,
                    slot_id INTEGER,
                    nombre_rp TEXT,
                    edad INTEGER,
                    raza TEXT DEFAULT 'Humano',
                    biblio_1 TEXT DEFAULT 'Sin contenido en la página 1.',
                    biblio_2 TEXT DEFAULT 'Sin contenido en la página 2.',
                    biblio_3 TEXT DEFAULT 'Sin contenido en la página 3.',
                    biblio_4 TEXT DEFAULT 'Sin contenido en la página 4.',
                    notas TEXT DEFAULT 'Sin notas registradas.',
                    poderes TEXT DEFAULT 'Sin poderes registrados.',
                    habilidades TEXT DEFAULT 'Sin habilidades registradas.',
                    rasgos TEXT DEFAULT 'Sin rasgos registrados.',
                    imagen_url TEXT DEFAULT '',
                    banner_url TEXT DEFAULT '',
                    color_hex TEXT DEFAULT '#ad9e85',
                    energia INTEGER DEFAULT 50,
                    int_stat INTEGER DEFAULT 10,
                    end_stat INTEGER DEFAULT 10,
                    str_stat INTEGER DEFAULT 10,
                    vel INTEGER DEFAULT 10,
                    pod INTEGER DEFAULT 10,
                    dex INTEGER DEFAULT 10,
                    PRIMARY KEY (user_id, slot_id)
                )
                """
            )
        else:
            migraciones = [
                ("raza", "TEXT DEFAULT 'Humano'"), 
                ("biblio_1", "TEXT DEFAULT 'Sin contenido en la página 1.'"),
                ("biblio_2", "TEXT DEFAULT 'Sin contenido en la página 2.'"),
                ("biblio_3", "TEXT DEFAULT 'Sin contenido en la página 3.'"),
                ("biblio_4", "TEXT DEFAULT 'Sin contenido en la página 4.'"),
                ("notas", "TEXT DEFAULT 'Sin notas registradas.'"), 
                ("poderes", "TEXT DEFAULT 'Sin poderes registrados.'"),
                ("habilidades", "TEXT DEFAULT 'Sin habilidades registradas.'"),
                ("rasgos", "TEXT DEFAULT 'Sin rasgos registrados.'"),
                ("imagen_url", "TEXT DEFAULT ''"),
                ("banner_url", "TEXT DEFAULT ''"),
                ("color_hex", "TEXT DEFAULT '#ad9e85'"),
                ("energia", "INTEGER DEFAULT 50"),
                ("int_stat", "INTEGER DEFAULT 10"),
                ("end_stat", "INTEGER DEFAULT 10"),
                ("str_stat", "INTEGER DEFAULT 10"),
                ("vel", "INTEGER DEFAULT 10"),
                ("pod", "INTEGER DEFAULT 10"),
                ("dex", "INTEGER DEFAULT 10")
            ]
            for col_nombre, col_tipo in migraciones:
                if col_nombre not in columnas:
                    try:
                        cursor.execute(f"ALTER TABLE personajes ADD COLUMN {col_nombre} {col_tipo}")
                    except sqlite3.OperationalError:
                        pass

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS personaje_activo (
                user_id INTEGER PRIMARY KEY,
                slot_activo INTEGER DEFAULT 1
            )
            """
        )
        conn.commit()

inicializar_base_datos()

# ---------------------------------------------------------
# Funciones Auxiliares
# ---------------------------------------------------------
def obtener_saldo(user_id: int) -> int:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM usuarios WHERE user_id = ?", (user_id,))
        resultado = cursor.fetchone()
        if resultado is None:
            cursor.execute(
                "INSERT INTO usuarios (user_id, balance) VALUES (?, ?)",
                (user_id, 100),
            )
            conn.commit()
            return 100
        return resultado[0]

def modificar_saldo(user_id: int, cantidad: int) -> int:
    saldo_actual = obtener_saldo(user_id)
    nuevo_saldo = max(0, saldo_actual + cantidad)
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET balance = ? WHERE user_id = ?",
            (nuevo_saldo, user_id),
        )
        conn.commit()
    return nuevo_saldo

def transferir_dinero(origen_id: int, destino_id: int, cantidad: int) -> bool:
    saldo_origen = obtener_saldo(origen_id)
    if saldo_origen < cantidad:
        return False
    obtener_saldo(destino_id)
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET balance = balance - ? WHERE user_id = ?",
            (cantidad, origen_id),
        )
        cursor.execute(
            "UPDATE usuarios SET balance = balance + ? WHERE user_id = ?",
            (cantidad, destino_id),
        )
        conn.commit()
    return True

def obtener_max_slots(member: discord.Member) -> int:
    ROL_TERCER_SLOT_ID = 1170825407436685374
    tiene_rol = any(role.id == ROL_TERCER_SLOT_ID for role in member.roles)
    return 3 if tiene_rol else 2

# ---------------------------------------------------------
# Formularios UI (Modals)
# ---------------------------------------------------------
class FormularioPersonajeSlot(discord.ui.Modal, title="✨ Creación de Personaje"):
    def __init__(self, slot_id: int, raza: str):
        super().__init__()
        self.slot_id = slot_id
        self.raza = raza

        self.nombre = discord.ui.TextInput(
            label="Nombre y Apellido",
            placeholder="Ej: Alonso Quijano",
            max_length=50,
            required=True,
        )
        self.edad = discord.ui.TextInput(
            label="Edad",
            placeholder="Ej: 18 (Solo números)",
            max_length=3,
            required=True,
        )
        self.color_hex = discord.ui.TextInput(
            label="Color de Ficha (HEX)",
            placeholder="Ej: ad9e85 o #ad9e85",
            default="#ad9e85",
            max_length=7,
            required=True,
        )
        self.banner = discord.ui.TextInput(
            label="Banner (Imagen Inferior URL)",
            placeholder="https://...",
            required=False,
        )

        self.add_item(self.nombre)
        self.add_item(self.edad)
        self.add_item(self.color_hex)
        self.add_item(self.banner)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not self.edad.value.strip().isdigit():
                await interaction.response.send_message(
                    "❌ La edad debe contener exclusivamente números enteros.",
                    ephemeral=True,
                )
                return

            user_id = interaction.user.id
            nombre_val = self.nombre.value.strip()
            edad_val = int(self.edad.value.strip())
            
            color_val = self.color_hex.value.strip()
            if not color_val.startswith("#"):
                color_val = f"#{color_val}"
                
            banner_val = self.banner.value.strip()
            stats = ESTADISTICAS_RAZAS.get(self.raza, ESTADISTICAS_RAZAS["Humano"])

            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO personajes (
                        user_id, slot_id, nombre_rp, edad, raza, color_hex, banner_url,
                        energia, int_stat, end_stat, str_stat, vel, pod, dex
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, slot_id) DO UPDATE SET
                        nombre_rp=excluded.nombre_rp,
                        edad=excluded.edad,
                        raza=excluded.raza,
                        color_hex=excluded.color_hex,
                        banner_url=excluded.banner_url,
                        energia=excluded.energia,
                        int_stat=excluded.int_stat,
                        end_stat=excluded.end_stat,
                        str_stat=excluded.str_stat,
                        vel=excluded.vel,
                        pod=excluded.pod,
                        dex=excluded.dex
                    """,
                    (
                        user_id, self.slot_id, nombre_val, edad_val, self.raza, color_val, banner_val,
                        stats["energia"], stats["int"], stats["end"], stats["str"], stats["vel"], stats["pod"], stats["dex"]
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO personaje_activo (user_id, slot_activo) VALUES (?, ?) 
                    ON CONFLICT(user_id) DO UPDATE SET slot_activo=excluded.slot_activo
                    """,
                    (user_id, self.slot_id),
                )
                conn.commit()

            await interaction.response.send_message(
                f"✅ Personaje **{nombre_val}** (**{self.raza}**) registrado con éxito en la **Casilla {self.slot_id}**.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Error crítico en FormularioPersonajeSlot: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"⚠️ Ocurrió un error al guardar el personaje: `{e}`", ephemeral=True
                )

class FormularioEditarFicha(discord.ui.Modal, title="🎨 Personalización de Ficha"):
    def __init__(self, slot_id: int, nombre_actual: str, edad_actual: int, color_actual: str, banner_actual: str):
        super().__init__()
        self.slot_id = slot_id

        self.nombre = discord.ui.TextInput(
            label="Nombre y Apellido",
            default=nombre_actual,
            max_length=50,
            required=True,
        )
        self.edad = discord.ui.TextInput(
            label="Edad",
            default=str(edad_actual),
            max_length=3,
            required=True,
        )
        self.color_hex = discord.ui.TextInput(
            label="Color de Ficha (HEX)",
            default=color_actual,
            max_length=7,
            required=True,
        )
        self.banner = discord.ui.TextInput(
            label="Banner (Imagen Inferior URL)",
            placeholder="https://...",
            default=banner_actual,
            required=False,
        )

        self.add_item(self.nombre)
        self.add_item(self.edad)
        self.add_item(self.color_hex)
        self.add_item(self.banner)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not self.edad.value.strip().isdigit():
                await interaction.response.send_message(
                    "❌ La edad debe contener exclusivamente números enteros.",
                    ephemeral=True,
                )
                return

            user_id = interaction.user.id
            nombre_val = self.nombre.value.strip()
            edad_val = int(self.edad.value.strip())
            
            color_val = self.color_hex.value.strip()
            if not color_val.startswith("#"):
                color_val = f"#{color_val}"
                
            banner_val = self.banner.value.strip()

            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE personajes 
                    SET nombre_rp = ?, edad = ?, color_hex = ?, banner_url = ? 
                    WHERE user_id = ? AND slot_id = ?
                    """,
                    (nombre_val, edad_val, color_val, banner_val, user_id, self.slot_id),
                )
                conn.commit()

            await interaction.response.send_message(
                "✅ ¡Ficha actualizada correctamente con la nueva personalización!",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Error en FormularioEditarFicha: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"⚠️ Error al actualizar la ficha: `{e}`", ephemeral=True
                )

class FormularioEditarBibliografia(discord.ui.Modal, title="📖 Editar Página de Bibliografía"):
    def __init__(self, pagina_num: int, contenido_actual: str, slot_id: int):
        super().__init__()
        self.pagina_num = pagina_num
        self.slot_id = slot_id

        self.contenido = discord.ui.TextInput(
            label=f"Contenido de la Página {pagina_num} (Máx. 2000 car.)",
            placeholder="Escribe la historia o capítulos...",
            style=discord.TextStyle.paragraph,
            default=contenido_actual if contenido_actual != f"Sin contenido en la página {pagina_num}." else "",
            max_length=2000,
            required=True,
        )
        self.add_item(self.contenido)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = interaction.user.id
            nuevo_texto = self.contenido.value.strip()
            columna = f"biblio_{self.pagina_num}"

            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE personajes SET {columna} = ? WHERE user_id = ? AND slot_id = ?",
                    (nuevo_texto, user_id, self.slot_id),
                )
                conn.commit()

            await interaction.response.send_message(
                f"✅ Página {self.pagina_num} de Bibliografía actualizada con éxito.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Error en FormularioEditarBibliografia: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"⚠️ Error al guardar la página: `{e}`", ephemeral=True
                )

class FormularioReporteProblema(discord.ui.Modal, title="🛟 Notificar un Problema"):
    def __init__(self):
        super().__init__()

        self.descripcion = discord.ui.TextInput(
            label="Descripción del Error (Máx. 2000 car.)",
            placeholder="Describe detalladamente qué sucedió...",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True,
        )
        self.enlace = discord.ui.TextInput(
            label="Enlace del mensaje o lugar (Opcional)",
            placeholder="https://discord.com/channels/...",
            required=False,
        )
        self.add_item(self.descripcion)
        self.add_item(self.enlace)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            canal_reportes = interaction.client.get_channel(CANAL_REPORTES_ID)
            if not canal_reportes:
                await interaction.response.send_message("❌ No se encontró el canal de reportes configurado.", ephemeral=True)
                return

            embed = discord.Embed(
                title="🚨 Nuevo Reporte de Problema",
                description=self.descripcion.value.strip(),
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
            embed.add_field(name="👤 Usuario", value=interaction.user.mention, inline=True)
            embed.add_field(name="🆔 ID de Usuario", value=str(interaction.user.id), inline=True)
            
            link_val = self.enlace.value.strip()
            if link_val:
                embed.add_field(name="🔗 Vínculo Indicado", value=link_val, inline=False)

            embed.set_footer(text="Sistema de Soporte Ruletaverso")
            await canal_reportes.send(embed=embed)

            await interaction.response.send_message("✅ ¡Tu reporte ha sido enviado exitosamente al equipo de administración!", ephemeral=True)
        except Exception as e:
            print(f"❌ Error al enviar reporte: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⚠️ Ocurrió un error al enviar el reporte: `{e}`", ephemeral=True)

# ---------------------------------------------------------
# Selección de Raza (Limpieza solicitada: Solo Tier y Nombre)
# ---------------------------------------------------------
class RazaSelect(discord.ui.Select):
    def __init__(self, slot_id: int):
        self.slot_id = slot_id
        options = [
            discord.SelectOption(label="Tier F - Humano"),
            discord.SelectOption(label="Tier D - Elfo"),
            discord.SelectOption(label="Tier D - Enano"),
            discord.SelectOption(label="Tier C - Mediano"),
            discord.SelectOption(label="Tier B - Fantasma"),
            discord.SelectOption(label="Tier B - Semi Humano"),
            discord.SelectOption(label="Tier A - Eleton"),
            discord.SelectOption(label="Tier S - Gigante"),
        ]
        super().__init__(placeholder="Elige la raza de tu personaje...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Limpiamos el texto seleccionado para extraer únicamente el nombre de la raza (ej: "Tier F - Humano" -> "Humano")
        raza_seleccionada = self.values[0].split(" - ")[1]
        await interaction.response.send_modal(FormularioPersonajeSlot(slot_id=self.slot_id, raza=raza_seleccionada))

class RazaSelectView(discord.ui.View):
    def __init__(self, slot_id: int):
        super().__init__(timeout=60)
        self.add_item(RazaSelect(slot_id))

# ---------------------------------------------------------
# Vistas y Menús Desplegables UI
# ---------------------------------------------------------
class SaldoView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    @discord.ui.button(label="🔄 Actualizar Saldo", style=discord.ButtonStyle.primary)
    async def refrescar_saldo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Solo puedes actualizar tu propio saldo.", ephemeral=True)
            return

        saldo_actual = obtener_saldo(self.user_id)
        embed = discord.Embed(
            title="💳 Estado de Cuenta",
            description=f"**Usuario:** {interaction.user.mention}\n**Dinero:** `${saldo_actual:,}`",
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

class HelpSelect(discord.ui.Select):
    def __init__(self, es_admin: bool, es_staff: bool):
        self.es_admin = es_admin
        self.es_staff = es_staff
        options = [
            discord.SelectOption(label="Economía", description="Comandos de saldo, transferencias y trabajo", emoji="💳"),
            discord.SelectOption(label="Personaje", description="Gestión y consulta de la ficha RP", emoji="🪪"),
        ]
        if self.es_staff or self.es_admin:
            options.append(discord.SelectOption(label="Staff", description="Comandos exclusivos para el equipo de moderación", emoji="🛡️"))
            
        super().__init__(placeholder="Selecciona una categoría de comandos...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Economía":
            embed = discord.Embed(
                title="💳 Categoría: Economía RP",
                description="Aquí tienes la lista detallada de comandos económicos del servidor:",
                color=discord.Color.gold(),
            )
            embed.add_field(
                name="👤 **Comandos de Jugador**",
                value=(
                    "`rv!saldo`\n"
                    "└ Consulta tu saldo con botón de actualización en tiempo real.\n\n"
                    "`rv!pagar <@usuario> <cantidad>`\n"
                    "└ Transfiere dinero a otro usuario.\n\n"
                    "`rv!trabajo`\n"
                    "└ Cobra tu paga semanal."
                ),
                inline=False,
            )
            if self.es_admin:
                embed.add_field(
                    name="🛡️ **Comandos de Administración**",
                    value=(
                        "`rv!dar_dinero <@usuario> <cantidad>`\n"
                        "└ Otorga dinero a un usuario.\n\n"
                        "`rv!quitar_dinero <@usuario> <cantidad>`\n"
                        "└ Retira o multa dinero a un usuario.\n\n"
                        "`rv!apagar`\n"
                        "└ Envía el mensaje de apagado y desconecta el bot."
                    ),
                    inline=False,
                )
            embed.set_footer(text="Usa el menú desplegable para cambiar de categoría.")
            await interaction.response.edit_message(embed=embed)
            
        elif self.values[0] == "Personaje":
            embed = discord.Embed(
                title="🪪 Categoría: Personaje RP",
                description="Comandos para la gestión y consulta de tu ficha de rol:",
                color=discord.Color.purple(),
            )
            embed.add_field(
                name="👤 **Comandos de Personaje**",
                value=(
                    "`rv!menu`\n"
                    "└ Despliega el panel de casillas para alternar, crear o eliminar personajes.\n\n"
                    "`rv!pj` (o `rv!me`)\n"
                    "└ Muestra la ficha interactiva de tu personaje activo."
                ),
                inline=False,
            )
            embed.set_footer(text="Usa el menú desplegable para cambiar de categoría.")
            await interaction.response.edit_message(embed=embed)
            
        elif self.values[0] == "Staff":
            embed = discord.Embed(
                title="🛡️ Categoría: Staff / Moderación",
                description="Comandos exclusivos para la gestión y moderación del servidor:",
                color=discord.Color.red(),
            )
            embed.add_field(
                name="🛠️ **Comandos de Staff**",
                value=(
                    "`rv!aprobar <@usuario>`\n"
                    "└ Otorga el rol correspondiente de aprobación al usuario mencionado."
                ),
                inline=False,
            )
            embed.set_footer(text="Usa el menú desplegable para cambiar de categoría.")
            await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, es_admin: bool, es_staff: bool, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(HelpSelect(es_admin=es_admin, es_staff=es_staff))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Solo quien usó `rv!ayuda` puede interactuar.", ephemeral=True)
            return False
        return True

class FichaSelect(discord.ui.Select):
    def __init__(self, owner_id: int, target_user: discord.User, slot_id: int):
        self.owner_id = owner_id
        self.target_user = target_user
        self.slot_id = slot_id

        options = [
            discord.SelectOption(label="· ⍛ Soporte · sim", description="Abrir opciones de soporte", emoji="🛟"),
            discord.SelectOption(label="· ⍛ Ficha · sim", description="Ver la ficha de tu personaje y estadísticas", emoji="📊"),
            discord.SelectOption(label="· ⍛ Bibliografía · sim", description="Gestionar tu historia (Páginas 1 a 4)", emoji="📖"),
            discord.SelectOption(label="· ⍛ Aptitudes · sim", description="Ver poderes, habilidades y rasgos", emoji="⚔️"),
            discord.SelectOption(label="· ⍛ Personalización · sim", description="Modificar nombre, edad, color y banner", emoji="🎨"),
        ]
        super().__init__(placeholder="Menú de Usuario...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nombre_rp, edad, raza, biblio_1, biblio_2, biblio_3, biblio_4, notas, poderes, habilidades, rasgos, imagen_url, banner_url, color_hex, energia, int_stat, end_stat, str_stat, vel, pod, dex FROM personajes WHERE user_id = ? AND slot_id = ?", 
                (self.target_user.id, self.slot_id)
            )
            res = cursor.fetchone()

        if not res:
            await interaction.response.send_message("❌ No se encontró información para este personaje.", ephemeral=True)
            return

        (
            nombre_rp, edad, raza, 
            b1, b2, b3, b4,
            notas, poderes, habilidades, rasgos, imagen_url, banner_url, color_hex,
            energia, int_stat, end_stat, str_stat, 
            vel, pod, dex
        ) = res

        try:
            color_int = int(color_hex.lstrip("#"), 16)
        except ValueError:
            color_int = 0xad9e85

        eleccion = self.values[0]
        embed = discord.Embed(color=color_int)
        view_a_usar = self.view

        if "Soporte" in eleccion:
            embed.title = "🛟 Opciones de Soporte"
            embed.description = "Si experimentas problemas con tu personaje, economía o comandos, puedes notificarlo directamente al equipo de administración mediante el botón de abajo."
            embed.add_field(name="Canal de Ayuda", value="Usa `rv!ayuda` para ver la lista completa de comandos.", inline=False)
            view_a_usar = SoporteView(self.owner_id, self.target_user, self.slot_id)
        elif "Ficha" in eleccion:
            embed.title = f"⌜ 🔔 Ruletaverso 🔔 ⌝"
            embed.description = (
                f"🔸 ┃ `[ Nombre ]` : **{nombre_rp}**\n"
                f"🔸 ┃ `[ Raza ]` : **{raza}**\n\n"
                f"◇────── `⚔️ Poder ⚔️` ──────◇\n"
                f"👑 `[ Energía (STA): {energia} ]`\n"
                f"🎓 `[ INT: {int_stat} ]` ୨୧ 🛡️ `[ END: {end_stat} ]`\n"
                f"🗡️ `[ STR: {str_stat} ]` ୨୧ 👢 `[ VEL: {vel} ]`\n"
                f"🔥 `[ POD: {pod} ]` ୨୧ 🪨 `[ DEX: {dex} ]`\n"
                f"╰────────────────────────╯"
            )
            if banner_url:
                embed.set_image(url=banner_url)
        elif "Bibliografía" in eleccion:
            embed.title = f"📖 Bibliografía de {nombre_rp} (Página 1 / 4)"
            embed.description = b1
            embed.set_footer(text="Usa los botones de abajo para cambiar de página o editar.")
            view_a_usar = BibliografiaView(self.owner_id, self.target_user, (b1, b2, b3, b4), self.slot_id)
        elif "Aptitudes" in eleccion:
            embed.title = f"⚔️ Aptitudes de {nombre_rp}"
            embed.description = "Panel de capacidades especiales del personaje."
            embed.add_field(name="🔮 Poderes", value=poderes, inline=False)
            embed.add_field(name="⚡ Habilidades", value=habilidades, inline=False)
            embed.add_field(name="🧬 Rasgos", value=rasgos, inline=False)
            embed.set_footer(text="Sección reservada para el desarrollo de aptitudes.")
        elif "Personalización" in eleccion:
            if interaction.user.id != self.target_user.id:
                await interaction.response.send_message("❌ Solo el dueño puede acceder a la personalización de este personaje.", ephemeral=True)
                return
            await interaction.response.send_modal(FormularioEditarFicha(self.slot_id, nombre_rp, edad, color_hex, banner_url))
            return

        if "Bibliografía" not in eleccion and "Soporte" not in eleccion and "Aptitudes" not in eleccion and banner_url and "Ficha" in eleccion:
            embed.set_image(url=banner_url)

        if "Bibliografía" not in eleccion and "Soporte" not in eleccion and "Aptitudes" not in eleccion:
            embed.set_footer(text="(ω)つ@,´9☁️𐌰𐌲˚｡✧")

        await interaction.response.edit_message(embed=embed, view=view_a_usar)

class FichaView(discord.ui.View):
    def __init__(self, owner_id: int, target_user: discord.User, slot_id: int):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.target_user = target_user
        self.slot_id = slot_id
        self.add_item(FichaSelect(owner_id, target_user, slot_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Solo quien consultó la ficha puede interactuar.", ephemeral=True)
            return False
        return True

class SoporteView(discord.ui.View):
    def __init__(self, owner_id: int, target_user: discord.User, slot_id: int):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.target_user = target_user
        self.slot_id = slot_id
        self.add_item(FichaSelect(owner_id, target_user, slot_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Solo quien consultó la ficha puede interactuar.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⚠️ Notificar un Problema", style=discord.ButtonStyle.danger, row=1)
    async def notificar_problema_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FormularioReporteProblema())

# Vista Interactiva para las 4 Páginas de Bibliografía
class BibliografiaView(discord.ui.View):
    def __init__(self, owner_id: int, target_user: discord.User, paginas: tuple, slot_id: int):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.target_user = target_user
        self.paginas = paginas  # (b1, b2, b3, b4)
        self.slot_id = slot_id
        self.pagina_actual = 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Solo quien consultó la ficha puede interactuar.", ephemeral=True)
            return False
        return True

    async def actualizar_vista(self, interaction: discord.Interaction):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT biblio_1, biblio_2, biblio_3, biblio_4, color_hex FROM personajes WHERE user_id = ? AND slot_id = ?", (self.target_user.id, self.slot_id))
            res = cursor.fetchone()
            if res:
                self.paginas = (res[0], res[1], res[2], res[3])
                color_hex = res[4]
            else:
                color_hex = "#ad9e85"

        try:
            color_int = int(color_hex.lstrip("#"), 16)
        except ValueError:
            color_int = 0xad9e85

        texto = self.paginas[self.pagina_actual - 1]
        embed = discord.Embed(
            title=f"📖 Bibliografía (Página {self.pagina_actual} / 4)",
            description=texto,
            color=color_int
        )
        embed.set_footer(text="Usa los botones para navegar entre páginas o editar la actual.")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀️ Anteriores", style=discord.ButtonStyle.secondary, row=0)
    async def btn_anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.pagina_actual = max(1, self.pagina_actual - 1)
        await self.actualizar_vista(interaction)

    @discord.ui.button(label="Siguientes ▶️", style=discord.ButtonStyle.secondary, row=0)
    async def btn_siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.pagina_actual = min(4, self.pagina_actual + 1)
        await self.actualizar_vista(interaction)

    @discord.ui.button(label="✏️ Editar Página Actual", style=discord.ButtonStyle.success, row=1)
    async def btn_editar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message("❌ Solo el dueño puede editar su bibliografía.", ephemeral=True)
            return
        contenido_actual = self.paginas[self.pagina_actual - 1]
        await interaction.response.send_modal(FormularioEditarBibliografia(pagina_num=self.pagina_actual, contenido_actual=contenido_actual, slot_id=self.slot_id))

    @discord.ui.button(label="🔙 Volver al Menú Principal", style=discord.ButtonStyle.primary, row=1)
    async def btn_volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nombre_rp, raza, color_hex, banner_url, energia, int_stat, end_stat, str_stat, vel, pod, dex FROM personajes WHERE user_id = ? AND slot_id = ?", 
                (self.target_user.id, self.slot_id)
            )
            res = cursor.fetchone()

        if not res:
            await interaction.response.send_message("❌ Error al recargar el personaje.", ephemeral=True)
            return

        nombre_rp, raza, color_hex, banner_url, energia, int_stat, end_stat, str_stat, vel, pod, dex = res

        try:
            color_int = int(color_hex.lstrip("#"), 16)
        except ValueError:
            color_int = 0xad9e85

        embed = discord.Embed(title=f"⌜ 🔔 Ruletaverso 🔔 ⌝", color=color_int)
        embed.description = (
            f"🔸 ┃ `[ Nombre ]` : **{nombre_rp}**\n"
            f"🔸 ┃ `[ Raza ]` : **{raza}**\n\n"
            f"◇────── `⚔️ Poder ⚔️` ──────◇\n"
            f"👑 `[ Energía (STA): {energia} ]`\n"
            f"🎓 `[ INT: {int_stat} ]` ୨୧ 🛡️ `[ END: {end_stat} ]`\n"
            f"🗡️ `[ STR: {str_stat} ]` ୨୧ 👢 `[ VEL: {vel} ]`\n"
            f"🔥 `[ POD: {pod} ]` ୨୧ 🪨 `[ DEX: {dex} ]`\n"
            f"╰────────────────────────╯"
        )
        if banner_url:
            embed.set_image(url=banner_url)

        embed.set_footer(text="(ω)つ@,´9☁️𐌰𐌲˚｡✧")
        await interaction.response.edit_message(embed=embed, view=FichaView(self.owner_id, self.target_user, self.slot_id))

class MenuPersonajesSelect(discord.ui.Select):
    def __init__(self, user_id: int, max_slots: int, personajes_existentes: dict):
        self.user_id = user_id
        options = []
        for slot in range(1, max_slots + 1):
            if slot in personajes_existentes:
                nombre = personajes_existentes[slot]
                options.append(discord.SelectOption(label=f"Slot {slot}: {nombre}", description="Seleccionar como activo", value=f"activar_{slot}", emoji="👤"))
                options.append(discord.SelectOption(label=f"🗑️ Slot {slot}: Eliminar ({nombre})", description="Borrar este personaje y vaciar la casilla", value=f"eliminar_{slot}", emoji="⚠️"))
            else:
                options.append(discord.SelectOption(label=f"Slot {slot}: [Casilla Vacía]", description="Crear personaje en este slot", value=f"crear_{slot}", emoji="➕"))
        super().__init__(placeholder="Selecciona, activa o borra un personaje...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        accion, slot_str = self.values[0].split("_")
        slot_id = int(slot_str)
        
        if accion == "activar":
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO personaje_activo (user_id, slot_activo) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET slot_activo=excluded.slot_activo",
                    (self.user_id, slot_id),
                )
                conn.commit()
            await interaction.response.send_message(f"✅ Has cambiado tu personaje activo al **Slot {slot_id}**.", ephemeral=True)
            
        elif accion == "eliminar":
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM personajes WHERE user_id = ? AND slot_id = ?", (self.user_id, slot_id))
                cursor.execute("SELECT slot_activo FROM personaje_activo WHERE user_id = ?", (self.user_id,))
                res = cursor.fetchone()
                if res and res[0] == slot_id:
                    cursor.execute("UPDATE personaje_activo SET slot_activo = 1 WHERE user_id = ?", (self.user_id,))
                conn.commit()
            await interaction.response.send_message(f"🗑️ El personaje del **Slot {slot_id}** ha sido eliminado y la casilla ha quedado vacía.", ephemeral=True)
            
        elif accion == "crear":
            await interaction.response.send_message("🧬 **Paso 1:** Selecciona la raza de tu personaje:", view=RazaSelectView(slot_id=slot_id), ephemeral=True)

class MenuPersonajesView(discord.ui.View):
    def __init__(self, user_id: int, max_slots: int, personajes_existentes: dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(MenuPersonajesSelect(user_id, max_slots, personajes_existentes))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Solo quien ejecutó el comando puede interactuar.", ephemeral=True)
            return False
        return True

# ---------------------------------------------------------
# Eventos y Sistema de Avisos
# ---------------------------------------------------------
@bot.event
async def on_ready():
    print(f"¡Bot listo! Conectado como {bot.user}")
    canal = bot.get_channel(CANAL_ANUNCIOS_ID)
    if canal:
        try:
            embed = discord.Embed(
                title="🟢 Bot Encendido",
                description="El sistema del servidor e interacciones está **activo y en línea**.\nUsa `rv!ayuda` para ver la lista de comandos disponibles.",
                color=discord.Color.green(),
            )
            embed.set_footer(text="Sistema Ruletaverso • Tiempo real")
            await canal.send(embed=embed)
        except Exception as e:
            print(f"No se pudo enviar el aviso de encendido: {e}")

async def enviar_aviso_apagado():
    try:
        canal = bot.get_channel(CANAL_ANUNCIOS_ID)
        if canal:
            embed = discord.Embed(
                title="🔴 Bot Apagado",
                description="El sistema del servidor e interacciones está **fuera de línea** por mantenimiento, reinicio u otros problemas.\nLos comandos no estarán disponibles temporalmente.",
                color=discord.Color.red(),
            )
            embed.set_footer(text="Sistema Ruletaverso • Tiempo real")
            await asyncio.wait_for(canal.send(embed=embed), timeout=3.0)
    except Exception as e:
        print(f"Aviso de apagado omitido o fallido: {e}")

# ---------------------------------------------------------
# Comandos de Economía y Utilidad
# ---------------------------------------------------------
@bot.command(name="ayuda", aliases=["help"])
async def ayuda(ctx):
    es_admin = ctx.author.guild_permissions.administrator
    es_staff = any(role.id in ROLES_STAFF_IDS for role in ctx.author.roles) or es_admin
    
    embed = discord.Embed(
        title="Menú Principal de Ayuda",
        description="Bienvenido al panel de ayuda del servidor.\n\n**Selecciona una categoría en el menú desplegable de abajo** para ver los comandos disponibles.",
        color=discord.Color.blue(),
    )
    embed.set_thumbnail(url="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3o2aW8yY2twb3RreW9zeDV4MnE2ZnZycDFrcXp6eThzaGF4bjVhbCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/26BROqO61E9yI3O1W/giphy.gif")
    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    view = HelpView(es_admin=es_admin, es_staff=es_staff, user_id=ctx.author.id)
    await ctx.send(embed=embed, view=view)

@bot.command(name="saldo", aliases=["bal", "dinero"])
async def saldo(ctx):
    saldo_actual = obtener_saldo(ctx.author.id)
    embed = discord.Embed(
        title="💳 Estado de Cuenta",
        description=f"**Usuario:** {ctx.author.mention}\n**Dinero:** `${saldo_actual:,}`",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed, view=SaldoView(ctx.author.id))

@bot.command(name="dar_dinero")
@commands.has_permissions(administrator=True)
async def dar_dinero(ctx, usuario: discord.User, cantidad: int):
    if cantidad <= 0:
        await ctx.send("❌ La cantidad debe ser mayor a 0.")
        return
    nuevo_saldo = modificar_saldo(usuario.id, cantidad)
    await ctx.send(f"✅ Se le han añadido `${cantidad:,}` a {usuario.mention}.")

@bot.command(name="pagar", aliases=["transferir", "pay"])
async def pagar(ctx, destino: discord.User, cantidad: int):
    if destino.id == ctx.author.id or destino.bot or cantidad <= 0:
        await ctx.send("❌ Transferencia inválida.")
        return
    exito = transferir_dinero(ctx.author.id, destino.id, cantidad)
    if exito:
        await ctx.send(f"💸 Transferencia exitosa de `${cantidad:,}` a {destino.mention}.")
    else:
        await ctx.send("❌ Fondos insuficientes.")

@bot.command(name="trabajo", aliases=["trabajar", "work"])
async def trabajo(ctx):
    user_id = ctx.author.id
    ahora = datetime.now()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ultimo_trabajo FROM usuarios WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        ultimo = res[0] if res else None

    if ultimo:
        if ahora - datetime.fromisoformat(ultimo) < timedelta(days=7):
            await ctx.send("⏳ Ya has trabajado esta semana.")
            return

    ganancia = random.randint(50, 200)
    nuevo_saldo = modificar_saldo(user_id, ganancia)
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET ultimo_trabajo = ? WHERE user_id = ?", (ahora.isoformat(), user_id))
        conn.commit()
    await ctx.send(f"💼 Ganaste `${ganancia:,}`. Saldo actual: `${nuevo_saldo:,}`")

@bot.command(name="apagar", aliases=["shutdown"])
@commands.has_permissions(administrator=True)
async def apagar(ctx):
    await ctx.send("🛑 Apagando el bot y notificando al servidor...")
    await enviar_aviso_apagado()
    await bot.close()

# ---------------------------------------------------------
# Comandos de Staff
# ---------------------------------------------------------
@bot.command(name="aprobar")
async def aprobar(ctx, miembro: discord.Member):
    es_admin = ctx.author.guild_permissions.administrator
    es_staff = any(role.id in ROLES_STAFF_IDS for role in ctx.author.roles)

    if not es_admin and not es_staff:
        await ctx.send("❌ No tienes permisos para usar este comando de staff.")
        return

    rol_a_dar = ctx.guild.get_role(ROL_APROBADO_ID)
    if not rol_a_dar:
        await ctx.send("❌ El rol de aprobación configurado no existe en este servidor.")
        return

    try:
        await miembro.add_roles(rol_a_dar)
        await ctx.send(f"✅ Se le ha otorgado exitosamente el rol **{rol_a_dar.name}** a {miembro.mention}.")
    except Exception as e:
        await ctx.send(f"⚠️ Ocurrió un error al intentar otorgar el rol: `{e}`")

# ---------------------------------------------------------
# Comandos de Personajes
# ---------------------------------------------------------
@bot.command(name="me", aliases=["pj", "personaje", "ficha"])
async def ver_personaje(ctx, usuario: discord.User = None):
    target = usuario or ctx.author
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT slot_activo FROM personaje_activo WHERE user_id = ?", (target.id,))
        res_activo = cursor.fetchone()
        slot_activo = res_activo[0] if res_activo else 1
        cursor.execute(
            "SELECT nombre_rp, edad, raza, biblio_1, biblio_2, biblio_3, biblio_4, notas, imagen_url, banner_url, color_hex, energia, int_stat, end_stat, str_stat, vel, pod, dex FROM personajes WHERE user_id = ? AND slot_id = ?", 
            (target.id, slot_activo)
        )
        resultado = cursor.fetchone()

    if not resultado:
        await ctx.send(f"❌ No hay personaje activo registrado en el Slot {slot_activo}. Usa `rv!menu` para crearlo.")
        return

    (
        nombre_rp, edad, raza, 
        b1, b2, b3, b4,
        notas, imagen_url, banner_url, color_hex,
        energia, int_stat, end_stat, str_stat, 
        vel, pod, dex
    ) = resultado
    
    try:
        color_int = int(color_hex.lstrip("#"), 16)
    except ValueError:
        color_int = 0xad9e85

    embed = discord.Embed(title=f"⌜ 🔔 Ruletaverso 🔔 ⌝", color=color_int)
    embed.description = (
        f"🔸 ┃ `[ Nombre ]` : **{nombre_rp}**\n"
        f"🔸 ┃ `[ Raza ]` : **{raza}**\n\n"
        f"◇────── `⚔️ Poder ⚔️` ──────◇\n"
        f"👑 `[ Energía (STA): {energia} ]`\n"
        f"🎓 `[ INT: {int_stat} ]` ୨୧ 🛡️ `[ END: {end_stat} ]`\n"
        f"🗡️ `[ STR: {str_stat} ]` ୨୧ 👢 `[ VEL: {vel} ]`\n"
        f"🔥 `[ POD: {pod} ]` ୨୧ 🪨 `[ DEX: {dex} ]`\n"
        f"╰────────────────────────╯"
    )
    
    if banner_url:
        embed.set_image(url=banner_url)

    embed.set_footer(text="(ω)つ@,´9☁️𐌰𐌲˚｡✧")

    await ctx.send(embed=embed, view=FichaView(ctx.author.id, target, slot_activo))

@bot.command(name="menu", aliases=["menu_pj", "personajes"])
async def menu_personajes(ctx):
    max_slots = obtener_max_slots(ctx.author)
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT slot_id, nombre_rp FROM personajes WHERE user_id = ?", (ctx.author.id,))
        filas = cursor.fetchall()
        personajes_existentes = {slot: nombre for slot, nombre in filas}
        cursor.execute("SELECT slot_activo FROM personaje_activo WHERE user_id = ?", (ctx.author.id,))
        res_activo = cursor.fetchone()
        slot_activo = res_activo[0] if res_activo else 1

    embed = discord.Embed(
        title=f"𐰁 🏺 ϭ - ᵞ Menú de Usuario ˚ ⁀",
        description=f"Casillas permitidas: **{max_slots}**\n**Personaje Activo Actual:** Slot {slot_activo}\n\n👇 *Selecciona una opción abajo para cambiar, crear o borrar personajes:*",
        color=discord.Color.from_rgb(173, 158, 133),
    )
    await ctx.send(embed=embed, view=MenuPersonajesView(ctx.author.id, max_slots, personajes_existentes))

# ---------------------------------------------------------
# Ejecución Principal del Bot
# ---------------------------------------------------------
if __name__ == "__main__":
    bot.run(TOKEN)