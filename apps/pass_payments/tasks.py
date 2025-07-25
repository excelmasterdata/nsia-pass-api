# apps/pass_payments/tasks.py

from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from datetime import timedelta

from .models import PaiementPass
from apps.mtn_integration.models import TransactionMTN
from apps.airtel_integration.models import TransactionAirtel
from apps.mtn_integration.services import MTNMobileMoneyService
from apps.airtel_integration.services import AirtelMoneyService
from apps.pass_clients.services import SouscriptionPassService

logger = get_task_logger(__name__)

@shared_task(bind=True)
def monitor_pending_payments(self):
    """
    Tâche périodique qui vérifie le statut des paiements en cours
    Exécutée toutes les 30 secondes
    """
    try:
        logger.info("Début du monitoring des paiements en cours...")
        
        # Compteurs
        mtn_checked = 0
        airtel_checked = 0
        mtn_updated = 0
        airtel_updated = 0
        
        # Vérifier les transactions MTN en attente
        pending_mtn = TransactionMTN.objects.filter(
            statut__in=['initiated', 'pending'],
            date_creation__gte=timezone.now() - timedelta(minutes=10)  # Max 10 minutes
        )
        
        logger.info(f"📱 {pending_mtn.count()} transactions MTN à vérifier")
        
        for transaction in pending_mtn:
            try:
                updated = check_mtn_transaction_status(transaction)
                if updated:
                    mtn_updated += 1
                mtn_checked += 1
            except Exception as e:
                logger.error(f"❌ Erreur MTN {transaction.external_id}: {e}")
        
        # Vérifier les transactions Airtel en attente
        pending_airtel = TransactionAirtel.objects.filter(
            statut__in=['initiated', 'pending'],
            date_creation__gte=timezone.now() - timedelta(minutes=10)  # Max 10 minutes
        )
        
        logger.info(f"📱 {pending_airtel.count()} transactions Airtel à vérifier")
        
        for transaction in pending_airtel:
            try:
                updated = check_airtel_transaction_status(transaction)
                if updated:
                    airtel_updated += 1
                airtel_checked += 1
            except Exception as e:
                logger.error(f"❌ Erreur Airtel {transaction.external_id}: {e}")
        
        # Log du résumé
        logger.info(
            f"Monitoring terminé - "
            f"MTN: {mtn_checked} vérifiées, {mtn_updated} mises à jour | "
            f"Airtel: {airtel_checked} vérifiées, {airtel_updated} mises à jour"
        )
        
        return {
            'success': True,
            'mtn_checked': mtn_checked,
            'mtn_updated': mtn_updated,
            'airtel_checked': airtel_checked,
            'airtel_updated': airtel_updated
        }
        
    except Exception as e:
        logger.error(f"💥 Erreur générale monitoring: {e}")
        return {'success': False, 'error': str(e)}

def check_mtn_transaction_status(transaction):
    """Vérifie le statut d'une transaction MTN"""
    try:
        if not transaction.financial_transaction_id:
            logger.warning(f"⚠️ MTN {transaction.external_id}: Pas de financial_transaction_id")
            return False
        
        mtn_service = MTNMobileMoneyService()
        result = mtn_service.check_payment_status(transaction.financial_transaction_id)
        
        if not result.get('success'):
            logger.warning(f"⚠️ MTN {transaction.external_id}: Impossible de vérifier le statut")
            return False
        
        mtn_status = result.get('status')
        previous_status = transaction.statut
        
        # Mapper le statut MTN
        if mtn_status == 'SUCCESSFUL':
            transaction.statut = 'successful'
            if transaction.paiement_pass:
                paiement = transaction.paiement_pass
                paiement.statut = 'succes'
                paiement.date_confirmation = timezone.now()
                paiement.code_confirmation = result.get('financial_transaction_id', '')
                paiement.save()
                
                # ✅ NOUVEAU : Activer la souscription si paiement initial
                if paiement.type_paiement == 'souscription_initiale':
                    try:
                        resultat_activation = SouscriptionPassService.activer_souscription(
                            paiement.souscription_pass.id
                        )
                        logger.info(
                            f"🎉 Souscription activée - Police: {resultat_activation['numero_police']}"
                        )
                    except Exception as e:
                        logger.error(f"❌ Erreur activation souscription: {e}")
                
        elif mtn_status == 'FAILED':
            transaction.statut = 'failed'
            transaction.status_reason = result.get('reason', 'Paiement MTN échoué')
            if transaction.paiement_pass:
                transaction.paiement_pass.statut = 'echec'
                transaction.paiement_pass.motif_echec = transaction.status_reason
                transaction.paiement_pass.save()
                
        elif mtn_status == 'PENDING':
            transaction.statut = 'pending'
        
        # Sauvegarder si changement
        if transaction.statut != previous_status:
            transaction.response_payload = result
            transaction.save()
            logger.info(f"🔄 MTN {transaction.external_id}: {previous_status} → {transaction.statut}")
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"❌ Erreur vérification MTN {transaction.external_id}: {e}")
        return False

# Dans apps/pass_payments/tasks.py - Debug encore plus détaillé

