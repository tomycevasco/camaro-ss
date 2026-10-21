"""
Motor V8 350 (small block Chevrolet) del Camaro SS 1968, hecho por script, pieza por pieza.

Se corre con el Blender portátil, sin abrir la ventana:
    blender -b -P blender/motor.py
(ver blender/LEEME.md). Genera modelos/motor.glb.

Cómo está armado:
1. Las medidas salen del motor de verdad: V a 90°, cilindros cada 4,4″ (11,2 cm), 9,025″ (22,9 cm)
   del cigüeñal a la cara de arriba del bloque. El cigüeñal se ubicó para que el filtro de aire
   quede a ~1,5 cm del capot cerrado, como en el auto.
2. Cada pieza es un objeto con el mismo nombre que el «id» de su ficha (datos/fichas.json). Las que
   van de a dos (tapas de cilindros, tapas de válvulas, múltiples de escape) son un objeto vacío con
   el id y adentro los dos lados («tapa-valvulas-izq», «tapa-valvulas-der»…), como dice «piezas3d».
3. Cada pieza tiene el origen en su centro: así separarla o mostrarla en el paso a paso es mover
   el objeto entero.
4. Todo cuelga de un objeto vacío «motor» (sin mover nada), para encontrar el grupo fácil.
5. Al final controla que nada toque el capot cerrado ni las paredes del vano (lo avisa en la consola).

Ejes en Blender (los mismos de carroceria.py): X = ancho (+X = lado izquierdo, el del conductor),
Y = largo (el frente mira a -Y), Z = arriba. Metros. El origen es el mismo de la carrocería.

Lados del motor: «izq» = lado del conductor (+X), «der» = lado del acompañante (-X).
"""

import importlib.util
import math
import os
import sys

import bmesh
import bpy
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

S45 = math.sqrt(0.5)


def a_lo_largo(lado, d, t=0.0):
    """Punto (x, z) de una fila de cilindros: 'd' a lo largo de la V desde el cigüeñal y 't' de
    costado (positivo = hacia afuera del motor). lado = +1 izquierda, -1 derecha."""
    x = lado * (d * S45 + t * S45)
    z = CIG_Z + d * S45 - t * S45
    return x, z


def cilindros_y(lado):
    corrida = 0.0 if lado > 0 else CORRIDA_BANCADA
    return [CILINDRO_1_Y + corrida + k * ENTRE_CILINDROS for k in range(4)]


# ----------------------------------------------------------------------------------------------
# Materiales
# ----------------------------------------------------------------------------------------------
def srgb_a_lineal(hexa):
    c = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1.0,)


def material(nombre, hexa, rugosidad, metal=0.0, barniz=0.0):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    color = srgb_a_lineal(hexa)
    p.inputs["Base Color"].default_value = color
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rugosidad
    p.inputs["Coat Weight"].default_value = barniz
    if barniz:
        p.inputs["Coat Roughness"].default_value = 0.12
    m.diffuse_color = color
    return m


def materiales():
    return {
        "naranja": material("naranja_chevrolet", "#e2581c", 0.38, barniz=0.45),
        "cromo": material("cromo", "#f2f2f4", 0.06, metal=1.0),
        "hierro": material("hierro_fundido", "#4a4542", 0.72, metal=0.6),
        "aluminio": material("aluminio", "#c4c4c0", 0.38, metal=1.0),
        "zinc": material("zinc_carburador", "#c9bc93", 0.42, metal=1.0),
        "negro": material("negro_semimate", "#1c1d20", 0.5),
        "goma": material("goma", "#0e0e0f", 0.85),
        "papel": material("papel_filtro", "#ddd3bb", 0.95),
    }


