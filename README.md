# 🏛️ Licitaciones Públicas · España

Buscador de **licitaciones públicas abiertas** en España sobre los datos oficiales de la Plataforma de Contratación del Sector Público (PLACE). Sin registro y sin API key.

**▶ En vivo:** https://jpm70.github.io/licitaciones/

Parte del proyecto [Un Fantasma en el Sistema](https://www.unfantasmaenelsistema.com).

## Qué hace
- Busca por texto en título, organismo, expediente, tipo de contrato, lugar y código CPV.
- Muestra importe sin IVA, plazo de presentación, organismo, expediente, tipo y provincia, con enlace a la ficha oficial en PLACE.
- Las abiertas salen primero, ordenadas por plazo más próximo.

## De dónde salen los datos
[PLACE](https://contrataciondelestado.es) publica un feed Atom de datos abiertos (Ministerio de Hacienda). Ese feed **no permite CORS**, así que un navegador no puede leerlo directamente, y los proxies públicos gratuitos son poco fiables (el `allorigins` que usaba la primera versión no respondía).

Por eso los datos van por una copia propia:

1. `tools/update_feed.py` descarga el feed `sindicacion_643` (y las páginas anteriores enlazadas con `rel="next"`), se queda con las licitaciones en estado **PUB** (publicadas) y las acumula en `licitaciones.json`.
2. Una GitHub Action (`.github/workflows/update-feed.yml`) lo ejecuta **cada 4 horas** y hace commit si cambia.
3. La web lee `licitaciones.json` desde el mismo dominio.

Se descartan las que ya han pasado su plazo, y el fichero se limita a 8.000 licitaciones. Para regenerarlo a mano:

```bash
python tools/update_feed.py
```

## Limitaciones
- PLACE publica con retraso: la web indica en la barra de estado hasta qué fecha llegan los datos.
- Solo recoge lo que aparece en el feed de perfiles de contratante; no sustituye a una consulta en PLACE para presentar una oferta.
- Al arrancar, el histórico es de aproximadamente un día; crece con cada actualización.

## Desarrollo local
Es HTML estático (con `file://` falla la carga de `licitaciones.json`):

```bash
python -m http.server 8000
```

## Aviso
Datos abiertos de PLACE, Ministerio de Hacienda. Proyecto educativo y sin ánimo de lucro.
