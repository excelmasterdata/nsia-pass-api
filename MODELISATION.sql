-- ===============================================
-- NSIA PASS Congo - Modélisation SQL Spécialisée
-- Contexte: Produits PASS via Mobile Money
-- ===============================================

-- ===============================================
-- 1. TABLE PRODUITS_PASS (Catalogue PASS)
-- ===============================================

CREATE TABLE produits_pass (
    id SERIAL PRIMARY KEY,
    
    -- Identification produit
    code_pass VARCHAR(20) UNIQUE NOT NULL,  -- KIMIA, BATELA, SALISA
    nom_pass VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Tarification PASS (simple)
    prix_minimum DECIMAL(10,2) DEFAULT 100.00,  -- À partir de 100 FCFA
    prix_maximum DECIMAL(10,2),
    
    -- Caractéristiques PASS
    nombre_beneficiaires_max INTEGER DEFAULT 6,
    duree_validite_jours INTEGER DEFAULT 365,
    
    -- Garanties incluses (JSON pour flexibilité)
    garanties JSONB NOT NULL,  -- Ex: {"accident": true, "frais_funeraires": true}
    
    -- Souscription
    souscription_mobile_money BOOLEAN DEFAULT TRUE,
    code_ussd VARCHAR(20),  -- Ex: *128*6*6*1#
    
    -- Métadonnées
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    statut VARCHAR(20) DEFAULT 'actif' CHECK (statut IN ('actif', 'inactif', 'archive')),
    
    -- Contraintes
    CHECK (prix_minimum > 0),
    CHECK (nombre_beneficiaires_max > 0)
);

-- Données initiales des produits PASS
INSERT INTO produits_pass (code_pass, nom_pass, description, garanties, code_ussd) VALUES
('KIMIA', 'PASS KIMIA', 'Pack accident + frais funéraires via Airtel Money', 
 '{"individuel_accident": true, "frais_medicaux": true, "indemnite_journaliere": true, "mosungui_funeraires": true}', 
 '*128*6*6*1#'),
('BATELA', 'PASS BATELA', 'Épargne retraite + frais funéraires', 
 '{"epargne_retraite": true, "taux_rendement": 3.5, "mosungui_funeraires": true}', 
 '*128*6*6*1#'),
('SALISA', 'PASS SALISA', 'Forfaits hospitaliers + frais funéraires', 
 '{"forfaits_hospitaliers": true, "indemnite_journaliere": true, "mosungui_funeraires": true}', 
 '*128*6*6*1#');

-- ===============================================
-- 2. TABLE CLIENTS_PASS (Souscripteurs PASS)
-- ===============================================

CREATE TABLE clients_pass (
    id SERIAL PRIMARY KEY,
    
    -- Informations personnelles (simplifiées pour PASS)
    nom VARCHAR(60) NOT NULL,
    prenom VARCHAR(60) NOT NULL,
    telephone VARCHAR(25) UNIQUE NOT NULL,  -- Clé principale pour mobile money
    date_naissance DATE,
    lieu_naissance VARCHAR(100),
    adresse TEXT,
    
    -- Spécifique Mobile Money
    operateur_mobile VARCHAR(20) CHECK (operateur_mobile IN ('airtel', 'mtn')),
    numero_mobile_money VARCHAR(25),  -- Peut être différent du téléphone principal
    
    -- Métadonnées PASS
    date_premiere_souscription TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    nombre_souscriptions_actives INTEGER DEFAULT 0,
    valeur_totale_souscriptions DECIMAL(12,2) DEFAULT 0.00,
    
    -- Statut
    statut VARCHAR(20) DEFAULT 'actif' CHECK (statut IN ('actif', 'inactif', 'suspendu')),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Index pour performance
    UNIQUE(telephone)
);

CREATE INDEX idx_clients_pass_telephone ON clients_pass(telephone);
CREATE INDEX idx_clients_pass_operateur ON clients_pass(operateur_mobile);

-- ===============================================
-- 3. TABLE SOUSCRIPTIONS_PASS (Demandes PASS)
-- ===============================================

