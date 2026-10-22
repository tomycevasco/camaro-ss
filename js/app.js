/*
  Camaro SS · la pantalla 3D
  ---------------------------------------------------------------------------
  Qué carga:
    1. modelos/manifiesto.json → la lista de .glb, cómo se abren capot/puertas/baúl y los módulos.
    2. datos/fichas.json       → las fichas de las piezas.
    3. Cada .glb del manifiesto (si falta, sigue; si tiene "reemplazo", pone un cubo gris).

  Cómo se reconoce una pieza:
    El objeto del .glb cuyo nombre (o la propiedad "id" puesta en Blender) es igual al "id" de su
    ficha. Se toma el objeto más de arriba con ese nombre: sus hijos se marcan y se mueven con él.
    Si Blender le agregó ".001" al nombre, igual se reconoce.

  Enganches para las otras tandas (sin tocar este archivo):
    · js/modulos/separar.js      → export function iniciar(api) { return { fijar(valor0a1), separarPieza(id) } }
                                   separarPieza devuelve true si la pieza quedó afuera, false si volvió.
    · js/modulos/paso-a-paso.js  → export function iniciar(api) { return { entrar(), salir(), siguiente(), anterior() } }
                                   y avisa cada paso con api.actualizarPaso({ actual, total, id, texto }).
    · js/modulos/vista-motor.js  → el botón «Motor»: saca el motor al soporte (avisa con el evento «vista-motor» en document).
    · js/modulos/motor-vivo.js   → Prender / Acelerar / Por adentro. Se muestra mientras la vista Motor está activa;
                                   lo que trae motor_interno.glb se suma a las piezas tocables apenas se baja.
    Si separar o paso a paso no existen, se usa la versión simple que está acá abajo («separadorBase», «pasoBase»).
    Las rutas salen de manifiesto.json → modulos; si falta alguna, se usa la de RUTAS_MODULOS.

  Controles sin rueda (Tomás usa touchpad): arrastrar gira · pellizcar, botones + / − o teclas + / − acercan ·
  Mayúscula + arrastrar o las flechas desplazan · Mayúscula + flechas giran · A ve por adentro · 0 vuelve.

    El objeto «api» que reciben trae:
      THREE, escena, camara, controles, renderer, raiz (todo lo cargado),
      piezas (Map id → objeto 3D), fichas (Map id → ficha), orden (ids en el orden de la lista),
      seleccionar(id, { enfocar }), seleccionada(), pedirRender(), animar(segundos, fn(k 0..1), curva?) → Promise,
      centroDe(objeto) → Vector3 en el mundo, actualizarPaso(estado), avisar(texto),
      abrir(clave, abierta) (capot, puertas, baul), enfocar(objeto), vistaInicial(animado, margen),
      on(evento, fn) con los eventos «seleccion» (detail: id o null), «modo» (detail: modo), «separacion» (detail: 0..1).
*/

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

// El decodificador Draco de la misma copia de Three.js que usa el importmap de index.html
const RUTA_DRACO = new URL('../vendor/three/examples/jsm/libs/draco/gltf/', import.meta.url).href;
const ACENTO = new THREE.Color('#d9600b');
const ARRIBA = new THREE.Vector3(0, 1, 0);
const sinMovimiento = matchMedia('(prefers-reduced-motion: reduce)');
const esAngosto = matchMedia('(max-width: 820px)');

const RUTAS_MODULOS = {
  separar: 'js/modulos/separar.js',
  paso_a_paso: 'js/modulos/paso-a-paso.js',
  vista_motor: 'js/modulos/vista-motor.js',
  motor_vivo: 'js/modulos/motor-vivo.js',
};

const MANIFIESTO_BASE = {
  frente: '+z',
  modelos: [{ archivo: 'carroceria.glb', reemplazo: { centro: [0, 0.65, 0], tamano: [1.84, 1.3, 4.69] } }],
  aberturas: {},
  modulos: {},
};

const $ = (selector) => document.querySelector(selector);
const el = {
  escena: $('#escena'), vista: $('#vista'), lienzo: $('#lienzo'),
  carga: $('#carga'), cargaProgreso: $('#carga-progreso'), aviso: $('#aviso'),
  guia: $('#guia'), guiaLinea: $('#guia-linea'), guiaPunto: $('#guia-punto'),
  ficha: $('#ficha'), fichaGrupo: $('#ficha-grupo'), fichaTitulo: $('#ficha-titulo'),
  fichaTexto: $('#ficha-texto'), fichaFalta: $('#ficha-falta'), fichaDato: $('#ficha-dato'),
  fichaSaber: $('#ficha-saber'), fichaCerrar: $('#ficha-cerrar'),
  fichaSeparar: $('#ficha-separar'), fichaSiguiente: $('#ficha-siguiente'),
  buscar: $('#buscar'), lista: $('#lista-piezas'), sinResultados: $('#sin-resultados'),
  separacion: $('#separacion'), vistaInicial: $('#vista-inicial'),
  paso: $('#paso'), pasoTexto: $('#paso-texto'), pasoAnterior: $('#paso-anterior'), pasoSiguiente: $('#paso-siguiente'),
  acercar: $('#acercar'), alejar: $('#alejar'), verAdentro: $('#ver-adentro'),
  ayuda: $('#ayuda'), abrirAyuda: $('#abrir-ayuda'), cerrarAyuda: $('#ayuda-entendido'), botonMotor: $('[data-vista-motor]'),
};

const eventos = new EventTarget();
const emitir = (nombre, detail) => eventos.dispatchEvent(new CustomEvent(nombre, { detail }));

const estado = {
  modo: 'explorar',
  seleccion: null,
  separacion: 0,
  manifiesto: MANIFIESTO_BASE,
};

const fichas = new Map();     // id → ficha normalizada
const piezas = new Map();     // id → Object3D
const idPorObjeto = new Map(); // Object3D raíz de pieza → id
let orden = [];               // ids en el orden de la lista

/* ===================== 3D base ===================== */

