# Botlive Full LLM - Diagnostic Report

- **Source CSV**: tests/botlive_scenario_results.csv
- **Flat CSV**: tests/botlive_scenario_results_flat.csv
- **Total turns**: **130**

---

## Turn 1

### Client
`	ext
Bonjour
`

### Réponse LLM
`	ext
Bonjour, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 2

### Client
`	ext
Salut
`

### Réponse LLM
`	ext
Bonjour, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 3

### Client
`	ext
Bjr
`

### Réponse LLM
`	ext
Bonjour, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 4

### Client
`	ext
Bonsoir
`

### Réponse LLM
`	ext
Bonsoir, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 5

### Client
`	ext
Hey
`

### Réponse LLM
`	ext
Bonsoir, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 6

### Client
`	ext
Cc
`

### Réponse LLM
`	ext
Bonsoir, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 7

### Client
`	ext
Yo
`

### Réponse LLM
`	ext
Bonsoir, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 8

### Client
`	ext
Hello
`

### Réponse LLM
`	ext
Bonsoir, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 9

### Client
`	ext
Salut ça va
`

### Réponse LLM
`	ext
Bonsoir, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 10

### Client
`	ext
Bonjour ici
`

### Réponse LLM
`	ext
Bonjour, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 11

### Client
`	ext
Merci beaucoup
`

### Réponse LLM
`	ext
Bonsoir, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 12

### Client
`	ext
Ok merci
`

### Réponse LLM
`	ext
Bonjour, je vais très bien merci. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 13

### Client
`	ext
D'accord merci
`

### Réponse LLM
`	ext
Bonjour, souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: hyde
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 14

### Client
`	ext
C'est gentil
`

### Réponse LLM
`	ext
Bonjour, souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: ACHAT_COMMANDE
- **confidence**: 0.7842131781654977
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 15

### Client
`	ext
Merci bien
`

### Réponse LLM
`	ext
Bonjour, souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: SALUT
- **confidence**: 0.98
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: A
- **prefilter**: salut_rule
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 16

### Client
`	ext
Où vous trouvez-vous
`

### Réponse LLM
`	ext
Nous livrons uniquement à Abidjan. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: ACHAT_COMMANDE
- **confidence**: 0.7324499635864816
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 17

### Client
`	ext
Vous êtes situé où
`

### Réponse LLM
`	ext
Nous livrons uniquement à Abidjan. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.9313198945582829
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 18

### Client
`	ext
Vous êtes dans quel quartier
`

### Réponse LLM
`	ext
Nous livrons uniquement à Abidjan. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: INFO_GENERALE
- **confidence**: 0.8
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: lexical_location
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 19

### Client
`	ext
C'est où votre boutique
`

### Réponse LLM
`	ext
Nous livrons uniquement à Abidjan. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.9969862890976489
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 20

### Client
`	ext
Quelle est votre adresse
`

### Réponse LLM
`	ext
Nous livrons uniquement à Abidjan. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.9964597764453051
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 21

### Client
`	ext
Vous êtes à Abidjan
`

### Réponse LLM
`	ext
Je comprends que vous souhaitez des informations sur notre localisation. Nous livrons uniquement à Abidjan. Pour vous aider, pouvez-vous préciser dans quel quartier vous vous trouvez ? 😊
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.9961850617044524
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_X
- **prompt_expected_key**: JESSICA_PROMPT_X
- **prompt_ok**: True
- **gating_path**: prompt_x
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 22

### Client
`	ext
Vous livrez dans quelle zone
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.82
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_C
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: C
- **prefilter**: lexical_livraison
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 23

### Client
`	ext
Vous êtes situé où exactement
`

### Réponse LLM
`	ext
Nous livrons uniquement à Abidjan. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.9960466872725239
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 24

### Client
`	ext
Je peux venir à la boutique
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.9978617716141459
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 25

