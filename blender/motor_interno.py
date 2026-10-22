"""
El 350 por dentro: cigüeñal, bielas, pistones, árbol de levas, botadores con varillas, balancines,
válvulas con sus resortes, la cadena de distribución, y el bloque y las tapas de cilindros cortados.

Se corre con el Blender portátil, sin abrir la ventana (ver blender/LEEME.md):
    blender -b -P blender/motor_interno.py
Genera modelos/motor_interno.glb sin comprimir; después va Draco (comandos al final de este texto).

Cómo está armado:
1. Usa las medidas y las herramientas de motor.py (Malla, materiales, cilindros_y, en_banco…), así
   queda en las MISMAS coordenadas que motor.glb: en la página se cuelga del vacío «motor» sin mover
   nada y cada pieza cae justo adentro de su cilindro.
2. Medidas del L48 (INVESTIGACION-motor-interno.md): carrera 88,4 mm (manivela de 44,2 mm), biela de
   144,8 mm, pistón de 101,6 mm, bancadas de 2,45″ y muñones de 2,10″, válvulas de 1,94″ y 1,50″.
3. Cada pieza que se mueve tiene el origen donde gira o desde donde se mueve, y está armada en la
   posición «cigüeñal en 0°» = el cilindro 1 arriba de todo, a punto de explotar:
     · ciguenal y arbol-levas: origen en su eje (giran alrededor del eje largo del motor).
     · piston-N: origen en el bulón; sube y baja a lo largo de su cilindro.
     · biela-N: origen en el ojo chico (el bulón); va con el pistón y se inclina.
     · valvula-N-adm/esc y botador-N-adm/esc: bajan/suben a lo largo de su eje.
     · resorte-N-adm/esc: origen en su asiento y girado para que su eje propio sea el de la válvula:
       se aplasta escalándolo a lo largo de ese eje (en Three.js, scale.y).
     · balancin-N-adm/esc: origen en la rótula; se hamaca alrededor de un eje paralelo al cigüeñal.
   El cigüeñal es «en cruz»: muñones A 0° · B 90° · C 270° · D 180° (horario, mirado de frente),
   orden de encendido 1-8-4-3-6-5-7-2. Las levas están orientadas con esa misma cuenta, así cada
   botador «pisa» su leva cuando js/modulos/motor-vivo.js abre la válvula.
4. Todo lo que el JS necesita saber va en las propiedades de cada objeto (en Three.js: userData):
   tipo, cilindro, lado (+1 conductor, -1 acompañante), clase (adm/esc), explota (grados del
   cigüeñal), y en el vacío «motor_interno» las medidas (radio de manivela, biela, alzada…).
5. El corte: «bloque-corte» y «tapas-cilindros-corte» son el bloque y las tapas de motor.py con un
   corte de taller: se saca la mitad de afuera de cada fila de cilindros (hasta el eje de los
   cilindros), lo de abajo del cigüeñal y el techo del valle (para ver el árbol de levas). Las caras
   cortadas van en gris de metal mecanizado y las camisas en acero bruñido. Tienen el MISMO origen que
   «bloque» y «tapa-cilindros-izq/der»: la página los cambia uno por otro con «Por adentro».
6. Nada de esto tiene ficha todavía (la escribe el Agente 7): las ids de los grupos son
   ciguenal, arbol-levas, pistones, bielas, valvulas, resortes-valvulas, balancines, botadores,
   cadena-distribucion.

Ejes en Blender (los de motor.py): +X = lado del conductor, el frente mira a -Y, Z arriba. Metros.
Al exportar a glTF: Three.js x = x, y = z, z = -y.

Comprimir (como motor.glb; sin texturas que pasar a WebP salvo el relieve de fundición):
    npx @gltf-transform/cli webp  modelos/motor_interno.glb modelos/motor_interno.glb --quality 85
    npx @gltf-transform/cli draco modelos/motor_interno.glb modelos/motor_interno.glb --method edgebreaker --quantize-position 12 --quantize-texcoord 10
"""

import importlib.util
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

AQUI = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location("motor", os.path.join(AQUI, "motor.py"))
mot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mot)

Malla, en_banco, eje_banco, afuera_banco = mot.Malla, mot.en_banco, mot.eje_banco, mot.afuera_banco
X, Y, Z, S45 = mot.X, mot.Y, mot.Z, mot.S45