CREATE TABLE souscriptions_pass (
    id SERIAL PRIMARY KEY,
    
    -- Relations
    client_id INTEGER NOT NULL REFERENCES clients_pass(id) ON DELETE RESTRICT,
    produit_pass_id INTEGER NOT NULL REFERENCES produits_pass(id) ON DELETE RESTRICT,
    
    -- Identification unique
    numero_souscription VARCHAR(30) UNIQUE NOT NULL,  -- Auto-généré: PASS-KIMIA-2024-001234
    
    -- Montant et paiement
    montant_souscription DECIMAL(10,2) NOT NULL,
    periodicite VARCHAR(20) DEFAULT 'mensuelle' CHECK (periodicite IN 
        ('hebdomadaire', 'mensuelle', 'unique')),
    
    -- Workflow PASS (simplifié)
    statut VARCHAR(30) DEFAULT 'en_cours' CHECK (statut IN 
        ('en_cours', 'activee', 'suspendue', 'expiree', 'annulee')),
    
    -- Validation automatique (Mobile Money)
    validation_automatique BOOLEAN DEFAULT TRUE,
    paiement_initial_recu BOOLEAN DEFAULT FALSE,
    
    -- Dates importantes
    date_souscription TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_activation TIMESTAMP,
    date_expiration DATE,  -- Calculée automatiquement
    
    -- Mobile Money spécifique
    transaction_mobile_money VARCHAR(50),
    operateur_paiement VARCHAR(20),
    
    -- Métadonnées
    commentaires TEXT,
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Contraintes
    CHECK (montant_souscription >= 100.00),  -- Minimum 100 FCFA
    CHECK (
        (statut = 'activee' AND date_activation IS NOT NULL AND date_expiration IS NOT NULL) OR
        (statut != 'activee')
    )
);

CREATE INDEX idx_souscriptions_pass_client ON souscriptions_pass(client_id);
CREATE INDEX idx_souscriptions_pass_numero ON souscriptions_pass(numero_souscription);
CREATE INDEX idx_souscriptions_pass_statut ON souscriptions_pass(statut);

-- ===============================================
-- 4. TABLE BENEFICIAIRES_PASS (Jusqu'à 6 par souscription)
-- ===============================================

CREATE TABLE beneficiaires_pass (
    id SERIAL PRIMARY KEY,
    
    -- Relations
    souscription_pass_id INTEGER NOT NULL REFERENCES souscriptions_pass(id) ON DELETE CASCADE,
    
    -- Informations bénéficiaire
    nom VARCHAR(60) NOT NULL,
    prenom VARCHAR(60) NOT NULL,
    telephone VARCHAR(25),
    relation_souscripteur VARCHAR(30) NOT NULL,  -- conjoint, enfant, parent, ami, etc.
    date_naissance DATE,
    
    -- Priorité (pour les prestations)
    ordre_priorite INTEGER DEFAULT 1,
    
    -- Statut
    statut VARCHAR(20) DEFAULT 'actif' CHECK (statut IN ('actif', 'inactif', 'decede')),
    date_ajout TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Contraintes
    CHECK (ordre_priorite >= 1 AND ordre_priorite <= 6),
    UNIQUE(souscription_pass_id, ordre_priorite)
);

-- Contrainte: Maximum 6 bénéficiaires par souscription
CREATE OR REPLACE FUNCTION check_max_beneficiaires()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM beneficiaires_pass WHERE souscription_pass_id = NEW.souscription_pass_id) >= 6 THEN
        RAISE EXCEPTION 'Maximum 6 bénéficiaires autorisés par souscription PASS';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_max_beneficiaires
    BEFORE INSERT ON beneficiaires_pass
    FOR EACH ROW
    EXECUTE FUNCTION check_max_beneficiaires();

-- ===============================================
-- 5. TABLE PAIEMENTS_PASS (Mobile Money)
-- ===============================================