let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas: el.lienzo, antialias: true, alpha: true, powerPreference: 'high-performance' });
} catch {
  mostrarError('Tu navegador no puede mostrar 3D. Probá con Chrome, Edge o Safari actualizados.');
  throw new Error('Sin WebGL');
}
// Si no hay placa de video de verdad (el navegador dibuja «a mano» con el procesador), cada cuadro
// cuesta muchísimo: ahí va el modo liviano (sin sombras en tiempo real, pintura más simple, menos nitidez).
const modoLiviano = (() => {
  const gl = renderer.getContext();
  const info = gl.getExtension('WEBGL_debug_renderer_info');
  const placa = String(info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
  return /swiftshader|llvmpipe|softpipe|software|basic render|microsoft basic/i.test(placa);
})();

// Nitidez: en el celular, 1,5 alcanza (más es casi el doble de trabajo por cuadro y no se nota).
renderer.setPixelRatio(modoLiviano ? 1 : Math.min(devicePixelRatio, esAngosto.matches ? 1.5 : 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = !modoLiviano;
renderer.shadowMap.type = THREE.PCFShadowMap;

// Si la placa de video se cuelga o el sistema la reinicia, el 3D se pierde: lo avisamos en vez de quedar en blanco.
el.lienzo.addEventListener('webglcontextlost', (e) => {
  e.preventDefault();
  el.carga.classList.remove('listo');
  el.carga.removeAttribute('aria-hidden');
  mostrarError('Se cortó el 3D (la placa de video se reinició). Recargá la página.', true);
});

const escena = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
escena.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
escena.environmentIntensity = 0.9;

const LENTE = 32;        // ángulo de la cámara afuera (el de la muestra)
const LENTE_CABINA = 62; // adentro se abre, para ver la cabina entera
const camara = new THREE.PerspectiveCamera(LENTE, 1, 0.05, 200);
camara.position.set(5, 2.2, 6);

const controles = new OrbitControls(camara, el.lienzo);
controles.enableDamping = true;
controles.dampingFactor = 0.08;
controles.maxPolarAngle = Math.PI * 0.485; // que no se meta abajo del piso
controles.screenSpacePanning = true;
// Sin mouse: arrastrar con un dedo gira; Mayúscula + arrastrar desplaza (lo trae OrbitControls);
// el pellizco del touchpad llega como «rueda con Ctrl» y acerca. Las teclas y los botones + / − van aparte.
controles.enableZoom = true;
controles.enablePan = true;
controles.zoomSpeed = 1.1;
controles.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
controles.addEventListener('change', pedirRender);

const luzCielo = new THREE.HemisphereLight(0xffffff, 0xd9d6cf, 0.6);
escena.add(luzCielo);
const sol = new THREE.DirectionalLight(0xffffff, 1.6);
sol.castShadow = true;
sol.shadow.mapSize.setScalar(esAngosto.matches ? 1024 : 2048);
sol.shadow.bias = -0.0004;
sol.shadow.normalBias = 0.02;
sol.shadow.radius = 4;
escena.add(sol, sol.target);

const raiz = new THREE.Group();
raiz.name = 'camaro';
escena.add(raiz);

const cajaAuto = new THREE.Box3(new THREE.Vector3(-0.92, 0, -2.35), new THREE.Vector3(0.92, 1.3, 2.35));

/* ===================== Dibujo a demanda ===================== */
// Se dibuja solo cuando algo cambia: así el celular no se calienta con el auto quieto.

let hayQueDibujar = true;
let preparando = true; // mientras se arman las pinturas no se dibuja (dibujar las armaría de golpe y congelaría la página)
const animaciones = new Set();
const reloj = new THREE.Timer();

function pedirRender() { hayQueDibujar = true; }

const suave = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const lineal = (k) => k;

function animar(segundos, fn, curva = suave) {
  const duracion = sinMovimiento.matches ? 0 : segundos;
  return new Promise((resolver) => {
    animaciones.add({ t: 0, duracion, fn, resolver, curva });
    pedirRender();
  });
}

function bucle(ahora) {
  requestAnimationFrame(bucle);
  reloj.update(ahora);
  const dt = Math.min(reloj.getDelta(), 0.1);
  for (const a of animaciones) {
    a.t += dt;
    const k = a.duracion === 0 ? 1 : Math.min(a.t / a.duracion, 1);
    a.fn(a.curva(k));
    if (k >= 1) { animaciones.delete(a); a.resolver(); }
    hayQueDibujar = true;
  }
  if (controles.update(dt)) hayQueDibujar = true;
  if (!hayQueDibujar || preparando) return;
  hayQueDibujar = false;
  renderer.render(escena, camara);
  dibujarGuia();
}

/* ===================== Tamaño y encuadre ===================== */

function ajustarTamano() {
  const { clientWidth: ancho, clientHeight: alto } = el.vista;
  if (!ancho || !alto) return;
  renderer.setSize(ancho, alto, false);
  camara.aspect = ancho / alto;
  // En la compu la ficha flota a la derecha: corro el auto un poco a la izquierda.
  if (!esAngosto.matches) camara.setViewOffset(ancho, alto, Math.min(170, ancho * 0.13), 0, ancho, alto);
  else camara.clearViewOffset();
  camara.updateProjectionMatrix();
  pedirRender();
}
new ResizeObserver(ajustarTamano).observe(el.vista);

function vectorFrente() {
  const texto = String(estado.manifiesto.frente || '+z').trim().toLowerCase();
  const signo = texto.startsWith('-') ? -1 : 1;
  const eje = texto.replace(/[+-]/, '');
  return new THREE.Vector3(eje === 'x' ? signo : 0, 0, eje === 'z' ? signo : 0);
}

function encuadreInicial() {
  const centro = cajaAuto.getCenter(new THREE.Vector3());
  const radio = cajaAuto.getBoundingSphere(new THREE.Sphere()).radius;
  const frente = vectorFrente();
  const izquierda = new THREE.Vector3().crossVectors(ARRIBA, frente);
  // 3/4 de adelante, del lado izquierdo, un poco desde arriba (como la muestra)
  const direccion = frente.clone().add(izquierda.multiplyScalar(0.95)).addScaledVector(ARRIBA, 0.5).normalize();
  const fovV = THREE.MathUtils.degToRad(LENTE);
  const fovH = 2 * Math.atan(Math.tan(fovV / 2) * camara.aspect);
  const distancia = (radio / Math.sin(Math.min(fovV, fovH) / 2)) * 0.98;
  const objetivo = centro.clone().setY(centro.y * 0.75);
  return { objetivo, posicion: objetivo.clone().addScaledVector(direccion, distancia), radio, distancia };
}

function irA(posicion, objetivo, segundos = 0.9) {
  const p0 = camara.position.clone();
  const o0 = controles.target.clone();
  return animar(segundos, (k) => {
    camara.position.lerpVectors(p0, posicion, k);
    controles.target.lerpVectors(o0, objetivo, k);
  });
}

// margen > 1 aleja la cámara (para que entre el auto separado)
function vistaInicial(animado = true, margen = 1) {
  marcarCabina(false, !animado);
  const { objetivo, posicion: cerca, radio, distancia } = encuadreInicial();
  controles.minDistance = radio * 0.3;
  controles.maxDistance = distancia * 2.4;
  const posicion = objetivo.clone().lerp(cerca, margen);
  if (margen > 1) objetivo.y += (margen - 1) * radio * 0.5;
  if (animado) return irA(posicion, objetivo);
  camara.position.copy(posicion);
  controles.target.copy(objetivo);
  controles.update();
  pedirRender();
}

function enfocar(objeto) {
  const caja = new THREE.Box3().setFromObject(objeto);
  if (caja.isEmpty()) return;
  const centro = caja.getCenter(new THREE.Vector3());
  const radio = Math.max(caja.getBoundingSphere(new THREE.Sphere()).radius, 0.15);
  const direccion = camara.position.clone().sub(controles.target).normalize();
  const distancia = THREE.MathUtils.clamp(radio * 5, controles.minDistance * 1.6, controles.maxDistance * 0.6);
  // No me acerco de más: si ya se ve bien, solo giro hacia la pieza.
  const actual = camara.position.distanceTo(controles.target);
  irA(centro.clone().addScaledVector(direccion, Math.min(actual, distancia)), centro, 0.8);
}

function centroDe(objeto) {
  return new THREE.Box3().setFromObject(objeto).getCenter(new THREE.Vector3());
}

/* ===================== Carga ===================== */

async function cargarJSON(ruta) {
  const respuesta = await fetch(ruta, { cache: 'no-cache' });
  if (!respuesta.ok) throw new Error(`${ruta}: ${respuesta.status}`);
  return respuesta.json();
}

const textoDe = (...valores) => valores.find((v) => typeof v === 'string' && v.trim())?.trim() ?? '';
const parrafos = (valor) =>
  (Array.isArray(valor) ? valor : typeof valor === 'string' ? valor.split(/\n\s*\n/) : [])
    .map((p) => String(p).trim()).filter(Boolean);

const NOMBRES_GRUPO = {
  motor: 'Motor', 'motor-interno': 'Motor por dentro', 'motor por dentro': 'Motor por dentro',
  carroceria: 'Carrocería', exterior: 'Carrocería', interior: 'Interior',
};
const sinAcentos = (t) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

// Acepta la forma de fichas.json que haya elegido la tanda de fichas (lista, {piezas:[…]} u objeto por id).
function normalizarFichas(datos) {
  const avisos = datos?.avisos ?? {};
  let lista = Array.isArray(datos) ? datos
    : Array.isArray(datos?.piezas) ? datos.piezas
    : Array.isArray(datos?.fichas) ? datos.fichas
    : datos && typeof datos === 'object'
      ? Object.entries(datos).filter(([, f]) => f && typeof f === 'object' && !Array.isArray(f)).map(([id, f]) => ({ id, ...f }))
      : [];
  lista = lista.filter((f) => f && typeof f.id === 'string' && f.id.trim());
  return lista.map((f, i) => {
    const grupoCrudo = textoDe(f.grupo, f.categoria, f.seccion, f.sistema_grande) || 'Otras piezas';
    const grupo = NOMBRES_GRUPO[sinAcentos(grupoCrudo)] ?? grupoCrudo.charAt(0).toUpperCase() + grupoCrudo.slice(1);
    const queHace = textoDe(f.que_hace, f.queHace);
    // «dato» puede venir como texto o como { texto, verificado } (los no verificados ya lo dicen en el texto)
    const dato = textoDe(f.dato_camaro, f.datoCamaro, f.dato?.texto, f.dato);
    const notaAuto = textoDe(f.notaAuto, f.nota_auto);
    return {
      id: f.id.trim(),
      nombre: textoDe(f.nombre, f.titulo, f.name) || f.id,
      grupo,
      subgrupo: textoDe(f.subgrupo, f.sistema, f.zona, f.etiqueta),
      texto: [...parrafos(f.que_es ?? f.queEs ?? f.explicacion ?? f.descripcion ?? f.texto), ...(queHace ? [queHace] : [])],
      dato,
      saberMas: [...parrafos(f.saber_mas ?? f.saberMas), ...(notaAuto ? [`${avisos.autoDelAmigo ?? 'En el auto de tu amigo'}: ${notaAuto}`] : [])],
      piezas3d: Array.isArray(f.piezas3d) ? f.piezas3d.filter((n) => typeof n === 'string') : [],
      adentro: f.adentro === true, // vive en motor_interno.glb: se ve con «Por adentro» en la vista Motor
      orden: Number.isFinite(f.orden) ? f.orden : Number.isFinite(f.paso) ? f.paso : 1000 + i,
    };
  });
}

function mostrarProgreso(fraccion) {
  el.cargaProgreso.style.width = `${Math.round(fraccion * 100)}%`;
}

function mostrarEtapa(texto) {
  el.carga.querySelector('b').textContent = texto;
}

function mostrarError(texto, conBoton = true) {
  el.carga.classList.add('error');
  mostrarEtapa(texto);
  el.carga.querySelector('.carga-barra')?.remove();
  if (conBoton && !el.carga.querySelector('button')) {
    const boton = Object.assign(document.createElement('button'), { type: 'button', className: 'boton principal', textContent: 'Recargar' });
    boton.addEventListener('click', () => location.reload());
    el.carga.append(boton);
  }
}

// Las pinturas (los «shaders») se preparan en segundo plano: así la página no se congela mientras
// la placa de video las arma, que en Windows la primera vez puede tardar varios segundos.
async function prepararPinturas() {
  try {
    await renderer.compileAsync(escena, camara);
  } catch {
    // Si el navegador no sabe hacerlo en segundo plano, se arman solas al dibujar.
  }
}

/* Los materiales más caros (pintura con laca) pasan a la versión común en el modo liviano. */
function simplificarMateriales() {
  raiz.traverse((o) => {
    if (!o.isMesh) return;
    const lista = [].concat(o.material);
    const nuevos = lista.map((m) => {
      if (!m?.isMeshPhysicalMaterial) return m;
      const comun = new THREE.MeshStandardMaterial();
      THREE.MeshStandardMaterial.prototype.copy.call(comun, m);
      comun.name = m.name;
      return comun;
    });
    o.material = Array.isArray(o.material) ? nuevos : nuevos[0];
  });
}

function crearReemplazo(archivo, { centro = [0, 0.5, 0], tamano = [1, 1, 1] } = {}) {
  const geometria = new THREE.BoxGeometry(...tamano);
  const caja = new THREE.Mesh(geometria, new THREE.MeshStandardMaterial({ color: 0xc9c6be, roughness: 0.8, transparent: true, opacity: 0.55 }));
  caja.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometria), new THREE.LineBasicMaterial({ color: 0x8a867d })));
  caja.position.set(...centro);
  caja.name = `reemplazo-${archivo.replace(/\.glb$/i, '')}`;
  caja.castShadow = true;
  return caja;
}

