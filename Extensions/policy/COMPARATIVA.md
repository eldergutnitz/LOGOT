# Niveles de politica: cual elegir

_Simulado el 30/07/2026 sobre 5.466 instalaciones y 523 usuarios._

Los tres niveles comparten la misma politica de IA (**solo GitHub Copilot y lo que publique Microsoft**) y el mismo criterio de fondo: se permite por capacidad de trabajo, nunca por numero de usuarios. Lo que cambia es cuanta capacidad se considera imprescindible.

| Nivel | Entradas | Cobertura | Ext. bloqueadas | Usuarios afectados | Pierden 5+ |
|---|---:|---:|---:|---:|---:|
| **Completa** | 404 | 86,5% | 308 | 214 | 39 |
| Reducida | 355 | 83,8% | 356 | 244 | 46 |
| Minima | 125 | 73,1% | 586 | 304 | 87 |

## Perfiles

Un perfil no es un escalon mas de esa lista: es una politica pensada para un tipo de usuario concreto. No se deriva del inventario y no tiene por que ser subconjunto de los niveles de arriba.

| Perfil | Entradas | Para quien |
|---|---:|---|
| **Vibecoding** | 71 | Para perfiles que no programan y trabajan apoyados en Copilot. Copilot, todo lo oficial de Microsoft y GitHub, git, y una lista corta de basicos: formateo, errores a la vista, Markdown, previsualizacion web y lectura de datos. Ni fabricantes de stacks, ni lenguajes de nicho, ni cadenas de compilacion. No se deriva del inventario: estos usuarios aun no estan en la flota. |

## Que incluye cada uno

| Capacidad | Completa | Reducida | Minima | Vibecoding |
|---|---|---|---|---|
| Cadena estandar: lint, formato y calidad | si | si | si | — |
| Soporte de lenguaje y cadenas de compilacion | si | si | si | — |
| Depuradores | si | si | si | — |
| Red corporativa | si | si | si | si |
| Control de versiones | si | si | si | si |
| Utilidades adicionales de git | si | si | si | — |
| Pruebas | si | si | — | — |
| Acceso a datos | si | si | — | — |
| Autoria en Python | si | si | — | — |
| Desarrollo web y clientes de API | si | — | — | — |
| Documentacion y diagramas | si | — | — | — |
| Herramientas de stacks corporativos | si | — | — | — |
| Basicos para perfiles no tecnicos | — | — | — | si |
| *Admite altas por categoria* | si | si | no (lista cerrada) | no (lista cerrada) |
| *Exige repositorio declarado* | no | si | si | si |
| *Fabricantes permitidos* | 28 | 22 | 14 | 0 |

## Ficheros de cada nivel

| Nivel | Politica | Anotada | Impacto |
|---|---|---|---|
| Completa | `extensions.allowed.json` | `extensions.allowed.jsonc` | `IMPACTO.md` |
| Reducida | `extensions.allowed.reducida.json` | `extensions.allowed.reducida.jsonc` | `IMPACTO.reducida.md` |
| Minima | `extensions.allowed.minima.json` | `extensions.allowed.minima.jsonc` | `IMPACTO.minima.md` |
| Vibecoding | `extensions.allowed.vibecoding.json` | `extensions.allowed.vibecoding.jsonc` | `IMPACTO.vibecoding.md` |

## En que se diferencian

### Completa

Todo lo que aporta una capacidad de trabajo. Bloquea aspecto, snippets, packs, deprecadas y la IA no permitida.

### Reducida

Desarrollo, pruebas y acceso a datos, ademas del control de versiones que llevan todos los niveles. Fuera quedan documentacion, diagramas, clientes de API, los fabricantes secundarios y todo lo que no declara repositorio.

### Minima

Git y la cadena de edicion, y poco mas. Nada entra por categoria: solo Microsoft, GitHub, los fabricantes de los stacks corporativos y una lista cerrada de lenguaje, lint, formato, depuracion y control de versiones. Cualquier lenguaje de nicho que no este en esa lista tendra que pedirse por el canal de excepciones.

### Vibecoding

Para perfiles que no programan y trabajan apoyados en Copilot. Copilot, todo lo oficial de Microsoft y GitHub, git, y una lista corta de basicos: formateo, errores a la vista, Markdown, previsualizacion web y lectura de datos. Ni fabricantes de stacks, ni lenguajes de nicho, ni cadenas de compilacion. No se deriva del inventario: estos usuarios aun no estan en la flota.

## Recomendacion

**Vibecoding** es independiente: se asigna a quien no programa, no se "sube" ni se "baja" desde los otros niveles.

Para el resto de la flota, empezar por **Completa**: ya bloquea la IA no autorizada, la cosmetica, los packs, los snippets y las deprecadas, que es donde esta el riesgo real, y deja trabajar a todo el mundo. **Reducida** y **Minima** existen para endurecer despues, cuando el canal de excepciones este rodado y se sepa que se pide de verdad. Saltar directamente a Minima significa 5 o mas extensiones perdidas para muchos usuarios el primer dia.
