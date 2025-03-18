from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class CustomTicketManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(cancelled=False)

    def get_confirmed_tickets(self):
        # returns all confirmed tickets with berth number assigned
        return self.get_queryset().filter(status='CNF', berth_number__isnull=False)

    def get_rac_tickets(self):
        return self.get_queryset().filter(status='RAC')

    def get_waiting_list_tickets(self):
        return self.get_queryset().filter(status='WL')

class Passenger(models.Model):
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female')])
    has_child = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    @property
    def is_child(self):
        return self.age < 5


class Ticket(models.Model):
    CONFIRMED_BERTHS = 63
    RAC_BERTHS = 18
    WAITING_LIST_TICKETS = 10
    BERTH_TYPES = [
        ('LB', 'Lower Berth'),
        ('MB', 'Middle Berth'),
        ('UB', 'Upper Berth'),
        ('SU', 'Side Upper Berth'),
        ('SL', 'Side Lower Berth'),  # For RAC berths
    ]
    STATUS_CHOICES = [
        ('CNF', 'Confirmed'),
        ('RAC', 'Reservation Against Cancellation'),
        ('WL', 'Waiting List'),
    ]
    passenger = models.ForeignKey(Passenger, on_delete=models.CASCADE)
    berth_number = models.IntegerField(null=True, blank=True)  # Dynamically assigned berth number
    berth_type = models.CharField(max_length=2, choices=BERTH_TYPES, null=True, blank=True)  # Dynamically assigned berth type
    status = models.CharField(max_length=3, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled = models.BooleanField(default=False)

    objects = CustomTicketManager()


    def __str__(self):
        return f"{self.passenger.name} - {self.status} (Berth: {self.berth_number} {self.berth_type})"