/*
  Separar: las piezas se alejan de su lugar y vuelven.
    · La barra «Separar piezas» las abre todas: primero la carrocería (capot arriba, puertas a los
      costados, paragolpes adelante y atrás…) y después el motor, que sube y se desarma en el aire.
    · «Separar esta pieza» (en la ficha) saca solo esa y la vuelve a poner.
  Hacia dónde va cada una está en movimiento.js.
*/

import { obtenerMovimiento, encuadrarEsfera } from './movimiento.js';

export function iniciar(api) {
  const { THREE, raiz } = api;
  const movimiento = obtenerMovimiento(api);

  // Cuánto ocupa el auto todo separado (sin el piso), medido una vez al arrancar.
  const esPiso = (o) => /^(piso|suelo|estudio|floor)/i.test(o.name);
  movimiento.fijarGeneral(1);
  raiz.updateMatrixWorld(true);
  const cajaSeparado = new THREE.Box3();
  raiz.traverse((o) => {
    if (o.isMesh && !esPiso(o) && !(o.parent && esPiso(o.parent))) cajaSeparado.expandByObject(o);
  });
  movimiento.fijarGeneral(0);
  raiz.updateMatrixWorld(true);

  // Al entrar a Separar, la cámara se aleja (desde donde la dejaste) para que entre todo.
  api.on('modo', (modo) => {
    if (modo === 'separar' && !cajaSeparado.isEmpty()) {
      encuadrarEsfera(api, cajaSeparado.getBoundingSphere(new THREE.Sphere()), { factor: 0.82, bajar: 0.8 });
    }
    if (modo === 'paso') movimiento.reiniciarPropios();
  });

  return {
    fijar(valor) {
      movimiento.fijarGeneral(valor);
    },
    separarPieza(id) {
      if (!movimiento.tieneModelo(id)) return false;
      const afuera = movimiento.propio(id) < 0.5;
      // Una pieza del motor sale por arriba: si el capot está cerrado, primero se abre.
      if (afuera && movimiento.esMotor(id)) api.abrir?.('capot', true);
      // La cámara sigue a la pieza, así no se va de cuadro.
      movimiento.animarPropio(id, afuera ? 1 : 0, 0.85).then(() => {
        if (api.seleccionada() === id) api.enfocar?.(api.piezas.get(id));
      });
      return afuera;
    },
  };
}
