---
name: power-bi-security
description: >
  Configures Row-Level Security (RLS) roles, DAX filter rules, perspectives, and access control in
  TMDL. Invoke whenever RLS, a security role, USERPRINCIPALNAME filtering, dynamic security, a
  perspective, or restricting which rows a given user may see is requested. Executes as part of
  Stage 6 — Security & Deployment.
---

# Power BI Security Skill

> **Authoring Policy (see `power-bi-dev`).** Executes as part of **Stage 6 — Security & Deployment**. RLS roles and perspectives are authored directly in TMDL files (`roles/*.tmdl`, `perspectives/*.tmdl`).

---

## RLS TMDL Syntax Example

```tmdl
role 'Regional Sales Manager'
	modelPermission: read

	tablePermission dCustomer = [Region] == USERPRINCIPALNAME()
```

- **Use `USERPRINCIPALNAME()`** for dynamic RLS security matching logged-in user UPNs.
- **Keep RLS Filters Simple:** Apply RLS filters on dimension tables (`d*`), allowing single-direction relationship filtering to propagate down to fact tables (`f*`).