### Client
`	ext
Vous avez un point de vente
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.9191633371179985
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 26

### Client
`	ext
C'est quelle commune
`

### Réponse LLM
`	ext
Nous livrons uniquement à Abidjan. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: INFO_GENERALE
- **confidence**: 0.8
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: hyde
- **segment_letter**: A
- **prefilter**: lexical_location
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 27

### Client
`	ext
Vous êtes ouvert jusqu'à quelle heure
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.6555877401493968
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 28

### Client
`	ext
Quels sont vos horaires
`

### Réponse LLM
`	ext
Un conseiller vous répondra au 0787360757. 📞
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.9846902928871545
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 29

### Client
`	ext
Vous travaillez le dimanche
`

### Réponse LLM
`	ext
Je comprends que vous souhaitez des informations sur nos horaires. Vous voulez savoir si nous travaillons le dimanche ou connaître nos horaires habituels ?
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.9878673612016012
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_X
- **prompt_expected_key**: JESSICA_PROMPT_X
- **prompt_ok**: True
- **gating_path**: prompt_x
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 30

### Client
`	ext
Vous êtes en ligne seulement
`

### Réponse LLM
`	ext
Nous sommes disponibles 24h/7j en ligne. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.9908736743652872
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: hyde
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 31

### Client
`	ext
C'est combien
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 32

### Client
`	ext
Quel est le prix
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_B
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 33

### Client
`	ext
Combien le paquet
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 34

### Client
`	ext
C'est combien dans le paquet
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 35

### Client
`	ext
Y'a combien dedans
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 36

### Client
`	ext
Le prix s'il vous plaît
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_B
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 37

### Client
`	ext
Pouvez-vous vérifier le prix
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_B
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 38

### Client
`	ext
Quel est le tarif
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 39

### Client
`	ext
C'est à combien
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 40

### Client
`	ext
Prix en gros
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 41

### Client
`	ext
Le prix de gros c'est combien
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_B
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 42

### Client
`	ext
Combien pour 10 paquets
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 43

### Client
`	ext
Vous avez des promotions
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.040132856275556704
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 44

### Client
`	ext
Y'a des réductions
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.03325713022076812
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 45

### Client
`	ext
Le prix a changé ou pas
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRIX_PROMO
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_prix_over_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 46

### Client
`	ext
Vous avez quoi comme produits
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 47

### Client
`	ext
Pouvez-vous m'en dire plus
`

### Réponse LLM
`	ext
Bonjour, nous vendons des couches pour bébés. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.82
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: lexical_more_info_to_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 48

### Client
`	ext
J'aimerais voir vos produits
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.34974615644103746
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 49

### Client
`	ext
Qu'est-ce que vous vendez
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 50

### Client
`	ext
Vous avez un catalogue
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 51

### Client
`	ext
Montrez-moi ce que vous avez
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: INFO_GENERALE
- **confidence**: 0.6
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 52

### Client
`	ext
Dites-moi vos articles
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 53

### Client
`	ext
Quels sont vos produits disponibles
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.6
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 54

### Client
`	ext
Vous vendez quoi exactement
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 55

### Client
`	ext
Présentez-moi vos articles
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 56

### Client
`	ext
J'aimerais connaître vos produits
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: CLARIFICATION
- **confidence**: 0.4
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 57

### Client
`	ext
Vous avez quoi en stock
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 58

### Client
`	ext
Vous avez des couches taille 4
`

### Réponse LLM
`	ext
Je vois que vous cherchez des couches taille 4 😊. Vous souhaitez :
- Commander ces couches ?
- Savoir si elles sont en stock ?
- Avoir des infos sur les prix ?
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_X
- **prompt_expected_key**: JESSICA_PROMPT_X
- **prompt_ok**: True
- **gating_path**: prompt_x
- **segment_letter**: A
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 59

### Client
`	ext
Les couches à pression sont disponibles
`

