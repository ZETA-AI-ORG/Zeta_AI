// État global
let products = [];
let autoSaveTimer = null;

// Sous-catégories
const subcategories = {
    baby_care: ["Couches & Lingettes", "Alimentation", "Hygiène & Soin", "Vêtements", "Jouets"],
    food: ["Fruits & Légumes", "Viandes & Poissons", "Épicerie", "Boissons"],
    fashion: ["Homme", "Femme", "Enfant", "Accessoires"],
    electronics: ["Téléphones", "Ordinateurs", "Audio & Vidéo", "Accessoires"],
    home: ["Meubles", "Décoration", "Cuisine", "Jardinage"]
};

// Initialisation
window.addEventListener('DOMContentLoaded', () => {
    loadDraft();
    if (products.length === 0) {
        addProduct();
    }
});

// Ajouter produit
function addProduct() {
    const html = `
        <div class="card-premium rounded-2xl p-8 shadow-premium-lg slide-in" data-product-index="${products.length}">
            <div class="flex justify-between items-center mb-8">
                <div class="flex items-center space-x-3">
                    <div class="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center shadow-glow">
                        <span class="text-2xl">📦</span>
                    </div>
                    <div>
                        <h3 class="text-xl font-bold text-white">Produit <span class="product-number gradient-text">#${products.length + 1}</span></h3>
                        <p class="text-xs text-gray-400 font-light">Remplissez les informations ci-dessous</p>
                    </div>
                </div>
                <button onclick="removeProduct(this)" class="group p-3 hover:bg-red-500/10 rounded-xl transition-all duration-300">
                    <svg class="w-5 h-5 text-red-400 group-hover:text-red-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
            </div>
            <div class="mb-8 pb-8 border-b border-dark-600/50">
                <h4 class="text-sm font-semibold text-primary-400 mb-6 flex items-center">
                    <span class="w-1.5 h-1.5 bg-primary-500 rounded-full mr-2"></span>
                    Informations Générales
                </h4>
                <div class="mb-5">
                    <label class="block text-sm font-medium text-gray-300 mb-2.5">Nom du Produit <span class="text-red-400">*</span></label>
                    <input type="text" class="product-name input-premium w-full rounded-xl px-4 py-3.5 text-white placeholder-gray-500" placeholder="Ex: Couches à pression" oninput="updateProduct(this)">
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2.5">Catégorie <span class="text-red-400">*</span></label>
                        <select class="product-category input-premium w-full rounded-xl px-4 py-3.5 text-white" onchange="updateSubcategories(this); updateProduct(this)">
                            <option value="">Sélectionner...</option>
                            <option value="baby_care">Bébé & Puériculture</option>
                            <option value="food">Alimentation</option>
                            <option value="fashion">Mode & Vêtements</option>
                            <option value="electronics">Électronique</option>
                            <option value="home">Maison & Jardin</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2.5">Sous-catégorie <span class="text-red-400">*</span></label>
                        <select class="product-subcategory input-premium w-full rounded-xl px-4 py-3.5 text-white" onchange="updateProduct(this)">
                            <option value="">Sélectionner catégorie d'abord</option>
                        </select>
                    </div>
                </div>
                <div class="mt-5">
                    <label class="block text-sm font-medium text-gray-300 mb-2.5">Image du Produit</label>
                    <div class="group border-2 border-dashed border-dark-600 hover:border-primary-500/50 rounded-xl p-8 text-center transition-all duration-300 cursor-pointer bg-dark-800/30 hover:bg-dark-800/50" onclick="this.querySelector('input').click()">
                        <input type="file" class="product-image hidden" accept="image/*" onchange="handleImageUpload(this)">
                        <div class="image-preview">
                            <div class="w-16 h-16 mx-auto mb-3 bg-primary-500/10 rounded-xl flex items-center justify-center group-hover:bg-primary-500/20 transition-all">
                                <span class="text-4xl">📷</span>
                            </div>
                            <p class="text-sm text-gray-300 font-medium">Cliquez pour uploader</p>
                            <p class="text-xs text-gray-500 mt-1.5">PNG, JPG, WEBP (max 5MB)</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="mb-8 pb-8 border-b border-dark-600/50">
                <div class="flex justify-between items-center mb-6">
                    <h4 class="text-sm font-semibold text-primary-400 flex items-center">
                        <span class="w-1.5 h-1.5 bg-primary-500 rounded-full mr-2"></span>
                        💰 Variantes et Prix
                    </h4>
                    <button onclick="addVariant(this)" class="group px-4 py-2 bg-primary-500/10 hover:bg-primary-500/20 rounded-lg text-primary-400 font-semibold text-sm transition-all flex items-center space-x-2">
                        <span class="text-lg">+</span>
                        <span>Ajouter</span>
                    </button>
                </div>
                <div class="variants-container space-y-4"></div>
            </div>
            <div>
                <h4 class="text-sm font-semibold text-primary-400 mb-6 flex items-center">
                    <span class="w-1.5 h-1.5 bg-primary-500 rounded-full mr-2"></span>
                    📝 Informations Complémentaires
                </h4>
                <div class="mb-5">
                    <label class="block text-sm font-medium text-gray-300 mb-2.5">Informations d'usage <span class="text-xs text-gray-500">(max 200)</span></label>
                    <textarea class="product-usage input-premium w-full rounded-xl px-4 py-3 text-white placeholder-gray-500" rows="2" maxlength="200" placeholder="Ex: Pour enfants de 0 à 30 kg" oninput="updateProduct(this)"></textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-300 mb-2.5">Notes spéciales <span class="text-xs text-gray-500">(max 300)</span></label>
                    <textarea class="product-notes input-premium w-full rounded-xl px-4 py-3 text-white placeholder-gray-500" rows="2" maxlength="300" placeholder="Ex: Promotion en cours" oninput="updateProduct(this)"></textarea>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('productsContainer').insertAdjacentHTML('beforeend', html);
    products.push({ name: '', category: '', subcategory: '', image: '', variants: [], usage: '', notes: '' });
    
    const productDiv = document.querySelector(`[data-product-index="${products.length - 1}"]`);
    addVariant(productDiv.querySelector('[onclick="addVariant(this)"]'));
    
    updatePreview();
}

// Supprimer produit
function removeProduct(button) {
    if (products.length <= 1) {
        alert('Vous devez avoir au moins un produit.');
        return;
    }
    if (!confirm('Supprimer ce produit ?')) return;
    
    const productDiv = button.closest('[data-product-index]');
    const index = parseInt(productDiv.getAttribute('data-product-index'));
    products.splice(index, 1);
    productDiv.remove();
    
    document.querySelectorAll('[data-product-index]').forEach((div, i) => {
        div.setAttribute('data-product-index', i);
        div.querySelector('.product-number').textContent = `#${i + 1}`;
    });
    
    updatePreview();
    triggerAutoSave();
}

