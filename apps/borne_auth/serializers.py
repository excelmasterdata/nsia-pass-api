# apps/borne_auth/serializers.py
from datetime import datetime
import uuid
from rest_framework import serializers
from apps.pass_clients.models import SouscriptionPass
from apps.borne_auth.models import NumeroPolice
from .models import Agent
from django.core.validators import RegexValidator
from django.db import transaction

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

class AgentSerializer(serializers.ModelSerializer):
    """Serializer complet pour les agents"""
    
    nom_complet = serializers.ReadOnlyField()
    
    class Meta:
        model = Agent
        fields = [
            'id', 'nom', 'prenom', 'nom_complet', 'telephone', 'email',
            'matricule', 'agence', 'poste', 'adresse',
            'solde_commissions', 'taux_commission',
            'date_embauche', 'statut', 'date_creation', 'date_modification'
        ]
        read_only_fields = ['id', 'nom_complet', 'date_creation', 'date_modification', 'solde_commissions']
    
    def validate_telephone(self, value):
        """Validation format téléphone Congo"""
        if not value.startswith('+242'):
            raise serializers.ValidationError("Le téléphone doit commencer par +242")
        
        # Vérifier longueur (9 chiffres après +242)
        if len(value) != 13:
            raise serializers.ValidationError("Format: +242XXXXXXXXX (9 chiffres)")
        
        return value
    
    def validate_matricule(self, value):
        """Validation matricule unique"""
        if Agent.objects.filter(matricule=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("Ce matricule existe déjà")
        
        return value.upper()

class AgentCreateSerializer(serializers.ModelSerializer):
    """Serializer pour création d'agent"""
    
    class Meta:
        model = Agent
        fields = [
            'nom', 'prenom', 'telephone', 'email',
            'agence', 'poste', 'adresse', 'taux_commission', 'date_embauche'
        ]
    
    def validate_telephone(self, value):
        if not value.startswith('+242'):
            raise serializers.ValidationError("Format requis: +242XXXXXXXXX")
        return value
    
    def generate_uuid_matricule(self):
        """
        Génère un matricule unique basé sur timestamp + UUID
        Format: AG-2024-A1B2C3 (plus robuste)
        """
        year = datetime.now().year
        short_uuid = str(uuid.uuid4())[:6].upper()
        return f"AG-{year}-{short_uuid}"
    
    def create(self, validated_data):
        validated_data['matricule'] = self.generate_uuid_matricule()
        validated_data['statut'] = 'actif'
        return super().create(validated_data)

class AgentListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste d'agents"""
    
    nom_complet = serializers.ReadOnlyField()
    
    class Meta:
        model = Agent
        fields = [
            'id', 'nom_complet', 'matricule', 'telephone', 
            'agence', 'poste', 'statut', 'date_creation'
        ]

class AgentStatsSerializer(serializers.ModelSerializer):
    """Serializer avec statistiques agent"""
    
    nom_complet = serializers.ReadOnlyField()
    nombre_souscriptions = serializers.IntegerField(read_only=True)
    chiffre_affaires = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    commissions_dues = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = Agent
        fields = [
            'id', 'nom_complet', 'matricule', 'agence', 'statut',
            'solde_commissions', 'taux_commission',
            'nombre_souscriptions', 'chiffre_affaires', 'commissions_dues'
        ]

class AgentLoginSerializer(serializers.Serializer):
    """Serializer pour login agent"""
    
    telephone = serializers.CharField(max_length=25)
    matricule = serializers.CharField(max_length=20)
    
    def validate(self, attrs):
        telephone = attrs.get('telephone')
        matricule = attrs.get('matricule').upper()
        
        if not telephone or not matricule:
            raise serializers.ValidationError('Téléphone et matricule requis')
        
        # Chercher l'agent
        try:
            agent = Agent.objects.get(
                telephone=telephone,
                matricule=matricule,
                statut='actif'
            )
        except Agent.DoesNotExist:
            raise serializers.ValidationError('Identifiants incorrects ou agent inactif')
        
        attrs['agent'] = agent
        return attrs
    
class AgentUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour modification d'agent - matricule non modifiable"""
    
    class Meta:
        model = Agent
        fields = [
            'nom', 'prenom', 'telephone', 'email', 
            'agence', 'poste', 'adresse', 'taux_commission'
        ]
        # ✅ Matricule et date_embauche exclus - non modifiables
    
    def validate_telephone(self, value):
        if not value.startswith('+242'):
            raise serializers.ValidationError("Format requis: +242XXXXXXXXX")
        return value