/* ============================================================
   admin.js — Logique admin dynamique (Supabase + Cloudinary)
   Chargé APRÈS le script inline — les fonctions ici écrasent
   celles définies dans le HTML.
   ============================================================ */

/* ── Supabase client ── */
const { createClient } = supabase;
const db = createClient(CONFIG.supabase.url, CONFIG.supabase.anonKey);

async function bootstrapSupabaseSessionFromUrl() {
  try {
    const params = new URLSearchParams((location.hash || '').replace(/^#/, ''));
    const qp = new URLSearchParams(location.search || '');

    const access_token =
      params.get('access_token') ||
      params.get('sb-access-token') ||
      qp.get('access_token') ||
      qp.get('sb-access-token');

    const refresh_token =
      params.get('refresh_token') ||
      params.get('sb-refresh-token') ||
      qp.get('refresh_token') ||
      qp.get('sb-refresh-token');

    if (access_token && refresh_token) {
      await db.auth.setSession({ access_token, refresh_token });
    }
  } catch (_) {
  }
}

/* ── Photo tracking (parallèle à formPhotos) ── */
let formPhotoData = [];

/* ══════════════════════════════════════
   AUTH CHECK
══════════════════════════════════════ */
(async () => {
  try {
    await bootstrapSupabaseSessionFromUrl();
    await db.auth.getSession();
  } catch (_) {
  }
})();

/* ══════════════════════════════════════
   CLOUDINARY UPLOAD
══════════════════════════════════════ */
async function uploadToCloudinary(file) {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('upload_preset', CONFIG.cloudinary.uploadPreset);
  fd.append('folder', 'products');
  const res = await fetch(
    `https://api.cloudinary.com/v1_1/${CONFIG.cloudinary.cloudName}/image/upload`,
    { method: 'POST', body: fd }
  );
  if (!res.ok) throw new Error('Cloudinary upload échoué');
  const data = await res.json();
  return data.secure_url;
}

/* ══════════════════════════════════════
   MAPPING DB → FORMAT HTML
══════════════════════════════════════ */
function mapProduct(row) {
  return {
    id:       row.id,
    name:     row.name,
    desc:     row.description || '',
    price:    row.price,
    promo:    row.promo_price || null,
    cat:      row.category,
    emoji:    row.emoji || '📦',
    avail:    row.available !== false,
    isNew:    row.is_new || false,
    qty:      row.qty || '',
    unit:     row.unit || 'Unité',
    photos:   row.photos || [],
    variants: (row.variants || []).map(v => ({ t: v.t ?? v.type ?? '', v: v.v ?? v.value ?? '' })),
    tiers:    (row.tiers || []).map(t => ({ min: t.min ?? t.min_qty ?? 0, price: t.price ?? 0 })),
  };
}

/* ══════════════════════════════════════
   PHOTOS — override handleFiles + removePhoto
══════════════════════════════════════ */
function handleFiles(input) {
  const files = Array.from(input.files || []).slice(0, 3 - formPhotos.length);
  if (!files.length) return;
  let pending = files.length;
  files.forEach(f => {
    const r = new FileReader();
    r.onload = ev => {
      formPhotos.push(ev.target.result);
      formPhotoData.push({ type: 'file', file: f, preview: ev.target.result });
      if (--pending === 0) renderPhotos();
    };
    r.readAsDataURL(f);
  });
  input.value = '';
}

function removePhoto(i) {
  formPhotos.splice(i, 1);
  formPhotoData.splice(i, 1);
  renderPhotos();
}

/* ══════════════════════════════════════
   RENDERGRILLE — async (charge depuis Supabase)
══════════════════════════════════════ */
async function renderGrid() {
  const grid = document.getElementById('grid');
  grid.innerHTML = '<div class="empty-adm"><div class="e-ico">⏳</div><div class="e-title">Chargement…</div></div>';

  const { data, error } = await db
    .from('products')
    .select('*')
    .order('created_at', { ascending: false });

  if (error) {
    grid.innerHTML = '<div class="empty-adm"><div class="e-ico">⚠️</div><div class="e-title">Erreur de chargement</div><div class="e-sub">' + error.message + '</div></div>';
    toast('Erreur chargement catalogue', 'rm');
    return;
  }

  products = data.map(mapProduct);
  buildTicker();

  let list = products.filter(p => {
    if (activeCat !== 'all' && p.cat !== activeCat) return false;
    if (searchQ && !p.name.toLowerCase().includes(searchQ) && !p.cat.toLowerCase().includes(searchQ)) return false;
    return true;
  });

  if (!list.length) {
    grid.innerHTML = `<div class="empty-adm">
      <div class="e-ico">📦</div>
      <div class="e-title">${products.length === 0 ? 'Catalogue vide' : 'Aucun résultat'}</div>
      <div class="e-sub">${products.length === 0 ? 'Appuyez sur Nouveau pour commencer' : 'Essayez une autre recherche'}</div>
    </div>`;
    return;
  }

  grid.innerHTML = list.map((p, i) => {
    const price    = p.promo && p.promo < p.price ? p.promo : p.price;
    const hasPromo = p.promo && p.promo < p.price;

    const badge = !p.avail
      ? '<div class="pbadge oos">Rupture</div>'
      : hasPromo ? `<div class="pbadge promo">−${pct(p.price, p.promo)}%</div>`
      : p.isNew  ? '<div class="pbadge new">Nouveau</div>' : '';

    const chips = [];
    if (p.qty) chips.push(`<span class="ichip c">${p.qty} ${p.unit}</span>`);
    if (p.tiers && p.tiers.length) chips.push(`<span class="ichip o">${p.tiers.length} palier${p.tiers.length > 1 ? 's' : ''}</span>`);
    const chipHtml = chips.length ? `<div class="img-chips">${chips.join('')}</div>` : '';

    const mainImg = p.photos && p.photos.length
      ? `<img src="${p.photos[0]}" alt="${p.name}" loading="lazy" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;"/>`
      : `<div class="acard-emoji">${p.emoji}</div>`;

    const varTypes = [...new Set((p.variants || []).map(v => v.t))];

    return `<div class="acard${p.avail ? '' : ' oos'}" style="animation-delay:${i % 6 * 0.04}s">
      <div class="acard-img">
        ${mainImg}
        ${badge}${chipHtml}
      </div>
      <div class="acard-info">
        <div class="acard-name">${p.name}</div>
        <div class="acard-price">
          <span class="ap-main">${fmt(price)}</span>
          ${hasPromo ? `<span class="ap-old">${fmt(p.price)}</span>` : ''}
        </div>
        <div class="acard-meta">${p.cat}${varTypes.length ? ' · ' + varTypes.join(', ') : ''}</div>
      </div>
      <div class="acard-acts">
        <button class="abtn edit" onclick="openForm('${p.id}')">Modifier</button>
        <button class="abtn tog ${p.avail ? 'pause' : 'play'}" onclick="toggleAvail('${p.id}')" title="${p.avail ? 'Mettre en rupture' : 'Remettre en vente'}">
          ${p.avail
            ? '<svg viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16" fill="currentColor"/><rect x="14" y="4" width="4" height="16" fill="currentColor"/></svg>'
            : '<svg viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21" fill="currentColor"/></svg>'}
        </button>
        <button class="abtn del" onclick="askDel('${p.id}')" title="Supprimer">
          <svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/></svg>
        </button>
      </div>
    </div>`;
  }).join('');
}

/* ══════════════════════════════════════
   OPEN FORM — override pour photos Cloudinary + UUID
══════════════════════════════════════ */
function openForm(id = null) {
  editId = id;
  const p = id ? products.find(x => x.id === id) : null;

  document.getElementById('sh-title').textContent = p ? 'Modifier le produit' : 'Nouveau produit';
  document.getElementById('save-lbl').textContent  = p ? 'Enregistrer' : 'Publier';
  document.getElementById('save-ico').innerHTML    = p
    ? '<polyline points="20 6 9 17 4 12"/>'
    : '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>';

  document.getElementById('f-name').value  = p?.name  ?? '';
  document.getElementById('f-desc').value  = p?.desc  ?? '';
  document.getElementById('f-price').value = p?.price ?? '';
  document.getElementById('f-promo').value = p?.promo ?? '';
  document.getElementById('f-qty').value   = p?.qty   ?? '';
  document.getElementById('f-unit').value  = p?.unit  ?? 'Unité';
  document.getElementById('f-cat').value   = p?.cat   ?? '';

  const existingPhotos = p?.photos || [];
  formPhotos    = [...existingPhotos];
  formPhotoData = existingPhotos.map(url => ({ type: 'url', file: null, preview: url }));

  formVars  = p ? [...(p.variants || [])] : [];
  formTiers = p ? [...(p.tiers    || [])] : [];
  wsOn      = formTiers.length > 0;

  renderPhotos();
  renderVars();

  const togWS    = document.getElementById('tog-ws');
  const tiersWrap = document.getElementById('tiers-wrap');
  togWS.classList.toggle('on', wsOn);
  tiersWrap.style.display = wsOn ? 'block' : 'none';
  renderTiers();

  updateSubcat();
  updateFmtPrev();
  updatePromoPrev();
  validate();

  document.getElementById('sheet').classList.add('open');
  document.querySelector('.sh-body').scrollTop = 0;
  document.body.style.overflow = 'hidden';
}

/* ══════════════════════════════════════
   ASK DEL — override pour UUID
══════════════════════════════════════ */
function askDel(id) {
  const p = products.find(x => x.id === id); if (!p) return;
  delId = id;
  document.getElementById('cfm-name').textContent = '"' + p.name + '"';
  document.getElementById('confirm').classList.add('open');
}

/* ══════════════════════════════════════
   TOGGLE DISPONIBILITÉ — async
══════════════════════════════════════ */
async function toggleAvail(id) {
  const p = products.find(x => x.id === id); if (!p) return;
  const { error } = await db.from('products').update({ available: !p.avail }).eq('id', id);
  if (error) { toast('Erreur mise à jour', 'rm'); return; }
  await renderGrid();
  const updated = products.find(x => x.id === id);
  if (updated) toast(
    updated.avail
      ? `✅ "${updated.name.slice(0, 22)}" remis en vente`
      : `⏸ "${updated.name.slice(0, 22)}" en rupture`,
    updated.avail ? 'ok' : 'rm'
  );
}

/* ══════════════════════════════════════
   SUPPRESSION — async
══════════════════════════════════════ */
async function doDel() {
  const p = products.find(x => x.id === delId);
  const { error } = await db.from('products').delete().eq('id', delId);
  if (error) { toast('Erreur suppression : ' + error.message, 'rm'); return; }
  document.getElementById('confirm').classList.remove('open');
  delId = null;
  await renderGrid();
  toast(`🗑 "${p?.name?.slice(0, 22)}" supprimé`, 'rm');
}

/* ══════════════════════════════════════
   SAUVEGARDE — async avec upload Cloudinary
══════════════════════════════════════ */
async function saveProduct() {
  if (!validate()) return;

  const btn   = document.getElementById('btn-save');
  const label = document.getElementById('save-lbl');
  btn.classList.add('dis');
  label.textContent = 'Enregistrement…';

  try {
    /* 1. Upload photos nouvelles → Cloudinary */
    const finalUrls = [];
    for (const ph of formPhotoData) {
      if (ph.type === 'url') {
        finalUrls.push(ph.preview);
      } else {
        const url = await uploadToCloudinary(ph.file);
        finalUrls.push(url);
      }
    }

    /* 2. Lire les champs du formulaire */
    const name     = document.getElementById('f-name').value.trim();
    const desc     = document.getElementById('f-desc').value.trim();
    const price    = Number(document.getElementById('f-price').value.replace(/\D/g, ''));
    const promoRaw = Number(document.getElementById('f-promo').value.replace(/\D/g, '')) || null;
    const promo_price = promoRaw && promoRaw < price ? promoRaw : null;
    const category = document.getElementById('f-cat').value;
    const unit     = document.getElementById('f-unit').value;
    const qty      = document.getElementById('f-qty').value.trim();

    const payload = {
      name,
      description:  desc,
      price,
      promo_price,
      category,
      unit,
      qty,
      photos:   finalUrls,
      variants: formVars,
      tiers:    wsOn ? formTiers : [],
      updated_at: new Date().toISOString(),
    };

    /* 3. INSERT ou UPDATE */
    if (editId) {
      const { error } = await db.from('products').update(payload).eq('id', editId);
      if (error) throw error;
      toast(`✅ "${name.slice(0, 22)}" modifié`);
    } else {
      const emojis = ['📦', '🛍️', '🏷️', '✨', '🎁'];
      payload.emoji     = emojis[Math.floor(Math.random() * emojis.length)];
      payload.available = true;
      payload.is_new    = true;
      const { error } = await db.from('products').insert(payload);
      if (error) throw error;
      toast(`✅ "${name.slice(0, 22)}" publié`);
    }

    closeForm();
    await renderGrid();

  } catch (e) {
    console.error('[saveProduct]', e);
    toast('Erreur : ' + (e.message || 'inconnue'), 'rm');
    btn.classList.remove('dis');
    label.textContent = editId ? 'Enregistrer' : 'Publier';
  }
}

/* ══════════════════════════════════════
   REALTIME — écoute les changements produits
══════════════════════════════════════ */
db.channel('products-admin-rt')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'products' }, () => {
    renderGrid();
  })
  .subscribe();

/* ══════════════════════════════════════
   INIT — remplace le renderGrid() synchrone du HTML
══════════════════════════════════════ */
renderGrid();
buildCats();
