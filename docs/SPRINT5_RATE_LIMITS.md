# Sprint 5 API rate limits

The API records fixed-window counters in `rate_limit_buckets`, so multiple backend workers share limits. Migration `0003_rate_limits` creates the table. Bucket keys are SHA-256 hashes of scope, subject and window; no raw email, token or IP is stored. Expired buckets are removed opportunistically.

| Endpoint group | Default limit | Identity |
|---|---:|---|
| Login | 60/minute per IP and 10/minute per email | IP and normalized email |
| Refresh | 60/minute | IP |
| Request creation and attachments | 120/hour each | User ID, or IP for invalid tokens |
| Messages | 60/minute | User ID, or IP for invalid tokens |
| Classification, similar cases and smart replies | 60/minute combined | User ID, or IP for invalid tokens |
| Report export | 10/hour combined | User ID, or IP for invalid tokens |
| Model retraining | 2/hour | User ID, or IP for invalid tokens |

The API returns HTTP 429 with `Retry-After` when a limit is exceeded. Successful requests include `X-RateLimit-Limit` and `X-RateLimit-Remaining`. Limits are configurable through `QOLDAU_RATE_LIMIT_*` settings in `backend/.env.example`.

The direct peer IP is authoritative by default. If a reverse proxy is in use, disable Uvicorn's automatic proxy-header processing and set `QOLDAU_TRUSTED_PROXY_CIDRS` to the proxy IPs or CIDRs. Only a peer in that list may supply `X-Forwarded-For`; the API reads the chain from right to left to reject untrusted prefixes. Do not list a broad public range as trusted.
