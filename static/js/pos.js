/**
 * Boutique Euler - Módulo del Punto de Venta (POS)
 */

let cart = [];
let activeCategory = 'TODAS';

// Agregar prenda al carrito
function addToCart(prenda) {
  if (prenda.stock <= 0) {
    showToast(`"${prenda.nombre}" no tiene stock disponible`, 'warning');
    return;
  }

  const existing = cart.find(item => item.prenda_id === prenda.id);
  if (existing) {
    if (existing.cantidad + 1 > prenda.stock) {
      showToast(`Stock máximo alcanzado (${prenda.stock} disponibles)`, 'warning');
      return;
    }
    existing.cantidad += 1;
  } else {
    cart.push({
      prenda_id: prenda.id,
      codigo: prenda.codigo,
      nombre: prenda.nombre,
      talla: prenda.talla,
      color: prenda.color,
      precio_usd: prenda.precio_venta,
      stock_max: prenda.stock,
      cantidad: 1
    });
  }

  renderCart();
  showToast(`"${prenda.nombre}" agregada al carrito`, 'success');
}

// Modificar cantidad en carrito
function changeQty(index, delta) {
  const item = cart[index];
  if (!item) return;

  const newQty = item.cantidad + delta;
  if (newQty <= 0) {
    cart.splice(index, 1);
  } else if (newQty > item.stock_max) {
    showToast(`Solo hay ${item.stock_max} unidades disponibles`, 'warning');
    return;
  } else {
    item.cantidad = newQty;
  }

  renderCart();
}

// Vaciar carrito
function clearCart() {
  if (cart.length === 0) return;
  if (confirm('¿Desea limpiar el carrito de venta?')) {
    cart = [];
    renderCart();
  }
}

// Renderizar carrito y recalcular totales
function renderCart() {
  const container = document.getElementById('pos-cart-items');
  const countBadge = document.getElementById('pos-cart-count');
  const emptyState = document.getElementById('pos-empty-state');
  const checkoutBtn = document.getElementById('btn-procesar-venta');

  if (!container) return;

  const totalPiezas = cart.reduce((sum, item) => sum + item.cantidad, 0);
  if (countBadge) countBadge.textContent = `${totalPiezas} piezas`;

  if (cart.length === 0) {
    container.innerHTML = `
      <div id="pos-empty-state" style="text-align:center; padding: 3rem 1rem; color: var(--text-muted);">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem; opacity: 0.5;">🛍️</div>
        <p style="font-size: 0.95rem;">El carrito está vacío</p>
        <p style="font-size: 0.78rem;">Seleccione prendas del catálogo para cobrar</p>
      </div>
    `;
    if (checkoutBtn) checkoutBtn.disabled = true;
    updateTotals(0);
    return;
  }

  if (checkoutBtn) checkoutBtn.disabled = false;

  let totalUsd = 0;
  container.innerHTML = cart.map((item, idx) => {
    const subUsd = item.cantidad * item.precio_usd;
    const subBs = subUsd * CURRENT_TASA;
    totalUsd += subUsd;

    return `
      <div class="cart-item">
        <div class="cart-item-info">
          <div class="cart-item-title">${item.nombre}</div>
          <div class="cart-item-sub">${item.codigo} | Talla: <strong>${item.talla}</strong> | ${item.color}</div>
        </div>
        <div class="cart-item-qty">
          <button class="btn btn-secondary btn-sm" onclick="changeQty(${idx}, -1)" title="Disminuir">-</button>
          <span style="font-weight: bold; min-width: 20px; text-align: center;">${item.cantidad}</span>
          <button class="btn btn-secondary btn-sm" onclick="changeQty(${idx}, 1)" title="Aumentar">+</button>
        </div>
        <div class="cart-item-price">
          <div class="p-usd">$${subUsd.toFixed(2)}</div>
          <div class="p-bs">${subBs.toFixed(2)} Bs</div>
        </div>
        <button class="btn btn-icon-only btn-rose btn-sm" onclick="changeQty(${idx}, -9999)" title="Quitar">✕</button>
      </div>
    `;
  }).join('');

  updateTotals(totalUsd);
}

function updateTotals(totalUsd) {
  const totalBs = totalUsd * CURRENT_TASA;
  const totalPiezas = cart.reduce((sum, item) => sum + item.cantidad, 0);
  
  const elUsd = document.getElementById('pos-total-usd');
  const elBs = document.getElementById('pos-total-bs');
  
  if (elUsd) elUsd.textContent = `$${totalUsd.toFixed(2)}`;
  if (elBs) elBs.textContent = `${totalBs.toFixed(2)} Bs.`;

  // Actualizar barra flotante móvil (solo en pantallas móviles <= 768px)
  const mobileBar = document.getElementById('mobile-cart-float-bar');
  const mobileCount = document.getElementById('mobile-cart-items-count');
  const mobileUsd = document.getElementById('mobile-cart-total-usd');
  const mobileBs = document.getElementById('mobile-cart-total-bs');

  if (mobileBar) {
    const esMovil = window.innerWidth <= 768;
    if (totalPiezas > 0 && esMovil) {
      mobileBar.style.display = 'flex';
      if (mobileCount) mobileCount.textContent = `${totalPiezas} pieza${totalPiezas > 1 ? 's' : ''}`;
      if (mobileUsd) mobileUsd.textContent = `$${totalUsd.toFixed(2)}`;
      if (mobileBs) mobileBs.textContent = `(${totalBs.toFixed(2)} Bs.)`;
    } else {
      mobileBar.style.display = 'none';
    }
  }
}

