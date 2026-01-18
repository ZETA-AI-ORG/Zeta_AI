import os
import easyocr
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import threading


class BotliveEngine:
    """Singleton pour éviter rechargement des modèles lourds (BLIP-2 + EasyOCR)"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Éviter réinitialisation si déjà chargé
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        print("[BOTLIVE_ENGINE] Initialisation...")
        self._initialized = False
        
        # Initialiser EasyOCR (fr + en pour robustesse)
        try:
            print("[BOTLIVE_ENGINE] Chargement EasyOCR...")
            self.payment_reader = easyocr.Reader(['fr', 'en'], verbose=False)
            print("[BOTLIVE_ENGINE] ✅ EasyOCR chargé")
        except Exception as e:
            print(f"[EasyOCR] ❌ Erreur d'initialisation: {e}")
            self.payment_reader = None

        # BLIP-2 pour captioning produits (optionnel)
        self.blip_processor = None
        self.blip_model = None
        try:
            if os.getenv("ENABLE_BLIP2", "false").lower() == "true":
                self._load_blip2()
            else:
                print("[BOTLIVE_ENGINE] ℹ️ BLIP-2 désactivé (ENABLE_BLIP2=false)")
        except Exception as e:
            print(f"[BLIP-2] ❌ Erreur init: {e}")
            self.blip_processor = None
            self.blip_model = None
        
        print("[BOTLIVE_ENGINE] ✅ Initialisation terminée")
        self._initialized = True

    def _load_blip2(self) -> None:
        if self.blip_processor is not None and self.blip_model is not None:
            return
        print("[BOTLIVE_ENGINE] Chargement BLIP-2...")
        self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        print("[BOTLIVE_ENGINE] ✅ BLIP-2 chargé")
    
    @classmethod
    def get_instance(cls):
        """Retourne l'instance singleton (thread-safe)"""
        if cls._instance is None:
            cls()
        return cls._instance

    
    def detect_product(self, image_path: str) -> dict:
        """
        Analyse une image avec BLIP-2 captioning pour description complète.
        Retour: {'name': <description>, 'confidence': <0..1>, 'error': <type_erreur>}
        """
        print(f"[BLIP-2] 🔍 Analyse image: {image_path}")
        
        # ✅ VALIDATION FICHIER ROBUSTE
        if not image_path or not isinstance(image_path, str):
            print(f"[BLIP-2] ❌ Chemin invalide: {image_path}")
            return {"name": "chemin image invalide", "confidence": 0.0, "error": "invalid_path"}
            
        if not os.path.isfile(image_path):
            print(f"[BLIP-2] ❌ Fichier non trouvé: {image_path}")
            return {"name": "image non trouvée", "confidence": 0.0, "error": "file_not_found"}
        
        # ✅ VALIDATION TAILLE FICHIER
        try:
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                print(f"[BLIP-2] ❌ Fichier vide: {image_path}")
                return {"name": "image vide ou corrompue", "confidence": 0.0, "error": "empty_file"}
            if file_size > 50 * 1024 * 1024:  # 50MB max
                print(f"[BLIP-2] ❌ Fichier trop volumineux: {file_size} bytes")
                return {"name": "image trop volumineuse", "confidence": 0.0, "error": "file_too_large"}
        except OSError as e:
            print(f"[BLIP-2] ❌ Erreur accès fichier: {e}")
            return {"name": "erreur accès fichier", "confidence": 0.0, "error": "file_access_error"}
        
        # ✅ VALIDATION MODÈLE
        if self.blip_processor is None or self.blip_model is None:
            if os.getenv("ENABLE_BLIP2", "false").lower() == "true":
                try:
                    self._load_blip2()
                except Exception:
                    print(f"[BLIP-2] ❌ Modèle non initialisé")
                    return {"name": "modèle BLIP-2 indisponible", "confidence": 0.0, "error": "model_not_loaded"}
            else:
                print(f"[BLIP-2] ❌ Désactivé (ENABLE_BLIP2=false)")
                return {"name": "modèle BLIP-2 désactivé", "confidence": 0.0, "error": "model_disabled"}
        
        try:
            # ✅ VALIDATION FORMAT IMAGE
            image = Image.open(image_path).convert('RGB')
            print(f"[BLIP-2] 📸 Image chargée: {image.size}")
            
            # ✅ VALIDATION DIMENSIONS
            width, height = image.size
            if width < 50 or height < 50:
                print(f"[BLIP-2] ❌ Image trop petite: {width}x{height}")
                return {"name": "image trop petite ou floue", "confidence": 0.0, "error": "image_too_small"}
            
            # ✅ TRAITEMENT BLIP-2 AVEC TIMEOUT
            inputs = self.blip_processor(image, return_tensors="pt")
            out = self.blip_model.generate(**inputs, max_length=50)
            caption = self.blip_processor.decode(out[0], skip_special_tokens=True)
            
            print(f"[BLIP-2] 📝 Caption brut: '{caption}'")
            
            # ✅ VALIDATION RÉSULTAT
            if not caption or len(caption.strip()) < 3:
                print(f"[BLIP-2] ❌ Caption vide ou trop court")
                return {"name": "image non identifiable", "confidence": 0.0, "error": "empty_caption"}
            
            # ✅ NETTOYAGE INTELLIGENT
            stop_phrases = ["sitting on a", "on a table", "in a room", "on the floor", "on a chair", "with a white background"]
            cleaned_caption = caption.strip()
            for phrase in stop_phrases:
                cleaned_caption = cleaned_caption.replace(phrase, "")
            
            # ✅ CALCUL CONFIANCE BASÉ SUR LA QUALITÉ
            confidence = 0.85
            if any(word in cleaned_caption.lower() for word in ["bag", "package", "diaper", "couche", "wipe"]):
                confidence = 0.90  # Mots-clés pertinents détectés
            elif len(cleaned_caption) < 10:
                confidence = 0.60  # Description courte = moins fiable
            
            print(f"[BLIP-2] ✅ Caption nettoyé: '{cleaned_caption.strip()}' (confiance: {confidence})")
            return {"name": cleaned_caption.strip(), "confidence": confidence, "error": None}
            
        except PIL.UnidentifiedImageError:
            print(f"[BLIP-2] ❌ Format image non supporté")
            return {"name": "format image non supporté", "confidence": 0.0, "error": "unsupported_format"}
        except MemoryError:
            print(f"[BLIP-2] ❌ Mémoire insuffisante")
            return {"name": "image trop complexe à analyser", "confidence": 0.0, "error": "memory_error"}
        except Exception as e:
            print(f"[BLIP-2] ❌ ERREUR: {e}")
            import traceback
            traceback.print_exc()
            return {"name": "erreur analyse image", "confidence": 0.0, "error": "processing_error"}

    def _normalize_phone(self, phone_str: str) -> str:
        """
        Normalise un numéro de téléphone en retirant TOUS les caractères non-numériques.
        Gère TOUS les formats possibles : espaces, codes pays, emojis, caractères spéciaux, etc.
        
        Args:
            phone_str: Numéro brut dans N'IMPORTE QUEL format
        
        Returns:
            Numéro normalisé (10 derniers chiffres uniquement) : "0787360757"
        
        Formats gérés (exemples réels):
            "📞 +225 07 87 36 07 57 ☎️" → "0787360757"
            "+225 07-87-36-07-57" → "0787360757"
            "WhatsApp: 07 87 36 07 57" → "0787360757"
            "+2250787360757" → "0787360757"
            "0787360757" → "0787360757"
            "Tel: 📱 +225-07.87.36.07.57 ✅" → "0787360757"
            "Contact: 💬 225 07 87 36 07 57" → "0787360757"
            "07.87.36.07.57" → "0787360757"
            
        Fonctionne pour N'IMPORTE QUEL pays:
            "+33 6 12 34 56 78" → "0612345678" (France)
            "+1-555-123-4567" → "5551234567" (USA)
            "🇨🇮 +225 01 02 03 04 05" → "0102030405" (Côte d'Ivoire autre)
        """
        if not phone_str:
            return ""
        
        import re
        
        # Retirer TOUS les caractères non-numériques (y compris emojis, espaces, +, -, points, etc.)
        # Garder UNIQUEMENT les chiffres
        digits_only = re.sub(r'[^\d]', '', phone_str)
        
        # Garder les 10 derniers chiffres (standard téléphone local)
        # Ignore automatiquement le code pays si présent (+225, 225, +33, +1, etc.)
        normalized = digits_only[-10:] if len(digits_only) >= 10 else digits_only
        
        return normalized
    
    def _extract_all_transactions(self, texts: list, joined: str) -> list:
        """
        Extrait toutes les transactions d'un historique (montant + numéro + date).
        
        Returns:
            Liste de dicts: [{'amount': '2020', 'phone': '0787360757', 'phone_normalized': '0787360757', 
                              'date': '07 oct', 'timestamp': 1696636800, 'currency': 'FCFA'}, ...]
        """
        import re
        from datetime import datetime
        
        transactions = []
        
        # Pattern pour trouver des blocs de transaction
        # Ex: "À ATTIELO 07 87 36 07 57 -2.020F 07 oct , 11.17"
        transaction_patterns = [
            r'(?:à|vers|de|au)\s+[\w\s]+?(\d{10}|\d{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2})[^\d]*?[-+]?(\d{1,3}[.,]\d{3}|\d{3,5})\s*f',
            r'(\d{10}|\d{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2})[^\d]*?[-+]?(\d{1,3}[.,]\d{3}|\d{3,5})\s*f',
        ]
        
        # Chercher les dates (pour timestamp)
        date_patterns = [
            r'(\d{1,2})\s+(jan|fév|févr|mar|avr|mai|juin|juil|juill|aoû|août|sep|sept|oct|nov|déc|dec)',
            r'(\d{1,2})/(\d{1,2})',
        ]
        
        # Extraire transactions
        text_blocks = texts  # Chaque élément OCR
        
        # IMPORTANT: Chercher dans TOUT le texte avec une fenêtre glissante large
        # pour gérer les cas où numéro et montant sont sur des lignes séparées
        for i, block in enumerate(text_blocks):
            block_lower = block.lower()
            
            # Chercher numéro de téléphone (patterns multiples pour robustesse)
            # Gère: "0787360757", "07 87 36 07 57", "+225 07 87 36 07 57", "📞 +225..."
            phone_patterns = [
                r'\+?225\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}',  # Avec code pays
                r'\d{10}',  # 10 chiffres collés
                r'\d{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}',  # Avec espaces
                r'\d{2}[-\s]*\d{2}[-\s]*\d{2}[-\s]*\d{2}[-\s]*\d{2}',  # Avec tirets/espaces
            ]
            
            phone_match = None
            for pattern in phone_patterns:
                phone_match = re.search(pattern, block)
                if phone_match:
                    break
            
            if not phone_match:
                continue
            
            phone_raw = phone_match.group(0)
            phone_normalized = self._normalize_phone(phone_raw)
            
            # Chercher montant dans une LARGE fenêtre (5 blocs avant + 5 blocs après)
            # pour gérer les cas où le texte est fragmenté
            window_start = max(0, i - 5)
            window_end = min(len(text_blocks), i + 6)
            search_text = " ".join(text_blocks[window_start:window_end]).lower()
            
            # NETTOYAGE OCR: Corriger O → 0 dans les montants
            # "30.OOOF" → "30.000F"
            search_text = re.sub(r'(\d+[.,])O+F', lambda m: m.group(0).replace('O', '0'), search_text, flags=re.IGNORECASE)
            search_text = re.sub(r'(\d)O(\d)', r'\g<1>0\g<2>', search_text)  # "1O2" → "102"
            
            # IMPORTANT: Privilégier montants de TRANSFERT, ignorer SOLDE
            # Patterns avec contexte (transfert, vers, envoi)
            transfer_patterns = [
                # "transfert de 202.00 FCFA" OU "transfert de 2.020 FCFA" (milliers)
                # Capture TOUT : X.XXX ou XXX.XX puis on analyse après
                r'(?:transfert|envoi|paiement)\s+de\s+([-+]?\d{1,5}(?:[.,]\d{2,3})?)\s*fcfa',
                # "202 FCFA vers" ou "2.020F vers"
                r'([-+]?\d{1,5}(?:[.,]\d{2,3})?)\s*f?cfa\s+vers',
                # "vers XXX 202 FCFA"
                r'vers.*?([-+]?\d{1,5}(?:[.,]\d{2,3})?)\s*fcfa',
            ]
            
            # Patterns génériques (fallback) - CAPTURER TOUT
            general_patterns = [
                # Format: -2.020F, 202.00 FCFA, 10.100F (avec ou sans signe)
                r'([-+]?\d{1,5}(?:[.,]\d{2,3})?)\s*f(?:cfa)?',
            ]
            
            amount = None
            
            # Fonction helper pour analyser montant
            def parse_amount(raw_amount):
                """Parse un montant en distinguant décimales vs milliers"""
                # Nettoyer signes
                raw_amount = raw_amount.replace('-', '').replace('+', '').strip()
                
                # Analyser si c'est des décimales ou des milliers
                # "202.00" → décimales (2 chiffres après) → 202
                # "2.020" → milliers (3 chiffres après) → 2020
                # "10.100" → milliers → 10100
                if '.' in raw_amount or ',' in raw_amount:
                    parts = raw_amount.replace(',', '.').split('.')
                    if len(parts) == 2:
                        if len(parts[1]) == 2:
                            # Décimales : ignorer
                            return parts[0]
                        elif len(parts[1]) == 3:
                            # Milliers : concaténer
                            return parts[0] + parts[1]
                        else:
                            return parts[0]
                    else:
                        return raw_amount.replace('.', '').replace(',', '')
                else:
                    return raw_amount
            
            # D'abord chercher avec contexte de transfert
            for pattern_idx, pattern in enumerate(transfer_patterns):
                m = re.search(pattern, search_text)
                if m:
                    raw_amount = m.group(1)
                    amount = parse_amount(raw_amount)
                    
                    try:
                        amount_val = int(amount)
                        if 100 <= amount_val <= 100000:
                            amount = str(amount_val)
                            print(f"[OCR] 🎯 Montant transfert détecté: {amount} FCFA (contexte: transfert/vers)")
                            break
                    except ValueError:
                        continue
            
            # Si pas trouvé avec contexte, ignorer montants près de "solde"
            if not amount:
                # Vérifier si "solde" est mentionné près du numéro
                if 'solde' in search_text:
                    # Ignorer ce bloc si c'est juste le solde
                    print(f"[OCR] ⚠️ Bloc ignoré (solde détecté, pas de transfert)")
                    continue
                
                # Sinon utiliser patterns génériques
                for pattern in general_patterns:
                    m = re.search(pattern, search_text)
                    if m:
                        raw_amount = m.group(1)
                        amount = parse_amount(raw_amount)
                        
                        try:
                            amount_val = int(amount)
                            if 100 <= amount_val <= 100000:
                                amount = str(amount_val)
                                break
                        except ValueError:
                            continue
            
            if not amount:
                continue
            
            # Chercher date
            date_str = ""
            timestamp = 0
            for pattern in date_patterns:
                m = re.search(pattern, search_text)
                if m:
                    date_str = m.group(0)
                    # Créer timestamp approximatif (année en cours)
                    try:
                        if 'jan' in date_str or 'fév' in date_str or 'mar' in date_str:
                            timestamp = 100000000 + int(m.group(1)) * 86400
                        elif 'avr' in date_str or 'mai' in date_str or 'juin' in date_str:
                            timestamp = 200000000 + int(m.group(1)) * 86400
                        elif 'juil' in date_str or 'aoû' in date_str or 'sep' in date_str:
                            timestamp = 300000000 + int(m.group(1)) * 86400
                        else:  # oct, nov, dec
                            timestamp = 400000000 + int(m.group(1)) * 86400
                    except:
                        timestamp = 0
                    break
            
            # Ajouter transaction
            transactions.append({
                'amount': amount,
                'phone': phone_raw,
                'phone_normalized': phone_normalized,
                'date': date_str,
                'timestamp': timestamp,
                'currency': 'FCFA'
            })
        
        # Dédupliquer (même montant + même numéro)
        seen = set()
        unique_transactions = []
        for t in transactions:
            key = f"{t['amount']}_{t['phone_normalized']}"
            if key not in seen:
                seen.add(key)
                unique_transactions.append(t)
        
        return unique_transactions

    def verify_payment(self, image_path: str, company_phone: str = None, required_amount: int = None) -> dict:
        """
        OCR pour extraire montant/devise, avec VALIDATION STRICTE du numéro entreprise.
        
        Args:
            image_path: Chemin vers l'image
            company_phone: Numéro de téléphone de l'entreprise (OBLIGATOIRE pour validation)
            required_amount: Montant acompte requis (extrait dynamiquement du prompt)
        
        Returns:
            Dict avec amount, currency, reference, raw_text, et transactions si multiples
            Retourne vide si numéro entreprise absent de l'image
        """
        out = {"amount": "", "currency": "", "reference": "", "raw_text": "", "all_transactions": [], "error": "", "valid": False}
        
        # ✅ VALIDATION ROBUSTE FICHIER
        if not image_path or not isinstance(image_path, str):
            print(f"[OCR] ❌ Chemin invalide: {image_path}")
            out["error"] = "INVALID_PATH"
            return out
            
        if not os.path.isfile(image_path):
            print(f"[OCR] ❌ Fichier non trouvé: {image_path}")
            out["error"] = "FILE_NOT_FOUND"
            return out
        
        # ✅ VALIDATION TAILLE FICHIER
        try:
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                print(f"[OCR] ❌ Fichier vide: {image_path}")
                out["error"] = "EMPTY_FILE"
                return out
            if file_size > 50 * 1024 * 1024:  # 50MB max
                print(f"[OCR] ❌ Fichier trop volumineux: {file_size} bytes")
                out["error"] = "FILE_TOO_LARGE"
                return out
        except OSError as e:
            print(f"[OCR] ❌ Erreur accès fichier: {e}")
            out["error"] = "FILE_ACCESS_ERROR"
            return out
        
        # ✅ VALIDATION MODÈLE OCR
        if self.payment_reader is None:
            print(f"[OCR] ❌ EasyOCR non initialisé")
            out["error"] = "OCR_NOT_LOADED"
            return out
        try:
            results = self.payment_reader.readtext(image_path, detail=1)
            texts = [r[1] for r in results if len(r) > 1]
            out["raw_text"] = " \n".join(texts)

            import re
            from datetime import datetime
            joined = " ".join(t.lower() for t in texts)
            
            # ═══════════════════════════════════════════════════════════
            # VALIDATION STRICTE #1 : NUMÉRO ENTREPRISE OBLIGATOIRE
            # ═══════════════════════════════════════════════════════════
            normalized_company_phone = None
            if company_phone:
                normalized_company_phone = self._normalize_phone(company_phone)
                if normalized_company_phone:
                    print(f"[OCR] 🎯 Validation stricte pour numéro: {normalized_company_phone}")
                    print(f"[OCR] 📱 Format original: {company_phone}")
                    
                    # VÉRIFIER que le numéro entreprise est dans l'image
                    phone_found = False
                    for text_block in texts:
                        normalized_block = self._normalize_phone(text_block)
                        if normalized_block and normalized_company_phone in normalized_block:
                            phone_found = True
                            print(f"[OCR] ✅ Numéro entreprise trouvé dans l'image")
                            break
                    
                    if not phone_found:
                        print(f"[OCR] ❌ REJET STRICT: Numéro entreprise ABSENT de l'image")
                        print(f"[OCR] 🚫 Capture invalide - numéro {normalized_company_phone} non détecté")
                        out["error"] = "NUMERO_ABSENT"
                        return out
                else:
                    print(f"[OCR] ⚠️ Impossible d'extraire numéro de: {company_phone}")
            
            # ÉTAPE 1: Extraire toutes les transactions (montant + numéro + date)
            all_transactions = self._extract_all_transactions(texts, joined)
            
            if all_transactions:
                print(f"[OCR] 📋 {len(all_transactions)} transactions détectées")
                for t in all_transactions[:3]:
                    print(f"     → {t['amount']}F vers {t.get('phone', 'N/A')} le {t.get('date', 'N/A')}")
            
            # ═══════════════════════════════════════════════════════════
            # ÉTAPE 2: Filtrer par numéro (OBLIGATOIRE)
            # ═══════════════════════════════════════════════════════════
            if normalized_company_phone and all_transactions:
                filtered = [t for t in all_transactions if t.get('phone_normalized') == normalized_company_phone]
                
                if filtered:
                    print(f"[OCR] ✅ {len(filtered)} transaction(s) vers numéro entreprise")
                    # Trier par date (plus récent en premier)
                    filtered_sorted = sorted(filtered, key=lambda x: x.get('timestamp', 0), reverse=True)
                    best_transaction = filtered_sorted[0]
                    
                    out["amount"] = best_transaction['amount']
                    out["currency"] = best_transaction.get('currency', 'FCFA')
                    out["phone"] = best_transaction.get('phone', '')
                    out["phone_normalized"] = best_transaction.get('phone_normalized', '')
                    out["reference"] = best_transaction.get('reference', '')
                    out["all_transactions"] = all_transactions
                    
                    print(f"[OCR] 🎯 Transaction sélectionnée: {out['amount']} FCFA vers {out['phone']} (la plus récente)")
                    
                    # ═══════════════════════════════════════════════════════════
                    # VALIDATION STRICTE #3 : MONTANT >= ACOMPTE REQUIS
                    # ═══════════════════════════════════════════════════════════
                    if required_amount:
                        try:
                            detected_amount = int(out['amount'])
                            if detected_amount < required_amount:
                                print(f"[OCR] ❌ REJET STRICT: Montant insuffisant")
                                print(f"[OCR] 💰 Détecté: {detected_amount} FCFA | Requis: {required_amount} FCFA")
                                out["error"] = "MONTANT_INSUFFISANT"
                                out["required_amount"] = required_amount
                                out["detected_amount"] = detected_amount
                                return out
                            else:
                                print(f"[OCR] ✅ Montant validé: {detected_amount} FCFA >= {required_amount} FCFA")
                        except ValueError:
                            print(f"[OCR] ⚠️ Impossible de valider montant: {out['amount']}")
                    
                    r = re.search(r"(ref[:\-\s]*[a-z0-9\-]+|wave[:\-\s]*[a-z0-9\-]+)", joined)
                    if r:
                        out["reference"] = r.group(1).upper()
                    
                    return out
                else:
                    print(f"[OCR] ❌ REJET STRICT: Aucune transaction vers {normalized_company_phone}")
                    print(f"[OCR] 🚫 Numéro trouvé mais pas de transaction valide associée")
                    out["error"] = "TRANSACTION_ABSENTE"
                    return out
            
            # ═══════════════════════════════════════════════════════════
            # VALIDATION STRICTE #2 : Si company_phone fourni mais pas de transaction → REJETER
            # ═══════════════════════════════════════════════════════════
            if normalized_company_phone and not all_transactions:
                print(f"[OCR] ❌ REJET STRICT: Numéro fourni mais aucune transaction détectée")
                print(f"[OCR] 🚫 Image invalide - capture floue ou incomplète")
                out["error"] = "CAPTURE_INVALIDE"
                return out
            
            # ═══════════════════════════════════════════════════════════
            # ÉTAPE 3: Fallback UNIQUEMENT si company_phone NON fourni
            # (Mode legacy pour compatibilité backward)
            # ═══════════════════════════════════════════════════════════
            if normalized_company_phone:
                # Si on arrive ici avec company_phone fourni, c'est une erreur
                print(f"[OCR] ❌ REJET STRICT: Validation échouée")
                out["error"] = "VALIDATION_ECHOUEE"
                return out
            
            print(f"[OCR] ⚠️ Mode legacy: company_phone non fourni, validation relâchée")
            
            # Patterns multiples pour robustesse (ordre de priorité)
            # IMPORTANT: Pour éviter de transformer 202.00 en 20200, on ignore les décimales
            patterns = [
                # Format avec décimales: 202.00 FCFA → on prend juste 202 (partie entière)
                r"(\d{3,5})(?:[.,]\d{1,2})?\s*fcfa",
                # Format Wave/Orange: -2.020F (milliers avec point) → -2020
                r"-\s*(\d{1,2})[.,](\d{3})\s*f(?:\s|$|\.)",
                # Montant avec séparateurs + F: 10.100F → 10100
                r"(\d{1,3})[.,](\d{3})\s*f(?:\s|$|\.)",
                # Montant 3-5 chiffres + F seul
                r"-?\s*(\d{3,5})\s*f(?:\s|$|\.)",
                # Montant près de mots-clés
                r"(?:montant|total|somme|paiement)[:\s]*-?\s*(\d{1,5})",
                # Juste un nombre 3-5 chiffres (dernier recours)
                r"(?<!\d)(\d{3,5})(?!\d)"
            ]
            
            candidates = []
            
            # Trouver tous les candidats
            for priority, pattern in enumerate(patterns):
                for m in re.finditer(pattern, joined):
                    # Gérer patterns selon leur structure
                    currency = ''
                    
                    if priority == 0:  # Pattern: XXX.XX FCFA (ignore décimales, 1 groupe)
                        amount_str = m.group(1)
                        currency = 'FCFA'
                    elif priority in [1, 2]:  # Patterns: X.XXXF (2 groupes pour reconstituer milliers)
                        # Reconstituer le montant: "2" + "020" = "2020"
                        amount_str = m.group(1) + m.group(2)
                    else:  # Patterns 3, 4, 5: juste le montant (1 groupe)
                        amount_str = m.group(1)
                    
                    amount_str = amount_str.replace(',', '.').replace(' ', '').replace('o', '0').replace('O', '0')
                    
                    try:
                        amount_val = abs(float(amount_str))  # Valeur absolue pour gérer les négatifs
                        # Filtrer montants réalistes (50 à 100000)
                        if 50 <= amount_val <= 100000:
                            candidates.append({
                                'amount': str(int(amount_val)),
                                'currency': currency.replace('XOF', 'FCFA').replace('F CFA', 'FCFA'),
                                'priority': priority,
                                'value': amount_val
                            })
                    except (ValueError, AttributeError, IndexError):
                        continue
            
            # Choisir le meilleur candidat
            if candidates:
                # Chercher numéro entreprise dans le texte (0787360757 ou variantes)
                company_number_patterns = [
                    r'0787360757', r'07\s*87\s*36\s*07\s*57', 
                    r'\+225\s*07\s*87\s*36\s*07\s*57'
                ]
                
                has_company_number = any(re.search(p, joined) for p in company_number_patterns)
                
                # Si numéro entreprise présent, privilégier montants entre 1000-5000 (paiements typiques)
                if has_company_number:
                    # Chercher mention de transfert/paiement VERS ce numéro
                    # IMPORTANT: Extraire montant AVANT le numéro ou juste après "transfert de XXX vers"
                    payment_to_company_patterns = [
                        # "transfert de 202.00 FCFA vers" → groupe 1 = partie entière, groupe 2 = décimales
                        r'(?:transfert|envoi|paiement)\s+de\s+(\d{1,5})(?:[.,](\d{1,2}))?\s*fcfa\s+vers',
                        # "202 FCFA vers 0787360757" (avant le numéro)
                        r'(\d{3,5})\s*fcfa\s+vers\s+(?:le\s+)?0787360757',
                    ]
                    
                    targeted_amount = None
                    for pattern_idx, pattern in enumerate(payment_to_company_patterns):
                        m = re.search(pattern, joined)
                        if m:
                            try:
                                # Pour pattern avec décimales : ignorer les décimales
                                if pattern_idx == 0 and len(m.groups()) >= 2 and m.group(2):
                                    # "202.00" → on garde juste "202" (partie entière)
                                    amount_str = m.group(1)
                                else:
                                    amount_str = m.group(1)
                                
                                targeted_amount = int(amount_str)
                                if 100 <= targeted_amount <= 100000:
                                    # Vérifier que ce n'est PAS un solde
                                    # Chercher "solde" dans les 50 caractères AVANT ce montant
                                    match_pos = m.start()
                                    context_before = joined[max(0, match_pos - 50):match_pos]
                                    if 'solde' not in context_before:
                                        print(f"[OCR] 🎯 Transaction ciblée vers entreprise détectée: {targeted_amount} FCFA")
                                        break
                                    else:
                                        print(f"[OCR] ⚠️ Montant {targeted_amount} ignoré (contexte: solde)")
                                        targeted_amount = None
                            except (ValueError, AttributeError):
                                continue
                    
                    # Si montant ciblé trouvé, le prioriser
                    if targeted_amount:
                        for c in candidates:
                            if abs(int(c['amount']) - targeted_amount) < 10:
                                best = c
                                print(f"[OCR] ✅ Montant ciblé sélectionné: {best['amount']} FCFA")
                                break
                        else:
                            # Sinon, privilégier montants typiques de dépôt (1500-3000)
                            typical_deposits = [c for c in candidates if 1500 <= c['value'] <= 3000]
                            best = typical_deposits[0] if typical_deposits else sorted(candidates, key=lambda x: (x['priority'], abs(x['value'] - 2000)))[0]
                            print(f"[OCR] ✅ Montant typique sélectionné: {best['amount']} FCFA")
                    else:
                        # Privilégier montants typiques (1500-3000 FCFA)
                        typical_deposits = [c for c in candidates if 1500 <= c['value'] <= 3000]
                        best = typical_deposits[0] if typical_deposits else sorted(candidates, key=lambda x: (x['priority'], abs(x['value'] - 2000)))[0]
                        print(f"[OCR] ⚠️ Sélection montant typique (1500-3000): {best['amount']} FCFA")
                else:
                    # Pas de numéro entreprise : trier normal
                    best = sorted(candidates, key=lambda x: (x['priority'], -1 if x['value'] >= 1000 else 1, -x['value']))[0]
                
                out["amount"] = best['amount']
                out["currency"] = best['currency'] if best['currency'] else ('FCFA' if any(k in joined for k in ['fcfa', 'xof', 'cfa', 'f ']) else '')
                
                # Debug: afficher tous les candidats
                if len(candidates) > 1:
                    print(f"[OCR] {len(candidates)} montants détectés, choisi: {best['amount']} FCFA (priorité {best['priority']})")
                    others = [f"{c['amount']}F (p{c['priority']})" for c in candidates[:5]]
                    print(f"[OCR] Autres candidats: {others}")
            elif any(k in joined for k in ['fcfa', 'xof', 'cfa']):
                out["currency"] = 'FCFA'
            r = re.search(r"(ref[:\-\s]*[a-z0-9\-]+|wave[:\-\s]*[a-z0-9\-]+)", joined)
            if r:
                out["reference"] = r.group(1).upper()
            return out
        except Exception as e:
            print(f"[EasyOCR][ERREUR] {e}")
            return out
    
    def process_live_order(self, product_img_path: str, payment_img_path: str) -> str:
        """
        Traite une commande: détection produit + OCR paiement, puis renvoie un message court (sans LLM).
        """
        product = self.detect_product(product_img_path)
        payment = self.verify_payment(payment_img_path)

        label = product.get('name', 'inconnu')
        conf = product.get('confidence', 0.0)
        amount = payment.get('amount', '')
        currency = payment.get('currency', '') or 'FCFA'
        ref = payment.get('reference', '')

        parts = []
        parts.append(f"🛒 Produit détecté: {label} ({conf*100:.1f}%).")
        if amount:
            parts.append(f"💳 Paiement: {amount} {currency}.")
        else:
            parts.append("💳 Paiement détecté: montant non lisible.")
        if ref:
            parts.append(f"Référence: {ref}.")

        return " ".join(parts)

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON CACHE - Évite de recharger les modèles à chaque requête
# ═══════════════════════════════════════════════════════════════════════════════

_botlive_engine_instance = None

def get_botlive_engine() -> BotliveEngine:
    """
    Retourne une instance singleton de BotliveEngine.
    Les modèles BLIP-2 et EasyOCR ne sont chargés qu'une seule fois.
    """
    global _botlive_engine_instance
    if _botlive_engine_instance is None:
        print("[SINGLETON] Première initialisation BotliveEngine...")
        _botlive_engine_instance = BotliveEngine()
        print("[SINGLETON] ✅ Instance créée et cachée")
    return _botlive_engine_instance

# Exemple d'utilisation
if __name__ == "__main__":
    engine = get_botlive_engine()  # Première fois: charge les modèles
    product_img = "path/to/product.jpg"
    payment_img = "path/to/payment.jpg"
    result = engine.process_live_order(product_img, payment_img)
    print("Confirmation de commande:", result)
    
    # Appels suivants: réutilise l'instance cachée
    engine2 = get_botlive_engine()  # Instant, pas de rechargement
    print("Même instance:", engine is engine2)  # True