### Réponse LLM
`	ext
Je vois que les couches à pression sont disponibles 😊. Vous souhaitez :
- Commander ces couches ?
- Avoir plus d'informations sur ce modèle ?
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_X
- **prompt_expected_key**: JESSICA_PROMPT_X
- **prompt_ok**: True
- **gating_path**: prompt_x
- **segment_letter**: A
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 60

### Client
`	ext
Vous avez la marque Pampers
`

### Réponse LLM
`	ext
Je vois que vous mentionnez la marque Pampers 😊. Vous souhaitez :
- Commander des couches Pampers ?
- Avoir des informations sur nos produits Pampers ?
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.22009302933517058
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_X
- **prompt_expected_key**: JESSICA_PROMPT_X
- **prompt_ok**: True
- **gating_path**: prompt_x
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 61

### Client
`	ext
C'est quelle taille ça
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.7665896132368601
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 62

### Client
`	ext
Les couches nouveau-né vous avez
`

### Réponse LLM
`	ext
Je vois que vous vous intéressez aux couches nouveau-né 😊. Vous parlez des couches Pampers ou d'un autre produit en particulier ?
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_X
- **prompt_expected_key**: JESSICA_PROMPT_X
- **prompt_ok**: True
- **gating_path**: prompt_x
- **segment_letter**: A
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 63

### Client
`	ext
Vous avez des couches adultes
`

### Réponse LLM
`	ext
Je vois que vous vous intéressez aux couches adultes 😊. Vous souhaitez :
- Commander des couches adultes ?
- Avoir des informations sur leur disponibilité ?
- Connaître les tailles disponibles ?
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_X
- **prompt_expected_key**: JESSICA_PROMPT_X
- **prompt_ok**: True
- **gating_path**: prompt_x
- **segment_letter**: A
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 64

### Client
`	ext
Y'a des couches culottes
`

### Réponse LLM
`	ext
Je comprends votre recherche. Un conseiller vous guidera. 🚚
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: D
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 65

### Client
`	ext
Vous vendez quelle marque
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 66

### Client
`	ext
Les tailles disponibles
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commander. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.6
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 67

### Client
`	ext
Vous avez en stock actuellement
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PAIEMENT
- **confidence**: 0.18504436890764142
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 68

### Client
`	ext
C'est pour quel âge ces couches
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: hyde
- **segment_letter**: B
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 69

### Client
`	ext
Différence entre les modèles
`

### Réponse LLM
`	ext
Je comprends votre demande 😊. Vous parlez des différences entre les modèles de couches ou d'un autre produit ? Pour vous aider, envoyez-moi la photo du produit vu au live.
`

### Metrics
- **intent**: PAIEMENT
- **confidence**: 0.08547127265922273
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_X
- **prompt_expected_key**: JESSICA_PROMPT_X
- **prompt_ok**: True
- **gating_path**: prompt_x
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 70

### Client
`	ext
Je veux commander
`

### Réponse LLM
`	ext
Pour commencer, envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: ACHAT_COMMANDE
- **confidence**: 0.88
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: C
- **prefilter**: lexical_achat
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 71

### Client
`	ext
Je prends 5 paquets
`

### Réponse LLM
`	ext
Pour la livraison demain, les frais sont de 1000F pour Abidjan et 1500F pour les autres zones. Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: ACHAT_COMMANDE
- **confidence**: 0.88
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: lexical_achat
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 72

### Client
`	ext
Comment passer commande
`

### Réponse LLM
`	ext
Pour commencer, veuillez faire un dépôt de validation de 2000F sur le 0787360757 (Wave) et m'envoyer la capture. Ensuite, nous pourrons finaliser votre commande.
`

### Metrics
- **intent**: ACHAT_COMMANDE
- **confidence**: 0.88
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: lexical_achat
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 73

### Client
`	ext
Je veux acheter
`

### Réponse LLM
`	ext
J'aurais besoin d'un Dépôt de validation wave de 2000F au 0787360757 puis envoyez la capture.
`