// Ajouter variante
function addVariant(button) {
    const productDiv = button.closest('[data-product-index]');
    const variantsContainer = productDiv.querySelector('.variants-container');
    const variantNumber = variantsContainer.children.length + 1;
    
    const html = `
        <div class="variant-item bg-gradient-to-br from-dark-800/50 to-dark-700/30 border border-dark-600 rounded-xl p-5 hover:border-primary-500/30 transition-all duration-300 fade-in">
            <div class="flex justify-between items-center mb-4">
                <div class="flex items-center space-x-2">
                    <div class="w-6 h-6 bg-primary-500/20 rounded-lg flex items-center justify-center">
                        <span class="text-xs font-bold text-primary-400">${variantNumber}</span>
                    </div>
                    <span class="text-sm font-semibold text-white">Variante ${variantNumber}</span>
                </div>
                <div class="flex items-center space-x-1">
                    <button onclick="moveVariantUp(this)" class="p-2 text-gray-400 hover:text-primary-400 hover:bg-primary-500/10 rounded-lg transition-all" title="Monter">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"></path></svg>
                    </button>
                    <button onclick="moveVariantDown(this)" class="p-2 text-gray-400 hover:text-primary-400 hover:bg-primary-500/10 rounded-lg transition-all" title="Descendre">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                    </button>
                    <button onclick="removeVariant(this)" class="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-all" title="Supprimer">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>
            </div>
            <div class="space-y-3.5">
                <div>
                    <label class="block text-xs font-medium text-gray-400 mb-2">Nom <span class="text-red-400">*</span></label>
                    <input type="text" class="variant-name input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500" placeholder="Ex: Taille 1" oninput="updateVariant(this)">
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-400 mb-2">Description</label>
                    <input type="text" class="variant-description input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500" placeholder="Ex: 0 à 4 kg" oninput="updateVariant(this)">
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-400 mb-2">Prix total <span class="text-red-400">*</span> <span class="text-primary-400 font-semibold">(F CFA)</span></label>
                    <input type="number" class="variant-price input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white font-semibold" placeholder="17900" min="0" oninput="updateVariant(this); calculateUnitPrice(this)">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-medium text-gray-400 mb-2">Quantité <span class="text-red-400">*</span></label>
                        <input type="number" class="variant-quantity input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white" placeholder="300" min="0" oninput="updateVariant(this); calculateUnitPrice(this)">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-400 mb-2">Unité <span class="text-red-400">*</span></label>
                        <select class="variant-unit input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white" onchange="updateVariant(this); calculateUnitPrice(this)">
                            <option value="">Choisir...</option>
                            <option value="unités">Unité(s)</option>
                            <option value="paquets">Paquet(s)</option>
                            <option value="kg">Kg</option>
                            <option value="g">Gramme(s)</option>
                            <option value="litres">Litre(s)</option>
                            <option value="ml">Ml</option>
                            <option value="pièces">Pièce(s)</option>
                            <option value="couches">Couche(s)</option>
                            <option value="colis">Colis</option>
                            <option value="sachets">Sachet(s)</option>
                        </select>
                    </div>
                </div>
                <div class="unit-price-display bg-gradient-to-r from-primary-500/10 to-emerald-500/10 border border-primary-500/30 rounded-lg px-4 py-3 text-sm hidden">
                    <div class="flex items-center justify-between">
                        <span class="text-gray-300">📊 Prix unitaire:</span>
                        <span class="text-primary-300 font-bold"><span class="unit-price-value">0</span> F/<span class="unit-price-unit">unité</span></span>
                    </div>
                </div>
                <div class="low-price-warning bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border border-yellow-500/40 rounded-lg px-4 py-3 text-sm hidden">
                    <div class="flex items-start space-x-2">
                        <span class="text-xl">⚠️</span>
                        <div class="flex-1">
                            <p class="text-yellow-300 font-semibold">Prix unitaire très bas</p>
                            <p class="text-yellow-400/80 text-xs mt-1"><span class="warning-price font-bold"></span> F/unité. Vérifiez le prix total.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    variantsContainer.insertAdjacentHTML('beforeend', html);
    
    const productIndex = parseInt(productDiv.getAttribute('data-product-index'));
    if (!products[productIndex].variants) products[productIndex].variants = [];
    products[productIndex].variants.push({ name: '', description: '', price: 0, quantity: 0, unit: '', pricePerUnit: 0 });
    
    updatePreview();
}

// Supprimer variante
function removeVariant(button) {
    const variantDiv = button.closest('.variant-item');
    const variantsContainer = variantDiv.parentElement;
    if (variantsContainer.children.length <= 1) {
        alert('Au moins une variante requise.');
        return;
    }
    if (!confirm('Supprimer cette variante ?')) return;
    
    const productDiv = button.closest('[data-product-index]');
    const productIndex = parseInt(productDiv.getAttribute('data-product-index'));
    const variantIndex = Array.from(variantsContainer.children).indexOf(variantDiv);
    
    products[productIndex].variants.splice(variantIndex, 1);
    variantDiv.remove();
    
    variantsContainer.querySelectorAll('.variant-item').forEach((v, i) => {
        v.querySelector('span.text-sm').textContent = `Variante ${i + 1}`;
    });
    
    updatePreview();
    triggerAutoSave();
}

// Déplacer variante
function moveVariantUp(button) {
    const variantDiv = button.closest('.variant-item');
    const prev = variantDiv.previousElementSibling;
    if (prev) {
        variantDiv.parentElement.insertBefore(variantDiv, prev);
        updateVariantNumbers(variantDiv.parentElement);
        updateProduct(variantDiv);
    }
}

function moveVariantDown(button) {
    const variantDiv = button.closest('.variant-item');
    const next = variantDiv.nextElementSibling;
    if (next) {
        variantDiv.parentElement.insertBefore(next, variantDiv);
        updateVariantNumbers(variantDiv.parentElement);
        updateProduct(variantDiv);
    }
}

function updateVariantNumbers(container) {
    container.querySelectorAll('.variant-item').forEach((v, i) => {
        v.querySelector('span.text-sm').textContent = `Variante ${i + 1}`;
    });
}

// Calculer prix unitaire
function calculateUnitPrice(input) {
    const variantDiv = input.closest('.variant-item');
    const price = parseFloat(variantDiv.querySelector('.variant-price').value) || 0;
    const quantity = parseFloat(variantDiv.querySelector('.variant-quantity').value) || 0;
    const unit = variantDiv.querySelector('.variant-unit').value;
    
    const display = variantDiv.querySelector('.unit-price-display');
    const warning = variantDiv.querySelector('.low-price-warning');
    
    if (price > 0 && quantity > 0 && unit) {
        const unitPrice = price / quantity;
        display.querySelector('.unit-price-value').textContent = unitPrice.toFixed(2);
        display.querySelector('.unit-price-unit').textContent = unit;
        display.classList.remove('hidden');
        
        if (unitPrice < 10) {
            warning.querySelector('.warning-price').textContent = unitPrice.toFixed(2);
            warning.classList.remove('hidden');
        } else {
            warning.classList.add('hidden');
        }
    } else {
        display.classList.add('hidden');
        warning.classList.add('hidden');
    }
}

// Mettre à jour sous-catégories
function updateSubcategories(select) {
    const productDiv = select.closest('[data-product-index]');
    const subcatSelect = productDiv.querySelector('.product-subcategory');
    const category = select.value;
    
    subcatSelect.innerHTML = '<option value="">Sélectionner...</option>';
    if (category && subcategories[category]) {
        subcategories[category].forEach(subcat => {
            subcatSelect.innerHTML += `<option value="${subcat}">${subcat}</option>`;
        });
    }
}

// Upload image
function handleImageUpload(input) {
    const file = input.files[0];
    if (!file) return;
    
    if (file.size > 5 * 1024 * 1024) {
        alert('Fichier trop volumineux (max 5MB)');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
        const preview = input.closest('div').querySelector('.image-preview');
        preview.innerHTML = `<img src="${e.target.result}" class="max-h-32 mx-auto rounded">`;
        
        const productDiv = input.closest('[data-product-index]');
        const index = parseInt(productDiv.getAttribute('data-product-index'));
        products[index].image = e.target.result;
        
        updatePreview();
        triggerAutoSave();
    };
    reader.readAsDataURL(file);
}

// Mettre à jour produit
function updateProduct(element) {
    const productDiv = element.closest('[data-product-index]');
    const index = parseInt(productDiv.getAttribute('data-product-index'));
    
    products[index].name = productDiv.querySelector('.product-name').value;
    products[index].category = productDiv.querySelector('.product-category').value;
    products[index].subcategory = productDiv.querySelector('.product-subcategory').value;
    products[index].usage = productDiv.querySelector('.product-usage').value;
    products[index].notes = productDiv.querySelector('.product-notes').value;
    
    updatePreview();
    triggerAutoSave();
}

// Générer un id propre pour chaque variante
function generateVariantId(productName, variantName, price) {
    function normalize(str) {
        return (str || "")
            .toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-z0-9 ]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }
    const prod = normalize(productName);
    const variant = normalize(variantName);
    const priceStr = price ? String(price).replace(/\s+/g, '') : '';
    let id = variant;
    if (!variant.startsWith(prod)) {
        id = prod + ' ' + variant;
    }
    if (priceStr) {
        id = id + ' ' + priceStr + ' fcfa';
    }
    return id.replace(/\s+/g, ' ').trim();
}

// Mettre à jour variante
function updateVariant(element) {
    const variantDiv = element.closest('.variant-item');
    const productDiv = element.closest('[data-product-index]');
    const productIndex = parseInt(productDiv.getAttribute('data-product-index'));
    const variantIndex = Array.from(variantDiv.parentElement.children).indexOf(variantDiv);
    
    if (!products[productIndex].variants[variantIndex]) {
        products[productIndex].variants[variantIndex] = {};
    }
    
    const name = variantDiv.querySelector('.variant-name').value;
    const description = variantDiv.querySelector('.variant-description').value;
    const price = parseInt(variantDiv.querySelector('.variant-price').value) || 0;
    const quantity = parseFloat(variantDiv.querySelector('.variant-quantity').value) || 0;
    const unit = variantDiv.querySelector('.variant-unit').value;
    
    // Générer l'id explicite
    const productName = productDiv.querySelector('.product-name').value;
    const variantId = generateVariantId(productName, name, price);
    
    products[productIndex].variants[variantIndex] = {
        name: name,
        description: description,
        price: price,
        quantity: quantity,
        unit: unit,
        pricePerUnit: (price > 0 && quantity > 0) ? price / quantity : 0,
        id: variantId
    };
    
    updatePreview();
    triggerAutoSave();
}


// Mettre à jour aperçu
function updatePreview() {
    const preview = document.getElementById('previewContainer');
    let totalVariants = 0;
    
    if (products.length === 0 || products.every(p => !p.name)) {
        preview.innerHTML = '<p class="text-gray-400 italic text-center py-8">Aucun produit ajouté</p>';
        document.getElementById('totalProducts').textContent = '0';
        document.getElementById('totalVariants').textContent = '0';
        return;
    }
    
    let html = '';
    products.forEach((product, i) => {
        if (product.name) {
            const variantsCount = product.variants.filter(v => v.name).length;
            totalVariants += variantsCount;
            
            html += `
                <div class="bg-dark-800/50 border-l-4 border-primary-500 rounded-lg p-4 hover:bg-dark-800 hover:border-primary-400 transition-all duration-300 cursor-pointer group relative"
                     onclick="console.log('Clic sur produit ${i}'); loadProductIntoForm(${i});">
                    <div class="flex items-start justify-between mb-2">
                        <div class="flex-1">
                            <div class="font-semibold text-white mb-1 group-hover:text-primary-400">
                                ${product.name}
                                <span class="ml-2 text-xs text-primary-400 opacity-0 group-hover:opacity-100 transition-opacity">✏️ Cliquer pour modifier</span>
                            </div>
                            <div class="text-xs text-gray-400">${product.category ? product.category.replace('_', ' ') : 'Sans catégorie'}</div>
                        </div>
                        <div class="flex items-center space-x-2">
                            ${variantsCount > 0 ? `<span class="px-2 py-1 bg-primary-500/20 text-primary-400 text-xs font-semibold rounded-full">${variantsCount}</span>` : ''}
                            <button onclick="event.stopPropagation(); console.log('Suppression produit ${i}'); deleteProductFromPreview(${i});" 
                                    class="opacity-0 group-hover:opacity-100 p-1.5 bg-red-500/20 hover:bg-red-500/40 rounded-lg text-red-400 hover:text-red-300 transition-all"
                                    title="Supprimer">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                            </button>
                        </div>
                    </div>
                    ${product.variants.filter(v => v.name).length > 0 ? `
                        <div class="mt-3 space-y-2 border-t border-dark-600 pt-3">
                            ${product.variants.filter(v => v.name).map(v => `
                                <div class="flex items-center justify-between text-xs">
                                    <span class="text-gray-300">• ${v.name}</span>
                                    <span class="font-semibold text-primary-300">${v.price.toLocaleString('fr-FR')} F</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }
    });
    
    preview.innerHTML = html || '<p class="text-gray-400 italic text-center py-8">En attente des données...</p>';
    document.getElementById('totalProducts').textContent = products.filter(p => p.name).length;
    document.getElementById('totalVariants').textContent = totalVariants;
}

