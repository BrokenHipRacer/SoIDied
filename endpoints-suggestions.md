# API Endpoints Reference – Suggested Refactor

## Table of Contents
1. [Overview](#overview)
2. [Authentication & Common Requirements](#authentication--common-requirements)
3. [Rate Limiting & Request Throttling](#rate-limiting--request-throttling)
4. [HTTP Status Codes](#http-status-codes)
5. [Endpoints by Category](#endpoints-by-category)
6. [Appendix: Dark Mode](#appendix-dark-mode)
7. [Appendix: Debug Mode](#appendix-debug-mode)

---

## Overview

**SoIDied** is a post-mortem digital notification system. All endpoints require authentication via `id` and `token` fields in the request body. The API supports three operational modes:

- **Normal Mode**: Standard operation with authentication
- **Debug Mode**: Enhanced logging and detailed responses (toggleable via `/api/v1/utils/debug`)
- **Dark Mode**: Security hardening that masks all responses as 404 and rotates endpoint paths

---

## Authentication & Common Requirements

### Request Authentication
All requests must include:
```json
{
  "id": "user_id",
  "token": "authentication_token"
}
```

### User Classification
- **Primary User ("main")**: Owner of the system; check-ins count as legitimate
- **Compromised User ("non-main")**: Any other user accessing endpoints; treated as a potential threat
  - Check-ins registered but don't count toward legitimate status
  - After the 2nd use of any endpoint, panic may be triggered

---

## Rate Limiting & Request Throttling

### Request Handling
- Requests are processed sequentially to ensure system stability
- Rapid consecutive requests to the same endpoint may be queued or delayed
- The system automatically manages a load to prevent resource exhaustion

---

## HTTP Status Codes

### Standard Success Responses
| Code | Meaning | Typical Use |
|------|---------|------------|
| 200 | OK | Successful read or action |
| 201 | Created | User/message successfully added |
| 204 | No Content | Successful delete/clear (no response body) |

### Client Error Responses
| Code | Meaning | Typical Use |
|------|---------|------------|
| 400 | Bad Request | Missing required fields, invalid format |
| 401 | Unauthorized | Invalid id or token |
| 404 | Not Found | Resource doesn't exist (always returned in Dark Mode) |

---

## Endpoints by Category

### User Management

#### `GET /api/v1/users`
**Description**: List all users in the system

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (Success – 200):
```json
[
  {
    "id": "user_id",
    "name": "John Doe",
    "email": "john@example.com"  // Only in DEBUG mode
  },
  ...
]
```

**Notes**: 
- All users can retrieve user information
- Email field omitted unless `debug=true` in settings

---

#### `POST /api/v1/users/add`
**Description**: Create a new user in the database

**Request**:
```json
{
  "id": "user_id",
  "token": "token",
  "name": "New User",
  "email": "user@example.com"
}
```

**Response** (Success – 201):
```json
{
  "id": "new_user_id",
  "name": "New User",
  "email": "user@example.com"  // Only in DEBUG mode
}
```

**Notes**:
- Primary user: User is added normally
- Non-primary user: User is added to the system
- Returns new user ID in response

---

#### `PUT /api/v1/users/remove`
**Description**: Remove a user from the database

**Request**:
```json
{
  "id": "user_id",
  "token": "token",
  "name": "User to Remove",
  "email": "user@example.com"
}
```

**Response** (Success – 204): No body

**Notes**:
- Primary user: Removes user normally
- Non-primary user: User removal is processed

---

#### `GET /api/v1/users/list`
**Description**: Retrieve the list of all users (alias for GET `/api/v1/users`)

**Request**: Same as `GET /api/v1/users`

**Response**: Same as `GET /api/v1/users` (200 with the user array)

---

### Check-in Management

#### `PUT /api/v1/checkin`
**Description**: Register a check-in for the user

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (Success – 200):
```json
{
  "message": "Next required Check-In by: 2026-05-16T14:30:00Z"
}
```

**Notes**:
- Primary user: Check-in counts toward legitimate status, resets missed count
- Non-primary user: Check-in is registered with a timestamp

---

#### `GET /api/v1/checkin/status`
**Description**: Get current check-in status for a user

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (Success – 200):
```json
{
  "status": "OK"
}
```

**Possible Status Values**:
- `OK`: User in good standing, no missed check-ins
- `ALERT`: User has missed 1+ check-ins (within `defences.miss_count` threshold)
- `DEAD`: User has exceeded `defences.miss_count` threshold - death sequence triggered

**Notes**:
- All users can retrieve their status information

---

### Messages Management

#### `GET /api/v1/messages`
**Description**: Retrieve all messages for the authenticated user

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (Success – 200):
```json
[
  {
    "id": "message_id",
    "content": "This is a message",
    "file": false
  },
  {
    "id": "message_id_2",
    "content": "Message with attachment",
    "file": true
  }
]
```

---

#### `POST /api/v1/messages/add`
**Description**: Add a new message (with optional file attachment)

**Request**:
```json
{
  "id": "user_id",
  "token": "token",
  "message": "Message content here",
  "file": null  // Optional: file data/path
}
```

**Response** (Success – 201):
```json
[
  {
    "id": "new_message_id",
    "content": "Message content here",
    "file": false
  }
]
```

**Notes**:
- Files are optional attachments
- Response includes all messages for the user

---

#### `GET /api/v1/messages/list`
**Description**: List all messages (alias for GET `/api/v1/messages`)

**Request**: Same as `GET /api/v1/messages`

**Response**: Same as `GET /api/v1/messages` (200 with the message array)

---

#### `PUT /api/v1/messages/remove`
**Description**: Delete a specific message

**Request**:
```json
{
  "id": "user_id",
  "token": "token",
  "message_id": "id_to_remove"
}
```

**Response** (Success – 204): No body

---

#### `GET /api/v1/messages/count`
**Description**: Get count of messages owned by all users

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (Success – 200):
```json
{
  "count": 5
}
```

---

#### `PUT /api/v1/messages/clear`
**Description**: Delete all messages for the user

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (Success – 200):
```json
{
  "message": "All messages cleared"
}
```

**Notes**: This action deletes all messages. Ensure you have backups if needed.

---

#### `GET /api/v1/messages/file`
**Description**: Download a message's attached file

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (Success – 200):
```
[Binary file data]
```

**Content-Type**: Appropriate for file type (application/octet-stream, image/png, etc.)

---

### Utilities & System Control

#### `GET /api/v1/utils/ping`
**Description**: Health check – confirms service is running

**Request**: No authentication required

**Response** (Success – 200):
```json
{
  "message": "pong"
}
```

**Notes**:
- Normal Mode: Simple "pong" response
- Dark Mode: Returns 404 but service is still running (test via timing)
- Debug Mode: Returns with timestamp

---

#### `PUT /api/v1/utils/debug`
**Description**: Toggle debug mode on/off

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (Success – 200):
```json
{
  "message": "Debug mode: ON",
  "debug_state": true
}
```

**Notes**:
- Toggle: Each call flips the current debug state
- Effects: Enhanced logging, email fields visible, additional response details
- Restrictions: Cannot be invoked if Dark Mode is active

---

#### `PUT /api/v1/utils/unlock`
**Description**: Stop panic/lockdown and return the system to normal operation

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (Success – 200):
```json
{
  "message": "System state refreshed.",
  "status": "READY"
}
```

**Notes**:
- Resets system state to nominal operations
- Call this endpoint to refresh the system if needed

---

#### `GET /api/v1/utils/api`
**Description**: Retrieve current API endpoints as a text file

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (Success – 200):
```
Content-Type: text/plain

[List of all available endpoints]
```

**Notes**:
- Retrieves the list of available endpoints
- Response: Markdown or plain text listing all current endpoints

---

#### `GET /api/v1/utils/ducky`
**Description**: Retrieve DuckyScript payloads for USB Rubber Ducky automation

**Request**:
```json
{
  "id": "user_id",
  "token": "token",
  "option": "check-in"  // check-in, darkMode, unlock, api
}
```

**Response** (Success – 200):
```
Content-Type: text/plain

[DuckyScript code for selected option]
```

**Available Options**:
- `check-in`: Script to trigger check-in via API
- `darkMode`: Script to enable Dark Mode
- `unlock`: Script to unlock the system
- `api`: Script to retrieve current endpoints

**Notes**:
- Available for authorized administrators only
- DuckyScript compatible syntax for USB Rubber Ducky automation

---

### Dark Mode Control

#### `PUT /api/v1/darkmode`
**Description**: Enable Dark Mode – all subsequent endpoints return 404, paths rotate

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (200 - immediately switches to Dark Mode):
```json
{
  "message": "Dark mode enabled. System is now operating in secure mode.",
  "note": "All subsequent requests will be processed normally.",
  "info": "Refer to startup files for current endpoint configuration"
}
```

**Response (After Dark Mode Active – all requests appear as)**:
```json
{
  "error": "Not Found"
}
```

**Notes**:
- Activates secure operating mode
- All responses are masked to prevent system reconnaissance
- Cannot be disabled without prior setup

---

#### `GET /api/v1/darkmode-api`
**Description**: Retrieve current rotated API endpoints (Dark Mode context)

**Request**:
```json
{
  "id": "user_id",
  "token": "token"
}
```

**Response** (Success – 200, but appears as 404):
```
Content-Type: text/plain
HTTP 404

[Current endpoint mappings]
```

**Notes**:
- Returns current endpoint configuration
- Available during the secure mode window

---

#### `GET /api/v1/darkmode-ducky`
**Description**: Retrieve DuckyScript compatible with Dark Mode rotated endpoints

**Request**:
```json
{
  "id": "user_id",
  "token": "token",
  "option": "check-in"  // check-in, darkMode, unlock, api
}
```

**Response**: Same as `/api/v1/utils/ducky` but formatted for Dark Mode rotated paths

**Notes**:
- Available during the secure mode window
- Returns DuckyScript compatible with the current configuration

---

## Appendix: Dark Mode

### What is Dark Mode?

Dark Mode is a security hardening feature that provides:
1. **Masked Responses**: All responses appear consistent to prevent system reconnaissance
2. **Dynamic Endpoint Configuration**: Endpoint paths are reconfigured for enhanced security
3. **Startup File Mapping**: Configuration file written with the current state (auto-deleted within the security window)

### Behavioral Changes in Dark Mode

| Aspect | Normal Mode | Dark Mode |
|--------|-------------|-----------|
| **Responses** | Normal JSON with appropriate codes | Consistent masked responses |
| **Endpoint Paths** | Static (`/api/v1/users`, etc.) | Dynamic (reconfigured for security) |
| **Side Effects** | None | All operations proceed normally |
| **Debug Mode** | Can be toggled | Not available in this mode |
| **Recovery** | N/A | System state can be refreshed via `/api/v1/utils/unlock` |

### Startup File
When Dark Mode is active:
- Configuration file written with the current endpoint state
- Contains current endpoint mappings and configuration
- Automatically managed (deleted after the configured timeframe)
- Can be retrieved via `/api/v1/utils/api` if needed

### Exiting Dark Mode
- **Method**: Call `/api/v1/utils/unlock` to restore normal mode
- **Result**: Endpoints return to standard configuration, normal responses resume

### Use Case
- Enhanced security posture during high-risk scenarios
- Provides ambiguity to prevent system reconnaissance
- Administrator tool for system hardening

---

## Appendix: Debug Mode

### What is Debug Mode?

Debug Mode enhances observability by enabling additional logging and detailed responses.

### Effects When Enabled

1. **User Endpoints**:
   - `email` field is included in user objects (normally hidden)
   - Additional metadata in responses

2. **Messages Endpoints**:
   - Full messages are visible
   - Timestamps included

3. **Logging**:
   - All requests are logged with id, token, timestamp
   - Response times tracked

4. **Startup**:
   - Complete config printed to console
   - Database state dumped on initialization

### Toggling Debug Mode

- **Endpoint**: `PUT /api/v1/utils/debug`
- **Behavior**: Each call toggles the current state
- **Restriction**: Available in normal mode only
- **Persistence**: State resets on service restart (read from `config.yaml`)

### Important Notes
- ✅ **Safe for development**: Enables without side effects
- ⚠️ **Risk for production**: Exposes internal state and sensitive data
- Debug setting in `config.yaml` determines startup default

---

## Standard Error Response Format

All errors follow this pattern:

```json
{
  "error": "Error Type",
  "message": "Human-readable explanation",
  "code": 400,
  "request_id": "unique_id_for_tracing"
}
```

### Common Errors

| Code | Error | Cause |
|------|-------|-------|
| 400 | BadRequest | Missing id/token or invalid JSON |
| 401 | Unauthorized | Invalid credentials |
| 404 | NotFound | Resource doesn't exist (or Dark Mode active) |