# ----------------------------------------------------------------------------------------------
# Medidas (metros). «d» = distancia a lo largo del cilindro desde el eje del cigüeñal; «t» = de
# costado, positivo hacia afuera del motor (las mismas de en_banco en motor.py).
# ----------------------------------------------------------------------------------------------
CIG_Z = mot.CIG_Z
CIG_Y = (mot.BLOQUE_Y[0] + mot.BLOQUE_Y[1]) / 2          # = enganche_ciguenal
MANIVELA = mot.CARRERA / 2                               # 44,2 mm
BIELA = 0.1448                                           # 5,7″ entre centros
ALTURA_COMPRESION = 0.0396                               # del bulón a la cabeza del pistón (1,56″)
BULON_ARRIBA = MANIVELA + BIELA                          # d del bulón con el pistón arriba de todo
RADIO_PISTON = mot.DIAMETRO / 2 - 0.0005
RADIO_CILINDRO = mot.DIAMETRO / 2
DECK = mot.DECK
BANCADA_R = 0.0311                                       # 2,45″
MUNON_R = 0.0267                                         # 2,10″
Y_MUNON0 = mot.CILINDRO_1_Y + mot.CORRIDA_BANCADA / 2    # entre el cilindro 1 y el 2
ANCHO_BIELA = 0.019

# Ángulo de cada muñón (A, B, C, D de adelante para atrás), horario mirado de frente, desde arriba,
# con el cigüeñal en 0° (cilindro 1 arriba). La fila izquierda está a +45°, la derecha a -45°.
MUNONES = [0 + 45, 90 + 45, 270 + 45, 180 + 45]
EXPLOTA = {1: 0, 8: 90, 4: 180, 3: 270, 6: 360, 5: 450, 7: 540, 2: 630}   # orden 1-8-4-3-6-5-7-2

# Distribución
LEVAS_Z = CIG_Z + 0.114                                  # eje del árbol de levas (en el medio de la V)
LEVA_BASE = 0.0195                                       # radio del círculo base de la leva
ALZADA = 0.0095                                          # lo que baja la válvula (≈0,375″)
RELACION = 1.5                                           # balancín 1,5 : 1
ALZADA_LEVA = ALZADA / RELACION
BOTADOR_LARGO = 0.05
# A lo largo del cilindro
D_VALVULA_CARA = 0.234                                   # cara de la cabeza de la válvula (en la cámara)
D_RESORTE_ASIENTO = 0.309                                # el resorte apoya acá (hundido en la tapa)
D_RETEN = 0.348                                          # retén de arriba del resorte
D_VALVULA_PUNTA = 0.356
D_BALANCIN = 0.362
T_VALVULA = 0.006                                        # las válvulas, apenas hacia afuera del eje
BRAZO_VALVULA = 0.038                                    # del balancín: rótula → válvula
BRAZO_VARILLA = BRAZO_VALVULA / RELACION                 # rótula → varilla
T_ROTULA = T_VALVULA - BRAZO_VALVULA
T_VARILLA = T_ROTULA - BRAZO_VARILLA
D_CAMARA = (0.222, 0.245)                                # cámara de combustión (hueco en la tapa)
RADIO_VALVULA = {"adm": 0.0493 / 2, "esc": 0.0381 / 2}
# Orden de las válvulas en cada tapa, de adelante para atrás: E-A-A-E-E-A-A-E
CORRIDA_VALVULA = 0.023


def clases_valvulas(k):
    """[(clase, corrimiento a lo largo)] del cilindro k (0 = el de adelante de esa fila)."""
    return [("esc", -CORRIDA_VALVULA), ("adm", CORRIDA_VALVULA)] if k % 2 == 0 else \
           [("adm", -CORRIDA_VALVULA), ("esc", CORRIDA_VALVULA)]


def polar(angulo, radio, centro_z=CIG_Z):
    """Punto (x, z) a 'angulo' grados horario desde arriba, mirado de frente."""
    a = math.radians(angulo)
    return radio * math.sin(a), centro_z + radio * math.cos(a)


def a_three(v):
    """De Blender (Z arriba) a Three.js (Y arriba)."""
    return [round(v[0], 5), round(v[2], 5), round(-v[1], 5)]


def poner_origen(obj, punto):
    """Mueve el origen del objeto a 'punto' (mundo) sin mover la malla."""
    punto = Vector(punto)
    obj.data.transform(Matrix.Translation(obj.location - punto))
    obj.location = punto


def con_marco(obj, matriz):
    """La malla se armó en coordenadas propias (alrededor del 0): la deja ahí y pone el objeto en
    'matriz' (posición y giro). Así el eje propio del objeto queda donde hace falta."""
    obj.data.transform(Matrix.Translation(obj.location))
    obj.location = (0, 0, 0)
    obj.matrix_world = matriz


def mover(m, matriz):
    """Lleva todo lo armado en la Malla con la matriz (se arma en coordenadas cómodas y se ubica)."""
    bmesh.ops.transform(m.bm, matrix=matriz, verts=m.bm.verts[:])