# ----------------------------------------------------------------------------------------------
# Herramientas para armar mallas: cada forma se agrega a una malla con su número de material
# ----------------------------------------------------------------------------------------------
class Malla:
    def __init__(self, mats):
        self.bm = bmesh.new()
        self.mats = mats                    # lista de nombres de material, en orden

    def _pintar(self, verts, mat):
        i = self.mats.index(mat)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = i

    def caja(self, centro, medida, mat, rot=None):
        m = Matrix.Translation(Vector(centro)) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal((*medida, 1))
        res = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self._pintar(res["verts"], mat)

    def cilindro(self, a, b, r1, mat, r2=None, lados=24):
        """Cilindro (o cono si r2 cambia) que va del punto a al punto b."""
        a, b = Vector(a), Vector(b)
        eje = b - a
        rot = Vector((0, 0, 1)).rotation_difference(eje.normalized()).to_matrix().to_4x4()
        m = Matrix.Translation((a + b) / 2) @ rot
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=lados,
                                    radius1=r1, radius2=r1 if r2 is None else r2, depth=eje.length, matrix=m)
        self._pintar(res["verts"], mat)

    def esfera(self, centro, radio, mat, escala=(1, 1, 1)):
        m = Matrix.Translation(Vector(centro)) @ Matrix.Diagonal((*escala, 1))
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=16, v_segments=8, radius=radio, matrix=m)
        self._pintar(res["verts"], mat)

    def prisma(self, perfil, y0, y1, mat):
        """Un perfil cerrado (x, z) estirado a lo largo de Y, de y0 a y1."""
        frente = [self.bm.verts.new((x, y0, z)) for x, z in perfil]
        atras = [self.bm.verts.new((x, y1, z)) for x, z in perfil]
        n = len(perfil)
        for k in range(n):
            self.bm.faces.new((frente[k], frente[(k + 1) % n], atras[(k + 1) % n], atras[k]))
        self.bm.faces.new(list(reversed(frente)))
        self.bm.faces.new(atras)
        self._pintar(frente + atras, mat)

    def tubo(self, puntos, radio, mat, lados=8):
        """Un caño o un cable que pasa suave por los puntos (curva de Bézier con espesor)."""
        curva = bpy.data.curves.new("tmp_tubo", "CURVE")
        curva.dimensions = "3D"
        curva.resolution_u = 6
        curva.bevel_depth = radio
        curva.bevel_resolution = max(0, (lados - 4) // 2)
        curva.use_fill_caps = True
        s = curva.splines.new("BEZIER")
        s.bezier_points.add(len(puntos) - 1)
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
        self._pintar(nuevos, mat)
        bpy.data.objects.remove(obj)
        bpy.data.curves.remove(curva)
        bpy.data.meshes.remove(malla)

    def objeto(self, nombre, mats_bpy, biselar=0.0):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        malla = bpy.data.meshes.new(nombre)
        self.bm.to_mesh(malla)
        self.bm.free()
        obj = bpy.data.objects.new(nombre, malla)
        bpy.context.scene.collection.objects.link(obj)
        for m in self.mats:
            obj.data.materials.append(mats_bpy[m])
        if biselar:
            # Cantos apenas redondeados: con luz de estudio es lo que hace que se vea «de verdad»
            mod = obj.modifiers.new("bisel", "BEVEL")
            mod.width = biselar
            mod.segments = 2
            mod.limit_method = "ANGLE"
            mod.angle_limit = math.radians(40)
            mod.harden_normals = False
            aplicar_modificadores(obj)
        suavizar(obj)
        centrar_origen(obj)
        return obj


def aplicar_modificadores(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    malla = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
    viejo = obj.data
    obj.modifiers.clear()
    obj.data = malla
    bpy.data.meshes.remove(viejo)
    malla.name = obj.name


def suavizar(obj, angulo=35):
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


def rot_y(grados):
    return Matrix.Rotation(math.radians(grados), 4, "Y")


def vacio(nombre, hijos):
    """Objeto vacío en el medio de sus hijos, que los agrupa (piezas que van de a dos)."""
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


# ----------------------------------------------------------------------------------------------
# Las piezas (en el orden del paso a paso de las fichas)
# ----------------------------------------------------------------------------------------------
def bloque(mats):
    """La V de hierro: perfil del bloque estirado a lo largo, tapa de distribución y soportes."""
    m = Malla(["naranja"])
    # Media V (lado +X) de abajo al medio, en metros relativos al cigüeñal
    ext = a_lo_largo(1, DECK, 0.115)
    inn = a_lo_largo(1, DECK, -0.085)
    media = [(0.0, -0.045), (0.205, -0.045), (0.228, 0.0), (ext[0] - 0.005, ext[1] - CIG_Z - 0.02),
             (ext[0], ext[1] - CIG_Z), (inn[0], inn[1] - CIG_Z), (0.035, 0.175), (0.0, 0.168)]
    perfil = [(x, CIG_Z + z) for x, z in media]
    perfil += [(-x, z) for x, z in reversed(perfil[1:-1])]     # la otra mitad, en espejo
    m.prisma(perfil, BLOQUE_Y[0], BLOQUE_Y[1], "naranja")
    # Tapa de la distribución (adelante, abajo de la bomba de agua)
    m.caja((0, BLOQUE_Y[0] - 0.015, CIG_Z + 0.03), (0.17, 0.03, 0.16), "naranja")
    m.cilindro((0, BLOQUE_Y[0] - 0.01, CIG_Z), (0, BLOQUE_Y[0] - 0.035, CIG_Z), 0.05, "naranja")
    # Brida de atrás (donde se atornilla la caja) y soportes del motor a los costados
    m.caja((0, BLOQUE_Y[1] + 0.008, CIG_Z + 0.06), (0.46, 0.016, 0.24), "naranja")
    for lado in (1, -1):
        m.caja((lado * 0.245, -1.30, CIG_Z + 0.02), (0.04, 0.10, 0.08), "naranja")
    return m.objeto("bloque", mats, biselar=0.006)


def tapas_cilindros(mats):
    hijos = []
    for lado, sufijo in ((1, "izq"), (-1, "der")):
        m = Malla(["naranja"])
        ys = cilindros_y(lado)
        y0, y1 = ys[0] - 0.10, ys[-1] + 0.10
        x, z = a_lo_largo(lado, DECK + CABEZA_ALTO / 2)
        rot = rot_y(45 * lado)
        m.caja((x, (y0 + y1) / 2, z), (CABEZA_ANCHO, y1 - y0, CABEZA_ALTO), "naranja", rot)
        # Las bocas de escape asoman del lado de afuera, entre las bujías
        for y in ys:
            px, pz = a_lo_largo(lado, DECK + 0.05, CABEZA_ANCHO / 2 + 0.01)
            m.caja((px, y, pz), (0.03, 0.045, 0.035), "naranja", rot)
        hijos.append(m.objeto(f"tapa-cilindros-{sufijo}", mats, biselar=0.005))
    return vacio("tapas-cilindros", hijos)


def carter(mats):
    m = Malla(["naranja"])
    arriba = CIG_Z - 0.045
    largo = BLOQUE_Y[1] - BLOQUE_Y[0] - 0.02
    m.caja((0, (BLOQUE_Y[0] + BLOQUE_Y[1]) / 2, arriba - 0.006), (0.43, largo, 0.012), "naranja")   # pestaña
    m.caja((0, (BLOQUE_Y[0] + BLOQUE_Y[1]) / 2, arriba - 0.06), (0.38, largo - 0.04, 0.11), "naranja")
    m.caja((0, -1.35, arriba - 0.12), (0.34, 0.28, 0.12), "naranja")                                 # pozo
    m.cilindro((0.06, -1.30, arriba - 0.18), (0.06, -1.30, arriba - 0.19), 0.012, "naranja")          # tapón
    return m.objeto("carter", mats, biselar=0.012)


def multiple_admision(mats):
    m = Malla(["naranja"])
    y0, y1 = BLOQUE_Y[0] + 0.06, BLOQUE_Y[1] - 0.05
    perfil = [(-0.13, BASE_CARB_Z - 0.045), (-0.075, CIG_Z + 0.172), (0.075, CIG_Z + 0.172),
              (0.13, BASE_CARB_Z - 0.045), (0.11, BASE_CARB_Z - 0.03), (-0.11, BASE_CARB_Z - 0.03)]
    m.prisma(perfil, y0, y1, "naranja")
    # Ocho caños, uno a cada cilindro (los bultos de arriba)
    for lado in (1, -1):
        for y in cilindros_y(lado):
            m.caja((lado * 0.115, y, BASE_CARB_Z - 0.045), (0.06, 0.05, 0.04), "naranja", rot_y(-25 * lado))
    # Base del carburador y la salida del termostato adelante
    m.caja((0, CARB_Y, BASE_CARB_Z - 0.02), (0.16, 0.16, 0.04), "naranja")
    m.cilindro((0, y0 + 0.02, BASE_CARB_Z - 0.035), (0, y0 - 0.03, BASE_CARB_Z - 0.03), 0.028, "naranja")
    # El «asiento» del distribuidor, atrás
    m.cilindro((DISTRIBUIDOR.x, DISTRIBUIDOR.y, CIG_Z + 0.2), (DISTRIBUIDOR.x, DISTRIBUIDOR.y, BASE_CARB_Z - 0.06),
               0.04, "naranja")
    return m.objeto("multiple-admision", mats, biselar=0.006)


def tapas_valvulas(mats):
    hijos = []
    for lado, sufijo in ((1, "izq"), (-1, "der")):
        m = Malla(["cromo", "negro"])
        ys = cilindros_y(lado)
        y0, y1 = ys[0] - 0.075, ys[-1] + 0.075
        rot = rot_y(45 * lado)
        x, z = a_lo_largo(lado, DECK + CABEZA_ALTO + 0.035)
        m.caja((x, (y0 + y1) / 2, z), (0.15, y1 - y0, 0.07), "cromo", rot)
        # Pestaña de abajo, apenas más ancha
        x2, z2 = a_lo_largo(lado, DECK + CABEZA_ALTO + 0.004)
        m.caja((x2, (y0 + y1) / 2, z2), (0.165, y1 - y0 + 0.012, 0.008), "cromo", rot)
        # Tapón de aceite (derecha, adelante) y válvula PCV (izquierda, atrás)
        tx, tz = a_lo_largo(lado, DECK + CABEZA_ALTO + 0.07, 0.01)
        ty = y0 + 0.07 if lado < 0 else y1 - 0.08
        punta = a_lo_largo(lado, DECK + CABEZA_ALTO + 0.10, 0.01)
        m.cilindro((tx, ty, tz), (punta[0], ty, punta[1]), 0.028 if lado < 0 else 0.016,
                   "cromo" if lado < 0 else "negro")
        hijos.append(m.objeto(f"tapa-valvulas-{sufijo}", mats, biselar=0.02))
    return vacio("tapas-valvulas", hijos)


TUBO_ESCAPE = (CABEZA_ANCHO / 2 + 0.075, DECK + 0.05)   # (de costado, a lo largo) del caño colector


def multiples_escape(mats):
    hijos = []
    for lado, sufijo in ((1, "izq"), (-1, "der")):
        m = Malla(["hierro"])
        ys = cilindros_y(lado)
        tx, tz = a_lo_largo(lado, DECK + 0.03, CABEZA_ANCHO / 2 + 0.06)
        tz -= 0.03
        m.cilindro((tx, ys[0] - 0.04, tz), (tx, ys[-1] + 0.04, tz), 0.032, "hierro", lados=16)
        for y in ys:
            px, pz = a_lo_largo(lado, DECK + 0.05, CABEZA_ANCHO / 2 + 0.02)
            m.cilindro((px, y, pz), (tx, y, tz), 0.024, "hierro", lados=12)
        # Salida hacia abajo, con su brida
        ys_salida = (ys[1] + ys[2]) / 2
        m.cilindro((tx, ys_salida, tz), (tx, ys_salida, 0.24), 0.032, "hierro", lados=16)
        m.cilindro((tx, ys_salida, 0.26), (tx, ys_salida, 0.245), 0.05, "hierro", lados=16)
        hijos.append(m.objeto(f"multiple-escape-{sufijo}", mats))
    return vacio("multiples-escape", hijos)


def bomba_agua(mats):
    m = Malla(["naranja"])
    y0 = BLOQUE_Y[0] - 0.005
    m.caja((0, y0 - 0.035, CIG_Z + 0.105), (0.27, 0.06, 0.06), "naranja")                  # brazos a cada fila
    m.cilindro((0, y0, BOMBA_Z - 0.02), (0, y0 - 0.085, BOMBA_Z - 0.02), 0.07, "naranja", lados=32)   # caracol
    m.cilindro((0, y0 - 0.085, BOMBA_Z), (0, POLEAS_Y + 0.012, BOMBA_Z), 0.035, "naranja")            # eje
    m.cilindro((-0.09, y0 - 0.05, CIG_Z + 0.08), (-0.10, y0 - 0.10, CIG_Z + 0.06), 0.02, "naranja")   # entrada
    return m.objeto("bomba-agua", mats)


def motor_arranque(mats):
    m = Malla(["negro", "aluminio"])
    c = Vector((-0.19, -0.98, 0.28))
    m.cilindro(c + Vector((0, -0.10, 0)), c + Vector((0, 0.10, 0)), 0.055, "negro", lados=24)
    m.cilindro(c + Vector((0, -0.11, 0)), c + Vector((0, -0.10, 0)), 0.045, "aluminio", lados=24)
    sol = c + Vector((-0.055, 0.02, 0.05))
    m.cilindro(sol + Vector((0, -0.06, 0)), sol + Vector((0, 0.06, 0)), 0.03, "negro", lados=20)
    m.cilindro(sol + Vector((0, -0.07, 0)), sol + Vector((0, -0.06, 0)), 0.022, "aluminio", lados=20)
    return m.objeto("motor-arranque", mats)


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
    m = Malla(["aluminio", "negro"])
    x, y = DISTRIBUIDOR.x, DISTRIBUIDOR.y
    m.cilindro((x, y, BASE_CARB_Z - 0.06), (x, y, TAPA_DIST_Z[0]), 0.038, "aluminio", lados=24)
    m.cilindro((x, y, TAPA_DIST_Z[0]), (x, y, TAPA_DIST_Z[1]), TAPA_DIST_R, "negro", r2=TAPA_DIST_R - 0.01, lados=32)
    m.cilindro((x, y, TAPA_DIST_Z[1]), (x, y, TAPA_DIST_Z[1] + 0.022), 0.009, "negro", lados=12)    # torre central
    for base, punta in torres_distribuidor():
        m.cilindro(base, punta, 0.009, "negro", lados=12)
    # Tornillo de vacío al costado (la «capsulita»)
    m.cilindro((x + 0.03, y - 0.03, TAPA_DIST_Z[0] - 0.02), (x + 0.10, y - 0.06, TAPA_DIST_Z[0] - 0.02),
               0.025, "aluminio", lados=16)
    return m.objeto("distribuidor", mats)


BOBINA = (Vector((-0.15, -1.02, 0.60)), Vector((-0.18, -1.03, 0.73)))   # abajo, arriba (sin tocar los cables)


def bobina(mats):
    m = Malla(["negro", "aluminio"])
    abajo, arriba = BOBINA
    m.cilindro(abajo, arriba, 0.028, "negro", lados=20)
    m.cilindro(arriba, arriba + (arriba - abajo).normalized() * 0.012, 0.022, "negro", lados=20)
    m.cilindro(arriba + (arriba - abajo).normalized() * 0.012, arriba + (arriba - abajo).normalized() * 0.03,
               0.008, "negro", lados=12)
    # Abrazadera y soporte al múltiple
    medio = (abajo + arriba) / 2
    m.cilindro(medio - (arriba - abajo) * 0.12, medio + (arriba - abajo) * 0.12, 0.031, "aluminio", lados=20)
    m.caja((medio.x + 0.05, medio.y, medio.z - 0.03), (0.08, 0.025, 0.006), "aluminio")
    return m.objeto("bobina", mats)


def cables_bujias(mats):
    m = Malla(["goma"])
    torres = torres_distribuidor()
    bujias = []
    for lado in (1, -1):
        for y in cilindros_y(lado):
            bx, bz = a_lo_largo(lado, DECK + 0.07, CABEZA_ANCHO / 2 + 0.07)
            bujias.append((lado, Vector((bx, y, bz))))
    # Cada torre al cilindro que le queda más a mano, sin cruzarse: se ordenan por ángulo
    def angulo(p):
        return math.atan2(p.y - DISTRIBUIDOR.y, p.x - DISTRIBUIDOR.x)
    torres.sort(key=lambda t: angulo(t[1]))
    bujias.sort(key=lambda b: angulo(b[1]))
    for k, ((_, punta), (lado, bujia)) in enumerate(zip(torres, bujias)):
        orden = abs(bujia.y - (-0.90)) / 0.6      # los de adelante van más afuera en el mazo
        sx, sz = a_lo_largo(lado, DECK + CABEZA_ALTO + 0.03, 0.115 + 0.01 * orden)
        puntos = [punta, punta + Vector((0, 0, 0.03)),
                  Vector((lado * 0.17, -0.90, TAPA_DIST_Z[1] + 0.01)),
                  Vector((sx, -0.955, sz)),
                  Vector((sx, bujia.y + 0.035, sz)),
                  bujia + Vector((lado * 0.012, 0.0, 0.03)), bujia]
        m.tubo(puntos, 0.0038, "goma", lados=4)
        # Capuchón de la bujía
        m.cilindro(bujia, bujia + Vector((-lado * 0.02, 0, 0.02)), 0.008, "goma", lados=10)
    return m.objeto("cables-bujias", mats)


def alternador(mats):
    m = Malla(["aluminio", "negro"])
    c = ALTERNADOR
    m.cilindro(c + Vector((0, 0.055, 0)), c + Vector((0, -0.055, 0)), 0.085, "aluminio", lados=32)
    for dy in (-0.058, 0.0, 0.058):                         # costuras de la carcasa
        m.cilindro(c + Vector((0, dy - 0.004, 0)), c + Vector((0, dy + 0.004, 0)), 0.088, "aluminio", lados=32)
    m.cilindro(c + Vector((0, -0.06, 0)), c + Vector((0, -0.075, 0)), 0.07, "negro", lados=24)   # ventilador
    m.cilindro(c + Vector((0, -0.075, 0)), Vector((c.x, POLEAS_Y + 0.012, c.z)), 0.012, "aluminio", lados=12)
    # Soportes: arriba al múltiple, abajo a la bomba de agua
    m.caja((c.x - 0.10, c.y + 0.04, c.z + 0.02), (0.14, 0.012, 0.03), "negro", rot_y(-15))
    m.caja((c.x - 0.09, c.y + 0.03, c.z - 0.09), (0.10, 0.012, 0.03), "negro", rot_y(30))
    return m.objeto("alternador", mats)


POLEAS = [
    # (x, z, radio) en el plano de las poleas
    (0.0, CIG_Z, 0.085),            # cigüeñal (la que manda)
    (0.0, BOMBA_Z, 0.075),          # bomba de agua (y el ventilador)
    (ALTERNADOR.x, ALTERNADOR.z, 0.036),
]


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
    m = Malla(["negro", "goma"])
    for x, z, r in POLEAS:
        m.cilindro((x, POLEAS_Y + 0.012, z), (x, POLEAS_Y - 0.012, z), r, "negro", lados=40)
        m.cilindro((x, POLEAS_Y - 0.012, z), (x, POLEAS_Y - 0.018, z), r * 0.45, "negro", lados=20)
    # Balanceador del cigüeñal, entre la polea y el motor
    m.cilindro((0, POLEAS_Y + 0.012, CIG_Z), (0, BLOQUE_Y[0] - 0.035, CIG_Z), 0.075, "negro", lados=40)
    # La correa: abraza las tres poleas por afuera
    muestras = []
    for x, z, r in POLEAS:
        for k in range(48):
            a = 2 * math.pi * k / 48
            muestras.append((round(x + r * math.cos(a), 5), round(z + r * math.sin(a), 5)))
    camino = envolvente(muestras)
    n = len(camino)
    bm = m.bm
    anillos = []
    for k, p in enumerate(camino):
        prev, sig = camino[k - 1], camino[(k + 1) % n]
        tx, tz = sig[0] - prev[0], sig[1] - prev[1]
        largo = math.hypot(tx, tz) or 1.0
        nx, nz = tz / largo, -tx / largo                   # hacia afuera (camino antihorario)
        afuera = (p[0] + nx * 0.009, p[1] + nz * 0.009)
        anillos.append([bm.verts.new((q[0], POLEAS_Y + dy, q[1]))
                        for q, dy in ((p, -0.007), (afuera, -0.007), (afuera, 0.007), (p, 0.007))])
    nuevos = []
    for k in range(n):
        a, b = anillos[k], anillos[(k + 1) % n]
        for j in range(4):
            nuevos.append(bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j])))
    for f in nuevos:
        f.material_index = m.mats.index("goma")
    return m.objeto("correas", mats)


