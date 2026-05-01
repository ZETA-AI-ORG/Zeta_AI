/* ============================================================
   catalogue.js — Logique publique dynamique (Supabase, read-only)
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

/* ── Produits chargés depuis Supabase ── */
let liveProducts = [];

/* ══════════════════════════════════════
   MAPPING DB → FORMAT HTML public
══════════════════════════════════════ */
function mapPublicProduct(row) {
  const hasPromo = row.promo_price && row.promo_price < row.price;

  const badge = !row.available
    ? null
    : hasPromo
      ? 'promo'
      : row.is_new ? 'new' : null;

  const displayPrice = hasPromo ? row.promo_price : row.price;
  const oldPrice     = hasPromo ? row.price : null;

  const sizes = (row.variants || [])
    .filter(v => ['Taille', 'Pointure', 'Size'].includes(v.t ?? v.type ?? ''))
    .map(v => v.v ?? v.value ?? '');

  const colorSwatches = (row.variants || [])
    .filter(v => (v.t ?? v.type ?? '') === 'Couleur')
    .map(v => v.v ?? v.value ?? '');

  const sub = row.qty
    ? `${row.qty} ${row.unit || ''}`.trim()
    : (row.description || '').slice(0, 50);

  const specs = (row.specs || []).map(s => ({
    k: s.k ?? s.key ?? '',
    v: s.v ?? s.value ?? '',
  }));

  return {
    id:      row.id,
    name:    row.name,
    sub:     sub || 'Produit',
    cat:     row.category,
    emoji:   row.emoji || '📦',
    price:   displayPrice,
    old:     oldPrice,
    badge,
    rat:     row.rating       ?? 4.5,
    rev:     row.review_count ?? 0,
    desc:    row.description  || '',
    tags:    row.tags         || [],
    sizes,
    swatches:   colorSwatches,
    specs,
    photos:     row.photos || [],
    available:  row.available !== false,
  };
}

/* ══════════════════════════════════════
   CHARGEMENT INITIAL
══════════════════════════════════════ */
async function loadProducts() {
  await bootstrapSupabaseSessionFromUrl();
  const { data, error } = await db
    .from('products')
    .select('*')
    .eq('available', true)
    .order('created_at', { ascending: false });

  if (error) {
    console.error('[catalogue] Erreur Supabase :', error.message);
    return;
  }

  liveProducts = data.map(mapPublicProduct);
  renderCats();
  renderGrid();
  updateHero();
  updateUI();
}

/* ══════════════════════════════════════
   GETVISIBLE — override pour liveProducts
══════════════════════════════════════ */
function getVisible() {
  const src = liveProducts.length ? liveProducts : PRODUCTS;
  let list = activeCat === 'all' ? [...src] : src.filter(p => p.cat === activeCat);
  if (query) list = list.filter(p =>
    p.name.toLowerCase().includes(query) ||
    p.sub.toLowerCase().includes(query)  ||
    p.desc.toLowerCase().includes(query)
  );
  return list.sort(SORTS[sortIdx].fn);
}

/* ══════════════════════════════════════
   UPDATEHERO — override pour liveProducts
══════════════════════════════════════ */
function updateHero() {
  const src = liveProducts.length ? liveProducts : PRODUCTS;
  const f   = src.find(p => p.badge === 'new') || src[0];
  if (!f) return;

  const heroImg = document.getElementById('hero-img');
  if (f.photos && f.photos.length) {
    heroImg.innerHTML = `<img src="${f.photos[0]}" alt="${f.name}" style="width:100%;height:100%;object-fit:cover;"/>`;
  } else {
    heroImg.textContent = f.emoji;
  }

  document.getElementById('hero-title').textContent = f.name;
  document.getElementById('hero-price').textContent = fmt(f.price);
  document.getElementById('hero-cover').onclick = () => openDetail(f.id);
}

