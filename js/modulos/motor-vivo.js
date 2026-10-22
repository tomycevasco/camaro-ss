/*
  Motor vivo · Prender, Acelerar y verlo por adentro
  ---------------------------------------------------------------------------
  Qué hace:
    · «Prender»: arranca el motor. Por afuera giran el ventilador y el balanceador y el motor tiembla.
    · «Por adentro»: cambia el bloque y las tapas de cilindros por su versión cortada
      (modelos/motor_interno.glb, se baja recién la primera vez), deja medio transparentes las piezas
      que tapan, y muestra cigüeñal, bielas, pistones, árbol de levas, botadores, balancines y
      válvulas moviéndose juntos, con el orden de encendido real (1-8-4-3-6-5-7-2) y el gas de cada
      cilindro pintado según el tiempo en que está.
    · «Acelerar»: un acelerón (sube de vueltas y vuelve al ralentí), con el sonido de verdad.
    · El sonido arranca apagado: se prende con el botón «Sonido» (los navegadores no dejan sonar nada
      hasta que la persona toca algo). Archivos y licencias en assets/audio/CREDITOS.md.

  Enganche (lo hace la integración, sin tocar este archivo):
    · modelos/manifiesto.json → "modulos": { …, "motor_vivo": "js/modulos/motor-vivo.js" }
    · Se inicia con cargarModulo() como los otros: export async function iniciar(api) → controlador.
    · El panel se arma solo y se pone al final de #escena. Se muestra cuando api.modo() es "motor"
      (evento «modo») o cuando alguien llama a mostrar(true). Para ponerlo en otro lado: montar(elemento).
    · Los estilos están en css/motor-vivo.css (si index.html no los enlaza, este archivo los agrega).

  El controlador que devuelve iniciar(api):
    prender(), apagar(), acelerar(), porAdentro(true|false) → Promise, sonido(true|false),
    camaraLenta(true|false), mostrar(true|false), montar(elemento), estado() → { andando, rpm, adentro, … },
    panel (el elemento), interno() → Promise con el grupo 3D de adentro (null si no se pudo bajar).

  Cuentas (las mismas de blender/motor_interno.py, que las guarda en userData del vacío «motor_interno»):
    θ = vueltas del cigüeñal en grados; θ = 0 con el cilindro 1 arriba a punto de explotar.
    Cada cilindro: local = (θ − explota) mod 720 → 0–180 explosión · 180–360 escape ·
    360–540 admisión · 540–720 compresión. El árbol de levas gira a la mitad.
    Todo gira en sentido horario mirado de frente: en Three.js es rotation.z negativo.
*/

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

const RUTA_MODELO = new URL('../../modelos/motor_interno.glb', import.meta.url).href;
const RUTA_DRACO = new URL('../../vendor/three/examples/jsm/libs/draco/gltf/', import.meta.url).href;
const RUTA_CSS = new URL('../../css/motor-vivo.css', import.meta.url).href;
const RUTA_AUDIO = {
  ralenti: new URL('../../assets/audio/v8-ralenti.mp3', import.meta.url).href,
  acelerando: new URL('../../assets/audio/v8-acelerando.mp3', import.meta.url).href,
};

const RALENTI = 700;          // vueltas por minuto en ralentí (INVESTIGACION-motor-interno.md, sección 6)
const MAXIMO = 4800;          // donde da la potencia máxima
const GRADOS = Math.PI / 180;
const sinMovimiento = matchMedia('(prefers-reduced-motion: reduce)');

// Los colores de los 4 tiempos (el naranja es el --acento del proyecto)
const TIEMPOS = [
  { id: 'explosion', nombre: 'Explosión', texto: 'salta la chispa y empuja', color: '#d9600b' },
  { id: 'escape', nombre: 'Escape', texto: 'salen los gases', color: '#8a8f96' },
  { id: 'admision', nombre: 'Admisión', texto: 'entra aire y nafta', color: '#2f6fd6' },
  { id: 'compresion', nombre: 'Compresión', texto: 'aprieta la mezcla', color: '#e2a800' },
];
const ORDEN_ENCENDIDO = [1, 8, 4, 3, 6, 5, 7, 2];

// Lo que tapa la vista de adentro: con «Por adentro» queda medio transparente
const TAPAN = ['tapas-valvulas', 'multiple-admision', 'carburador', 'filtro-aire', 'distribuidor', 'bobina',
  'cables-bujias', 'bujias', 'multiples-escape', 'termostato', 'carter', 'tapa-distribucion', 'mangueras'];
// Lo que se cambia por su versión cortada
const CORTES = { bloque: 'bloque-corte', 'tapas-cilindros': 'tapas-cilindros-corte' };