CREATE TABLE paiements_pass (
    id SERIAL PRIMARY KEY,
    
    -- Relations
    souscription_pass_id INTEGER NOT NULL REFERENCES souscriptions_pass(id) ON DELETE RESTRICT,
    client_id INTEGER NOT NULL REFERENCES clients_pass(id) ON DELETE RESTRICT,
    
    -- Identification paiement
    numero_transaction VARCHAR(50) UNIQUE NOT NULL,
    reference_mobile_money VARCHAR(100),  -- Référence opérateur
    
    -- Montant
    montant DECIMAL(10,2) NOT NULL,
    frais_transaction DECIMAL(8,2) DEFAULT 0.00,
    montant_net DECIMAL(10,2) GENERATED ALWAYS AS (montant - frais_transaction) STORED,
    
    -- Mobile Money spécifique
    operateur VARCHAR(20) NOT NULL CHECK (operateur IN ('airtel_money', 'mtn_money')),
    numero_payeur VARCHAR(25) NOT NULL,
    code_confirmation VARCHAR(20),
    
    -- Statut paiement
    statut VARCHAR(30) DEFAULT 'en_cours' CHECK (statut IN 
        ('en_cours', 'succes', 'echec', 'rembourse', 'en_verification')),
    motif_echec TEXT,
    
    -- Dates
    date_paiement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_confirmation TIMESTAMP,
    date_comptabilisation TIMESTAMP,
    
    -- Métadonnées
    type_paiement VARCHAR(20) DEFAULT 'cotisation' CHECK (type_paiement IN 
        ('souscription_initiale', 'cotisation', 'renouvellement', 'rattrapage')),
    
    -- Contraintes
    CHECK (montant > 0),
    CHECK (frais_transaction >= 0),
    CHECK (
        (statut = 'succes' AND date_confirmation IS NOT NULL) OR
        (statut = 'echec' AND motif_echec IS NOT NULL) OR
        (statut NOT IN ('succes', 'echec'))
    )
);

CREATE INDEX idx_paiements_pass_souscription ON paiements_pass(souscription_pass_id);
CREATE INDEX idx_paiements_pass_transaction ON paiements_pass(numero_transaction);
CREATE INDEX idx_paiements_pass_operateur ON paiements_pass(operateur);

-- ===============================================
-- 6. TABLE SINISTRES_PASS (Déclarations et prestations)
-- ===============================================

CREATE TABLE sinistres_pass (
    id SERIAL PRIMARY KEY,
    
    -- Relations
    souscription_pass_id INTEGER NOT NULL REFERENCES souscriptions_pass(id) ON DELETE RESTRICT,
    beneficiaire_id INTEGER REFERENCES beneficiaires_pass(id) ON DELETE SET NULL,
    
    -- Identification
    numero_sinistre VARCHAR(30) UNIQUE NOT NULL,
    
    -- Type de sinistre selon le produit PASS
    type_sinistre VARCHAR(50) NOT NULL CHECK (type_sinistre IN 
        ('accident', 'hospitalisation', 'deces', 'frais_medicaux', 'indemnite_journaliere')),
    
    -- Description
    description_sinistre TEXT NOT NULL,
    lieu_sinistre VARCHAR(200),
    date_sinistre DATE NOT NULL,
    
    -- Montant demandé/accordé
    montant_demande DECIMAL(12,2),
    montant_accorde DECIMAL(12,2) DEFAULT 0.00,
    
    -- Workflow sinistre
    statut VARCHAR(30) DEFAULT 'declare' CHECK (statut IN 
        ('declare', 'en_instruction', 'valide', 'rejete', 'paye', 'clos')),
    motif_rejet TEXT,
    
    -- Documents
    documents_requis JSONB,  -- Liste des documents demandés
    documents_recus JSONB,   -- Documents effectivement reçus
    
    -- Dates de traitement
    date_declaration TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_validation TIMESTAMP,
    date_paiement TIMESTAMP,
    
    -- Métadonnées
    commentaires_instruction TEXT,
    instructeur_id INTEGER,  -- Référence vers un agent NSIA si nécessaire
    
    -- Contraintes
    CHECK (date_sinistre <= CURRENT_DATE),
    CHECK (montant_accorde <= montant_demande OR montant_demande IS NULL),
    CHECK (
        (statut = 'valide' AND montant_accorde > 0) OR
        (statut = 'rejete' AND motif_rejet IS NOT NULL) OR
        (statut NOT IN ('valide', 'rejete'))
    )
);

CREATE INDEX idx_sinistres_pass_souscription ON sinistres_pass(souscription_pass_id);
CREATE INDEX idx_sinistres_pass_numero ON sinistres_pass(numero_sinistre);
CREATE INDEX idx_sinistres_pass_statut ON sinistres_pass(statut);

