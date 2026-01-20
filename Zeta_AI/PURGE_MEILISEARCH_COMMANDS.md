# 🧹 COMMANDES PURGE MEILISEARCH

## 📋 **COMMANDE SIMPLE ET RAPIDE**

```bash
python3 -c "
import meilisearch
client = meilisearch.Client('http://localhost:7700', 'Bac2018mado@2066')
indexes = client.get_indexes()
print('Index trouvés:', len(indexes['results']))
for idx in indexes['results']:
    print(f'Suppression: {idx.uid}')
    try:
        task = client.delete_index(idx.uid)
        client.wait_for_task(task.task_uid)
        print(f'✅ Supprimé: {idx.uid}')
    except Exception as e:
        print(f'❌ Erreur: {e}')
print('🎉 PURGE TERMINÉE')
"
```

## 🔍 **VÉRIFICATION AVANT PURGE**

```bash
# Lister tous les index existants
python3 -c "
import meilisearch
client = meilisearch.Client('http://localhost:7700', 'Bac2018mado@2066')
indexes = client.get_indexes()
print('Index existants:')
for idx in indexes['results']:
    stats = client.index(idx.uid).get_stats()
    print(f'  📁 {idx.uid}: {stats[\"numberOfDocuments\"]} documents')
"
```

## ✅ **VÉRIFICATION APRÈS PURGE**

```bash
# Vérifier que MeiliSearch est vierge
python3 -c "
import meilisearch
client = meilisearch.Client('http://localhost:7700', 'Bac2018mado@2066')
indexes = client.get_indexes()
if len(indexes['results']) == 0:
    print('✅ MeiliSearch complètement vierge!')
else:
    print(f'⚠️ {len(indexes[\"results\"])} index restants')
"
```

## 🔧 **CONFIGURATION**

- **URL MeiliSearch:** `http://localhost:7700`
- **Clé API:** `Bac2018mado@2066`
- **Environnement:** Ubuntu WSL

## 📝 **NOTES IMPORTANTES**

1. **Syntaxe correcte:** Utiliser `task.task_uid` et non `task['taskUid']`
2. **Accès attributs:** Utiliser `idx.uid` et non `idx['uid']`
3. **Attendre les tâches:** Toujours utiliser `client.wait_for_task()` pour s'assurer que la suppression est terminée
4. **Gestion d'erreurs:** Le script continue même si une suppression échoue

## 🚀 **WORKFLOW COMPLET**

```bash
# 1. Vérification avant
python3 -c "import meilisearch; client = meilisearch.Client('http://localhost:7700', 'Bac2018mado@2066'); indexes = client.get_indexes(); print('Index avant:', len(indexes['results']))"

# 2. Purge complète
python3 -c "import meilisearch; client = meilisearch.Client('http://localhost:7700', 'Bac2018mado@2066'); indexes = client.get_indexes(); [client.wait_for_task(client.delete_index(idx.uid).task_uid) for idx in indexes['results']]; print('🎉 PURGE TERMINÉE')"

# 3. Vérification après
python3 -c "import meilisearch; client = meilisearch.Client('http://localhost:7700', 'Bac2018mado@2066'); indexes = client.get_indexes(); print('✅ Vierge!' if len(indexes['results']) == 0 else f'⚠️ {len(indexes[\"results\"])} restants')"
```

## 🎯 **PROCHAINES ÉTAPES**

Après la purge, tu peux :

1. **Ingérer tes nouvelles données via N8N**
2. **Lancer l'analyse HyDE :** `python3 ingestion_complete.py`
3. **Tester l'endpoint /chat :** `python3 test_endpoint_complet.py`
