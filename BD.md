# Estructura de datos

## Schemas de PostgreSQL

La base de datos utiliza dos schemas separados para garantizar trazabilidad y reproducibilidad:

### `staging_`
Contiene los datos en **edición activa**. Las coordinaciones capturan y modifican aquí sus catálogos antes de publicarlos. La validación flexible permite trabajo incremental.

- Tablas: `staging_profesores`, `staging_materias`, `staging_grupos`, `staging_aulas`, etc.
- Estado: mutable, editable, con historial de cambios.

### `operative_`
Contiene los datos **publicados e inmutables**. Cada publicación genera un `release_id` único (hash + timestamp). El solver siempre opera sobre un `release_id` específico, garantizando reproducibilidad total.

- Tablas: `operative_profesores`, `operative_materias`, etc.
- Estado: inmutable. Solo se crea nueva versión con `POST /staging/publish`.
- Cada corrida del solver referencia su `release_id` para reproducibilidad.

---



## Coordinacion
- `PROFESORES` → Toda la informacion relacionada con los profesores.
- `MATERIAS` → Toda la informacion relacionada con los materias.
- `RELACION MATERIA-PROFESOR` → Relacion entre profesores y materias.
- `DISPONIBILIDAD DEL PROFESOR` → Horarios disponibles de cada profesor.
- `AULAS` → Datos de las aulas.
- `GRUPOS` → Informacion de grupos.
- `MATERIAS-GRUPÓS` → Relacion de los grupos con las materias que se ofertaran.
- `TURNOS-HORAS-DIAS` → Relacion de los turnos de clase con las horas.
- `DIAS-PREFERENCIAS` → Preferencias de las clases de materias por los dias.

## Registros
- `runs` → Registro de cada ejecución del solver (métricas, configuración, resultado).
- `solucion_x` → Valores activos de la variable de asignación X por ejecución.
- `solucion_w` → Valores de la variable de huecos de grupo W por ejecución.
- `solucion_r` → Valores de la variable de preferencias R por ejecución.


# Contenido de las Tablas

## Coordinacion

### PROFESORES
- `ID_PROFESOR` → Indentificador del profesor. 
- `NOMBRE` → Nombre del profesor.
- `HORAS_MAX` → Cantidad de horas que puede ocupar el profesor.
- `HORAS_MIN` → Cantidad de horas que debe ocupar el profesor.
- `ACTIVO` → Si el profesor esta activo o no.
- `NO_MATERIAS` → Numero de materias que imparte el profesor.
- `HORAS_DISPONIBLES` → Horas disponibles del profesor.
- `PRIORIDAD` → Escala de prioridad del profesor.

### MATERIAS
- `ID_MATERIA` → Identificador de la materia.
- `NOMBRE` → Nombre de la materia.
- `HORAS_SEMANA` → Cantidad de horas que imparte la materia.
- `TIPO` → Tipo de materia (obligatoria u optativa).
- `CARRERA` → Carrera a la que pertenece la materia.
- `PLAN` → Plan de estudios de la materia.
- `PREFERENCIA` → Preferencia de la materia por dias de la semana.
- `TIPO_DE_AULA` → Tipo de aula donde se imparte la materia.
- `SEMESTRE` → Semestre en el que se imparte la materia.
- `NO_DE_PROFESORES` → Numero de profesores que imparten la materia.
- `GRUPOS_ABIERTOS` → Numero de grupos abiertos para la materia.

### RELACION MATERIA-PROFESOR
- `ID_MATERIA` → Id de la Materia de la tabla `MATERIAS`
- `ID_PROFESOR` → Id del profesor de la tabla `PROFESORES`
- `SEMESTRE` → Semestre en el que se imparte la materia.
- `AFINIDAD` → Afinidad del profesor con la materia.
- `PRIORIDAD` → Prioridad del profesor con la materia.

### DISPONIBILIDAD DEL PROFESOR
- `ID_PROFESOR` → Id del profeso de la tabla `PROFESORES`
- `DIA` → Dia de la semana.
- `PESO` → Grado de prioridad entre la disponibilidad del profesor y el dia.

### AULAS
- `ID_AULA` → Id del aula.
- `NOMBRE` → Nombre del aula.
- `CARRERA` → Carrera a la que pertenece el aula.
- `TIPO_DE_AULA` → Tipo de aula.

### GRUPOS
- `ID_GRUPO` → Id del grupo.
- `GRUPO` → Nombre del grupo.
- `CARRERA` → Carrera a la que pertenece el grupo.
- `TURNO` → Turno al que pertenece el grupo.
- `ID_AULA` → Id del aula al que pertenece el grupo.
- `SEMESTRE` → Semestre en el que se imparte el grupo.
- `ACTIVO` → Si el grupo esta activo o no.

### MATERIAS-GRUPÓS
- `ID_MATERIA` → Id de la materia de la tabla `MATERIAS`
- `ID_GRUPO` → id del grupo de la tabla `GRUPOS`
- `SEMESTRE` → Semestre en el que se imparte el grupo.

### TURNOS-HORAS-DIAS
- `TURNO` → Turno.
- `HORA` → Hora del dia.
- `PESO` → Peso de la prioridad entre el turno y la hora.

