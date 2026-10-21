"""
Todo lo de afuera del Camaro SS 1968, hecho por script: paragolpes, parrilla, faros, luces,
emblemas, tapa de la nafta, llantas Rally con sus cubiertas, vidrios, espejo, manijas e interior.

Se corre con el Blender portátil, sin abrir la ventana (ver blender/LEEME.md):
    blender -b -P blender/exterior.py
Genera modelos/exterior.glb (o la ruta que vaya después de «--»).

Cómo está armado:
1. Arma la carrocería de blender/carroceria.py en la escena, SOLO para medir (no se exporta).
2. Cada pieza se apoya en la chapa «tirándole rayos»: así los paragolpes siguen la forma del frente
   y de la cola, las luces quedan pegadas al panel y la parrilla va en el fondo de su hueco.
3. Los vidrios salen de los mismos huecos que la carrocería les dejó, con un filete cromado.
4. Exporta solo lo de acá, con los nombres de datos/fichas.json:
     paragolpes-delantero, paragolpes-trasero, parrilla, tapa-nafta, espejo (objetos sueltos)
     faros, luces-posicion, luces-traseras, emblemas-ss, llantas-rally, vidrios (grupos: un objeto
     vacío con el id de la ficha y adentro cada pieza, con los nombres de «piezas3d»).
   Lo que no tiene ficha (interior, faldones, luces de estacionamiento, manijas…) va con nombres
   que no chocan con ninguna ficha: se ve, pero no se toca.

Lo que se mueve con las puertas (ventanillas, espejo y manijas) tiene el origen en la misma bisagra
que la puerta: modelos/manifiesto.json lo gira junto con ella.

Ejes en Blender: X = ancho (+X = lado izquierdo, el del conductor), Y = largo (el frente mira a -Y),
Z = arriba. Metros. Al exportar: arriba = +Y y el frente mira a +Z (como la carrocería).
"""

import importlib.util
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

AQUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("carroceria", os.path.join(AQUI, "carroceria.py"))
car = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(car)

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

# Bisagra de las puertas (la misma que usa carroceria.py)
Y_BISAGRA = car.PUERTA_Y[0] + car.RANURA
BISAGRA_IZQ = Vector((car.LADO_X(Y_BISAGRA) - 0.01, Y_BISAGRA, 0.55))
BISAGRA_DER = Vector((-BISAGRA_IZQ.x, Y_BISAGRA, 0.55))
GRADOS_PUERTA = {"izq": -62, "der": 62}     # en los ejes de Three.js (como la carrocería)


# ----------------------------------------------------------------------------------------------
# Materiales
# ----------------------------------------------------------------------------------------------
def material(nombre, color, rugosidad, metal=0.0, alfa=1.0, barniz=0.0):
    if isinstance(color, str):
        color = car.srgb_a_lineal(color)
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = color
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rugosidad
    p.inputs["Coat Weight"].default_value = barniz
    if barniz:
        p.inputs["Coat Roughness"].default_value = 0.04
    if alfa < 1.0:
        p.inputs["Alpha"].default_value = alfa
        m.surface_render_method = "BLENDED"
    m.use_backface_culling = False
    m.diffuse_color = color
    return m


def materiales():
    return {
        "cromo": material("cromo", (0.92, 0.92, 0.93, 1), 0.08, metal=1.0),
        "plata": material("plata_parrilla", "#b9bcbf", 0.32, metal=0.9),
        "gris_rally": material("gris_rally", "#7d8184", 0.38, metal=0.65),
        "goma": material("goma", "#1a1a1b", 0.88),
        "negro_mate": material("negro_mate_ext", (0.012, 0.012, 0.013, 1), 0.85),
        "parrilla": material("negro_parrilla", (0.010, 0.010, 0.011, 1), 0.55),
        "pintura": material("pintura_negra_ext", (0.006, 0.006, 0.007, 1), 0.22, barniz=1.0),
        "vidrio": material("vidrio_soft_ray", "#0f1715", 0.06, alfa=0.5),
        "lente_faro": material("lente_faro", "#dfe6ea", 0.05, alfa=0.35),
        "ambar": material("lente_ambar", "#e5881c", 0.28),
        "rojo": material("lente_rojo", "#a3121a", 0.25),
        "blanco": material("lente_blanco", "#ecebe6", 0.22),
        "vinilo": material("vinilo_negro", "#151617", 0.5),
        "alfombra": material("alfombra_negra", "#111112", 1.0),
        "tablero": material("tablero_negro", "#121314", 0.62),
    }


# ----------------------------------------------------------------------------------------------
# Una pieza = una malla en armado (bmesh) con su lista de materiales
# ----------------------------------------------------------------------------------------------
class Pieza:
    def __init__(self, nombre, mats):
        self.nombre = nombre
        self.mats = mats
        self.usados = []
        self.bm = bmesh.new()

    def m(self, clave):
        """Índice del material 'clave' en esta pieza (lo suma si hace falta)."""
        if clave not in self.usados:
            self.usados.append(clave)
        return self.usados.index(clave)

    def caras_nuevas(self, desde, clave):
        self.bm.faces.ensure_lookup_table()
        indice = self.m(clave)
        for f in self.bm.faces[desde:]:
            f.material_index = indice

    def objeto(self, origen=(0, 0, 0), padre=None, angulo_suave=34):
        malla = bpy.data.meshes.new(self.nombre)
        self.bm.normal_update()
        self.bm.to_mesh(malla)
        self.bm.free()
        obj = bpy.data.objects.new(self.nombre, malla)
        bpy.context.scene.collection.objects.link(obj)
        for clave in self.usados:
            obj.data.materials.append(self.mats[clave])
        origen = Vector(origen)
        if origen.length:
            obj.data.transform(Matrix.Translation(-origen))
            obj.location = origen
        if padre is not None:
            obj.parent = padre
        with bpy.context.temp_override(selected_editable_objects=[obj], active_object=obj, object=obj):
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angulo_suave))
        return obj