-- ===============================================
-- 7. TRIGGERS AUTOMATIQUES POUR PASS
-- ===============================================

-- Trigger pour calculer automatiquement la date d'expiration
CREATE OR REPLACE FUNCTION set_date_expiration_pass()
RETURNS TRIGGER AS $$
DECLARE
    duree_validite INTEGER;
BEGIN
    -- Récupérer la durée de validité du produit PASS
    SELECT duree_validite_jours INTO duree_validite
    FROM produits_pass
    WHERE id = NEW.produit_pass_id;
    
    -- Si activation, calculer l'expiration
    IF NEW.statut = 'activee' AND OLD.statut != 'activee' THEN
        NEW.date_expiration := CURRENT_DATE + INTERVAL '1 day' * duree_validite;
        NEW.date_activation := CURRENT_TIMESTAMP;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_expiration_pass
    BEFORE UPDATE ON souscriptions_pass
    FOR EACH ROW
    EXECUTE FUNCTION set_date_expiration_pass();

-- Trigger pour mettre à jour les statistiques client
CREATE OR REPLACE FUNCTION update_stats_client_pass()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        UPDATE clients_pass 
        SET 
            nombre_souscriptions_actives = (
                SELECT COUNT(*) 
                FROM souscriptions_pass 
                WHERE client_id = NEW.client_id 
                  AND statut = 'activee'
            ),
            valeur_totale_souscriptions = (
                SELECT COALESCE(SUM(montant_souscription), 0)
                FROM souscriptions_pass 
                WHERE client_id = NEW.client_id 
                  AND statut IN ('activee', 'en_cours')
            ),
            date_modification = CURRENT_TIMESTAMP
        WHERE id = NEW.client_id;
        
        RETURN NEW;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_stats_client_pass
    AFTER INSERT OR UPDATE ON souscriptions_pass
    FOR EACH ROW
    EXECUTE FUNCTION update_stats_client_pass();

-- ===============================================
-- 8. VUES MÉTIER POUR L'API BORNE PASS
-- ===============================================

-- Vue dashboard client PASS
CREATE OR REPLACE VIEW vue_dashboard_pass AS
SELECT 
    c.id as client_id,
    c.nom,
    c.prenom,
    c.telephone,
    c.operateur_mobile,
    c.nombre_souscriptions_actives,
    c.valeur_totale_souscriptions,
    
    -- Statistiques souscriptions
    COUNT(s.id) as total_souscriptions,
    COUNT(CASE WHEN s.statut = 'activee' THEN 1 END) as souscriptions_actives,
    COUNT(CASE WHEN s.statut = 'expiree' THEN 1 END) as souscriptions_expirees,
    
    -- Informations paiements
    COALESCE(SUM(CASE WHEN p.statut = 'succes' THEN p.montant_net ELSE 0 END), 0) as total_paye,
    MAX(p.date_paiement) as dernier_paiement,
    
    -- Dernière activité
    GREATEST(c.date_modification, MAX(s.date_modification)) as derniere_activite
    
FROM clients_pass c
LEFT JOIN souscriptions_pass s ON c.id = s.client_id
LEFT JOIN paiements_pass p ON s.id = p.souscription_pass_id
GROUP BY c.id, c.nom, c.prenom, c.telephone, c.operateur_mobile, 
         c.nombre_souscriptions_actives, c.valeur_totale_souscriptions;

-- Vue détail souscription PASS avec bénéficiaires
CREATE OR REPLACE VIEW vue_souscriptions_pass_completes AS
SELECT 
    s.id,
    s.numero_souscription,
    s.montant_souscription,
    s.periodicite,
    s.statut,
    s.date_souscription,
    s.date_activation,
    s.date_expiration,
    
    -- Informations produit
    pp.code_pass,
    pp.nom_pass,
    pp.garanties,
    
    -- Informations client
    c.nom as client_nom,
    c.prenom as client_prenom,
    c.telephone as client_telephone,
    
    -- Bénéficiaires (agrégés)
    COUNT(b.id) as nombre_beneficiaires,
    JSON_AGG(
        JSON_BUILD_OBJECT(
            'nom', b.nom,
            'prenom', b.prenom,
            'relation', b.relation_souscripteur,
            'ordre', b.ordre_priorite
        ) ORDER BY b.ordre_priorite
    ) as beneficiaires,
    
    -- Paiements
    COUNT(p.id) as nombre_paiements,
    COALESCE(SUM(CASE WHEN p.statut = 'succes' THEN p.montant_net ELSE 0 END), 0) as total_paye
    
