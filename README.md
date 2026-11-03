# SmartStore - Le Vendeur WhatsApp Intelligent (Dantokpa)

Agent conversationnel intelligent propulsé par RodiumAI, intégré à FastAPI et connecté à WhatsApp via Green API, conçu pour automatiser les ventes d'une boutique de pagnes et d'accessoires au marché Dantokpa (Cotonou, Bénin).

---

## Le Projet

Afi tient une boutique à Dantokpa et reçoit des commandes à toute heure, notamment de la diaspora. Cet agent permet de :
1. **Répondre aux questions** sur les produits, les prix (en FCFA) et le catalogue.
2. **Vérifier le stock** en temps réel avant de promettre un article (gestion des ruptures et proposition d'alternatives).
3. **Calculer les frais de livraison** selon la zone (Cotonou, Calavi, Porto-Novo, etc.).
4. **Convertir les devises** en temps réel (EUR, USD, NGN, etc.) via une API de taux réels.
5. **Gérer les commandes avec validation humaine** : enregistrement en statut `pending`, notification sur le WhatsApp d'Afi, validation/rejet par Afi via WhatsApp (`OUI <id>` / `NON <id>`), décrémentation automatique du stock et information au client.

---

## Outils de l'Agent

L'agent dispose de 5 outils principaux (norme verbe-objet) :
- `chercher_produits` : Recherche les produits par mot-clé dans le catalogue.
- `verifier_stock` : Vérifie la disponibilité et la quantité exacte d'une référence.
- `frais_livraison` : Calcule les frais et délais selon la zone géographique.
- `convertir_devise` : Convertit les montants FCFA vers d'autres devises.
- `creer_commande` : Enregistre la commande (génère un devis ou une demande en attente).

---

## Architecture Technique

- **Framework Web / API :** FastAPI (Python)
- **Modèle LLM :** API RodiumAI (`/chat/completions`)
- **Stockage Persistant :** Fichiers JSON (stocks, commandes)
- **Canal de Communication :** WhatsApp via Green API (Webhooks asynchrones)
- **Sécurité & Garde-fous :** 
  - Jeton de sécurité pour les webhooks (`Authorization`)
  - Dédoublonnage des messages entrants (`receiptId`)
  - Limite d'étapes (`max_steps`) et système d'évaluation à double niveau (règles en code + juge LLM) pour interdire l'invention de chiffres.

---

## Installation et Lancement

### 1. Prérequis
- Python 3.10+
- Un compte [Green API](https://green-api.com) configuré avec une instance WhatsApp.
- Une clé API RodiumAI.

### 2. Cloner le dépôt et installer les dépendances
```bash
git clone https://github.com/Lucreine/smartstore.git
cd smartstore
# Si tu utilises uv ou pip :
pip install -e .