### Metrics
- **intent**: ACHAT_COMMANDE
- **confidence**: 0.88
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: lexical_achat
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 74

### Client
`	ext
Envoie-moi 10 paquets
`

### Réponse LLM
`	ext
Les frais de livraison sont de 1000F pour votre zone. Livraison prévue demain. C'est noté. On vous livre où ? (commune et quartier)
`

### Metrics
- **intent**: ACHAT_COMMANDE
- **confidence**: 0.88
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: lexical_achat
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 75

### Client
`	ext
Je commande maintenant
`

### Réponse LLM
`	ext
Pour valider votre commande, veuillez effectuer un dépôt de validation de 2000F sur le 0787360757 (Wave) puis envoyez-moi la capture. On continue ?
`

### Metrics
- **intent**: ACHAT_COMMANDE
- **confidence**: 0.88
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: C
- **prefilter**: lexical_achat
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 76

### Client
`	ext
Comment faire pour acheter
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.2751792532017474
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 77

### Client
`	ext
Je vais prendre ça
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.9820768973288333
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 78

### Client
`	ext
J'en veux 3 paquets
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: ACHAT_COMMANDE
- **confidence**: 0.85
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_achat_quantity
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 79

### Client
`	ext
Je passe commande
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? J'aurais besoin d'un Dépôt de validation wave de 2000F au 0787360757 puis envoyez la capture.
`

### Metrics
- **intent**: ACHAT_COMMANDE
- **confidence**: 0.88
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: lexical_achat
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 80

### Client
`	ext
Réserve-moi 2 cartons
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.9105574445927096
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 81

### Client
`	ext
Je reviens pour commander
`

### Réponse LLM
`	ext
Pour commencer, j'aurais besoin d'un dépôt de validation Wave de 2000F au 0787360757 puis envoyez la capture.
`

### Metrics
- **intent**: ACHAT_COMMANDE
- **confidence**: 0.88
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: lexical_achat
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 82

### Client
`	ext
Vous livrez à Yopougon
`

### Réponse LLM
`	ext
Noté 👍 Livraison à Yopougon → 1500F 🚚
Livraison prévue demain.
Dernière info : votre numéro de téléphone ? 📞
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.82
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,zone,tel
- **prompt_used_key**: 
- **prompt_expected_key**: 
- **prompt_ok**: 
- **gating_path**: 
- **segment_letter**: 
- **prefilter**: lexical_livraison
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 83

### Client
`	ext
Comment se passe la livraison
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.82
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_C
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: lexical_livraison
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 84

### Client
`	ext
La livraison c'est combien
`

### Réponse LLM
`	ext
Les frais de livraison dépendent de votre zone/commune. Pouvez-vous me dire votre quartier (ex: Cocody, Yopougon, Abobo…) ?
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: PYTHON_SHORT_CIRCUIT
- **prompt_expected_key**: PYTHON_SHORT_CIRCUIT
- **prompt_ok**: True
- **gating_path**: 
- **segment_letter**: 
- **prefilter**: lexical_livraison_prix
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 85

### Client
`	ext
Vous livrez quand
`

### Réponse LLM
`	ext
Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.82
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_C
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: lexical_livraison
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 86

### Client
`	ext
Je veux être livré demain
`

### Réponse LLM
`	ext
Pour la livraison demain, les frais sont de 1000F et le délai est de 24h. Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.82
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_C
- **prompt_ok**: True
- **gating_path**: hyde
- **segment_letter**: C
- **prefilter**: lexical_livraison
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 87

### Client
`	ext
Livraison à Cocody possible
`

### Réponse LLM
`	ext
Noté 👍 Livraison à Cocody → 1500F 🚚
Livraison prévue demain.
Dernière info : votre numéro de téléphone ? 📞
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.82
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: 
- **prompt_expected_key**: 
- **prompt_ok**: 
- **gating_path**: 
- **segment_letter**: 
- **prefilter**: lexical_livraison
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 88

