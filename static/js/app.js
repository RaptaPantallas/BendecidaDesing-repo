/**
 * Boutique Euler - JavaScript Principal
 */

// Toast Notifications
function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  let icon = '✓';
  if (type === 'error') icon = '✕';
  if (type === 'warning') icon = '⚠';

  toast.innerHTML = `
    <span style="font-weight: bold; font-size: 1.1rem;">${icon}</span>
    <span>${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Modales
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// Cerrar modal al hacer clic en el backdrop
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
    document.body.style.overflow = '';
  }
});

// Modal de Actualización de Tasa
function abrirModalTasa() {
  openModal('modal-tasa-cambio');
  setTimeout(() => {
    const input = document.getElementById('input-nueva-tasa');
    if (input) {
      input.focus();
      input.select();
    }
  }, 100);
}

async function guardarNuevaTasa(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('input-nueva-tasa');
  const nuevaTasa = parseFloat(input.value);

  if (isNaN(nuevaTasa) || nuevaTasa <= 0) {
    showToast('Por favor ingrese una tasa válida mayor a 0', 'error');
    return;
  }

  try {
    const res = await fetch('/api/tasa/actualizar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tasa: nuevaTasa })
    });

    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      closeModal('modal-tasa-cambio');
      // Actualizar el valor en el pill del navbar
      const pillVal = document.getElementById('navbar-tasa-val');
      if (pillVal) pillVal.textContent = `${nuevaTasa.toFixed(2)} Bs/$`;

      // Si estamos en inventario o POS, recargar para reflejar precios en Bs
      setTimeout(() => window.location.reload(), 600);
    } else {
      showToast(data.message || 'Error al actualizar la tasa', 'error');
    }
  } catch (err) {
    showToast('Error de conexión al servidor', 'error');
  }
}

// Ajuste rápido de stock (+ / -) desde la tabla de inventario
async function ajustarStockRapido(prendaId, delta) {
  try {
    const res = await fetch(`/api/prendas/${prendaId}/stock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delta: delta })
    });
    const data = await res.json();
    if (data.success) {
      const stockEl = document.getElementById(`stock-val-${prendaId}`);
      if (stockEl) {
        stockEl.textContent = data.nuevo_stock;
        
        // Actualizar estilo si quedó en stock crítico
        const row = document.getElementById(`prenda-row-${prendaId}`);
        const stockMin = parseInt(row?.dataset.stockMinimo || '0');
        if (row) {
          if (data.nuevo_stock <= 0) {
            row.className = 'table-row-danger';
          } else if (data.nuevo_stock <= stockMin) {
            row.className = 'table-row-warning';
          } else {
            row.className = '';
          }
        }
      }
      showToast(`Stock actualizado a ${data.nuevo_stock}`, 'success');
    } else {
      showToast(data.message || 'Error al actualizar el stock', 'error');
    }
  } catch (err) {
    showToast('Error de red al actualizar stock', 'error');
  }
}