const clips = []; // { nombre, mezclador, clip }

async function cargarModelos(modelos) {
  const draco = new DRACOLoader().setDecoderPath(RUTA_DRACO);
  const cargador = new GLTFLoader().setDRACOLoader(draco).setMeshoptDecoder(MeshoptDecoder);
  const avance = new Array(modelos.length).fill(0);
  const actualizar = () => mostrarProgreso(avance.reduce((a, b) => a + b, 0) / Math.max(modelos.length, 1));

  const resultados = await Promise.all(modelos.map(async (modelo, i) => {
    try {
      const gltf = await cargador.loadAsync(`modelos/${modelo.archivo}`, (e) => {
        if (e.total) { avance[i] = e.loaded / e.total; actualizar(); }
      });
      return { modelo, gltf };
    } catch {
      return { modelo, gltf: null };
    } finally {
      avance[i] = 1; actualizar();
    }
  }));

  let cargados = 0;
  for (const { modelo, gltf } of resultados) {
    if (gltf) {
      cargados++;
      gltf.scene.name ||= modelo.archivo;
      raiz.add(gltf.scene);
      if (gltf.animations?.length) {
        const mezclador = new THREE.AnimationMixer(gltf.scene);
        for (const clip of gltf.animations) clips.push({ nombre: sinAcentos(clip.name), mezclador, clip });
      }
    } else if (modelo.reemplazo) {
      raiz.add(crearReemplazo(modelo.archivo, modelo.reemplazo));
    }
  }
  draco.dispose();
  return cargados;
}

const esPiso = (o) => /^(piso|suelo|estudio|floor)/i.test(o.name);

function prepararObjetos() {
  let hayPiso = false;
  // En el celular, las ~90 piezas del motor no tiran sombra: quedan adentro del vano (no se nota) y
  // así cada cuadro dibuja casi la mitad menos de cosas para la sombra.
  const motor = esAngosto.matches ? raiz.getObjectByName('motor') : null;
  const motorSinSombra = new Set();
  motor?.traverse((o) => { if (o.isMesh) motorSinSombra.add(o); });
  raiz.traverse((o) => {
    if (!o.isMesh) return;
    const piso = esPiso(o) || (o.parent && esPiso(o.parent));
    if (piso) hayPiso = true;
    o.castShadow = !piso && !motorSinSombra.has(o);
    o.receiveShadow = true;
  });

  // La caja del auto, sin el piso, para encuadrar y ubicar la luz.
  const caja = new THREE.Box3();
  raiz.updateMatrixWorld(true);
  raiz.traverse((o) => {
    if (o.isMesh && !esPiso(o) && !(o.parent && esPiso(o.parent))) caja.expandByObject(o);
  });
  if (!caja.isEmpty()) cajaAuto.copy(caja);

  const centro = cajaAuto.getCenter(new THREE.Vector3());
  const radio = cajaAuto.getBoundingSphere(new THREE.Sphere()).radius;
  sol.position.copy(centro).add(new THREE.Vector3(radio * 0.35, radio * 2.4, radio * 0.55));
  sol.target.position.copy(centro);
  const sombra = sol.shadow.camera;
  sombra.left = sombra.bottom = -radio * 1.2;
  sombra.right = sombra.top = radio * 1.2;
  sombra.near = 0.1; sombra.far = radio * 5;
  sombra.updateProjectionMatrix();

  // Si el .glb no trae piso, pongo uno invisible que solo recibe la sombra (el auto apoyado, nunca flotando).
  if (!hayPiso) {
    const piso = new THREE.Mesh(new THREE.PlaneGeometry(radio * 8, radio * 8), new THREE.ShadowMaterial({ opacity: 0.22 }));
    piso.rotation.x = -Math.PI / 2;
    piso.position.set(centro.x, cajaAuto.min.y + 0.001, centro.z);
    piso.receiveShadow = true;
    piso.name = 'piso-sombra';
    escena.add(piso);
  }
}

function idDe(objeto) {
  const candidatos = [objeto.userData?.id, objeto.userData?.ficha, objeto.name];
  if (objeto.name) candidatos.push(objeto.name.replace(/(_\d+|\.?\d{3})$/, '')); // «capot.001» → «capot001» → «capot»
  return candidatos.find((c) => typeof c === 'string' && fichas.has(c));
}

// Fichas cuyo objeto 3D se llama distinto («tapa-baul» es «baul» en el modelo) o va de a varios
// («puertas» son puerta_izq y puerta_der): se buscan por «piezas3d» y, si son varios, se juntan
// en un grupo con el id de la ficha. Las manijas van con las puertas (se tocan y se separan con ellas).
const OTROS_NOMBRES = { 'tapa-baul': ['baul'] };
const VAN_CON = { puertas: ['manija-izq', 'manija-der'] };
const nombreLimpio = (o) => o.name.replace(/(_\d+|\.?\d{3})$/, '').replaceAll('_', '-');

