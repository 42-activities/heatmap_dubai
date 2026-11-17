# Data Dictionary — Dubai RTA Bus Datasets

Field-level reference for the four `rta` open datasets consumed by this project.
Compiled from **live STG responses** (2026-11-17) and the Dubai Data portal
attribute tables. Where the two disagree, live wins — see `CLAUDE.md`.

## Confirmation legend

| Mark | Meaning |
|---|---|
| ✅ | Verified in a live response; type and presence clear |
| 🔶 | Seen live, but value set / meaning not yet confirmed |
| 📄 | From the portal attribute table only; not independently verified live |
| ❓ | Unknown / not yet observed |

> **STG caveat:** `rta_bus_ridership-open-api` has only **1 row in STG**, so its
> nullability, `txn_type` code set, and zone range are **not** established.
> Re-profile on PROD (`scripts/profile_ridership.py`) before trusting them.

## Access (all datasets)

- Endpoint: `GET {base}/open/rta/<dataset>` with `Authorization: Bearer <token>`
- Response envelope: `{"results": [ {record}, ... ]}`
- Pagination: `limit`/`offset` **or** `page`/`pageSize` (default page ~1000)
- Rate limit 60 req/min · timeout 30 s · see `CLAUDE.md` for the token flow

Types below use generic names (`string`, `integer`, `float`, `date` `YYYY-MM-DD`,
`time` `HH:MM:SS`, `timestamp` `YYYY-MM-DD HH:MM:SS`).

---

## 1. `rta_bus_routes-open-api` — Route → stop sequence

- **Grain:** one row per route + direction + stop position (this dataset *is* the
  route↔stop bridge). No primary key exposed.
- **STG rows:** 14,620

| Field | Type | Nullable | Example | Status | Notes |
|---|---|---|---|---|---|
| `route_name` | string | no | `"GE95B"` | ✅ | Join key to stops & ridership |
| `route_type` | string | ? | `"EK"` | 🔶 | Short code; meaning unconfirmed |
| `direction` | string | ? | `"DOZCC1 -> AC2"` | ✅ | Terminal-to-terminal, `->` separator |
| `stop_name` | string | ? | `"Russian International School 1"` | ✅ | Join key to stops |
| `stop_number` | integer | ? | `1` | ✅ | Sequence position along the route |
| `load_timestamp` | timestamp | ? | `"2020-11-02 21:09:00"` | ✅ | Platform load time, not a service time |

---

## 2. `rta_bus_stop_details-open-api` — Stop master

- **Grain:** one row per stop **per route** (a stop recurs across routes and
  validity windows). Dedup by `stop_id` for a clean `dim_stop`.
- **STG rows:** 20,000+ (hit paging cap; true count TBD)

| Field | Type | Nullable | Example | Status | Notes |
|---|---|---|---|---|---|
| `report_date` | date | ? | `"2024-04-21"` | ✅ | Reporting date |
| `stop_name` | string | no | `"Al Madar Scala Tower 2"` | ✅ | Join key to routes/ridership |
| `stop_id` | integer | no | `5174` | ✅ | Natural stop key (dedup on this) |
| `street_name` | string | yes (often `""`) | `""` | ✅ | Frequently empty |
| `route_name` | string | ? | `"F14"` | ✅ | Stop belongs to this route |
| `stop_location_longitude` | float | ? | `55.286114` | ✅ | WGS84 lon — **heatmap X** |
| `stop_location_latitude` | float | ? | `25.185223` | ✅ | WGS84 lat — **heatmap Y** |
| `bus_stop_type` | string | yes (often `""`) | `""` | 🔶 | Category code; values TBD |
| `time_table_panel` | string | ? | `"Yes"` | 🔶 | Looks boolean (`Yes`/`No`?) |
| `mupi_available` | string | yes (often `""`) | `""` | 🔶 | Boolean-ish; MUPI panel present |
| `rtpi_available` | string | yes (often `""`) | `""` | 🔶 | Boolean-ish; real-time info panel |
| `last_survey_date` | date | yes (`null`) | `null` | ✅ | Nullable |
| `valid_from` | date | ? | `"2017-04-15"` | ✅ | Validity window start |
| `valid_until` | date | ? | `"2036-01-01"` | ✅ | Validity window end |

