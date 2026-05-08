---
name: atlas-query
description: Use when user asks to query Atlas product data, pull milestone dates, look up product schedules, search for product names in Atlas, asks about POR/Trend/Actual dates, or mentions Atlas, ECDW, or product milestone data from Intel's product planning system.
---

# Atlas Query

## Overview

Atlas is Intel's product lifecycle management system. This skill queries Atlas data via two paths:

| Path | Priority | AGS Role Required |
| --- | --- | --- |
| Snowflake / ECA | **Primary** | `cda_design_product_planning_prod_reader` |
| iBI DaaS REST API | Fallback | `EC GER ibi_idc_5961 R` + `IPG iBI Data Read Access` |

**Read-only.** Never attempt INSERT, UPDATE, DELETE, or DDL.

---

## AGS Requirements

Request all roles at `goto/ags` → Submit Request for Self.

| AGS Entitlement | Approver | Grants Access To |
| --- | --- | --- |
| `cda_design_product_planning_prod_reader` | Auto / DFlowAnalytics | Snowflake ECDW prod — `PRODUCT_ENGINEERING` database |
| `IPG iBI Data Read Access` | Auto | iBI DaaS API login |
| `IPG iBI Cloud Read` | Auto | iBI Cloud read access |
| `EC GER ibi_idc_5961 R` | Approver-idc.10311 | iBI DaaS Atlas domain views |
| `Atlas Data Reader` | Atlas team | Direct SQL access to `atlas-rep.intel.com` (legacy) |

**After approval:** Run `klist purge` in a Command Prompt before first use to refresh your Kerberos ticket. If still denied, wait 10–15 min for AD replication then purge again.

---

## Snowflake Connection (Primary)

**Package:** `pip install snowflake-connector-python --proxy="http://proxy-chain.intel.com:911"`

```python
import snowflake.connector

conn = snowflake.connector.connect(
    account='xd14286-ecdw.privatelink',
    user='firstname.lastname@intel.com',       # your Intel email
    authenticator='externalbrowser',            # opens browser SSO — complete login when prompted
    role='CDA_DESIGN_PRODUCT_PLANNING_PROD_READER',
    database='PRODUCT_ENGINEERING',
    schema='DESIGN_PRODUCT_PLANNING_ANALYSIS',
    warehouse='WH_PRDENG_CONSUMPTION',
    proxy_host='proxy-chain.intel.com',
    proxy_port=912,
    login_timeout=120,
)
cur = conn.cursor()
# ... queries ...
conn.close()
```

### Available Views

| View | Key Columns | Use For |
| --- | --- | --- |
| `PRODUCT_ENGINEERING_SCHEDULE` | `PROJECT`, `ITEM_ID`, `PRODUCT_ENGINEERING_MILESTONE_BASE_NM`, `REV_STEP_TXT`, `PLC_ORDER`, `PLAN_OF_RECORD_DTM`, `TREND_DTM`, `ACTUAL_FINISH_DTM`, `DRIVE_TO_DTM` | Milestone dates — **start here** |
| `PROJECT_PROPERTIES_PIVOT` | `ITEM_ID`, `METHODOLOGY`, `SEGMENT`, `PLANNING STATE`, `COMPLEXITY TYPE`, `PROJECT TYPE`, `ENG ORG`, `P&L ORG` | Product metadata |
| `PRODUCT_ENGINEERING_ATLAS_ENTITY` | `ATLAS_ENTITY_ID`, `ATLAS_PARENT_ENTITY_ID`, `ENTITY_ENTITY_TYPE`, `ATLAS_ENTITY_NAME` | Entity hierarchy |
| `PRODUCT_CONTACT` | `ITEM_ID` + contact fields | Product owners / contacts |
| `PRODUCT_PLANNING_PROPERTY` | `PRODUCT_PROPERTY_UNIQUE_ID`, `PRODUCT_PROPERTY_NM`, `PRODUCT_PROPERTY_TYPE` | Property definitions |

---

## iBI DaaS Connection (Fallback)

**Package:** `pip install requests requests-kerberos --proxy="http://proxy-chain.intel.com:911"`

Uses your Windows SSO Kerberos ticket automatically — no passwords needed.

```python
import requests, urllib3, json
from requests_kerberos import HTTPKerberosAuth, OPTIONAL

urllib3.disable_warnings()
krb_auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)

def ibi_query(sql):
    r = requests.get(
        'https://ibi-daas.intel.com/daas/web/services/sql',
        params={'command': sql},
        verify=False,
        auth=krb_auth,
        timeout=30,
    )
    data = json.loads(r.content.decode('utf-8-sig'))  # utf-8-sig strips the BOM
    if not data.get('Success'):
        raise RuntimeError(data.get('Logs', [{}])[0].get('Message', 'Unknown error'))
    return data['Data']
```

