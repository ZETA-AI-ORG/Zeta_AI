// Données de finalisation
let finalizationData = {
    payment: {
        acompteRequired: false,
        acompteAmount: 0,
        prepaidOnly: false,
        methods: [],
        numbers: {}
    },
    delivery: '',
    contact: {
        phone: '',
        hours: '',
        location: '',
        hasPhysicalStore: false,
        returnPolicy: ''
    },
    faq: []
};

// Toggle affichage champ montant acompte
function toggleAcompteAmount() {
    const acompteRequired = document.getElementById('acompteRequired').checked;
    const acompteField = document.getElementById('acompteAmountField');
    
    if (acompteRequired) {
        acompteField.classList.remove('hidden');
    } else {
        acompteField.classList.add('hidden');
        document.getElementById('acompteAmount').value = '';
    }
}

// Initialisation
window.addEventListener('DOMContentLoaded', () => {
    loadDraft();
    setupPaymentMethodListeners();
    addFAQ(); // Ajouter une FAQ par défaut
    toggleAcompteAmount(); // Toggle affichage champ montant acompte
});

// Setup listeners pour modes de paiement
function setupPaymentMethodListeners() {
    const checkboxes = document.querySelectorAll('input[name="paymentMethods"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            updatePaymentNumbers();
        });
    });
}

// Mettre à jour les champs de numéros
function updatePaymentNumbers() {
    const container = document.getElementById('paymentNumbers');
    const checkboxes = document.querySelectorAll('input[name="paymentMethods"]:checked');
    
    if (checkboxes.length === 0) {
        container.innerHTML = '';
        return;
    }
    
    let html = '<div class="bg-primary-500/10 border border-primary-500/30 rounded-xl p-5"><div class="text-sm font-semibold text-primary-400 mb-4">Numéros de paiement</div><div class="grid grid-cols-1 md:grid-cols-2 gap-4">';
    
    checkboxes.forEach(checkbox => {
        const method = checkbox.value;
        const methodName = checkbox.parentElement.textContent.trim();
        html += `
            <div>
                <label class="block text-xs font-medium text-gray-400 mb-2">${methodName}</label>
                <input type="tel" id="number-${method}" data-method="${method}"
                       class="input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500"
                       placeholder="Ex: +225 07 07 12 34 56"
                       oninput="updateFinalizationData()">
            </div>
        `;
    });
    
    html += '</div></div>';
    container.innerHTML = html;
}

