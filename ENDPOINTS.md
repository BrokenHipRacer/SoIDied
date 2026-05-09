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
    - `http code`
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
  - **RESPONSE**:
    - `http code`
    - JSON of user has:
      - `id`: Unique identifier for the user.
      - `name`: The name of the user.
      - `email`: The canary email address of the user.  **ONLY IF IN DEBUG MODE**
    

- `/api/v1/users/remove`: Remove user from the database. #Will remove an ID if present, but you are compromised. Panic after the second use of any removed user, nothing will happen with any requests.
  - **PUT**:
    - JSON object with the following fields:
      - `id`: The ID of the user making the request.
      - `token`: The authentication token for the user.
      - `name`: The name of the user to add.
      - `email`: The canary email address of the user to add.
  - **RESPONSE**:
    - `http code`
    

- `/api/v1/users/list`: List all users in the database. #Will list but you are compromised.
  - **GET**:
    - JSON object with the following fields:
      - `id`: The ID of the user making the request.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code`
    - JSON array of users. Each user has:
      - `id`: Unique identifier for the user.
      - `name`: The name of the user.
      - `email`: The canary email address of the user.  **ONLY IF IN DEBUG MODE**

### Check-in:
- `/api/v1/checkin`: Register a check-in for a user. Only main will internally count as real, non-main user will register, but you are compromised.
  - **PUT**:
    - JSON object with the following fields:
      - `id`: The ID of the user making the request.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code`
    - `message` : "Next required Check-In by: [timestamp]"


- `/api/v1/checkin/status`: Get the current check-in status of a user. #Will return status but you are compromised.
  - **GET**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code`
    - `Status` : "OK" if user is in good standing, "ALERT" if user has missed check-ins, "DEAD" if user has reached the missed count threshold.

### Messages:
- `/api/v1/messages`: list all messages.
  - **GET**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code`
    - JSON array of messages. Each message has:
      - `id`: Unique identifier for the message.
      - `content`: The content of the message.
      - `file`: boolean if the message has a file attached.


- `/api/v1/messages/add`: Add a new message.
  - **POST**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
      - `message`: The content of the message to add.
      - `file`: Optional file to attach to the message.
  - **RESPONSE**:
    - `http code`
    - JSON array of messages. Each message has:
      - `id`: Unique identifier for the message.
      - `content`: The content of the message.


- `/api/v1/messages/remove`: Remove a message.
  - **PUT**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
      - `message_id`: The ID of the message to remove.
  - **RESPONSE**:
    - `http code`

  
- `/api/v1/messages/list`: List all messages.
  - **GET**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code` :
    - JSON array of messages. Each message has:
      - `id`: Unique identifier for the message.
      - `content`: The content of the message.
      - `file`: boolean if the message has a file attached.

  
- `/api/v1/messages/count`: Get the count of messages.
  - **GET**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code` :
    - `count`: The count of messages.


- `/api/v1/messages/clear`: "Clear all messages", will panic immediately but response as if it was successful.
  - **PUT**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code`


- `/api/v1/messages/file`: Get the file of a message.
  - **GET**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code` :
    - `file`: The file of the message.

### Utilities:
- `/api/v1/utils/ping`: Responds with "pong" to confirm the service is running. #Will respond, but you are compromised unless DEBUG MODE is enabled.
  - **GET**:
    - Does not require any fields.
  - **RESPONSE**:
    - `http code`
    - `message` : "pong"


- `/api/v1/utils/unlock`: Unlock the service. #Will unlock/stop PANIC but careful you might be compromised.
  - **PUT**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code`

  
- `/api/v1/utils/api`: Get a txt file of the APIs for the service.  **USE WITH CAUTION!** This only works for a limited time in the starting of Dark Mode.
  - **GET**:
     - JSON object with the following fields:
       - `id`: The ID of the user to check status for.
       - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code`
    - `file`: The txt file of the APIs for the service.


- `/api/v1/utils/debug`: Toggle debug mode on/off.  Endpoints will respond with more information.  **USE WITH CAUTION!** Does not work in DARK MODE.
  - **PUT**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code`


- `/api/v1/utils/ducky`: Get a txt file of the DuckyScript for the service. **USE WITH CAUTION!** This only works for a limited time in the starting of Dark Mode.
  - ?OPTIONS are: check-in, darkMode, unlock, api
  - **GET**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code`
    - `file`: The txt file of the DuckyScript for the service.  **USE WITH CAUTION!**

### Dark mode:
- `/api/v1/darkmode`: Toggle dark mode on.  There is no response and no way to turn it off unless DEBUG MODE is enabled beforehand.
  - **PUT**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code` : 404
    - `message` : "Dark mode enabled. All endpoints will now respond with 404 and paths will rotate. Use /api/v1/utils/unlock to stop PANIC and return to normal operation, but be aware you may be compromised."
    - `file`: A txt file of the APIs for the service.


- `/api/v1/darkmode-api`: Get a txt file of the APIs for the service.  **USE WITH CAUTION!** This only works for a limited time in the starting of Dark Mode.
  - **GET**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code` : 404
    - `message` : "Dark mode enabled. All endpoint paths have rotated." / NONE
    - `file`: A txt file of the APIs for the service. / NONE

- `/api/v1/darkmode-ducky`: Get a txt file of the DuckyScript for the service. **USE WITH CAUTION!** This only works for a limited time in the starting of Dark Mode.
  - ?OPTIONS are: check-in, darkMode, unlock, api
  - **GET**:
    - JSON object with the following fields:
      - `id`: The ID of the user to check status for.
      - `token`: The authentication token for the user.
  - **RESPONSE**:
    - `http code`
    - `message` : "Dark mode enabled. All endpoint paths have rotated." / NONE
    - `file`: A ducky script file for the service. / NONE

---

## Dark mode changes:
- Dark mode is enabled by default.
- Dark mode can be toggled by sending a POST request to `/api/v1/darkmode` with the following payload:
    - `mode`: "on" or "off" to enable or disable dark mode. **DEBUG MODE ONLY**
- WHILE dark mode is enabled:
    - All endpoints will respond with a 404 "not found" regardless of the actual outcome.
    - Endpoints will change their paths to make them harder to find. The new paths will be logged for reference.
    - Startup files will be written and available for a certain period of time and then securely deleted for less accessible to attackers. 