def check_airtel_transaction_status(transaction):
    """Vérifie le statut d'une transaction Airtel"""
    try:
        if not transaction.airtel_transaction_id:
            logger.warning(f"⚠️ Airtel {transaction.external_id}: Pas d'airtel_transaction_id")
            return False
        
        airtel_service = AirtelMoneyService()
        result = airtel_service.check_payment_status(transaction.airtel_transaction_id)
        
        if not result.get('success'):
            logger.warning(f"⚠️ Airtel {transaction.external_id}: API indisponible - {result.get('error')}")
            return check_airtel_by_timeout(transaction)
        
        airtel_status = result.get('status')
        previous_status = transaction.statut
        
        if airtel_status == 'SUCCESSFUL':
            logger.info(f"🎯 Mise à jour Airtel {transaction.external_id}: {previous_status} → successful")
            
            # ✅ ESSAYER UNE MISE À JOUR MINIMALE D'ABORD
            try:
                # Test 1: Juste le statut
                logger.info("   Test 1: Mise à jour statut uniquement")
                transaction.statut = 'successful'
                transaction.save(update_fields=['statut'])
                logger.info("   ✅ Statut mis à jour avec succès")
                
                # Test 2: Ajouter response_payload
                logger.info("   Test 2: Ajout response_payload")
                transaction.response_payload = result
                transaction.save(update_fields=['response_payload'])
                logger.info("   ✅ Response_payload mis à jour avec succès")
                
            except Exception as save_error:
                logger.error(f"   ❌ Erreur lors de la sauvegarde: {save_error}")
                
                # Debug SQL si possible
                logger.info("   🔍 Debug SQL détaillé:")
                try:
                    from django.db import connection
                    logger.info(f"   Database: {connection.settings_dict}")
                except:
                    pass
                
                # Essayer sans response_payload
                try:
                    logger.info("   Test 3: Mise à jour sans response_payload")
                    transaction.statut = 'successful'
                    transaction.response_payload = None  # Enlever le JSON
                    transaction.save()
                    logger.info("   ✅ Sauvegarde sans response_payload réussie")
                except Exception as minimal_error:
                    logger.error(f"   ❌ Même erreur sans response_payload: {minimal_error}")
                    
                    # Essayer avec une transaction Django fraîche
                    try:
                        logger.info("   Test 4: Recharger depuis la DB")
                        fresh_transaction = TransactionAirtel.objects.get(id=transaction.id)
                        fresh_transaction.statut = 'successful'
                        fresh_transaction.save()
                        logger.info("   ✅ Sauvegarde avec objet rechargé réussie")
                    except Exception as fresh_error:
                        logger.error(f"   ❌ Erreur avec objet rechargé: {fresh_error}")
                        return False
            
            # Mise à jour du paiement seulement si transaction mise à jour
            if transaction.paiement_pass:
                paiement = transaction.paiement_pass
                paiement.statut = 'succes'
                paiement.date_confirmation = timezone.now()
                paiement.code_confirmation = transaction.airtel_transaction_id
                paiement.save()
                
                # Activer la souscription si paiement initial
                if paiement.type_paiement == 'souscription_initiale':
                    try:
                        resultat_activation = SouscriptionPassService.activer_souscription(
                            paiement.souscription_pass.id
                        )
                        logger.info(
                            f"🎉 Souscription Airtel activée - Police: {resultat_activation['numero_police']}"
                        )
                    except Exception as e:
                        logger.error(f"❌ Erreur activation souscription Airtel: {e}")
            
            logger.info(f"🔄 Airtel {transaction.external_id}: Mise à jour terminée avec succès")
            return True
                        
        elif airtel_status == 'FAILED':
            transaction.statut = 'failed'
            transaction.status_reason = result.get('reason', 'Paiement Airtel échoué')[:190]  # Tronquer
            transaction.save()
            
            if transaction.paiement_pass:
                transaction.paiement_pass.statut = 'echec'
                transaction.paiement_pass.motif_echec = transaction.status_reason
                transaction.paiement_pass.save()
                
        elif airtel_status == 'PENDING':
            # Pas de changement nécessaire
            transaction.statut = 'pending'
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Erreur vérification Airtel {transaction.external_id}: {e}")
        return check_airtel_by_timeout(transaction)


def check_airtel_by_timeout(transaction):
    """Logique de fallback basée sur le timeout (2 minutes minimum)"""
    time_elapsed = timezone.now() - transaction.date_creation
    previous_status = transaction.statut
    
    # Attendre au moins 2 minutes avant de considérer comme réussi
    if time_elapsed > timedelta(minutes=2) and transaction.statut == 'pending':
        logger.info(f"⏰ Airtel {transaction.external_id}: Validation par timeout (API indisponible)")
        
        transaction.statut = 'successful'
        if transaction.paiement_pass:
            paiement = transaction.paiement_pass
            paiement.statut = 'succes'
            paiement.date_confirmation = timezone.now()
            paiement.code_confirmation = transaction.airtel_transaction_id
            paiement.save()
            
            # Activer la souscription si paiement initial
            if paiement.type_paiement == 'souscription_initiale':
                try:
                    resultat_activation = SouscriptionPassService.activer_souscription(
                        paiement.souscription_pass.id
                    )
                    logger.info(
                        f"🎉 Souscription Airtel activée (timeout) - Police: {resultat_activation['numero_police']}"
                    )
                except Exception as e:
                    logger.error(f"❌ Erreur activation souscription Airtel: {e}")
        
        transaction.save()
        logger.info(f"🔄 Airtel {transaction.external_id}: {previous_status} → {transaction.statut} (timeout)")
        return True
    
    return False