# apps/borne_auth/serializers.py
from rest_framework import serializers
from apps.pass_clients.models import SouscriptionPass
from apps.borne_auth.models import NumeroPolice

class BorneAuthenticationSerializer(serializers.Serializer):
    """
    Serializer pour l'authentification borne NSIA PASS
    Utilise : police + téléphone (format Congo)
    """
    police = serializers.CharField(
        max_length=30,
        help_text="Numéro de police (ex: CG-2024-VIE-001)"
    )
    telephone = serializers.CharField(
        max_length=25,
        help_text="Numéro de téléphone Congo (+242061234567)"
    )
    
    def validate_telephone(self, value):
        """Validation format téléphone Congo"""
        import re
        # Format Congo sans espaces : +242061234567
        if not re.match(r'^\+242[0-9]{9}$', value):
            raise serializers.ValidationError(
                "Format téléphone invalide. Utilisez +242XXXXXXXXX"
            )
        return value
    
    def validate(self, attrs):
        """
        Validation croisée police + téléphone
        Recherche dans les tables existantes
        """
        police = attrs.get('police')
        telephone = attrs.get('telephone')
        
        try:
            # Recherche via NumeroPolice qui lie souscription + police
            numero_police = NumeroPolice.objects.select_related(
                'souscription_pass__client'
            ).get(
                numero_police=police,
                souscription_pass__client__telephone=telephone,
                statut='attribue'
            )
            attrs['numero_police'] = numero_police
            attrs['client'] = numero_police.souscription_pass.client
            attrs['souscription'] = numero_police.souscription_pass
            
        except NumeroPolice.DoesNotExist:
            raise serializers.ValidationError(
                f"Combinaison police/téléphone introuvable ou police inactive"
            )
        
        return attrs

class ClientDashboardSerializer(serializers.Serializer):
    """
    Serializer pour le dashboard client PASS
    """
    client_info = serializers.DictField()
    souscriptions_actives = serializers.IntegerField()
    valeur_totale = serializers.DecimalField(max_digits=12, decimal_places=2)
    contrats = serializers.ListField()
    derniers_paiements = serializers.ListField()
