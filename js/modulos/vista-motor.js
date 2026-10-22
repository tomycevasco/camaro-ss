/*
  Vista Motor: el V8 sale del auto, va al soporte de taller y ahí se gira, se separa en orden, se
  arma paso a paso y cada pieza muestra su ficha. «Volver al auto» lo pone de nuevo en el vano.

    1. Se abre el capot, la grúa levanta el motor del vano (el radiador y la batería quedan en el auto).
    2. Fundido a blanco: el auto se va, aparece el soporte y el motor baja hasta quedar abrazado
       por la brida de atrás (donde va la caja).
    3. En el soporte: girarlo sobre el eje del cigüeñal, separarlo en el orden de un desarme real,
       armarlo pieza por pieza y tocar cada pieza para ver su ficha.

  Cómo se engancha (tanda de integración, sin tocar este archivo):
    · modelos/manifiesto.json → "modulos": { …, "vista_motor": "js/modulos/vista-motor.js" }
    · js/app.js → cargarModulo(modulos.vista_motor), con el auto ya cargado y en su lugar.
    · css/vista-motor.css lo enlaza este archivo solo, si la página todavía no lo tiene.
    · El botón: si en la página hay un botón con [data-vista-motor], ese abre y cierra la vista;
      si no hay ninguno, este módulo pone el botón «Motor» en la barra de arriba.

  Lo que deja para los demás módulos (motor-vivo.js, por ejemplo):
    · api.vistaMotor → { activa(), entrar(), salir(), centrar(), girar(grados), separar(0..1), motor, soporte, ranura }
    · Sin mouse ni rueda: los botones generales de acercar / alejar (app.js) siguen a la vista con el motor
      en el soporte; las flechas y + / − andan aunque el foco no esté en el 3D; api.vistaInicial() centra el motor.
    · El evento «vista-motor» en document, con detail { activa, motor, soporte, ranura }: se avisa
      con activa: true cuando el motor ya quedó en el soporte y con activa: false apenas se empieza a ir.
    · La ranura #vista-motor-extra en la barra de abajo: ahí van Prender, Acelerar, por afuera / por adentro.

  Hacia dónde sale cada pieza, cuánto y en qué orden: manifiesto.json → vista_motor (no se escribe acá).
  Si dos piezas salen para el mismo lado y una está encima de la otra, la de afuera se corre un poco
  más, para que no se metan una adentro de la otra.
*/

import { obtenerMovimiento, encuadrarEsfera } from './movimiento.js';

const ALTO_GRUA = 1.0;        // cuánto levanta la grúa el motor para sacarlo del vano, en metros
const AIRE_ENTRE_PIEZAS = 0.1; // lo que queda entre dos piezas apiladas cuando se separan
const VENTANA_SEPARAR = 0.18;  // qué parte de la barra tarda cada pieza en salir (se pisan un poco)

// Nombres de las piezas que todavía no tienen ficha (con ficha, manda el nombre de la ficha).
const NOMBRES = {
  'tapa-distribucion': 'Tapa de la distribución',
  'soportes-motor': 'Soportes del motor',
  termostato: 'Termostato',
  bujias: 'Bujías',
  balanceador: 'Balanceador',
  poleas: 'Poleas',
  'bomba-nafta': 'Bomba de nafta',
  'filtro-aceite': 'Filtro de aceite',
  'varilla-aceite': 'Varilla del aceite',
  mangueras: 'Mangueras',
};

const sinMovimiento = matchMedia('(prefers-reduced-motion: reduce)');
const esperar = (ms) => new Promise((listo) => setTimeout(listo, sinMovimiento.matches ? 0 : ms));
const limpio = (nombre) => nombre.replace(/(_\d+|\.?\d{3})$/, '').replaceAll('_', '-');
const esPiso = (o) => /^(piso|suelo|estudio|floor)/i.test(o.name);
const curvaSuave = (k) => k * k * (3 - 2 * k);

