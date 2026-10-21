"""
Motor V8 350 (small block Chevrolet) del Camaro SS 1968, hecho por script, pieza por pieza y con detalle.

Se corre con el Blender portátil, sin abrir la ventana:
    blender -b -P blender/motor.py
(ver blender/LEEME.md). Genera modelos/motor.glb (sin comprimir: después va Draco, ver README.md).

Cómo está armado:
1. Las medidas salen del motor de verdad: V a 90°, cilindros cada 4,4″ (11,2 cm), 9,025″ (22,9 cm)
   del cigüeñal a la cara de arriba del bloque. El cigüeñal se ubicó para que el filtro de aire
   quede a ~1,5 cm del capot cerrado, como en el auto.
2. Lo que es del 67-68 y no de otros años: bomba de agua corta con el alternador del lado del
   conductor, bomba de nafta mecánica del lado del acompañante (adelante, abajo), varilla del aceite
   del lado del conductor, Quadrajet con las bocas chicas adelante. Fuentes: INVESTIGACION-motor-detalle.md.
3. Cada pieza es un objeto con el mismo nombre que el «id» de su ficha (datos/fichas.json). Las que
   van de a varias (tapas de cilindros, tapas de válvulas, múltiples de escape, bujías) son un objeto
   vacío con el id y adentro cada una («tapa-valvulas-izq», «bujia-1»…), como dice «piezas3d».
4. Cada pieza tiene el origen en su centro: separarla o mostrarla en el paso a paso es mover el objeto.
   Los tornillos van adentro de la malla de su pieza (se separan con ella y no suman objetos).
5. El detalle: cada forma se bisela al crearla (cantos redondeados de verdad), después se suaviza con
   normales ponderadas, y los materiales fundidos llevan una textura de relieve que hace este mismo
   script (ruido de fundición, se repite sin costuras). Nada se baja de internet.
6. Todo cuelga de un objeto vacío «motor» (sin mover nada), con tres puntos de enganche adentro
   para la vista Motor y el interior: enganche_soporte, enganche_ciguenal y enganche_gancho.
7. Al final controla que nada toque el capot cerrado ni las paredes del vano (lo avisa en la consola).

Ejes en Blender (los mismos de carroceria.py): X = ancho (+X = lado izquierdo, el del conductor),
Y = largo (el frente mira a -Y), Z = arriba. Metros. El origen es el mismo de la carrocería.
Lados del motor: «izq» = lado del conductor (+X), «der» = lado del acompañante (-X).

Para armar encima (motor_interno.py): importalo como dice blender/LEEME.md y usá construir(),
las medidas de acá arriba, a_lo_largo(), cilindros_y(), Malla y materiales().
"""

import importlib.util
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

AQUI = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------------------------------
# Medidas del motor (metros)
# ----------------------------------------------------------------------------------------------
CIG_Z = 0.35                        # altura del cigüeñal
BLOQUE_Y = (-1.52, -0.90)           # cara de adelante y de atrás del bloque
DECK = 0.229                        # 9,025″: del cigüeñal a la cara de arriba del bloque
ENTRE_CILINDROS = 0.1118            # 4,4″
CILINDRO_1_Y = -1.42                # el cilindro 1 va adelante, del lado izquierdo
CORRIDA_BANCADA = 0.020             # la fila derecha va un poco más atrás que la izquierda
DIAMETRO = 0.1016                   # 4″ de diámetro de cilindro (para motor_interno.py)
CARRERA = 0.0884                    # 3,48″ de carrera
CABEZA_ALTO = 0.11                  # alto de la tapa de cilindros (a lo largo de la V)
CABEZA_ANCHO = 0.21
POLEAS_Y = -1.70                    # plano de las poleas y la correa
VENTILADOR_Y = -1.79
CARB_Y = -1.20                      # centro del carburador y del filtro de aire
BASE_CARB_Z = 0.68                  # la cara de arriba del múltiple, donde apoya el carburador
FILTRO_RADIO = 0.20                 # 16″ de diámetro
RADIADOR_Y = -1.97
BOMBA_Z = CIG_Z + 0.14              # eje de la bomba de agua y del ventilador
ALTERNADOR = Vector((0.22, -1.60, 0.60))
DISTRIBUIDOR = Vector((0.02, -0.93, 0.0))
BATERIA = Vector((0.50, -1.80, 0.535))   # centro de la base (= enganche_bateria de la carrocería)
TORPEDO_Y = -0.66                   # la pared del vano (hasta ahí llegan las mangueras de la calefacción)
TEXTURA_METROS = 0.16               # cada cuánto se repite la textura de fundición

S45 = math.sqrt(0.5)
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def a_lo_largo(lado, d, t=0.0):
    """Punto (x, z) de una fila de cilindros: 'd' a lo largo de la V desde el cigüeñal y 't' de
    costado (positivo = hacia afuera del motor). lado = +1 izquierda, -1 derecha."""
    x = lado * (d * S45 + t * S45)
    z = CIG_Z + d * S45 - t * S45
    return x, z


def en_banco(lado, d, t, y):
    """Lo mismo que a_lo_largo pero devuelve el punto 3D."""
    x, z = a_lo_largo(lado, d, t)
    return Vector((x, y, z))


def eje_banco(lado):
    """Dirección del cilindro (hacia la tapa de válvulas)."""
    return Vector((lado * S45, 0, S45))


def afuera_banco(lado):
    """Dirección de costado, hacia afuera del motor (hacia el múltiple de escape)."""
    return Vector((lado * S45, 0, -S45))


def cilindros_y(lado):
    corrida = 0.0 if lado > 0 else CORRIDA_BANCADA
    return [CILINDRO_1_Y + corrida + k * ENTRE_CILINDROS for k in range(4)]


def numero_cilindro(lado, k):
    """Numeración Chevrolet: izquierda 1-3-5-7, derecha 2-4-6-8 (de adelante para atrás)."""
    return 2 * k + (1 if lado > 0 else 2)


def rot_y(grados):
    return Matrix.Rotation(math.radians(grados), 4, "Y")


def base_de(u, v, w):
    """Matriz cuyos ejes locales x, y, z apuntan a u, v, w."""
    m = Matrix.Identity(4)
    for col, eje in enumerate((u, v, w)):
        e = Vector(eje).normalized()
        for fila in range(3):
            m[fila][col] = e[fila]
    return m


def rot_hacia(direccion):
    """Matriz que lleva el eje Z a 'direccion'."""
    return Z.rotation_difference(Vector(direccion).normalized()).to_matrix().to_4x4()


# ----------------------------------------------------------------------------------------------
# Texturas hechas acá mismo (ruido de fundición que se repite sin costura)
# ----------------------------------------------------------------------------------------------
def ruido_repetible(tam, semilla, bandas):
    """Ruido que se repite sin costura: ruido blanco filtrado en frecuencia. 'bandas' es una lista
    de (ciclos por imagen, peso): pocos ciclos = manchas grandes, muchos = grano fino."""
    rng = np.random.default_rng(semilla)
    f = np.hypot(np.fft.fftfreq(tam)[:, None], np.fft.fftfreq(tam)[None, :]) * tam
    alto = np.zeros((tam, tam))
    for ciclos, peso in bandas:
        blanco = np.fft.fft2(rng.standard_normal((tam, tam)))
        capa = np.real(np.fft.ifft2(blanco * np.exp(-(f / ciclos) ** 2)))
        alto += peso * capa / (np.abs(capa).max() or 1.0)
    return alto


def imagen_relieve(nombre, tam=256, semilla=7):
    """Mapa de relieve (normal map) de fundición en arena: grano fino, ondas suaves y algún poro."""
    alto = ruido_repetible(tam, semilla, [(24, 0.3), (90, 0.7)])
    poros = ruido_repetible(tam, semilla + 1, [(70, 1.0)])
    alto -= np.clip(poros - 0.55, 0, None) * 2.2          # poritos hundidos, como el hierro de verdad
    dx = (np.roll(alto, -1, 1) - np.roll(alto, 1, 1)) * 0.5
    dy = (np.roll(alto, -1, 0) - np.roll(alto, 1, 0)) * 0.5
    fuerza = 2.2
    n = np.dstack((-dx * fuerza, -dy * fuerza, np.ones_like(alto)))
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    rgba = np.dstack((n * 0.5 + 0.5, np.ones_like(alto))).astype(np.float32)
    img = bpy.data.images.new(nombre, tam, tam, alpha=False)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(rgba.ravel())
    img.file_format = "PNG"
    img.pack()
    return img


# ----------------------------------------------------------------------------------------------
# Materiales
# ----------------------------------------------------------------------------------------------
def srgb_a_lineal(hexa):
    c = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1.0,)


def material(nombre, hexa, rugosidad, metal=0.0, barniz=0.0, relieve=None, fuerza=0.0):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    nodos = m.node_tree.nodes
    p = nodos.get("Principled BSDF")
    color = srgb_a_lineal(hexa)
    p.inputs["Base Color"].default_value = color
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rugosidad
    p.inputs["Coat Weight"].default_value = barniz
    if barniz:
        p.inputs["Coat Roughness"].default_value = 0.18
    if relieve is not None and fuerza:
        tex = nodos.new("ShaderNodeTexImage")
        tex.image = relieve
        tex.interpolation = "Linear"
        mapa = nodos.new("ShaderNodeNormalMap")
        mapa.inputs["Strength"].default_value = fuerza      # en el .glb queda como normalTexture.scale
        m.node_tree.links.new(tex.outputs["Color"], mapa.inputs["Color"])
        m.node_tree.links.new(mapa.outputs["Normal"], p.inputs["Normal"])
    m.diffuse_color = color
    return m


DETALLE_REDONDOS = 0.75        # 1 = todos los lados pedidos; menos = más liviano (las piezas chicas no cambian)


def menos_lados(lados):
    """Las piezas redondas grandes pierden algunos lados (no se nota y pesa menos); las chicas no."""
    return lados if lados <= 12 else max(12, round(lados * DETALLE_REDONDOS))


MATERIALES_CON_TEXTURA ={"naranja", "hierro", "aluminio", "zinc"}


def materiales():
    relieve = bpy.data.images.get("fundicion_relieve") or imagen_relieve("fundicion_relieve")
    return {
        # Hierro fundido pintado de naranja Chevrolet: se nota el grano abajo de la pintura
        "naranja": material("naranja_chevrolet", "#e2581c", 0.42, barniz=0.35, relieve=relieve, fuerza=0.3),
        "cromo": material("cromo", "#f2f2f4", 0.05, metal=1.0),
        "hierro": material("hierro_fundido", "#4a4542", 0.78, metal=0.55, relieve=relieve, fuerza=0.8),
        "aluminio": material("aluminio_fundido", "#c4c4c0", 0.42, metal=1.0, relieve=relieve, fuerza=0.35),
        "acero": material("acero", "#8a8c90", 0.35, metal=1.0),
        "zinc": material("zinc_carburador", "#c9bc93", 0.4, metal=1.0, relieve=relieve, fuerza=0.2),
        "negro": material("negro_semimate", "#1c1d20", 0.5),
        "goma": material("goma", "#0e0e0f", 0.85),
        "papel": material("papel_filtro", "#ddd3bb", 0.95),
        "blanco": material("porcelana", "#f1efe8", 0.25),
    }