def ventilador(mats):
    m = Malla(["negro"])
    y = VENTILADOR_Y
    m.cilindro((0, POLEAS_Y - 0.018, BOMBA_Z), (0, y, BOMBA_Z), 0.03, "negro", lados=20)        # separador
    m.cilindro((0, y + 0.006, BOMBA_Z), (0, y - 0.006, BOMBA_Z), 0.065, "negro", lados=32)       # cubo
    # 4 palas con su ángulo (de serie: fijo de 4 palas)
    for k in range(4):
        giro = Matrix.Rotation(math.radians(45 + 90 * k), 4, "Y")
        paso = Matrix.Rotation(math.radians(28), 4, "X")
        pala = Matrix.Translation((0, y, BOMBA_Z)) @ giro @ Matrix.Translation((0.14, 0, 0)) @ paso
        m.caja(pala.to_translation(), (0.17, 0.004, 0.075), "negro", (giro @ paso).to_3x3().to_4x4())
    return m.objeto("ventilador", mats)


def carburador(mats):
    m = Malla(["zinc", "goma", "aluminio"])
    c = Vector((0, CARB_Y, BASE_CARB_Z))
    m.caja(c + Vector((0, 0, 0.004)), (0.15, 0.16, 0.008), "aluminio")                 # placa de abajo
    m.caja(c + Vector((0, 0.01, 0.037)), (0.13, 0.13, 0.058), "zinc")                   # cuerpo
    m.caja(c + Vector((0, -0.075, 0.03)), (0.11, 0.035, 0.045), "zinc")                  # cuba (adelante)
    m.caja(c + Vector((0, 0.0, 0.074)), (0.145, 0.165, 0.016), "zinc")                  # tapa de arriba
    # 4 bocas: dos chicas adelante, dos grandes atrás
    for x in (-0.028, 0.028):
        m.cilindro(c + Vector((x, -0.04, 0.081)), c + Vector((x, -0.04, 0.083)), 0.018, "goma", lados=20)
        m.cilindro(c + Vector((x, 0.035, 0.081)), c + Vector((x, 0.035, 0.083)), 0.03, "goma", lados=24)
    # Palanca del acelerador al costado y entrada de nafta adelante
    m.cilindro(c + Vector((0.065, 0.02, 0.025)), c + Vector((0.085, 0.02, 0.025)), 0.02, "aluminio", lados=16)
    m.cilindro(c + Vector((0.03, -0.09, 0.03)), c + Vector((0.03, -0.12, 0.03)), 0.008, "aluminio", lados=10)
    return m.objeto("carburador", mats, biselar=0.002)