def marcar(obj, **props):
    for k, v in props.items():
        obj[k] = v
    obj["grupo"] = "motor"
    return obj


def materiales():
    mats = mot.materiales()
    mats["corte"] = mot.material("corte_mecanizado", "#b9b6af", 0.4, metal=0.75)
    mats["camisa"] = mot.material("camisa_brunida", "#cfd0cf", 0.22, metal=1.0)
    mats["forjado"] = mot.material("acero_forjado", "#5b5d61", 0.48, metal=1.0)
    mats["pulido"] = mot.material("acero_pulido", "#d5d6d8", 0.12, metal=1.0)
    mats["piston"] = mot.material("aluminio_piston", "#bfc0bc", 0.38, metal=1.0)
    return mats


# ----------------------------------------------------------------------------------------------
# Cigüeñal
# ----------------------------------------------------------------------------------------------
def perfil_brazo(angulo_munon):
    """Contorno (x, z) de un brazo del cigüeñal: abraza el muñón y lleva el contrapeso del otro lado."""
    puntos = []
    rho = MUNON_R + 0.009
    for k in range(44):
        ang = k * 360 / 44
        rel = math.radians(ang - angulo_munon)
        r = 0.041                                                  # alrededor de la bancada
        disc = rho ** 2 - (MANIVELA * math.sin(rel)) ** 2
        if disc > 0:
            r = max(r, MANIVELA * math.cos(rel) + math.sqrt(disc))  # alrededor del muñón
        lejos = abs(((ang - angulo_munon) % 360) - 180)            # 0 = justo enfrente del muñón
        if lejos < 58:
            r = max(r, 0.079)                                      # el contrapeso
        elif lejos < 80:
            r = max(r, 0.079 - (lejos - 58) / 22 * 0.038)
        puntos.append(polar(ang, r))
    return puntos


def engranaje(m, centro_xz, y0, y1, dientes, radio, mat, angulo0=0.0):
    """Rueda dentada de la cadena (perfil con dientes estirado a lo largo de Y)."""
    perfil = []
    for k in range(dientes * 2):
        r = radio if k % 2 == 0 else radio - 0.0045
        x, z = polar(angulo0 + k * 180 / dientes, r, 0)
        perfil.append((centro_xz[0] + x, centro_xz[1] + z))
    m.prisma(perfil, y0, y1, mat, bisel=0.0006)


def ciguenal(mats):
    m = Malla(["forjado", "pulido"])
    bancadas = [Y_MUNON0 - 0.0559 + j * mot.ENTRE_CILINDROS for j in range(5)]
    for y in bancadas:
        m.cilindro((0, y - 0.0125, CIG_Z), (0, y + 0.0125, CIG_Z), BANCADA_R, "pulido", lados=28, bisel=0.0015)
    for k, ang in enumerate(MUNONES):
        y = Y_MUNON0 + k * mot.ENTRE_CILINDROS
        x, z = polar(ang, MANIVELA)
        m.cilindro((x, y - 0.0274, z), (x, y + 0.0274, z), MUNON_R, "pulido", lados=24, bisel=0.0015)
        # Los dos brazos, uno de cada lado del muñón (con su contrapeso)
        for y0, y1 in ((y - 0.0434, y - 0.0274), (y + 0.0274, y + 0.0434)):
            m.prisma(perfil_brazo(ang), y0, y1, "forjado", bisel=0.003)
        # El agujero de aceite del muñón
        m.cilindro((x * 1.6, y, CIG_Z + (z - CIG_Z) * 1.6), (x * 1.62, y, CIG_Z + (z - CIG_Z) * 1.62), 0.004, "forjado", lados=8)
    # Adelante: la punta (donde va el balanceador) con la rueda de la cadena
    frente = bancadas[0] - 0.0125
    m.cilindro((0, frente - 0.085, CIG_Z), (0, frente, CIG_Z), 0.021, "pulido", lados=20, bisel=0.001)
    engranaje(m, (0, CIG_Z), -1.548, -1.535, 21, 0.027, "forjado")
    m.caja((0, -1.585, CIG_Z + 0.021), (0.006, 0.05, 0.004), "forjado")           # chaveta
    # Atrás: la brida del volante y el retén
    atras = bancadas[-1] + 0.0125
    m.cilindro((0, atras, CIG_Z), (0, atras + 0.06, CIG_Z), 0.027, "pulido", lados=24, bisel=0.001)
    m.cilindro((0, atras + 0.06, CIG_Z), (0, atras + 0.075, CIG_Z), 0.048, "forjado", lados=28, bisel=0.002)
    for k in range(6):
        x, z = polar(30 + k * 60, 0.036)
        m.cilindro((x, atras + 0.075, z), (x, atras + 0.08, z), 0.004, "pulido", lados=6)
    obj = m.objeto("ciguenal", mats)
    poner_origen(obj, (0, CIG_Y, CIG_Z))
    return marcar(obj, id="ciguenal", tipo="ciguenal")