# ----------------------------------------------------------------------------------------------
# Herramientas para armar mallas: cada forma se agrega a una malla con su material y su bisel
# ----------------------------------------------------------------------------------------------
class Malla:
    def __init__(self, mats):
        self.bm = bmesh.new()
        self.mats = list(mats)              # lista de nombres de material, en orden

    # -- lo interno ---------------------------------------------------------------------------
    def _terminar(self, verts, mat, bisel, segmentos=2, angulo=30):
        """Pinta la forma recién creada y le redondea los cantos (solo los que doblan más de
        'angulo' grados: las caras curvas quedan como están)."""
        i = self.mats.index(mat)
        caras = {f for v in verts for f in v.link_faces}
        for f in caras:
            f.material_index = i
        if bisel <= 0:
            return
        for f in caras:
            f.normal_update()
        aristas = [e for e in {e for v in verts for e in v.link_edges}
                   if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(angulo)]
        if aristas:
            bmesh.ops.bevel(self.bm, geom=aristas, offset=bisel, offset_type="OFFSET", segments=segmentos,
                            profile=0.5, affect="EDGES", clamp_overlap=True)

    # -- formas -------------------------------------------------------------------------------
    def caja(self, centro, medida, mat, rot=None, bisel=0.0, segmentos=2):
        m = Matrix.Translation(Vector(centro)) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal((*medida, 1))
        res = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self._terminar(res["verts"], mat, bisel, segmentos)

    def cilindro(self, a, b, r1, mat, r2=None, lados=24, bisel=0.0, segmentos=2):
        """Cilindro (o cono si r2 cambia) que va del punto a al punto b."""
        a, b = Vector(a), Vector(b)
        m = Matrix.Translation((a + b) / 2) @ rot_hacia(b - a)
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=menos_lados(lados),
                                    radius1=r1, radius2=r1 if r2 is None else r2, depth=(b - a).length, matrix=m)
        self._terminar(res["verts"], mat, bisel, segmentos)

    def esfera(self, centro, radio, mat, escala=(1, 1, 1), segmentos=16):
        m = Matrix.Translation(Vector(centro)) @ Matrix.Diagonal((*escala, 1))
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=segmentos, v_segments=segmentos // 2, radius=radio, matrix=m)
        self._terminar(res["verts"], mat, 0)

    def torno(self, perfil, base, eje, mat, lados=32, bisel=0.0, angulo=30):
        """Pieza de revolución (lo que saldría de un torno): 'perfil' es una lista de (radio, altura)
        a lo largo del 'eje', desde 'base'. Si el primer o el último radio no es 0, se tapa."""
        base, eje = Vector(base), Vector(eje).normalized()
        m = Matrix.Translation(base) @ rot_hacia(eje)
        lados = menos_lados(lados)
        anillos = []
        for r, h in perfil:
            if r <= 1e-6:
                anillos.append([self.bm.verts.new(m @ Vector((0, 0, h)))])
                continue
            anillos.append([self.bm.verts.new(m @ Vector((r * math.cos(2 * math.pi * k / lados),
                                                          r * math.sin(2 * math.pi * k / lados), h)))
                            for k in range(lados)])
        for a, b in zip(anillos, anillos[1:]):
            for k in range(lados):
                k2 = (k + 1) % lados
                if len(a) == 1:
                    self.bm.faces.new((a[0], b[k], b[k2]))
                elif len(b) == 1:
                    self.bm.faces.new((a[k], b[0], a[k2]))
                else:
                    self.bm.faces.new((a[k], b[k], b[k2], a[k2]))
        if len(anillos[0]) > 1:
            self.bm.faces.new(list(reversed(anillos[0])))
        if len(anillos[-1]) > 1:
            self.bm.faces.new(anillos[-1])
        todos = [v for anillo in anillos for v in anillo]
        self._terminar(todos, mat, bisel, angulo=angulo)

    def placa(self, perfil, matriz, espesor, mat, bisel=0.0):
        """Un perfil cerrado (u, v) estirado 'espesor' a lo largo de su w local. 'matriz' lleva el
        sistema (u, v, w) al mundo."""
        abajo = [self.bm.verts.new(matriz @ Vector((u, v, 0))) for u, v in perfil]
        arriba = [self.bm.verts.new(matriz @ Vector((u, v, espesor))) for u, v in perfil]
        n = len(perfil)
        for k in range(n):
            self.bm.faces.new((abajo[k], abajo[(k + 1) % n], arriba[(k + 1) % n], arriba[k]))
        self.bm.faces.new(list(reversed(abajo)))
        self.bm.faces.new(arriba)
        self._terminar(abajo + arriba, mat, bisel)

    def prisma(self, perfil, y0, y1, mat, bisel=0.0):
        """Un perfil cerrado (x, z) estirado a lo largo de Y, de y0 a y1."""
        matriz = Matrix(((1, 0, 0, 0), (0, 0, 1, y0), (0, 1, 0, 0), (0, 0, 0, 1)))
        # (u, v, w) → (x, y0 + w, z): el perfil se da en sentido horario visto desde adelante
        self.placa(perfil, matriz, y1 - y0, mat, bisel)

    def tubo(self, puntos, radio, mat, lados=8, ciclico=False, resolucion=6):
        """Un caño, una manguera o un cable que pasa suave por los puntos (Bézier con espesor)."""
        curva = bpy.data.curves.new("tmp_tubo", "CURVE")
        curva.dimensions = "3D"
        curva.resolution_u = resolucion
        curva.bevel_depth = radio
        curva.bevel_resolution = max(0, (lados - 4) // 2)
        curva.use_fill_caps = not ciclico
        s = curva.splines.new("BEZIER")
        s.bezier_points.add(len(puntos) - 1)
        s.use_cyclic_u = ciclico
        for bp, p in zip(s.bezier_points, puntos):
            bp.co = Vector(p)
            bp.handle_left_type = bp.handle_right_type = "AUTO"
        obj = bpy.data.objects.new("tmp_tubo", curva)
        bpy.context.scene.collection.objects.link(obj)
        deps = bpy.context.evaluated_depsgraph_get()
        malla = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
        antes = set(self.bm.verts)
        self.bm.from_mesh(malla)
        nuevos = [v for v in self.bm.verts if v not in antes]
        self._terminar(nuevos, mat, 0)
        bpy.data.objects.remove(obj)
        bpy.data.curves.remove(curva)
        bpy.data.meshes.remove(malla)

    def anillo(self, centro, eje, radio, grueso, mat, lados=24):
        """Un aro (toroide): abrazaderas, tapas, la manija de la varilla."""
        centro, eje = Vector(centro), Vector(eje).normalized()
        m = Matrix.Translation(centro) @ rot_hacia(eje)
        puntos = [m @ Vector((radio * math.cos(2 * math.pi * k / 8), radio * math.sin(2 * math.pi * k / 8), 0))
                  for k in range(8)]
        self.tubo(puntos, grueso, mat, lados=6, ciclico=True, resolucion=3)

    # -- detalles que se repiten ------------------------------------------------------------------
    def tornillo(self, punto, normal, mat="acero", r=0.0065, alto=0.006, arandela=True):
        """Cabeza hexagonal (con arandela) apoyada en 'punto', mirando hacia 'normal'."""
        p, n = Vector(punto), Vector(normal).normalized()
        if arandela:
            self.cilindro(p, p + n * 0.0015, r * 1.45, mat, lados=10)
        self.cilindro(p + n * (0.0015 if arandela else 0), p + n * (alto + 0.0015), r, mat, lados=6, bisel=r * 0.12, segmentos=1)

    def tornillos(self, puntos, normal, **kw):
        for p in puntos:
            self.tornillo(p, normal, **kw)

    def abrazadera(self, centro, eje, radio, mat="acero"):
        """Abrazadera de manguera: un fleje alrededor con su tornillito."""
        centro, eje = Vector(centro), Vector(eje).normalized()
        self.cilindro(centro - eje * 0.006, centro + eje * 0.006, radio + 0.0022, mat, lados=20)
        lado = eje.orthogonal().normalized()
        self.caja(centro + lado * (radio + 0.006), (0.010, 0.010, 0.010), mat, rot_hacia(lado))

    # -- final ----------------------------------------------------------------------------------
    def objeto(self, nombre, mats_bpy, angulo=32):
        bm = self.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.normal_update()
        for capa in list(bm.loops.layers.uv.values()):     # los tubos traen la suya: sobra
            bm.loops.layers.uv.remove(capa)
        # Coordenadas de textura por proyección de caja: cada cara toma el plano que más mira
        # (solo si algún material de la pieza tiene textura: si no, es peso de más)
        con_textura = any(m in MATERIALES_CON_TEXTURA for m in self.mats)
        uv = bm.loops.layers.uv.new("UVMap") if con_textura else None
        for f in (bm.faces if con_textura else []):
            n = f.normal
            eje = max(range(3), key=lambda i: abs(n[i]))
            a, b = [(1, 2), (0, 2), (0, 1)][eje]
            for loop in f.loops:
                co = loop.vert.co
                loop[uv].uv = (co[a] / TEXTURA_METROS, co[b] / TEXTURA_METROS)
        malla = bpy.data.meshes.new(nombre)
        bm.to_mesh(malla)
        bm.free()
        obj = bpy.data.objects.new(nombre, malla)
        bpy.context.scene.collection.objects.link(obj)
        for m in self.mats:
            obj.data.materials.append(mats_bpy[m])
        suavizar(obj, angulo)
        # Normales ponderadas: las caras grandes mandan, así los cantos biselados se ven firmes
        wn = obj.modifiers.new("normales", "WEIGHTED_NORMAL")
        wn.mode = "FACE_AREA"
        wn.weight = 50
        wn.keep_sharp = True
        aplicar_modificadores(obj)
        centrar_origen(obj)
        return obj


def aplicar_modificadores(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    malla = bpy.data.meshes.new_from_object(obj.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
    viejo = obj.data
    obj.modifiers.clear()
    obj.data = malla
    bpy.data.meshes.remove(viejo)
    malla.name = obj.name


def suavizar(obj, angulo=32):
    with bpy.context.temp_override(selected_editable_objects=[obj], active_object=obj, object=obj):
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angulo))


def centrar_origen(obj):
    """Lleva el origen al centro de la pieza sin moverla (para separar y para el paso a paso)."""
    vs = [v.co for v in obj.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    c = (lo + hi) / 2
    obj.data.transform(Matrix.Translation(-c))
    obj.location = obj.location + c


def vacio(nombre, hijos):
    """Objeto vacío en el medio de sus hijos, que los agrupa (piezas que van de a varias)."""
    centro = sum((h.location for h in hijos), Vector()) / len(hijos)
    e = bpy.data.objects.new(nombre, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.05
    e.location = centro
    bpy.context.scene.collection.objects.link(e)
    for h in hijos:
        h.parent = e
        h.location = h.location - centro
    return e


def redondeado(ancho, alto, radio, pasos=4, cx=0.0, cy=0.0):
    """Perfil de un rectángulo con las esquinas redondeadas (sentido antihorario)."""
    puntos = []
    esquinas = [(ancho / 2 - radio, alto / 2 - radio, 0), (-ancho / 2 + radio, alto / 2 - radio, 90),
                (-ancho / 2 + radio, -alto / 2 + radio, 180), (ancho / 2 - radio, -alto / 2 + radio, 270)]
    for x, y, a0 in esquinas:
        for k in range(pasos + 1):
            a = math.radians(a0 + 90 * k / pasos)
            puntos.append((cx + x + radio * math.cos(a), cy + y + radio * math.sin(a)))
    return puntos


# Sistemas de dibujo para placas: (u, v, w) → mundo
def plano_frente(y):
    """Placa en la cara de adelante del motor: u = X, v = Z, w hacia adelante (-Y)."""
    return Matrix.Translation((0, y, 0)) @ Matrix.Rotation(math.radians(90), 4, "X")


# ----------------------------------------------------------------------------------------------
# Las piezas
# ----------------------------------------------------------------------------------------------
def bloque(mats):
    """La V de hierro: perfil del bloque estirado a lo largo, con nervios, tapones, la brida de
    atrás y los asientos de lo que se le atornilla."""
    m = Malla(["naranja", "acero"])
    ext = a_lo_largo(1, DECK, 0.115)
    inn = a_lo_largo(1, DECK, -0.085)
    media = [(0.0, -0.045), (0.215, -0.045), (0.228, -0.02), (0.232, 0.03), (ext[0] - 0.004, ext[1] - CIG_Z - 0.02),
             (ext[0], ext[1] - CIG_Z), (inn[0], inn[1] - CIG_Z), (0.035, 0.175), (0.0, 0.168)]
    perfil = [(x, CIG_Z + z) for x, z in media]
    perfil += [(-x, z) for x, z in reversed(perfil[1:-1])]
    m.prisma(list(reversed(perfil)), BLOQUE_Y[0], BLOQUE_Y[1], "naranja", bisel=0.006)
    for lado in (1, -1):
        # Riel de abajo (donde apoya el cárter), apenas saliente
        m.caja((lado * 0.222, (BLOQUE_Y[0] + BLOQUE_Y[1]) / 2, CIG_Z - 0.037), (0.022, 0.60, 0.016), "naranja", bisel=0.003)
        # Las camisas de agua marcan bultos entre cilindro y cilindro
        for y in cilindros_y(lado):
            m.cilindro((lado * 0.226, y, CIG_Z + 0.005), (lado * 0.226, y, CIG_Z + 0.07), 0.042, "naranja", lados=20, bisel=0.004)
        # Tapones de agua (los «freeze plugs»): tres por lado, de chapa
        for y in (cilindros_y(lado)[0] + 0.056, cilindros_y(lado)[1] + 0.056, cilindros_y(lado)[2] + 0.056):
            c = Vector((lado * 0.246, y, CIG_Z + 0.04))
            m.cilindro(c - X * lado * 0.004, c + X * lado * 0.003, 0.019, "acero", lados=20, bisel=0.0015)
        # Nervios de refuerzo abajo, en diagonal
        for y in (-1.40, -1.18, -0.98):
            m.caja((lado * 0.236, y, CIG_Z - 0.012), (0.012, 0.014, 0.05), "naranja", bisel=0.003)
    # Brida de atrás, donde se atornilla la caja (y el soporte de taller en la vista Motor)
    brida = [(math.cos(a) * 0.245, CIG_Z + 0.05 + math.sin(a) * 0.17) for a in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
    m.placa(brida, plano_frente(BLOQUE_Y[1] + 0.018), 0.018, "naranja", bisel=0.004)
    for a in np.linspace(0.3, 2 * math.pi - 0.3, 8):
        p = Vector((math.cos(a) * 0.215, BLOQUE_Y[1] + 0.018, CIG_Z + 0.05 + math.sin(a) * 0.145))
        m.tornillo(p, Y, r=0.008)
    # Asientos: bomba de nafta (der, adelante), filtro de aceite (izq, atrás), sensor de aceite (atrás arriba)
    m.caja((-0.236, -1.42, CIG_Z - 0.005), (0.03, 0.08, 0.07), "naranja", bisel=0.005)
    m.cilindro((0.225, -1.00, CIG_Z - 0.02), (0.255, -1.00, CIG_Z - 0.045), 0.05, "naranja", lados=24, bisel=0.004)
    m.cilindro((0.06, BLOQUE_Y[1] - 0.04, CIG_Z + 0.17), (0.06, BLOQUE_Y[1] - 0.04, CIG_Z + 0.20), 0.011, "acero", lados=6, bisel=0.001)
    # Cara de adelante: la nariz del cigüeñal asoma debajo de la tapa de distribución
    m.caja((0, BLOQUE_Y[0] - 0.004, CIG_Z + 0.06), (0.30, 0.008, 0.26), "naranja", bisel=0.003)
    return m.objeto("bloque", mats)


def tapa_distribucion(mats):
    """Tapa de chapa estampada de la cadena de distribución, con su reten y la regla del encendido."""
    m = Malla(["naranja", "acero", "cromo"])
    y0 = BLOQUE_Y[0] - 0.008
    perfil = [(0.085, CIG_Z), (0.088, CIG_Z + 0.06), (0.075, CIG_Z + 0.115), (-0.075, CIG_Z + 0.115),
              (-0.088, CIG_Z + 0.06), (-0.085, CIG_Z)] + [
        (math.cos(math.radians(a)) * 0.085, CIG_Z + math.sin(math.radians(a)) * 0.085) for a in range(190, 351, 20)]
    m.placa(perfil, plano_frente(y0), 0.026, "naranja", bisel=0.008)
    # La pestaña de alrededor, con sus tornillitos
    m.placa([(u * 1.08, CIG_Z + (v - CIG_Z) * 1.08) for u, v in perfil], plano_frente(y0), 0.004, "naranja", bisel=0.001)
    for a in (200, 250, 290, 340):
        p = Vector((math.cos(math.radians(a)) * 0.088, y0 - 0.004, CIG_Z + math.sin(math.radians(a)) * 0.088))
        m.tornillo(p, -Y, r=0.005)
    for x in (0.08, -0.08):
        m.tornillo((x, y0 - 0.004, CIG_Z + 0.08), -Y, r=0.005)
    # Reten del cigüeñal
    m.torno([(0.05, 0), (0.052, 0.01), (0.04, 0.02), (0.0, 0.02)], (0, y0 - 0.02, CIG_Z), -Y, "naranja", lados=32, bisel=0.003)
    # Regla del punto de encendido (del lado del acompañante, arriba del balanceador)
    regla = Matrix.Translation((-0.055, y0 - 0.03, CIG_Z + 0.075)) @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Rotation(math.radians(-35), 4, "Z")
    m.placa(redondeado(0.05, 0.016, 0.004), regla, 0.002, "cromo")
    for k in range(6):
        marca = regla @ Vector((-0.02 + k * 0.008, 0.009, 0.002))
        m.caja(marca, (0.0015, 0.006, 0.0015), "cromo", regla.to_3x3().to_4x4())
    return m.objeto("tapa-distribucion", mats)


def tapas_cilindros(mats):
    hijos = []
    for lado, sufijo in ((1, "izq"), (-1, "der")):
        m = Malla(["naranja", "acero"])
        ys = cilindros_y(lado)
        y0, y1 = ys[0] - 0.10, ys[-1] + 0.10
        rot = rot_y(45 * lado)
        centro = en_banco(lado, DECK + CABEZA_ALTO / 2, 0, (y0 + y1) / 2)
        m.caja(centro, (CABEZA_ANCHO, y1 - y0, CABEZA_ALTO), "naranja", rot, bisel=0.007, segmentos=3)
        # Riel de la tapa de válvulas (arriba), un poco más angosto
        riel = en_banco(lado, DECK + CABEZA_ALTO + 0.004, 0.01, (y0 + y1) / 2)
        m.caja(riel, (0.17, y1 - y0 - 0.02, 0.01), "naranja", rot, bisel=0.002)
        for k, y in enumerate(ys):
            # Bocas de escape (con su cara plana para el múltiple) y el asiento de la bujía
            boca = en_banco(lado, DECK + 0.05, CABEZA_ANCHO / 2 + 0.012, y)
            m.caja(boca, (0.026, 0.05, 0.038), "naranja", rot, bisel=0.004)
            if k < 3:
                b = en_banco(lado, DECK + 0.03, CABEZA_ANCHO / 2 + 0.003, y + ENTRE_CILINDROS / 2)
                m.tornillo(b, afuera_banco(lado), r=0.0075, alto=0.008)       # tornillos de tapa
            base, _, _ = bujia_puntos(lado, y)
            m.cilindro(base - afuera_banco(lado) * 0.02, base, 0.014, "naranja", lados=16, bisel=0.002)
        # Los tornillos de la tapa del lado de afuera, abajo (los que se ven)
        for y in (y0 + 0.02, y1 - 0.02):
            b = en_banco(lado, DECK + 0.03, CABEZA_ANCHO / 2 + 0.003, y)
            m.tornillo(b, afuera_banco(lado), r=0.0075, alto=0.008)
        # Orejas de adelante, donde se toman los soportes de los accesorios
        oreja = en_banco(lado, DECK + 0.05, 0.03, y0 - 0.008)
        m.caja(oreja, (0.06, 0.016, 0.05), "naranja", rot, bisel=0.003)
        hijos.append(m.objeto(f"tapa-cilindros-{sufijo}", mats))
    return vacio("tapas-cilindros", hijos)


def carter(mats):
    m = Malla(["naranja", "acero"])
    arriba = CIG_Z - 0.045
    largo = BLOQUE_Y[1] - BLOQUE_Y[0] - 0.02
    cy = (BLOQUE_Y[0] + BLOQUE_Y[1]) / 2
    m.caja((0, cy, arriba - 0.005), (0.46, largo, 0.01), "naranja", bisel=0.003)            # pestaña
    m.caja((0, cy + 0.02, arriba - 0.055), (0.40, largo - 0.06, 0.095), "naranja", bisel=0.02, segmentos=3)
    m.caja((0, -1.36, arriba - 0.115), (0.36, 0.26, 0.13), "naranja", bisel=0.025, segmentos=3)  # pozo (adelante)
    # Nervios estampados a los costados del pozo
    for lado in (1, -1):
        for y in (-1.43, -1.36, -1.29):
            m.caja((lado * 0.178, y, arriba - 0.12), (0.012, 0.02, 0.08), "naranja", bisel=0.005)
        # Tornillos de la pestaña (los de los costados)
        m.tornillos([(lado * 0.215, y, arriba) for y in np.linspace(BLOQUE_Y[0] + 0.04, BLOQUE_Y[1] - 0.04, 9)],
                    Z * -1, r=0.0055, alto=0.005)
    # Tapón del aceite, abajo
    m.tornillo((0.06, -1.30, arriba - 0.18), -Z, r=0.011, alto=0.01)
    return m.objeto("carter", mats)


def multiple_admision(mats):
    m = Malla(["naranja", "acero"])
    y0, y1 = BLOQUE_Y[0] + 0.06, BLOQUE_Y[1] - 0.05
    # El cuerpo central (el plénum), con los costados en pendiente hacia cada tapa de cilindros
    perfil = [(-0.13, BASE_CARB_Z - 0.05), (-0.075, CIG_Z + 0.172), (0.075, CIG_Z + 0.172),
              (0.13, BASE_CARB_Z - 0.05), (0.09, BASE_CARB_Z - 0.025), (-0.09, BASE_CARB_Z - 0.025)]
    m.prisma(perfil, y0, y1, "naranja", bisel=0.008)
    # Ocho conductos, uno a cada cilindro, que bajan hasta la boca de admisión
    for lado in (1, -1):
        for y in cilindros_y(lado):
            boca = en_banco(lado, DECK + 0.055, -0.07, y)
            arriba = Vector((lado * 0.085, y, BASE_CARB_Z - 0.045))
            m.tubo([arriba, (arriba + boca) / 2 + Vector((lado * 0.015, 0, 0.012)), boca], 0.024, "naranja", lados=10)
            m.caja(boca - eje_banco(lado) * 0.004, (0.05, 0.054, 0.008), "naranja", rot_y(45 * lado - 90 * lado), bisel=0.002)
        # Tornillos a las tapas de cilindros, entre conducto y conducto
        for y in cilindros_y(lado)[:3]:
            p = en_banco(lado, DECK + 0.075, -0.06, y + ENTRE_CILINDROS / 2)
            m.tornillo(p, Vector((lado * 0.4, 0, 1)), r=0.0065)
    # Base del carburador, con sus 4 espárragos
    m.caja((0, CARB_Y, BASE_CARB_Z - 0.018), (0.16, 0.17, 0.036), "naranja", bisel=0.005)
    for dx in (0.06, -0.06):
        for dy in (0.065, -0.065):
            m.cilindro((dx, CARB_Y + dy, BASE_CARB_Z), (dx, CARB_Y + dy, BASE_CARB_Z + 0.012), 0.004, "acero", lados=8)
    # Adelante: el paso de agua (donde apoya el termostato) y la toma de la calefacción
    m.caja((0, y0 - 0.01, BASE_CARB_Z - 0.06), (0.2, 0.05, 0.05), "naranja", bisel=0.008)
    m.cilindro(TOMA_CALEFACCION, TOMA_CALEFACCION + Vector((-0.004, -0.03, 0.012)), 0.009, "acero", lados=12)
    # Atrás: el asiento del distribuidor
    m.cilindro((DISTRIBUIDOR.x, DISTRIBUIDOR.y, CIG_Z + 0.2), (DISTRIBUIDOR.x, DISTRIBUIDOR.y, BASE_CARB_Z - 0.065),
               0.042, "naranja", lados=24, bisel=0.004)
    return m.objeto("multiple-admision", mats)


TOMA_CALEFACCION = Vector((-0.075, BLOQUE_Y[0] + 0.05, BASE_CARB_Z - 0.05))
TERMOSTATO = Vector((0, BLOQUE_Y[0] + 0.045, BASE_CARB_Z - 0.035))   # base del termostato


def termostato(mats):
    """La toma de agua de arriba (codo de hierro) que tapa el termostato; de acá sale la manguera
    de arriba al radiador."""
    m = Malla(["naranja", "acero"])
    base = TERMOSTATO
    m.caja(base + Vector((0, 0, 0.006)), (0.075, 0.05, 0.012), "naranja", bisel=0.003)
    m.torno([(0.03, 0), (0.028, 0.028), (0.0, 0.028)], base + Vector((0, 0, 0.012)), Z, "naranja", lados=24, bisel=0.004)
    cuello = termostato_cuello()
    m.cilindro(base + Vector((0, 0, 0.03)), cuello, 0.021, "naranja", lados=20, bisel=0.002)
    m.cilindro(cuello, cuello + (cuello - base - Vector((0, 0, 0.03))).normalized() * 0.006, 0.024, "naranja", lados=20, bisel=0.002)
    for dx in (0.03, -0.03):
        m.tornillo(base + Vector((dx, 0, 0.012)), Z, r=0.006)
    return m.objeto("termostato", mats)


def termostato_cuello():
    return TERMOSTATO + Vector((0.035, -0.05, 0.055))


def tapas_valvulas(mats):
    hijos = []
    for lado, sufijo in ((1, "izq"), (-1, "der")):
        m = Malla(["cromo", "negro", "goma"])
        ys = cilindros_y(lado)
        y0, y1 = ys[0] - 0.075, ys[-1] + 0.075
        rot = rot_y(45 * lado)
        c = en_banco(lado, DECK + CABEZA_ALTO + 0.042, 0, (y0 + y1) / 2)
        # La tapa estampada: bien redondeada, con la pestaña de abajo y dos refuerzos a lo largo
        m.caja(c, (0.15, y1 - y0, 0.072), "cromo", rot, bisel=0.022, segmentos=5)
        pest = en_banco(lado, DECK + CABEZA_ALTO + 0.008, 0, (y0 + y1) / 2)
        m.caja(pest, (0.168, y1 - y0 + 0.014, 0.006), "cromo", rot, bisel=0.0025)
        m.caja(en_banco(lado, DECK + CABEZA_ALTO + 0.004, 0, (y0 + y1) / 2), (0.16, y1 - y0 + 0.006, 0.004), "goma", rot)
        for t in (0.04, -0.04):
            nerv = en_banco(lado, DECK + CABEZA_ALTO + 0.078, t, (y0 + y1) / 2)
            m.caja(nerv, (0.012, y1 - y0 - 0.1, 0.006), "cromo", rot, bisel=0.003)
        # Cuatro tornillos con sus planchuelas (dos arriba, dos abajo)
        for t in (0.088, -0.088):
            for y in (y0 + 0.07, y1 - 0.07):
                p = en_banco(lado, DECK + CABEZA_ALTO + 0.012, t, y)
                m.caja(p, (0.018, 0.03, 0.003), "cromo", rot, bisel=0.001)
                m.tornillo(p + eje_banco(lado) * 0.0015, eje_banco(lado), mat="cromo", r=0.005, alto=0.005, arandela=False)
        # Tapón del aceite con respiradero (derecha, adelante) y válvula PCV (izquierda, atrás)
        if lado < 0:
            b = en_banco(lado, DECK + CABEZA_ALTO + 0.078, -0.01, y0 + 0.08)
            m.torno([(0.022, 0), (0.034, 0.004), (0.034, 0.03), (0.03, 0.036), (0.0, 0.038)], b, eje_banco(lado),
                    "cromo", lados=32, bisel=0.002)
        else:
            b = en_banco(lado, DECK + CABEZA_ALTO + 0.078, -0.01, y1 - 0.08)
            m.torno([(0.016, 0), (0.016, 0.012), (0.011, 0.016), (0.011, 0.04), (0.0, 0.04)], b, eje_banco(lado),
                    "goma", lados=16)
        hijos.append(m.objeto(f"tapa-valvulas-{sufijo}", mats))
    return vacio("tapas-valvulas", hijos)


def pcv_punto():
    return en_banco(1, DECK + CABEZA_ALTO + 0.078 + 0.04, -0.01, cilindros_y(1)[-1] + 0.075 - 0.08)


def multiples_escape(mats):
    hijos = []
    for lado, sufijo in ((1, "izq"), (-1, "der")):
        m = Malla(["hierro", "acero"])
        ys = cilindros_y(lado)
        log = en_banco(lado, DECK + 0.03, CABEZA_ANCHO / 2 + 0.06, 0) - Vector((0, 0, 0.03))
        # El colector («log»), más grueso hacia la salida
        ys_salida = (ys[1] + ys[2]) / 2
        m.cilindro((log.x, ys[0] - 0.035, log.z), (log.x, ys_salida, log.z), 0.028, "hierro", r2=0.034, lados=16, bisel=0.004)
        m.cilindro((log.x, ys_salida, log.z), (log.x, ys[-1] + 0.035, log.z), 0.034, "hierro", r2=0.028, lados=16, bisel=0.004)
        for y in ys:
            boca = en_banco(lado, DECK + 0.05, CABEZA_ANCHO / 2 + 0.031, y)
            m.tubo([boca, boca + afuera_banco(lado) * 0.02 - Vector((0, 0, 0.005)), Vector((log.x, y, log.z))],
                   0.021, "hierro", lados=10)
            # Brida contra la tapa de cilindros (apoyada en la boca), con su tornillo
            m.caja(boca, (0.010, 0.05, 0.04), "hierro", rot_y(45 * lado), bisel=0.003)
            m.tornillo(boca + afuera_banco(lado) * 0.006 + Y * 0.02, afuera_banco(lado), r=0.006)
        # Salida hacia abajo con la brida de dos espárragos
        m.cilindro((log.x, ys_salida, log.z), (log.x, ys_salida, 0.245), 0.033, "hierro", lados=16)
        m.torno([(0.033, 0), (0.055, 0.0), (0.055, 0.014), (0.033, 0.014)], (log.x, ys_salida, 0.245), -Z, "hierro",
                lados=24, bisel=0.002)
        for dy in (0.045, -0.045):
            m.tornillo((log.x, ys_salida + dy, 0.231), -Z, r=0.0065)
        if lado < 0:
            # Válvula de calor (el contrapeso al costado de la salida, del lado del acompañante)
            m.cilindro((log.x - 0.04, ys_salida, 0.27), (log.x + 0.04, ys_salida, 0.27), 0.006, "acero", lados=8)
            m.caja((log.x - 0.048, ys_salida - 0.012, 0.262), (0.008, 0.04, 0.022), "acero", bisel=0.002)
        else:
            # Oreja donde se toma el soporte de abajo del alternador
            m.caja((log.x + 0.005, ys[0] - 0.02, log.z + 0.035), (0.02, 0.03, 0.03), "hierro", bisel=0.003)
        hijos.append(m.objeto(f"multiple-escape-{sufijo}", mats))
    return vacio("multiples-escape", hijos)


def bomba_agua(mats):
    """Bomba de agua corta (la de 1967-68): caracol, brazos a cada fila, eje con su brida."""
    m = Malla(["naranja", "acero"])
    y0 = BLOQUE_Y[0] - 0.034
    for lado in (1, -1):
        m.tubo([(lado * 0.13, y0 + 0.01, CIG_Z + 0.115), (lado * 0.07, y0 - 0.02, CIG_Z + 0.12),
                (0, y0 - 0.035, BOMBA_Z - 0.03)], 0.026, "naranja", lados=10)
        m.cilindro((lado * 0.135, y0 + 0.012, CIG_Z + 0.115), (lado * 0.135, y0 - 0.004, CIG_Z + 0.115), 0.032,
                   "naranja", lados=16, bisel=0.003)
        m.tornillo((lado * 0.135, y0 - 0.004, CIG_Z + 0.135), -Y, r=0.0065)
        m.tornillo((lado * 0.135, y0 - 0.004, CIG_Z + 0.095), -Y, r=0.0065)
    # Caracol y nariz (de atrás para adelante)
    m.torno([(0.072, 0), (0.074, 0.045), (0.06, 0.06), (0.04, 0.07), (0.03, 0.09)],
            (0, y0 + 0.005, BOMBA_Z - 0.01), -Y, "naranja", lados=32, bisel=0.004)
    m.torno([(0.022, 0), (0.022, 0.03), (0.0, 0.03)], (0, y0 - 0.085, BOMBA_Z), -Y, "acero", lados=20)
    m.torno([(0.045, 0), (0.045, 0.005), (0.0, 0.005)], (0, POLEAS_Y + 0.018, BOMBA_Z), -Y, "acero", lados=24)
    # Entrada de la manguera de abajo (del lado del conductor) y la de la calefacción, arriba
    m.cilindro(BOMBA_ENTRADA - Vector((-0.02, 0.0, 0.02)) * 0.8, BOMBA_ENTRADA, 0.02, "naranja", lados=16, bisel=0.002)
    m.cilindro((-0.04, y0 - 0.04, BOMBA_Z + 0.04), BOMBA_CALEFACCION, 0.008, "acero", lados=10)
    return m.objeto("bomba-agua", mats)


BOMBA_ENTRADA = Vector((0.10, BLOQUE_Y[0] - 0.034 - 0.07, CIG_Z + 0.06))
BOMBA_CALEFACCION = Vector((-0.05, BLOQUE_Y[0] - 0.034 - 0.045, BOMBA_Z + 0.075))


def motor_arranque(mats):
    m = Malla(["negro", "aluminio", "acero"])
    c = Vector((-0.19, -0.98, 0.28))
    m.torno([(0.0, 0), (0.05, 0.0), (0.055, 0.008), (0.055, 0.19), (0.05, 0.2), (0.0, 0.2)], c - Y * 0.1, Y,
            "negro", lados=28, bisel=0.002)
    m.torno([(0.0, 0), (0.046, 0), (0.05, 0.03), (0.04, 0.05), (0.0, 0.05)], c + Y * 0.1, Y, "aluminio", lados=28, bisel=0.003)
    m.torno([(0.03, 0), (0.045, 0.02), (0.0, 0.025)], c - Y * 0.1, -Y, "aluminio", lados=24, bisel=0.002)
    for a in (40, 220):
        p = c + Vector((math.cos(math.radians(a)) * 0.042, -0.125, math.sin(math.radians(a)) * 0.042))
        m.tornillo(p, -Y, r=0.005)
    # El solenoide encima, con sus bornes
    sol = c + Vector((-0.045, 0.03, 0.06))
    m.torno([(0.0, 0), (0.028, 0), (0.03, 0.006), (0.03, 0.11), (0.0, 0.11)], sol - Y * 0.06, Y, "negro", lados=24, bisel=0.002)
    m.torno([(0.0, 0), (0.024, 0.0), (0.024, 0.016), (0.0, 0.02)], sol - Y * 0.06, -Y, "negro", lados=20)
    for dx in (0.012, -0.012):
        m.cilindro(sol + Vector((dx, -0.076, 0.0)), sol + Vector((dx, -0.092, 0.0)), 0.004, "acero", lados=8)
        m.tornillo(sol + Vector((dx, -0.084, 0.0)), -Y, r=0.006, alto=0.004, arandela=False)
    # Las orejas de sujeción al bloque
    m.caja(c + Vector((0.05, 0.1, 0.03)), (0.05, 0.03, 0.04), "aluminio", bisel=0.004)
    return m.objeto("motor-arranque", mats)


def bomba_nafta(mats):
    """Bomba de nafta mecánica: va del lado del acompañante, adelante y abajo; la mueve una varilla
    que toca el árbol de levas."""
    m = Malla(["negro", "acero", "zinc"])
    base = Vector((-0.251, -1.42, CIG_Z - 0.005))
    m.caja(base + Vector((-0.005, 0, 0)), (0.012, 0.075, 0.07), "acero", bisel=0.002)
    for dz in (0.024, -0.024):
        m.tornillo(base + Vector((-0.011, 0.025, dz)), -X, r=0.0065)
    cuerpo = base + Vector((-0.045, 0, -0.01))
    m.torno([(0.03, 0), (0.032, 0.04), (0.0, 0.045)], base + Vector((-0.01, 0, 0)), -X, "zinc", lados=20, bisel=0.003)
    # La «hamburguesa»: las dos mitades del diafragma, con el borde engrapado
    m.torno([(0.0, 0), (0.042, 0), (0.046, 0.006), (0.046, 0.012), (0.042, 0.016), (0.0, 0.02)],
            cuerpo + Vector((0, 0, -0.012)), Z, "negro", lados=32, bisel=0.001)
    m.torno([(0.0, 0), (0.04, 0), (0.038, 0.022), (0.0, 0.026)], cuerpo + Vector((0, 0, 0.008)), Z, "negro", lados=32, bisel=0.002)
    m.torno([(0.0, 0), (0.04, 0), (0.036, 0.028), (0.0, 0.032)], cuerpo + Vector((0, 0, -0.012)), -Z, "negro", lados=32, bisel=0.002)
    # Entrada (abajo) y salida (arriba, hacia el carburador)
    m.cilindro(cuerpo + Vector((0, -0.03, -0.02)), cuerpo + Vector((0, -0.055, -0.02)), 0.006, "acero", lados=8)
    m.cilindro(cuerpo + Vector((0, 0.0, 0.03)), BOMBA_NAFTA_SALIDA, 0.006, "acero", lados=8)
    m.tornillo(BOMBA_NAFTA_SALIDA, Z, r=0.008, alto=0.008, arandela=False)
    return m.objeto("bomba-nafta", mats)


BOMBA_NAFTA_SALIDA = Vector((-0.296, -1.42, CIG_Z + 0.04))


def filtro_aceite(mats):
    """Filtro de aceite de cartucho, enroscado abajo del lado del conductor, atrás."""
    m = Malla(["negro", "acero"])
    base = Vector((0.255, -1.00, CIG_Z - 0.045))
    eje = Vector((0.55, 0, -0.83)).normalized()
    m.torno([(0.0, 0), (0.044, 0), (0.047, 0.006), (0.047, 0.11), (0.044, 0.116), (0.03, 0.12), (0.0, 0.12)],
            base, eje, "negro", lados=32, bisel=0.002)
    m.torno([(0.047, 0.004), (0.0485, 0.008), (0.047, 0.012)], base, eje, "acero", lados=32)   # el borde enrollado
    for k in range(3):                      # canaletas para agarrarlo con la llave
        m.torno([(0.0472, 0.09 + k * 0.006), (0.0478, 0.092 + k * 0.006), (0.0472, 0.094 + k * 0.006)], base, eje, "negro", lados=32)
    return m.objeto("filtro-aceite", mats)


def varilla_aceite(mats):
    """La varilla para medir el aceite: el caño sale del bloque, del lado del conductor, y sube
    por afuera del múltiple de escape hasta la manija."""
    m = Malla(["acero", "naranja"])
    y = -1.14
    puntos = [Vector((0.238, y, CIG_Z - 0.03)), Vector((0.31, y, CIG_Z - 0.035)), Vector((0.385, y - 0.005, CIG_Z + 0.03)),
              Vector((0.40, y - 0.015, CIG_Z + 0.18)), Vector((0.395, y - 0.025, CIG_Z + 0.30))]
    m.tubo(puntos, 0.0055, "acero", lados=8)
    tope = puntos[-1]
    m.cilindro(tope, tope + Vector((0, -0.004, 0.012)), 0.008, "acero", lados=12)
    m.cilindro(tope + Vector((0, -0.004, 0.012)), tope + Vector((0, -0.005, 0.02)), 0.0045, "acero", lados=8)
    m.anillo(tope + Vector((0, -0.006, 0.042)), X, 0.02, 0.003, "naranja")
    m.cilindro(puntos[0] - X * 0.006, puntos[0] + X * 0.012, 0.009, "acero", lados=12)
    return m.objeto("varilla-aceite", mats)


TAPA_DIST_Z = (0.665, 0.715)       # tapa del distribuidor: abajo, arriba
TAPA_DIST_R = 0.065


def torres_distribuidor():
    """Las 8 torres de la tapa del distribuidor: (punto de abajo, punta)."""
    torres = []
    for k in range(8):
        ang = math.radians(22.5 + 45 * k)
        dx, dy = math.cos(ang), math.sin(ang)
        base = Vector((DISTRIBUIDOR.x + dx * 0.045, DISTRIBUIDOR.y + dy * 0.045, TAPA_DIST_Z[1] - 0.005))
        torres.append((base, base + Vector((dx * 0.008, dy * 0.008, 0.022))))
    return torres


def distribuidor(mats):
    m = Malla(["aluminio", "negro", "acero"])
    x, y = DISTRIBUIDOR.x, DISTRIBUIDOR.y
    zb = BASE_CARB_Z - 0.065
    # Cuerpo de aluminio (con la base y el collar) y la grapa de sujeción
    m.torno([(0.0, 0), (0.034, 0), (0.036, 0.02), (0.044, 0.025), (0.046, 0.04), (0.06, 0.045), (0.062, TAPA_DIST_Z[0] - zb),
             (0.0, TAPA_DIST_Z[0] - zb)], (x, y, zb), Z, "aluminio", lados=32, bisel=0.003)
    m.caja((x + 0.05, y, zb + 0.012), (0.05, 0.02, 0.006), "acero", bisel=0.002)
    m.tornillo((x + 0.068, y, zb + 0.015), Z, r=0.0065)
    # La tapa (negra, de baquelita) con sus 8 torres y la del medio
    m.torno([(0.0, 0), (TAPA_DIST_R, 0), (TAPA_DIST_R + 0.003, 0.008), (TAPA_DIST_R, 0.014), (TAPA_DIST_R - 0.01, TAPA_DIST_Z[1] - TAPA_DIST_Z[0]),
             (0.0, TAPA_DIST_Z[1] - TAPA_DIST_Z[0])], (x, y, TAPA_DIST_Z[0]), Z, "negro", lados=40, bisel=0.002)
    m.torno([(0.012, 0), (0.012, 0.018), (0.009, 0.026), (0.0, 0.026)], (x, y, TAPA_DIST_Z[1]), Z, "negro", lados=16, bisel=0.001)
    for base, punta in torres_distribuidor():
        m.cilindro(base, punta, 0.0095, "negro", lados=12, bisel=0.001)
    # Las dos grampas de alambre que la sujetan
    for lado in (1, -1):
        p = Vector((x + lado * (TAPA_DIST_R + 0.004), y, TAPA_DIST_Z[0]))
        m.tubo([p - Vector((0, 0.008, 0.03)), p + Vector((lado * 0.002, 0, 0.004)), p + Vector((-lado * 0.004, 0.008, 0.014))],
               0.0016, "acero", lados=4)
    # El avance por vacío (la «capsulita» al costado, hacia adelante y a la izquierda)
    v0 = Vector((x + 0.04, y - 0.03, TAPA_DIST_Z[0] - 0.02))
    v1 = Vector((x + 0.11, y - 0.07, TAPA_DIST_Z[0] - 0.02))
    m.cilindro(v0, v1 - (v1 - v0).normalized() * 0.03, 0.01, "aluminio", lados=12)
    m.torno([(0.0, 0), (0.028, 0), (0.03, 0.012), (0.028, 0.026), (0.0, 0.03)], v1 - (v1 - v0).normalized() * 0.03,
            v1 - v0, "acero", lados=24, bisel=0.002)
    m.cilindro(v1, v1 + (v1 - v0).normalized() * 0.012, 0.004, "acero", lados=8)
    return m.objeto("distribuidor", mats)


BOBINA = (Vector((-0.15, -1.02, 0.60)), Vector((-0.18, -1.03, 0.73)))   # abajo, arriba (sin tocar los cables)


def bobina(mats):
    m = Malla(["negro", "aluminio", "acero"])
    abajo, arriba = BOBINA
    eje = (arriba - abajo).normalized()
    largo = (arriba - abajo).length
    m.torno([(0.0, 0), (0.024, 0), (0.028, 0.008), (0.028, largo), (0.0, largo)], abajo, eje, "negro", lados=24, bisel=0.002)
    m.torno([(0.0, 0), (0.026, 0), (0.022, 0.012), (0.012, 0.016), (0.009, 0.034), (0.0, 0.036)], arriba, eje, "negro",
            lados=24, bisel=0.001)
    # Bornes de los costados (+ y -) con sus tuercas
    for dx in (0.012, -0.012):
        p = arriba + eje * 0.012 + Vector((dx, -0.012, 0))
        m.cilindro(p, p + eje * 0.012, 0.0025, "acero", lados=6)
        m.tornillo(p + eje * 0.004, eje, r=0.0045, alto=0.004, arandela=False)
    # Abrazadera y soporte al múltiple
    medio = (abajo + arriba) / 2
    for k in (-0.25, 0.2):
        m.cilindro(medio + (arriba - abajo) * (k - 0.06), medio + (arriba - abajo) * (k + 0.06), 0.0305, "aluminio", lados=24)
    m.caja((medio.x + 0.05, medio.y, medio.z - 0.03), (0.08, 0.025, 0.004), "aluminio", bisel=0.001)
    m.tornillo((medio.x + 0.08, medio.y, medio.z - 0.028), Z, r=0.006)
    return m.objeto("bobina", mats)


def bujia_puntos(lado, y):
    """Bujía: base (donde entra en la tapa de cilindros), punta (donde termina la porcelana) y eje."""
    base = en_banco(lado, DECK + 0.055, CABEZA_ANCHO / 2 + 0.03, y + 0.028)
    eje = (afuera_banco(lado) * 0.75 + Z * 0.66).normalized()
    return base, base + eje * 0.062, eje


def bujias(mats):
    hijos = []
    for lado in (1, -1):
        for k, y in enumerate(cilindros_y(lado)):
            m = Malla(["acero", "blanco"])
            base, punta, eje = bujia_puntos(lado, y)
            m.torno([(0.0, 0), (0.0105, 0), (0.0105, 0.016), (0.0075, 0.02), (0.0, 0.02)], base, eje, "acero", lados=6)
            m.torno([(0.0, 0.02), (0.0075, 0.02), (0.0065, 0.04), (0.005, 0.056), (0.003, 0.062), (0.0, 0.062)],
                    base, eje, "blanco", lados=16)
            hijos.append(m.objeto(f"bujia-{numero_cilindro(lado, k)}", mats))
    hijos.sort(key=lambda o: int(o.name.split("-")[1]))
    return vacio("bujias", hijos)


def cables_bujias(mats):
    m = Malla(["goma", "negro"])
    torres = torres_distribuidor()
    tapas = []
    for lado in (1, -1):
        for y in cilindros_y(lado):
            base, punta, eje = bujia_puntos(lado, y)
            tapas.append((lado, punta, eje))
    def angulo(p):
        return math.atan2(p.y - DISTRIBUIDOR.y, p.x - DISTRIBUIDOR.x)
    torres.sort(key=lambda t: angulo(t[1]))
    tapas.sort(key=lambda b: angulo(b[1]))
    for (_, tope), (lado, punta, eje) in zip(torres, tapas):
        orden = abs(punta.y - (-0.90)) / 0.6      # los de adelante van más afuera en el mazo
        sx, sz = a_lo_largo(lado, DECK + CABEZA_ALTO + 0.03, 0.12 + 0.01 * orden)
        capuchon = punta + eje * 0.012
        puntos = [tope + Vector((0, 0, 0.012)), tope + Vector((0, 0, 0.035)),
                  Vector((lado * 0.17, -0.90, TAPA_DIST_Z[1] + 0.01)),
                  Vector((sx, -0.955, sz)),
                  Vector((sx, punta.y, sz)),
                  capuchon + eje * 0.025, capuchon]
        m.tubo(puntos, 0.0036, "goma", lados=6)
        # Capuchón de la bujía (cubre la punta de la porcelana) y el de la tapa del distribuidor
        m.torno([(0.0, 0), (0.0085, 0), (0.0085, 0.03), (0.006, 0.038), (0.0, 0.038)], punta - eje * 0.022, eje, "goma", lados=12)
        m.torno([(0.0, 0), (0.0105, 0), (0.0105, 0.016), (0.006, 0.022), (0.0, 0.022)], tope - Vector((0, 0, 0.008)), Z, "goma", lados=12)
    # Los separadores de plástico que sostienen el mazo arriba de cada tapa de válvulas
    for lado in (1, -1):
        sx, sz = a_lo_largo(lado, DECK + CABEZA_ALTO + 0.03, 0.125)
        for y in (-1.33, -1.10):
            m.caja((sx, y, sz), (0.022, 0.012, 0.03), "negro", rot_y(45 * lado), bisel=0.002)
    # El cable de la bobina al centro de la tapa
    abajo, arriba = BOBINA
    sale = arriba + (arriba - abajo).normalized() * 0.036
    m.tubo([sale, sale + Vector((0, 0, 0.04)), Vector((DISTRIBUIDOR.x - 0.06, DISTRIBUIDOR.y - 0.03, TAPA_DIST_Z[1] + 0.07)),
            Vector((DISTRIBUIDOR.x, DISTRIBUIDOR.y, TAPA_DIST_Z[1] + 0.05)), Vector((DISTRIBUIDOR.x, DISTRIBUIDOR.y, TAPA_DIST_Z[1] + 0.024))],
           0.0036, "goma", lados=6)
    return m.objeto("cables-bujias", mats)


def polea_v(m, centro, eje, r, mat, ancho=0.024, cubo=0.02):
    """Polea de una garganta en V (lo que agarra la correa)."""
    h = ancho / 2
    m.torno([(cubo, -h), (r, -h), (r, -h + 0.004), (r - 0.011, -0.0015), (r - 0.011, 0.0015), (r, h - 0.004), (r, h),
             (cubo, h)], Vector(centro), eje, mat, lados=48, bisel=0.0015, angulo=40)


def alternador(mats):
    """Delcotron de 1968 (con el regulador aparte): carcasa de aluminio de dos mitades, ventilador,
    polea y los soportes a la bomba de agua y a la tapa de cilindros."""
    m = Malla(["aluminio", "acero", "negro"])
    c = ALTERNADOR
    # Mitad de atrás y mitad de adelante, con la costura en el medio
    m.torno([(0.0, 0), (0.06, 0), (0.078, 0.01), (0.085, 0.03), (0.085, 0.058), (0.0, 0.058)], c + Y * 0.058, -Y,
            "aluminio", lados=40, bisel=0.002)
    m.torno([(0.0, 0), (0.085, 0), (0.085, 0.03), (0.075, 0.05), (0.03, 0.058), (0.0, 0.058)], c - Y * 0.002, -Y,
            "aluminio", lados=40, bisel=0.002)
    # Ventanas de ventilación (oscuras) alrededor de la mitad de atrás
    for k in range(10):
        a = 2 * math.pi * k / 10
        d = Vector((math.cos(a), 0, math.sin(a)))
        m.caja(c + d * 0.083 + Y * 0.03, (0.012, 0.022, 0.006), "negro", base_de(d.cross(Y), Y, d))
    # Los 4 tornillos pasantes y las orejas (abajo el pivote, arriba la de ajuste)
    for a in (45, 135, 225, 315):
        d = Vector((math.cos(math.radians(a)), 0, math.sin(math.radians(a))))
        m.cilindro(c + d * 0.08 + Y * 0.05, c + d * 0.08 - Y * 0.05, 0.006, "aluminio", lados=10)
        m.tornillo(c + d * 0.08 - Y * 0.056, -Y, r=0.005, alto=0.004, arandela=False)
    m.caja(c + Vector((-0.03, 0.0, -0.088)), (0.03, 0.11, 0.03), "aluminio", bisel=0.005)
    m.caja(c + Vector((-0.07, -0.02, 0.06)), (0.03, 0.02, 0.03), "aluminio", bisel=0.004)
    # Bornes de atrás (BAT y el enchufe)
    m.cilindro(c + Vector((0.02, 0.058, 0.03)), c + Vector((0.02, 0.078, 0.03)), 0.004, "acero", lados=8)
    m.tornillo(c + Vector((0.02, 0.07, 0.03)), Y, r=0.006, alto=0.004, arandela=False)
    m.caja(c + Vector((-0.02, 0.066, 0.035)), (0.022, 0.016, 0.012), "negro", bisel=0.002)
    # Ventilador de chapa: dos discos con paletas en el medio, y la polea adelante
    vf = c - Y * 0.068
    m.cilindro(vf + Y * 0.008, vf + Y * 0.006, 0.072, "acero", lados=32)
    m.cilindro(vf - Y * 0.008, vf - Y * 0.006, 0.072, "acero", lados=32)
    for k in range(12):
        a = 2 * math.pi * k / 12
        d = Vector((math.cos(a), 0, math.sin(a)))
        m.caja(vf + d * 0.048, (0.046, 0.013, 0.0016), "acero", base_de(d, Y, d.cross(Y)))
    polea_v(m, Vector((c.x, POLEAS_Y, c.z)), Y, 0.036, "acero", cubo=0.012)
    m.cilindro(vf - Y * 0.008, Vector((c.x, POLEAS_Y + 0.012, c.z)), 0.012, "acero", lados=12)
    m.tornillo(Vector((c.x, POLEAS_Y - 0.012, c.z)), -Y, r=0.009, alto=0.007)
    # Soportes: el brazo de ajuste (ranurado) a la tapa de cilindros y el de abajo a la bomba de agua
    brazo = Matrix.Translation(c + Vector((-0.12, -0.03, 0.055))) @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Rotation(math.radians(-12), 4, "Z")
    m.placa(redondeado(0.12, 0.024, 0.011), brazo, 0.006, "negro", bisel=0.0015)
    m.tornillo(c + Vector((-0.07, -0.036, 0.062)), -Y, r=0.0065)
    abajo = Matrix.Translation(c + Vector((-0.09, -0.06, -0.075))) @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Rotation(math.radians(25), 4, "Z")
    m.placa(redondeado(0.13, 0.03, 0.012), abajo, 0.008, "negro", bisel=0.0015)
    return m.objeto("alternador", mats)


POLEAS = [
    # (x, z, radio de afuera) en el plano de las poleas
    (0.0, CIG_Z, 0.085),            # cigüeñal (la que manda)
    (0.0, BOMBA_Z, 0.075),          # bomba de agua (y el ventilador)
    (ALTERNADOR.x, ALTERNADOR.z, 0.036),
]


def poleas(mats):
    """Las poleas del cigüeñal y de la bomba de agua (la del alternador va con él)."""
    m = Malla(["negro", "acero"])
    for x, z, r in POLEAS[:2]:
        polea_v(m, Vector((x, POLEAS_Y, z)), -Y, r, "negro", cubo=0.03)
        m.torno([(0.0, 0), (0.032, 0), (0.032, 0.006), (0.0, 0.006)], Vector((x, POLEAS_Y - 0.012, z)), -Y, "negro", lados=24)
        for k in range(4 if z > CIG_Z else 3):
            a = 2 * math.pi * k / (4 if z > CIG_Z else 3) + 0.4
            m.tornillo(Vector((x + math.cos(a) * 0.022, POLEAS_Y - 0.018, z + math.sin(a) * 0.022)), -Y, r=0.0055)
    return m.objeto("poleas", mats)


def balanceador(mats):
    """El balanceador armónico: un aro de hierro sobre una goma, en la punta del cigüeñal, con la
    marca para poner a punto el encendido."""
    m = Malla(["hierro", "goma", "blanco", "acero"])
    atras, adelante = BLOQUE_Y[0] - 0.036, POLEAS_Y + 0.012
    largo = atras - adelante
    m.torno([(0.0, 0), (0.035, 0), (0.035, 0.012), (0.05, 0.016), (0.05, largo - 0.022), (0.035, largo - 0.018),
             (0.035, largo), (0.0, largo)], Vector((0, atras, CIG_Z)), -Y, "hierro", lados=40, bisel=0.002)
    m.torno([(0.05, 0.004), (0.0545, 0.004), (0.0545, largo - 0.014), (0.05, largo - 0.014)],
            Vector((0, atras, CIG_Z)), -Y, "goma", lados=40)
    m.torno([(0.0545, 0), (0.0755, 0.002), (0.076, largo - 0.016), (0.0545, largo - 0.014)],
            Vector((0, atras - 0.004, CIG_Z)), -Y, "hierro", lados=48, bisel=0.002)
    # La rayita del punto muerto superior, pintada de blanco
    m.caja((-0.055, (atras + adelante) / 2 + 0.008, CIG_Z + 0.055), (0.004, largo - 0.03, 0.002), "blanco",
           Matrix.Rotation(math.radians(-45), 4, "Y"))
    m.tornillo((0, adelante - 0.008, CIG_Z), -Y, r=0.012, alto=0.01)
    return m.objeto("balanceador", mats)


def envolvente(puntos):
    """Cápsula convexa de puntos 2D (cadena monótona), en sentido antihorario."""
    pts = sorted(set(puntos))

    def cruz(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    abajo, arriba = [], []
    for p in pts:
        while len(abajo) >= 2 and cruz(abajo[-2], abajo[-1], p) <= 0:
            abajo.pop()
        abajo.append(p)
    for p in reversed(pts):
        while len(arriba) >= 2 and cruz(arriba[-2], arriba[-1], p) <= 0:
            arriba.pop()
        arriba.append(p)
    return abajo[:-1] + arriba[:-1]


def correas(mats):
    """La correa en V que abraza las tres poleas, con su sección de trapecio."""
    m = Malla(["goma"])
    muestras = []
    for x, z, r in POLEAS:
        for k in range(64):
            a = 2 * math.pi * k / 64
            rr = r - 0.009                      # la correa apoya adentro de la garganta
            muestras.append((round(x + rr * math.cos(a), 5), round(z + rr * math.sin(a), 5)))
    camino = envolvente(muestras)
    n = len(camino)
    bm = m.bm
    anillos = []
    for k, p in enumerate(camino):
        prev, sig = camino[k - 1], camino[(k + 1) % n]
        tx, tz = sig[0] - prev[0], sig[1] - prev[1]
        largo = math.hypot(tx, tz) or 1.0
        nx, nz = tz / largo, -tx / largo                   # hacia afuera (camino antihorario)
        seccion = ((0.0, -0.0045), (0.0115, -0.0065), (0.0115, 0.0065), (0.0, 0.0045))
        anillos.append([bm.verts.new((p[0] + nx * h, POLEAS_Y + dy, p[1] + nz * h)) for h, dy in seccion])
    nuevos = []
    for k in range(n):
        a, b = anillos[k], anillos[(k + 1) % n]
        for j in range(4):
            nuevos.append(bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j])))
    m._terminar([v for a in anillos for v in a], "goma", 0)
    return m.objeto("correas", mats, angulo=60)


def ventilador(mats):
    m = Malla(["negro", "acero"])
    y = VENTILADOR_Y
    m.torno([(0.0, 0), (0.03, 0), (0.034, 0.004), (0.034, 0.055), (0.0, 0.058)], Vector((0, POLEAS_Y - 0.018, BOMBA_Z)),
            -Y, "negro", lados=24, bisel=0.002)
    m.torno([(0.0, 0), (0.07, 0), (0.075, 0.004), (0.07, 0.008), (0.0, 0.008)], Vector((0, y + 0.004, BOMBA_Z)), -Y,
            "negro", lados=40, bisel=0.001)
    for k in range(4):
        a = 2 * math.pi * k / 4
        m.tornillo(Vector((math.cos(a) * 0.022, y - 0.004, BOMBA_Z + math.sin(a) * 0.022)), -Y, r=0.0055)
    # 4 palas de chapa, anchas en la punta, con paso y un poco de curva
    pala = [(0.055, -0.022), (0.12, -0.032), (0.205, -0.04), (0.222, -0.03), (0.226, 0.0), (0.222, 0.03), (0.205, 0.04),
            (0.12, 0.034), (0.055, 0.026)]
    for k in range(4):
        giro = Matrix.Rotation(math.radians(45 + 90 * k), 4, "Y")
        paso = Matrix.Rotation(math.radians(28), 4, "X")       # el ángulo que empuja el aire
        mat = Matrix.Translation((0, y, BOMBA_Z)) @ giro @ Matrix.Rotation(math.radians(-90), 4, "X") @ paso
        m.placa(pala, mat, 0.003, "negro", bisel=0.001)
        # El remache de cada pala contra el cubo
        for r in (0.045, 0.06):
            m.tornillo(mat @ Vector((r, 0, -0.0005)), (giro @ Vector((0, -1, 0))), r=0.004, alto=0.002, arandela=False)
    return m.objeto("ventilador", mats)


def carburador(mats):
    """Rochester Quadrajet de 4 bocas: chicas adelante (las primarias), grandes atrás."""
    m = Malla(["zinc", "aluminio", "acero", "negro"])
    c = Vector((0, CARB_Y, BASE_CARB_Z))
    m.caja(c + Vector((0, 0, 0.007)), (0.15, 0.165, 0.014), "aluminio", bisel=0.003)                 # base del acelerador
    for dx in (0.06, -0.06):
        for dy in (0.065, -0.065):
            m.tornillo(c + Vector((dx, dy, 0.014)), Z, r=0.0055, alto=0.004, arandela=False)
    m.caja(c + Vector((0, 0.012, 0.04)), (0.13, 0.13, 0.052), "zinc", bisel=0.006)                    # cuerpo
    m.caja(c + Vector((0, -0.07, 0.034)), (0.11, 0.04, 0.05), "zinc", bisel=0.01)                     # cuba (adelante)
    m.caja(c + Vector((0, -0.002, 0.071)), (0.142, 0.17, 0.012), "zinc", bisel=0.004)                 # tapa de arriba
    # Las 4 bocas con sus mariposas: el cebador adelante, las compuertas de aire atrás
    for x in (-0.026, 0.026):
        m.torno([(0.019, 0), (0.023, 0.006), (0.019, 0.007)], c + Vector((x, -0.04, 0.074)), Z, "zinc", lados=24)
        m.cilindro(c + Vector((x, -0.04, 0.069)), c + Vector((x, -0.04, 0.0695)), 0.017, "negro", lados=20)
        m.torno([(0.03, 0), (0.034, 0.005), (0.03, 0.006)], c + Vector((x, 0.035, 0.074)), Z, "zinc", lados=28)
        m.cilindro(c + Vector((x, 0.035, 0.069)), c + Vector((x, 0.035, 0.0695)), 0.029, "negro", lados=24)
    m.caja(c + Vector((0, -0.04, 0.0785)), (0.09, 0.03, 0.002), "zinc", Matrix.Rotation(math.radians(-15), 4, "X"))   # cebador
    m.caja(c + Vector((0, 0.05, 0.0785)), (0.11, 0.035, 0.002), "zinc", Matrix.Rotation(math.radians(8), 4, "X"))     # compuerta
    # Palanca del acelerador con su resorte, del lado del conductor
    m.cilindro(c + Vector((0.075, 0.02, 0.022)), c + Vector((0.09, 0.02, 0.022)), 0.022, "aluminio", lados=24, bisel=0.002)
    m.caja(c + Vector((0.093, 0.035, 0.01)), (0.004, 0.035, 0.012), "acero", bisel=0.001)
    m.tubo([c + Vector((0.093, 0.05, 0.005)), c + Vector((0.093, 0.075, -0.004)), c + Vector((0.093, 0.1, -0.01))], 0.002, "acero", lados=4)
    # La bomba de pique (la varilla de arriba) y la entrada de nafta adelante, del lado izquierdo
    m.cilindro(c + Vector((0.035, -0.06, 0.077)), c + Vector((0.035, -0.06, 0.095)), 0.004, "acero", lados=8)
    m.caja(c + Vector((0.045, -0.06, 0.096)), (0.03, 0.008, 0.004), "acero", bisel=0.001)
    m.torno([(0.0, 0), (0.012, 0), (0.012, 0.018), (0.0, 0.018)], CARB_ENTRADA, -Y, "acero", lados=6)
    return m.objeto("carburador", mats)


CARB_ENTRADA = Vector((-0.035, CARB_Y - 0.09, BASE_CARB_Z + 0.03))


def filtro_aire(mats):
    """Filtro de aire redondo cromado, de elemento a la vista: base, papel plegado y tapa con aros."""
    m = Malla(["cromo", "papel", "acero"])
    c = Vector((0, CARB_Y, BASE_CARB_Z + 0.085))
    r = FILTRO_RADIO
    # Base: el plato con el borde enrollado y el cuello que entra en el carburador
    m.torno([(0.06, -0.01), (0.062, 0.0), (r - 0.004, 0.0), (r + 0.004, 0.004), (r + 0.005, 0.012), (r - 0.002, 0.014),
             (0.07, 0.012), (0.06, 0.012)], c, Z, "cromo", lados=72, bisel=0.001)
    # El elemento de papel plegado, entre dos aros de chapa
    bm = m.bm
    pliegues, alto, z0 = 96, 0.046, c.z + 0.013
    arriba, abajo = [], []
    for k in range(pliegues * 2):
        a = math.pi * k / pliegues
        rr = r - 0.010 if k % 2 == 0 else r - 0.017
        arriba.append(bm.verts.new((rr * math.cos(a), c.y + rr * math.sin(a), z0 + alto)))
        abajo.append(bm.verts.new((rr * math.cos(a), c.y + rr * math.sin(a), z0)))
    n = len(arriba)
    for k in range(n):
        bm.faces.new((abajo[k], abajo[(k + 1) % n], arriba[(k + 1) % n], arriba[k]))
    m._terminar(arriba + abajo, "papel", 0)
    for zz in (z0 + 0.003, z0 + alto - 0.003):
        m.torno([(r - 0.009, -0.003), (r - 0.0085, 0.003)], Vector((0, c.y, zz)), Z, "acero", lados=72)
    # Tapa: el borde que baja, la panza con dos aros estampados y la mariposa del medio
    z1 = z0 + alto
    m.torno([(r + 0.005, -0.012), (r + 0.006, 0.0), (r - 0.004, 0.006), (r - 0.03, 0.009), (r - 0.034, 0.012),
             (r - 0.04, 0.011), (r - 0.075, 0.014), (r - 0.08, 0.017), (r - 0.088, 0.017), (0.05, 0.019),
             (0.028, 0.019), (0.0, 0.019)], Vector((0, c.y, z1)), Z, "cromo", lados=72, angulo=45)
    m.torno([(r + 0.003, -0.012), (0.0, -0.012)], Vector((0, c.y, z1 - 0.0005)), Z, "cromo", lados=72)
    # La mariposa (la tuerca de alas), bajita: arriba queda apenas 1,5 cm hasta el capot
    m.torno([(0.0, 0), (0.016, 0), (0.014, 0.008), (0.0, 0.009)], Vector((0, c.y, z1 + 0.019)), Z, "cromo", lados=24, bisel=0.001)
    m.placa([(-0.032, 0.0), (-0.028, 0.009), (-0.012, 0.011), (0.012, 0.011), (0.028, 0.009), (0.032, 0.0)],
            Matrix.Translation((0, c.y - 0.002, z1 + 0.019)) @ Matrix.Rotation(math.radians(90), 4, "X"), 0.004, "cromo", bisel=0.0012)
    return m.objeto("filtro-aire", mats)


def radiador(mats):
    m = Malla(["negro", "goma", "cromo", "acero"])
    y = RADIADOR_Y
    ancho, z0, z1 = 0.533, 0.34, 0.74                     # panal de 21″ de ancho
    m.caja((0, y, (z0 + z1) / 2), (ancho, 0.05, z1 - z0), "negro", bisel=0.002)
    # Las aletas (rayas finitas en la cara de atrás, la que se ve con el capot abierto)
    for k in range(28):
        z = z0 + 0.01 + k * (z1 - z0 - 0.02) / 27
        m.caja((0, y + 0.0255, z), (ancho - 0.01, 0.002, 0.004), "goma")
    # Tanques a los costados y el marco de arriba y de abajo
    for lado in (1, -1):
        m.caja((lado * (ancho / 2 + 0.022), y, (z0 + z1) / 2), (0.044, 0.065, z1 - z0 + 0.04), "negro", bisel=0.008)
    for zz in (z0 - 0.012, z1 + 0.012):
        m.caja((0, y, zz), (ancho + 0.02, 0.06, 0.016), "negro", bisel=0.003)
    for lado in (1, -1):
        for zz in (z0 + 0.03, z1 - 0.03):
            m.tornillo((lado * (ancho / 2 + 0.05), y + 0.032, zz), Y, r=0.006)
    # Boca de llenado con la tapa a presión (arriba del tanque izquierdo) y el grifo de abajo
    boca = Vector((ancho / 2 + 0.022, y, z1 + 0.02))
    m.cilindro(boca, boca + Z * 0.016, 0.018, "negro", lados=20)
    m.torno([(0.0, 0), (0.025, 0), (0.026, 0.006), (0.02, 0.012), (0.0, 0.013)], boca + Z * 0.016, Z, "cromo", lados=28, bisel=0.001)
    m.caja(boca + Z * 0.03, (0.03, 0.006, 0.006), "cromo", bisel=0.001)
    m.cilindro((-ancho / 2 - 0.022, y + 0.033, z0 + 0.01), (-ancho / 2 - 0.022, y + 0.05, z0 + 0.01), 0.006, "acero", lados=8)
    # Mangueras con sus abrazaderas: arriba desde el termostato, abajo hacia la bomba de agua
    cuello = termostato_cuello()
    sale = (cuello - TERMOSTATO - Vector((0, 0, 0.03))).normalized()
    arriba = [cuello - sale * 0.012, cuello + sale * 0.03, Vector((0.21, -1.78, 0.715)),
              Vector((ancho / 2 + 0.01, y + 0.06, 0.70)), Vector((ancho / 2 + 0.02, y + 0.034, 0.70))]
    m.tubo(arriba, 0.019, "goma", lados=12)
    m.abrazadera(arriba[0] + sale * 0.014, sale, 0.019)
    m.abrazadera(arriba[-1] + Y * 0.012, Y, 0.019)
    entrada = BOMBA_ENTRADA
    abajo = [entrada - Vector((-0.02, 0.0, 0.02)) * 0.3, entrada + Vector((0.02, -0.05, -0.04)), Vector((0.0, -1.83, 0.30)),
             Vector((-ancho / 2 - 0.01, y + 0.06, 0.38)), Vector((-ancho / 2 - 0.02, y + 0.034, 0.38))]
    m.tubo(abajo, 0.019, "goma", lados=12)
    m.abrazadera(abajo[0] + Vector((0.006, -0.012, -0.01)), Vector((0.3, -0.6, -0.6)), 0.019)
    m.abrazadera(abajo[-1] + Y * 0.012, Y, 0.019)
    return m.objeto("radiador", mats)


def bateria(mats):
    m = Malla(["negro", "aluminio", "goma", "acero"])
    largo, ancho, alto = 0.26, 0.17, 0.19           # 61 A·h, bornes arriba
    b = BATERIA
    m.caja(b + Vector((0, 0, -0.008)), (ancho + 0.03, largo + 0.03, 0.012), "negro", bisel=0.003)            # bandeja
    m.caja(b + Vector((0, 0, alto / 2)), (ancho, largo, alto), "negro", bisel=0.006)
    m.caja(b + Vector((0, 0, alto + 0.004)), (ancho - 0.01, largo - 0.01, 0.008), "goma", bisel=0.003)       # tapa
    for k in range(6):
        y = b.y - largo / 2 + 0.03 + k * (largo - 0.06) / 5
        m.torno([(0.0, 0), (0.012, 0), (0.012, 0.008), (0.0, 0.009)], (b.x, y, alto + b.z + 0.008), Z, "negro", lados=12, bisel=0.001)
    # Bornes: hacia atrás, el positivo del lado del guardabarros, con sus terminales y cables
    for dx, signo in ((0.055, 1), (-0.055, -1)):
        p = Vector((b.x + dx, b.y + largo / 2 - 0.03, b.z + alto + 0.008))
        m.cilindro(p, p + Vector((0, 0, 0.022)), 0.011, "aluminio", r2=0.009, lados=14)
        m.caja(p + Vector((0, 0, 0.014)), (0.03, 0.022, 0.012), "aluminio", bisel=0.002)
        m.tornillo(p + Vector((0.012, 0, 0.02)), Z, r=0.005, alto=0.004, arandela=False)
        m.tubo([p + Vector((0, 0.012, 0.014)), p + Vector((0, 0.05, 0.0)), p + Vector((signo * 0.02, 0.07, -0.08))], 0.007, "goma", lados=8)
    # Sujeción de arriba con sus varillas
    m.caja((b.x, b.y, b.z + alto + 0.012), (ancho + 0.02, 0.025, 0.006), "negro", bisel=0.002)
    for dx in (ancho / 2 + 0.006, -ancho / 2 - 0.006):
        m.cilindro((b.x + dx, b.y, b.z + alto + 0.016), (b.x + dx, b.y, b.z - 0.008), 0.003, "acero", lados=8)
    return m.objeto("bateria", mats)


def soportes_motor(mats):
    """Los soportes del motor: oreja de acero en el bloque, el taco de goma y la base al chasis."""
    hijos = []
    for lado, sufijo in ((1, "izq"), (-1, "der")):
        m = Malla(["negro", "goma", "acero"])
        c = Vector((lado * 0.262, -1.30, CIG_Z + 0.02))
        m.caja(c, (0.016, 0.11, 0.09), "negro", bisel=0.003)
        for dz in (0.025, -0.025):
            m.tornillo(c + Vector((lado * 0.008, 0.035, dz)), X * lado, r=0.0065)
        taco = c + Vector((lado * 0.035, 0, -0.025))
        m.caja(taco, (0.05, 0.085, 0.05), "goma", bisel=0.006)
        m.caja(taco + Vector((lado * 0.035, 0, -0.035)), (0.08, 0.10, 0.008), "negro", Matrix.Rotation(math.radians(-25 * lado), 4, "Y"), bisel=0.002)
        m.cilindro(taco + Vector((0, 0, 0.03)), taco + Vector((0, 0, -0.06)), 0.005, "acero", lados=8)
        hijos.append(m.objeto(f"soporte-motor-{sufijo}", mats))
    return vacio("soportes-motor", hijos)


def mangueras(mats):
    """Las mangueras y caños que van a otras partes del auto: calefacción (al torpedo), PCV,
    vacío del distribuidor y el caño de nafta de la bomba al carburador."""
    m = Malla(["goma", "acero"])
    # Calefacción: del múltiple y de la bomba de agua, por el lado del acompañante, hasta el torpedo
    for inicio, desvio in ((TOMA_CALEFACCION + Vector((-0.004, -0.03, 0.012)), 0.0), (BOMBA_CALEFACCION, 0.03)):
        puntos = [inicio, inicio + Vector((-0.05, -0.02, 0.03)), Vector((-0.40 - desvio, -1.42, 0.60)),
                  Vector((-0.44 - desvio, -1.05, 0.57)), Vector((-0.43 - desvio, TORPEDO_Y - 0.01, 0.58))]
        m.tubo(puntos, 0.0085, "goma", lados=10)
        m.abrazadera(inicio, puntos[1] - inicio, 0.0085)
    # PCV: de la válvula en la tapa izquierda a la base del carburador
    pcv = pcv_punto()
    m.tubo([pcv, pcv + Vector((0, 0, 0.03)), Vector((0.10, -1.07, BASE_CARB_Z + 0.02)),
            Vector((0.07, CARB_Y + 0.07, BASE_CARB_Z + 0.008))], 0.007, "goma", lados=8)
    # Vacío: de la capsulita del distribuidor al carburador
    x, y = DISTRIBUIDOR.x, DISTRIBUIDOR.y
    v1 = Vector((x + 0.11, y - 0.07, TAPA_DIST_Z[0] - 0.02)) + Vector((0.07, -0.04, 0)).normalized() * 0.012
    m.tubo([v1, v1 + Vector((0.03, -0.03, 0.0)), Vector((0.09, CARB_Y + 0.07, BASE_CARB_Z + 0.02)),
            Vector((0.066, CARB_Y + 0.05, BASE_CARB_Z + 0.025))], 0.0035, "goma", lados=6)
    # Caño de nafta: de la bomba (abajo a la derecha) sube por delante hasta la entrada del carburador
    s = BOMBA_NAFTA_SALIDA
    m.tubo([s + Vector((0, 0, 0.008)), s + Vector((0.0, -0.01, 0.06)), Vector((-0.27, -1.52, 0.56)),
            Vector((-0.12, -1.52, 0.66)), CARB_ENTRADA + Vector((0, -0.05, 0)), CARB_ENTRADA - Y * 0.018],
           0.0045, "acero", lados=8)
    return m.objeto("mangueras", mats)


# ----------------------------------------------------------------------------------------------
# Todo junto
# ----------------------------------------------------------------------------------------------
PIEZAS = [
    ("bloque", bloque), ("tapa-distribucion", tapa_distribucion), ("tapas-cilindros", tapas_cilindros),
    ("carter", carter), ("soportes-motor", soportes_motor),
    ("multiple-admision", multiple_admision), ("termostato", termostato), ("tapas-valvulas", tapas_valvulas),
    ("multiples-escape", multiples_escape), ("bujias", bujias), ("bomba-agua", bomba_agua),
    ("balanceador", balanceador), ("poleas", poleas), ("motor-arranque", motor_arranque),
    ("bomba-nafta", bomba_nafta), ("filtro-aceite", filtro_aceite), ("varilla-aceite", varilla_aceite),
    ("distribuidor", distribuidor), ("bobina", bobina), ("cables-bujias", cables_bujias),
    ("alternador", alternador), ("correas", correas), ("ventilador", ventilador),
    ("carburador", carburador), ("filtro-aire", filtro_aire), ("mangueras", mangueras),
    ("radiador", radiador), ("bateria", bateria),
]

# Puntos de enganche (en coordenadas de Blender): los usan la vista Motor y motor_interno.py
ENGANCHES = {
    "enganche_soporte": (0, BLOQUE_Y[1] + 0.018, CIG_Z),    # centro de la brida de atrás: ahí abraza el soporte de taller
    "enganche_ciguenal": (0, (BLOQUE_Y[0] + BLOQUE_Y[1]) / 2, CIG_Z),   # medio del eje del cigüeñal
    "enganche_gancho": (0, CARB_Y, BASE_CARB_Z + 0.23),       # de donde lo levanta la grúa (arriba del filtro)
}


def limpiar_escena():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def construir():
    """Arma el motor en la escena actual y devuelve {id: objeto} (más «motor», el que agrupa)."""
    mats = materiales()
    objs = {}
    for id_, hacer in PIEZAS:
        obj = hacer(mats)
        assert obj.name == id_, f"{obj.name} != {id_}"
        # En Three.js quedan en objeto.userData
        obj["id"] = id_
        obj["grupo"] = "motor"
        objs[id_] = obj
    raiz = bpy.data.objects.new("motor", None)
    raiz.empty_display_type = "PLAIN_AXES"
    bpy.context.scene.collection.objects.link(raiz)
    raiz["grupo"] = "motor"
    for obj in objs.values():
        obj.parent = raiz
    for nombre, lugar in ENGANCHES.items():
        e = bpy.data.objects.new(nombre, None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 0.08
        e.location = lugar
        bpy.context.scene.collection.objects.link(e)
        e.parent = raiz
        objs[nombre] = e
    objs["motor"] = raiz
    return objs


def todos(objs):
    """Los objetos y sus hijos."""
    lista = []
    for o in objs.values():
        lista.append(o)
        lista.extend(o.children_recursive)
    return list(dict.fromkeys(lista))


def controlar(objs):
    """Avisa si alguna pieza toca el capot cerrado o se sale del vano (usa las medidas de la
    carrocería). No frena: solo escribe en la consola."""
    try:
        spec = importlib.util.spec_from_file_location("carroceria", os.path.join(AQUI, "carroceria.py"))
        car = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(car)
    except Exception as error:      # sin la carrocería no se controla, pero se exporta igual
        print(f"  (no se pudo leer carroceria.py para controlar: {error})")
        return True
    bien = True
    bpy.context.view_layer.update()
    for o in todos(objs):
        if o.type != "MESH":
            continue
        mw = o.matrix_world
        holgura, ancho = 9.0, 0.0
        for v in o.data.vertices:
            p = mw @ v.co
            if car.CAPOT_Y[0] < p.y < car.CAPOT_Y[1] and abs(p.x) < car.CAPOT_X:
                holgura = min(holgura, car.altura_chapa(p.y, abs(p.x)) - 0.012 - p.z)
            if p.y > -2.0 and p.z > 0.31:
                ancho = max(ancho, abs(p.x))
        aviso = ""
        if holgura < 0.005:
            aviso += "  ¡TOCA EL CAPOT!"
            bien = False
        if ancho > 0.630:
            aviso += "  ¡SE SALE DEL VANO!"
            bien = False
        print(f"  {o.name:22s} hasta el capot {holgura * 100:5.1f} cm · hasta el costado {ancho:.3f} m{aviso}")
    return bien


def exportar(objs, ruta):
    bpy.ops.object.select_all(action="DESELECT")
    for o in todos(objs):
        o.select_set(True)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=ruta,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_extras=True,
        export_texcoords=True,           # para la textura de fundición
        export_normals=True,
        export_tangents=False,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_cameras=False,
        export_lights=False,
        export_animations=False,
        export_draco_mesh_compression_enable=False,   # Draco va después, con gltf-transform (README.md)
    )


def ruta_salida():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args:
        return os.path.abspath(args[0])
    return os.path.join(AQUI, "..", "modelos", "motor.glb")


if __name__ == "__main__":
    limpiar_escena()
    objetos = construir()
    print("Control de lugar:")
    controlar(objetos)
    salida = ruta_salida()
    exportar(objetos, salida)
    tris = 0
    for o in todos(objetos):
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
    print(f"Listo: {os.path.normpath(salida)} ({os.path.getsize(salida) / 1024:.0f} KB, {tris} triángulos)")