### Client
`	ext
Les frais de livraison
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.82
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_C
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: C
- **prefilter**: lexical_livraison
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 89

### Client
`	ext
Vous pouvez livrer ce soir
`

### Réponse LLM
`	ext
Je vois votre demande de livraison ce soir 😊. Pour vous répondre précisément :
- C'est pour une commande en cours ?
- Ou une nouvelle demande urgente ?
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.82
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_X
- **prompt_expected_key**: JESSICA_PROMPT_X
- **prompt_ok**: True
- **gating_path**: prompt_x
- **segment_letter**: A
- **prefilter**: lexical_livraison
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 90

### Client
`	ext
La livraison prend combien de temps
`

### Réponse LLM
`	ext
Les frais de livraison dépendent de votre zone/commune. Pouvez-vous me dire votre quartier (ex: Cocody, Yopougon, Abobo…) ?
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.85
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: PYTHON_SHORT_CIRCUIT
- **prompt_expected_key**: PYTHON_SHORT_CIRCUIT
- **prompt_ok**: True
- **gating_path**: 
- **segment_letter**: 
- **prefilter**: lexical_livraison_prix
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 91

### Client
`	ext
Je veux changer l'adresse de livraison
`

### Réponse LLM
`	ext
Je note votre demande de modification. Un conseiller humain va s'en charger.
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.82
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_C
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: D
- **prefilter**: lexical_livraison
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 92

### Client
`	ext
Vous acceptez quoi comme paiement
`

### Réponse LLM
`	ext
On accepte le paiement par Wave. Pour valider votre commande, envoyez un dépôt de 2000F au 0787360757 puis la capture. On continue ?
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.992325027427739
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_C
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 93

### Client
`	ext
Je peux payer avec Wave
`

### Réponse LLM
`	ext
Parfait, vous pouvez payer avec Wave. J'aurais besoin d'un Dépôt de validation wave de 2000F au 0787360757 puis envoyez la capture. Ensuite, on passera à la photo du produit.
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.5028372589329805
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_C
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 94

### Client
`	ext
Mode de paiement disponible
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? J'aurais besoin d'un Dépôt de validation wave de 2000F au 0787360757 puis envoyez la capture.
`

### Metrics
- **intent**: PAIEMENT
- **confidence**: 0.9971813478426684
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 95

### Client
`	ext
Vous prenez Orange Money
`

### Réponse LLM
`	ext
Pour le paiement, un dépôt de validation de 2000F est requis sur le 0787360757. Envoyez-moi la capture une fois effectué. 💳
`

### Metrics
- **intent**: PAIEMENT
- **confidence**: 0.996561786153557
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 96

### Client
`	ext
Paiement à la livraison possible
`

### Réponse LLM
`	ext
Pour les frais de livraison, c'est 500F pour Abidjan centre et 1000F pour les zones périphériques. Livraison demain avant 18h. Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: PAIEMENT
- **confidence**: 0.88
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_C
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: C
- **prefilter**: lexical_paiement_livraison
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 97

### Client
`	ext
Je paie comment
`

### Réponse LLM
`	ext
Pour commander, envoyez un dépôt de 2000F sur le 0787360757 + capture. Photo du produit + zone + numéro requis. 📸
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.020729081472413088
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 98

### Client
`	ext
MTN Money ça passe
`

### Réponse LLM
`	ext
MTN Money est accepté. Pour valider, envoyez un dépôt de 2000F au 0787360757 puis la capture. On continue ?
`

### Metrics
- **intent**: PAIEMENT
- **confidence**: 0.9763703409644456
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 99

### Client
`	ext
Vous acceptez les espèces
`