function agruparPiezas() {
  for (const f of fichas.values()) {
    if (buscarObjeto([f.id])) continue;
    const nombres = new Set([...f.piezas3d, ...(OTROS_NOMBRES[f.id] ?? [])]);
    const hallados = [];
    raiz.traverse((o) => {
      if (!nombres.has(nombreLimpio(o))) return;
      for (let x = o.parent; x; x = x.parent) if (hallados.includes(x)) return; // ya está su padre
      hallados.push(o);
    });
    if (!hallados.length) continue;
    const acompanantes = (VAN_CON[f.id] ?? []).map((n) => buscarObjeto([n])).filter(Boolean);
    if (hallados.length === 1 && !acompanantes.length) { hallados[0].userData.id = f.id; continue; }
    const grupo = new THREE.Group();
    grupo.name = f.id;
    hallados[0].parent.add(grupo);
    for (const o of [...hallados, ...acompanantes]) grupo.attach(o);
  }
}

function indexarPiezas() {
  agruparPiezas();
  raiz.traverse((o) => {
    const id = idDe(o);
    if (id && !piezas.has(id)) { piezas.set(id, o); idPorObjeto.set(o, id); }
  });
}

// El motor por dentro (motor_interno.glb) llega recién con «Por adentro»: sus piezas se suman al bajarse.
// Las versiones cortadas y los espárragos se tocan como la pieza de siempre.
const ALIAS_INTERNO = { 'bloque-corte': 'bloque', 'tapas-cilindros-corte': 'tapas-cilindros', esparragos: 'balancines' };

function sumarPiezas(grupo) {
  grupo.traverse((o) => {
    const alias = ALIAS_INTERNO[nombreLimpio(o)];
    if (alias && fichas.has(alias)) { idPorObjeto.set(o, alias); return; }
    const id = idDe(o);
    if (!id || piezas.has(id)) return;
    piezas.set(id, o);
    idPorObjeto.set(o, id);
    el.lista.querySelector(`button[data-id="${CSS.escape(id)}"] .sin-modelo`)?.remove();
  });
  if (estado.seleccion) mostrarFicha(estado.seleccion);
}

/* ===================== Capot, puertas y baúl ===================== */

const aberturas = {}; // clave → { abierta, k, partes: [{ objeto, eje, radianes, q0 }], clip }

function buscarObjeto(nombres) {
  for (const nombre of nombres) {
    let hallado = null;
    raiz.traverse((o) => {
      if (hallado) return;
      if (o.name === nombre || o.userData?.id === nombre || o.name.replace(/(_\d+|\.?\d{3})$/, '') === nombre) hallado = o;
    });
    if (hallado) return hallado;
  }
  return null;
}

function prepararAberturas() {
  for (const [clave, conf] of Object.entries(estado.manifiesto.aberturas ?? {})) {
    if (!Array.isArray(conf)) continue;
    const clip = clips.find((c) => c.nombre === clave || c.nombre.startsWith(clave));
    const partes = [];
    if (!clip) {
      for (const parte of conf) {
        const objeto = buscarObjeto(parte.objetos ?? []);
        if (!objeto) continue;
        const eje = ['x', 'y', 'z'].includes(objeto.userData?.abre_eje) ? objeto.userData.abre_eje : parte.eje ?? 'x';
        const grados = Number.isFinite(objeto.userData?.abre_grados) ? objeto.userData.abre_grados : parte.grados ?? 45;
        // La puerta derecha arranca un poquito después que la izquierda: se nota que son dos.
        const retraso = clave === 'puertas' && /der/.test(nombreLimpio(objeto)) ? 0.1 : 0;
        partes.push({ objeto, eje, radianes: THREE.MathUtils.degToRad(grados), q0: objeto.quaternion.clone(), k: 0, retraso });
      }
    } else {
      clip.accion = clip.mezclador.clipAction(clip.clip);
      clip.accion.setLoop(THREE.LoopOnce, 1);
      clip.accion.clampWhenFinished = true;
      clip.accion.play();
      clip.accion.paused = true;
    }
    if (clip || partes.length) aberturas[clave] = { abierta: false, k: 0, partes, clip };
  }
}

const EJES = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };
const giro = new THREE.Quaternion();

function aplicarApertura(abertura, k) {
  abertura.k = k;
  if (abertura.clip) {
    abertura.clip.accion.time = THREE.MathUtils.clamp(k, 0, 1) * abertura.clip.clip.duration;
    abertura.clip.mezclador.update(0);
  }
}

function girarParte(p, k) {
  p.k = k;
  giro.setFromAxisAngle(EJES[p.eje], p.radianes * k);
  p.objeto.quaternion.copy(p.q0).multiply(giro);
}

// Al abrir: sale con ganas, frena suave y se pasa apenas, como sostenida por los resortes.
function curvaAbrir(p) {
  const c = 0.9;
  return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2);
}
// Al cerrar: arranca lento, toma envión y cierra con un rebotecito chico.
function curvaCerrar(p) {
  if (p < 0.82) return 1 - Math.pow(p / 0.82, 2.3);
  return 0.022 * Math.sin((Math.PI * (p - 0.82)) / 0.18);
}

const NOMBRE_ABERTURA = { capot: 'El capot', puertas: 'Las puertas', baul: 'El baúl' };
const DURACION_ABERTURA = { capot: 1.15, puertas: 1, baul: 1.05 };

function alternarAbertura(clave, abrir) {
  const abertura = aberturas[clave];
  const boton = document.querySelector(`[data-abrir="${clave}"]`);
  if (!abertura) {
    avisar(`${NOMBRE_ABERTURA[clave] ?? 'Eso'} todavía no se puede abrir: falta esa parte del modelo.`);
    return Promise.resolve();
  }
  const abierta = abrir ?? !abertura.abierta;
  if (abierta === abertura.abierta && abertura.animando) return abertura.animando;
  abertura.abierta = abierta;
  boton?.setAttribute('aria-pressed', String(abierta));

  // Si la tocan a mitad de camino, sigue desde donde está (la última orden manda).
  const turno = (abertura.turno = {});
  const forma = abierta ? curvaAbrir : curvaCerrar;
  const desdeClip = abertura.k;
  const desdes = abertura.partes.map((p) => p.k);
  const recorrido = abierta ? 1 - Math.min(...desdes, desdeClip) : Math.max(...desdes, desdeClip);
  const segundos = (DURACION_ABERTURA[clave] ?? 1) * THREE.MathUtils.clamp(recorrido, 0.3, 1);

  const mover = (desde, p) => (abierta ? desde + (1 - desde) * forma(p) : desde * forma(p));
  abertura.animando = animar(segundos, (p) => {
    if (abertura.turno !== turno) return;
    aplicarApertura(abertura, mover(desdeClip, p));
    abertura.partes.forEach((parte, i) => {
      const pp = THREE.MathUtils.clamp((p - parte.retraso) / (1 - parte.retraso), 0, 1);
      girarParte(parte, mover(desdes[i], pp));
    });
  }, lineal).then(() => { if (abertura.turno === turno) abertura.animando = null; });
  return abertura.animando;
}

function abrir(clave, abierta) {
  return aberturas[clave] ? alternarAbertura(clave, abierta) : Promise.resolve();
}

/* ===================== Separar (versión simple) ===================== */
// Cada pieza se aleja del centro de su grupo (motor o carrocería). js/modulos/separar.js la reemplaza.