/* ══════════════════════════════════════
   RENDERGRID — override avec UUIDs quotés + photos
══════════════════════════════════════ */
function renderGrid() {
  const list = getVisible();
  const rCount = document.getElementById('r-count');
  if (rCount) rCount.textContent = list.length + ' résultat' + (list.length > 1 ? 's' : '') + (query ? ' pour "' + query + '"' : '');

  const grid = document.getElementById('grid');
  if (!grid) return;

  if (!list.length) {
    grid.innerHTML = '<div class="empty-state"><div class="empty-ico">🔍</div><div class="empty-title">Aucun résultat</div><div class="empty-sub">Essayez un autre mot-clé</div><button class="empty-btn" onclick="clearSearch();setCat(\'all\')">Tout afficher</button></div>';
    return;
  }

  grid.innerHTML = list.map((p, i) => {
    const inCart   = cart.find(x => x.id === p.id)?.qty || 0;
    const isLiked  = liked.has(p.id);
    const bTxt     = p.badge === 'promo' ? '-' + pct(p.old, p.price) + '%'
                   : p.badge === 'new'   ? 'NOUVEAU'
                   : p.badge === 'hot'   ? 'TOP DEAL' : '';

    const imgBlock = p.photos && p.photos.length
      ? `<img src="${p.photos[0]}" alt="${p.name}" loading="lazy" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;"/>`
      : `<div class="pcard-emoji">${p.emoji}</div>`;

    const swHTML = p.swatches && p.swatches.length
      ? '<div class="pcard-swatches">' + p.swatches.map(c => `<div class="swatch" style="background:${c}"></div>`).join('') + '</div>'
      : '';

    return `<div class="pcard" style="animation-delay:${i % 8 * 0.04}s">
      <div class="pcard-img" onclick="openDetail('${p.id}')">
        ${imgBlock}
        ${p.badge ? `<div class="pbadge ${p.badge}">${bTxt}</div>` : ''}
        ${swHTML}
        <button class="pwish${isLiked ? ' on' : ''}" onclick="event.stopPropagation();toggleWishCard('${p.id}',this)">${isLiked ? '♥' : '♡'}</button>
      </div>
      <div class="pcard-body" onclick="openDetail('${p.id}')">
        <div class="pcard-stars">${stars(p.rat)}<span class="st-n">(${p.rev})</span></div>
        <div class="pcard-name">${hl(p.name, query)}</div>
        <div class="pcard-sub">${p.sub.split('·')[0].trim()}</div>
      </div>
      <div class="pcard-cta">
        <div class="price-block">
          <span class="price-main">${fmt(p.price)}</span>
          ${p.old ? `<span class="price-old">${fmt(p.old)}</span>` : ''}
          ${p.swatches && p.swatches.length ? `<div class="price-coloris">${p.swatches.length} coloris</div>` : ''}
        </div>
        <button class="padd${inCart ? ' has' : ''}" onclick="event.stopPropagation();quickAdd('${p.id}')">
          ${inCart > 0 ? inCart : '<svg viewBox="0 0 24 24"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg>'}
        </button>
      </div>
    </div>`;
  }).join('');
}

/* ══════════════════════════════════════
   CART — override pour UUIDs + liveProducts
══════════════════════════════════════ */
function cartAdd(id, qty = 1) {
  const src = liveProducts.length ? liveProducts : PRODUCTS;
  const p   = src.find(x => x.id === id);
  if (!p) return;
  const ex = cart.find(i => i.id === id);
  if (ex) ex.qty += qty;
  else cart.push({ id: p.id, name: p.name, emoji: p.emoji, price: p.price, qty, sub: p.sub });
  updateUI();
  renderGrid();
}

function quickAdd(id) {
  cartAdd(id);
  const src = liveProducts.length ? liveProducts : PRODUCTS;
  const p   = src.find(x => x.id === id);
  if (p) toast('✓  ' + p.name.slice(0, 24) + '… ajouté');
}