### Réponse LLM
`	ext
Je vois votre question sur les espèces 😊. Vous souhaitez confirmer un paiement en espèces pour votre commande en cours, ou vous informer sur nos options de paiement ?
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.9920599428018183
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_X
- **prompt_expected_key**: JESSICA_PROMPT_X
- **prompt_ok**: True
- **gating_path**: prompt_x
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 100

### Client
`	ext
Quel est votre numéro
`

### Réponse LLM
`	ext
Un conseiller vous contacte au 0787360757 pour votre demande. 📞
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.9
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_contact
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 101

### Client
`	ext
Je peux vous appeler
`

### Réponse LLM
`	ext
Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.9
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: lexical_contact
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 102

### Client
`	ext
Donnez-moi votre contact
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.0018555791162535888
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 103

### Client
`	ext
Comment vous contacter
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.992523060918441
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 104

### Client
`	ext
Votre WhatsApp
`

### Réponse LLM
`	ext
Bonjour ! Pour commencer, envoyez-moi la photo du produit vu au live pour valider votre commande 📸. Merci !
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.9
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: lexical_contact
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 105

### Client
`	ext
Je vous appelle mais pas de réponse
`

### Réponse LLM
`	ext
Envoyez-moi la photo du produit vu au live pour commencer 📸. On continue ?
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.9
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_A
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: C
- **prefilter**: lexical_contact
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 106

### Client
`	ext
C'est quel numéro pour vous joindre
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.9
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: lexical_contact
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 107

### Client
`	ext
Vos coordonnées s'il vous plaît
`

### Réponse LLM
`	ext
Pour nous joindre, contactez le 07873607357. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.9
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: A
- **prefilter**: lexical_contact
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 108

### Client
`	ext
Le paquet est abîmé
`

### Réponse LLM
`	ext
Je comprends votre inquiétude. Un collègue va vous recontacter rapidement. 🚚
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.95
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: D
- **prefilter**: human_handoff_sav_marker
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 109

### Client
`	ext
Les couches ne sont pas bonnes
`

### Réponse LLM
`	ext
Je comprends votre déception. Un conseiller va vous aider rapidement. 🚚
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.95
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: D
- **prefilter**: human_handoff_sav_marker
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 110

### Client
`	ext
Je n'ai pas reçu ma commande
`

### Réponse LLM
`	ext
Pour ce détail, contactez le 0787360757. On continue ? Envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.95
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_D
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: human_handoff_sav_marker
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 111

### Client
`	ext
Il y a un problème avec le colis
`

### Réponse LLM
`	ext
Je comprends votre inquiétude. Un collègue va vous recontacter rapidement. 🚚
`

### Metrics
- **intent**: CONTACT_COORDONNEES
- **confidence**: 0.864084859165525
- **mode**: COMMANDE
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: D
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 112

### Client
`	ext
Je veux retourner le produit
`

### Réponse LLM
`	ext
Envoyez la photo du produit + preuve de paiement (2000F) 📸
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.95
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: human_handoff_sav_marker
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 113

### Client
`	ext
Où est ma commande
`

### Réponse LLM
`	ext
Je comprends votre inquiétude. Un collègue va vous recontacter rapidement. 🚚
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.4860731226687232
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_LIGHT_D
- **prompt_ok**: False
- **gating_path**: light
- **segment_letter**: D
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 114

### Client
`	ext
Mon colis arrive quand
`

### Réponse LLM
`	ext
Je comprends votre inquiétude. Un collègue va vous recontacter rapidement. 🚚
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.28221946282678567
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: D
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 115

### Client
`	ext
Le livreur est parti
`

### Réponse LLM
`	ext
Je comprends votre inquiétude. Un collègue va vous recontacter rapidement. 🚚
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.2348696846500355
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_D
- **prompt_ok**: True
- **gating_path**: hyde
- **segment_letter**: D
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 116

### Client
`	ext
Je n'ai pas encore reçu
`

