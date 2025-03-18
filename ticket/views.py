from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from .models import Passenger, Ticket
from .serializers import PassengerSerializer, TicketSerializer
import threading
import random
import time
booking_lock = threading.Lock()

class TicketViewSet(viewsets.ModelViewSet):
    authentication_classes = []
    permission_classes = []

    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    @action(detail=False, methods=['get'])
    def available(self, request, *args, **kwargs):
        response = {
            'available': None,
            'rac': None,
            'waiting_list': None,
        }
        available_tickets = Ticket.CONFIRMED_BERTHS - Ticket.objects.get_confirmed_tickets().count()
        if available_tickets > 0:
            response['available'] = available_tickets
            return Response(response, status=status.HTTP_200_OK)

        # Calculate available RAC berths
        rac_tickets = Ticket.objects.get_rac_tickets().count()
        if rac_tickets < Ticket.RAC_BERTHS:
            response['rac'] = rac_tickets + 1
            return Response(response, status=status.HTTP_200_OK)

        # Calculate available waiting list slots
        waiting_list_tickets = Ticket.objects.get_waiting_list_tickets().count()
        if waiting_list_tickets < Ticket.WAITING_LIST_TICKETS:
            response['waiting_list'] = waiting_list_tickets + 1
            return Response(response, status=status.HTTP_200_OK)
        
        return Response({
            'message': 'No tickets available'
        }, status=status.HTTP_200_OK)
    
    def _get_berth_type_for_number(self, number):
        """
        Get berth type based on berth number according to the pattern:
        1-LB, 2-MB, 3-UB, 4-LB, 5-MB, 6-UB, 7-SL, 8-SU and so on
        """
        remainder = number % 8
        if remainder == 1 or remainder == 4:
            return 'LB'
        elif remainder == 2 or remainder == 5:
            return 'MB'
        elif remainder == 3 or remainder == 6:
            return 'UB'
        elif remainder == 7:
            return 'SL'  # Side Lower (not used for regular bookings)
        elif remainder == 0:  # number % 8 == 0
            return 'SU'  # Side Upper

        return None
    
    def _allocate_confirmed_berth(self, passenger):
        """
        Allocate a confirmed berth based on priority rules and pattern
        """
        # Get all occupied berth numbers
        occupied_berths = list(Ticket.objects.exclude(
            berth_number__isnull=True
        ).values_list('berth_number', flat=True))
        
        # Identify all available berths and reserve lowers for senior and lady with child
        available_lower_berths = []
        other_available_berths = []
        for berth in range(1, 73): 
            if berth not in occupied_berths:
                # Skip side lower berths (7, 15, 23, etc.) as they aren't for regular bookings
                berth_type = self._get_berth_type_for_number(berth)
                if berth_type == 'LB':
                    available_lower_berths.append((berth, berth_type))
                elif berth_type == 'SL':
                    continue
                else:
                    other_available_berths.append((berth, berth_type))

        # Filter by priority for seniors and ladies with children
        is_senior = passenger.age >= 60
        is_lady_with_child = (
            passenger.gender == 'F' and 
            passenger.has_child
        )
        
        # If priority needed, filter for lower berths
        if (is_senior or is_lady_with_child) and available_lower_berths:
            x = random.choice(available_lower_berths) # Return available lower berth
            return x
        
        # For regular passengers, return random berth
        if other_available_berths:
            return random.choice(other_available_berths)
        
        # Fallback to lower berths if no other berths available
        if available_lower_berths:
            return random.choice(available_lower_berths)

        # This should not happen due to availability check
        raise Exception("No berths available despite confirmation check")
    
    def _allocate_rac_berth(self):
        """
        Allocate a RAC berth (side lower)
        """
        # RAC berths 
        rac_berths = [n for n in range(1, 74) if n % 8 == 7]
        
        # Get occupied RAC berths and count per berth
        rac_allocation = Ticket.objects.get_rac_tickets().values('berth_number').annotate(
            count=Count('berth_number')
        )
        
        # Find berths with 0 or 1 passenger (can accommodate another)
        occupied_counts = {item['berth_number']: item['count'] for item in rac_allocation}
        
        # Find first berth that can hold another passenger
        for berth in rac_berths:
            if berth not in occupied_counts:
                # Empty berth
                return berth, 'SL'
            elif occupied_counts[berth] < 2:
                # Has space for one more
                return berth, 'SL'
        
        # Fallback (should not happen due to availability checks)
        raise Exception("No RAC berths available despite availability check")

    @action(detail=False, methods=['post'], serializer_class=PassengerSerializer)
    def book_ticket(self, request, *args, **kwargs):
        """
        Book a ticket with proper berth allocation based on business rules
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Critical section - use lock to prevent concurrent bookings, and can be used for single process
        with booking_lock:
        # Start transaction
            with transaction.atomic():
                # Create passenger
                passenger = serializer.save()

                # Check if child under 5 (doesn't get berth)
                if passenger.is_child:
                    ticket = Ticket.objects.create(
                        passenger=passenger,
                        status='CNF',
                        berth_type=None,
                        berth_number=None
                    )
                    return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)
                
                # Get counts for each ticket category
                confirmed_count = Ticket.objects.get_confirmed_tickets().select_for_update().count()
                rac_count = Ticket.objects.get_rac_tickets().select_for_update().count()
                wl_count = Ticket.objects.get_waiting_list_tickets().select_for_update().count()
                
                # Determine ticket status based on availability
                if confirmed_count < Ticket.CONFIRMED_BERTHS:
                    status_code = 'CNF'
                elif rac_count < Ticket.RAC_BERTHS:
                    status_code = 'RAC'
                elif wl_count < Ticket.WAITING_LIST_TICKETS:
                    status_code = 'WL'
                else:
                    return Response({"detail": "No tickets available"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                # Assign berth for confirmed tickets
                berth_type = None
                berth_number = None
                
                if status_code == 'CNF':
                    berth_number, berth_type = self._allocate_confirmed_berth(passenger)
                elif status_code == 'RAC':
                    berth_number, berth_type = self._allocate_rac_berth()
                    
                ticket = Ticket.objects.create(
                    passenger=passenger,
                    status=status_code,
                    berth_type=berth_type,
                    berth_number=berth_number
                )
                
                return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)


    def _promote_rac_to_confirmed(self, berth_number, berth_type):
        """
        Promote first RAC ticket to confirmed status with given berth and wl to rac
        """
        # Get oldest RAC ticket
        rac_ticket = Ticket.objects.get_rac_tickets().order_by('created_at').first()
        
        if rac_ticket:
            self._promote_wl_to_rac(rac_ticket.berth_number, rac_ticket.berth_type)
            rac_ticket.status = 'CNF'
            rac_ticket.berth_number = berth_number
            rac_ticket.berth_type = berth_type
            rac_ticket.save()
        
    
    def _promote_wl_to_rac(self, berth_number, berth_type):
        """
        Promote first waiting list ticket to RAC
        """
        # Get oldest waiting list ticket
        wl_ticket = Ticket.objects.get_waiting_list_tickets().order_by('created_at').first()
        
        if wl_ticket:
            wl_ticket.status = 'RAC'
            wl_ticket.berth_number = berth_number
            wl_ticket.berth_type = berth_type
            wl_ticket.created_at = timezone.now() # Update created_at to reflect new RAC ticket
            wl_ticket.save()

    @action(detail=True, methods=['post'])
    def cancel_ticket(self, request, *args, **kwargs):
        """
        Cancel a ticket and handle promotion of RAC/WL tickets
        """
        ticket = self.get_object()
        # Critical section - use lock to prevent concurrent cancellations/bookings
        with booking_lock:
            with transaction.atomic():
                status_before = ticket.status
                berth_number = ticket.berth_number
                berth_type = ticket.berth_type
                
                # Mark the ticket cancelled
                ticket.cancelled = True
                ticket.save()
                
                # If it was a confirmed ticket (and not a child without berth)
                if status_before == 'CNF' and berth_number is not None:
                    # Promote RAC to confirmed and wl to rac
                    self._promote_rac_to_confirmed(berth_number, berth_type)
                    
                    
                # If it was a RAC ticket
                elif status_before == 'RAC':
                    # Promote WL to RAC
                    self._promote_wl_to_rac(berth_number, berth_type)

                
                return Response({"detail": "Ticket cancelled successfully"}, 
                               status=status.HTTP_200_OK)

        