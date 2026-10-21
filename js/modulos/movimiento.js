/*
  Lo que comparten Separar y Paso a paso: hacia dónde se va cada pieza y cómo vuelve.

  Cada ficha con modelo se mueve como una o varias «unidades»:
    · Si la pieza es un grupo de cosas separadas (las 4 llantas, los 2 faros, las 2 puertas…),
      cada una es una unidad y se va para su lado.
    · Si no, toda la pieza es una unidad.
  Las cosas sin ficha (faldones, interior, vano del motor…) acompañan a la pieza que les toca.

  Cada unidad tiene dos corrimientos, guardados en el sistema de su padre:
    · separar → la vista desarmada (el motor sube arriba del auto y sus piezas se abren alrededor).
    · llegar  → de dónde llega la pieza en el Paso a paso (el motor se arma en su lugar, sin subir),
                y adónde va cuando se separa sola.
  Y tres cantidades de 0 a 1: «general» (la barra), «propio» (Separar esta pieza) y «paso».
*/

const ELEVAR_MOTOR = 0.95; // cuánto sube el motor entero al separar, en metros

const signo = (v) => (v >= 0 ? 1 : -1);
const aLosCostados = (c, margen = 0.3) => (Math.abs(c.x) > margen ? signo(c.x) : 0);

// Hacia dónde se va cada pieza al separar, en metros (x = costado, y = arriba, z = adelante).
// c es el centro de la pieza (o de cada parte, si la pieza va de a varias).
const SEPARAR = {
  carroceria: () => [0, 0, 0],
  capot: () => [-1.55, 1.0, 0.35], // al costado de atrás: así no tapa el motor desde la vista inicial
  puertas: (c) => [signo(c.x) * 0.95, 0.04, 0.1],
  'tapa-baul': () => [0, 0.85, -0.55],
  'paragolpes-delantero': () => [0, 0, 0.95],
  'paragolpes-trasero': () => [0, 0, -0.85],
  parrilla: () => [0, 0.02, 0.62],
  faros: (c) => [signo(c.x) * 0.22, 0, 0.72],
  'luces-posicion': (c) => [signo(c.x) * 0.38, -0.02, 0.4],
  'luces-traseras': (c) => [signo(c.x) * 0.2, 0.05, -0.55],
  'tapa-nafta': () => [0, 0.25, -0.45],
  'emblemas-ss': (c) => (aLosCostados(c) ? [signo(c.x) * 0.5, 0.12, 0] : [0, 0.14, 0.82]),
  'llantas-rally': (c) => [signo(c.x) * 0.62, 0, 0],
  vidrios: (c) => (aLosCostados(c)
    ? [signo(c.x) * 0.42, 0.42, 0]
    : [0, 0.6, signo(c.z + 0.4) * 0.35]),
  espejo: () => [0.75, 0.3, 0.1],

  // Motor: estos corrimientos son alrededor del motor ya subido.
  bloque: () => [0, 0, 0],
  'tapas-cilindros': (c) => [signo(c.x) * 0.3, 0.06, 0],
  carter: () => [0, -0.32, 0],
  'multiple-admision': () => [0, 0.3, 0],
  'tapas-valvulas': (c) => [signo(c.x) * 0.48, 0.22, 0],
  'multiples-escape': (c) => [signo(c.x) * 0.55, -0.12, 0],
  'bomba-agua': () => [0, -0.05, 0.26],
  'motor-arranque': () => [-0.42, -0.2, -0.05],
  distribuidor: () => [0.05, 0.48, -0.42],
  bobina: () => [-0.32, 0.45, -0.36],
  'cables-bujias': () => [0, 0.16, -0.12],
  alternador: () => [0.45, 0.1, 0.32],
  correas: () => [0.05, 0.02, 0.42],
  ventilador: () => [0, 0, 0.58],
  carburador: () => [0, 0.42, 0],
  'filtro-aire': () => [0, 0.66, 0],
  radiador: () => [0, 0.05, 0.78],
  bateria: () => [0.55, 0.3, 0.3],
};

// De dónde llega cada pieza en el Paso a paso, cuando no alcanza con el corrimiento de separar.
const LLEGAR = {
  carroceria: () => [0, 1.6, 0],
  bloque: () => [0, 0.8, 0],
};

// Las cosas sin ficha se mueven con la pieza que les toca (el resto, con la carrocería).
const ACOMPANA = {
  'faldon-delantero': 'paragolpes-delantero',
  'luces-estacionamiento': 'paragolpes-delantero',
  'faldon-trasero': 'paragolpes-trasero',
  'marcadores-traseros': 'paragolpes-trasero',
};