export async function iniciar(api) {
  const { THREE, escena, camara, controles, renderer, raiz } = api;
  const V = (lista, porDefecto = [0, 0, 0]) => new THREE.Vector3(...(Array.isArray(lista) ? lista : porDefecto));

  sumarEstilos();
  const manifiesto = await fetch('modelos/manifiesto.json', { cache: 'no-cache' }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const conf = manifiesto?.vista_motor ?? {};

  const motor = buscarNodo(raiz, conf.raiz ?? 'motor', (o) => o.children.length > 0);
  const ui = armarInterfaz();
  if (!motor) {
    ui.botonMotor.addEventListener('click', () => api.avisar('El motor todavía no está en el modelo 3D.'));
    return null;
  }

  const movimiento = obtenerMovimiento(api); // para dejar todo en su lugar antes de sacar el motor

  /* ---------- Puntos de enganche (en el sistema del motor) ---------- */

  const punto = (clave, porDefecto) => {
    const datos = conf[clave] ?? {};
    const enganche = datos.enganche && buscarNodo(motor, datos.enganche);
    return enganche ? enganche.position.clone() : V(datos.punto, porDefecto);
  };
  const ejeCiguenal = punto('eje_ciguenal', [0, 0.35, 1.21]);
  const direccionCiguenal = V(conf.eje_ciguenal?.direccion, [0, 0, 1]).normalize();
  const brida = punto('soporte', [0, 0.35, 0.882]);
  const gancho = punto('gancho', [0, 0.91, 1.2]);
  const medidas = conf.soporte?.medidas_sugeridas ?? {};
  const altoEje = Number(medidas.alto_del_eje) || 0.8;
  const enSoporte = new THREE.Vector3(ejeCiguenal.x, altoEje, ejeCiguenal.z); // dónde queda el cigüeñal en el soporte
  const izado = new THREE.Vector3(0, ALTO_GRUA, 0);

  const reposo = { posicion: motor.position.clone(), giro: motor.quaternion.clone() };

  // Pone el motor de modo que «pivote» (un punto del motor) quede en «destino», girado «q».
  function colocar(pivote, destino, q) {
    motor.quaternion.copy(q);
    motor.position.copy(destino).sub(pivote.clone().applyQuaternion(q));
    motor.updateMatrixWorld(true);
    api.pedirRender();
  }
  const giroCiguenal = (angulo) => new THREE.Quaternion().setFromAxisAngle(direccionCiguenal, angulo);
  const balanceo = (angulo) => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), angulo);
  const colgado = (k, vaiven = 0) => colocar(gancho, gancho.clone().addScaledVector(izado, k), balanceo(vaiven));
  // bajada: 0 = colgado arriba del soporte, 1 = apoyado en el soporte
  const enElSoporte = (bajada, angulo) => colocar(
    ejeCiguenal,
    ejeCiguenal.clone().add(izado).lerp(enSoporte, bajada),
    giroCiguenal(angulo),
  );
  const aReposo = () => { motor.position.copy(reposo.posicion); motor.quaternion.copy(reposo.giro); motor.updateMatrixWorld(true); api.pedirRender(); };

  /* ---------- El soporte de taller, la grúa y la sombra ---------- */

  const soporte = armarSoporte(medidas);
  // La base del soporte va en el piso, justo debajo de la brida, y sale hacia atrás («mira»).
  const bridaEnSoporte = brida.clone().sub(ejeCiguenal).add(enSoporte);
  soporte.grupo.position.set(bridaEnSoporte.x, 0, bridaEnSoporte.z);
  const mira = V(conf.soporte?.mira, [0, 0, -1]);
  soporte.grupo.rotation.y = Math.atan2(-mira.x, -mira.z);
  soporte.cabezal.position.y = bridaEnSoporte.y;
  soporte.grupo.visible = false;
  escena.add(soporte.grupo);
  soporte.grupo.updateMatrixWorld(true);
  const ejeCabezal = direccionCiguenal.clone().applyQuaternion(soporte.grupo.quaternion.clone().invert());

  const grua = armarGrua();
  grua.visible = false;
  escena.add(grua);

  // Las pinturas nuevas se arman en segundo plano (armarlas al dibujar congela la página un rato).
  const pinturasListas = renderer.compileAsync(soporte.grupo, camara, escena).catch(() => {});
  if (!renderer.shadowMap.enabled) soporte.sombra.material.opacity = 0.62; // sin sombras de verdad, la pintada pesa más

  function moverGrua() {
    const arriba = motor.localToWorld(gancho.clone());
    const largo = 5 - arriba.y;
    grua.position.copy(arriba);
    grua.userData.cable.scale.y = Math.max(largo, 0.01);
    grua.userData.cable.position.y = largo / 2;
  }

  /* ---------- Las piezas que se separan ---------- */

  let unidades = null;      // [{ id, rango, objeto, p0, local, general, propio, paso }]
  const porId = new Map();  // id → [unidad]
  let ordenArmado = [];     // ids, del bloque al filtro de aire

  function buscarPieza(id) {
    return motor.children.find((o) => limpio(o.name) === id) ?? buscarNodo(motor, id);
  }

  function prepararUnidades() {
    motor.updateMatrixWorld(true);
    const aMotor = motor.matrixWorld.clone().invert();
    const giroMotor = motor.getWorldQuaternion(new THREE.Quaternion());
    const lista = [];
    const pasos = Array.isArray(conf.orden_desarme) ? conf.orden_desarme : [];
    pasos.forEach((paso, indice) => {
      const objeto = paso?.id && buscarPieza(paso.id);
      if (!objeto) return;
      const partes = paso.por_lado ? objeto.children.filter(conMalla) : [];
      for (const parte of partes.length ? partes : [objeto]) {
        const caja = new THREE.Box3().setFromObject(parte).applyMatrix4(aMotor);
        const direccion = V(paso.sale);
        // De a dos: cada parte se va para su lado (el signo de su x)
        if (paso.por_lado) direccion.x = Math.abs(direccion.x) * (caja.getCenter(new THREE.Vector3()).x >= 0 ? 1 : -1);
        if (direccion.lengthSq() > 0) direccion.normalize();
        lista.push({ id: paso.id, indice, objeto: parte, p0: parte.position.clone(), direccion, distancia: Math.max(Number(paso.distancia) || 0, 0), caja, general: 0, propio: 0, paso: 0 });
      }
    });

    // De adentro hacia afuera: si una pieza sale para el mismo lado que otra que tiene abajo, va más lejos.
    const colocadas = [];
    for (let i = lista.length - 1; i >= 0; i--) {
      const u = lista[i];
      let distancia = u.distancia;
      if (distancia > 0) {
        for (const otra of colocadas) {
          if (otra.id === u.id || otra.direccion.dot(u.direccion) < 0.85) continue;
          if (solapamiento(u.caja, otra.caja, u.direccion) < 0.3) continue;
          distancia = Math.max(distancia, otra.corrimiento.dot(u.direccion) + AIRE_ENTRE_PIEZAS);
        }
      }
      u.corrimiento = u.direccion.clone().multiplyScalar(distancia);
      colocadas.push(u);
    }

    // El corrimiento se guarda en el sistema del padre de cada parte (así anda aunque esté adentro de un grupo).
    for (const u of lista) {
      const giroPadre = u.objeto.parent.getWorldQuaternion(new THREE.Quaternion());
      const padreEnMotor = giroMotor.clone().invert().multiply(giroPadre);
      u.local = u.corrimiento.clone().applyQuaternion(padreEnMotor.invert());
    }

    // Rango: en qué turno sale cada pieza al mover la barra (las de distancia 0 no se mueven).
    const indicesQueSalen = [...new Set(lista.filter((u) => u.distancia > 0).map((u) => u.indice))];
    for (const u of lista) u.rango = indicesQueSalen.indexOf(u.indice);
    for (const u of lista) {
      if (!porId.has(u.id)) porId.set(u.id, []);
      porId.get(u.id).push(u);
    }
    ordenArmado = [...new Set(lista.map((u) => u.id))].reverse();
    unidades = lista;
    totalQueSalen = indicesQueSalen.length;
  }
  let totalQueSalen = 0;

  // Cuánto se pisan dos piezas vistas desde la dirección en que sale la primera (0 = nada, 1 = una tapa a la otra).
  function solapamiento(a, b, direccion) {
    const u = new THREE.Vector3(1, 0, 0);
    if (Math.abs(direccion.dot(u)) > 0.9) u.set(0, 1, 0);
    u.sub(direccion.clone().multiplyScalar(direccion.dot(u))).normalize();
    const w = new THREE.Vector3().crossVectors(direccion, u);
    const rango = (caja, eje) => {
      let min = Infinity; let max = -Infinity;
      for (let i = 0; i < 8; i++) {
        const esquina = new THREE.Vector3(i & 1 ? caja.max.x : caja.min.x, i & 2 ? caja.max.y : caja.min.y, i & 4 ? caja.max.z : caja.min.z);
        const d = esquina.dot(eje);
        min = Math.min(min, d); max = Math.max(max, d);
      }
      return [min, max];
    };
    const pisa = (ra, rb) => Math.max(0, Math.min(ra[1], rb[1]) - Math.max(ra[0], rb[0]));
    const [au, bu, aw, bw] = [rango(a, u), rango(b, u), rango(a, w), rango(b, w)];
    const area = (ru, rw) => Math.max((ru[1] - ru[0]) * (rw[1] - rw[0]), 1e-6);
    return (pisa(au, bu) * pisa(aw, bw)) / Math.min(area(au, aw), area(bu, bw));
  }

  function aplicar() {
    for (const u of unidades ?? []) {
      const k = Math.max(u.general, u.propio, u.paso);
      u.objeto.position.copy(u.p0).addScaledVector(u.local, k);
    }
    api.pedirRender();
  }

  let separacion = 0;
  function fijarSeparacion(valor) {
    separacion = THREE.MathUtils.clamp(valor, 0, 1);
    const salto = (1 - VENTANA_SEPARAR) / Math.max(totalQueSalen - 1, 1);
    for (const u of unidades ?? []) {
      u.general = u.rango < 0 ? 0 : curvaSuave(THREE.MathUtils.clamp((separacion - u.rango * salto) / VENTANA_SEPARAR, 0, 1));
    }
    ui.separar.value = String(Math.round(separacion * 100));
    aplicar();
  }

  // Anima una cantidad («propio» o «paso») de las partes de una pieza; si llega otra orden, manda la última.
  function animarCantidad(id, cantidad, hasta, segundos) {
    const lista = porId.get(id) ?? [];
    if (!lista.length) return Promise.resolve();
    const turno = {};
    for (const u of lista) u[`turno_${cantidad}`] = turno;
    const desde = lista.map((u) => u[cantidad]);
    return api.animar(segundos, (k) => {
      lista.forEach((u, i) => { if (u[`turno_${cantidad}`] === turno) u[cantidad] = desde[i] + (hasta - desde[i]) * k; });
      aplicar();
    });
  }

  const mostrarPieza = (id, visible) => {
    for (const u of porId.get(id) ?? []) u.objeto.visible = visible;
    api.pedirRender();
  };
  const nombreDe = (id) => api.fichas.get(id)?.nombre ?? NOMBRES[id] ?? id.replaceAll('-', ' ').replace(/^./, (c) => c.toUpperCase());

  /* ---------- Cámara ---------- */

  const cajaDe = (...objetos) => {
    const caja = new THREE.Box3();
    for (const o of objetos) o.updateMatrixWorld(true); // las piezas recién movidas todavía no se dibujaron
    for (const o of objetos) o.traverse((x) => { if (x.isMesh && x.visible && !x.userData.sinCaja) caja.expandByObject(x); });
    return caja;
  };

  // De tres cuartos de adelante, del lado del conductor y un poco de arriba (como la vista inicial del auto).
  const direccionVista = new THREE.Vector3(0.95, 0.55, 1).normalize();
  function distanciaPara(radio, factor) {
    const fovV = THREE.MathUtils.degToRad(camara.fov);
    const fovH = 2 * Math.atan(Math.tan(fovV / 2) * camara.aspect);
    return (radio / Math.sin(Math.min(fovV, fovH) / 2)) * factor;
  }
  function ponerCamara(esfera, factor = 1) {
    controles.target.copy(esfera.center);
    camara.position.copy(esfera.center).addScaledVector(direccionVista, distanciaPara(esfera.radius, factor));
    controles.update();
    api.pedirRender();
  }
  function encuadrarMotor(factor = 0.92) {
    const esfera = cajaDe(motor, soporte.grupo).getBoundingSphere(new THREE.Sphere());
    return encuadrarEsfera(api, esfera, { factor });
  }

  /* ---------- El auto: lo que se esconde mientras el motor está en el soporte ---------- */

  const quedanEnElAuto = (Array.isArray(conf.quedan_en_el_auto) ? conf.quedan_en_el_auto : ['radiador', 'bateria'])
    .map((id) => buscarPieza(id)).filter(Boolean);
  let escondidos = [];

  function esconderAuto() {
    escondidos = [];
    for (const arriba of raiz.children) {
      for (const o of arriba.isMesh ? [arriba] : arriba.children) {
        if (o === motor || /interno/i.test(o.name)) continue;
        if (esPiso(o) && !/sombra/i.test(o.name)) continue; // el piso del estudio queda; la sombra del auto, no
        escondidos.push([o, o.visible]);
        o.visible = false;
      }
    }
    api.pedirRender();
  }
  function mostrarAuto() {
    for (const [o, visible] of escondidos) o.visible = visible;
    escondidos = [];
    api.pedirRender();
  }

  /* ---------- Entrar y salir ---------- */

  const estado = { activa: false, ocupada: false, angulo: 0, paso: false, actual: -1 };
  let turno = 0; // cada salida «al toque» corta lo que estaba animando

  const avisarALosDemas = (activa) => {
    document.dispatchEvent(new CustomEvent('vista-motor', { detail: { activa, motor, soporte: soporte.grupo, ranura: ui.ranura } }));
  };

  function fundido(prendido) {
    ui.fundido.classList.toggle('visible', prendido);
    return esperar(320);
  }

  async function entrar() {
    if (estado.activa || estado.ocupada) return;
    // Todo en su lugar antes de sacarlo: modo Explorar, nada separado, nada marcado.
    // (Explorar va antes de marcarla ocupada: si no, el aviso de «tocaron un modo» la cortaría.)
    document.querySelector('.modos [data-modo="explorar"]')?.click();
    const miTurno = ++turno;
    const sigue = () => miTurno === turno;
    estado.ocupada = true;
    ponerOcupada(true, 'Sacando el motor del auto…');
    movimiento.reiniciarPropios();
    movimiento.fijarGeneral(0);
    api.seleccionar(null);
    document.body.dataset.vista = 'motor';
    marcarLista(true);
    for (const b of document.querySelectorAll('.modos button')) b.setAttribute('aria-pressed', 'false');

    // La cámara mira el vano y el lugar de arriba, por donde va a salir.
    const cajaVano = cajaDe(motor);
    cajaVano.union(cajaVano.clone().translate(izado));
    encuadrarEsfera(api, cajaVano.getBoundingSphere(new THREE.Sphere()), { factor: 1.1 });
    await api.abrir('capot', true);
    if (!sigue()) return;
    if (!unidades) prepararUnidades();

    // El radiador y la batería se quedan en el auto (se cuelgan del .glb, fuera del motor).
    for (const o of quedanEnElAuto) motor.parent.attach(o);

    // 1. La grúa lo levanta, con un vaivén chiquito de cosa colgada.
    grua.visible = true;
    moverGrua();
    await api.animar(1.5, (k) => {
      if (!sigue()) return;
      colgado(k, Math.sin(k * Math.PI * 2) * 0.03 * (1 - k));
      moverGrua();
    });
    if (!sigue()) return;

    // 2. Fundido: se va el auto, aparece el soporte.
    await pinturasListas;
    await fundido(true);
    if (!sigue()) return;
    esconderAuto();
    soporte.grupo.visible = true;
    estado.angulo = 0;
    girarCabezal(0);
    enElSoporte(1, 0);
    const esferaSoporte = cajaDe(motor, soporte.grupo).getBoundingSphere(new THREE.Sphere());
    enElSoporte(0, 0);
    moverGrua();
    controles.minDistance = 0.8; // al elegir una pieza de la lista, la cámara no se mete adentro del motor
    controles.maxDistance = esferaSoporte.radius * 9;
    ponerCamara(esferaSoporte, 1.08);
    await fundido(false);
    if (!sigue()) return;

    // 3. Baja hasta el soporte.
    await api.animar(1.2, (k) => {
      if (!sigue()) return;
      enElSoporte(k, 0);
      moverGrua();
    });
    if (!sigue()) return;
    grua.visible = false;
    api.pedirRender();

    estado.activa = true;
    estado.ocupada = false;
    ponerOcupada(false, 'Listo: el motor está en el soporte.');
    ui.botonMotor.setAttribute('aria-pressed', 'true');
    ui.titulo.classList.add('visible');
    avisarALosDemas(true);
  }

  async function salir() {
    if (!estado.activa || estado.ocupada) return;
    const miTurno = ++turno;
    const sigue = () => miTurno === turno;
    estado.ocupada = true;
    ui.titulo.classList.remove('visible');
    avisarALosDemas(false);
    ponerOcupada(true, 'Volviendo al auto…');
    api.seleccionar(null);

    // Se arma de nuevo y vuelve derecho.
    if (estado.paso) salirDelPaso();
    const desde = separacion;
    const anguloDesde = estado.angulo;
    const propios = unidades.map((u) => u.propio);
    await api.animar(desde > 0 || anguloDesde || propios.some(Boolean) ? 0.9 : 0, (k) => {
      if (!sigue()) return;
      unidades.forEach((u, i) => { u.propio = propios[i] * (1 - k); });
      fijarSeparacion(desde * (1 - k));
      estado.angulo = anguloDesde * (1 - k);
      girarCabezal(estado.angulo);
      enElSoporte(1, estado.angulo);
    });
    if (!sigue()) return;
    estado.angulo = 0;

    // La grúa lo levanta del soporte…
    grua.visible = true;
    moverGrua();
    await api.animar(1, (k) => {
      if (!sigue()) return;
      enElSoporte(1 - k, 0);
      moverGrua();
    });
    if (!sigue()) return;

    // …fundido: vuelve el auto…
    await fundido(true);
    if (!sigue()) return;
    soporte.grupo.visible = false;
    mostrarAuto();
    colgado(1);
    moverGrua();
    const cajaVano = cajaDe(motor);
    cajaVano.union(cajaVano.clone().translate(izado.clone().negate()));
    ponerCamara(cajaVano.getBoundingSphere(new THREE.Sphere()), 1.1);
    await fundido(false);
    if (!sigue()) return;

    // …y lo baja al vano.
    await api.animar(1.4, (k) => {
      if (!sigue()) return;
      colgado(1 - k, Math.sin(k * Math.PI * 2) * 0.02 * k);
      moverGrua();
    });
    if (!sigue()) return;
    terminarSalida();
    await api.abrir('capot', false);
    if (!sigue()) return;
    api.vistaInicial?.(true);
    ponerOcupada(false, 'El motor volvió a su lugar.');
  }

  // Lo que deja todo como estaba (se usa al final de la salida y en la salida «al toque»).
  function terminarSalida() {
    grua.visible = false;
    soporte.grupo.visible = false;
    aReposo();
    for (const o of quedanEnElAuto) motor.attach(o);
    if (escondidos.length) mostrarAuto();
    for (const u of unidades ?? []) { u.general = 0; u.propio = 0; u.paso = 0; u.objeto.visible = true; }
    separacion = 0;
    ui.separar.value = '0';
    aplicar();
    estado.activa = false;
    estado.ocupada = false;
    estado.angulo = 0;
    girarCabezal(0);
    delete document.body.dataset.vista;
    ui.titulo.classList.remove('visible');
    marcarLista(false);
    ui.botonMotor.setAttribute('aria-pressed', 'false');
    const modo = api.modo?.() ?? 'explorar';
    for (const b of document.querySelectorAll('.modos button')) b.setAttribute('aria-pressed', String(b.dataset.modo === modo));
  }

  // Si tocan Explorar / Separar / Paso a paso con el motor afuera: vuelve todo de golpe y sigue el modo pedido.
  function salirAlToque() {
    if (!estado.activa && !estado.ocupada) return;
    const estaba = estado.activa;
    turno++;
    if (estaba) avisarALosDemas(false);
    if (estado.paso) salirDelPaso();
    ui.fundido.classList.remove('visible');
    api.seleccionar(null);
    terminarSalida();
    api.abrir('capot', false);
    api.vistaInicial?.(true);
    ponerOcupada(false, '');
  }

  /* ---------- En el soporte: girar, separar, paso a paso, fichas ---------- */

  function girarCabezal(angulo) {
    soporte.cabezal.quaternion.setFromAxisAngle(ejeCabezal, angulo);
  }

  function girar(grados = 90) {
    return girarHasta(estado.angulo + THREE.MathUtils.degToRad(grados));
  }

  function girarHasta(hasta) {
    if (!estado.activa) return Promise.resolve();
    const desde = estado.angulo;
    estado.angulo = hasta;
    const miTurno = turno;
    return api.animar(Math.abs(hasta - desde) < 1e-6 ? 0 : 1.1, (k) => {
      if (miTurno !== turno || !estado.activa) return;
      const angulo = desde + (hasta - desde) * k;
      girarCabezal(angulo);
      enElSoporte(1, angulo);
    });
  }

  function entrarAlPaso() {
    estado.paso = true;
    fijarSeparacion(0);
    for (const u of unidades) { u.propio = 0; u.turno_propio = null; }
    for (const id of ordenArmado) {
      for (const u of porId.get(id)) { u.paso = 1; u.turno_paso = null; }
      mostrarPieza(id, false);
    }
    estado.actual = -1;
    ui.botonPaso.setAttribute('aria-pressed', 'true');
    ui.cajaSeparar.hidden = true;
    ui.cajaPaso.hidden = false;
    irAlPaso(0);
    // Se arma derecho: si estaba dado vuelta, vuelve a la posición de la vuelta más cercana.
    const derecho = Math.round(estado.angulo / (Math.PI * 2)) * Math.PI * 2;
    girarHasta(derecho).then(() => encuadrarMotor(1.1));
  }

  function salirDelPaso() {
    estado.paso = false;
    for (const u of unidades) { u.paso = 0; u.turno_paso = null; u.objeto.visible = true; }
    aplicar();
    estado.actual = -1;
    ui.botonPaso.setAttribute('aria-pressed', 'false');
    ui.cajaSeparar.hidden = false;
    ui.cajaPaso.hidden = true;
    if (api.seleccionada()) api.seleccionar(null);
  }

  function irAlPaso(destino) {
    destino = THREE.MathUtils.clamp(destino, 0, ordenArmado.length - 1);
    const anterior = estado.actual;
    if (destino === anterior) return;
    if (destino > anterior) {
      for (let i = anterior + 1; i <= destino; i++) {
        const id = ordenArmado[i];
        mostrarPieza(id, true);
        animarCantidad(id, 'paso', 0, 0.8);
      }
    } else {
      for (let i = anterior; i > destino; i--) {
        const id = ordenArmado[i];
        animarCantidad(id, 'paso', 1, 0.55).then(() => {
          // Si mientras se iba la volvieron a pedir, se queda.
          if (estado.paso && ordenArmado.indexOf(id) > estado.actual) mostrarPieza(id, false);
        });
      }
    }
    estado.actual = destino;
    const id = ordenArmado[destino];
    ui.pasoTexto.replaceChildren(`Paso ${destino + 1} de ${ordenArmado.length}`, Object.assign(document.createElement('small'), { textContent: nombreDe(id) }));
    ui.pasoAnterior.disabled = destino <= 0;
    ui.pasoSiguiente.disabled = destino >= ordenArmado.length - 1;
    if (api.fichas.has(id)) api.seleccionar(id); else if (api.seleccionada()) api.seleccionar(null);
  }

  // «Separar esta pieza» de la ficha: con el motor en el soporte, sale en su dirección de desarme.
  function separarPieza(id) {
    if (!porId.has(id)) return false;
    const afuera = (porId.get(id)[0].propio ?? 0) < 0.5;
    animarCantidad(id, 'propio', afuera ? 1 : 0, 0.8);
    return afuera;
  }

  function siguientePieza() {
    if (estado.paso) { irAlPaso(estado.actual + 1); return; }
    const conFicha = [...ordenArmado].reverse().filter((id) => api.fichas.has(id) && api.piezas.has(id));
    if (!conFicha.length) return;
    const i = conFicha.indexOf(api.seleccionada());
    api.seleccionar(conFicha[(i + 1) % conFicha.length], { enfocar: true });
  }

  /* ---------- La interfaz ---------- */

  function ponerOcupada(ocupada, texto) {
    ui.barra.classList.toggle('ocupada', ocupada);
    for (const b of ui.barra.querySelectorAll('button, input')) {
      if (b.closest('#vista-motor-extra')) continue;
      b.disabled = ocupada;
    }
    // El botón Motor no se apaga del todo (perdería el foco del teclado): solo no hace nada mientras viaja.
    ui.botonMotor.setAttribute('aria-disabled', String(ocupada));
    ui.estado.textContent = texto;
    if (!ocupada && estado.paso) { ui.pasoAnterior.disabled = estado.actual <= 0; ui.pasoSiguiente.disabled = estado.actual >= ordenArmado.length - 1; }
    // Si el foco quedó en un botón que se apagó, va a «Volver al auto» o al botón Motor.
    if (!ocupada && (!document.activeElement || document.activeElement === document.body)) {
      (estado.activa ? ui.volver : ui.botonMotor).focus({ preventScroll: true });
    }
  }

  // En la lista quedan solo las piezas del motor que están en el soporte.
  function marcarLista(enMotor) {
    const fuera = new Set(Array.isArray(conf.quedan_en_el_auto) ? conf.quedan_en_el_auto : ['radiador', 'bateria']);
    for (const grupo of document.querySelectorAll('#lista-piezas .grupo-piezas')) {
      const titulo = grupo.querySelector('summary')?.firstChild?.textContent ?? '';
      const esDelMotor = /^motor/i.test(titulo.trim());
      grupo.classList.toggle('vm-fuera', enMotor && !esDelMotor);
      if (enMotor && esDelMotor) grupo.open = true;
    }
    for (const boton of document.querySelectorAll('#lista-piezas button[data-id]')) {
      boton.closest('li')?.classList.toggle('vm-fuera', enMotor && fuera.has(boton.dataset.id));
    }
  }

  ui.botonMotor.addEventListener('click', () => (estado.activa ? salir() : entrar()));
  ui.volver.addEventListener('click', salir);
  ui.girar.addEventListener('click', () => girar(90));
  ui.centrar.addEventListener('click', () => encuadrarMotor());
  ui.botonPaso.addEventListener('click', () => (estado.paso ? salirDelPaso() : entrarAlPaso()));
  ui.pasoAnterior.addEventListener('click', () => irAlPaso(estado.actual - 1));
  ui.pasoSiguiente.addEventListener('click', () => irAlPaso(estado.actual + 1));
  ui.separar.addEventListener('input', () => fijarSeparacion(Number(ui.separar.value) / 100));
  // Al soltar la barra, la cámara se aleja o se acerca para que entre todo.
  ui.separar.addEventListener('change', () => encuadrarMotor());

  // Explorar / Separar / Paso a paso con el motor afuera: primero vuelve todo (esto corre antes que app.js).
  document.querySelector('.modos')?.addEventListener('click', (e) => {
    if (e.target.closest('button') && (estado.activa || estado.ocupada)) salirAlToque();
  }, true);

  // Los botones de la ficha hacen lo de la vista Motor mientras está abierta.
  const fichaSeparar = document.getElementById('ficha-separar');
  const fichaSiguiente = document.getElementById('ficha-siguiente');
  const textoSeparar = (id) => ((porId.get(id)?.[0]?.propio ?? 0) > 0.5 ? 'Volver a su lugar' : 'Separar esta pieza');
  fichaSeparar?.addEventListener('click', (e) => {
    if (!estado.activa) return;
    e.stopImmediatePropagation();
    const id = api.seleccionada();
    if (!id) return;
    const afuera = separarPieza(id);
    fichaSeparar.textContent = afuera ? 'Volver a su lugar' : 'Separar esta pieza';
  }, true);
  fichaSiguiente?.addEventListener('click', (e) => {
    if (!estado.activa) return;
    e.stopImmediatePropagation();
    siguientePieza();
  }, true);
  api.on('seleccion', (id) => {
    if (!estado.activa || !id || !fichaSeparar) return;
    fichaSeparar.hidden = estado.paso || !porId.has(id);
    fichaSeparar.textContent = textoSeparar(id);
  });

  // Tocar una pieza nueva que todavía no tiene ficha: se dice qué es, en vez de no hacer nada.
  const lienzo = renderer.domElement;
  const rayo = new THREE.Raycaster();
  let apretado = null;
  lienzo.addEventListener('pointerdown', (e) => { apretado = { x: e.clientX, y: e.clientY }; }, true);
  lienzo.addEventListener('pointerup', (e) => {
    if (!estado.activa || !apretado) return;
    const movido = Math.hypot(e.clientX - apretado.x, e.clientY - apretado.y);
    apretado = null;
    if (movido > 6) return;
    const id = piezaDelMotorBajo(e);
    if (!id || api.fichas.has(id)) return; // con ficha (o en el aire) se encarga app.js
    e.stopImmediatePropagation();
    if (api.seleccionada()) api.seleccionar(null);
    api.avisar(`${nombreDe(id)}: su ficha todavía no está cargada.`);
  }, true);

  function piezaDelMotorBajo(e) {
    const marco = lienzo.getBoundingClientRect();
    const puntero = new THREE.Vector2(((e.clientX - marco.left) / marco.width) * 2 - 1, -((e.clientY - marco.top) / marco.height) * 2 + 1);
    rayo.setFromCamera(puntero, camara);
    for (const golpe of rayo.intersectObject(motor, true)) {
      let visible = true;
      for (let x = golpe.object; x; x = x.parent) if (!x.visible) visible = false;
      if (!visible) continue;
      let o = golpe.object;
      while (o.parent && o.parent !== motor) o = o.parent;
      return o.parent === motor ? limpio(o.name) : null;
    }
    return null;
  }

  // Sin mouse: con el motor en el soporte, las flechas giran y + / − acercan aunque el foco no esté
  // en el 3D (se le pasan al lienzo, que es el que sabe moverse). En un campo o una barra, no.
  const TECLAS = new Set(['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '=', '-']);
  document.addEventListener('keydown', (e) => {
    if (!estado.activa || !TECLAS.has(e.key) || e.target === lienzo || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.target.closest?.('input, textarea, select, [contenteditable]')) return;
    e.preventDefault();
    lienzo.dispatchEvent(new KeyboardEvent('keydown', { key: e.key, bubbles: true, cancelable: true }));
  });

  // «Vista inicial» (de los botones generales) con el motor en el soporte: lo centra a él, no al auto escondido.
  const vistaInicialDelAuto = api.vistaInicial;
  api.vistaInicial = (...args) => (estado.activa && !estado.ocupada ? encuadrarMotor() : vistaInicialDelAuto?.(...args));

  const control = {
    activa: () => estado.activa,
    centrar: () => (estado.activa ? encuadrarMotor() : Promise.resolve()),
    entrar, salir, girar,
    separar: (valor) => { if (estado.activa && !estado.paso) fijarSeparacion(valor); },
    motor, soporte: soporte.grupo, ranura: ui.ranura,
  };
  api.vistaMotor = control;
  return control;

  /* ---------- Piezas de la escena hechas acá ---------- */

  function armarSoporte({ alto_del_eje: alto = 0.8, radio_brida: radio = 0.2, brazos = 4, largo_base: largo = 0.9 } = {}) {
    const grupo = new THREE.Group();
    grupo.name = 'soporte-taller';
    const cabezal = new THREE.Group(); // la parte que gira con el motor
    cabezal.name = 'soporte-cabezal';
    grupo.add(cabezal);
    cabezal.position.y = alto;

    const pintura = new THREE.MeshStandardMaterial({ name: 'soporte-pintura', color: 0x2b2f36, roughness: 0.5, metalness: 0.35 });
    const cromo = new THREE.MeshStandardMaterial({ name: 'soporte-cromo', color: 0xd9dde2, roughness: 0.22, metalness: 1 });
    const goma = new THREE.MeshStandardMaterial({ name: 'soporte-goma', color: 0x151618, roughness: 0.85 });
    const naranja = new THREE.MeshStandardMaterial({ name: 'soporte-perilla', color: 0xd9600b, roughness: 0.4, metalness: 0.1 });

    const malla = (geometria, material, padre, x = 0, y = 0, z = 0) => {
      const m = new THREE.Mesh(geometria, material);
      m.position.set(x, y, z);
      m.castShadow = true;
      m.receiveShadow = true;
      padre.add(m);
      return m;
    };
    const caja = (ancho, alto2, prof, material, padre, x, y, z) => malla(new THREE.BoxGeometry(ancho, alto2, prof), material, padre, x, y, z);
    const cilindro = (r, largo2, material, eje, padre, x, y, z, lados = 24) => {
      const g = new THREE.CylinderGeometry(r, r, largo2, lados);
      if (eje === 'z') g.rotateX(Math.PI / 2);
      if (eje === 'x') g.rotateZ(Math.PI / 2);
      return malla(g, material, padre, x, y, z);
    };
    // Un caño cuadrado entre dos puntos del piso (a la altura y)
    const cano = (x1, z1, x2, z2, y, grosor) => {
      const largo2 = Math.hypot(x2 - x1, z2 - z1);
      const m = caja(grosor, grosor, largo2, pintura, grupo, (x1 + x2) / 2, y, (z1 + z2) / 2);
      m.rotation.y = Math.atan2(x2 - x1, z2 - z1);
      return m;
    };

    // Cabezal: el plato, los brazos en cruz que se atornillan a la brida y el eje que entra en el caño.
    cilindro(0.072, 0.026, pintura, 'z', cabezal, 0, 0, -0.036, 32);
    cilindro(0.028, 0.2, pintura, 'z', cabezal, 0, 0, -0.15);
    for (let i = 0; i < brazos; i++) {
      const angulo = Math.PI / 4 + (i * Math.PI * 2) / brazos;
      const [c, s] = [Math.cos(angulo), Math.sin(angulo)];
      const medio = (0.05 + radio) / 2;
      const brazo = caja(radio - 0.04, 0.03, 0.016, pintura, cabezal, c * medio, s * medio, -0.024);
      brazo.rotation.z = angulo;
      const pie = caja(0.046, 0.046, 0.008, pintura, cabezal, c * radio, s * radio, -0.01);
      pie.rotation.z = angulo;
      cilindro(0.0085, 0.03, cromo, 'z', cabezal, c * radio, s * radio, -0.002, 12);
      cilindro(0.014, 0.009, cromo, 'z', cabezal, c * radio, s * radio, -0.019, 6); // cabeza del bulón
    }

    // Lo fijo: el caño donde gira el eje, la columna y la perilla que traba el giro.
    const zColumna = -0.29;
    cilindro(0.043, 0.13, pintura, 'z', grupo, 0, alto, -0.2, 28);
    caja(0.085, 0.085, 0.11, pintura, grupo, 0, alto, zColumna + 0.02);
    caja(0.072, alto - 0.02, 0.072, pintura, grupo, 0, 0.06 + (alto - 0.02) / 2, zColumna);
    cilindro(0.007, 0.075, cromo, 'y', grupo, 0, alto + 0.075, -0.2, 10);
    malla(new THREE.SphereGeometry(0.018, 20, 14), naranja, grupo, 0, alto + 0.12, -0.2);

    // La base: travesaño de atrás, dos patas que van hacia adelante (debajo del motor) y un refuerzo.
    const yBase = 0.075;
    const zAdelante = zColumna + largo;
    caja(0.64, 0.05, 0.056, pintura, grupo, 0, yBase, zColumna);
    cano(0.05, zColumna, 0.34, zAdelante, yBase, 0.05);
    cano(-0.05, zColumna, -0.34, zAdelante, yBase, 0.05);
    const zTravesano = zColumna + largo * 0.48;
    const anchoTravesano = 2 * (0.05 + 0.29 * 0.48);
    caja(anchoTravesano, 0.04, 0.044, pintura, grupo, 0, yBase, zTravesano);
    const refuerzo = caja(0.045, 0.045, Math.hypot(0.33, zTravesano - zColumna), pintura, grupo, 0, (0.4 + yBase) / 2, (zColumna + zTravesano) / 2);
    refuerzo.rotation.x = Math.atan2(0.4 - yBase, zTravesano - zColumna);

    // Las cuatro ruedas giratorias.
    for (const [x, z] of [[0.31, zColumna], [-0.31, zColumna], [0.34, zAdelante], [-0.34, zAdelante]]) {
      caja(0.056, 0.008, 0.056, pintura, grupo, x, 0.052, z);
      caja(0.006, 0.036, 0.03, pintura, grupo, x + 0.018, 0.034, z);
      caja(0.006, 0.036, 0.03, pintura, grupo, x - 0.018, 0.034, z);
      cilindro(0.032, 0.024, goma, 'x', grupo, x, 0.032, z, 20);
      cilindro(0.012, 0.032, cromo, 'x', grupo, x, 0.032, z, 12);
    }

    // Sombra de contacto pintada en el piso: que el soporte y el motor se vean apoyados, nunca flotando.
    const lienzoSombra = document.createElement('canvas');
    lienzoSombra.width = lienzoSombra.height = 128;
    const ctx = lienzoSombra.getContext('2d');
    const degradado = ctx.createRadialGradient(64, 64, 4, 64, 64, 64);
    degradado.addColorStop(0, 'rgba(20,22,26,.55)');
    degradado.addColorStop(0.55, 'rgba(20,22,26,.22)');
    degradado.addColorStop(1, 'rgba(20,22,26,0)');
    ctx.fillStyle = degradado;
    ctx.fillRect(0, 0, 128, 128);
    const textura = new THREE.CanvasTexture(lienzoSombra);
    textura.colorSpace = THREE.SRGBColorSpace;
    const sombra = new THREE.Mesh(
      new THREE.PlaneGeometry(1.2, largo + 0.75),
      new THREE.MeshBasicMaterial({ name: 'soporte-sombra', map: textura, transparent: true, depthWrite: false, opacity: 0.4, toneMapped: false }),
    );
    sombra.rotation.x = -Math.PI / 2;
    sombra.position.set(0, 0.002, zColumna + (largo + 0.35) / 2);
    sombra.renderOrder = -1;
    sombra.userData.sinCaja = true; // no cuenta para encuadrar
    grupo.add(sombra);

    return { grupo, cabezal, sombra };
  }

  function armarGrua() {
    const grupo = new THREE.Group();
    grupo.name = 'grua';
    const material = new THREE.MeshStandardMaterial({ name: 'grua', color: 0x2b2f36, roughness: 0.45, metalness: 0.6 });
    const cable = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 1, 8), material);
    const anzuelo = new THREE.Mesh(new THREE.TorusGeometry(0.03, 0.007, 8, 20, Math.PI * 1.6), material);
    anzuelo.rotation.z = Math.PI * 0.7;
    anzuelo.position.y = 0.02;
    cable.castShadow = anzuelo.castShadow = true;
    grupo.add(cable, anzuelo);
    grupo.userData.cable = cable;
    return grupo;
  }
}