def grupo(nombre, ficha=None):
    """Objeto vacío que agrupa varias piezas de una misma ficha (ej.: los dos faros)."""
    e = bpy.data.objects.new(nombre, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.1
    bpy.context.scene.collection.objects.link(e)
    if ficha:
        e["id"] = ficha
    return e


def marco(origen, normal, arriba=Z):
    """Matriz con columnas (u, v, n): u = a la derecha de quien mira la pieza de frente,
    v = arriba, n = hacia afuera de la superficie. Sirve para apoyar cosas sobre la chapa."""
    n = Vector(normal).normalized()
    u = arriba.cross(n)
    if u.length < 1e-4:
        u = Y.cross(n)
    u.normalize()
    v = n.cross(u).normalized()
    m = Matrix((u, v, n)).transposed().to_4x4()
    m.translation = Vector(origen)
    return m


# ----------------------------------------------------------------------------------------------
# Formas básicas (todas en coordenadas de un marco)
# ----------------------------------------------------------------------------------------------
def caja(p, clave, M, x0, x1, y0, y1, z0, z1, clave_frente=None, cara_frente=1, bisel=0.0, seg=2):
    """Caja en el marco M. Una cara puede llevar otro material: 'cara_frente' 1 = la +Z local
    (la de afuera en un marco), 2 = la -Y local."""
    bm = p.bm
    c = [bm.verts.new(M @ Vector((x, y, z))) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    caras = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    nuevas = []
    for k, idx in enumerate(caras):
        f = bm.faces.new([c[i] for i in idx])
        f.material_index = p.m(clave_frente if (k == cara_frente and clave_frente) else clave)
        nuevas.append(f)
    if bisel:
        aristas = list({e for f in nuevas for e in f.edges})
        bmesh.ops.bevel(bm, geom=aristas, offset=bisel, segments=seg, profile=0.5, affect="EDGES",
                        clamp_overlap=True)
    return nuevas


def revolver(p, perfil, claves, M, segmentos=40, saltar=None, suave=True):
    """Gira un perfil [(radio, altura)] alrededor del eje Z local. 'claves' = un material o uno por
    tramo. 'saltar(tramo, segmento)' deja huecos (las ranuras de la llanta Rally)."""
    bm = p.bm
    anillos = []
    for r, a in perfil:
        if r < 1e-6:
            anillos.append([bm.verts.new(M @ Vector((0, 0, a)))] * segmentos)
            continue
        anillos.append([bm.verts.new(M @ Vector((r * math.cos(2 * math.pi * k / segmentos),
                                                 r * math.sin(2 * math.pi * k / segmentos), a)))
                        for k in range(segmentos)])
    for j in range(len(perfil) - 1):
        clave = claves if isinstance(claves, str) else claves[j]
        for k in range(segmentos):
            if saltar and saltar(j, k):
                continue
            k2 = (k + 1) % segmentos
            vs = [anillos[j][k], anillos[j][k2], anillos[j + 1][k2], anillos[j + 1][k]]
            sin_rep = []
            for v in vs:
                if v not in sin_rep:
                    sin_rep.append(v)
            if len(sin_rep) < 3:
                continue
            f = bm.faces.new(sin_rep)
            f.material_index = p.m(clave)
            f.smooth = suave
    return anillos


def barrer(p, puntos, normales, perfil, clave, tapar=True):
    """Pasa un perfil cerrado [(d hacia afuera, h hacia arriba)] a lo largo de un camino."""
    bm = p.bm
    filas = []
    for q, n in zip(puntos, normales):
        filas.append([bm.verts.new(q + n * d + Z * h) for d, h in perfil])
    m = len(perfil)
    for a, b in zip(filas, filas[1:]):
        for k in range(m):
            k2 = (k + 1) % m
            f = bm.faces.new((a[k], a[k2], b[k2], b[k]))
            f.material_index = p.m(clave)
            f.smooth = True
    if tapar:
        for fila in (filas[0], filas[-1]):
            f = bm.faces.new(fila)
            f.material_index = p.m(clave)
    return filas


def texto(p, cuerpo, tamano, alto, M, clave, inclinacion=0.18):
    """Letras de verdad (fuente de Blender) en relieve, apoyadas en el plano XY del marco M."""
    cu = bpy.data.curves.new("letras", "FONT")
    cu.body = cuerpo
    cu.size = tamano
    cu.extrude = alto / 2
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.shear = inclinacion
    cu.resolution_u = 3
    ob = bpy.data.objects.new("letras", cu)
    bpy.context.scene.collection.objects.link(ob)
    deps = bpy.context.evaluated_depsgraph_get()
    malla = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.curves.remove(cu)
    malla.transform(M @ Matrix.Translation((0, 0, alto / 2)))
    p.bm.faces.ensure_lookup_table()
    desde = len(p.bm.faces)
    p.bm.from_mesh(malla)
    bpy.data.meshes.remove(malla)
    p.caras_nuevas(desde, clave)


def placa(p, clave, M, ancho, alto, espesor, radio=0.0, pasos=4, hundir=0.004):
    """Placa plana de esquinas redondeadas sobre el marco M (se hunde un poco en la chapa)."""
    contorno = []
    r = min(radio, ancho / 2, alto / 2)
    if r <= 0:
        contorno = [(-ancho / 2, -alto / 2), (ancho / 2, -alto / 2), (ancho / 2, alto / 2), (-ancho / 2, alto / 2)]
    else:
        for cx, cy, a0 in ((ancho / 2 - r, -alto / 2 + r, -90), (ancho / 2 - r, alto / 2 - r, 0),
                           (-ancho / 2 + r, alto / 2 - r, 90), (-ancho / 2 + r, -alto / 2 + r, 180)):
            for k in range(pasos + 1):
                a = math.radians(a0 + 90 * k / pasos)
                contorno.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    bm = p.bm
    atras = [bm.verts.new(M @ Vector((x, y, -hundir))) for x, y in contorno]
    frente = [bm.verts.new(M @ Vector((x, y, espesor))) for x, y in contorno]
    n = len(contorno)
    caras = [bm.faces.new(frente), bm.faces.new(list(reversed(atras)))]
    for k in range(n):
        k2 = (k + 1) % n
        caras.append(bm.faces.new((atras[k], atras[k2], frente[k2], frente[k])))
    for f in caras:
        f.material_index = p.m(clave)
    return caras


# ----------------------------------------------------------------------------------------------
# Medir la chapa con rayos
# ----------------------------------------------------------------------------------------------
class Chapa:
    def __init__(self, objetos):
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        self.arboles = []
        for o in objetos:
            mw = o.matrix_world.copy()
            self.arboles.append((BVHTree.FromObject(o, deps), mw, mw.inverted()))

    def rayo(self, origen, direccion, largo=10.0):
        """Primer punto de la chapa en esa dirección: (punto, normal mirando hacia el rayo)."""
        origen, direccion = Vector(origen), Vector(direccion).normalized()
        mejor = None
        for arbol, mw, inv in self.arboles:
            o = inv @ origen
            d = (inv.to_3x3() @ direccion).normalized()
            punto, normal, _, _ = arbol.ray_cast(o, d, largo)
            if punto is None:
                continue
            punto = mw @ punto
            dist = (punto - origen).length
            if mejor is None or dist < mejor[2]:
                n = (inv.transposed().to_3x3() @ normal).normalized()
                if n.dot(direccion) > 0:
                    n = -n
                mejor = (punto, n, dist)
        return (mejor[0], mejor[1]) if mejor else (None, None)

    def desde_afuera(self, punto, direccion_hacia_adentro):
        """Apunta desde 1 m afuera hacia 'punto' y devuelve dónde toca la chapa."""
        d = Vector(direccion_hacia_adentro).normalized()
        return self.rayo(Vector(punto) - d, d, 2.0)


def suavizar_camino(puntos, normales, vueltas=2):
    for _ in range(vueltas):
        puntos = [puntos[0]] + [(puntos[i - 1] + puntos[i] * 2 + puntos[i + 1]) / 4
                                for i in range(1, len(puntos) - 1)] + [puntos[-1]]
        normales = [normales[0]] + [(normales[i - 1] + normales[i] * 2 + normales[i + 1]).normalized()
                                    for i in range(1, len(normales) - 1)] + [normales[-1]]
    return puntos, normales


def contorno_plano(chapa, centro, z, adelante, hasta_y, separacion):
    """Recorre el frente (adelante=-1) o la cola (+1) a la altura z, de un costado al otro, y
    devuelve el camino un poco afuera de la chapa, con sus normales horizontales."""
    puntos, normales = [], []
    for k in range(-86, 87, 2):
        a = math.radians(k)
        d = Vector((math.sin(a), adelante * math.cos(a), 0))
        q, n = chapa.rayo(Vector((0, centro, z)), d, 3.0)
        if q is None:
            continue
        if (adelante < 0 and q.y > hasta_y) or (adelante > 0 and q.y < hasta_y):
            continue
        n = -n                       # el rayo sale de adentro: la normal buena apunta afuera
        n.z = 0
        n.normalize()
        puntos.append(q + n * separacion)
        normales.append(n)
    return suavizar_camino(puntos, normales, 3)


# ----------------------------------------------------------------------------------------------
# Paragolpes, faldones y luces de estacionamiento
# ----------------------------------------------------------------------------------------------
PERFIL_PARAGOLPES = [(0.0, 0.050), (0.020, 0.058), (0.042, 0.053), (0.056, 0.036), (0.061, 0.012),
                     (0.060, -0.022), (0.052, -0.043), (0.032, -0.055), (0.0, -0.052)]
# El faldón: chapa pintada, metida abajo del paragolpes (de 0,25 a 0,33 m del piso)
PERFIL_FALDON = [(-0.030, 0.125), (-0.004, 0.120), (0.004, 0.100), (0.002, 0.060), (-0.008, 0.045),
                 (-0.030, 0.048)]


def paragolpes(mats, chapa, adelante):
    if adelante < 0:
        nombre, z, centro, hasta = "paragolpes-delantero", 0.37, -1.75, -2.115
    else:
        nombre, z, centro, hasta = "paragolpes-trasero", 0.43, 1.80, 2.165
    puntos, normales = contorno_plano(chapa, centro, z, adelante, hasta, 0.022)
    p = Pieza(nombre, mats)
    barrer(p, [q + Z * 0 for q in puntos], normales, PERFIL_PARAGOLPES, "cromo")
    # Los soportes de atrás (se ven por abajo)
    for s in (1, -1):
        i = min(range(len(puntos)), key=lambda i: abs(puntos[i].x - s * 0.45))
        M = marco(puntos[i] - Z * 0.02, -normales[i])
        caja(p, "negro_mate", M, -0.03, 0.03, -0.025, 0.025, -0.002, 0.05)
    obj = p.objeto(origen=puntos[len(puntos) // 2])
    obj["id"] = nombre

    # El faldón pintado de abajo, con las luces de estacionamiento ovaladas del 68 adelante
    faldon = Pieza("faldon-delantero" if adelante < 0 else "faldon-trasero", mats)
    medio = [i for i, q in enumerate(puntos) if abs(q.x) < 0.80]
    pf = [puntos[i] - Z * 0.165 - normales[i] * 0.012 for i in medio]
    nf = [normales[i] for i in medio]
    barrer(faldon, pf, nf, PERFIL_FALDON, "pintura")
    extras = [faldon.objeto()]
    if adelante < 0:
        luces = Pieza("luces-estacionamiento", mats)
        for s in (1, -1):
            i = min(range(len(pf)), key=lambda i: abs(pf[i].x - s * 0.42))
            M = marco(pf[i] + Z * 0.085 + nf[i] * 0.004, nf[i]) @ Matrix.Diagonal((1.0, 0.36, 1.0, 1.0))
            revolver(luces, [(0.0, 0.010), (0.045, 0.008), (0.052, 0.002), (0.055, -0.006)], "cromo",
                     M, segmentos=24)
            revolver(luces, [(0.0, 0.013), (0.040, 0.010), (0.045, 0.008)], "ambar", M, segmentos=24)
        extras.append(luces.objeto())
    return obj, extras


# ----------------------------------------------------------------------------------------------
# Parrilla y faros (en el hueco del frente)
# ----------------------------------------------------------------------------------------------
HUECO_X = 0.745
HUECO_Z = (0.412, 0.690)


def fondo_hueco(chapa, x, z):
    q, _ = chapa.desde_afuera(Vector((x, -2.6, z)), Y)
    return q.y if q is not None else -2.13


def parrilla(mats, chapa):
    p = Pieza("parrilla", mats)
    xs = [-HUECO_X + 2 * HUECO_X * k / 24 for k in range(25)]
    zs = [HUECO_Z[0] + (HUECO_Z[1] - HUECO_Z[0]) * k / 6 for k in range(7)]
    fondo = {(i, j): fondo_hueco(chapa, x, z) for i, x in enumerate(xs) for j, z in enumerate(zs)}

    def y_fondo(x, z):
        i = min(range(len(xs)), key=lambda i: abs(xs[i] - x))
        j = min(range(len(zs)), key=lambda j: abs(zs[j] - z))
        return fondo[(i, j)]

    # Fondo de malla negra
    bm = p.bm
    grilla = [[bm.verts.new((x, fondo[(i, j)] - 0.003, z)) for j, z in enumerate(zs)] for i, x in enumerate(xs)]
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            f = bm.faces.new((grilla[i][j], grilla[i + 1][j], grilla[i + 1][j + 1], grilla[i][j + 1]))
            f.material_index = p.m("parrilla")

    # Rejilla: barras horizontales con el filo plateado (el 68) y verticales negras
    n_h = 10
    tramos = xs[::3]     # las barras van en tramos rectos de 18 cm, siguiendo la punta
    for k in range(n_h):
        z = HUECO_Z[0] + 0.012 + (HUECO_Z[1] - HUECO_Z[0] - 0.024) * k / (n_h - 1)
        for x0, x1 in zip(tramos, tramos[1:]):
            y = (y_fondo(x0, z) + y_fondo(x1, z)) / 2
            # Barra negra con el filo de adelante plateado
            caja(p, "parrilla", Matrix.Translation((0, y, z)), x0, x1, -0.035, -0.004, -0.0035, 0.0035,
                 clave_frente="plata", cara_frente=2)
    for k in range(33):
        x = -HUECO_X + 0.01 + (2 * HUECO_X - 0.02) * k / 32
        y = y_fondo(x, 0.55)
        caja(p, "parrilla", Matrix.Translation((x, y, 0)), -0.0025, 0.0025, -0.026, -0.004,
             HUECO_Z[0], HUECO_Z[1])
    # Marco cromado finito arriba y abajo
    for z in HUECO_Z:
        for x0, x1 in zip(tramos, tramos[1:]):
            y = y_fondo((x0 + x1) / 2, z)
            caja(p, "cromo", Matrix.Translation((0, y, z)), x0, x1, -0.040, -0.004, -0.006, 0.006)
    obj = p.objeto(origen=(0, y_fondo(0, 0.55), 0.55))
    obj["id"] = "parrilla"
    frente_centro = y_fondo(0, 0.55) - 0.036
    return obj, frente_centro


def faros(mats, chapa):
    g = grupo("faros", "faros")
    for lado, s in (("izq", 1), ("der", -1)):
        x, z = s * 0.615, 0.551
        y = fondo_hueco(chapa, x, z)
        p = Pieza(f"faro-{lado}", mats)
        M = marco(Vector((x, y, z)), -Y)
        # Taza de atrás (reflector), aro cromado y vidrio abombado de 7″
        revolver(p, [(0.0, 0.004), (0.05, 0.010), (0.082, 0.028), (0.090, 0.040)], "cromo", M)
        revolver(p, [(0.084, 0.040), (0.112, 0.040), (0.114, 0.050), (0.106, 0.064), (0.094, 0.068),
                     (0.086, 0.064)], "cromo", M)
        revolver(p, [(0.088, 0.054), (0.07, 0.066), (0.04, 0.073), (0.0, 0.075)], "lente_faro", M)
        # Las rayitas del vidrio (los prismas del faro sellado), apenas marcadas
        for k in range(-3, 4):
            ancho = math.sqrt(max(0.0, 0.07 ** 2 - (k * 0.018) ** 2))
            caja(p, "lente_faro", M, -ancho, ancho, k * 0.018 - 0.0015, k * 0.018 + 0.0015, 0.050, 0.068)
        p.objeto(origen=(x, y - 0.05, z), padre=g)
    return g


# ----------------------------------------------------------------------------------------------
# Luces de los costados, luces traseras y tapa de la nafta
# ----------------------------------------------------------------------------------------------
def marcador(p, chapa, y, z, largo, alto, clave_lente, lado):
    q, n = chapa.desde_afuera(Vector((lado * 0.95, y, z)), -lado * X)
    M = marco(q, n)
    placa(p, "cromo", M, largo + 0.012, alto + 0.012, 0.004, radio=0.008, hundir=0.012)
    placa(p, clave_lente, M, largo, alto, 0.008, radio=0.005, hundir=0.0)


def luces_posicion(mats, chapa):
    g = grupo("luces-posicion", "luces-posicion")
    for lado, s in (("izq", 1), ("der", -1)):
        p = Pieza(f"luz-posicion-{lado}", mats)
        marcador(p, chapa, -2.00, 0.425, 0.125, 0.040, "ambar", s)
        p.objeto(origen=(s * 0.86, -2.00, 0.425), padre=g)
    # Las rojas de atrás (también son del 68; no tienen ficha)
    p = Pieza("marcadores-traseros", mats)
    for s in (1, -1):
        marcador(p, chapa, 1.94, 0.475, 0.110, 0.034, "rojo", s)
    return g, p.objeto()


def luces_traseras(mats, chapa):
    g = grupo("luces-traseras", "luces-traseras")
    for lado, s in (("izq", 1), ("der", -1)):
        p = Pieza(f"luz-trasera-{lado}", mats)
        cx, cz = s * 0.44, 0.705
        q, n = chapa.desde_afuera(Vector((cx, 2.6, cz)), -Y)
        M = marco(q, n)
        ancho, alto = 0.50, 0.165
        placa(p, "cromo", M, ancho, alto, 0.008, radio=0.014, hundir=0.014)
        # En el 68 cada luz está partida en dos; la de adentro tiene abajo la marcha atrás
        for mitad in (-1, 1):
            u0 = mitad * 0.0065 + (mitad * ancho / 4 - 0.0035 * mitad)
            M2 = M @ Matrix.Translation((u0, 0, 0))
            adentro = (mitad * s) > 0     # la mitad que da al centro (mirando de atrás, u = -X)
            if adentro:
                placa(p, "rojo", M2 @ Matrix.Translation((0, 0.022, 0)), ancho / 2 - 0.03, alto - 0.07,
                      0.012, radio=0.006, hundir=0.0)
                placa(p, "blanco", M2 @ Matrix.Translation((0, -0.052, 0)), ancho / 2 - 0.03, 0.036,
                      0.012, radio=0.006, hundir=0.0)
            else:
                placa(p, "rojo", M2, ancho / 2 - 0.03, alto - 0.03, 0.012, radio=0.008, hundir=0.0)
            # Rayas horizontales cromadas sobre el vidrio
            for k in (-1, 0, 1):
                caja(p, "cromo", M2, -(ancho / 4 - 0.02), ancho / 4 - 0.02, k * 0.032 - 0.002 + (0.022 if adentro else 0),
                     k * 0.032 + 0.002 + (0.022 if adentro else 0), 0.010, 0.015)
        p.objeto(origen=q, padre=g)
    return g


def tapa_nafta(mats, chapa):
    p = Pieza("tapa-nafta", mats)
    q, n = chapa.desde_afuera(Vector((0, 2.6, 0.705)), -Y)
    M = marco(q, n)
    placa(p, "cromo", M, 0.150, 0.092, 0.010, radio=0.03, pasos=6, hundir=0.012)
    placa(p, "negro_mate", M @ Matrix.Translation((0, 0, 0.010)), 0.128, 0.070, 0.002, radio=0.022,
          pasos=6, hundir=0.0)
    texto(p, "SS", 0.062, 0.004, M @ Matrix.Translation((0, 0, 0.012)), "cromo")
    obj = p.objeto(origen=q)
    obj["id"] = "tapa-nafta"
    return obj


# ----------------------------------------------------------------------------------------------
# Emblemas SS (parrilla y guardabarros delanteros)
# ----------------------------------------------------------------------------------------------
def emblemas(mats, chapa, frente_parrilla):
    g = grupo("emblemas-ss", "emblemas-ss")
    p = Pieza("emblema-parrilla", mats)
    q = Vector((0, frente_parrilla - 0.002, 0.555))
    M = marco(q, -Y)
    placa(p, "rojo", M, 0.120, 0.058, 0.006, radio=0.010, hundir=0.004)
    placa(p, "cromo", M, 0.128, 0.066, 0.003, radio=0.012, hundir=0.004)
    texto(p, "SS", 0.058, 0.004, M @ Matrix.Translation((0, 0, 0.006)), "cromo")
    p.objeto(origen=q, padre=g)
    for lado, s in (("izq", 1), ("der", -1)):
        p = Pieza(f"emblema-guardabarros-{lado}", mats)
        q, n = chapa.desde_afuera(Vector((s * 0.95, -0.86, 0.60)), -s * X)
        M = marco(q, n)
        texto(p, "SS", 0.070, 0.005, M @ Matrix.Translation((0, 0, -0.001)), "cromo")
        texto(p, "350", 0.032, 0.004, M @ Matrix.Translation((0, -0.040, -0.001)), "cromo", 0.1)
        p.objeto(origen=q, padre=g)
    return g


# ----------------------------------------------------------------------------------------------
# Llantas Rally de 14″ con sus cubiertas
# ----------------------------------------------------------------------------------------------
CUBIERTA = [(0.185, -0.092), (0.235, -0.104), (0.292, -0.106), (0.318, -0.098), (0.330, -0.072),
            (0.332, 0.0), (0.330, 0.072), (0.318, 0.098), (0.292, 0.106), (0.235, 0.104),
            (0.185, 0.092)]
# Llanta: aro cromado, plato gris con 5 ranuras, centro con la tapa acanalada del 68
ARO = [(0.183, 0.092), (0.186, 0.099), (0.180, 0.104), (0.166, 0.098), (0.152, 0.088)]
PLATO = [(0.152, 0.088), (0.140, 0.082), (0.124, 0.078), (0.100, 0.076), (0.084, 0.080), (0.068, 0.084)]
TAPA = [(0.066, 0.084), (0.060, 0.092), (0.052, 0.100), (0.036, 0.106), (0.0, 0.110)]


def llanta(p, M):
    revolver(p, CUBIERTA, "goma", M, segmentos=44)
    revolver(p, ARO, "cromo", M, segmentos=44)
    # Ranuras: 5 huecos entre los radios 0,10 y 0,14, de 7 segmentos de 44 cada uno
    ranura = lambda j, k: j in (1, 2) and (k % 9) < 3
    revolver(p, PLATO, "gris_rally", M, segmentos=45, saltar=ranura)
    revolver(p, TAPA, "cromo", M, segmentos=30)
    # Lo de atrás de las ranuras (el tambor del freno), oscuro
    revolver(p, [(0.0, 0.040), (0.150, 0.040), (0.150, 0.070)], "negro_mate", M, segmentos=30)
    # Tuercas
    for k in range(5):
        a = 2 * math.pi * (k + 0.5) / 5
        Mt = M @ Matrix.Translation((0.075 * math.cos(a), 0.075 * math.sin(a), 0.084))
        revolver(p, [(0.0, 0.016), (0.009, 0.014), (0.010, 0.0)], "cromo", Mt, segmentos=6, suave=False)
    # Las rayitas de la tapa
    for k in range(12):
        a = 2 * math.pi * k / 12
        Mr = M @ Matrix.Rotation(a, 4, "Z")
        caja(p, "negro_mate", Mr, 0.040, 0.060, -0.0015, 0.0015, 0.090, 0.101)


def llantas(mats):
    g = grupo("llantas-rally", "llantas-rally")
    for nombre, eje_y, trocha in (("del", car.EJE_DEL_Y, car.TROCHA_DEL), ("tras", car.EJE_TRAS_Y, car.TROCHA_TRAS)):
        for lado, s in (("izq", 1), ("der", -1)):
            centro = Vector((s * trocha / 2, eje_y, car.RADIO_RUEDA))
            p = Pieza(f"llanta-{nombre}-{lado}", mats)
            llanta(p, marco(centro, s * X))
            p.objeto(origen=centro, padre=g, angulo_suave=40)
    return g


# ----------------------------------------------------------------------------------------------
# Vidrios: salen de los mismos huecos que dejó la carrocería
# ----------------------------------------------------------------------------------------------
def caras_de_vidrio(bm):
    """Repite el corte de carroceria.abrir_vidrios() y devuelve {nombre: [índices de caras]}."""
    capa_j = bm.verts.layers.float["j"]
    p0, p1 = Vector((0.0, 0.98, 0.92)), Vector((0.0, 0.52, 1.22))
    corte_atras = Vector((0.0, p1.z - p0.z, -(p1.y - p0.y))).normalized()
    car.cortar(bm, p0, corte_atras, lambda f, c: car.j_de_cara(f, capa_j)[0] >= car.J_VIDRIO_BASE - 1)
    # La ventanilla de la puerta termina donde termina la puerta
    y_corte = car.PUERTA_Y[1] - car.RANURA / 2
    car.cortar(bm, Vector((0, y_corte, 0)), Y,
               lambda f, c: car.j_de_cara(f, capa_j)[0] >= car.J_VIDRIO_BASE - 1 and abs(c.x) > 0.3)
    bm.faces.index_update()
    zonas = {k: [] for k in ("parabrisas", "luneta", "ventanilla-izq", "ventanilla-der",
                             "ventanilla-tras-izq", "ventanilla-tras-der")}
    for f in bm.faces:
        c = f.calc_center_median()
        jmin, jmax = car.j_de_cara(f, capa_j)
        if jmin >= car.J_TECHO_BORDE and car.CUBRE_Y < c.y < car.TECHO_Y[0]:
            zonas["parabrisas"].append(f.index)
        elif jmin >= car.J_LUNETA and car.TECHO_Y[1] < c.y < car.LUNETA_Y:
            zonas["luneta"].append(f.index)
        elif (jmin >= car.J_VIDRIO_BASE and jmax <= car.J_VENTANA_ARRIBA and c.y > car.VENTANA_Y0
              and (c - p0).dot(corte_atras) < 0 and c.y < 1.1):
            lado = "izq" if c.x > 0 else "der"
            zonas[f"ventanilla-{lado}" if c.y < y_corte else f"ventanilla-tras-{lado}"].append(f.index)
    return zonas


def vidrio(nombre, bm, indices, mats, origen=(0, 0, 0), padre=None):
    copia = bm.copy()
    copia.faces.index_update()
    quedarse = set(indices)
    bmesh.ops.delete(copia, geom=[f for f in copia.faces if f.index not in quedarse], context="FACES")
    bmesh.ops.delete(copia, geom=[v for v in copia.verts if not v.link_faces], context="VERTS")
    copia.verts.layers.float.remove(copia.verts.layers.float["j"])
    vidrio_caras = list(copia.faces)
    # Filete cromado de 1,4 cm alrededor y el vidrio un poco hundido
    filete = bmesh.ops.inset_region(copia, faces=vidrio_caras, thickness=0.014, depth=0.0)["faces"]
    copia.normal_update()
    adentro = {v for f in vidrio_caras for v in f.verts}
    normales = {v: v.normal.copy() for v in adentro}
    for v in adentro:
        v.co -= normales[v] * 0.006
    p = Pieza(nombre, mats)
    p.bm.free()
    p.bm = copia
    for f in copia.faces:
        f.material_index = p.m("cromo") if f in filete else p.m("vidrio")
    # El orden de los materiales tiene que coincidir con los índices puestos
    return p.objeto(origen=origen, padre=padre)


def vidrios(mats):
    bm = car.malla_chapa()
    zonas = caras_de_vidrio(bm)
    g = grupo("vidrios", "vidrios")
    for nombre, indices in zonas.items():
        if not indices:
            print(f"Ojo: no encontré caras para {nombre}")
            continue
        origen = (0, 0, 0)
        if nombre == "ventanilla-izq":
            origen = BISAGRA_IZQ
        elif nombre == "ventanilla-der":
            origen = BISAGRA_DER
        obj = vidrio(nombre, bm, indices, mats, origen=origen, padre=g)
        if nombre in ("ventanilla-izq", "ventanilla-der"):
            lado = nombre.split("-")[1]
            obj["abre_eje"] = "y"
            obj["abre_grados"] = GRADOS_PUERTA[lado]
    bm.free()
    return g


# ----------------------------------------------------------------------------------------------
# Espejo y manijas (van con la puerta)
# ----------------------------------------------------------------------------------------------
def espejo(mats, chapa):
    p = Pieza("espejo", mats)
    q, n = chapa.desde_afuera(Vector((0.95, -0.47, 0.835)), -X)
    base = marco(q, n)
    placa(p, "cromo", base, 0.060, 0.030, 0.010, radio=0.012, hundir=0.006)
    # Brazo hacia afuera y arriba
    brazo = q + n * 0.010
    cabeza = q + n * 0.075 + Z * 0.06
    eje = (cabeza - brazo)
    Mb = marco(brazo, eje)
    revolver(p, [(0.010, 0.0), (0.008, eje.length * 0.6), (0.007, eje.length)], "cromo", Mb, segmentos=12)
    # Cabeza cuadrada (el 68 pasó de redondo a cuadrado), con el espejo mirando para atrás
    Mc = marco(cabeza + Z * 0.012, Y)
    placa(p, "cromo", Mc, 0.115, 0.072, 0.012, radio=0.012, hundir=0.022)
    placa(p, "vidrio", Mc @ Matrix.Translation((0, 0, 0.012)), 0.100, 0.058, 0.001, radio=0.008, hundir=0.0)
    obj = p.objeto(origen=BISAGRA_IZQ)
    obj["id"] = "espejo"
    obj["abre_eje"] = "y"
    obj["abre_grados"] = GRADOS_PUERTA["izq"]
    return obj


def manijas(mats, chapa):
    objs = []
    for lado, s, bisagra in (("izq", 1, BISAGRA_IZQ), ("der", -1, BISAGRA_DER)):
        p = Pieza(f"manija-{lado}", mats)
        q, n = chapa.desde_afuera(Vector((s * 0.95, 0.38, 0.775)), -s * X)
        M = marco(q, n)
        placa(p, "negro_mate", M, 0.150, 0.034, 0.002, radio=0.010, hundir=0.006)
        placa(p, "cromo", M @ Matrix.Translation((0, 0.004, 0.002)), 0.135, 0.018, 0.010, radio=0.008, hundir=0.0)
        # La cerradura, adelante de la manija
        revolver(p, [(0.0, 0.009), (0.010, 0.007), (0.011, 0.0)], "cromo",
                 M @ Matrix.Translation((s * 0.0, -0.040, 0.0)), segmentos=16)
        obj = p.objeto(origen=bisagra)
        obj["abre_eje"] = "y"
        obj["abre_grados"] = GRADOS_PUERTA[lado]
        objs.append(obj)
    return objs


# ----------------------------------------------------------------------------------------------
# Interior negro (se ve por las ventanillas; sin fichas)
# ----------------------------------------------------------------------------------------------
I = Matrix.Identity(4)


def butaca(p, x):
    # Almohadón y respaldo, sin apoyacabezas (como el 68), con costuras marcadas
    caja(p, "vinilo", I, x - 0.25, x + 0.25, -0.12, 0.38, 0.30, 0.45, bisel=0.035, seg=3)
    respaldo = Matrix.Translation((x, 0.40, 0.42)) @ Matrix.Rotation(math.radians(-14), 4, "X")
    caja(p, "vinilo", respaldo, -0.245, 0.245, -0.06, 0.06, 0.0, 0.58, bisel=0.04, seg=3)
    for k in range(-2, 3):
        caja(p, "alfombra", I, x + k * 0.075 - 0.003, x + k * 0.075 + 0.003, -0.08, 0.34, 0.448, 0.452)
        caja(p, "alfombra", respaldo, k * 0.075 - 0.003, k * 0.075 + 0.003, -0.063, -0.058, 0.06, 0.54)
    # Cinturón de cintura: dos tiras apoyadas sobre el almohadón y la hebilla cromada al medio
    for s in (1, -1):
        caja(p, "tablero", I, x + s * 0.03, x + s * 0.25, 0.25, 0.29, 0.451, 0.457)
    caja(p, "cromo", I, x - 0.03, x + 0.03, 0.245, 0.295, 0.452, 0.460)


def interior(mats):
    g = grupo("interior")
    objs = [g]

    p = Pieza("piso-interior", mats)
    caja(p, "alfombra", I, -0.80, 0.80, -0.70, 1.50, 0.22, 0.26)
    caja(p, "alfombra", I, -0.13, 0.13, -0.70, 0.62, 0.24, 0.40, bisel=0.05, seg=3)   # túnel
    for s in (1, -1):    # costados de atrás (tapan el pasaruedas)
        caja(p, "vinilo", I, s * 0.66, s * 0.80, 0.58, 1.48, 0.26, 0.84, bisel=0.02)
    caja(p, "vinilo", I, -0.80, 0.80, 1.36, 1.56, 0.84, 0.87)                         # luneta: bandeja
    objs.append(p.objeto(padre=g))

    p = Pieza("butacas", mats)
    butaca(p, 0.37)
    butaca(p, -0.37)
    objs.append(p.objeto(padre=g))

    p = Pieza("asiento-trasero", mats)
    caja(p, "vinilo", I, -0.64, 0.64, 0.72, 1.16, 0.28, 0.42, bisel=0.04, seg=3)
    respaldo = Matrix.Translation((0, 1.18, 0.40)) @ Matrix.Rotation(math.radians(-24), 4, "X")
    caja(p, "vinilo", respaldo, -0.64, 0.64, -0.06, 0.06, 0.0, 0.50, bisel=0.04, seg=3)
    objs.append(p.objeto(padre=g))

    p = Pieza("tablero", mats)
    caja(p, "tablero", I, -0.80, 0.80, -0.74, -0.47, 0.60, 0.80, bisel=0.03)
    caja(p, "tablero", I, -0.80, 0.80, -0.78, -0.50, 0.79, 0.84, bisel=0.02)            # acolchado
    for gx in (0.27, 0.45):      # los dos relojes grandes del lado del conductor
        Mr = marco(Vector((gx, -0.47, 0.72)), Y)
        revolver(p, [(0.064, -0.01), (0.066, 0.012), (0.058, 0.014)], "cromo", Mr, segmentos=28)
        revolver(p, [(0.0, 0.004), (0.058, 0.004)], "negro_mate", Mr, segmentos=28)
        caja(p, "blanco", Mr, -0.002, 0.002, 0.0, 0.045, 0.004, 0.006)                   # aguja
    caja(p, "cromo", I, -0.30, 0.10, -0.471, -0.466, 0.655, 0.665)                       # filete
    objs.append(p.objeto(padre=g))

    # Volante de 3 rayos, inclinado hacia el conductor
    p = Pieza("volante", mats)
    centro = Vector((0.37, -0.30, 0.80))
    normal = Vector((0, math.cos(math.radians(28)), math.sin(math.radians(28))))
    Mv = marco(centro, normal)
    # El aro: un círculo de 1,3 cm girado alrededor del centro (una rosquita)
    aro = [(0.19 + 0.013 * math.cos(2 * math.pi * k / 8), 0.013 * math.sin(2 * math.pi * k / 8)) for k in range(9)]
    revolver(p, aro, "tablero", Mv, segmentos=36)
    for a in (0, 180, 270):
        Mr = Mv @ Matrix.Rotation(math.radians(a), 4, "Z")
        caja(p, "plata", Mr, 0.035, 0.182, -0.018, 0.018, -0.004, 0.004)
    revolver(p, [(0.0, 0.020), (0.040, 0.016), (0.045, 0.0), (0.040, -0.02)], "tablero", Mv, segmentos=24)
    texto(p, "SS", 0.032, 0.002, Mv @ Matrix.Translation((0, 0, 0.018)), "cromo")
    columna = marco(centro - normal * 0.30, normal)
    revolver(p, [(0.030, 0.0), (0.026, 0.28)], "tablero", columna, segmentos=16)
    objs.append(p.objeto(padre=g))

    # Palanca al piso (caja manual de 4), con fuelle y bocha negra
    p = Pieza("palanca", mats)
    base = Vector((0, -0.10, 0.40))
    revolver(p, [(0.0, 0.07), (0.035, 0.05), (0.06, 0.0)], "vinilo", Matrix.Translation(base), segmentos=16)
    tope = Vector((0, -0.16, 0.66))
    eje = tope - base
    revolver(p, [(0.007, 0.0), (0.006, eje.length)], "cromo", marco(base, eje), segmentos=10)
    bpy_esfera = bmesh.ops.create_uvsphere(p.bm, u_segments=14, v_segments=8, radius=0.024,
                                           matrix=Matrix.Translation(tope))
    for f in {f for v in bpy_esfera["verts"] for f in v.link_faces}:
        f.material_index = p.m("tablero")
        f.smooth = True
    objs.append(p.objeto(padre=g))
    return objs


# ----------------------------------------------------------------------------------------------
# Todo junto
# ----------------------------------------------------------------------------------------------
def construir():
    """Arma lo de afuera en la escena actual (sobre la carrocería) y devuelve los objetos a exportar."""
    referencia = car.construir(sombra=False)
    chapa = Chapa([referencia[n] for n in ("carroceria", "puerta_izq", "puerta_der", "capot", "baul")])
    chapa_fija = Chapa([referencia["carroceria"]])
    mats = materiales()

    objs = []
    for adelante in (-1, 1):
        o, extras = paragolpes(mats, chapa_fija, adelante)
        objs += [o] + extras
    o, frente_parrilla = parrilla(mats, chapa_fija)
    objs.append(o)
    objs.append(faros(mats, chapa_fija))
    g, rojas = luces_posicion(mats, chapa_fija)
    objs += [g, rojas]
    objs.append(luces_traseras(mats, chapa_fija))
    objs.append(tapa_nafta(mats, chapa_fija))
    objs.append(emblemas(mats, chapa_fija, frente_parrilla))
    objs.append(llantas(mats))
    objs.append(vidrios(mats))
    objs.append(espejo(mats, chapa))
    objs += manijas(mats, chapa)
    objs += interior(mats)

    # La carrocería de referencia no se exporta
    for o in referencia.values():
        bpy.data.objects.remove(o, do_unlink=True)

    # Todo lo que cuelga de un grupo también va
    todos = set()
    for o in objs:
        todos.add(o)
        todos.update(o.children_recursive)
    return todos


def exportar(objetos, ruta):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objetos:
        o.select_set(True)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=ruta,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_extras=True,
        export_texcoords=False,
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
    return os.path.join(AQUI, "..", "modelos", "exterior.glb")


if __name__ == "__main__":
    car.limpiar_escena()
    objetos = construir()
    salida = ruta_salida()
    exportar(objetos, salida)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objetos if o.type == "MESH")
    print(f"Listo: {os.path.normpath(salida)} ({os.path.getsize(salida) / 1024:.0f} KB, {tris} triángulos)")