# ----------------------------------------------------------------------------------------------
# Pistones y bielas (se arman parados sobre +Z con el bulón en el 0 y después se inclinan a su fila)
# ----------------------------------------------------------------------------------------------
def cilindros():
    """[(número, lado, k, y)] de los 8 cilindros."""
    lista = []
    for lado in (1, -1):
        for k, y in enumerate(mot.cilindros_y(lado)):
            lista.append((mot.numero_cilindro(lado, k), lado, k, y))
    return sorted(lista)


def en_su_cilindro(lado, y, d):
    """Matriz que lleva lo armado sobre +Z (origen en 0) al cilindro, con el 0 a 'd' del cigüeñal."""
    return Matrix.Translation(en_banco(lado, d, 0, y)) @ mot.rot_y(45 * lado)


def piston(mats, numero, lado, k, y):
    m = Malla(["piston", "pulido"])
    alto = ALTURA_COMPRESION
    falda = 0.036
    # El cuerpo: la falda, la zona de los aros y la cabeza apenas abombada, con su canto
    m.torno([(0.0, 0.0), (RADIO_PISTON - 0.0012, 0.0), (RADIO_PISTON, 0.004), (RADIO_PISTON, falda + alto - 0.0025),
             (RADIO_PISTON - 0.0015, falda + alto), (0.035, falda + alto + 0.0006), (0.0, falda + alto + 0.0008)],
            (0, 0, -falda), Z, "piston", lados=32)
    # Tres aros: dos de compresión y uno de aceite
    for h in (alto - 0.0055, alto - 0.0105, alto - 0.0165):
        m.cilindro((0, 0, h - 0.0009), (0, 0, h + 0.0009), RADIO_PISTON + 0.0003, "pulido", lados=32)
    # Los dos rebajes chicos para las válvulas, en la cabeza
    for clase, dy in clases_valvulas(k):
        m.cilindro((T_VALVULA * lado, dy, alto + 0.0002), (T_VALVULA * lado, dy, alto + 0.0009),
                   RADIO_VALVULA[clase] + 0.002, "piston", lados=24)
    # El bulón asoma a los dos costados
    m.cilindro((0, -RADIO_PISTON - 0.0003, 0), (0, RADIO_PISTON + 0.0003, 0), 0.0112, "pulido", lados=16)
    mover(m, en_su_cilindro(lado, y, BULON_ARRIBA))
    obj = m.objeto(f"piston-{numero}", mats)
    poner_origen(obj, en_banco(lado, BULON_ARRIBA, 0, y))
    return marcar(obj, tipo="piston", cilindro=numero, lado=lado, explota=EXPLOTA[numero],
                  manivela=MUNONES[k], eje=a_three(eje_banco(lado)))


def biela(mats, numero, lado, k, y):
    m = Malla(["forjado"])
    ancho = ANCHO_BIELA
    m.cilindro((0, -ancho / 2, 0), (0, ancho / 2, 0), 0.0155, "forjado", lados=20, bisel=0.0015)
    # El cuerpo (sección en I simplificada: más fino en el medio, con su nervio)
    plano = Matrix(((1, 0, 0, 0), (0, 0, 1, -0.006), (0, 1, 0, 0), (0, 0, 0, 1)))
    m.placa([(0.0095, -0.01), (0.017, -BIELA + 0.03), (-0.017, -BIELA + 0.03), (-0.0095, -0.01)], plano, 0.012,
            "forjado", bisel=0.002)
    for lado_i in (1, -1):
        m.caja((lado_i * 0.012, 0, -BIELA / 2 - 0.008), (0.006, ancho * 0.95, BIELA - 0.06), "forjado", bisel=0.0015)
    # El ojo grande con su tapa abulonada (abraza el muñón)
    m.cilindro((0, -ancho / 2, -BIELA), (0, ancho / 2, -BIELA), MUNON_R + 0.009, "forjado", lados=28, bisel=0.0015)
    m.caja((0, 0, -BIELA - 0.002), (0.082, ancho, 0.012), "forjado", bisel=0.002)
    for lado_i in (1, -1):
        m.cilindro((lado_i * 0.032, 0, -BIELA - 0.045), (lado_i * 0.032, 0, -BIELA + 0.012), 0.0042, "forjado", lados=8)
        m.cilindro((lado_i * 0.032, 0, -BIELA - 0.045), (lado_i * 0.032, 0, -BIELA - 0.037), 0.0065, "forjado", lados=6)
    mover(m, en_su_cilindro(lado, y, BULON_ARRIBA))
    obj = m.objeto(f"biela-{numero}", mats)
    poner_origen(obj, en_banco(lado, BULON_ARRIBA, 0, y))
    return marcar(obj, tipo="biela", cilindro=numero, lado=lado, explota=EXPLOTA[numero], manivela=MUNONES[k])


