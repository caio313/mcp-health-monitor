# Política de datos — MCP Health Server

## Qué recopilamos
- Estado de los MCP servers que monitoreás (healthy/unhealthy)
- Latencia de respuesta en ms
- Cantidad de tools disponibles
- Timestamp de cada check

## Qué NO recopilamos
- Contenido de las respuestas de tus tools
- Datos de tus usuarios finales
- Credenciales o API keys

## Cómo usamos los datos
- Para mostrarte tu historial y drift detection
- Para generar benchmarks agregados y anonimizados
  comparando tu performance vs el ecosistema
- Nunca vendemos datos individuales identificados

## Cómo anonimizamos
Las URLs de tus MCP servers se convierten en un hash SHA256
irreversible antes de usarse en benchmarks cross-industry.
Nadie puede reconstruir tu URL a partir del hash.

## Tus derechos
- Podés solicitar eliminación de todos tus datos
- Podés exportar tu historial completo en formato JSON