/* ══════════════════════════════════════
   DETAIL PRODUIT — override pour liveProducts + photos
══════════════════════════════════════ */
function openDetail(id) {
  const src = liveProducts.length ? liveProducts : PRODUCTS;
  curP = src.find(x => x.id === id);
  if (!curP) return;
  dQty = 1;
  const p = curP;

  document.getElementById('d-sh-title').textContent = p.name;
  document.getElementById('d-cat').textContent  = CATS.find(c => c.id === p.cat)?.lbl || p.cat;
  document.getElementById('d-name').textContent = p.name;
  document.getElementById('d-sub').textContent  = p.sub;
  document.getElementById('d-stars').innerHTML  = stars(p.rat, 14);
  document.getElementById('d-score').textContent = p.rat.toFixed(1);
  document.getElementById('d-rcnt').textContent  = '(' + p.rev + ' avis)';
  document.getElementById('d-price').textContent = fmt(p.price);
  document.getElementById('d-old').textContent   = p.old ? fmt(p.old) : '';

  const pt = document.getElementById('d-ptag');
  if (p.old) { pt.style.display = 'block'; pt.textContent = '-' + pct(p.old, p.price) + '%'; }
  else pt.style.display = 'none';

  document.getElementById('d-desc').textContent = p.desc;
  document.getElementById('d-qty').textContent  = 1;
  document.getElementById('d-tags').innerHTML   = (p.tags || []).map(t => '<div class="d-tag">' + t + '</div>').join('');

  const specsEl = document.getElementById('specs-block');
  specsEl.innerHTML = p.specs && p.specs.length
    ? '<div class="specs-title">Fiche technique</div><div class="specs-grid">' +
      p.specs.map(s => '<div class="spec-item"><div class="spec-k">' + s.k + '</div><div class="spec-v">' + s.v + '</div></div>').join('') +
      '</div>' : '';

  const szL = document.getElementById('sz-lbl');
  const szZ = document.getElementById('d-sizes');
  if (p.sizes && p.sizes.length) {
    szL.style.display = 'flex';
    szZ.innerHTML = p.sizes.map((s, i) => `<button class="sz${i === 0 ? ' on' : ''}" onclick="selSz(this,'${s}')">${s}</button>`).join('');
    document.getElementById('sel-sz').textContent = p.sizes[0];
  } else {
    szL.style.display = 'none';
    szZ.innerHTML = '';
  }

  /* Galerie photos ou emoji */
  const dEmoji = document.getElementById('d-emoji');
  const thumbsRow = document.getElementById('d-thumbs');
  if (p.photos && p.photos.length) {
    dEmoji.innerHTML = `<img src="${p.photos[0]}" alt="${p.name}" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;"/>`;
    thumbsRow.innerHTML = p.photos.map((url, idx) =>
      `<div class="d-thumb${idx === 0 ? ' active' : ''}" onclick="selThumbImg(this,'${url}')"><img src="${url}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:8px;"/></div>`
    ).join('');
  } else {
    dEmoji.textContent = p.emoji;
    thumbsRow.innerHTML = `<div class="d-thumb active" onclick="selThumb(this,'${p.emoji}')">${p.emoji}</div>` +
      ['🔍', '📦', '📐'].map(e => `<div class="d-thumb" onclick="selThumb(this,'${e}')">${e}</div>`).join('');
  }

  /* Reset avis */
  document.getElementById('review-form').classList.remove('open');
  pickedStar = 0;
  document.querySelectorAll('.sp-star').forEach(s => s.classList.remove('lit'));
  document.getElementById('star-hint').textContent = '';
  document.getElementById('star-hint').classList.remove('show');
  document.getElementById('rv-name').value = '';
  document.getElementById('rv-text').value = '';

  showView('v-detail');
  renderReviews(p.id);
}

/* Sélection vignette photo */
function selThumbImg(el, url) {
  document.querySelectorAll('.d-thumb').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  const dEmoji = document.getElementById('d-emoji');
  dEmoji.innerHTML = `<img src="${url}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;"/>`;
}