# ----------------------------------------------------------------------------------------------
# Árbol de levas, botadores, varillas, balancines, válvulas y resortes
# ----------------------------------------------------------------------------------------------
def valvulas_todas():
    """[(número, lado, k, y_valvula, clase)] de las 16 válvulas."""
    lista = []
    for numero, lado, k, y in cilindros():
        for clase, dy in clases_valvulas(k):
            lista.append((numero, lado, k, y + dy, clase))
    return lista


def pico_leva(numero, clase):
    """Hacia dónde apunta la punta de la leva con el árbol en 0° (horario desde arriba).
    La válvula está abierta del todo en el medio de su tiempo: escape a 270°, admisión a 450° del
    cigüeñal después de la explosión. El árbol gira a la mitad, en el mismo sentido."""
    pico = EXPLOTA[numero] + (270 if clase == "esc" else 450)
    lado = 1 if numero % 2 else -1
    return 45 * lado - pico / 2


def perfil_leva(pico):
    puntos = []
    for k in range(36):
        ang = k * 360 / 36
        delta = ((ang - pico + 180) % 360) - 180
        r = LEVA_BASE
        if abs(delta) < 45:
            r += ALZADA_LEVA * math.cos(math.pi * delta / 90)
        puntos.append(polar(ang, r, LEVAS_Z))
    return puntos


def arbol_levas(mats):
    m = Malla(["forjado", "pulido"])
    y0, y1 = mot.BLOQUE_Y[0] + 0.01, mot.BLOQUE_Y[1] - 0.02
    m.cilindro((0, y0, LEVAS_Z), (0, y1, LEVAS_Z), 0.0145, "forjado", lados=16)
    for j in range(5):
        y = Y_MUNON0 - 0.0559 + j * mot.ENTRE_CILINDROS
        m.cilindro((0, y - 0.009, LEVAS_Z), (0, y + 0.009, LEVAS_Z), 0.0237, "pulido", lados=24, bisel=0.001)
    for numero, lado, k, yv, clase in valvulas_todas():
        m.prisma(perfil_leva(pico_leva(numero, clase)), yv - 0.0068, yv + 0.0068, "pulido")
    # Adelante: la rueda grande de la cadena (el doble de dientes que la del cigüeñal: media vuelta)
    m.cilindro((0, y0, LEVAS_Z), (0, -1.535, LEVAS_Z), 0.02, "forjado", lados=16)
    engranaje(m, (0, LEVAS_Z), -1.548, -1.535, 42, 0.052, "forjado")
    m.cilindro((0, -1.535, LEVAS_Z), (0, -1.533, LEVAS_Z), 0.036, "forjado", lados=24)
    for k in range(3):
        x, z = polar(k * 120, 0.022, LEVAS_Z)
        m.tornillo((x, -1.548, z), -Y, mat="pulido", r=0.0055)
    obj = m.objeto("arbol-levas", mats)
    poner_origen(obj, (0, CIG_Y, LEVAS_Z))
    return marcar(obj, id="arbol-levas", tipo="levas")


def direccion_botador(lado):
    """Los botadores van inclinados como su fila (a 45°), apoyados arriba de la leva."""
    return Vector((math.sin(math.radians(45 * lado)), 0, math.cos(math.radians(45 * lado))))


def cadena(mats):
    """La cadena que une las dos ruedas (quieta: con el motor andando no se ve que corre)."""
    m = Malla(["acero"])
    puntos = []
    for k in range(10):          # media vuelta arriba (rueda grande) y media abajo (rueda chica)
        a = math.radians(-90 + k * 20)
        puntos.append((0.055 * math.sin(a), -1.5415, LEVAS_Z + 0.055 * math.cos(a)))
    for k in range(10):
        a = math.radians(90 + k * 20)
        puntos.append((0.030 * math.sin(a), -1.5415, CIG_Z + 0.030 * math.cos(a)))
    m.tubo(puntos, 0.0035, "acero", lados=4, ciclico=True, resolucion=3)
    obj = m.objeto("cadena-distribucion", mats)
    return marcar(obj, id="cadena-distribucion", tipo="fija")