// Ajouter FAQ
function addFAQ() {
    const index = faqItems.length;
    const html = `
        <div class="bg-dark-800/50 border border-dark-600 rounded-xl p-5" data-faq-index="${index}">
            <div class="flex justify-between items-start mb-4">
                <span class="text-sm font-semibold text-primary-400">Question ${index + 1}</span>
                <button type="button" onclick="removeFAQ(this)" class="text-red-400 hover:text-red-300 p-1">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="space-y-3">
                <div>
                    <label class="block text-xs font-medium text-gray-400 mb-2">Question</label>
                    <input type="text" class="faq-question input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white"
                           placeholder="Ex: Où se situe le magasin ?"
                           oninput="updateFAQ(this)">
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-400 mb-2">Réponse</label>
                    <textarea class="faq-answer input-premium w-full rounded-lg px-3 py-2.5 text-sm text-white"
                              rows="2"
                              placeholder="Réponse détaillée..."
                              oninput="updateFAQ(this)"></textarea>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('faqContainer').insertAdjacentHTML('beforeend', html);
    faqItems.push({ question: '', answer: '' });
}

// Supprimer FAQ
function removeFAQ(button) {
    if (faqItems.length <= 1) {
        alert('Vous devez avoir au moins une FAQ.');
        return;
    }
    
    const faqDiv = button.closest('[data-faq-index]');
    const index = parseInt(faqDiv.getAttribute('data-faq-index'));
    
    faqItems.splice(index, 1);
    faqDiv.remove();
    
    // Réindexer
    document.querySelectorAll('[data-faq-index]').forEach((div, i) => {
        div.setAttribute('data-faq-index', i);
        div.querySelector('span').textContent = `Question ${i + 1}`;
    });
}

// Mettre à jour FAQ
function updateFAQ(element) {
    const faqDiv = element.closest('[data-faq-index]');
    const index = parseInt(faqDiv.getAttribute('data-faq-index'));
    
    const question = faqDiv.querySelector('.faq-question').value;
    const answer = faqDiv.querySelector('.faq-answer').value;
    
    faqItems[index] = { question, answer };
    updateFinalizationData();
}

// Mettre à jour données
function updateFinalizationData() {
    // Payment
    finalizationData.payment.acompteRequired = document.getElementById('acompteRequired').checked;
    finalizationData.payment.acompteAmount = parseInt(document.getElementById('acompteAmount').value) || 0;
    finalizationData.payment.prepaidOnly = document.getElementById('prepaidOnly').checked;
    
    const methods = [];
    const numbers = {};
    document.querySelectorAll('input[name="paymentMethods"]:checked').forEach(cb => {
        methods.push(cb.value);
        const numberInput = document.getElementById(`number-${cb.value}`);
        if (numberInput) {
            numbers[cb.value] = numberInput.value;
        }
    });
    finalizationData.payment.methods = methods;
    finalizationData.payment.numbers = numbers;
    
    // Delivery
    finalizationData.delivery = document.getElementById('deliveryInfo').value;
    
    // Contact
    finalizationData.contact = {
        phone: document.getElementById('phone').value,
        hours: document.getElementById('hours').value,
        location: document.getElementById('location').value,
        hasPhysicalStore: document.getElementById('hasPhysicalStore').checked,
        returnPolicy: document.getElementById('returnPolicy').value
    };
    
    // FAQ
    finalizationData.faq = faqItems.filter(item => item.question || item.answer);
    
    triggerAutoSave();
}

// Auto-save
let autoSaveTimer = null;
function triggerAutoSave() {
    clearTimeout(autoSaveTimer);
    autoSaveTimer = setTimeout(() => {
        saveDraft();
    }, 2000);
}

function saveDraft() {
    localStorage.setItem('finalisation_data', JSON.stringify(finalizationData));
    console.log('✅ Finalisation sauvegardée');
}

// Sauvegarde manuelle avec indicateur visuel
function manualSaveFinalization() {
    updateFinalizationData();
    saveDraft();
    const statusEl = document.getElementById('finalizationSaveStatus');
    if (statusEl) {
        const originalText = statusEl.textContent;
        statusEl.textContent = '✅ Sauvegardé !';
        setTimeout(() => {
            statusEl.textContent = originalText;
        }, 2000);
    }
}

function loadDraft() {
    const saved = localStorage.getItem('finalisation_data');
    if (saved) {
        finalizationData = JSON.parse(saved);
        
        // Restaurer payment
        document.getElementById('acompteRequired').checked = finalizationData.payment.acompteRequired || false;
        document.getElementById('acompteAmount').value = finalizationData.payment.acompteAmount || '';
        document.getElementById('prepaidOnly').checked = finalizationData.payment.prepaidOnly || false;
        toggleAcompteAmount(); // Afficher/masquer champ montant
        
        finalizationData.payment.methods.forEach(method => {
            const checkbox = document.querySelector(`input[name="paymentMethods"][value="${method}"]`);
            if (checkbox) checkbox.checked = true;
        });
        updatePaymentNumbers();
        
        // Restaurer numéros
        setTimeout(() => {
            Object.entries(finalizationData.payment.numbers).forEach(([method, number]) => {
                const input = document.getElementById(`number-${method}`);
                if (input) input.value = number;
            });
        }, 100);
        
        // Restaurer delivery
        document.getElementById('deliveryInfo').value = finalizationData.delivery || '';
        
        // Restaurer contact
        document.getElementById('phone').value = finalizationData.contact.phone || '';
        document.getElementById('hours').value = finalizationData.contact.hours || '';
        document.getElementById('location').value = finalizationData.contact.location || '';
        document.getElementById('hasPhysicalStore').checked = finalizationData.contact.hasPhysicalStore || false;
        document.getElementById('returnPolicy').value = finalizationData.contact.returnPolicy || '';
        
        // Restaurer FAQ
        if (finalizationData.faq && finalizationData.faq.length > 0) {
            document.getElementById('faqContainer').innerHTML = '';
            faqItems = [];
            finalizationData.faq.forEach((item, i) => {
                addFAQ();
                setTimeout(() => {
                    const faqDiv = document.querySelector(`[data-faq-index="${i}"]`);
                    if (faqDiv) {
                        faqDiv.querySelector('.faq-question').value = item.question || '';
                        faqDiv.querySelector('.faq-answer').value = item.answer || '';
                    }
                }, 50);
            });
        }
    }
    
    // Restaurer Company ID si sauvegardé
    const savedCompanyId = localStorage.getItem('company_id');
    if (savedCompanyId) {
        document.getElementById('companyId').value = savedCompanyId;
    }
}

// Soumission finale
function submitFinalization() {
    const form = document.getElementById('finalizationForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    // Récupérer et valider le Company ID
    const companyId = document.getElementById('companyId').value.trim();
    if (!companyId) {
        alert('⚠️ Le Company ID est obligatoire !');
        document.getElementById('companyId').focus();
        return;
    }
    
    if (companyId.length < 10) {
        alert('⚠️ Le Company ID semble invalide (trop court).');
        document.getElementById('companyId').focus();
        return;
    }
    
    updateFinalizationData();
    
    // Sauvegarder le Company ID
    localStorage.setItem('company_id', companyId);
    
    // Récupérer toutes les données des 3 étapes
    const identityData = JSON.parse(localStorage.getItem('identity_data') || '{}');
    const catalogueData = JSON.parse(localStorage.getItem('catalogue_draft') || '[]');
    
    const completeData = {
        company_id: companyId,
        identity: identityData,
        catalogue: catalogueData,
        finalisation: finalizationData,
        timestamp: new Date().toISOString()
    };
    
    console.log('📤 Données complètes:', JSON.stringify(completeData, null, 2));
    console.log(`🏢 Company ID: ${companyId}`);
    
    // Envoyer à N8N
    const webhookUrl = 'https://n8n.zetaapp.xyz/webhook-test/bfa03414-3abe-46c8-9d1d-e0cf08e108c7';
    console.log(`🌐 Envoi vers: ${webhookUrl}`);
    
    fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(completeData)
    })
    .then(response => response.json())
    .then(data => {
        console.log('✅ Succès:', data);
        
        // Afficher modal de succès
        showSuccessModal();
        
        // Nettoyer localStorage après délai
        setTimeout(() => {
            localStorage.removeItem('identity_data');
            localStorage.removeItem('catalogue_draft');
            localStorage.removeItem('finalisation_data');
        }, 5000);
    })
    .catch(error => {
        console.error('❌ Erreur:', error);
        alert('Erreur lors de l\'envoi. Vérifiez la console pour plus de détails.');
    });
}

// Modal de succès
function showSuccessModal() {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 fade-in';
    modal.innerHTML = `
        <div class="card-premium rounded-2xl p-12 max-w-md mx-4 text-center slide-in">
            <div class="w-20 h-20 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6 pulse-glow">
                <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>
            </div>
            <h3 class="text-2xl font-bold gradient-text mb-3">Configuration Terminée !</h3>
            <p class="text-gray-300 mb-6">Votre assistant IA est maintenant prêt à fonctionner.</p>
            <button onclick="window.location.href='/dashboard'" class="btn-premium w-full py-4 rounded-xl font-bold">
                Accéder au tableau de bord
            </button>
        </div>
    `;
    document.body.appendChild(modal);
}

// Événements
document.getElementById('acompteRequired').addEventListener('change', updateFinalizationData);
document.getElementById('prepaidOnly').addEventListener('change', updateFinalizationData);
document.getElementById('deliveryInfo').addEventListener('input', updateFinalizationData);
document.getElementById('phone').addEventListener('input', updateFinalizationData);
document.getElementById('hours').addEventListener('input', updateFinalizationData);
document.getElementById('location').addEventListener('input', updateFinalizationData);
document.getElementById('hasPhysicalStore').addEventListener('change', updateFinalizationData);
document.getElementById('returnPolicy').addEventListener('input', updateFinalizationData);
