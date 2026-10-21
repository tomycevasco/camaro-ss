"""
Carrocería del Camaro SS 1968 coupé, hecha por script.

Se corre con el Blender portátil, sin abrir la ventana:
    blender -b -P blender/carroceria.py
(ver blender/LEEME.md). Genera modelos/carroceria.glb.

Cómo está armada:
1. La chapa sale de «rebanadas» transversales del auto (perfil()), con las medidas reales del 68
   (108″ entre ejes, 1841 mm de ancho, 1295 mm de alto). Las rebanadas se unen en una malla.
2. Se abren los huecos de los vidrios y de las ruedas.
3. Se recortan capot, puertas y baúl con una ranura fina, y cada uno queda como objeto propio con el
   origen en su bisagra (girar el objeto = abrirlo).
4. Se agregan el vano del motor, los pasaruedas, el piso, la sombra de contacto horneada y los
   puntos de enganche (objetos vacíos «enganche_*») para lo que viene después.

Ejes en Blender: X = ancho (+X = lado izquierdo del auto), Y = largo (el frente mira a -Y),
Z = arriba. Metros. El exportador lo pasa a Three.js: arriba = +Y y el frente mira a +Z.
El origen está en el piso, en el medio entre los dos ejes.

Otros scripts lo pueden reusar sin exportar:
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("carroceria", "blender/carroceria.py")
    car = importlib.util.module_from_spec(spec); spec.loader.exec_module(car)
    objetos = car.construir()          # arma todo en la escena actual
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

# ----------------------------------------------------------------------------------------------
# Medidas (metros). Las «reales» salen de la ficha del 68; el resto es forma del auto.
# ----------------------------------------------------------------------------------------------
ENTRE_EJES = 2.742                 # 108″
EJE_DEL_Y = -ENTRE_EJES / 2        # el frente mira a -Y
EJE_TRAS_Y = ENTRE_EJES / 2
TROCHA_DEL = 1.499
TROCHA_TRAS = 1.496
RADIO_RUEDA = 0.33                 # cubierta 14″ de la época (~26″ de diámetro)
RADIO_ARCO = 0.37                  # hueco del guardabarros
FRENTE_Y = -2.22                   # chapa adelante (el paragolpes sale un poco más)
COLA_Y = 2.32                      # chapa atrás
# Con paragolpes el auto mide 4691 mm: el Agente 4 los pone en enganche_paragolpes_*.

RANURA = 0.005                     # ranura entre paneles (5 mm)

# Bordes de los paneles que se abren
CAPOT_Y = (-2.19, -0.68)           # adelante, atrás (bisagra atrás, junto al parabrisas)
CAPOT_X = 0.70                     # medio ancho del capot (la unión con los guardabarros)
PUERTA_Y = (-0.62, 0.53)           # delantero (bisagra), trasero
PUERTA_Z = 0.30                    # borde de abajo de la puerta
BAUL_Y = (1.52, 2.29)              # delantero (bisagra), trasero
BAUL_X = 0.68

# Vidrios (los huecos; los vidrios los pone el Agente 4)
CUBRE_Y = -0.60                    # base del parabrisas
TECHO_Y = (0.05, 0.70)             # techo: delante, atrás
LUNETA_Y = 1.50                    # base de la luneta (vidrio trasero)
VENTANA_Y0 = -0.50                 # frente de la ventanilla


# ----------------------------------------------------------------------------------------------
# Curvas suaves que pasan por puntos dados, sin pasarse de largo (cúbica monótona)
# ----------------------------------------------------------------------------------------------
def curva(puntos):
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    n = len(xs)
    h = [xs[k + 1] - xs[k] for k in range(n - 1)]
    d = [(ys[k + 1] - ys[k]) / h[k] for k in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for k in range(1, n - 1):
        if d[k - 1] * d[k] <= 0:
            m[k] = 0.0
        else:
            m[k] = 3 * (h[k - 1] + h[k]) / ((2 * h[k] + h[k - 1]) / d[k - 1] + (h[k] + 2 * h[k - 1]) / d[k])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        k = 0
        while x > xs[k + 1]:
            k += 1
        t = (x - xs[k]) / h[k]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[k] + (t3 - 2 * t2 + t) * h[k] * m[k]
                + (-2 * t3 + 3 * t2) * ys[k + 1] + (t3 - t2) * h[k] * m[k + 1])
    return f


def suave(a, b, x):
    """0 antes de a, 1 después de b, curva suave en el medio."""
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def mezclar(a, b, t):
    return a + (b - a) * t


# Cada medida de la rebanada cambia a lo largo del auto (y). Valores: (y, medida).
FONDO_Z = curva([(-2.22, 0.30), (-1.90, 0.27), (-1.00, 0.22), (1.80, 0.22), (2.32, 0.30)])
ZOCALO_X = curva([(-2.22, 0.80), (-1.80, 0.84), (0.00, 0.85), (2.00, 0.84), (2.32, 0.80)])
# De arriba se ve la «botella de Coca»: angosto en la puerta, ancho sobre la rueda de atrás
LADO_X = curva([(-2.22, 0.86), (-1.95, 0.895), (-1.37, 0.905), (-0.40, 0.893), (0.30, 0.888),
                (1.37, 0.920), (2.05, 0.905), (2.32, 0.875)])
# La línea marcada del costado: baja por la puerta y sube sobre la rueda de atrás (la «cadera»)
LINEA_Z = curva([(-2.22, 0.700), (-1.00, 0.695), (0.30, 0.680), (1.00, 0.720), (1.40, 0.755),
                 (2.00, 0.750), (2.32, 0.740)])
HOMBRO_X = curva([(-2.22, 0.825), (-1.40, 0.860), (-0.60, 0.860), (0.30, 0.845), (1.40, 0.875),
                  (2.32, 0.850)])
HOMBRO_Z = curva([(-2.22, 0.775), (-1.40, 0.800), (-0.60, 0.855), (0.30, 0.885), (1.00, 0.900),
                  (1.50, 0.918), (2.32, 0.905)])
# Altura del centro de capot y baúl (el lomo del capot SS va aparte)
CRESTA_Z = curva([(-2.22, 0.795), (-1.40, 0.838), (-0.60, 0.890), (0.00, 0.910), (1.50, 0.950),
                  (2.00, 0.958), (2.32, 0.935)])
LOMO_ALTO = curva([(-2.16, 0.0), (-1.98, 0.024), (-0.76, 0.028), (-0.66, 0.0)])
# Cuánto «techo» tiene cada rebanada: 0 = capot o baúl, 1 = techo entero
TECHO = curva([(CUBRE_Y, 0.0), (TECHO_Y[0], 1.0), (TECHO_Y[1], 1.0), (LUNETA_Y, 0.0)])
TECHO_BORDE_Z = curva([(0.05, 1.235), (0.40, 1.250), (0.70, 1.222)])
TECHO_CENTRO_Z = curva([(0.05, 1.280), (0.35, 1.295), (0.70, 1.272)])
TECHO_X = curva([(0.05, 0.615), (0.40, 0.630), (0.70, 0.600)])
VIDRIO_BASE_X = 0.755

# Índices del perfil (mitad izquierda, de abajo al centro de arriba): sirven para abrir huecos
J_VIDRIO_BASE = 14      # la base de las ventanillas
J_VENTANA_ARRIBA = 16
J_TECHO_BORDE = 17
J_LUNETA = 18
N_PERFIL = 21


def lomo(x):
    """El lomo central del capot SS: 1 en el medio, 0 afuera, con costado firme (sin rejillas)."""
    if x <= 0.28:
        return 1.0
    if x >= 0.32:
        return 0.0
    return (0.32 - x) / 0.04


def perfil(y):
    """Media rebanada (lado +X) en la posición y: lista de N_PERFIL puntos (x, z)."""
    zb, xr, xs = FONDO_Z(y), ZOCALO_X(y), LADO_X(y)
    zc, xc = LINEA_Z(y), xs + 0.012
    xsh, zsh = HOMBRO_X(y), HOMBRO_Z(y)
    zalto = zsh - 0.035
    abajo = [
        (0.00, zb), (0.40, zb), (xr - 0.08, zb), (xr - 0.015, zb + 0.015), (xr, zb + 0.06),
        (xs - 0.01, 0.42), (xs, 0.52),
        (xc, zc),                                                   # línea marcada
        (xc - 0.010, zc + 0.35 * (zalto - zc)),
        (xsh + 0.025, zc + 0.75 * (zalto - zc)),
        (xsh + 0.010, zalto), (xsh - 0.010, zsh - 0.005), (xsh - 0.050, zsh + 0.005),
    ]
    # Arriba: capot / baúl ...
    x_capot = [xsh - 0.10, 0.62, 0.48, 0.38, 0.32, 0.28, 0.14, 0.0]
    x_cubierta = [xsh - 0.08, xsh - 0.11, 0.72, 0.70, 0.66, 0.52, 0.26, 0.0]
    t = suave(-0.70, -0.60, y)
    xe, ze, zcr, alto_lomo = xsh - 0.05, zsh + 0.005, CRESTA_Z(y), LOMO_ALTO(y)
    cubierta = []
    for xa, xb in zip(x_capot, x_cubierta):
        x = mezclar(xa, xb, t)
        z = zcr - (zcr - ze) * (x / xe) ** 2 + alto_lomo * lomo(x)
        cubierta.append((x, z))
    # ... o techo, con las ventanillas
    w = TECHO(y)
    if w <= 0:
        return abajo + cubierta
    zre, zrc, xgt, xgb = TECHO_BORDE_Z(y), TECHO_CENTRO_Z(y), TECHO_X(y), VIDRIO_BASE_X
    techo = [
        (xgb + 0.02, zsh + 0.008), (xgb, zsh + 0.02),
        (mezclar(xgb, xgt, 0.5) + 0.012, mezclar(zsh + 0.02, zre - 0.07, 0.5)),
        (xgt + 0.02, zre - 0.07), (xgt - 0.035, zre),
        (0.45, zre + 0.65 * (zrc - zre)), (0.22, zre + 0.92 * (zrc - zre)), (0.0, zrc),
    ]
    arriba = [(mezclar(a[0], b[0], w), mezclar(a[1], b[1], w)) for a, b in zip(cubierta, techo)]
    return abajo + arriba


def rebanadas():
    """Las posiciones y de las rebanadas: parejas cada ~3,5 cm, más las justas en los bordes."""
    paso = 0.035
    n = int((COLA_Y - FRENTE_Y) / paso)
    ys = {round(FRENTE_Y + (COLA_Y - FRENTE_Y) * k / n, 5) for k in range(n + 1)}
    ys |= {CUBRE_Y, TECHO_Y[0], TECHO_Y[1], LUNETA_Y, VENTANA_Y0}
    return sorted(ys)


# ----------------------------------------------------------------------------------------------
# Materiales
# ----------------------------------------------------------------------------------------------
def srgb_a_lineal(hexa):
    c = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1.0,)


def material(nombre, color, rugosidad, barniz=0.0, doble_cara=True):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = color
    p.inputs["Metallic"].default_value = 0.0
    p.inputs["Roughness"].default_value = rugosidad
    p.inputs["Coat Weight"].default_value = barniz
    if barniz:
        p.inputs["Coat Roughness"].default_value = 0.04
    m.use_backface_culling = not doble_cara
    m.diffuse_color = color
    return m


def materiales():
    return {
        # Negro laca con barniz (en Three.js sale como MeshPhysicalMaterial con clearcoat)
        "pintura": material("pintura_negra", (0.006, 0.006, 0.007, 1), 0.22, barniz=1.0),
        "mate": material("negro_mate", (0.012, 0.012, 0.013, 1), 0.85),
        "piso": material("piso_estudio", srgb_a_lineal("#f3f2ee"), 1.0, doble_cara=False),
    }


# ----------------------------------------------------------------------------------------------
# La chapa
# ----------------------------------------------------------------------------------------------
def malla_chapa():
    """Une las rebanadas en una sola malla cerrada. Cada vértice guarda su índice de perfil (j)."""
    bm = bmesh.new()
    capa_j = bm.verts.layers.float.new("j")
    ys = rebanadas()

    def anillo(y, encoger=1.0, apretar=1.0):
        media = perfil(y)
        zmedio = 0.55
        puntos = [(x * encoger, zmedio + (z - zmedio) * apretar, j) for j, (x, z) in enumerate(media)]
        # mitad derecha (espejo), sin repetir los dos puntos del medio
        puntos += [(-x, z, j) for (x, z, j) in reversed(puntos[1:-1])]
        return [(x, y, z, j) for (x, z, j) in puntos]

    # Un anillo apenas más chico en cada punta redondea el canto del frente y de la cola
    anillos = [[(x, ys[0] - 0.008, z, j) for (x, _, z, j) in anillo(ys[0], 0.975, 0.985)]]
    anillos += [anillo(y) for y in ys]
    anillos.append([(x, ys[-1] + 0.008, z, j) for (x, _, z, j) in anillo(ys[-1], 0.975, 0.985)])

    filas = []
    for a in anillos:
        fila = []
        for (x, y, z, j) in a:
            # Vista de arriba: el frente y la cola tienen una punta suave en el medio
            if y < FRENTE_Y + 0.17:
                t = suave(FRENTE_Y + 0.17, FRENTE_Y, y)
                y -= 0.022 * (1 - (x / 0.92) ** 2) * t
                # De costado: el frente se mete hacia abajo (la trompa de arriba sobresale)
                y += 0.05 * (1 - min(1.0, max(0.0, (z - 0.30) / 0.48))) * t
            if y > COLA_Y - 0.10:
                y += 0.015 * (1 - (x / 0.92) ** 2) * suave(COLA_Y - 0.10, COLA_Y, y)
            v = bm.verts.new((x, y, z))
            v[capa_j] = j
            fila.append(v)
        filas.append(fila)
    n = len(filas[0])
    for a, b in zip(filas, filas[1:]):
        for k in range(n):
            k2 = (k + 1) % n
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    frente = bm.faces.new(filas[0])
    cola = bm.faces.new(filas[-1])
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    # El frente del 68 (no RS): marco de chapa y adentro el hueco ancho de la parrilla, con los
    # faros redondos adentro (la parrilla y los faros los pone el Agente 4 en el fondo del hueco).
    bmesh.ops.inset_region(bm, faces=[frente], thickness=0.10, depth=0.0)
    bmesh.ops.inset_region(bm, faces=[frente], thickness=0.004, depth=-0.085)
    # La cola: un panel apenas hundido donde van las luces y la tapa de nafta
    bmesh.ops.inset_region(bm, faces=[cola], thickness=0.06, depth=0.0)
    bmesh.ops.inset_region(bm, faces=[cola], thickness=0.003, depth=-0.012)
    return bm


def j_de_cara(cara, capa_j):
    js = [v[capa_j] for v in cara.verts]
    return min(js), max(js)


def abrir_vidrios(bm):
    capa_j = bm.verts.layers.float["j"]
    # La ventanilla termina atrás con un borde inclinado que sigue al parante trasero
    p0, p1 = Vector((0.0, 0.98, 0.92)), Vector((0.0, 0.52, 1.22))
    corte_atras = Vector((0.0, p1.z - p0.z, -(p1.y - p0.y))).normalized()   # perpendicular, en (y, z)
    cortar(bm, p0, corte_atras, lambda f, c: j_de_cara(f, capa_j)[0] >= J_VIDRIO_BASE - 1)
    afuera = []
    for f in bm.faces:
        c = f.calc_center_median()
        jmin, jmax = j_de_cara(f, capa_j)
        if jmin >= J_TECHO_BORDE and CUBRE_Y < c.y < TECHO_Y[0]:
            afuera.append(f)                                     # parabrisas
        elif jmin >= J_LUNETA and TECHO_Y[1] < c.y < LUNETA_Y:
            afuera.append(f)                                     # luneta
        elif (jmin >= J_VIDRIO_BASE and jmax <= J_VENTANA_ARRIBA and c.y > VENTANA_Y0
              and (c - p0).dot(corte_atras) < 0 and c.y < 1.1):
            afuera.append(f)                                     # ventanillas (sin parante del medio)
    bmesh.ops.delete(bm, geom=afuera, context="FACES")


def abrir_ruedas(bm):
    for eje_y in (EJE_DEL_Y, EJE_TRAS_Y):
        centro = Vector((eje_y, RADIO_RUEDA))
        afuera = [f for f in bm.faces
                  if abs(f.calc_center_median().x) > 0.60
                  and (Vector((f.calc_center_median().y, f.calc_center_median().z)) - centro).length < RADIO_ARCO]
        bmesh.ops.delete(bm, geom=afuera, context="FACES")
        # El borde del hueco queda escalonado: lo llevo justo al círculo
        for v in bm.verts:
            # (solo el arco: el borde de abajo, en el zócalo, queda donde está)
            if v.is_boundary and abs(v.co.x) > 0.72 and v.co.z > FONDO_Z(v.co.y) + 0.03:
                d = Vector((v.co.y, v.co.z)) - centro
                if d.length >= RADIO_ARCO + 0.15:
                    continue
                if d.y >= 0:                    # mitad de arriba: al círculo
                    d = d.normalized() * RADIO_ARCO
                    v.co.y, v.co.z = centro.x + d.x, centro.y + d.y
                else:                           # mitad de abajo: solo hacia adelante o atrás
                    lado = 1 if d.x >= 0 else -1
                    v.co.y = centro.x + lado * math.sqrt(max(0.0, RADIO_ARCO ** 2 - d.y ** 2))


def cortar(bm, co, normal, filtro=None):
    """Corta la malla con un plano, solo en las caras que pasan el filtro(cara, centro)."""
    caras = [f for f in bm.faces if filtro is None or filtro(f, f.calc_center_median())]
    aristas = {e for f in caras for e in f.edges}
    verts = {v for f in caras for v in f.verts}
    bmesh.ops.bisect_plane(bm, geom=list(verts) + list(aristas) + caras, plane_co=co, plane_no=normal)


def zonas_de_paneles(bm):
    """Corta los bordes de los paneles y devuelve qué caras son de cada panel y cuáles son ranura."""
    X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    arriba_capot = lambda f, c: c.z > 0.65 and c.y < -0.4 and abs(c.x) < 0.80
    arriba_baul = lambda f, c: c.z > 0.75 and c.y > 1.3 and abs(c.x) < 0.80
    costado = lambda f, c: abs(c.x) > 0.5 and c.z > 0.24 and -0.8 < c.y < 0.7
    for s in (1, -1):
        for x in (CAPOT_X, CAPOT_X + RANURA):
            cortar(bm, Vector((s * x, 0, 0)), X, arriba_capot)
        for x in (BAUL_X, BAUL_X + RANURA):
            cortar(bm, Vector((s * x, 0, 0)), X, arriba_baul)
    for y in (CAPOT_Y[0] - RANURA, CAPOT_Y[0], CAPOT_Y[1], CAPOT_Y[1] + RANURA):
        cortar(bm, Vector((0, y, 0)), Y, arriba_capot)
    for y in (BAUL_Y[0], BAUL_Y[0] + RANURA, BAUL_Y[1] - RANURA, BAUL_Y[1]):
        cortar(bm, Vector((0, y, 0)), Y, arriba_baul)
    for y in (PUERTA_Y[0], PUERTA_Y[0] + RANURA, PUERTA_Y[1] - RANURA, PUERTA_Y[1]):
        cortar(bm, Vector((0, y, 0)), Y, costado)
    for z in (PUERTA_Z - RANURA, PUERTA_Z):
        cortar(bm, Vector((0, 0, z)), Z, costado)

    capa_j = bm.verts.layers.float["j"]
    bm.faces.index_update()
    zonas = {"capot": [], "puerta_izq": [], "puerta_der": [], "baul": [], "ranura": []}
    for f in bm.faces:
        c = f.calc_center_median()
        ax = abs(c.x)
        _, jmax = j_de_cara(f, capa_j)
        # Capot
        if c.z > 0.70 and CAPOT_Y[0] - RANURA < c.y < CAPOT_Y[1] + RANURA and ax < CAPOT_X + RANURA:
            zona = "capot" if (ax < CAPOT_X and CAPOT_Y[0] < c.y < CAPOT_Y[1]) else "ranura"
        # Baúl
        elif c.z > 0.80 and BAUL_Y[0] < c.y < BAUL_Y[1] and ax < BAUL_X + RANURA:
            zona = "baul" if (ax < BAUL_X and BAUL_Y[0] + RANURA < c.y < BAUL_Y[1] - RANURA) else "ranura"
        # Puertas
        elif (ax > 0.5 and jmax <= J_VIDRIO_BASE and c.z > PUERTA_Z - RANURA
              and PUERTA_Y[0] < c.y < PUERTA_Y[1]):
            dentro = c.z > PUERTA_Z and PUERTA_Y[0] + RANURA < c.y < PUERTA_Y[1] - RANURA
            zona = ("puerta_izq" if c.x > 0 else "puerta_der") if dentro else "ranura"
        else:
            continue
        zonas[zona].append(f.index)
    return zonas


def objeto_desde_bm(nombre, bm, mats, quedarse):
    """Copia de la malla con solo las caras de 'quedarse' (índices)."""
    copia = bm.copy()
    copia.faces.index_update()
    quedarse = set(quedarse)
    bmesh.ops.delete(copia, geom=[f for f in copia.faces if f.index not in quedarse], context="FACES")
    bmesh.ops.delete(copia, geom=[v for v in copia.verts if not v.link_faces], context="VERTS")
    malla = bpy.data.meshes.new(nombre)
    copia.to_mesh(malla)
    copia.free()
    malla.attributes.remove(malla.attributes["j"])
    obj = bpy.data.objects.new(nombre, malla)
    bpy.context.scene.collection.objects.link(obj)
    for m in mats:
        obj.data.materials.append(m)
    return obj


def poner_bisagra(obj, punto):
    """Mueve el origen del objeto a 'punto' sin que la pieza se mueva."""
    punto = Vector(punto)
    obj.data.transform(Matrix.Translation(-punto))
    obj.location = punto


def engrosar(obj, espesor=0.012):
    """Le da espesor a un panel: la cara de adentro queda negro mate (material 2)."""
    mod = obj.modifiers.new("espesor", "SOLIDIFY")
    mod.thickness = espesor
    mod.offset = -1.0
    mod.use_rim = True
    mod.material_offset = 1
    mod.material_offset_rim = 1


def suavizar(obj, angulo=38):
    with bpy.context.temp_override(selected_editable_objects=[obj], active_object=obj, object=obj):
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angulo))


def aplicar_modificadores(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    malla = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
    viejo = obj.data
    obj.modifiers.clear()
    obj.data = malla
    bpy.data.meshes.remove(viejo)
    malla.name = obj.name


def altura_chapa(y, x=0.0):
    """Altura de la parte de arriba de la chapa en (x, y): sirve para ubicar bisagras."""
    media = perfil(y)[12:]
    for (x0, z0), (x1, z1) in zip(media, media[1:]):
        if x1 <= x <= x0:
            return mezclar(z0, z1, (x0 - x) / (x0 - x1 or 1))
    return media[-1][1]


# ----------------------------------------------------------------------------------------------
# Piezas simples de adentro (negro mate)
# ----------------------------------------------------------------------------------------------
def caja(bm, centro, medida):
    m = Matrix.Translation(centro) @ Matrix.Diagonal((*medida, 1))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)


def vano_motor(mats):
    """Torpedo (pared entre motor y cabina), pasaruedas internos y soporte del radiador."""
    bm = bmesh.new()
    caja(bm, Vector((0, CAPOT_Y[1] + 0.03, 0.56)), (1.60, 0.02, 0.62))                 # torpedo
    caja(bm, Vector((0, -2.02, 0.53)), (1.60, 0.04, 0.46))                               # soporte del radiador
    for s in (1, -1):
        caja(bm, Vector((s * 0.645, -1.36, 0.52)), (0.02, 1.30, 0.42))                  # pared interna
        caja(bm, Vector((s * 0.735, -1.36, 0.735)), (0.17, 1.30, 0.012))                # pestaña de arriba
    malla = bpy.data.meshes.new("vano_motor")
    bm.to_mesh(malla)
    bm.free()
    obj = bpy.data.objects.new("vano_motor", malla)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mats["mate"])
    return obj


def pasaruedas(mats):
    """Medio tubo adentro de cada hueco de rueda, para que no se vea el hueco de la chapa."""
    bm = bmesh.new()
    segmentos, r = 28, RADIO_ARCO + 0.02
    for eje_y in (EJE_DEL_Y, EJE_TRAS_Y):
        for s in (1, -1):
            x0, x1 = s * 0.56, s * 0.89
            arco = [math.radians(-15 + 210 * k / segmentos) for k in range(segmentos + 1)]
            adentro, afuera = [], []
            for a in arco:
                y, z = eje_y + r * math.cos(a), RADIO_RUEDA + r * math.sin(a)
                adentro.append(bm.verts.new((x0, y, z)))
                afuera.append(bm.verts.new((x1, y, z)))
            centro = bm.verts.new((x0, eje_y, RADIO_RUEDA - 0.05))
            for k in range(segmentos):
                bm.faces.new((adentro[k], adentro[k + 1], afuera[k + 1], afuera[k]))
                bm.faces.new((centro, adentro[k + 1], adentro[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    malla = bpy.data.meshes.new("pasaruedas")
    bm.to_mesh(malla)
    bm.free()
    obj = bpy.data.objects.new("pasaruedas", malla)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mats["mate"])
    return obj


# ----------------------------------------------------------------------------------------------
# Piso del estudio y sombra de contacto
# ----------------------------------------------------------------------------------------------
def piso(mats):
    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=9.0, fill_type="NGON", location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = obj.data.name = "piso"
    obj.data.materials.append(mats["piso"])
    return obj


SOMBRA_MEDIDA = (3.4, 6.4)          # ancho (x), largo (y) del plano de la sombra
SOMBRA_PIXELES = (256, 512)


def ruedas_provisorias():
    """Cubiertas de mentira, solo para que la sombra horneada tenga el apoyo de las ruedas.
    No se exportan: las ruedas de verdad las hace el Agente 4 en los enganche_rueda_*."""
    objs = []
    for eje_y, trocha in ((EJE_DEL_Y, TROCHA_DEL), (EJE_TRAS_Y, TROCHA_TRAS)):
        for s in (1, -1):
            bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=RADIO_RUEDA, depth=0.21,
                                                location=(s * trocha / 2, eje_y, RADIO_RUEDA),
                                                rotation=(0, math.pi / 2, 0))
            objs.append(bpy.context.active_object)
    return objs


def hornear_sombra(objetos_que_tapan):
    """Calcula con Cycles la oclusión (lo que tapa la luz del cielo) sobre un plano debajo del auto
    y la guarda como imagen negra con transparencia: la sombra de contacto."""
    escena = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0.002))
    plano = bpy.context.active_object
    plano.name = plano.data.name = "piso_sombra"
    plano.scale = (SOMBRA_MEDIDA[0], SOMBRA_MEDIDA[1], 1)
    bpy.ops.object.transform_apply(scale=True)

    img = bpy.data.images.new("sombra_contacto", SOMBRA_PIXELES[0], SOMBRA_PIXELES[1], alpha=True)
    mat = bpy.data.materials.new("sombra_contacto")
    mat.use_nodes = True
    nodos = mat.node_tree.nodes
    p = nodos.get("Principled BSDF")
    tex = nodos.new("ShaderNodeTexImage")
    tex.image = img
    nodos.active = tex
    plano.data.materials.append(mat)

    escena.render.engine = "CYCLES"
    escena.cycles.device = "CPU"
    escena.cycles.samples = 96
    if escena.world is None:
        escena.world = bpy.data.worlds.new("mundo")
    escena.world.light_settings.distance = 1.1      # hasta dónde mira la oclusión (m)
    for o in bpy.context.scene.objects:
        o.hide_render = not (o in objetos_que_tapan or o == plano)
    bpy.ops.object.select_all(action="DESELECT")
    plano.select_set(True)
    bpy.context.view_layer.objects.active = plano
    bpy.ops.object.bake(type="AO", margin=2)
    for o in bpy.context.scene.objects:
        o.hide_render = False

    # Oclusión (1 = libre, 0 = tapado) → negro con alfa; borde del plano siempre transparente
    w, h = img.size
    px = list(img.pixels)
    nuevos = [0.0] * len(px)
    for fy in range(h):
        borde_y = min(fy, h - 1 - fy) / (h * 0.06)
        for fx in range(w):
            borde = min(1.0, borde_y, min(fx, w - 1 - fx) / (w * 0.06))
            ao = px[(fy * w + fx) * 4]
            a = max(0.0, min(1.0, (1.0 - ao) * 1.35)) ** 1.15 * 0.85 * borde
            nuevos[(fy * w + fx) * 4 + 3] = a
    img.pixels = nuevos
    img.file_format = "PNG"
    img.pack()

    p.inputs["Base Color"].default_value = (0, 0, 0, 1)
    p.inputs["Roughness"].default_value = 1.0
    mat.node_tree.links.new(tex.outputs["Alpha"], p.inputs["Alpha"])
    mat.surface_render_method = "BLENDED"
    mat.use_backface_culling = True
    return plano


# ----------------------------------------------------------------------------------------------
# Puntos de enganche para la tanda 2 (objetos vacíos con nombre y posición)
# ----------------------------------------------------------------------------------------------
def enganches():
    lugares = {
        "enganche_motor": (0, -1.15, 0.55),
        "enganche_radiador": (0, -1.98, 0.55),
        "enganche_bateria": (0.50, -1.80, 0.62),
        "enganche_paragolpes_del": (0, FRENTE_Y - 0.05, 0.42),
        "enganche_paragolpes_tras": (0, COLA_Y + 0.05, 0.44),
        "enganche_parrilla": (0, FRENTE_Y - 0.01, 0.57),
        "enganche_faro_izq": (0.62, FRENTE_Y - 0.01, 0.60),
        "enganche_faro_der": (-0.62, FRENTE_Y - 0.01, 0.60),
        "enganche_luz_posicion_izq": (0.86, FRENTE_Y + 0.17, 0.40),
        "enganche_luz_posicion_der": (-0.86, FRENTE_Y + 0.17, 0.40),
        "enganche_luces_traseras_izq": (0.52, COLA_Y + 0.01, 0.72),
        "enganche_luces_traseras_der": (-0.52, COLA_Y + 0.01, 0.72),
        "enganche_tapa_nafta": (0, COLA_Y + 0.012, 0.72),
        "enganche_parabrisas": (0, (CUBRE_Y + TECHO_Y[0]) / 2, 1.07),
        "enganche_luneta": (0, (TECHO_Y[1] + LUNETA_Y) / 2, 1.10),
        "enganche_interior": (0, 0.20, 0.45),
        "enganche_rueda_del_izq": (TROCHA_DEL / 2, EJE_DEL_Y, RADIO_RUEDA),
        "enganche_rueda_del_der": (-TROCHA_DEL / 2, EJE_DEL_Y, RADIO_RUEDA),
        "enganche_rueda_tras_izq": (TROCHA_TRAS / 2, EJE_TRAS_Y, RADIO_RUEDA),
        "enganche_rueda_tras_der": (-TROCHA_TRAS / 2, EJE_TRAS_Y, RADIO_RUEDA),
    }
    objs = []
    for nombre, lugar in lugares.items():
        e = bpy.data.objects.new(nombre, None)
        e.empty_display_type = "PLAIN_AXES"
        e.empty_display_size = 0.08
        e.location = lugar
        bpy.context.scene.collection.objects.link(e)
        objs.append(e)
    return objs


# ----------------------------------------------------------------------------------------------
# Todo junto
# ----------------------------------------------------------------------------------------------
def limpiar_escena():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def construir(sombra=True):
    """Arma la carrocería en la escena actual y devuelve {nombre: objeto}."""
    mats = materiales()
    bm = malla_chapa()
    abrir_vidrios(bm)
    abrir_ruedas(bm)
    zonas = zonas_de_paneles(bm)
    bm.faces.ensure_lookup_table()
    todas = set(range(len(bm.faces)))
    de_paneles = set().union(*zonas.values())

    objs = {"carroceria": objeto_desde_bm("carroceria", bm, [mats["pintura"]], todas - de_paneles)}
    for nombre in ("capot", "puerta_izq", "puerta_der", "baul"):
        objs[nombre] = objeto_desde_bm(nombre, bm, [mats["pintura"], mats["mate"]], zonas[nombre])
    bm.free()

    # Bisagras. Las puertas giran sobre su borde de adelante; capot y baúl, sobre el borde
    # que da al parabrisas / a la luneta.
    y_puerta = PUERTA_Y[0] + RANURA
    poner_bisagra(objs["capot"], (0, CAPOT_Y[1], altura_chapa(CAPOT_Y[1]) - 0.015))
    poner_bisagra(objs["baul"], (0, BAUL_Y[0] + RANURA, altura_chapa(BAUL_Y[0]) - 0.015))
    poner_bisagra(objs["puerta_izq"], (LADO_X(y_puerta) - 0.01, y_puerta, 0.55))
    poner_bisagra(objs["puerta_der"], (-(LADO_X(y_puerta) - 0.01), y_puerta, 0.55))

    for nombre in ("capot", "puerta_izq", "puerta_der", "baul"):
        engrosar(objs[nombre])
    for obj in objs.values():
        aplicar_modificadores(obj)
        suavizar(obj)

    objs["vano_motor"] = vano_motor(mats)
    objs["pasaruedas"] = pasaruedas(mats)
    objs["piso"] = piso(mats)

    # Datos para la pantalla (en Three.js quedan en objeto.userData). Ángulos con la regla de la
    # mano derecha en los ejes de Three.js (Y arriba, el frente mira a +Z).
    datos = {
        "carroceria": {"pieza": "carroceria"},
        "capot": {"pieza": "capot", "se_abre": 1, "eje": "x", "abierto_grados": -55},
        "puerta_izq": {"pieza": "puerta_izq", "se_abre": 1, "eje": "y", "abierto_grados": -62},
        "puerta_der": {"pieza": "puerta_der", "se_abre": 1, "eje": "y", "abierto_grados": 62},
        "baul": {"pieza": "baul", "se_abre": 1, "eje": "x", "abierto_grados": 58},
        "vano_motor": {"pieza": "vano_motor"},
        "pasaruedas": {"pieza": "pasaruedas"},
        "piso": {"escena": "piso"},
    }
    for nombre, d in datos.items():
        for k, v in d.items():
            objs[nombre][k] = v

    for e in enganches():
        objs[e.name] = e

    if sombra:
        provisorias = ruedas_provisorias()
        tapan = [objs[n] for n in ("carroceria", "capot", "puerta_izq", "puerta_der", "baul",
                                   "vano_motor", "pasaruedas")] + provisorias
        objs["piso_sombra"] = hornear_sombra(tapan)
        objs["piso_sombra"]["escena"] = "sombra"
        for o in provisorias:
            bpy.data.objects.remove(o, do_unlink=True)
    return objs


def exportar(objs, ruta):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs.values():
        o.select_set(True)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=ruta,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_extras=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_cameras=False,
        export_lights=False,
        export_animations=False,
        export_draco_mesh_compression_enable=False,   # la compresión la hace el cierre (Agente 7)
    )


def ruta_salida():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args:
        return os.path.abspath(args[0])
    aqui = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(aqui, "..", "modelos", "carroceria.glb")


if __name__ == "__main__":
    limpiar_escena()
    objetos = construir()
    salida = ruta_salida()
    exportar(objetos, salida)
    print(f"Listo: {os.path.normpath(salida)} ({os.path.getsize(salida) / 1024:.0f} KB)")