def botador(mats, numero, lado, k, yv, clase):
    """Botador hidráulico (sobre la leva) y la varilla que sube hasta el balancín: se mueven juntos."""
    m = Malla(["acero"])
    eje = direccion_botador(lado)
    pie = Vector((0, yv, LEVAS_Z)) + eje * (LEVA_BASE + 0.0003)
    arriba = pie + eje * BOTADOR_LARGO
    m.torno([(0.0, 0.0), (0.0105, 0.0), (0.0105, BOTADOR_LARGO - 0.004), (0.009, BOTADOR_LARGO), (0.0, BOTADOR_LARGO)],
            pie, eje, "acero", lados=14)
    copa = en_banco(lado, D_BALANCIN - 0.0055, T_VARILLA, yv)
    m.cilindro(arriba - eje * 0.004, copa, 0.004, "acero", lados=8)
    m.esfera(copa, 0.0048, "acero", segmentos=8)
    obj = m.objeto(f"botador-{numero}-{clase}", mats)
    poner_origen(obj, pie)
    return marcar(obj, tipo="botador", cilindro=numero, lado=lado, clase=clase, explota=EXPLOTA[numero],
                  eje=a_three(eje))


def valvula(mats, numero, lado, k, yv, clase):
    m = Malla(["acero"])
    r = RADIO_VALVULA[clase]
    largo = D_VALVULA_PUNTA - D_VALVULA_CARA
    # Cabeza en forma de tulipa y el vástago, armados sobre +Z desde la cara
    m.torno([(0.0, 0.0), (r, 0.0), (r, 0.0022), (r * 0.62, 0.0075), (0.0052, 0.016), (0.0042, 0.024), (0.0042, largo),
             (0.0, largo)], (0, 0, 0), Z, "acero", lados=18)
    # El retén con las trabas, arriba (baja con la válvula)
    h = D_RETEN - D_VALVULA_CARA
    m.torno([(0.0055, h - 0.002), (0.0148, h), (0.0148, h + 0.0035), (0.0065, h + 0.006), (0.0, h + 0.006)],
            (0, 0, 0), Z, "acero", lados=12)
    mover(m, Matrix.Translation(en_banco(lado, D_VALVULA_CARA, T_VALVULA, yv)) @ mot.rot_y(45 * lado))
    obj = m.objeto(f"valvula-{numero}-{clase}", mats)
    poner_origen(obj, en_banco(lado, D_VALVULA_CARA, T_VALVULA, yv))
    return marcar(obj, tipo="valvula", cilindro=numero, lado=lado, clase=clase, explota=EXPLOTA[numero],
                  eje=a_three(eje_banco(lado)))


def resorte(mats, numero, lado, k, yv, clase):
    m = Malla(["acero"])
    largo = D_RETEN - D_RESORTE_ASIENTO
    vueltas, por_vuelta, radio = 5.5, 6, 0.0138
    puntos = []
    n = int(vueltas * por_vuelta)
    for i in range(n + 1):
        a = 2 * math.pi * i / por_vuelta
        puntos.append((radio * math.cos(a), radio * math.sin(a), 0.0022 + (largo - 0.0044) * (i / n)))
    m.tubo(puntos, 0.0021, "acero", lados=4, resolucion=2)
    m.cilindro((0, 0, 0), (0, 0, 0.0012), radio + 0.003, "acero", lados=16)        # el asiento
    obj = m.objeto(f"resorte-{numero}-{clase}", mats)
    w = eje_banco(lado)
    marco = Matrix.Translation(en_banco(lado, D_RESORTE_ASIENTO, T_VALVULA, yv)) @ mot.base_de(Y.cross(w), Y, w)
    con_marco(obj, marco)
    return marcar(obj, tipo="resorte", cilindro=numero, lado=lado, clase=clase, explota=EXPLOTA[numero],
                  largo=round(largo, 5))


def balancin(mats, numero, lado, k, yv, clase):
    """Balancín de chapa estampada: hamaca sobre la rótula, la varilla empuja de un lado y del otro
    baja la válvula."""
    m = Malla(["acero"])
    rot = mot.rot_y(45 * lado)
    t_medio = (T_VALVULA + T_VARILLA) / 2
    largo = T_VALVULA - T_VARILLA + 0.014
    # Las dos paredes laterales y el fondo (la «U» de chapa)
    for dy in (-0.0062, 0.0062):
        m.caja(en_banco(lado, D_BALANCIN + 0.002, t_medio, yv + dy), (largo, 0.0018, 0.012), "acero", rot, bisel=0.0007)
    m.caja(en_banco(lado, D_BALANCIN - 0.0035, t_medio, yv), (largo, 0.0142, 0.0018), "acero", rot, bisel=0.0006)
    # La punta que apoya en la válvula y la copa de la varilla
    m.caja(en_banco(lado, D_BALANCIN - 0.0045, T_VALVULA, yv), (0.008, 0.008, 0.003), "acero", rot, bisel=0.001)
    m.esfera(en_banco(lado, D_BALANCIN, T_ROTULA, yv), 0.0075, "acero", segmentos=8)      # la rótula
    obj = m.objeto(f"balancin-{numero}-{clase}", mats)
    poner_origen(obj, en_banco(lado, D_BALANCIN, T_ROTULA, yv))
    return marcar(obj, tipo="balancin", cilindro=numero, lado=lado, clase=clase, explota=EXPLOTA[numero],
                  brazo=BRAZO_VALVULA)


