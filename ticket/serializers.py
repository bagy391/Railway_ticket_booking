from rest_framework import serializers
from .models import Passenger, Ticket


from rest_framework import serializers
from .models import Passenger, Ticket

class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = '__all__'

class TicketSerializer(serializers.ModelSerializer):
    passenger = PassengerSerializer(read_only=True)
    
    class Meta:
        model = Ticket
        fields = '__all__'