// El acelerón de la grabación (v8-acelerando.mp3, que se toca desde DESDE_SEGUNDO): vueltas a cada momento.
// Sale de medir el volumen de la grabación: dos acelerones (picos a los 0,6 s y a los 1,5 s) y vuelve al ralentí.
const DESDE_SEGUNDO = 2.0;
const ACELERON = [[0, 750], [0.2, 1800], [0.55, 4200], [0.75, 3900], [1.0, 2800], [1.35, 4500], [1.7, 4800],
  [1.95, 3900], [2.3, 2000], [2.7, 1050], [3.4, 760], [4.2, 700]];

const mod = (a, n) => ((a % n) + n) % n;
const entre = (a, b, k) => a + (b - a) * k;

export async function iniciar(api) {
  agregarEstilos();

  const estado = {
    marcha: 'apagado',     // apagado · arrancando · andando · apagando
    rpm: 0,
    theta: 0,
    t: 0,                  // segundos desde que se tocó Prender / Apagar
    aceleron: null,        // segundos desde que se tocó Acelerar (null = no está acelerando)
    rpmApagando: 0,
    adentro: false,
    lento: sinMovimiento.matches,
    sonido: false,
    visible: false,
  };

  /* ===================== Las piezas ===================== */

  let motor = null;        // el vacío «motor» de motor.glb
  let interno = null;      // el vacío «motor_interno» de motor_interno.glb
  let cargandoInterno = null;
  const partes = { pistones: [], bielas: [], valvulas: [], resortes: [], balancines: [], botadores: [], gases: [] };
  let ciguenal = null;
  let levas = null;
  const giratorios = [];   // de afuera: ventilador y balanceador
  const cortes = [];       // { original, corte } para copiar la posición si la vista Motor los mueve
  const fantasmas = new Map(); // malla → { material original, sombra }
  const sacudida = new THREE.Vector3();
  let fogonazo = null;
  let medidas = null;

  function buscarMotor() {
    if (motor?.parent) return motor;
    const bloque = api.raiz.getObjectByName('bloque');
    motor = bloque?.parent ?? null;
    if (motor) prepararAfuera();
    return motor;
  }

  function prepararAfuera() {
    giratorios.length = 0;
    // Mismo eje que en blender/motor.py: el ventilador va en el eje de la bomba de agua y gira un poco más rápido
    const ejes = { ventilador: [0, 0.49, 1.3], balanceador: [0, 0.35, 1] };
    for (const [nombre, [x, y, relacion]] of Object.entries(ejes)) {
      const objeto = motor.getObjectByName(nombre);
      if (objeto) giratorios.push({ objeto, eje: new THREE.Vector2(x, y), relacion, base: null });
    }
  }

  function cargarInterno() {
    if (interno) return Promise.resolve(interno);
    if (cargandoInterno) return cargandoInterno;
    cargandoInterno = (async () => {
      const draco = new DRACOLoader().setDecoderPath(RUTA_DRACO);
      const cargador = new GLTFLoader().setDRACOLoader(draco);
      try {
        const gltf = await cargador.loadAsync(RUTA_MODELO);
        const raiz = gltf.scene.getObjectByName('motor_interno') ?? gltf.scene;
        prepararInterno(raiz);
        // Las pinturas se arman antes de mostrarlo: si no, la primera vez la página se congela un rato
        try { await api.renderer.compileAsync(raiz, api.camara, api.escena); } catch { /* se arman solas */ }
        interno = raiz;
        return interno;
      } catch (error) {
        console.error('No pude bajar el motor por dentro:', error);
        cargandoInterno = null;
        return null;
      } finally {
        draco.dispose();
      }
    })();
    return cargandoInterno;
  }

  function prepararInterno(raiz) {
    const u = raiz.userData;
    medidas = {
      centro: new THREE.Vector3(...(u.centro_ciguenal ?? [0, 0.35, 1.21])),
      r: u.radio_manivela ?? 0.0442,
      l: u.biela ?? 0.1448,
      alzada: u.alzada ?? 0.0095,
      relacion: u.relacion ?? 1.5,
      compresion: u.altura_compresion ?? 0.0396,
      radio: u.radio_cilindro ?? 0.0508,
      camara: u.d_camara ?? 0.241,
    };
    const liviano = !api.renderer.shadowMap.enabled;
    raiz.traverse((o) => {
      if (o.isMesh) {
        // Sin sombras propias: adentro del bloque no suman nada y son 150 dibujos más por cuadro
        o.castShadow = false;
        o.receiveShadow = false;
        if (liviano) o.material = sinLaca(o.material);
      }
      const d = o.userData;
      // «corrido»: dónde está el grupo que la contiene (pistones, bielas…): las cuentas van en coordenadas del motor
      const corrido = o.parent && o.parent !== raiz ? o.parent.position.clone() : new THREE.Vector3();
      const datos = { objeto: o, base: o.position.clone(), corrido, lado: d.lado ?? 1, explota: d.explota ?? 0, clase: d.clase };
      switch (d.tipo) {
        case 'ciguenal': ciguenal = o; break;
        case 'levas': levas = o; break;
        case 'piston': partes.pistones.push({ ...datos, manivela: d.manivela ?? 45, cilindro: d.cilindro }); break;
        case 'biela': partes.bielas.push({ ...datos, manivela: d.manivela ?? 45 }); break;
        case 'valvula': partes.valvulas.push(datos); break;
        case 'resorte': partes.resortes.push({ ...datos, largo: d.largo ?? 0.039 }); break;
        case 'balancin': partes.balancines.push({ ...datos, brazo: d.brazo ?? 0.038, base: o.rotation.z }); break;
        case 'botador': partes.botadores.push(datos); break;
        default: break;
      }
    });
    for (const [original, nombre] of Object.entries(CORTES)) {
      const corte = raiz.getObjectByName(nombre);
      if (corte) cortes.push({ nombreOriginal: original, corte });
    }
    crearGases(raiz);
    raiz.visible = false;
  }

  // El gas de cada cilindro: una columna entre la cabeza del pistón y la cámara, del color de su tiempo
  function crearGases(raiz) {
    const forma = new THREE.CylinderGeometry(medidas.radio * 0.97, medidas.radio * 0.97, 1, 32, 1, false);
    forma.translate(0, 0.5, 0);
    for (const p of partes.pistones) {
      const eje = new THREE.Vector3(Math.SQRT1_2 * p.lado, Math.SQRT1_2, 0);
      // Color plano (sin luces ni el «tono de cine» de la escena): así cada tiempo es exactamente su color
      const material = new THREE.MeshBasicMaterial({
        color: TIEMPOS[0].color, transparent: true, opacity: 0.55, depthWrite: false, toneMapped: false,
      });
      const gas = new THREE.Mesh(forma, material);
      gas.name = `gas-${p.cilindro}`;
      gas.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), eje);
      gas.renderOrder = 2;
      gas.castShadow = false;
      raiz.add(gas);
      partes.gases.push({ gas, piston: p, eje, colores: TIEMPOS.map((t) => new THREE.Color(t.color)) });
      fogonazo ??= new THREE.Color('#fff1e0');
    }
  }

  function sinLaca(material) {
    const lista = [].concat(material).map((m) => {
      if (!m?.isMeshPhysicalMaterial) return m;
      const comun = new THREE.MeshStandardMaterial();
      THREE.MeshStandardMaterial.prototype.copy.call(comun, m);
      comun.name = m.name;
      return comun;
    });
    return Array.isArray(material) ? lista : lista[0];
  }

  /* ===================== La pose: dónde está cada pieza para un ángulo del cigüeñal ===================== */

  function tiempoDe(local) { return Math.floor(local / 180); } // 0 explosión · 1 escape · 2 admisión · 3 compresión

  function alzadaValvula(local, clase) {
    const desde = clase === 'esc' ? 180 : 360;
    if (local < desde || local > desde + 180) return 0;
    return medidas.alzada * Math.sin(((local - desde) / 180) * Math.PI);
  }

  const vTmp = new THREE.Vector3();
  const vMunon = new THREE.Vector3();

  function aplicarPose(theta) {
    if (!interno || !medidas) return;
    const { centro, r, l } = medidas;
    if (ciguenal) ciguenal.rotation.z = -theta * GRADOS;
    if (levas) levas.rotation.z = (-theta / 2) * GRADOS;

    const pin = new Map();
    for (const p of partes.pistones) {
      const beta = 45 * p.lado;
      const a = (p.manivela + theta) * GRADOS;
      const alfa = a - beta * GRADOS;
      const s = r * Math.cos(alfa) + Math.sqrt(l * l - (r * Math.sin(alfa)) ** 2);
      vTmp.set(Math.SQRT1_2 * p.lado, Math.SQRT1_2, 0).multiplyScalar(s - (r + l));
      p.objeto.position.copy(p.base).add(vTmp);
      pin.set(p.objeto.userData.cilindro, { posicion: p.objeto.position.clone().add(p.corrido), a, beta, s });
    }
    for (const b of partes.bielas) {
      const datos = pin.get(b.objeto.userData.cilindro);
      if (!datos) continue;
      b.objeto.position.copy(datos.posicion).sub(b.corrido);
      vMunon.set(centro.x + r * Math.sin(datos.a), centro.y + r * Math.cos(datos.a), datos.posicion.z);
      const dx = vMunon.x - datos.posicion.x;
      const dy = vMunon.y - datos.posicion.y;
      // Ángulo entre «para abajo de la fila» y la línea bulón → muñón
      const ax = -Math.SQRT1_2 * b.lado;
      const ay = -Math.SQRT1_2;
      b.objeto.rotation.z = Math.atan2(ax * dy - ay * dx, ax * dx + ay * dy);
    }
    const eje = (lado) => vTmp.set(Math.SQRT1_2 * lado, Math.SQRT1_2, 0);
    for (const v of partes.valvulas) {
      const alzada = alzadaValvula(mod(theta - v.explota, 720), v.clase);
      v.objeto.position.copy(v.base).addScaledVector(eje(v.lado), -alzada);
    }
    for (const v of partes.resortes) {
      const alzada = alzadaValvula(mod(theta - v.explota, 720), v.clase);
      v.objeto.scale.y = (v.largo - alzada) / v.largo;
    }
    for (const v of partes.balancines) {
      const alzada = alzadaValvula(mod(theta - v.explota, 720), v.clase);
      v.objeto.rotation.z = v.base - v.lado * Math.atan(alzada / v.brazo);
    }
    for (const v of partes.botadores) {
      const alzada = alzadaValvula(mod(theta - v.explota, 720), v.clase) / medidas.relacion;
      v.objeto.position.copy(v.base).addScaledVector(eje(v.lado), alzada);
    }
    pintarGases(theta, pin);
  }

  function pintarGases(theta, pin) {
    const { compresion, camara } = medidas;
    for (const g of partes.gases) {
      const datos = pin.get(g.piston.objeto.userData.cilindro);
      const local = mod(theta - g.piston.explota, 720);
      const tiempo = tiempoDe(local);
      const avance = (local % 180) / 180;
      // De la cabeza del pistón hasta la cámara de la tapa
      g.gas.position.copy(datos.posicion).addScaledVector(g.eje, compresion);
      const arriba = camara - (datos.s + compresion);
      g.gas.scale.set(1, Math.max(arriba, 0.002), 1);
      const m = g.gas.material;
      m.color.copy(g.colores[tiempo]);
      if (tiempo === 0) {          // la explosión: un fogonazo claro que vuelve al naranja mientras empuja
        m.color.lerp(fogonazo, Math.max(0, 1 - avance * 4) * 0.85);
        m.opacity = 0.85 - 0.25 * avance;
      } else if (tiempo === 3) {   // la compresión se pone más intensa a medida que aprieta
        m.opacity = 0.4 + 0.35 * avance;
      } else {
        m.opacity = tiempo === 2 ? 0.5 : 0.55 - 0.25 * avance;
      }
      g.gas.visible = estado.adentro;
    }
  }

  /* ===================== Por afuera / por adentro ===================== */

  async function porAdentro(si) {
    si = Boolean(si);
    if (si === estado.adentro) return;
    if (si) {
      if (!buscarMotor()) { api.avisar?.('Todavía no está el motor: esperá a que cargue.'); return; }
      ui.mostrarCargando(true);
      const listo = await cargarInterno();
      ui.mostrarCargando(false);
      if (!listo) { api.avisar?.('No pude bajar el motor por dentro. Probá de nuevo en un rato.'); ui.actualizar(); return; }
      if (interno.parent !== motor) motor.add(interno);
    }
    estado.adentro = si;
    if (interno) interno.visible = si;
    for (const { nombreOriginal, corte } of cortes) {
      const original = motor?.getObjectByName(nombreOriginal);
      if (original) original.visible = !si;
      corte.visible = si;
    }
    for (const nombre of TAPAN) {
      const pieza = motor?.getObjectByName(nombre);
      if (pieza) fantasma(pieza, si);
    }
    sincronizarCortes();
    aplicarPose(estado.theta);
    api.pedirRender();
    ui.actualizar();
    ui.anunciar(si ? 'Por adentro: el bloque está cortado y lo de arriba quedó transparente.' : 'Por afuera.');
    despertar();
  }

  function fantasma(pieza, si) {
    pieza.traverse((o) => {
      if (!o.isMesh) return;
      if (si) {
        if (fantasmas.has(o)) return;
        const original = o.material;
        const transparente = [].concat(original).map((m) => {
          const copia = m.clone();
          copia.transparent = true;
          copia.opacity = 0.14;
          copia.depthWrite = false;
          return copia;
        });
        fantasmas.set(o, { original, puesto: Array.isArray(original) ? transparente : transparente[0], sombra: o.castShadow });
        o.material = fantasmas.get(o).puesto;
        o.castShadow = false;
      } else {
        const guardado = fantasmas.get(o);
        if (!guardado) return;
        // Si mientras tanto la pantalla la marcó (otro material), la devuelvo igual a su material de verdad
        o.material = guardado.original;
        o.castShadow = guardado.sombra;
        [].concat(guardado.puesto).forEach((m) => m.dispose());
        fantasmas.delete(o);
      }
    });
  }

  // Si la vista Motor separa o mueve el bloque y las tapas, los cortados van con ellos
  function sincronizarCortes() {
    if (!motor) return false;
    let cambio = false;
    for (const { nombreOriginal, corte } of cortes) {
      const original = motor.getObjectByName(nombreOriginal);
      if (!original) continue;
      cambio = copiarLugar(original, corte) || cambio;
      original.children.forEach((hijo, i) => {
        const par = corte.getObjectByName(`${hijo.name}-corte`) ?? corte.children[i];
        if (par) cambio = copiarLugar(hijo, par) || cambio;
      });
    }
    return cambio;
  }

  function copiarLugar(de, a) {
    if (a.position.equals(de.position) && a.quaternion.equals(de.quaternion) && a.scale.equals(de.scale)) return false;
    a.position.copy(de.position);
    a.quaternion.copy(de.quaternion);
    a.scale.copy(de.scale);
    return true;
  }

  /* ===================== Marcha ===================== */

  function prender() {
    if (!buscarMotor()) { api.avisar?.('Todavía no está el motor: esperá a que cargue.'); return; }
    if (estado.marcha === 'andando' || estado.marcha === 'arrancando') return;
    estado.marcha = 'arrancando';
    estado.t = 0;
    estado.aceleron = null;
    sonido.arrancar();
    cargarInterno();         // se va bajando por si después quiere verlo por adentro
    ui.actualizar();
    ui.anunciar('Motor prendido, en ralentí.');
    despertar();
  }

  function apagar() {
    if (estado.marcha === 'apagado' || estado.marcha === 'apagando') return;
    estado.marcha = 'apagando';
    estado.t = 0;
    estado.aceleron = null;
    estado.rpmApagando = estado.rpm;
    sonido.apagar();
    ui.actualizar();
    ui.anunciar('Motor apagado.');
    despertar();
  }

  function acelerar() {
    if (estado.marcha !== 'andando' && estado.marcha !== 'arrancando') return;
    estado.marcha = 'andando';
    estado.aceleron = 0;
    sonido.acelerar();
    ui.anunciar('Acelerando.');
    despertar();
  }

  function rpmDelAceleron(t) {
    for (let i = 1; i < ACELERON.length; i++) {
      const [t1, r1] = ACELERON[i];
      const [t0, r0] = ACELERON[i - 1];
      if (t <= t1) return entre(r0, r1, (1 - Math.cos(((t - t0) / (t1 - t0)) * Math.PI)) / 2);
    }
    return null; // terminó
  }

  function actualizarRpm(dt) {
    estado.t += dt;
    if (estado.marcha === 'arrancando') {
      // El burro de arranque gira el motor despacio y enseguida «agarra»
      if (estado.t < 0.75) estado.rpm = 200 + 40 * Math.sin(estado.t * 40);
      else if (estado.t < 2.2) estado.rpm = entre(1150, RALENTI, (estado.t - 0.75) / 1.45);
      else { estado.rpm = RALENTI; estado.marcha = 'andando'; }
    } else if (estado.marcha === 'andando') {
      if (estado.aceleron !== null) {
        estado.aceleron += dt;
        const rpm = rpmDelAceleron(estado.aceleron);
        if (rpm === null) estado.aceleron = null;
        else estado.rpm = rpm;
      }
      if (estado.aceleron === null) estado.rpm = entre(estado.rpm, RALENTI + 12 * Math.sin(estado.t * 2.3), Math.min(1, dt * 3));
    } else if (estado.marcha === 'apagando') {
      const k = Math.min(estado.t / 1.1, 1);
      estado.rpm = estado.rpmApagando * (1 - k) ** 2;
      if (k >= 1) { estado.rpm = 0; estado.marcha = 'apagado'; ui.actualizar(); }
    }
  }

  // Lo que se ve: a vueltas de verdad no se distingue nada, así que se muestra más despacio
  function vueltasPorSegundo(rpm) {
    if (rpm <= 0) return 0;
    const k = Math.sqrt(rpm / RALENTI);
    return estado.lento ? 0.3 * k : 2.1 * k;
  }

  /* ===================== El bucle (solo mientras hace falta) ===================== */

  let pedido = 0;
  let antes = 0;
  let ultimoTexto = 0;

  function despertar() {
    if (pedido) return;
    antes = performance.now();
    pedido = requestAnimationFrame(cuadro);
  }

  function cuadro(ahora) {
    pedido = 0;
    const dt = Math.min((ahora - antes) / 1000, 0.1);
    antes = ahora;
    const andando = estado.marcha !== 'apagado';
    let cambio = false;

    if (andando) {
      actualizarRpm(dt);
      estado.theta = mod(estado.theta + vueltasPorSegundo(estado.rpm) * 360 * dt, 720);
      for (const g of giratorios) {
        g.base ??= { x: g.objeto.position.x, y: g.objeto.position.y, z: g.objeto.rotation.z };
        girarSobre(g, -estado.theta * g.relacion * GRADOS);
      }
      sacudir(true);
      aplicarPose(estado.theta);
      sonido.seguir(estado.rpm, estado.aceleron !== null);
      cambio = true;
      if (ahora - ultimoTexto > 120) { ultimoTexto = ahora; ui.rpm(); }
    } else {
      sacudir(false);
    }
    if (estado.adentro && sincronizarCortes()) cambio = true;
    if (cambio) api.pedirRender();
    if (andando || estado.adentro) pedido = requestAnimationFrame(cuadro);
  }

  // Gira una pieza de afuera alrededor de su eje (paralelo al cigüeñal), sin perder dónde estaba
  function girarSobre(g, angulo) {
    const o = g.objeto;
    const dx = g.base.x - g.eje.x;
    const dy = g.base.y - g.eje.y;
    // Si otra parte de la pantalla la movió (separar), el eje se mueve con ella
    const c = Math.cos(angulo);
    const s = Math.sin(angulo);
    const corridoX = o.position.x - (g.ultimo?.x ?? o.position.x);
    const corridoY = o.position.y - (g.ultimo?.y ?? o.position.y);
    g.eje.x += corridoX; g.eje.y += corridoY;
    g.base.x += corridoX; g.base.y += corridoY;
    o.position.x = g.eje.x + dx * c - dy * s;
    o.position.y = g.eje.y + dx * s + dy * c;
    o.rotation.z = g.base.z + angulo;
    g.ultimo = { x: o.position.x, y: o.position.y };
  }

  function devolverGiratorios() {
    for (const g of giratorios) {
      if (!g.base) continue;
      girarSobre(g, 0);
      g.base = null;
      g.ultimo = null;
    }
  }

  // El temblor del motor andando: unas décimas de milímetro, más fuerte al acelerar
  function sacudir(si) {
    if (!motor) return;
    motor.position.sub(sacudida);
    if (si && !sinMovimiento.matches) {
      const fuerza = 0.00045 + 0.0009 * Math.min(1, Math.max(0, (estado.rpm - RALENTI) / (MAXIMO - RALENTI)));
      sacudida.set((Math.random() - 0.5) * fuerza, (Math.random() - 0.5) * fuerza * 1.4, (Math.random() - 0.5) * fuerza * 0.5);
    } else {
      sacudida.set(0, 0, 0);
    }
    motor.position.add(sacudida);
  }

  /* ===================== Sonido (Web Audio) ===================== */

  const sonido = (() => {
    let ctx = null;
    let general = null;    // volumen general (0 = sin sonido)
    let bucleGanancia = null;
    let bucle = null;
    let golpe = null;
    let buffers = null;
    let cargando = null;

    function contexto() {
      if (!ctx) {
        const Contexto = window.AudioContext || window.webkitAudioContext;
        if (!Contexto) return null;
        ctx = new Contexto();
        general = ctx.createGain();
        general.gain.value = 0;
        general.connect(ctx.destination);
      }
      // Tiene que pasar dentro del clic: si no, el navegador no deja sonar
      if (ctx.state === 'suspended' && !document.hidden) ctx.resume();
      return ctx;
    }

    function bajar() {
      if (buffers) return Promise.resolve(buffers);
      cargando ??= Promise.all(Object.entries(RUTA_AUDIO).map(async ([nombre, ruta]) => {
        const respuesta = await fetch(ruta);
        if (!respuesta.ok) throw new Error(`${ruta}: ${respuesta.status}`);
        return [nombre, await ctx.decodeAudioData(await respuesta.arrayBuffer())];
      })).then((lista) => (buffers = Object.fromEntries(lista))).catch((error) => {
        console.error('No pude bajar el sonido:', error);
        cargando = null;
        return null;
      });
      return cargando;
    }

    async function empezarBucle() {
      if (!estado.sonido || bucle || estado.marcha === 'apagado' || estado.marcha === 'apagando') return;
      if (!(await bajar()) || bucle || !estado.sonido) return;
      if (estado.marcha === 'apagado' || estado.marcha === 'apagando') return;
      const b = buffers.ralenti;
      bucle = ctx.createBufferSource();
      bucle.buffer = b;
      bucle.loop = true;
      bucle.loopStart = 0.03;
      bucle.loopEnd = b.duration - 0.03;
      bucleGanancia = ctx.createGain();
      bucleGanancia.gain.setValueAtTime(0, ctx.currentTime);
      bucleGanancia.gain.linearRampToValueAtTime(0.9, ctx.currentTime + 0.35);
      bucle.connect(bucleGanancia).connect(general);
      bucle.start(0, 0.03);
    }

    function pararBucle(segundos = 0.5) {
      if (!bucle) return;
      const viejo = bucle;
      const g = bucleGanancia;
      g.gain.cancelScheduledValues(ctx.currentTime);
      g.gain.setValueAtTime(g.gain.value, ctx.currentTime);
      g.gain.linearRampToValueAtTime(0, ctx.currentTime + segundos);
      viejo.playbackRate.linearRampToValueAtTime(0.55, ctx.currentTime + segundos);
      viejo.stop(ctx.currentTime + segundos + 0.05);
      bucle = null;
      bucleGanancia = null;
    }

    return {
      prender(si) {
        estado.sonido = si;
        if (si) {
          if (!contexto()) { estado.sonido = false; api.avisar?.('Este navegador no puede pasar el sonido.'); return; }
          general.gain.cancelScheduledValues(ctx.currentTime);
          general.gain.setTargetAtTime(0.8, ctx.currentTime, 0.08);
          bajar();
          if (estado.marcha === 'andando' || estado.marcha === 'arrancando') empezarBucle();
        } else if (ctx) {
          general.gain.setTargetAtTime(0, ctx.currentTime, 0.06);
          pararBucle(0.2);
          golpe?.stop(ctx.currentTime + 0.25);
          golpe = null;
        }
      },
      arrancar() {
        if (!estado.sonido || !contexto()) return;
        empezarBucle();
      },
      apagar() { if (ctx) { pararBucle(0.9); golpe?.stop(ctx.currentTime + 0.3); golpe = null; } },
      async acelerar() {
        if (!estado.sonido || !contexto() || !(await bajar())) return;
        golpe?.stop();
        golpe = ctx.createBufferSource();
        golpe.buffer = buffers.acelerando;
        const g = ctx.createGain();
        g.gain.value = 1;
        golpe.connect(g).connect(general);
        golpe.start(0, DESDE_SEGUNDO);
        const este = golpe;
        golpe.onended = () => { if (golpe === este) golpe = null; };
        // El ralentí se baja mientras suena el acelerón (la grabación ya trae su propio ralentí)
        if (bucleGanancia) {
          const ahora = ctx.currentTime;
          const dura = buffers.acelerando.duration - DESDE_SEGUNDO;
          bucleGanancia.gain.cancelScheduledValues(ahora);
          bucleGanancia.gain.setValueAtTime(bucleGanancia.gain.value, ahora);
          bucleGanancia.gain.linearRampToValueAtTime(0.08, ahora + 0.12);
          bucleGanancia.gain.setValueAtTime(0.08, ahora + dura - 1.2);
          bucleGanancia.gain.linearRampToValueAtTime(0.9, ahora + dura);
        }
      },
      seguir(rpm, acelerando) {
        if (!bucle || acelerando) return;
        // Más vueltas = el bucle suena más agudo (hasta 1,6: más arriba suena a dibujo animado)
        const tono = THREE.MathUtils.clamp(0.75 + 0.25 * (rpm / RALENTI) ** 0.9, 0.6, 1.6);
        bucle.playbackRate.setTargetAtTime(tono, ctx.currentTime, 0.05);
      },
      pausar(si) {
        if (!ctx) return;
        if (si) ctx.suspend();
        else if (estado.sonido && estado.marcha !== 'apagado') ctx.resume();
      },
    };
  })();

  document.addEventListener('visibilitychange', () => sonido.pausar(document.hidden));

  /* ===================== El panel ===================== */

  const ui = crearPanel({
    alPrender: () => (estado.marcha === 'apagado' || estado.marcha === 'apagando' ? prender() : apagar()),
    alAcelerar: acelerar,
    alAdentro: (si) => porAdentro(si),
    alSonido: () => { sonido.prender(!estado.sonido); ui.actualizar(); },
    alLento: () => { estado.lento = !estado.lento; ui.actualizar(); },
    estado,
  });

  api.on?.('modo', (modo) => mostrar(modo === 'motor'));
  if (api.modo?.() === 'motor') mostrar(true);

  function mostrar(si) {
    estado.visible = Boolean(si);
    ui.panel.hidden = !estado.visible;
    if (!estado.visible) {
      apagar();
      porAdentro(false);
    }
  }

  function apagarTodo() {
    apagar();
    devolverGiratorios();
  }

  // Cuando terminó de apagarse, las poleas vuelven a su lugar exacto
  const vigilar = setInterval(() => {
    if (estado.marcha === 'apagado' && giratorios.some((g) => g.base)) { devolverGiratorios(); sacudir(false); api.pedirRender(); }
  }, 500);

  return {
    prender, apagar: apagarTodo, acelerar, porAdentro,
    sonido: (si) => { sonido.prender(Boolean(si)); ui.actualizar(); },
    camaraLenta: (si) => { estado.lento = Boolean(si); ui.actualizar(); },
    mostrar,
    montar: (elemento) => elemento?.append(ui.panel),
    estado: () => ({ andando: estado.marcha !== 'apagado', marcha: estado.marcha, rpm: Math.round(estado.rpm),
      adentro: estado.adentro, lento: estado.lento, sonido: estado.sonido, angulo: estado.theta }),
    interno: () => cargarInterno(),
    panel: ui.panel,
    destruir() { apagarTodo(); clearInterval(vigilar); ui.panel.remove(); },
  };
}