### Réponse LLM
`	ext
Votre livraison est prévue demain. Un collègue vous contactera pour plus de détails. 🚚
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.95
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_D
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: A
- **prefilter**: human_handoff_sav_marker
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 117

### Client
`	ext
Suivi de ma commande
`

### Réponse LLM
`	ext
Je comprends votre inquiétude. Un conseiller vous contactera rapidement. 🚚
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.9525013578809784
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_D
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: D
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 118

### Client
`	ext
C'est à quel niveau mon colis
`

### Réponse LLM
`	ext
Votre livraison est prévue pour demain. Pour finaliser, envoyez-moi la photo du produit vu au live pour commencer 📸
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.9827529634418904
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_C
- **prompt_expected_key**: JESSICA_PROMPT_A
- **prompt_ok**: False
- **gating_path**: standard
- **segment_letter**: C
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 119

### Client
`	ext
Le livreur ne répond pas
`

### Réponse LLM
`	ext
Je comprends votre inquiétude. Un conseiller vous contactera rapidement. 🚚
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.7301450228947471
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_D
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: D
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 120

### Client
`	ext
Ma commande a été expédiée
`

### Réponse LLM
`	ext
Je comprends votre inquiétude. Un conseiller vous contactera rapidement. 🚚
`

### Metrics
- **intent**: COMMANDE_EXISTANTE
- **confidence**: 0.9727178985657841
- **mode**: RECEPTION_SAV
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_D
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: D
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 121

### Client
`	ext
Vous avez en stock actuellement
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: LIVRAISON
- **confidence**: 0.006458513121436771
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 122

### Client
`	ext
Vous avez quoi en stock
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.86
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_produit
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 123

### Client
`	ext
Vous avez en stock
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.2581422602653694
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 124

### Client
`	ext
C'est disponible maintenant
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PAIEMENT
- **confidence**: 0.29809258414593026
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: hyde
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 125

### Client
`	ext
C'est en rupture ou pas
`

### Réponse LLM
`	ext
Pour les stocks, contactez le live au 0787360757. Souhaitez-vous passer commande ? 📸
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.2481553696029737
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_A
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 126

### Client
`	ext
Il en reste combien
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.82
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: lexical_stock
- **router_name**: prefilter
- **router_source**: setfit_prefilter

---

## Turn 127

### Client
`	ext
Quand ça revient en stock
`

### Réponse LLM
`	ext
Je comprends votre question sur le stock 😊. Vous parlez d'un produit spécifique ou d'une catégorie en particulier ?
`

### Metrics
- **intent**: PAIEMENT
- **confidence**: 0.3835311883494713
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_X
- **prompt_expected_key**: JESSICA_PROMPT_X
- **prompt_ok**: True
- **gating_path**: prompt_x
- **segment_letter**: A
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 128

### Client
`	ext
Vous n'avez plus ce modèle
`

### Réponse LLM
`	ext
Je comprends votre inquiétude. Un conseiller va vous recontacter rapidement. 🚚
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.6
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_D
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: False
- **gating_path**: hyde
- **segment_letter**: D
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 129

### Client
`	ext
C'est dispo pour aujourd'hui
`

### Réponse LLM
`	ext
Pour les prix et le stock, contactez le live. Revenez vers moi quand vous serez prêt pour que j'enregistre votre commande. 📸
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.8406996647256868
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: hyde
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

## Turn 130

### Client
`	ext
Vous avez le produit X en stock
`

### Réponse LLM
`	ext
Envoyez la photo du produit vu au live pour commencer 📸.
`

### Metrics
- **intent**: PRODUIT_GLOBAL
- **confidence**: 0.9950219479698876
- **mode**: GUIDEUR
- **missing_fields**: photo,paiement,tel
- **prompt_used_key**: JESSICA_PROMPT_B
- **prompt_expected_key**: JESSICA_PROMPT_B
- **prompt_ok**: True
- **gating_path**: standard
- **segment_letter**: B
- **prefilter**: 
- **router_name**: setfit_v4
- **router_source**: setfit

---