def esparragos(mats):
    """Los 16 espárragos con su tuerca, donde se apoya cada balancín (quietos)."""
    m = Malla(["acero"])
    for numero, lado, k, yv, clase in valvulas_todas():
        abajo = en_banco(lado, DECK + mot.CABEZA_ALTO - 0.004, T_ROTULA, yv)
        tuerca = en_banco(lado, D_BALANCIN + 0.0075, T_ROTULA, yv)
        m.cilindro(abajo, tuerca + eje_banco(lado) * 0.016, 0.0042, "acero", lados=8)
        m.cilindro(tuerca, tuerca + eje_banco(lado) * 0.009, 0.0072, "acero", lados=6, bisel=0.0008, segmentos=1)
    obj = m.objeto("esparragos", mats)
    return marcar(obj, tipo="fija")


# ----------------------------------------------------------------------------------------------
# El corte del bloque y de las tapas de cilindros
# ----------------------------------------------------------------------------------------------
def cortadores_bloque(mats):
    """Lo que se le saca al bloque: las camisas (el hueco de cada cilindro), la mitad de afuera de cada
    fila y lo de abajo del cigüeñal (dos semiespacios desde el eje de cada fila) y el techo del valle."""
    largo = 1.0
    cortes = Malla(["corte"])
    for lado in (1, -1):
        centro = en_banco(lado, 0.15, 0.4, CIG_Y)
        cortes.caja(centro, (0.8, largo, 1.4), "corte", mot.rot_y(45 * lado))
    cortes.caja((0, CIG_Y, CIG_Z + 0.085 + 0.3), (0.14, largo, 0.6), "corte")
    camisas = Malla(["camisa"])
    for numero, lado, k, y in cilindros():
        camisas.cilindro(en_banco(lado, 0.06, 0, y), en_banco(lado, DECK + 0.02, 0, y), RADIO_CILINDRO, "camisa", lados=40)
    return [cortes.objeto("tmp_corte", mats), camisas.objeto("tmp_camisas", mats)]


def cortadores_tapas(mats):
    largo = 1.0
    cortes = Malla(["corte"])
    for lado in (1, -1):
        # En las tapas el corte va un poco más adentro, así se ven enteros válvulas y resortes
        centro = en_banco(lado, 0.3, 0.4 - 0.012, CIG_Y)
        cortes.caja(centro, (0.8, largo, 1.0), "corte", mot.rot_y(45 * lado))
    camaras = Malla(["camisa"])
    for numero, lado, k, y in cilindros():
        camaras.cilindro(en_banco(lado, D_CAMARA[0], 0, y), en_banco(lado, D_CAMARA[1], 0, y), RADIO_CILINDRO, "camisa", lados=36)
    return [cortes.objeto("tmp_corte_tapas", mats), camaras.objeto("tmp_camaras", mats)]