/* ===================== Panel (HTML) ===================== */

function crearPanel({ alPrender, alAcelerar, alAdentro, alSonido, alLento, estado }) {
  const crear = (etiqueta, props = {}, ...hijos) => {
    const nodo = Object.assign(document.createElement(etiqueta), props);
    nodo.append(...hijos);
    return nodo;
  };
  const boton = (texto, clase, alTocar) => {
    const b = crear('button', { type: 'button', className: clase, textContent: texto });
    b.addEventListener('click', alTocar);
    return b;
  };

  const panel = crear('section', { className: 'motor-vivo', id: 'motor-vivo', hidden: true });
  panel.setAttribute('aria-labelledby', 'motor-vivo-titulo');

  const titulo = crear('h2', { id: 'motor-vivo-titulo', textContent: 'Motor en marcha' });
  const numero = crear('b', { textContent: '0' });
  const rpmTexto = crear('p', { className: 'mv-rpm' }, numero, crear('span', { textContent: 'vueltas por minuto' }));
  const nota = crear('small', { className: 'mv-nota', textContent: '' });
  rpmTexto.append(nota);

  const prender = boton('Prender', 'boton principal mv-prender', alPrender);
  const acelerar = boton('Acelerar', 'boton mv-acelerar', alAcelerar);
  acelerar.disabled = true;

  const afuera = boton('Por afuera', '', () => alAdentro(false));
  const adentro = boton('Por adentro', '', () => alAdentro(true));
  const vista = crear('div', { className: 'mv-vista' }, afuera, adentro);
  vista.setAttribute('role', 'group');
  vista.setAttribute('aria-label', 'Cómo ver el motor');

  const icono = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor"/><path class="mv-ondas" d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path class="mv-mudo" d="M16 9l5 6M21 9l-5 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  const sonido = boton('', 'boton mv-chico mv-sonido', alSonido);
  sonido.innerHTML = `${icono}<span>Sonido</span>`; // el ícono es fijo (no viene de afuera)
  const lento = boton('Cámara lenta', 'boton mv-chico', alLento);

  const cargando = crear('p', { className: 'mv-cargando', hidden: true, textContent: 'Bajando el motor por dentro…' });
  cargando.setAttribute('role', 'status');

  // Leyenda de los 4 tiempos (solo por adentro)
  const lista = crear('ol', { className: 'mv-tiempos' });
  for (const t of TIEMPOS.slice(2).concat(TIEMPOS.slice(0, 2))) {   // en el orden del ciclo: admisión primero
    const li = crear('li', {}, crear('i', { className: 'mv-color' }), crear('b', { textContent: t.nombre }), crear('span', { textContent: t.texto }));
    li.style.setProperty('--color', t.color);
    li.dataset.tiempo = t.id;
    lista.append(li);
  }
  const orden = crear('p', { className: 'mv-orden' });
  orden.append(crear('span', { textContent: 'Orden de encendido' }));
  const cilindros = ORDEN_ENCENDIDO.map((n) => crear('i', { textContent: String(n) }));
  orden.append(crear('span', { className: 'mv-cilindros' }, ...cilindros));
  const leyenda = crear('div', { className: 'mv-leyenda', hidden: true }, lista, orden);

  const vivo = crear('p', { className: 'solo-lector' });
  vivo.setAttribute('aria-live', 'polite');

  panel.append(
    crear('div', { className: 'mv-cabeza' }, titulo, rpmTexto),
    crear('div', { className: 'mv-fila' }, prender, acelerar),
    vista,
    cargando,
    leyenda,
    crear('div', { className: 'mv-fila mv-opciones' }, sonido, lento),
    vivo,
  );

  const escena = document.getElementById('escena') ?? document.body;
  escena.append(panel);

  let ultimoEncendido = -1;

  return {
    panel,
    actualizar() {
      const andando = estado.marcha === 'andando' || estado.marcha === 'arrancando';
      prender.textContent = andando ? 'Apagar' : 'Prender';
      acelerar.disabled = !andando;
      afuera.setAttribute('aria-pressed', String(!estado.adentro));
      adentro.setAttribute('aria-pressed', String(estado.adentro));
      sonido.setAttribute('aria-pressed', String(estado.sonido));
      lento.setAttribute('aria-pressed', String(estado.lento));
      leyenda.hidden = !estado.adentro;
      panel.dataset.adentro = String(estado.adentro);
      this.rpm();
    },
    rpm() {
      numero.textContent = new Intl.NumberFormat('es-AR').format(Math.round(estado.rpm / 10) * 10);
      nota.textContent = estado.marcha === 'apagado' ? 'Apagado' : estado.lento ? 'Lo ves en cámara lenta' : 'Lo ves más lento que en la realidad';
      // En cámara lenta se marca el cilindro que está explotando (más rápido sería un parpadeo)
      let actual = -1;
      if (estado.adentro && estado.lento && estado.marcha !== 'apagado') actual = Math.floor(mod(estado.theta, 720) / 90) % 8;
      if (actual !== ultimoEncendido) {
        cilindros.forEach((c, i) => c.classList.toggle('activo', i === actual));
        ultimoEncendido = actual;
      }
    },
    mostrarCargando(si) { cargando.hidden = !si; adentro.disabled = si; },
    anunciar(texto) { vivo.textContent = texto; },
  };
}

function agregarEstilos() {
  const yaEsta = [...document.querySelectorAll('link[rel="stylesheet"]')].some((l) => l.href === RUTA_CSS || /motor-vivo\.css$/.test(l.href));
  if (yaEsta) return;
  document.head.append(Object.assign(document.createElement('link'), { rel: 'stylesheet', href: RUTA_CSS }));
}