FROM souscriptions_pass s
JOIN produits_pass pp ON s.produit_pass_id = pp.id
JOIN clients_pass c ON s.client_id = c.id
LEFT JOIN beneficiaires_pass b ON s.id = b.souscription_pass_id
LEFT JOIN paiements_pass p ON s.id = p.souscription_pass_id
GROUP BY s.id, s.numero_souscription, s.montant_souscription, s.periodicite, s.statut,
         s.date_souscription, s.date_activation, s.date_expiration,
         pp.code_pass, pp.nom_pass, pp.garanties,
         c.nom, c.prenom, c.telephone;

-- ===============================================
-- 9. FONCTIONS MÉTIER SPÉCIFIQUES PASS
-- ===============================================

-- Fonction pour authentifier un client PASS sur la borne
CREATE OR REPLACE FUNCTION authentifier_client_pass(
    p_numero_souscription VARCHAR(30),
    p_telephone VARCHAR(25)
)
RETURNS TABLE (
    client_id INTEGER,
    nom VARCHAR(60),
    prenom VARCHAR(60),
    telephone VARCHAR(25),
    souscription_valide BOOLEAN,
    nombre_souscriptions INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.nom,
        c.prenom,
        c.telephone,
        (s.statut = 'activee' AND s.date_expiration > CURRENT_DATE) as souscription_valide,
        c.nombre_souscriptions_actives
    FROM clients_pass c
    JOIN souscriptions_pass s ON c.id = s.client_id
    WHERE s.numero_souscription = p_numero_souscription
      AND c.telephone = p_telephone
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- ===============================================
-- 10. DONNÉES DE TEST PASS
-- ===============================================

-- Client de test Congo
INSERT INTO clients_pass (nom, prenom, telephone, operateur_mobile, numero_mobile_money) VALUES
('KONGO', 'Jean Baptiste', '+242061234567', 'airtel', '+242061234567'),
('MOUKOKO', 'Marie Claire', '+242059876543', 'mtn', '+242059876543'),
('NGOUABI', 'Pierre', '+242042345678', 'mtn', '+242042345678');

-- Souscriptions de test
INSERT INTO souscriptions_pass (
    client_id, produit_pass_id, numero_souscription, montant_souscription, 
    statut, date_activation, date_expiration
) VALUES 
(1, 1, 'PASS-KIMIA-2024-001', 5000.00, 'activee', CURRENT_TIMESTAMP, CURRENT_DATE + INTERVAL '365 days'),
(1, 2, 'PASS-BATELA-2024-001', 10000.00, 'activee', CURRENT_TIMESTAMP, CURRENT_DATE + INTERVAL '365 days'),
(2, 3, 'PASS-SALISA-2024-001', 7500.00, 'activee', CURRENT_TIMESTAMP, CURRENT_DATE + INTERVAL '365 days');

-- Bénéficiaires de test
INSERT INTO beneficiaires_pass (souscription_pass_id, nom, prenom, relation_souscripteur, ordre_priorite) VALUES
(1, 'KONGO', 'Marie', 'conjoint', 1),
(1, 'KONGO', 'Junior', 'enfant', 2),
(2, 'KONGO', 'Marie', 'conjoint', 1),
(3, 'MOUKOKO', 'André', 'enfant', 1);

-- Paiements de test
INSERT INTO paiements_pass (
    souscription_pass_id, client_id, numero_transaction, montant, 
    operateur, numero_payeur, statut, date_confirmation
) VALUES
(1, 1, 'AIRTEL-2024-12345', 5000.00, 'airtel_money', '+242061234567', 'succes', CURRENT_TIMESTAMP),
(2, 1, 'AIRTEL-2024-12346', 10000.00, 'airtel_money', '+242061234567', 'succes', CURRENT_TIMESTAMP),
(3, 2, 'MTN-2024-54321', 7500.00, 'mtn_money', '+242059876543', 'succes', CURRENT_TIMESTAMP);