// Eliminar / Desactivar prenda
async function confirmarEliminarPrenda(prendaId, nombre) {
  if (!confirm(`¿Está seguro de eliminar o retirar la prenda "${nombre}"?`)) return;

  try {
    const res = await fetch(`/api/prendas/${prendaId}/eliminar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      const row = document.getElementById(`prenda-row-${prendaId}`);
      if (row) row.remove();
    } else {
      showToast(data.message || 'Error al eliminar', 'error');
    }
  } catch (err) {
    showToast('Error al procesar la solicitud', 'error');
  }
}

// Sincronización Automática con la Tasa Oficial del BCV
async function sincronizarTasaBCV() {
  const btn = document.getElementById('btn-sync-bcv');
  const infoEl = document.getElementById('modal-bcv-fecha-info');
  const inputTasa = document.getElementById('input-nueva-tasa');

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '⏳ Consultando...';
  }

  showToast('Consultando tasa oficial del BCV...', 'warning');

  try {
    // Intentar primero a través del backend
    let nuevaTasa = 0;
    let fechaStr = '';

    try {
      const res = await fetch('/api/tasa/sincronizar_bcv', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        nuevaTasa = data.nueva_tasa;
        fechaStr = data.fecha_bcv;
      }
    } catch (backendErr) {
      console.warn('Backend proxy no disponible, intentando directo desde navegador...', backendErr);
    }

    // Fallback: si el backend no pudo (ej. proxy PythonAnywhere free), consultar directamente desde el navegador
    if (!nuevaTasa) {
      const resDirect = await fetch('https://ve.dolarapi.com/v1/dolares/oficial');
      const directData = await resDirect.json();
      if (directData && directData.promedio) {
        nuevaTasa = parseFloat(directData.promedio);
        fechaStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Guardar en el backend
        await fetch('/api/tasa/actualizar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tasa: nuevaTasa })
        });
      }
    }

    if (nuevaTasa > 0) {
      if (inputTasa) inputTasa.value = nuevaTasa.toFixed(2);
      if (infoEl) infoEl.textContent = `Oficial BCV: ${nuevaTasa.toFixed(2)} Bs/$ (Sincronizado ahora)`;
      
      const pillVal = document.getElementById('navbar-tasa-val');
      if (pillVal) pillVal.textContent = `${nuevaTasa.toFixed(2)} Bs/$`;

      showToast(`¡Tasa BCV actualizada a ${nuevaTasa.toFixed(2)} Bs/$!`, 'success');
      setTimeout(() => window.location.reload(), 900);
    } else {
      showToast('No se pudo obtener la tasa del BCV en este momento', 'error');
    }
  } catch (err) {
    showToast('Error de conexión con la API del BCV', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '🔄 Sincronizar BCV';
    }
  }
}

// Previsualización de imagen al seleccionarla
function previewPrendaImagen(input) {
  const previewBox = document.getElementById('image-preview-container');
  const previewImg = document.getElementById('image-preview-element');
  const placeholder = document.getElementById('image-upload-placeholder');

  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function(e) {
      if (previewImg) previewImg.src = e.target.result;
      if (previewBox) previewBox.style.display = 'block';
      if (placeholder) placeholder.style.display = 'none';
    };
    reader.readAsDataURL(input.files[0]);
  }
}

// Guardar nueva prenda o edición (Soporta imágenes vía FormData)
async function submitPrendaForm(e) {
  e.preventDefault();
  const form = e.target;
  const formData = new FormData(form);

  const btnSubmit = document.getElementById('btn-submit-prenda');
  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.textContent = 'Guardando...';
  }

  const prendaId = form.dataset.editId;
  const url = prendaId ? `/api/prendas/${prendaId}/editar` : '/api/prendas/crear';

  try {
    const res = await fetch(url, {
      method: 'POST',
      body: formData // Envía Multipart automáticamente con la foto
    });
    const resp = await res.json();
    if (resp.success) {
      showToast(resp.message, 'success');
      closeModal('modal-prenda');
      setTimeout(() => window.location.reload(), 500);
    } else {
      showToast(resp.message || 'Error al guardar la prenda', 'error');
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.textContent = 'Guardar Prenda';
      }
    }
  } catch (err) {
    showToast('Error al conectar con el servidor', 'error');
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.textContent = 'Guardar Prenda';
    }
  }
}

// Anular venta desde la vista de ventas
async function anularVenta(ventaId, numeroRecibo) {
  if (!confirm(`¿Está seguro de ANULAR la venta ${numeroRecibo}? Las prendas serán devueltas al inventario.`)) return;

  try {
    const res = await fetch(`/api/ventas/${ventaId}/anular`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      setTimeout(() => window.location.reload(), 600);
    } else {
      showToast(data.message || 'Error al anular venta', 'error');
    }
  } catch (err) {
    showToast('Error al comunicarse con el servidor', 'error');
  }
}

// Ver detalle de venta en modal
async function verDetalleVenta(ventaId) {
  try {
    const res = await fetch(`/api/ventas/${ventaId}`);
    const data = await res.json();
    if (!data.success) {
      showToast('No se pudo cargar el detalle', 'error');
      return;
    }

    const v = data.datos.venta;
    const items = data.datos.detalles;

    document.getElementById('modal-recibo-numero').textContent = v.numero_recibo;
    document.getElementById('modal-recibo-fecha').textContent = v.fecha;
    document.getElementById('modal-recibo-cliente').textContent = v.cliente_nombre;
    document.getElementById('modal-recibo-metodo').textContent = v.metodo_pago;
    document.getElementById('modal-recibo-tasa').textContent = `${v.tasa_momento.toFixed(2)} Bs/$`;
    document.getElementById('modal-recibo-total-usd').textContent = `$${v.total_usd.toFixed(2)}`;
    document.getElementById('modal-recibo-total-bs').textContent = `${v.total_bs.toFixed(2)} Bs.`;

    const itemsContainer = document.getElementById('modal-recibo-items');
    itemsContainer.innerHTML = items.map(item => `
      <tr>
        <td><strong>${item.nombre}</strong><br><small style="color:var(--text-muted);">${item.codigo} | Talla: ${item.talla} | ${item.color}</small></td>
        <td style="text-align:center;">${item.cantidad}</td>
        <td style="text-align:right;">$${item.precio_unitario_usd.toFixed(2)}<br><small style="color:var(--primary-light);">${item.precio_unitario_bs.toFixed(2)} Bs</small></td>
        <td style="text-align:right; font-weight:bold;">$${item.subtotal_usd.toFixed(2)}<br><small style="color:var(--primary-light);">${item.subtotal_bs.toFixed(2)} Bs</small></td>
      </tr>
    `).join('');

    openModal('modal-detalle-venta');
  } catch (err) {
    showToast('Error al cargar la venta', 'error');
  }
}

// Eliminar venta definitivamente (para ventas anuladas)
async function eliminarVentaDefinitiva(ventaId, numeroRecibo) {
  if (!confirm(`¿Está completamente seguro de ELIMINAR DEFINITIVAMENTE la venta anulada ${numeroRecibo}? Esta acción no se puede deshacer y borrará todo rastro del historial.`)) return;

  try {
    const res = await fetch(`/api/ventas/${ventaId}/eliminar_definitiva`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      setTimeout(() => window.location.reload(), 600);
    } else {
      showToast(data.message || 'Error al eliminar', 'error');
    }
  } catch (err) {
    showToast('Error al procesar la solicitud', 'error');
  }
}

// Purgar todas las ventas anuladas del sistema
async function purgarTodasVentasAnuladas() {
  if (!confirm('¿Desea BORRAR DEFINITIVAMENTE TODAS las ventas anuladas? El historial quedará purgado únicamente con las ventas reales y válidas.')) return;

  try {
    const res = await fetch('/api/ventas/purgar_anuladas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      setTimeout(() => {
        window.location.href = '/ventas';
      }, 700);
    } else {
      showToast(data.message || 'Error al purgar', 'error');
    }
  } catch (err) {
    showToast('Error al conectar con el servidor', 'error');
  }
}