def filtro_aire(mats):
    m = Malla(["cromo", "papel"])
    c = Vector((0, CARB_Y, BASE_CARB_Z + 0.085))           # apoya arriba del carburador
    r = FILTRO_RADIO
    m.cilindro(c, c + Vector((0, 0, 0.012)), r, "cromo", lados=64)                         # base
    m.cilindro(c + Vector((0, 0, 0.008)), c + Vector((0, 0, 0.004)), 0.06, "cromo", lados=32)   # cuello
    # El elemento de papel plegado, a la vista entre la base y la tapa
    bm = m.bm
    pliegues, alto, z0 = 72, 0.048, c.z + 0.012
    arriba, abajo = [], []
    for k in range(pliegues * 2):
        a = math.pi * k / pliegues
        rr = r - 0.010 if k % 2 == 0 else r - 0.016
        arriba.append(bm.verts.new((rr * math.cos(a), c.y + rr * math.sin(a), z0 + alto)))
        abajo.append(bm.verts.new((rr * math.cos(a), c.y + rr * math.sin(a), z0)))
    n = len(arriba)
    caras = [bm.faces.new((abajo[k], abajo[(k + 1) % n], arriba[(k + 1) % n], arriba[k])) for k in range(n)]
    for f in caras:
        f.material_index = m.mats.index("papel")
    # Tapa cromada con un poco de panza, el borde que baja y la mariposa del medio
    z1 = z0 + alto
    m.cilindro(Vector((0, c.y, z1 - 0.012)), Vector((0, c.y, z1 + 0.006)), r + 0.004, "cromo", lados=64)
    m.cilindro(Vector((0, c.y, z1 + 0.006)), Vector((0, c.y, z1 + 0.014)), r - 0.01, "cromo", r2=r - 0.09, lados=64)
    m.cilindro(Vector((0, c.y, z1 + 0.014)), Vector((0, c.y, z1 + 0.022)), 0.018, "cromo", lados=20)
    m.caja(Vector((0, c.y, z1 + 0.024)), (0.05, 0.006, 0.012), "cromo")
    return m.objeto("filtro-aire", mats)


