# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Descripción del proyecto

Addons custom de Odoo 18 para el proyecto Maralva (Fábrica de Software Maralva / GDigital). Este repo se clona en el servidor como carpeta `gdigital-custom` dentro de cada instancia Odoo (ver `maralva-deploy`), y es la tercera pata del `addons_path` junto al core OCB y los repos OCA.

Ambos módulos están en fase de scaffolding: tienen manifest, seguridad y datos por defecto de compañía (país España / moneda EUR), pero aún **no contienen modelos ni vistas propias** (`ir.model.access.csv` vacío en los dos, `models/__init__.py` sin imports).

## Entorno técnico

- No hay entorno Python/PostgreSQL local en este checkout: Odoo corre en un servidor Linux remoto provisionado por `maralva-deploy` (`/opt/odoo/<version>/gdigital-custom` = este repo). Para probar cambios hay que desplegarlos/sincronizarlos al servidor, no ejecutar `odoo-bin` desde aquí.
- **Addons-path en servidor**: `odoo/addons,oca,gdigital-custom` (ver `maralva-deploy/scripts/02-odoo-setup.sh`).
- **Módulos custom de este repo**:
  - `maralva_base_internal` — pack maestro (`application: True`) con ~110 dependencias: CRM, ventas, proyectos, RRHH, website, timesheets, spreadsheet dashboards, y localización española (`l10n_es`, `l10n_es_edi_verifactu` para Verifactu). Fuerza país/moneda/logo de la compañía principal vía `data/res_company_data.xml`.
  - `maralva_conta` — pack de contabilidad más ligero ("Conta Gdigital"), depende solo de `account` y `account_edi`. Fuerza país/moneda/formato de papel de la compañía y activa el EUR.
- Ambos módulos fueron generados con `maralva-deploy/scripts/pack-maker.sh`, que scaffoldea `__init__.py`, `__manifest__.py`, `README.md`, `data/res_company_data.xml` y un `ir.model.access.csv` vacío a partir de una lista de dependencias en `maralva-deploy/config/pack_*.txt`.

## Convenciones del proyecto

- **Ramas**: por versión de Odoo (`18.0`, `19.0`), sin sufijo de módulo — no una rama por módulo.
- **Versión de Odoo**: 18.0 (Community + OCA), con soporte inicial 19.0 en preparación.
- **Estructura de manifest**: `security/ir.model.access.csv` + `data/res_company_data.xml` siempre presentes; `application: True`, licencia `AGPL-3`.
- **Datos de compañía**: cada módulo fuerza país=España y moneda=EUR sobre `base.main_company` vía XML `noupdate="1"`.

## Comandos habituales

No hay suite de tests ni linter configurados en este repo todavía. La actualización de módulo se hace en el servidor (fuera de este checkout), típicamente:

```bash
./odoo-bin -c odoo.conf -u maralva_base_internal,maralva_conta -d <nombre_bd> --stop-after-init
```

## Notas para Claude Code

- Este repo se trabaja **solo desde VS Code + extensión Claude Code** (edición, instalación, pruebas, ejecución de Odoo, revisión de diffs).
- Cowork (Claude en la app de escritorio) se usa aparte para seguimiento y documentación del proyecto, sin tocar este entorno técnico — ver `ESTADO.md` para la bitácora que Cowork puede consultar.
- Al final de cada sesión de trabajo, actualizar `ESTADO.md` con un resumen de lo hecho (pedir a Claude Code: "resume lo que hicimos hoy en ESTADO.md").