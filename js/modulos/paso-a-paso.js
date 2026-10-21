/*
  Paso a paso: el Camaro se arma de a una pieza.
    1. El motor, en su lugar y sin la carrocería alrededor: del bloque al filtro de aire.
    2. Baja la carrocería sobre el motor y llegan las ruedas, el radiador y la batería.
    3. La chapa que se abre, los vidrios y, al final, los detalles de adelante y de atrás.
  Cada pieza llega volando desde donde queda cuando se separa, se marca en naranja y abre su ficha.
  Para atrás, la última pieza se va por donde vino.
*/

import { obtenerMovimiento, encuadrarEsfera } from './movimiento.js';

const ORDEN = [
  // 1. El motor
  'bloque', 'tapas-cilindros', 'carter', 'multiple-admision', 'tapas-valvulas', 'multiples-escape',
  'bomba-agua', 'motor-arranque', 'distribuidor', 'bobina', 'cables-bujias', 'alternador',
  'correas', 'ventilador', 'carburador', 'filtro-aire',
  // 2. La carrocería y lo que se atornilla a ella
  'carroceria', 'llantas-rally', 'radiador', 'bateria',
  // 3. Chapa, vidrios y detalles
  'puertas', 'vidrios', 'espejo', 'capot', 'tapa-baul',
  'parrilla', 'faros', 'luces-posicion', 'paragolpes-delantero',
  'paragolpes-trasero', 'luces-traseras', 'tapa-nafta', 'emblemas-ss',
];

const FASES = [
  { hasta: 'filtro-aire', nombre: 'El motor' },
  { hasta: 'bateria', nombre: 'La carrocería' },
  { hasta: null, nombre: 'Los detalles' },
];

export function iniciar(api) {
  const { THREE } = api;
  const movimiento = obtenerMovimiento(api);
  let pasos = [];
  let actual = -1;
  let adentro = false;

  // Lo que diga ORDEN, y al final cualquier pieza nueva que tenga modelo y no esté en la lista.
  const armarPasos = () => {
    const conModelo = (id) => movimiento.tieneModelo(id);
    const lista = ORDEN.filter(conModelo);
    for (const id of api.orden) if (conModelo(id) && !lista.includes(id)) lista.push(id);
    return lista;
  };

  const faseDe = (indice) => {
    for (const fase of FASES) {
      const fin = fase.hasta ? pasos.indexOf(fase.hasta) : Infinity;
      if (fase.hasta === null || (fin !== -1 && indice <= fin)) return fase;
    }
    return FASES[FASES.length - 1];
  };

  const enMotor = (indice) => movimiento.esMotor(pasos[indice]) && faseDe(indice) === FASES[0];

  // El motor armado, medido al arrancar (todo en su lugar), para encuadrarlo en la fase del motor.
  const cajaMotor = new THREE.Box3();
  for (const [id, objeto] of api.piezas) if (movimiento.esMotor(id)) cajaMotor.expandByObject(objeto);

  // La sombra de contacto pintada en el piso es la del auto: sin carrocería, no va.
  const sombrasDelAuto = [];
  api.raiz.traverse((o) => { if (/sombra/i.test(o.name)) sombrasDelAuto.push(o); });
  const mostrarSombra = (visible) => { for (const o of sombrasDelAuto) o.visible = visible; api.pedirRender(); };

  function encuadrar(indice, anterior) {
    const ahora = enMotor(indice);
    mostrarSombra(!ahora);
    if (anterior !== undefined && ahora === enMotor(anterior)) return;
    if (ahora && !cajaMotor.isEmpty()) encuadrarEsfera(api, cajaMotor.getBoundingSphere(new THREE.Sphere()), { factor: 1.25 });
    else api.vistaInicial?.(true);
  }

  function llega(id) {
    movimiento.fijarPaso(id, 1);
    movimiento.mostrar(id, true);
    movimiento.animarPaso(id, 0, 0.8);
  }

  function seVa(id) {
    movimiento.animarPaso(id, 1, 0.55).then(() => {
      // Si mientras se iba volvieron a pedirla, se queda.
      if (adentro && pasos.indexOf(id) > actual) movimiento.mostrar(id, false);
    });
  }

  function ir(destino) {
    destino = Math.max(0, Math.min(destino, pasos.length - 1));
    const anterior = actual;
    if (destino === anterior) return;
    if (destino > anterior) for (let i = anterior + 1; i <= destino; i++) llega(pasos[i]);
    else for (let i = anterior; i > destino; i--) seVa(pasos[i]);
    actual = destino;
    encuadrar(actual, anterior < 0 ? undefined : anterior);
    const id = pasos[actual];
    const nombre = api.fichas.get(id)?.nombre ?? id;
    api.actualizarPaso({ actual: actual + 1, total: pasos.length, id, texto: `${faseDe(actual).nombre} · ${nombre}` });
  }

  return {
    entrar() {
      pasos = armarPasos();
      if (!pasos.length) {
        api.avisar('Todavía no hay piezas en el modelo para armar paso a paso.');
        return false;
      }
      adentro = true;
      for (const clave of ['capot', 'puertas', 'baul']) api.abrir?.(clave, false);
      movimiento.reiniciarPropios();
      for (const id of pasos) { movimiento.fijarPaso(id, 1); movimiento.mostrar(id, false); }
      actual = -1;
      ir(0);
      return true;
    },
    salir() {
      adentro = false;
      for (const id of pasos) { movimiento.fijarPaso(id, 0); movimiento.mostrar(id, true); }
      mostrarSombra(true);
      actual = -1;
      api.vistaInicial?.(true);
    },
    siguiente() { if (adentro) ir(actual + 1); },
    anterior() { if (adentro) ir(actual - 1); },
  };
}