/* ---------- Ayudas sin estado ---------- */

function buscarNodo(desde, nombre, condicion = () => true) {
  let hallado = null;
  desde.traverse((o) => {
    if (hallado || o === desde) return;
    if ((o.name === nombre || o.name.replace(/\.\d{3}$/, '') === nombre || limpio(o.name) === nombre) && condicion(o)) hallado = o;
  });
  return hallado;
}

function conMalla(o) {
  let si = false;
  o.traverse((x) => { if (x.isMesh) si = true; });
  return si;
}

function sumarEstilos() {
  if (document.querySelector('link[href$="vista-motor.css"]')) return;
  const enlace = document.createElement('link');
  enlace.rel = 'stylesheet';
  enlace.href = new URL('../../css/vista-motor.css', import.meta.url).href;
  document.head.append(enlace);
}

function armarInterfaz() {
  const crear = (etiqueta, atributos = {}, ...hijos) => {
    const nodo = document.createElement(etiqueta);
    for (const [clave, valor] of Object.entries(atributos)) {
      if (clave === 'texto') nodo.textContent = valor;
      else if (clave === 'clase') nodo.className = valor;
      else nodo.setAttribute(clave, valor);
    }
    nodo.append(...hijos);
    return nodo;
  };
  const boton = (texto, clase = 'boton', extra = {}) => crear('button', { type: 'button', clase, texto, ...extra });

  // El botón «Motor» de arriba (si la página ya trae uno con [data-vista-motor], se usa ese).
  let botonMotor = document.querySelector('[data-vista-motor]');
  if (!botonMotor) {
    botonMotor = crear('button', { type: 'button', clase: 'vm-boton-motor', 'data-vista-motor': '', 'aria-pressed': 'false' });
    botonMotor.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><path d="M4 9h3l1.5-2h5L15 9h2l1.5 2H21v5h-2.5L17 18h-3l-1-1.5H9L7.5 18H4z" fill="currentColor"/><circle cx="11.5" cy="12.5" r="2" fill="var(--superficie, #fff)"/></svg>';
    botonMotor.append('Motor');
    const nav = document.querySelector('.barra .modos');
    if (nav) nav.after(botonMotor); else document.querySelector('.barra')?.append(botonMotor);
  }
  botonMotor.setAttribute('aria-pressed', 'false');
  if (!botonMotor.title) botonMotor.title = 'Sacar el motor del auto y verlo en el soporte de taller';

  const volver = boton('‹ Volver al auto');
  const girar = boton('Girar en el soporte');
  const centrar = boton('Centrar');
  const botonPaso = boton('Paso a paso', 'boton', { 'aria-pressed': 'false' });
  const separar = crear('input', { type: 'range', min: '0', max: '100', value: '0', step: '1' });
  const cajaSeparar = crear('label', { clase: 'separar vm-separar' }, 'Separar en orden ', separar);
  const pasoAnterior = boton('‹ Anterior');
  const pasoTexto = crear('p', { clase: 'paso-texto', 'aria-live': 'polite' });
  const pasoSiguiente = boton('Siguiente ›', 'boton principal');
  const cajaPaso = crear('div', { clase: 'paso vm-paso' }, pasoAnterior, pasoTexto, pasoSiguiente);
  cajaPaso.hidden = true;
  // Acá se enganchan Prender / Acelerar / por afuera-adentro (motor-vivo.js)
  const ranura = crear('div', { clase: 'vm-extra', id: 'vista-motor-extra' });
  const estado = crear('p', { clase: 'solo-lector', role: 'status' });
  // Ayuda corta para usarlo sin mouse ni rueda (el cartel general de controles lo arma app.js)
  const ayuda = crear('p', { clase: 'vm-ayuda' },
    crear('span', { clase: 'vm-ayuda-teclado' },
      'Arrastrá con el touchpad o usá las flechas ', crear('kbd', { texto: '← →' }), ' para girarlo · ',
      crear('kbd', { texto: '+' }), ' y ', crear('kbd', { texto: '−' }), ' acercan y alejan · tocá una pieza para ver su ficha'),
    crear('span', { clase: 'vm-ayuda-dedo' }, 'Arrastrá con un dedo para girarlo · pellizcá para acercar · tocá una pieza para ver su ficha'));
  const barra = crear('div', { clase: 'vm-barra', id: 'vista-motor-barra', role: 'group', 'aria-label': 'Controles del motor en el soporte' },
    crear('div', { clase: 'vm-botones' }, volver, girar, centrar, botonPaso), cajaSeparar, cajaPaso, ranura, ayuda, estado);
  const controles = document.querySelector('.controles') ?? document.body;
  controles.append(barra);

  const escena = document.getElementById('escena') ?? document.body;
  const fundido = crear('div', { clase: 'vm-fundido', 'aria-hidden': 'true' });
  const titulo = crear('p', { clase: 'vm-titulo', 'aria-hidden': 'true' }, crear('b', { texto: 'V8 350' }), ' en el soporte');
  escena.append(fundido, titulo);

  return { botonMotor, barra, titulo, volver, girar, centrar, botonPaso, separar, cajaSeparar, pasoAnterior, pasoTexto, pasoSiguiente, cajaPaso, ranura, estado, fundido };
}