### DIAS-PREFERENCIAS
- `PREFERENCIA` → Preferencia de la materia por dia de la semana.
- `DIA` → Dia de la semana.
- `PESO` → Peso de la prioridad entre la preferencia de la materia y el dia.


## Registros

### runs
Tabla principal. Una fila por ejecución del solver. Escrita por `model/utils.py::registrar_run()`.  
Implementada en `scripts/init_db.py`. Base de datos: `results/experiments.db`.

| Campo             | Tipo    | Descripción                                              |
|-------------------|---------|----------------------------------------------------------|
| `id`              | INTEGER | Clave primaria autoincremental                           |
| `experiment`      | TEXT    | Tipo de experimento: `full`, `benchmark`, `sensitivity`  |
| `release_id`      | TEXT    | Versión del dataset usado (hash o etiqueta)              |
| `solver`          | TEXT    | Solver aplicado: `gurobi`, `highs`, `cbc`, `glpk`       |
| `semestre`        | INTEGER | Semestre resuelto (1–9)                                  |
| `replica`         | INTEGER | Número de réplica dentro del experimento                 |
| `permutacion`     | TEXT    | Orden de semestres procesados, ej. `"1-3-5-9"`           |
| `huecos_grupo`    | INTEGER | 1 si se minimizaron huecos de grupo en la FO             |
| `huecos_prof`     | INTEGER | 1 si se minimizaron huecos del profesor en la FO         |
| `preferencias`    | INTEGER | 1 si se incluyeron preferencias en la FO                 |
| `disjuntives`     | INTEGER | 1 si se usaron restricciones disyuntivas                 |
| `peso_tn`         | REAL    | Factor de escala aplicado al parámetro `tn` (turno/hora) |
| `peso_md`         | REAL    | Factor de escala aplicado al parámetro `md` (día)        |
| `peso_ags`        | REAL    | Factor de escala aplicado al parámetro `ags` (aula)      |
| `status`          | TEXT    | `optimal`, `feasible`, `timeout`, `infeasible`, `error`  |
| `obj_val`         | REAL    | Valor de la función objetivo                             |
| `tiempo_total_s`  | REAL    | Tiempo total de ejecución (segundos)                     |
| `tiempo_solver_s` | REAL    | Tiempo de resolución del solver (segundos)               |
| `cpu_percent`     | REAL    | Uso de CPU al momento del registro                       |
| `ram_percent`     | REAL    | Uso de RAM al momento del registro                       |
| `n_variables`     | INTEGER | Número de variables del modelo                           |
| `n_restricciones` | INTEGER | Número de restricciones del modelo                       |
| `modelo_version`  | TEXT    | Versión del código del modelo                            |
| `fecha`           | TEXT    | Timestamp automático al insertar (`datetime('now')`)     |
| `notas`           | TEXT    | Notas libres (escenario de sensibilidad, flags, etc.)    |

---

### solucion_x
Valores activos de la variable de asignación **X** (profesor–materia–día–hora–aula–grupo).  
Una fila por variable con valor > 0. Referencia a `runs.id`.  
> Actualmente los runners guardan esta información en CSV (`results/solutions/`). Esta tabla está disponible para migrar si se requiere consulta SQL sobre las soluciones.

| Campo      | Tipo    | Descripción                          |
|------------|---------|--------------------------------------|
| `id`       | INTEGER | Clave primaria autoincremental       |
| `run_id`   | INTEGER | FK → `runs.id`                       |
| `profesor` | TEXT    | Identificador del profesor           |
| `materia`  | TEXT    | Identificador de la materia          |
| `dia`      | TEXT    | Día de la semana                     |
| `hora`     | INTEGER | Hora del bloque                      |
| `aula`     | TEXT    | Identificador del aula               |
| `grupo`    | TEXT    | Identificador del grupo              |
| `valor`    | REAL    | Valor de la variable (típicamente 1) |

---

### solucion_w
Valores de la variable de huecos de grupo **W** (día–hora–grupo).  
Activa solo cuando `huecos_grupo = 1` en la corrida correspondiente.

| Campo    | Tipo    | Descripción                    |
|----------|---------|--------------------------------|
| `id`     | INTEGER | Clave primaria autoincremental |
| `run_id` | INTEGER | FK → `runs.id`                 |
| `dia`    | TEXT    | Día de la semana               |
| `hora`   | INTEGER | Hora del bloque                |
| `grupo`  | TEXT    | Identificador del grupo        |
| `valor`  | REAL    | Valor de la variable           |

---

### solucion_r
Valores de la variable de preferencias **R** (materia–día–hora–aula–grupo).  
Activa solo cuando `preferencias = 1` en la corrida correspondiente.

| Campo     | Tipo    | Descripción                    |
|-----------|---------|--------------------------------|
| `id`      | INTEGER | Clave primaria autoincremental |
| `run_id`  | INTEGER | FK → `runs.id`                 |
| `materia` | TEXT    | Identificador de la materia    |
| `dia`     | TEXT    | Día de la semana               |
| `hora`    | INTEGER | Hora del bloque                |
| `aula`    | TEXT    | Identificador del aula         |
| `grupo`   | TEXT    | Identificador del grupo        |
| `valor`   | REAL    | Valor de la variable           |