def radiador(mats):
    m = Malla(["negro", "goma", "cromo"])
    y = RADIADOR_Y
    ancho, z0, z1 = 0.533, 0.34, 0.74                     # panal de 21″ de ancho
    m.caja((0, y, (z0 + z1) / 2), (ancho, 0.05, z1 - z0), "negro")
    # Las aletas (rayas finitas en la cara de atrás, la que se ve con el capot abierto)
    for k in range(18):
        z = z0 + 0.012 + k * (z1 - z0 - 0.024) / 17
        m.caja((0, y + 0.026, z), (ancho - 0.01, 0.003, 0.006), "goma")
    # Tanques a los costados, tapa arriba del izquierdo
    for lado in (1, -1):
        m.caja((lado * (ancho / 2 + 0.022), y, (z0 + z1) / 2), (0.044, 0.065, z1 - z0 + 0.04), "negro")
    m.cilindro((ancho / 2 + 0.022, y, z1 + 0.02), (ancho / 2 + 0.022, y, z1 + 0.035), 0.022, "cromo", lados=20)
    # Mangueras: arriba desde el termostato, abajo hacia la bomba de agua
    termostato = Vector((0, BLOQUE_Y[0] + 0.06 - 0.03, BASE_CARB_Z - 0.03))
    m.tubo([termostato, termostato + Vector((0.03, -0.06, 0.03)), Vector((0.21, -1.78, 0.715)),
            Vector((ancho / 2 + 0.01, y + 0.04, 0.70)), Vector((ancho / 2 + 0.02, y + 0.03, 0.70))],
           0.019, "goma", lados=12)
    entrada = Vector((-0.10, BLOQUE_Y[0] - 0.005 - 0.10, CIG_Z + 0.06))
    m.tubo([entrada, entrada + Vector((-0.02, -0.04, -0.04)), Vector((-0.27, -1.80, 0.30)),
            Vector((-ancho / 2 - 0.01, y + 0.04, 0.38)), Vector((-ancho / 2 - 0.02, y + 0.03, 0.38))],
           0.019, "goma", lados=12)
    return m.objeto("radiador", mats)