function crearSeparadorBase() {
  const datos = new Map(); // id → { objeto, p0, delta, propio }
  const centrosGrupo = new Map();
  const centros = new Map();
  for (const [id, objeto] of piezas) {
    const c = centroDe(objeto);
    centros.set(id, c);
    const grupo = fichas.get(id).grupo;
    const acumulado = centrosGrupo.get(grupo) ?? { suma: new THREE.Vector3(), n: 0 };
    acumulado.suma.add(c); acumulado.n++;
    centrosGrupo.set(grupo, acumulado);
  }
  for (const [id, objeto] of piezas) {
    const { suma, n } = centrosGrupo.get(fichas.get(id).grupo);
    const centroGrupo = suma.clone().divideScalar(n);
    const c = centros.get(id);
    const direccion = c.clone().sub(centroGrupo);
    const largo = direccion.length();
    if (largo < 1e-3) direccion.set(0, 1, 0); else direccion.divideScalar(largo);
    direccion.y = Math.max(direccion.y, 0) + 0.35; // siempre un poco para arriba, que no se hunda en el piso
    direccion.normalize().multiplyScalar(THREE.MathUtils.clamp(largo * 0.9, 0.25, 0.9));
    // El corrimiento se guarda en el sistema del padre, así funciona aunque la pieza esté adentro de otra.
    const padre = objeto.parent;
    const a = padre.worldToLocal(c.clone());
    const b = padre.worldToLocal(c.clone().add(direccion));
    datos.set(id, { objeto, p0: objeto.position.clone(), delta: b.sub(a), propio: 0 });
  }
  let general = 0;
  const aplicar = () => {
    for (const d of datos.values()) d.objeto.position.copy(d.p0).addScaledVector(d.delta, Math.max(general, d.propio));
    pedirRender();
  };
  return {
    fijar(valor) { general = valor; aplicar(); },
    separarPieza(id) {
      const d = datos.get(id);
      if (!d) return false;
      const desde = d.propio;
      const hasta = desde > 0.5 ? 0 : 1;
      animar(0.7, (k) => { d.propio = desde + (hasta - desde) * k; aplicar(); });
      return hasta === 1;
    },
  };
}

/* ===================== Paso a paso (versión simple) ===================== */
// Arma el auto en el orden de la lista: cada paso suma una pieza. js/modulos/paso-a-paso.js la reemplaza.

function crearPasoBase() {
  const conModelo = () => orden.filter((id) => piezas.has(id));
  let actual = 0;
  const mostrar = () => {
    const ids = conModelo();
    ids.forEach((id, i) => { piezas.get(id).visible = i <= actual; });
    const id = ids[actual];
    api.actualizarPaso({ actual: actual + 1, total: ids.length, id, texto: fichas.get(id)?.nombre });
    pedirRender();
  };
  return {
    entrar() {
      if (!conModelo().length) { avisar('Todavía no hay piezas en el modelo para armar paso a paso.'); return false; }
      actual = 0; mostrar(); return true;
    },
    salir() { for (const objeto of piezas.values()) objeto.visible = true; pedirRender(); },
    siguiente() { actual = Math.min(actual + 1, conModelo().length - 1); mostrar(); },
    anterior() { actual = Math.max(actual - 1, 0); mostrar(); },
  };
}

/* ===================== Selección y resaltado ===================== */

let resaltados = []; // { malla, original }

function tenir(material) {
  const copia = material.clone();
  if ('emissive' in copia) {
    copia.emissive = ACENTO.clone();
    copia.emissiveIntensity = 0.55;
    copia.emissiveMap = null;
  } else if (copia.color) {
    copia.color.lerp(ACENTO, 0.5);
  }
  return copia;
}

function quitarResaltado() {
  for (const { malla, original } of resaltados) {
    const usado = malla.material;
    malla.material = original;
    (Array.isArray(usado) ? usado : [usado]).forEach((m) => m.dispose());
  }
  resaltados = [];
}

function resaltar(objeto) {
  quitarResaltado();
  objeto.traverse((o) => {
    if (!o.isMesh) return;
    resaltados.push({ malla: o, original: o.material });
    o.material = Array.isArray(o.material) ? o.material.map(tenir) : tenir(o.material);
  });
}

const esMotor = (id) => sinAcentos(fichas.get(id)?.grupo ?? '').includes('motor');

function seleccionar(id, { enfocar: hayQueEnfocar = false } = {}) {
  if (id && !fichas.has(id)) return;
  estado.seleccion = id ?? null;
  const objeto = id ? piezas.get(id) : null;
  if (objeto) resaltar(objeto); else quitarResaltado();

  for (const boton of el.lista.querySelectorAll('button[data-id]')) {
    boton.setAttribute('aria-current', String(boton.dataset.id === id));
  }
  if (id) {
    mostrarFicha(id);
    // Una pieza del motor no se ve con el capot cerrado: lo abro (separado o armándose, el capot no tapa).
    const capotTapa = estado.modo === 'explorar' && estado.separacion < 0.05;
    if (objeto && capotTapa && esMotor(id) && aberturas.capot && !aberturas.capot.abierta) alternarAbertura('capot', true);
    if (objeto && hayQueEnfocar) enfocar(objeto);
  } else {
    el.ficha.hidden = true;
  }
  emitir('seleccion', estado.seleccion);
  pedirRender();
}

const TEXTO_FALTA = el.fichaFalta.textContent;
const TEXTO_ADENTRO = 'Esta pieza está adentro del motor: para verla tocá «Motor» y después «Por adentro».';

function mostrarFicha(id) {
  const f = fichas.get(id);
  el.fichaGrupo.textContent = [f.grupo, f.subgrupo].filter(Boolean).join(' · ');
  el.fichaTitulo.textContent = f.nombre;
  el.fichaTexto.replaceChildren(...f.texto.map((t) => Object.assign(document.createElement('p'), { textContent: t })));
  const objeto = piezas.get(id);
  el.fichaFalta.textContent = f.adentro ? TEXTO_ADENTRO : TEXTO_FALTA;
  el.fichaFalta.hidden = f.adentro ? Boolean(objeto && visibleDeVerdad(objeto)) : Boolean(objeto);
  el.fichaDato.hidden = !f.dato;
  el.fichaDato.querySelector('span').textContent = f.dato;
  el.fichaSaber.hidden = !f.saberMas.length;
  el.fichaSaber.open = false;
  el.fichaSaber.querySelector('div').replaceChildren(...f.saberMas.map((t) => Object.assign(document.createElement('p'), { textContent: t })));
  el.fichaSeparar.hidden = !piezas.has(id) || f.adentro || estado.modo === 'paso';
  el.fichaSeparar.textContent = separadas.has(id) ? 'Volver a su lugar' : 'Separar esta pieza';
  el.ficha.hidden = false;
  el.ficha.scrollTop = 0;
}

function siguientePieza() {
  if (estado.modo === 'paso') { pasoAPaso.siguiente(); return; }
  const visibles = [...el.lista.querySelectorAll('li:not([hidden]) button[data-id]')].map((b) => b.dataset.id);
  const lista = visibles.length ? visibles : orden;
  const i = lista.indexOf(estado.seleccion);
  seleccionar(lista[(i + 1) % lista.length], { enfocar: true });
}

/* ===================== La línea de la pieza a la ficha ===================== */

const punto = new THREE.Vector3();
function dibujarGuia() {
  const objeto = estado.seleccion && piezas.get(estado.seleccion);
  if (!objeto || el.ficha.hidden || !objeto.visible) { el.guia.style.visibility = 'hidden'; return; }
  punto.copy(centroDe(objeto)).project(camara);
  if (punto.z > 1) { el.guia.style.visibility = 'hidden'; return; }
  const vista = el.vista.getBoundingClientRect();
  const marco = el.escena.getBoundingClientRect();
  const x = vista.left - marco.left + (punto.x * 0.5 + 0.5) * vista.width;
  const y = vista.top - marco.top + (-punto.y * 0.5 + 0.5) * vista.height;
  el.guiaPunto.setAttribute('cx', x.toFixed(1));
  el.guiaPunto.setAttribute('cy', y.toFixed(1));
  const ficha = el.ficha.getBoundingClientRect();
  const fx = ficha.left - marco.left;
  const fy = ficha.top - marco.top + 34;
  el.guiaLinea.setAttribute('d', fx > x + 40 ? `M${x.toFixed(1)} ${y.toFixed(1)} L${(fx - 60).toFixed(1)} ${fy.toFixed(1)} L${fx.toFixed(1)} ${fy.toFixed(1)}` : '');
  el.guia.style.visibility = 'visible';
}

/* ===================== Lista de piezas ===================== */

