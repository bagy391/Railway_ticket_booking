# Installation steps
1. Clone the repository
2. Install docker and docker-compose / docker desktop
3. Build container using below command
```bash
docker-compose up
```
4. Go to http://localhost:8000/admin/ to view the application
5. Default admin creds: 
   username: admin
   password: password
6. API's:
   7. Available Tickets 
      - GET http://localhost:8000/api/v1/tickets/available/
      CURL:
         curl --location 'http://localhost:8000/api/v1/tickets/available/'
   8. Booked Tickets
      - GET http://localhost:8000/api/v1/tickets/
      CURL:
         curl --location 'http://localhost:8000/api/v1/tickets/'
   9. Book Ticket
      - POST http://localhost:8000/api/v1/tickets/book_ticket/
      payload - 
      {
         "name": "name",
         "age": 30,
         "gender": "M",
         "has_child": false
      }
      gender options: "M" for Male, "F" for female

      CURL:
         curl --location 'http://localhost:8000/api/v1/tickets/book_ticket/' \
         --header 'Content-Type: application/json' \
         --data '{
            "name": "Rangan",
            "age": 20,
            "gender": "M",
            "has_child": false
         }'

   10. Cancel Ticket
      - POST http://localhost:8000/api/v1/tickets/{ticket_id}/cancel_ticket/
            ex: http://localhost:8000/api/v1/tickets/361/cancel_ticket/
      
      CURL:
         curl --location --request POST 'http://localhost:8000/api/v1/tickets/316/cancel_ticket/' \
         --data ''