def bateria(mats):
    m = Malla(["negro", "aluminio", "goma"])
    largo, ancho, alto = 0.26, 0.17, 0.19           # 61 A·h, bornes arriba
    b = BATERIA
    m.caja(b + Vector((0, 0, -0.008)), (ancho + 0.03, largo + 0.03, 0.012), "negro")            # bandeja
    m.caja(b + Vector((0, 0, alto / 2)), (ancho, largo, alto), "negro")
    m.caja(b + Vector((0, 0, alto + 0.004)), (ancho - 0.01, largo - 0.01, 0.008), "goma")       # tapa
    for k in range(6):
        y = b.y - largo / 2 + 0.03 + k * (largo - 0.06) / 5
        m.cilindro((b.x, y, alto + b.z + 0.008), (b.x, y, alto + b.z + 0.016), 0.012, "negro", lados=12)
    # Bornes: hacia atrás, el positivo del lado del guardabarros
    for dx in (0.055, -0.055):
        p = Vector((b.x + dx, b.y + largo / 2 - 0.03, b.z + alto + 0.008))
        m.cilindro(p, p + Vector((0, 0, 0.022)), 0.011, "aluminio", r2=0.009, lados=14)
    # Sujeción de arriba
    m.caja((b.x, b.y, b.z + alto + 0.012), (ancho + 0.02, 0.025, 0.006), "negro")
    return m.objeto("bateria", mats, biselar=0.004)


# ----------------------------------------------------------------------------------------------
# Todo junto
# ----------------------------------------------------------------------------------------------
PIEZAS = [
    ("bloque", bloque), ("tapas-cilindros", tapas_cilindros), ("carter", carter),
    ("multiple-admision", multiple_admision), ("tapas-valvulas", tapas_valvulas),
    ("multiples-escape", multiples_escape), ("bomba-agua", bomba_agua), ("motor-arranque", motor_arranque),
    ("distribuidor", distribuidor), ("bobina", bobina), ("cables-bujias", cables_bujias),
    ("alternador", alternador), ("correas", correas), ("ventilador", ventilador),
    ("carburador", carburador), ("filtro-aire", filtro_aire), ("radiador", radiador), ("bateria", bateria),
]


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
        export_texcoords=False,          # no hay texturas
        export_normals=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
        export_animations=False,
        export_draco_mesh_compression_enable=False,   # la compresión la hace el cierre (Agente 7)
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