function armarLista() {
  const grupos = new Map();
  for (const f of [...fichas.values()].sort((a, b) => a.orden - b.orden)) {
    if (!grupos.has(f.grupo)) grupos.set(f.grupo, []);
    grupos.get(f.grupo).push(f);
  }
  // Motor primero, después carrocería, después el resto (como en la muestra)
  const peso = (g) => ({ motor: 0, 'motor por dentro': 1, carroceria: 2, interior: 3 })[sinAcentos(g)] ?? 4;
  const ordenados = [...grupos.entries()].sort((a, b) => peso(a[0]) - peso(b[0]));
  orden = ordenados.flatMap(([, lista]) => lista.map((f) => f.id));

  if (!ordenados.length) {
    el.lista.replaceChildren(Object.assign(document.createElement('p'), {
      className: 'lista-vacia', textContent: 'Las fichas de las piezas todavía no están cargadas.',
    }));
    return;
  }

  el.lista.replaceChildren(...ordenados.map(([grupo, lista], i) => {
    const detalles = document.createElement('details');
    detalles.className = 'grupo-piezas';
    detalles.open = i === 0;
    const resumen = document.createElement('summary');
    const cantidad = document.createElement('span');
    cantidad.textContent = String(lista.length);
    resumen.append(grupo, cantidad);
    const ul = document.createElement('ul');
    for (const f of lista) {
      const li = document.createElement('li');
      li.dataset.busqueda = sinAcentos(`${f.nombre} ${f.subgrupo} ${f.grupo}`);
      const boton = document.createElement('button');
      boton.type = 'button';
      boton.dataset.id = f.id;
      boton.setAttribute('aria-current', 'false');
      boton.append(f.nombre);
      if (!piezas.has(f.id)) {
        const marca = document.createElement('span');
        marca.className = 'sin-modelo';
        marca.textContent = f.adentro ? 'por dentro' : 'sin 3D';
        boton.append(marca);
      }
      li.append(boton);
      ul.append(li);
    }
    detalles.append(resumen, ul);
    return detalles;
  }));
}

function filtrarLista() {
  const busqueda = sinAcentos(el.buscar.value.trim());
  let total = 0;
  for (const grupo of el.lista.querySelectorAll('.grupo-piezas')) {
    let visibles = 0;
    for (const li of grupo.querySelectorAll('li')) {
      const coincide = !busqueda || li.dataset.busqueda.includes(busqueda);
      li.hidden = !coincide;
      if (coincide) visibles++;
    }
    grupo.hidden = visibles === 0;
    if (busqueda && visibles) grupo.open = true;
    total += visibles;
  }
  el.sinResultados.hidden = !busqueda || total > 0 || !fichas.size;
}

/* ===================== Modos y controles ===================== */

let separador = null;
let pasoAPaso = null;
const separadas = new Set();

function fijarSeparacion(valor, { animado = false } = {}) {
  const desde = estado.separacion;
  const hasta = THREE.MathUtils.clamp(valor, 0, 1);
  estado.separacion = hasta;
  el.separacion.value = String(Math.round(hasta * 100));
  const aplicar = (v) => separador?.fijar?.(v);
  emitir('separacion', hasta);
  if (!animado) { aplicar(hasta); pedirRender(); return Promise.resolve(); }
  return animar(0.9, (k) => aplicar(desde + (hasta - desde) * k));
}

function cambiarModo(modo) {
  if (modo === estado.modo) return;
  if (enCabina) vistaInicial(false);
  const anterior = estado.modo;
  if (modo === 'paso') {
    estado.modo = 'paso'; // ya en modo paso mientras arma el primer paso (así no se abre el capot)
    if (!(pasoAPaso?.entrar?.() ?? false)) { estado.modo = anterior; return; }
  }
  if (anterior === 'paso') pasoAPaso?.salir?.();

  estado.modo = modo;
  document.body.dataset.modo = modo;
  for (const boton of document.querySelectorAll('.modos button')) {
    boton.setAttribute('aria-pressed', String(boton.dataset.modo === modo));
  }
  el.paso.hidden = modo !== 'paso';

  if (modo === 'separar' && estado.separacion < 0.05) fijarSeparacion(0.7, { animado: true });
  if (modo === 'explorar' && anterior === 'separar') fijarSeparacion(0, { animado: true });
  if (modo === 'paso') { fijarSeparacion(0); separadas.clear(); }
  if (estado.seleccion) mostrarFicha(estado.seleccion);
  emitir('modo', modo);
  pedirRender();
}

let temporizadorAviso;
function avisar(texto) {
  el.aviso.textContent = texto;
  el.aviso.classList.add('visible');
  clearTimeout(temporizadorAviso);
  temporizadorAviso = setTimeout(() => el.aviso.classList.remove('visible'), 3800);
}

function conectarControles() {
  for (const boton of document.querySelectorAll('.modos button')) {
    boton.addEventListener('click', () => cambiarModo(boton.dataset.modo));
  }
  for (const boton of document.querySelectorAll('[data-abrir]')) {
    boton.addEventListener('click', () => alternarAbertura(boton.dataset.abrir));
  }
  el.vistaInicial.addEventListener('click', () => api.vistaInicial(true));
  el.acercar.addEventListener('click', () => acercar(0.8));
  el.alejar.addEventListener('click', () => acercar(1.25));
  el.verAdentro.addEventListener('click', () => verAdentro());

  el.separacion.addEventListener('input', () => {
    const valor = Number(el.separacion.value) / 100;
    fijarSeparacion(valor);
    if (valor > 0 && estado.modo === 'explorar') cambiarModo('separar');
  });

  el.fichaCerrar.addEventListener('click', () => {
    const id = estado.seleccion;
    seleccionar(null);
    (el.lista.querySelector(`button[data-id="${CSS.escape(id ?? '')}"]`) ?? el.lienzo).focus();
  });
  el.fichaSiguiente.addEventListener('click', siguientePieza);
  el.fichaSeparar.addEventListener('click', () => {
    const id = estado.seleccion;
    if (!id) return;
    const afuera = separador?.separarPieza?.(id);
    if (afuera) separadas.add(id); else separadas.delete(id);
    el.fichaSeparar.textContent = afuera ? 'Volver a su lugar' : 'Separar esta pieza';
  });

  el.pasoAnterior.addEventListener('click', () => pasoAPaso?.anterior?.());
  el.pasoSiguiente.addEventListener('click', () => pasoAPaso?.siguiente?.());

  el.buscar.addEventListener('input', filtrarLista);
  el.lista.addEventListener('click', (e) => {
    const boton = e.target.closest('button[data-id]');
    if (!boton) return;
    seleccionar(boton.dataset.id, { enfocar: true });
    if (esAngosto.matches) el.escena.scrollIntoView({ behavior: sinMovimiento.matches ? 'auto' : 'smooth', block: 'start' });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && estado.seleccion && !el.ayuda.open && !e.target.closest?.('input')) {
      el.fichaCerrar.click();
    }
  });
  document.addEventListener('keydown', moverConTeclado);
  conectarToques();
}

/* ===================== Cámara sin rueda: teclado, + / −, desplazar y ver por adentro ===================== */
// Las teclas andan en toda la página (no hace falta hacer clic en el auto), salvo escribiendo en un campo
// o con el foco en una barra, en la lista o en la ficha (ahí las flechas son de ellas).
//   + / −  acercar y alejar      ·  flechas  desplazar      ·  Mayúscula + flechas  girar
//   A      ver por adentro       ·  0 o Inicio  vista inicial  ·  ?  la ayuda

const esfera = new THREE.Spherical();
const derecha = new THREE.Vector3();
const haciaArriba = new THREE.Vector3();
const haciaAtras = new THREE.Vector3();

function girarCamara(dTheta, dPhi) {
  const desplazamiento = camara.position.clone().sub(controles.target);
  esfera.setFromVector3(desplazamiento);
  esfera.theta += dTheta;
  esfera.phi = THREE.MathUtils.clamp(esfera.phi + dPhi, 0.15, controles.maxPolarAngle);
  camara.position.copy(controles.target).add(desplazamiento.setFromSpherical(esfera));
  controles.update();
  pedirRender();
}

// factor < 1 acerca, > 1 aleja (siempre hacia el punto que se está mirando)
function acercar(factor) {
  const desde = camara.position.distanceTo(controles.target);
  const hasta = THREE.MathUtils.clamp(desde * factor, controles.minDistance, controles.maxDistance);
  if (Math.abs(hasta - desde) < 1e-4) return;
  const direccion = camara.position.clone().sub(controles.target).normalize();
  const objetivo = controles.target.clone();
  animar(0.25, (k) => {
    camara.position.copy(objetivo).addScaledVector(direccion, desde + (hasta - desde) * k);
  }, lineal);
}

