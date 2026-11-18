# Sprint 5 access rules

| Resource | Student | Agent / unit head | Admin |
|---|---|---|---|
| Request, timeline, messages, attachments | Own requests | Own unit or assigned requests | All requests |
| Unassigned `Needs Review` request | Own request | Triage unit only | All requests |
| Request status, assignment, AI override, workflow step | No | Same request scope as above | All requests |
| Internal notes and attachments | No | Same request scope as above | All requests |
| Knowledge base management | No | Staff actions with unit-specific publish rules | All units |
| Analytics | No | Own unit | All units |
| Report export | No | Unit heads, own unit | All units |
| Admin configuration and model management | No | No | All units |

The API returns 404 for a request outside the viewer's scope so its existence is not disclosed. Role-only endpoints return 403. Signed attachment and export links are bound to a user ID and expire; each download also rechecks the user's active status, current role and current request access. WebSocket request subscriptions use the same visibility rule as HTTP request reads.

Regression coverage lives in `backend/tests/test_sprint5_rbac.py` alongside earlier sprint access tests.