/* ══════════════════════════════════════
   RENDERCART — override pour IDs UUID quotés
══════════════════════════════════════ */
function renderCart() {
  const el = document.getElementById('cart-body');
  if (!el) return;
  if (!cart.length) {
    el.innerHTML = '<div class="c-empty"><div class="ce-ico">🛒</div><div class="ce-title">Votre panier est vide</div><div class="ce-sub">Explorez notre catalogue</div><button class="ce-btn" onclick="goBack(\'v-cat\')">Explorer le catalogue</button></div>';
    return;
  }
  const sub = getT(), FREE = 30000, prog = Math.min(sub / FREE * 100, 100);
  el.innerHTML =
    '<div class="cart-hero"><div class="cart-ttl">' + getN() + ' article' + (getN() > 1 ? 's' : '') + '</div><div class="cart-sub">Paiement à la livraison · Satisfaction garantie</div></div>' +
    '<div class="lp"><div class="lp-t">' + (sub >= FREE ? '✅ Livraison offerte !' : '🎁 Plus que ' + fmt(FREE - sub) + ' pour la livraison offerte') + '</div><div class="lp-track"><div class="lp-fill" style="width:' + prog + '%"></div></div></div>' +
    '<div class="c-list">' + cart.map((it, i) =>
      '<div class="c-item" style="animation-delay:' + (i * 0.05) + 's">' +
      '<div class="ci-img">' + it.emoji + '</div>' +
      '<div class="ci-info"><div class="ci-name">' + it.name + '</div>' +
      '<div class="ci-sub">' + (it.sub || '').split('·')[0].trim() + '</div>' +
      '<div class="ci-ctrl"><div class="cqty">' +
      '<button onclick="cartM(\'' + it.id + '\')">−</button><span>' + it.qty + '</span>' +
      '<button onclick="cartP(\'' + it.id + '\')">+</button></div>' +
      '<button class="ci-del" onclick="cartDel(\'' + it.id + '\')">' +
      '<svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/></svg>' +
      '</button></div></div>' +
      '<div class="ci-price"><div class="ci-total">' + fmt(it.price * it.qty) + '</div><div class="ci-unit">' + fmt(it.price) + '/u</div></div>' +
      '</div>'
    ).join('') + '</div>' +
    '<div class="commune-block">' +
    '<button class="commune-toggle' + (deliveryCommune ? ' open' : '') + '" id="commune-toggle" onclick="toggleCommune()">' +
    '<div class="ct-l"><span class="ct-ico">📍</span><div><div>Zone de livraison</div>' +
    '<div style="font-size:11px;color:var(--text3);font-weight:400;margin-top:1px">' + (deliveryCommune || 'Sélectionnez votre commune') + '</div></div></div>' +
    '<svg viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg></button>' +
    '<div class="commune-body' + (deliveryCommune ? ' open' : '') + '" id="commune-body">' +
    '<select class="commune-select" onchange="onCommuneChange(this)"><option value="">Choisir ma commune…</option>' + buildCommuneSelect() + '</select>' +
    '<div class="delivery-result" id="deliv-result" style="' + (deliveryCommune ? '' : 'display:none') + '">' +
    (deliveryCommune ? '<span class="dr-label">🚚 ' + deliveryCommune + '</span><span class="dr-price">' + fmt(deliveryCost) + '</span>' : '') +
    '</div></div></div>' +
    '<div class="promo-block"><div class="promo-row"><input class="promo-in" type="text" id="promo-in" placeholder="Code promo"/><button class="promo-btn" onclick="applyPromo()">Appliquer</button></div></div>' +
    '<div class="cart-summary" id="cart-summary"></div>' +
    '<button class="checkout-btn" onclick="openModal()">Commander <svg viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg></button>';
  renderSummary();
}

/* ══════════════════════════════════════
   REALTIME — écoute les changements produits
══════════════════════════════════════ */
db.channel('products-public-rt')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'products' }, () => {
    loadProducts();
  })
  .subscribe();

/* ══════════════════════════════════════
   INIT
══════════════════════════════════════ */
loadProducts();