def cortar(obj, cortadores):
    col = bpy.data.collections.new("tmp_cortadores")
    bpy.context.scene.collection.children.link(col)
    for c in cortadores:
        for coleccion in list(c.users_collection):
            coleccion.objects.unlink(c)
        col.objects.link(c)
    mod = obj.modifiers.new("corte", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.operand_type = "COLLECTION"
    mod.collection = col
    mod.material_mode = "TRANSFER"
    mot.aplicar_modificadores(obj)
    # Las normales de antes no sirven en las caras nuevas: se rehacen
    with bpy.context.temp_override(selected_editable_objects=[obj], active_object=obj, object=obj):
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    mot.suavizar(obj, 32)
    wn = obj.modifiers.new("normales", "WEIGHTED_NORMAL")
    wn.mode, wn.weight, wn.keep_sharp = "FACE_AREA", 50, True
    mot.aplicar_modificadores(obj)


def borrar_cortadores():
    for c in list(bpy.data.objects):
        if c.name.startswith("tmp_"):
            bpy.data.objects.remove(c)
    for col in list(bpy.data.collections):
        if col.name.startswith("tmp_"):
            bpy.data.collections.remove(col)


def bloque_corte(mats):
    obj = mot.bloque(mats)
    obj.name = obj.data.name = "bloque-corte"
    cortar(obj, cortadores_bloque(mats))
    borrar_cortadores()
    return marcar(obj, tipo="corte", reemplaza="bloque")


def tapas_corte(mats):
    grupo = mot.tapas_cilindros(mats)
    grupo.name = "tapas-cilindros-corte"
    bpy.context.view_layer.update()
    for hijo in grupo.children:
        base = hijo.name
        hijo.name = hijo.data.name = f"{base}-corte"
        cortar(hijo, cortadores_tapas(mats))
        borrar_cortadores()
        marcar(hijo, tipo="corte", reemplaza=base)
    return marcar(grupo, tipo="corte", reemplaza="tapas-cilindros")


# ----------------------------------------------------------------------------------------------
# Armado y exportación
# ----------------------------------------------------------------------------------------------
def grupo(nombre, hijos, tipo):
    e = mot.vacio(nombre, hijos)
    return marcar(e, id=nombre, tipo=tipo)


def construir():
    mats = materiales()
    objs = {}
    objs["bloque-corte"] = bloque_corte(mats)
    objs["tapas-cilindros-corte"] = tapas_corte(mats)
    objs["ciguenal"] = ciguenal(mats)
    objs["arbol-levas"] = arbol_levas(mats)
    objs["cadena-distribucion"] = cadena(mats)
    objs["esparragos"] = esparragos(mats)
    objs["pistones"] = grupo("pistones", [piston(mats, *c) for c in cilindros()], "grupo")
    objs["bielas"] = grupo("bielas", [biela(mats, *c) for c in cilindros()], "grupo")
    valvs = valvulas_todas()
    objs["valvulas"] = grupo("valvulas", [valvula(mats, *v) for v in valvs], "grupo")
    objs["resortes-valvulas"] = grupo("resortes-valvulas", [resorte(mats, *v) for v in valvs], "grupo")
    objs["balancines"] = grupo("balancines", [balancin(mats, *v) for v in valvs], "grupo")
    objs["botadores"] = grupo("botadores", [botador(mats, *v) for v in valvs], "grupo")

    raiz = bpy.data.objects.new("motor_interno", None)
    raiz.empty_display_type = "PLAIN_AXES"
    bpy.context.scene.collection.objects.link(raiz)
    for o in objs.values():
        o.parent = raiz
    # Las medidas que usa js/modulos/motor-vivo.js (en coordenadas de Three.js)
    marcar(raiz, tipo="raiz",
           centro_ciguenal=a_three((0, CIG_Y, CIG_Z)), centro_levas=a_three((0, CIG_Y, LEVAS_Z)),
           radio_manivela=MANIVELA, biela=BIELA, alzada=ALZADA, relacion=RELACION,
           altura_compresion=ALTURA_COMPRESION, radio_cilindro=RADIO_CILINDRO,
           d_camara=D_CAMARA[1] - 0.004, d_bulon_arriba=BULON_ARRIBA,
           orden_encendido=[1, 8, 4, 3, 6, 5, 7, 2])
    objs["motor_interno"] = raiz
    return objs


def ruta_salida():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args:
        return os.path.abspath(args[0])
    return os.path.join(AQUI, "..", "modelos", "motor_interno.glb")


def controlar():
    """Cuentas rápidas para ver que nada choca (no frena: solo escribe)."""
    arriba = BULON_ARRIBA + ALTURA_COMPRESION
    print(f"  cabeza del pistón arriba de todo: {arriba * 1000:.1f} mm (cara del bloque {DECK * 1000:.1f} mm)")
    print(f"  cabeza del pistón abajo de todo:  {(arriba - mot.CARRERA) * 1000:.1f} mm")
    print(f"  balancín: {BRAZO_VARILLA * 1000:.1f} mm del lado de la varilla, {BRAZO_VALVULA * 1000:.1f} mm de la válvula")
    for numero in (1, 2):
        print(f"  cilindro {numero}: leva de escape a {pico_leva(numero, 'esc') % 360:.0f}°, de admisión a {pico_leva(numero, 'adm') % 360:.0f}°")


if __name__ == "__main__":
    mot.limpiar_escena()
    objetos = construir()
    print("Control:")
    controlar()
    salida = ruta_salida()
    mot.exportar(objetos, salida)
    tris = 0
    for o in mot.todos(objetos):
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
    print(f"Listo: {os.path.normpath(salida)} ({os.path.getsize(salida) / 1024:.0f} KB, {tris} triángulos)")
