# This is the list of endpoints, their descriptions, and how to use them.

## Comments:
- Any non-main user usage will expect you are compromised
- See [end | link to dark mode section] for dark mode changes to endpoints and responses.
- panic after the second use of any endpoint too soon after the previous call, IF non-dark mode service can be unlocked, otherwise, panic after the timer runs out.
- every endpoint will panic after the second use of any endpoint too soon after the previous call
- every endpoint will respond with normally expected responses but only 404 "not found" if dark mode is enabled.
- every endpoint will require id and token to be sent in the request.
- adding messages will not trigger a panic.


---

## The endpoints are:
### User management:
- `/api/v1/users`: User management (create, read, update, delete), Responed a list of users. 
  - **GET**:
    - JSON object with the following fields:
      - `id`: The ID of the user making the request.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - JSON array of users. Each user has:
      - `id`: Unique identifier for the user.
      - `name`: The name of the user.
      - `email`: The canary email address of the user.  **ONLY IF IN DEBUG MODE**


- `/api/v1/users/add`: Add user to the database. #Will add an ID but you are compromised. Panic after the second use of any added user, nothing will happen with any requests.
  - **POST**:
    - JSON object with the following fields:
      - `id`: The ID of the user making the request.
      - `token`: The authentication token for the user.
      - `name`: The name of the user to add.
      - `email`: The canary email address of the user to add.
  **RESPONSE**:
    - JSON array of users. Each user has:
      - `id`: Unique identifier for the user.
      - `name`: The name of the user.
      - `email`: The canary email address of the user.  **ONLY IF IN DEBUG MODE**
    
- `/api/v1/users/remove`: Remove user from the database. #Will remove an ID if present, but you are compromised. Panic after the second use of any removed user, nothing will happen with any requests.
- `/api/v1/users/list`: List all users in the database. #Will list but you are compromised.

### Check-in:
- `/api/v1/checkin`: Register a check-in for a user. Only main will internally count as real, non-main user will register, but you are compromised.
  - **POST**:
    - `id`: The ID of the user to check in.
    - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code` : 200 "success" if check-in is successful, "failure" otherwise.
    - `message` : "Next required Check-In by: [timestamp]"


- `/api/v1/checkin/status`: Get the current check-in status of a user. #Will return status but you are compromised.
    - **GET**:
        - `id`: The ID of the user to check status for.
        - `token`: The authentication token for the user.
    - **RESPONSE**:
        - `http code` : 200 "success" if status retrieval is successful, "failure" otherwise.
        - `Status` : "OK" if user is in good standing, "ALERT" if user has missed check-ins, "DEAD" if user has reached the missed count threshold.

### Messages:
- `/api/v1/messages`: list all messages.
  - **RESPONSE**:
    - JSON array of messages. Each message has:
        - `id`: Unique identifier for the message.
        - `content`: The content of the message.


- `/api/v1/messages/add`: Add a new message.
- 
- `/api/v1/messages/remove`: Remove a message. #
- `/api/v1/messages/list`: List all messages.
- `/api/v1/messages/count`: Get the count of messages.
- `/api/v1/messages/clear`: "Clear all messages", will panic immediately but response as if it was successful.
- `/api/v1/messages/file`: Get the file of a message.


### Utilities:
- `/api/v1/utils/ping`: Responds with "pong" to confirm the service is running. #Will respond but you are compromised.
- `/api/v1/utils/unlock`: Unlock the service. #Will unlock/stop PANIC but careful you might be compromised.
- `/api/v1/utils/api`: Get a txt file of the APIs for the service.
- `/api/v1/utils/debug`: Toggle debug mode on/off.  Endpoints will respond with more information.  **USE WITH CAUTION!**
- `/api/v1/utils/ducky`: Get a txt file of the DuckyScript for the service.
  - TODO: I think I need to make a ? to get individual scripts for the different files
  - `?checkin`
  - `?darkmode`

### Dark mode:
- `/api/v1/darkmode`: Toggle dark mode on.  There is no response and no way to turn it off unless DEBUG MODE is enabled.
- 

---

## Dark mode changes:
- Dark mode is enabled by default.
- Dark mode can be toggled by sending a POST request to `/api/v1/darkmode` with the following payload:
    - `mode`: "on" or "off" to enable or disable dark mode. **DEBUG MODE ONLY**
- WHILE dark mode is enabled:
    - All endpoints will respond with a 404 "not found" regardless of the actual outcome.
    - Endpoints will change their paths to make them harder to find. The new paths will be logged for reference.
    - Startup files will be written and available for a certain period of time and then securely deleted for less accessible to attackers. 