const instancias = new WeakMap();

// Lleva la cámara a mostrar entera una esfera (centro + radio), desde donde está mirando ahora.
export function encuadrarEsfera(api, esfera, { factor = 1, bajar = 1 } = {}) {
  const { THREE, camara, controles } = api;
  const fovV = THREE.MathUtils.degToRad(camara.fov);
  const fovH = 2 * Math.atan(Math.tan(fovV / 2) * camara.aspect);
  const distancia = (esfera.radius / Math.sin(Math.min(fovV, fovH) / 2)) * factor;
  const direccion = camara.position.clone().sub(controles.target).normalize();
  const objetivo = esfera.center.clone();
  objetivo.y *= bajar;
  const posicion = objetivo.clone().addScaledVector(direccion, distancia);
  const p0 = camara.position.clone();
  const o0 = controles.target.clone();
  return api.animar(1, (k) => {
    camara.position.lerpVectors(p0, posicion, k);
    controles.target.lerpVectors(o0, objetivo, k);
  });
}

export function obtenerMovimiento(api) {
  if (!instancias.has(api)) instancias.set(api, crearMovimiento(api));
  return instancias.get(api);
}

function crearMovimiento(api) {
  const { THREE, piezas, fichas, raiz } = api;
  const sinAcentos = (t) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const esMotor = (id) => sinAcentos(fichas.get(id)?.grupo ?? '').includes('motor');
  const nombreLimpio = (o) => o.name.replace(/(_\d+|\.?\d{3})$/, '').replaceAll('_', '-');
  const esPiso = (o) => /^(piso|suelo|estudio|floor)/i.test(o.name);

  raiz.updateMatrixWorld(true);
  const centroAuto = new THREE.Box3().setFromObject(piezas.get('carroceria') ?? raiz).getCenter(new THREE.Vector3());

  // Una pieza «va de a varias» si es un grupo cuyos hijos no son sus propios pedazos (capot_1, capot_2…).
  function partesDe(id, objeto) {
    const hijos = objeto.children.filter((h) => h.name);
    const deAVarias = !objeto.isMesh && hijos.length > 1 && hijos.every((h) => !h.name.startsWith(`${objeto.name}_`));
    return deAVarias ? hijos : [objeto];
  }

  function haciaDondeSepara(id, centro) {
    const regla = SEPARAR[id];
    if (regla) return new THREE.Vector3(...regla(centro));
    // Pieza que no está en la tabla: se aleja del centro de su grupo y un poco para arriba.
    const desde = esMotor(id) ? centroMotor : centroAuto;
    const direccion = centro.clone().sub(desde);
    direccion.y = Math.max(direccion.y, 0) + 0.3;
    return direccion.normalize().multiplyScalar(0.6);
  }

  // Pasa un corrimiento del mundo al sistema del padre del objeto (así anda aunque esté adentro de otro).
  function corrimientoLocal(objeto, mundo) {
    const padre = objeto.parent;
    const a = padre.worldToLocal(new THREE.Vector3());
    const b = padre.worldToLocal(mundo.clone());
    return b.sub(a);
  }

  const centroMotor = (() => {
    const caja = new THREE.Box3();
    for (const [id, objeto] of piezas) if (esMotor(id)) caja.expandByObject(objeto);
    return caja.isEmpty() ? new THREE.Vector3(0, 0.6, 1.2) : caja.getCenter(new THREE.Vector3());
  })();

  const unidades = new Map(); // id de ficha → [unidad]
  const todas = [];

  function sumarUnidad(id, objetos, centro) {
    const separar = haciaDondeSepara(id, centro);
    const motor = esMotor(id);
    if (motor) separar.y += ELEVAR_MOTOR;
    // Para el paso a paso, el motor se arma en su lugar: sin la subida.
    let llegar = LLEGAR[id] ? new THREE.Vector3(...LLEGAR[id](centro)) : separar.clone();
    if (motor && !LLEGAR[id]) llegar.y -= ELEVAR_MOTOR;
    if (llegar.length() < 0.2) llegar.setLength(0.2).add(new THREE.Vector3(0, 0.45, 0));
    const unidad = {
      id,
      retraso: 0,
      general: 0, propio: 0, paso: 0,
      objetos: objetos.map((objeto) => ({
        objeto,
        p0: objeto.position.clone(),
        separar: corrimientoLocal(objeto, separar),
        llegar: corrimientoLocal(objeto, llegar),
      })),
    };
    if (!unidades.has(id)) unidades.set(id, []);
    unidades.get(id).push(unidad);
    todas.push(unidad);
    return unidad;
  }

  for (const [id, objeto] of piezas) {
    for (const parte of partesDe(id, objeto)) {
      sumarUnidad(id, [parte], new THREE.Box3().setFromObject(parte).getCenter(new THREE.Vector3()));
    }
  }

  // Los acompañantes: lo de primer nivel de cada .glb que no tiene ficha ni es el piso.
  const conFicha = new Set(piezas.values());
  const contienePieza = (o) => {
    let si = false;
    o.traverse((x) => { if (x !== o && conFicha.has(x)) si = true; });
    return si;
  };
  for (const escenaGlb of raiz.children) {
    for (const o of escenaGlb.children) {
      if (conFicha.has(o) || esPiso(o) || contienePieza(o)) continue;
      let tieneMalla = false;
      o.traverse((x) => { if (x.isMesh) tieneMalla = true; });
      if (!tieneMalla) continue; // marcas vacías de Blender
      const id = ACOMPANA[nombreLimpio(o)] ?? 'carroceria';
      const unidad = unidades.get(id)?.[0];
      if (!unidad) continue;
      // Se mueve igual que la primera parte de su pieza (en el mundo)
      const ref = unidad.objetos[0];
      const mundo = (local) => ref.objeto.parent.localToWorld(local.clone()).sub(ref.objeto.parent.localToWorld(new THREE.Vector3()));
      unidad.objetos.push({
        objeto: o,
        p0: o.position.clone(),
        separar: corrimientoLocal(o, mundo(ref.separar)),
        llegar: corrimientoLocal(o, mundo(ref.llegar)),
      });
    }
  }

  // Al separar con la barra: primero se abre la carrocería y después se desarma el motor.
  const ordenIds = api.orden.filter((id) => unidades.has(id));
  const motorIds = ordenIds.filter(esMotor);
  for (const id of ordenIds) {
    const retraso = esMotor(id)
      ? 0.16 + 0.2 * (motorIds.indexOf(id) / Math.max(motorIds.length - 1, 1))
      : 0.1 * ((ordenIds.indexOf(id) % 6) / 5);
    for (const u of unidades.get(id)) u.retraso = retraso;
  }

  const curva = (k) => k * k * (3 - 2 * k); // arranca y frena suave
  let general = 0;

  function aplicar() {
    for (const u of todas) {
      const k = curva(THREE.MathUtils.clamp((general - u.retraso) / (1 - u.retraso), 0, 1));
      u.general = k;
      // Sola, una pieza se aparta lo justo (sin que el motor suba); con todo separado, manda la barra.
      const sola = u.propio * (1 - k) + u.paso;
      for (const o of u.objetos) {
        o.objeto.position.copy(o.p0).addScaledVector(o.separar, k).addScaledVector(o.llegar, sola);
      }
    }
    api.pedirRender();
  }

  // Anima una cantidad («propio» o «paso») de las unidades de una pieza. Si llega otra orden, manda la última.
  function animarCantidad(id, cantidad, hasta, segundos) {
    const lista = unidades.get(id) ?? [];
    if (!lista.length) return Promise.resolve();
    const turno = {};
    for (const u of lista) u[`turno_${cantidad}`] = turno;
    const desde = lista.map((u) => u[cantidad]);
    return api.animar(segundos, (k) => {
      lista.forEach((u, i) => {
        if (u[`turno_${cantidad}`] !== turno) return;
        // Las partes de una misma pieza salen apenas desfasadas: se nota que son varias.
        const r = lista.length > 1 ? (i / (lista.length - 1)) * 0.18 : 0;
        const kk = THREE.MathUtils.clamp((k - r) / (1 - r), 0, 1);
        u[cantidad] = desde[i] + (hasta - desde[i]) * kk;
      });
      aplicar();
    });
  }

  return {
    unidades,
    esMotor,
    tieneModelo: (id) => unidades.has(id),
    fijarGeneral(valor) { general = valor; aplicar(); },
    propio: (id) => unidades.get(id)?.[0]?.propio ?? 0,
    animarPropio: (id, hasta, segundos = 0.8) => animarCantidad(id, 'propio', hasta, segundos),
    animarPaso: (id, hasta, segundos = 0.75) => animarCantidad(id, 'paso', hasta, segundos),
    fijarPaso(id, valor) {
      for (const u of unidades.get(id) ?? []) { u.paso = valor; u.turno_paso = null; }
      aplicar();
    },
    mostrar(id, visible) {
      for (const u of unidades.get(id) ?? []) for (const o of u.objetos) o.objeto.visible = visible;
      api.pedirRender();
    },
    reiniciarPropios() {
      for (const u of todas) { u.propio = 0; u.turno_propio = null; }
      aplicar();
    },
    aplicar,
  };
}
