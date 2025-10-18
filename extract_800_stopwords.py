#!/usr/bin/env python3
"""
Extraction de la liste complète de ~800 stop words de l'ancien système RAG
"""

def extract_all_stopwords():
    """Extrait tous les stop words du système actuel"""
    
    from core.smart_stopwords import filter_query_for_meilisearch
    import inspect
    
    # Récupérer le code source de la fonction
    source = inspect.getsource(filter_query_for_meilisearch)
    
    # Extraire la liste stop_words_minimal
    lines = source.split('\n')
    in_stopwords = False
    stopwords = set()
    
    for line in lines:
        line = line.strip()
        
        # Détecter le début de stop_words_minimal
        if 'stop_words_minimal = {' in line:
            in_stopwords = True
            continue
            
        # Détecter la fin
        if in_stopwords and line == '}':
            break
            
        # Extraire les mots
        if in_stopwords and line.startswith("'"):
            # Extraire tous les mots de la ligne
            words_in_line = []
            parts = line.split("'")
            for i in range(1, len(parts), 2):  # Prendre les éléments impairs (entre quotes)
                word = parts[i].strip()
                if word and word not in [',', ' ', '']:
                    words_in_line.append(word)
            
            stopwords.update(words_in_line)
    
    return sorted(list(stopwords))

def main():
    print("🔍 EXTRACTION DE LA LISTE COMPLÈTE DE STOP WORDS")
    print("=" * 60)
    
    try:
        stopwords = extract_all_stopwords()
        
        print(f"📊 TOTAL STOP WORDS EXTRAITS: {len(stopwords)}")
        print()
        
        # Afficher par catégories de 50
        for i in range(0, len(stopwords), 50):
            batch = stopwords[i:i+50]
            print(f"📋 BATCH {i//50 + 1} ({len(batch)} mots):")
            for j, word in enumerate(batch):
                print(f"   {i+j+1:3d}. {word}")
            print()
        
        # Sauvegarder dans un fichier
        with open("liste_800_stopwords.txt", "w", encoding="utf-8") as f:
            f.write("# Liste complète des stop words (~800 mots)\n")
            f.write(f"# Total: {len(stopwords)} mots\n")
            f.write("# Extrait du système RAG actuel\n\n")
            
            for i, word in enumerate(stopwords, 1):
                f.write(f"{i:3d}. {word}\n")
        
        print(f"💾 Liste sauvegardée dans: liste_800_stopwords.txt")
        
        # Créer aussi une liste Python utilisable
        with open("stopwords_list.py", "w", encoding="utf-8") as f:
            f.write("# Liste des ~800 stop words pour RAG\n")
            f.write(f"# Total: {len(stopwords)} mots\n\n")
            f.write("STOP_WORDS_COMPLETE = [\n")
            for word in stopwords:
                f.write(f'    "{word}",\n')
            f.write("]\n")
        
        print(f"🐍 Liste Python sauvegardée dans: stopwords_list.py")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