// Corre la cámara y el punto que mira, de costado o para arriba y abajo (como Mayúscula + arrastrar)
function desplazar(x, y) {
  const paso = camara.position.distanceTo(controles.target) * 0.06;
  camara.updateMatrixWorld();
  camara.matrixWorld.extractBasis(derecha, haciaArriba, haciaAtras);
  const corrimiento = derecha.multiplyScalar(x * paso).addScaledVector(haciaArriba, y * paso);
  camara.position.add(corrimiento);
  controles.target.add(corrimiento);
  controles.update();
  pedirRender();
}

function moverConTeclado(e) {
  // Los avisos que reenvía la vista Motor son copias (isTrusted = false): se atiende solo la tecla de verdad.
  if (!e.isTrusted || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
  if (el.ayuda.open) return;
  const destino = e.target instanceof Element ? e.target : document.body;
  if (destino.closest('input, textarea, select, [contenteditable]')) return;
  if (e.key.startsWith('Arrow') && destino.closest('.panel, .ficha, .motor-vivo')) return;
  const giro = THREE.MathUtils.degToRad(8);
  const teclas = {
    ArrowLeft: () => (e.shiftKey ? girarCamara(-giro, 0) : desplazar(-1, 0)),
    ArrowRight: () => (e.shiftKey ? girarCamara(giro, 0) : desplazar(1, 0)),
    ArrowUp: () => (e.shiftKey ? girarCamara(0, -giro) : desplazar(0, 1)),
    ArrowDown: () => (e.shiftKey ? girarCamara(0, giro) : desplazar(0, -1)),
    '+': () => acercar(0.85),
    '=': () => acercar(0.85),
    '-': () => acercar(1 / 0.85),
    a: () => verAdentro(),
    A: () => verAdentro(),
    0: () => api.vistaInicial(true),
    Home: () => api.vistaInicial(true),
    '?': () => abrirAyuda(),
  };
  if (!teclas[e.key]) return;
  e.preventDefault();
  teclas[e.key]();
}

// «Adentro»: la cámara se mete en la cabina, detrás de las butacas, mirando el tablero.
// Arrastrar ahí es mirar alrededor (gira sobre un punto cercano, sin salir del auto).
let enCabina = false;
let distanciasAfuera = null;

function marcarCabina(si, inmediato = false) {
  if (!si && enCabina && distanciasAfuera) {
    controles.minDistance = distanciasAfuera.min;
    controles.maxDistance = distanciasAfuera.max;
  }
  if (si !== enCabina) cambiarLente(si ? LENTE_CABINA : LENTE, inmediato);
  enCabina = si;
  controles.rotateSpeed = si ? 0.45 : 1; // adentro, mirar alrededor más despacio
  document.body.toggleAttribute('data-cabina', si);
  el.verAdentro.setAttribute('aria-pressed', String(si));
  el.verAdentro.querySelector('span').textContent = si ? 'Salir' : 'Adentro';
  el.verAdentro.title = si ? 'Salir de la cabina (tecla A)' : 'Ver por adentro, desde la cabina (tecla A)';
}

function cambiarLente(hasta, inmediato = false) {
  const desde = camara.fov;
  const turno = (cambiarLente.turno = {});
  const poner = (k) => {
    if (cambiarLente.turno !== turno) return;
    camara.fov = desde + (hasta - desde) * k;
    camara.updateProjectionMatrix();
  };
  if (inmediato) poner(1); else animar(0.9, poner);
}

function puntoCabina() {
  const caja = (nombre) => {
    const objeto = buscarObjeto([nombre]);
    return objeto ? new THREE.Box3().setFromObject(objeto) : null;
  };
  const butacas = caja('butacas');
  const tablero = caja('tablero');
  const volante = caja('volante');
  const frente = vectorFrente();
  // Si el modelo no trae el interior, se calcula con las medidas de la carrocería.
  const ojo = butacas
    ? new THREE.Vector3(0, butacas.max.y + 0.12, 0).addScaledVector(frente, Math.min(frente.dot(butacas.min), frente.dot(butacas.max)) - 0.38)
    : cajaAuto.getCenter(new THREE.Vector3()).setY(cajaAuto.max.y * 0.84).addScaledVector(frente, -0.9);
  const mira = tablero
    ? tablero.getCenter(new THREE.Vector3())
    : ojo.clone().addScaledVector(frente, 1.4).setY(ojo.y - 0.25);
  if (volante) mira.x = volante.getCenter(new THREE.Vector3()).x * 0.35; // un poco hacia el volante
  const centro = ojo.clone().add(mira.clone().sub(ojo).setLength(0.55));
  return { ojo, centro };
}

function verAdentro(si = !enCabina) {
  if (api.vistaMotor?.activa?.()) { avisar('Con el motor en el soporte no hay cabina: tocá «Volver al auto».'); return; }
  if (!si) { api.vistaInicial(true); return; }
  if (!enCabina) distanciasAfuera = { min: controles.minDistance, max: controles.maxDistance };
  const { ojo, centro } = puntoCabina();
  marcarCabina(true);
  controles.minDistance = 0.12;
  controles.maxDistance = 1.1;
  irA(ojo, centro, 1.2);
  avisar('Estás adentro: arrastrá para mirar alrededor. «Salir» o la tecla A te sacan.');
}

/* ===================== El cartel de ayuda ===================== */
// Aparece la primera vez que se entra (se recuerda en este navegador) y vuelve con el botón «?» de arriba.

const AYUDA_VISTA = 'camaro-ayuda-vista';
let focoAntesDeAyuda = null;

function abrirAyuda() {
  if (el.ayuda.open) return;
  focoAntesDeAyuda = document.activeElement;
  el.ayuda.showModal();
}

function conectarAyuda() {
  el.abrirAyuda.addEventListener('click', abrirAyuda);
  el.cerrarAyuda.addEventListener('click', () => el.ayuda.close());
  // Tocar afuera del cartel también lo cierra (Esc lo cierra solo: es un <dialog>)
  el.ayuda.addEventListener('click', (e) => { if (e.target === el.ayuda) el.ayuda.close(); });
  el.ayuda.addEventListener('close', () => {
    try { localStorage.setItem(AYUDA_VISTA, '1'); } catch { /* sin memoria del navegador: se vuelve a mostrar */ }
    // Vuelve al botón «?» (o a donde estaba). Si salió solo al entrar, no se marca nada: las teclas igual andan.
    if (focoAntesDeAyuda && focoAntesDeAyuda !== document.body) focoAntesDeAyuda.focus({ preventScroll: true });
  });
  let yaLaVio = false;
  try { yaLaVio = localStorage.getItem(AYUDA_VISTA) === '1'; } catch { /* idem */ }
  if (!yaLaVio) abrirAyuda();
}

/* ===================== Tocar piezas en el 3D ===================== */

const rayo = new THREE.Raycaster();
const puntero = new THREE.Vector2();

function visibleDeVerdad(o) {
  for (let x = o; x; x = x.parent) if (!x.visible) return false;
  return true;
}

// Con el motor en el soporte, lo que quedó transparente («Por adentro») y el gas de colores no frenan
// el toque: se toca lo que se ve detrás (el pistón, la válvula…).
const esVelo = (o) => [].concat(o.material).every((m) => m?.transparent && m.depthWrite === false);

function golpeBajo(evento) {
  const marco = el.lienzo.getBoundingClientRect();
  puntero.set(((evento.clientX - marco.left) / marco.width) * 2 - 1, -((evento.clientY - marco.top) / marco.height) * 2 + 1);
  rayo.setFromCamera(puntero, camara);
  const enSoporte = api.vistaMotor?.activa?.();
  for (const golpe of rayo.intersectObject(raiz, true)) {
    if (!visibleDeVerdad(golpe.object)) continue;
    if (enSoporte && esVelo(golpe.object)) continue;
    for (let o = golpe.object; o && o !== raiz; o = o.parent) {
      if (idPorObjeto.has(o)) return { id: idPorObjeto.get(o), objeto: golpe.object };
    }
    return { id: null, objeto: golpe.object }; // tocó algo que no tiene ficha (vidrio, piso…)
  }
  return null;
}

function piezaBajo(evento) {
  return golpeBajo(evento)?.id ?? null;
}

const esDelInterno = (o) => { for (let x = o; x; x = x.parent) if (x.name === 'motor_interno') return true; return false; };

function conectarToques() {
  let inicio = null;

  // En el soporte, las piezas de adentro (motor_interno.glb) las atiende app.js antes que la vista Motor,
  // que no las conoce (diría «su ficha todavía no está cargada»). Va en la fase de captura de la vista.
  let inicioSoporte = null;
  el.vista.addEventListener('pointerdown', (e) => { inicioSoporte = { x: e.clientX, y: e.clientY }; }, true);
  el.vista.addEventListener('pointerup', (e) => {
    if (e.target !== el.lienzo || !inicioSoporte || !api.vistaMotor?.activa?.()) return;
    const movido = Math.hypot(e.clientX - inicioSoporte.x, e.clientY - inicioSoporte.y);
    inicioSoporte = null;
    if (movido > 6) return;
    const golpe = golpeBajo(e);
    if (!golpe || !esDelInterno(golpe.objeto)) return;
    e.stopPropagation();
    inicio = null;
    if (golpe.id) seleccionar(golpe.id); else if (estado.seleccion) seleccionar(null);
  }, true);
  el.lienzo.addEventListener('pointerdown', (e) => { inicio = { x: e.clientX, y: e.clientY }; });
  el.lienzo.addEventListener('pointerup', (e) => {
    if (!inicio) return;
    const movido = Math.hypot(e.clientX - inicio.x, e.clientY - inicio.y);
    inicio = null;
    if (movido > 6) return; // fue un arrastre para girar, no un toque
    const id = piezaBajo(e);
    if (id) seleccionar(id);
    else if (estado.seleccion && estado.modo !== 'paso') seleccionar(null);
  });

  // Manito sobre las piezas (solo con mouse)
  let pendiente = false;
  el.lienzo.addEventListener('pointermove', (e) => {
    if (e.pointerType !== 'mouse' || e.buttons || pendiente) return;
    pendiente = true;
    requestAnimationFrame(() => {
      pendiente = false;
      el.lienzo.classList.toggle('sobre-pieza', Boolean(piezaBajo(e)));
    });
  });
}

/* ===================== Módulos de otras tandas ===================== */

async function cargarModulo(ruta) {
  if (!ruta) return null;
  try {
    const modulo = await import(new URL(ruta, document.baseURI).href);
    if (typeof modulo.iniciar !== 'function') return null;
    return (await modulo.iniciar(api)) ?? null;
  } catch (error) {
    // Si el archivo todavía no existe no es un error: se usa la versión simple.
    if (!/fetch|import|resolve|load/i.test(String(error?.message))) console.error(`No pude iniciar ${ruta}:`, error);
    return null;
  }
}

const api = {
  THREE, escena, camara, controles, renderer, raiz, piezas, fichas,
  get orden() { return orden; },
  seleccionar, seleccionada: () => estado.seleccion,
  pedirRender, animar, centroDe, avisar, abrir, enfocar, vistaInicial,
  modo: () => estado.modo,
  actualizarPaso({ actual, total, id, texto } = {}) {
    el.pasoTexto.replaceChildren(`Paso ${actual} de ${total}`);
    const nombre = texto ?? fichas.get(id)?.nombre;
    if (nombre) el.pasoTexto.append(Object.assign(document.createElement('small'), { textContent: nombre }));
    el.pasoAnterior.disabled = actual <= 1;
    el.pasoSiguiente.disabled = actual >= total;
    if (id && fichas.has(id)) seleccionar(id);
  },
  on(evento, fn) { eventos.addEventListener(evento, (e) => fn(e.detail)); },
};
window.camaro = api; // a mano, desde la consola del navegador, para probar

// El panel de Prender / Acelerar se ve solo con el motor en el soporte. Lo de adentro del motor se baja
// recién con «Por adentro»: cuando llega, sus piezas se suman a las que se tocan y tienen ficha.
function conectarMotorVivo(motorVivo) {
  motorVivo.mostrar(false);
  document.addEventListener('vista-motor', (e) => {
    if (e.detail?.activa) marcarCabina(false);
    motorVivo.mostrar(Boolean(e.detail?.activa));
  });
  motorVivo.panel?.addEventListener('click', (e) => {
    const boton = e.target.closest('.mv-vista button');
    if (!boton || boton !== boton.parentElement.lastElementChild) return; // solo «Por adentro»
    motorVivo.interno().then((grupo) => { if (grupo) sumarPiezas(grupo); });
  });
}

/* ===================== Arranque ===================== */

async function arrancar() {
  ajustarTamano();
  bucle();
  conectarControles();
  conectarAyuda(); // el cartel sale ya, mientras el auto carga
  // Antes que la vista Motor (que encuadra desde donde está la cámara): si estaba en la cabina, sale.
  el.botonMotor?.addEventListener('click', () => { if (enCabina) vistaInicial(false); }, true);
  el.botonMotor?.addEventListener('click', () => { if (!api.vistaMotor) avisar('El motor se está preparando: probá en un segundo.'); });

  const [manifiesto, datosFichas] = await Promise.all([
    cargarJSON('modelos/manifiesto.json').catch(() => null),
    cargarJSON('datos/fichas.json').catch(() => null),
  ]);
  if (manifiesto) estado.manifiesto = { ...MANIFIESTO_BASE, ...manifiesto };
  for (const f of normalizarFichas(datosFichas)) fichas.set(f.id, f);

  // Los módulos se bajan mientras tanto (se inician cuando el auto ya está).
  const modulos = { ...RUTAS_MODULOS, ...(estado.manifiesto.modulos ?? {}) };
  for (const clave of Object.keys(RUTAS_MODULOS)) {
    if (modulos[clave]) import(new URL(modulos[clave], document.baseURI).href).catch(() => {});
  }

  const modelos = (estado.manifiesto.modelos ?? []).filter((m) => m?.archivo);
  const cargados = await cargarModelos(modelos);
  if (!cargados) avisar('Todavía no hay modelo 3D: se ven cubos de reemplazo.');

  if (modoLiviano) simplificarMateriales();
  prepararObjetos();
  indexarPiezas();
  prepararAberturas();
  armarLista();
  ajustarTamano();
  vistaInicial(false);

  mostrarEtapa('Preparando la pintura…');
  await prepararPinturas();
  preparando = false;
  pedirRender();

  const [modSeparar, modPaso] = await Promise.all([cargarModulo(modulos.separar), cargarModulo(modulos.paso_a_paso)]);
  const base = crearSeparadorBase();
  separador = { fijar: modSeparar?.fijar?.bind(modSeparar) ?? base.fijar, separarPieza: modSeparar?.separarPieza?.bind(modSeparar) ?? base.separarPieza };
  pasoAPaso = modPaso ?? crearPasoBase();

  // La vista Motor (el motor al soporte) y, encima, el motor en marcha (Prender, Acelerar, Por adentro).
  // Van después de Separar y Paso a paso: la vista Motor usa el mismo «movimiento» que ellos.
  const vistaMotor = await cargarModulo(modulos.vista_motor);
  const motorVivo = vistaMotor ? await cargarModulo(modulos.motor_vivo) : null;
  if (motorVivo) conectarMotorVivo(motorVivo);

  clearTimeout(avisoLento);
  el.carga.classList.add('listo');
  el.carga.setAttribute('aria-hidden', 'true');
  if (modoLiviano) avisar('Tu navegador está dibujando sin placa de video: se ve en modo liviano.');
  pedirRender();
}

// Si en 20 segundos no terminó, lo decimos (en vez de dejar la barra quieta para siempre).
const avisoLento = setTimeout(() => {
  if (el.carga.classList.contains('listo') || el.carga.classList.contains('error')) return;
  mostrarEtapa('Está tardando más de lo normal…');
  const boton = Object.assign(document.createElement('button'), { type: 'button', className: 'boton', textContent: 'Recargar' });
  boton.addEventListener('click', () => location.reload());
  el.carga.append(boton);
}, 20000);

arrancar().catch((error) => {
  console.error(error);
  mostrarError('No se pudo armar el auto. Recargá la página para probar de nuevo.');
});