// Control del Carrito en dispositivos móviles (Bottom Drawer / Modal)
function mostrarCarritoMovil() {
  const panel = document.getElementById('pos-cart-panel');
  const backdrop = document.getElementById('pos-cart-backdrop');
  if (panel) {
    panel.classList.add('mobile-open');
    if (backdrop) backdrop.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function cerrarCarritoMovil() {
  const panel = document.getElementById('pos-cart-panel');
  const backdrop = document.getElementById('pos-cart-backdrop');
  if (panel) {
    panel.classList.remove('mobile-open');
    if (backdrop) backdrop.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// Filtrar catálogo por categoría y búsqueda
function filterPosCatalog() {
  const searchTerm = (document.getElementById('pos-search-input')?.value || '').toLowerCase().trim();
  const cards = document.querySelectorAll('.pos-card');

  cards.forEach(card => {
    const name = (card.dataset.nombre || '').toLowerCase();
    const code = (card.dataset.codigo || '').toLowerCase();
    const color = (card.dataset.color || '').toLowerCase();
    const category = card.dataset.categoria || '';

    const matchCategory = (activeCategory === 'TODAS' || category === activeCategory);
    const matchSearch = (!searchTerm || name.includes(searchTerm) || code.includes(searchTerm) || color.includes(searchTerm));

    if (matchCategory && matchSearch) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });
}

function setPosCategory(cat, btn) {
  activeCategory = cat;
  document.querySelectorAll('.cat-pill').forEach(el => el.classList.remove('active'));
  if (btn) btn.classList.add('active');
  filterPosCatalog();
}

// Abrir modal de cobro final
function abrirModalCobro() {
  if (cart.length === 0) {
    showToast('El carrito está vacío', 'warning');
    return;
  }

  cerrarCarritoMovil();

  const totalUsd = cart.reduce((sum, item) => sum + (item.cantidad * item.precio_usd), 0);
  const totalBs = totalUsd * CURRENT_TASA;

  document.getElementById('checkout-modal-usd').textContent = `$${totalUsd.toFixed(2)}`;
  document.getElementById('checkout-modal-bs').textContent = `${totalBs.toFixed(2)} Bs.`;
  document.getElementById('checkout-modal-tasa').textContent = `${CURRENT_TASA.toFixed(2)} Bs/$`;

  openModal('modal-checkout');
}

// Procesar Venta en el servidor
async function procesarVentaSubmit(e) {
  e.preventDefault();
  if (cart.length === 0) return;

  const btn = document.getElementById('btn-confirmar-cobro');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Procesando...';
  }

  const totalUsd = cart.reduce((sum, item) => sum + (item.cantidad * item.precio_usd), 0);
  const clienteNombre = document.getElementById('checkout-cliente-nombre')?.value.trim() || 'Cliente General';
  const clienteTelefono = document.getElementById('checkout-cliente-telefono')?.value.trim() || '';
  const metodoPago = document.getElementById('checkout-metodo-pago')?.value || 'Efectivo Divisas ($)';
  const notas = document.getElementById('checkout-notas')?.value.trim() || '';

  const payload = {
    total_usd: totalUsd,
    cliente_nombre: clienteNombre,
    cliente_telefono: clienteTelefono,
    metodo_pago: metodoPago,
    notas: notas,
    items: cart
  };

  try {
    const res = await fetch('/api/ventas/crear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (data.success) {
      closeModal('modal-checkout');
      mostrarTicketRecibo(data.resultado, payload);
      cart = [];
      renderCart();
      showToast(`¡Venta procesada con éxito! Recibo ${data.resultado.numero_recibo}`, 'success');
    } else {
      showToast(data.message || 'Error al procesar la venta', 'error');
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Confirmar y Cobrar';
      }
    }
  } catch (err) {
    showToast('Error de red al procesar venta', 'error');
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Confirmar y Cobrar';
    }
  }
}

// Mostrar Ticket en Modal
function mostrarTicketRecibo(resultado, payload) {
  document.getElementById('ticket-recibo-nro').textContent = resultado.numero_recibo;
  document.getElementById('ticket-fecha').textContent = resultado.fecha;
  document.getElementById('ticket-cliente').textContent = payload.cliente_nombre;
  document.getElementById('ticket-metodo').textContent = payload.metodo_pago;
  document.getElementById('ticket-tasa').textContent = `${resultado.tasa.toFixed(2)} Bs/$`;

  const itemsTable = document.getElementById('ticket-items-tbody');
  itemsTable.innerHTML = payload.items.map(it => `
    <tr>
      <td>${it.nombre} (${it.talla})</td>
      <td style="text-align:center;">${it.cantidad}</td>
      <td style="text-align:right;">$${(it.cantidad * it.precio_usd).toFixed(2)}</td>
    </tr>
  `).join('');

  document.getElementById('ticket-total-usd').textContent = `$${resultado.total_usd.toFixed(2)}`;
  document.getElementById('ticket-total-bs').textContent = `${resultado.total_bs.toFixed(2)} Bs.`;

  openModal('modal-ticket');
}

function imprimirTicket() {
  window.print();
}
