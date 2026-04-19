# 🛡️ SQL TRANSACTION ENFORCEMENT

## Règle n°1
Toute commande SQL de type ALTER, UPDATE, DELETE, DROP ou CREATE doit être enveloppée dans un bloc transactionnel explicite (BEGIN; ... COMMIT;).

## Règle n°2
Si tu proposes une migration de schéma (comme sur Supabase), tu dois TOUJOURS générer un script de "Safe-Preview" qui utilise ROLLBACK; à la fin pour que je puisse valider le résultat sans impacter la base.

## Règle n°3
En cas d'erreur de schéma (comme l'erreur PGRST200), ton premier réflexe doit être de vérifier les Foreign Keys avant de proposer un correctif de code.