### Available Views

| View | Description |
| --- | --- |
| `V_RAWDATA_ATLAS_PRODUCT_MILESTONES` | Latest milestone data for all products |
| `V_RAWDATA_ATLAS_PRODUCT_PROPERTIES` | Product properties |
| `V_RAWDATA_ATLAS_PRODUCT_CONTACTS` | OVO and delegates per product |
| `V_BM_AIM_ATLAS_CALCULATED_DATES` | Cross-product Si/Die date calculations |
| `V_BM_IPG_ATLAS_MILESTONES_HISTORY` | Weekly milestone snapshot history |

---

## Path Selection

```python
def get_atlas_cursor():
    """Returns (path, cursor_or_query_fn). Snowflake first, iBI fallback."""
    try:
        import snowflake.connector
        conn = snowflake.connector.connect(
            account='xd14286-ecdw.privatelink',
            user='firstname.lastname@intel.com',
            authenticator='externalbrowser',
            role='CDA_DESIGN_PRODUCT_PLANNING_PROD_READER',
            database='PRODUCT_ENGINEERING',
            schema='DESIGN_PRODUCT_PLANNING_ANALYSIS',
            warehouse='WH_PRDENG_CONSUMPTION',
            proxy_host='proxy-chain.intel.com',
            proxy_port=912,
            login_timeout=120,
        )
        return ('snowflake', conn.cursor())
    except Exception as e:
        print(f'Snowflake unavailable: {e} — falling back to iBI DaaS')
        return ('ibi', ibi_query)
```

---

## Common Query Patterns

### Find products by name
```sql
-- Snowflake
SELECT DISTINCT PROJECT, ITEM_ID
FROM PRODUCT_ENGINEERING_SCHEDULE
WHERE UPPER(PROJECT) LIKE '%NOVA%LAKE%H%'
ORDER BY PROJECT;

-- iBI DaaS
SELECT TOP 20 PRODUCT_NAME, PRODUCT_CODE
FROM V_RAWDATA_ATLAS_PRODUCT_MILESTONES
WHERE UPPER(PRODUCT_NAME) LIKE '%NOVA%LAKE%H%'
```

### Get milestones for a product (Snowflake)
```sql
SELECT PRODUCT_ENGINEERING_MILESTONE_BASE_NM AS Milestone,
       REV_STEP_TXT                          AS Stepping,
       PLAN_OF_RECORD_DTM                    AS POR,
       TREND_DTM                             AS Trend,
       ACTUAL_FINISH_DTM                     AS Actual
FROM PRODUCT_ENGINEERING_SCHEDULE
WHERE ITEM_ID = 10051746          -- replace with target ITEM_ID
ORDER BY PLC_ORDER;
```

### Upcoming milestones only (not yet completed)
```sql
SELECT PROJECT, PRODUCT_ENGINEERING_MILESTONE_BASE_NM, REV_STEP_TXT,
       TREND_DTM, PLAN_OF_RECORD_DTM
FROM PRODUCT_ENGINEERING_SCHEDULE
WHERE UPPER(PROJECT) LIKE '%NOVA%LAKE%H%'
  AND ACTUAL_FINISH_DTM IS NULL
  AND TREND_DTM IS NOT NULL
ORDER BY TREND_DTM;
```

### Product metadata join
```sql
SELECT s.PROJECT, p.SEGMENT, p."ENG ORG", p."P&L ORG", p."PLANNING STATE"
FROM PROJECT_PROPERTIES_PIVOT p
JOIN (SELECT DISTINCT ITEM_ID, PROJECT
      FROM PRODUCT_ENGINEERING_SCHEDULE
      WHERE UPPER(PROJECT) LIKE '%NOVA%LAKE%H%') s
  ON p.ITEM_ID = s.ITEM_ID;
```

---

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| iBI returns `access denied` | `EC GER ibi_idc_5961 R` not yet active | Run `klist purge`, wait 10–15 min for AD replication, try again |
| Snowflake SSO mismatch error | Wrong Microsoft account selected in browser | Click `firstname.lastname@intel.com` in the SSO popup |
| `No active warehouse selected` | Warehouse missing from connect() | Add `warehouse='WH_PRDENG_CONSUMPTION'` |
| `Cannot perform SELECT. No current database` | Database/schema not set | Add `database='PRODUCT_ENGINEERING'` and `schema='DESIGN_PRODUCT_PLANNING_ANALYSIS'` |
| iBI JSON decode error | UTF-8 BOM in response | Use `r.content.decode('utf-8-sig')` not `r.text` |
| Empty results for product name | Naming variation | Try shorter patterns: `%NOVA%H%`, `%NOVA%LAKE%` |
| iBI `Success: False` after purge | AD replication lag (role just provisioned) | Wait 10–15 min then `klist purge` again |