---

## 3. `rta_bus_ridership-open-api` — Tap transactions

- **Grain:** one tap/transaction event. No primary key exposed — synthesize a
  surrogate key on load.
- **STG rows:** **1 (sample only)** — everything below needs PROD re-profiling.

| Field | Type | Nullable | Example | Status | Notes |
|---|---|---|---|---|---|
| `txn_type` | string | ? | `"CKA"` | 🔶 | **Code, not `Check In`/`Check Out`.** Only `CKA` seen; enumerate on PROD |
| `txn_date` | date | ? | `"2025-10-18"` | ✅ | Transaction date |
| `txn_time` | time | ? | `"21:28:15"` | ✅ | Transaction time |
| `start_location` | string | ? | `"Al Nahda 1, DEWA-1"` | 🔶 | Free text; may not match `stop_name` |
| `end_location` | string | ? | `"Al Nahda 1, DEWA-1"` | 🔶 | Free text; join coverage TBD |
| `route_name` | string | ? | `"F22"` | ✅ | Join key to routes/stops |
| `start_zone` | string | ? | `"Zone 5"` | 🔶 | `"Zone N"` format; full range TBD |
| `end_zone` | string | ? | `"Zone 5"` | 🔶 | `"Zone N"` format; full range TBD |
| `load_timestamp` | timestamp | ? | `"2026-02-22 21:52:39"` | ✅ | Platform load time |

**Open questions (resolve on PROD):** full `txn_type` code set & meanings;
whether rows pair into trips; zone range (plan assumed `Zone 0`–`Zone 9`);
`start_location`/`end_location` match rate against `stop_name`.

---

## 4. `rta_bus_network_coverage-open-api` — Community bus accessibility

- **Grain:** one row per community per `report_date`. **Primary key:**
  `community_num` (per portal).
- **STG rows:** 227
- **Portal metadata:** source *Public Transportation Planning System* (SDSC),
  CSV; source updated **weekly**, platform refreshed **annually**; classification
  Open / English. *(These three facts are portal-stated, not live-verified.)*

| Field | Type | Nullable | Example | Status | Notes |
|---|---|---|---|---|---|
| `report_date` | date | ? | `"2024-12-31"` | ✅ | Date of reporting |
| `community_num` | integer | no | `246` | ✅📄 | **Primary key** (portal) |
| `community_name` | string(200) | ? | `"AL QUSAIS IND. THIRD"` | ✅ | |
| `community_area_size` | numeric | ? | `1` | ✅📄 | Area in km² |
| `makani_points` | integer | ? | `195` | ✅ | Makani address points in community |
| `population` | integer | ? | `2838` | ✅ | Community population |
| `nume_of_bus_stops` | numeric | ? | `12` | 🔶 | Name says count; portal desc says "per km²" — reconcile |
| `accessible_population` | integer | ? | `2765` | ✅ | Population within 400 m of a stop |
| `geographic_coverage` | numeric | ? | `100` | ✅ | Coverage **%** (0–100) — accessibility heatmap value |
| `load_timestamp` | timestamp | ? | `"2025-08-20 03:48:41"` | ✅ | Added by API; not in portal table |

---

## Cross-dataset relationships

```
routes.route_name  ─┬─>  stops.route_name          (string join)
                    └─>  ridership.route_name       (string join)
routes.stop_name    ──>  stops.stop_name            (string join)
ridership.start_location / end_location  ~~>  stops.stop_name   (fuzzy; coverage TBD)
coverage.community_num                   (standalone; community grain, no bus-stop FK)
```

- **No numeric foreign keys** across datasets — all joins are on `route_name`
  and name/location **strings**. Normalize casing/whitespace before joining.
- `coverage` does not link to individual stops; it aggregates at the community
  level and is used as a separate accessibility layer.

## Maintenance

Regenerate field lists with `scripts/test_dataset.py` (one record per dataset).
When PROD access lands, update the 🔶 rows in §3 from
`scripts/profile_ridership.py` and `scripts/join_coverage.py` output, and change
the marks to ✅ once values are confirmed.