// Auto-save
function triggerAutoSave() {
    clearTimeout(autoSaveTimer);
    autoSaveTimer = setTimeout(() => {
        saveDraft();
    }, 2000);
}

// Sauvegarde brouillon
function saveDraft() {
    localStorage.setItem('catalogue_draft', JSON.stringify(products));
    console.log(' Brouillon sauvegardé');
}

// Sauvegarde manuelle avec indicateur visuel
function manualSaveCatalogue() {
    saveDraft();
    const statusEl = document.getElementById('catalogueSaveStatus');
    if (statusEl) {
        const originalText = statusEl.textContent;
        statusEl.textContent = 'Sauvegardé !';
        setTimeout(() => {
            statusEl.textContent = originalText;
        }, 2000);
    }
}

// Rendre un produit dans le DOM
function renderProduct(index) {
    const product = products[index];
    if (!product || !product.name) return;
    
    const container = document.getElementById('productsContainer');
    const existingDiv = document.querySelector(`[data-product-index="${index}"]`);
    
    // Si déjà rendu, ne rien faire
    if (existingDiv) return;
    
    // Créer le HTML du produit
    const productHTML = `
        <div class="card-premium rounded-2xl p-8 shadow-premium-lg slide-in" data-product-index="${index}">
            <div class="flex items-center justify-between mb-6">
                <div class="flex items-center space-x-4">
                    <div class="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center">
                        <span class="text-white font-bold text-lg">${index + 1}</span>
                    </div>
                    <h3 class="text-xl font-bold text-white">Produit #${index + 1}</h3>
                </div>
                <button onclick="removeProduct(this)" class="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-all">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
            </div>
            
            <div class="space-y-6">
                <div>
                    <label class="block text-sm font-medium text-gray-300 mb-2.5">Nom du Produit <span class="text-red-400">*</span></label>
                    <input type="text" class="product-name input-premium w-full rounded-xl px-4 py-3 text-white" value="${product.name}" oninput="updateProduct(this)">
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2.5">Catégorie <span class="text-red-400">*</span></label>
                        <select class="product-category input-premium w-full rounded-xl px-4 py-3 text-white" onchange="updateSubcategories(this); updateProduct(this);">
                            <option value="">Sélectionner...</option>
                            ${Object.keys(categories).map(cat => `<option value="${cat}" ${product.category === cat ? 'selected' : ''}>${cat.replace('_', ' ')}</option>`).join('')}
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-2.5">Sous-catégorie</label>
                        <select class="product-subcategory input-premium w-full rounded-xl px-4 py-3 text-white" onchange="updateProduct(this)">
                            <option value="">Aucune</option>
                            ${product.category && categories[product.category] ? categories[product.category].map(sub => `<option value="${sub}" ${product.subcategory === sub ? 'selected' : ''}>${sub}</option>`).join('') : ''}
                        </select>
                    </div>
                </div>
                
                <div class="variants-container space-y-4">
                    ${product.variants.map((v, vIndex) => createVariantHTML(vIndex + 1, v)).join('')}
                </div>
                
                <button onclick="addVariant(this)" class="w-full py-3 bg-primary-500/10 hover:bg-primary-500/20 border border-primary-500/50 rounded-xl text-primary-400 font-semibold">+ Ajouter une variante</button>
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', productHTML);
}

// Créer HTML pour une variante
function createVariantHTML(number, variant = {}) {
    return `
        <div class="variant-item bg-gradient-to-br from-dark-800/50 to-dark-700/30 border border-dark-600 rounded-xl p-5">
            <div class="space-y-3">
                <input type="text" class="variant-name input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white" placeholder="Nom" value="${variant.name || ''}" oninput="updateVariant(this)">
                <input type="number" class="variant-price input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white" placeholder="Prix" value="${variant.price || ''}" oninput="updateVariant(this)">
                <input type="number" class="variant-quantity input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white" placeholder="Quantité" value="${variant.quantity || ''}" oninput="updateVariant(this)">
                <select class="variant-unit input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white" onchange="updateVariant(this)">
                    <option value="">Unité...</option>
                    ${['unités', 'paquets', 'kg', 'g', 'litres', 'ml', 'pièces', 'couches', 'colis', 'sachets'].map(u => `<option value="${u}" ${variant.unit === u ? 'selected' : ''}>${u}</option>`).join('')}
                </select>
            </div>
        </div>
    `;
}

function loadDraft() {
    const draft = localStorage.getItem('catalogue_draft');
    if (draft) {
        products = JSON.parse(draft);
        console.log('📥 Brouillon chargé:', products.length, 'produit(s)');
        
        // Rendre tous les produits sauvegardés
        products.forEach((product, index) => {
            if (product.name) {
                renderProduct(index);
            }
        });
        
        updatePreview();
    }
}

// Charger un produit depuis l'aperçu pour modification
function loadProductIntoForm(productIndex) {
    console.log('🔍 Chargement produit index:', productIndex);
    
    // Vérifier si le produit existe déjà dans le DOM
    let productDiv = document.querySelector(`[data-product-index="${productIndex}"]`);
    
    if (!productDiv) {
        console.log('📦 Produit pas encore affiché, on le rend...');
        renderProduct(productIndex);
        
        // Attendre que le DOM soit mis à jour
        setTimeout(() => {
            productDiv = document.querySelector(`[data-product-index="${productIndex}"]`);
            scrollToProduct(productDiv);
        }, 100);
    } else {
        console.log('✅ Produit déjà affiché, scroll vers lui');
        scrollToProduct(productDiv);
    }
}

// Fonction helper pour scroll
function scrollToProduct(productDiv) {
    if (productDiv) {
        productDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Animation pulse
        productDiv.classList.add('border-4', 'border-primary-400');
        productDiv.style.animation = 'pulse 0.5s ease-in-out 3';
        
        setTimeout(() => {
            productDiv.classList.remove('border-4', 'border-primary-400');
            productDiv.style.animation = '';
        }, 1500);
    }
}

// Supprimer un produit depuis l'aperçu
function deleteProductFromPreview(productIndex) {
    if (confirm(`Supprimer "${products[productIndex].name}" ?`)) {
        products.splice(productIndex, 1);
        saveDraft();
        updatePreview();
        location.reload();
    }
}

// Validation et soumission
function submitAndNext() {
    // Nettoyer les produits vides AVANT validation
    products = products.filter(p => p.name && p.name.trim() !== '');
    
    // Pour chaque produit, nettoyer les variantes vides
    products.forEach(product => {
        product.variants = product.variants.filter(v => v.name && v.name.trim() !== '');
    });
    
    const errors = validateProducts();
    if (errors.length > 0) {
        alert('⚠️ Erreurs de validation:\n\n' + errors.join('\n'));
        return;
    }
    
    // Sauvegarder et passer à la finalisation
    saveDraft();
    console.log('✅ Catalogue nettoyé et sauvegardé:', products.length, 'produit(s)');
    window.location.href = 'onboarding_finalisation.html';
}

function validateProducts() {
    const errors = [];
    
    // Filtrer uniquement les produits avec un nom (produits valides)
    const validProducts = products.filter(p => p.name && p.name.trim() !== '');
    
    if (validProducts.length === 0) {
        errors.push('⚠️ Ajoutez au moins un produit complet');
        return errors;
    }
    
    validProducts.forEach((product, i) => {
        const productNum = products.indexOf(product) + 1;
        
        // Validation produit
        if (!product.category) {
            errors.push(`Produit ${productNum}: Catégorie manquante`);
        }
        
        // Validation variantes (seulement celles qui ont un nom)
        const validVariants = product.variants.filter(v => v.name && v.name.trim() !== '');
        
        if (validVariants.length === 0) {
            errors.push(`Produit ${productNum}: Ajoutez au moins une variante complète`);
        }
        
        validVariants.forEach((variant) => {
            const variantNum = product.variants.indexOf(variant) + 1;
            
            if (!variant.price || variant.price <= 0) {
                errors.push(`Produit ${productNum}, Variante ${variantNum}: Prix invalide ou manquant`);
            }
            if (!variant.quantity || variant.quantity <= 0) {
                errors.push(`Produit ${productNum}, Variante ${variantNum}: Quantité invalide ou manquante`);
            }
            if (!variant.unit) {
                errors.push(`Produit ${productNum}, Variante ${variantNum}: Unité manquante`);
            }
        });
    });
    
    return errors;
}
