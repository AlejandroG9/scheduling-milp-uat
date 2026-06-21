import pyomo.environ as pyo
from pathlib import Path
import pandas as pd
import os
import logging
from model.utils import etapa_registrada, guardar_registro_csv, guardar_registro_sqlite, obtener_siguiente_iteracion

# === Preparar registro y archivo CSV ===
archivo_csv = Path(__file__).resolve().parents[1] / "results" / "reporte_modelo.csv"
archivo_csv.parent.mkdir(parents=True, exist_ok=True)







#archivo = 'Generador/Datos/Datos_para_modelos.xlsx'


def crear_modelo_horarios(semestre,permutacion,datos,solucion=None, impresion = False,
                          huecos_grupo  = True,
                          preferencias  = False,
                          huecos_prof   = False,
                          disjuntives   = False):

    # Verifica si ya existe el archivo para saber el número de iteración
    iteracion_actual = obtener_siguiente_iteracion()
    versio_modelo = "constructor_decorador"

    # Lista para guardar registros
    registros = []

    # Leer datos del archivo Excel
    with etapa_registrada("Cargar Datos", iteracion_actual, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        df_profesores               = datos["df_profesores"]
        df_profesores_disponibles   = datos["df_profesores_disponibles"]
        df_materias                 = datos["df_materias"]
        df_materias_profesores      = datos["df_materias_profesores"]
        df_aulas                    = datos["df_aulas"]
        df_grupos                   = datos["df_grupos"]
        df_materias_grupos          = datos["df_materias_grupos"]
        df_turnos_horas             = datos["df_turnos_horas"]
        df_turnos_grupos            = datos["df_turnos_grupos"]
        df_dias_preferencias        = datos["df_dias_preferencias"]
        df_materias_dias            = datos["df_materias_dias"]
        df_aulas_disponibles        = datos["df_aulas_disponibles"]
        #df_materias_aulas = df_aulas.merge(df_materias, on='AULA')
        df_profesores_disp_bin      = datos["df_profesores_disp_bin"]

    with etapa_registrada("Filtrar Datos", iteracion_actual, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        aula_clase                  = df_grupos[df_grupos['SEMESTRE'] == semestre]
        df_aulas_ocupadas           = df_grupos[(~df_grupos['SEMESTRE'].isin(permutacion)) & (~df_grupos['ID_AULA'].isin(aula_clase['ID_AULA']))]
        df_materias                 = df_materias[df_materias['SEMESTRE'] == semestre]
        df_materias_profesores      = df_materias_profesores[df_materias_profesores['SEMESTRE'] == semestre]
        df_profesores               = df_profesores[df_profesores['id'].isin(df_materias_profesores['ID_PROFESOR'])]
        df_profesores_disponibles   = df_profesores_disponibles[df_profesores_disponibles['ID_PROFESOR'].isin(df_profesores['id'])]
        df_profesores_disp_bin      = df_profesores_disp_bin[df_profesores_disp_bin['ID_PROFESOR'].isin(df_profesores['id'])]
        df_grupos                   = df_grupos[df_grupos['SEMESTRE'] == semestre]
        df_materias_grupos          = df_materias_grupos[df_materias_grupos['SEMESTRE'] == semestre]
        df_grupos                   = df_grupos[df_grupos['id'].isin(df_materias_grupos['ID_GRUPOS'])]
        df_turnos_grupos            = df_turnos_grupos[df_turnos_grupos['SEMESTRE'] == semestre]
        df_turnos_grupos            = df_turnos_grupos[df_turnos_grupos['id'].isin(df_grupos['id'])]
        df_materias_dias            = df_materias_dias[df_materias_dias['SEMESTRE'] == semestre]
        df_aulas                    = df_aulas[(df_aulas['CARRERA'] == 'IIS') | (df_aulas['CARRERA'] == 'GENERAL')]
        df_aulas                    = df_aulas[~df_aulas['id'].isin(df_aulas_ocupadas['ID_AULA'])]
        df_materias_sem             = df_materias[df_materias['Preferencia'] == 'Semana']
        df_materias_fin             = df_materias[df_materias['Preferencia'] == 'Fin']
        df_materias_var             = df_materias[df_materias['Preferencia'] == 'Variable']
        df_materias_lab             = df_materias[df_materias['TIPO_DE_AULA'] != 'NORMAL']
        df_aulas_lab                = df_aulas[df_aulas['TIPO_DE_AULA'].isin(df_materias_lab['TIPO_DE_AULA'])]
        df_aulas                    = df_aulas[(df_aulas['TIPO_DE_AULA'] == 'NORMAL') | df_aulas['id'].isin(df_aulas_lab['id'])]
        df_aulas_disponibles        = df_aulas_disponibles[df_aulas_disponibles['ID_AULA'].isin(df_aulas['id'])]

    print("Datos cargados correctamente\n")


    # Crear un modelo concreto
    modelo = pyo.ConcreteModel("Modelo de Horarios")

    # Definir los conjuntos
    with etapa_registrada("Definicion de Conjuntos", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        modelo.PROFESORES       = pyo.Set(initialize=[str(p) for p in df_profesores['id']])
        modelo.MATERIAS         = pyo.Set(initialize=[str(m) for m in df_materias['id']])
        modelo.MATERIAS_SEM     = pyo.Set(initialize=[str(m) for m in df_materias_sem['id']], within=modelo.MATERIAS)
        modelo.MATERIAS_FIN     = pyo.Set(initialize=[str(m) for m in df_materias_fin['id']], within=modelo.MATERIAS)
        modelo.MATERIAS_VAR     = pyo.Set(initialize=[str(m) for m in df_materias_var['id']], within=modelo.MATERIAS)
        modelo.MATERIAS_LAB     = pyo.Set(initialize=[str(m) for m in df_materias_lab['id']], within=modelo.MATERIAS)
        modelo.DIAS             = pyo.Set(initialize=["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"])
        modelo.HORAS            = pyo.Set(initialize=[7,8,9,10,11,12,13,14,15,16,17,18,19,20], ordered=True)
        modelo.AULAS            = pyo.Set(initialize=[str(a) for a in df_aulas['id']])
        modelo.AULAS_LAB        = pyo.Set(initialize=[str(a) for a in df_aulas_lab['id']], within=modelo.AULAS)
        modelo.GRUPOS           = pyo.Set(initialize=[str(g) for g in df_grupos['id']])



    if False:
        print(f'Numero de Profesores = {len(modelo.PROFESORES)}')
        modelo.PROFESORES.pprint()
        print(f'Numero de Materias = {len(modelo.MATERIAS)}')
        modelo.MATERIAS.pprint()
        print(f'Numero de Materias Semana = {len(modelo.MATERIAS_SEM)}')
        modelo.MATERIAS_SEM.pprint()
        print(f'Numero de Materias Fin = {len(modelo.MATERIAS_FIN)}')
        modelo.MATERIAS_FIN.pprint()
        print(f'Numero de Materias Variable = {len(modelo.MATERIAS_VAR)}')
        modelo.MATERIAS_VAR.pprint()
        print(f'Numero de Materias Lab = {len(modelo.MATERIAS_LAB)}')
        modelo.MATERIAS_LAB.pprint()
        print(f'Numero de Aulas = {len(modelo.AULAS)}')
        modelo.AULAS.pprint()
        print(f'Numero de Aulas Lab = {len(modelo.AULAS_LAB)}')
        modelo.AULAS_LAB.pprint()
        print(f'Numero de Grupos = {len(modelo.GRUPOS)}')
        modelo.GRUPOS.pprint()




    print("\nConjuntos definidos correctamente")

    # Crear diccionarios desde Excel
    horas_max_dict          = {str(row['id']): row['horas_max'] if pd.notna(row['horas_max']) else 20
                            for _, row in df_profesores.iterrows()}
    horas_mat_dict          = {str(row['id']): row['horas_semana'] if pd.notna(row['horas_semana']) else 0
                            for _, row in df_materias.iterrows()}
    horas_con_dict          = {str(row['id']): row['horas_continuas'] if pd.notna(row['horas_continuas']) else 2
                            for _, row in df_materias.iterrows()}
    tipo_aula_dict          = {str(row['id']): row['TIPO_DE_AULA']
                            for _, row in df_aulas.iterrows()}
    materias_aulas          = {(str(row['id'])): str(row['TIPO_DE_AULA'])
                            for _, row in df_materias.iterrows()}

    # Crear diccionario de materias permitidas por profesor
    materias_permitidas     = {(str(row['ID_PROFESOR']), str(row['ID_MATERIA'])): 1
                            for _, row in df_materias_profesores.iterrows()}
    # Crear diccionario de prioridad de profesores por materias
    materias_profesores     = {(str(row['ID_PROFESOR']), str(row['ID_MATERIA'])): int(row['PRIORIDAD'])
                            for _, row in df_materias_profesores.iterrows()}
    # Crear diccionario de materias  por grupos
    materias_por_grupo      = {(str(row['ID_MATERIA']), str(row['ID_GRUPOS'])): 1
                            for _, row in df_materias_grupos.iterrows()}
    # Crear diccionario de Relacion grupos por Horas
    turnos_horas_grupo      = {(str(row['Dia']), int(row['Hora']), row['id']): int(row['Peso'])
                            for _, row in df_turnos_grupos.iterrows()}
    # Crear diccionario de Relacion de preferencia de materias por dias
    materias_preferencias   = {(str(row['id']), row['Dia']): row['Peso']
                            for _, row in df_materias_dias.iterrows()}
    # Crear diccionario de aulas grupos
    aulas_grupos_semestre   = {(str(row['ID_AULA']), str(row['id'])): 1
                            for _, row in df_grupos.iterrows()}
    # Crear diccionario de profesores disponibles
    profesores_disponibles  = {(str(row['ID_PROFESOR']),(str(row['Dia'])), row['HORA']): int(row['PESO'])
                            for _, row in df_profesores_disponibles.iterrows()}
    profesores_disp_bin     = {(str(row['ID_PROFESOR']),(str(row['DIA'])), row['HORA']): int(row['DISPONIBLE'])
                            for _, row in df_profesores_disp_bin.iterrows()}
    # Crear diccionario de disponiblidad de aulas
    aulas_disponibles       = {(str(row['DIA']), int(row['HORA']), str(row['ID_AULA'])): int(row['DISPONIBLE'])
                            for _, row in df_aulas_disponibles.iterrows()}

    # Definir parámetros
    with etapa_registrada("Definicion de Parametros", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        modelo.h_max            = pyo.Param(modelo.PROFESORES, initialize=horas_max_dict,
                                            doc="Número máximo de horas por profesor")
        modelo.h_mat            = pyo.Param(modelo.MATERIAS, initialize=horas_mat_dict,
                                            doc="Numero de horas por semana de cada materia")
        modelo.h_con            = pyo.Param(modelo.MATERIAS, initialize=horas_con_dict,
                                            doc="Numero de horas continuas permitidas de cada materia")
        modelo.y                = pyo.Param(modelo.PROFESORES, modelo.MATERIAS,  initialize=materias_permitidas,
                                            default=0, doc="1 si el profesor puede dar la materia, 0 si no")
        modelo.u                = pyo.Param(modelo.MATERIAS, modelo.GRUPOS, initialize=materias_por_grupo,
                                            default=0, doc="1 si la materia se da en el grupo, 0 si no")
        modelo.tn               = pyo.Param(modelo.DIAS, modelo.HORAS, modelo.GRUPOS, initialize=turnos_horas_grupo,
                                            default=20, doc="Preferencia de los grupos por horas/turnos")
        modelo.md               = pyo.Param(modelo.MATERIAS, modelo.DIAS, initialize=materias_preferencias,
                                            default=0, doc="Prefencia de las materias por dia")
        modelo.ags              = pyo.Param(modelo.AULAS,modelo.GRUPOS, initialize=aulas_grupos_semestre,
                                            default=5, doc="Preferencias de aulas por grupos")
        modelo.prio             = pyo.Param(modelo.PROFESORES, modelo.MATERIAS, initialize=materias_profesores,
                                            default=6, doc="Prioridad de los profesores por materias")
        #modelo.ta = pyo.Param(modelo.AULAS, initialize=tipo_aula_dict,
        #                         doc="Tipo de aula")
        modelo.mta              = pyo.Param(modelo.MATERIAS, initialize=materias_aulas,
                                            within=pyo.Any, doc="Tipo de aula de las materias")
        modelo.dis_pref         = pyo.Param(modelo.PROFESORES, modelo.DIAS, modelo.HORAS, initialize=profesores_disponibles,
                                            default=20, doc="Peso si el profesor p esta disponible en la hora h")
        modelo.dis_bin          = pyo.Param(modelo.PROFESORES, modelo.DIAS, modelo.HORAS, initialize=profesores_disp_bin,
                                           default=0, doc="1 si el profesor p esta disponible en la hora h")
        modelo.dia              = pyo.Param(modelo.DIAS,modelo.HORAS,modelo.AULAS, initialize=aulas_disponibles,
                                            default=0, doc="1 si el aula a esta disponible en el dia d a la hora h")
        modelo.base             = pyo.Param(initialize=0, doc="Base de la función objetivo")



    print("\nParámetros definidos correctamente")
    #modelo.tn.pprint()

    modelo.x = pyo.Var(modelo.PROFESORES,
                    modelo.MATERIAS,
                    modelo.DIAS,
                    modelo.HORAS,
                    modelo.AULAS,
                    modelo.GRUPOS,
                    domain=pyo.Binary,
                    initialize=0,
                    doc="1 si el profesor p da la materia m el día d a la hora h en el aula a en el grupo g")
    if preferencias:
        modelo.r = pyo.Var(
                        modelo.PROFESORES,
                        modelo.MATERIAS,
                        modelo.DIAS,
                        modelo.HORAS,
                        modelo.AULAS,
                        modelo.GRUPOS,
                        domain=pyo.NonNegativeIntegers,
                        initialize=0,
                        doc="Resultado de mamultiplicaicon de preferencias de materias por dia y grupos por hora")

    if huecos_grupo:
        modelo.w = pyo.Var(modelo.DIAS,
                        modelo.HORAS,
                        modelo.GRUPOS,
                        domain=pyo.Binary,
                        initialize=1,
                        doc="1 si hay un hueco en el día d a la hora h en el grupo g")
        modelo.z = pyo.Var(modelo.DIAS,
                        modelo.HORAS,
                        modelo.GRUPOS,
                        domain=pyo.Binary,
                        initialize=0,
                        doc="1 si hay alguna clase en el día d a la hora h en el grupo g")
        modelo.k = pyo.Var(modelo.DIAS,
                        modelo.HORAS,
                        modelo.GRUPOS,
                        domain=pyo.Binary,
                        initialize=0,
                        doc="1 si existe una clases antes y una clase despues")
        modelo.s = pyo.Var(modelo.DIAS,
                        modelo.HORAS,
                        modelo.GRUPOS,
                        domain=pyo.Binary,
                        initialize=0,
                        doc="1 si existe almenos una clase el dia d antes de la hora h en el grupo g")
        modelo.t = pyo.Var(modelo.DIAS,
                        modelo.HORAS,
                        modelo.GRUPOS,
                        domain=pyo.Binary,
                        initialize=0,
                        doc="1 si existe almenos una clase el dia d despues de la hora h en el grupo g")

    if huecos_prof:
        modelo.l = pyo.Var(modelo.PROFESORES,
                           modelo.DIAS,
                        modelo.HORAS,
                        domain=pyo.Binary,
                        initialize=0,
                        doc="1 si hay un hueco en el profesor o en el día d a la hora h")
        modelo.e = pyo.Var(modelo.PROFESORES,
                           modelo.DIAS,
                        modelo.HORAS,
                        domain=pyo.Binary,
                        initialize=0,
                        doc="1 si hay alguna clase en el día d a la hora h en el grupo g")
        modelo.f = pyo.Var(modelo.PROFESORES,
                           modelo.DIAS,
                        modelo.HORAS,
                        domain=pyo.Binary,
                        initialize=0,
                        doc="1 si existe una clase antes y una clase despues en el horario del profesor p")
        modelo.i = pyo.Var(modelo.PROFESORES,
                           modelo.DIAS,
                        modelo.HORAS,
                        domain=pyo.Binary,
                        initialize=0,
                        doc="1 si existe almenos una clase el dia d antes de la hora h en el grupo g")
        modelo.j = pyo.Var(modelo.PROFESORES,
                        modelo.DIAS,
                        modelo.HORAS,
                        domain=pyo.Binary,
                        initialize=0,
                        doc="1 si existe almenos una clase el dia d despues de la hora h en el grupo g")
    modelo.v = pyo.Var(modelo.PROFESORES, 
                    modelo.MATERIAS, 
                    modelo.HORAS, 
                    modelo.AULAS, 
                    modelo.GRUPOS,
                    domain=pyo.Binary,
                    initialize=0,
                    doc="1 si al profesor p le fue asignada la materia m a cierta hora h en el aula a en el grupo g en el semestre s")
    modelo.q = pyo.Var(modelo.PROFESORES, 
                    modelo.MATERIAS, 
                    modelo.DIAS, 
                    modelo.AULAS, 
                    modelo.GRUPOS,
                        domain=pyo.Binary,
                    initialize=0,
                    doc="1 si al profesor p le fue asignada la materia m a cierta dia d en el aula a en el grupo g en el semestre s")

    print("\nVariables definidas correctamente")

    # modelo.M = pyo.Param(initialize=1000, mutable=True, 
    #                  doc = "Gran M para generar disyuntivas")  # Ajusta este valor según la escala de tu problema


    # FUNCION OBJETIVO: MINIMIZAR HUECOS
    with etapa_registrada("Funcion Objetivo", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Objective(sense=pyo.minimize,doc="Minimizar el número de huecos en el horario" )
        def objetivo(modelo):
            total = 0

            if huecos_grupo:
                suma_huecos_grupo = sum(modelo.w[d,h,g] for d in modelo.DIAS for h in modelo.HORAS for g in modelo.GRUPOS)
                total += suma_huecos_grupo

            if preferencias:
                suma_preferencias = sum(modelo.r[p,m,d,h,a,g]  for p in modelo.PROFESORES for m in modelo.MATERIAS
                                    for d in modelo.DIAS  for h in modelo.HORAS for a in modelo.AULAS  for g in modelo.GRUPOS)
                total += suma_preferencias

            if huecos_prof:
                suma_huecos_prof = sum(modelo.l[p,d,h] for p in modelo.PROFESORES for d in modelo.DIAS for h in modelo.HORAS)
                total += suma_huecos_prof

            return total

        if impresion:
            print("\nFunción objetivo definida correctamente")




    if huecos_grupo:
        # RESTRICCIÓN PARA DEFINIR SI HAY CLASE EN UNA HORA
        with etapa_registrada("Restriccion Construccion Z", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                              semestre=semestre, permutacion=permutacion):
            @modelo.Constraint(modelo.DIAS, modelo.HORAS, modelo.GRUPOS,
                doc="Define si hay alguna clase el día d en la hora h en el grupo g")
            def restriccion_hora_ocupada(modelo,d,h,g):
                return modelo.z[d,h,g] == sum(modelo.x[p,m,d,h,a,g]
                                            for p in modelo.PROFESORES
                                            for m in modelo.MATERIAS
                                            for a in modelo.AULAS)
            if impresion:
                print("\nRestricción de hora ocupada definida correctamente")


        # RESTRICCIÓN PARA DEFINIR SI HAY CLASE ANTES Y DESPUES
        with etapa_registrada("Restriccion Construccion K", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                              semestre=semestre, permutacion=permutacion):
            @modelo.Constraint(modelo.DIAS, modelo.HORAS, modelo.GRUPOS,
                 doc= "Define si hay clase antes y después de una hora para modelar huecos")
            def restriccion_aux_hueco(modelo, d, h,g):
                if h == min(modelo.HORAS) or h == max(modelo.HORAS):
                    return modelo.k[d,h,g] == 0
                else:
                    return modelo.k[d,h,g] == modelo.s[d,h,g] + modelo.t[d,h,g] - 1


        # LINEARIZAR EL PRODUCTO k * (1 - z)
        with etapa_registrada("Restriccion Construccion W1", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                              semestre=semestre, permutacion=permutacion):
            @modelo.Constraint( modelo.DIAS, modelo.HORAS,modelo.GRUPOS,
                       doc="Fuerza w = 1 cuando hay un hueco" )
            def restriccion_huecos_forzar_1(modelo,d,h,g):
                if h == min(modelo.HORAS) or h == max(modelo.HORAS):
                    return modelo.w[d,h,g] == 0
                else:
                    # Linearización del producto binario
                    return modelo.w[d,h,g] <= modelo.k[d,h,g]                   # w <= k


        # LINEARIZAR EL PRODUCTO k * (1 - z)
        with etapa_registrada("Restriccion Construccion W2", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                              semestre=semestre, permutacion=permutacion):
            @modelo.Constraint(modelo.DIAS, modelo.HORAS,modelo.GRUPOS,
                 doc="Fuerza w[d,h] = 1 cuando hay un hueco" )
            def restriccion_huecos_forza_2(modelo,d,h,g):
                if h == min(modelo.HORAS) or h == max(modelo.HORAS):
                    return modelo.w[d,h,g] == 0
                else:
                    # Linearización del producto binario
                    return modelo.w[d,h,g] <= 1 - modelo.z[d,h,g]                # w <= 1 - z


         # LINEARIZAR EL PRODUCTO k * (1 - z)
        with etapa_registrada("Restriccion Construccion W3", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                              semestre=semestre, permutacion=permutacion):
            @modelo.Constraint( modelo.DIAS, modelo.HORAS,modelo.GRUPOS,
                doc="Fuerza w[d,h] = 1 cuando hay un hueco")
            def restriccion_huecos_forzar_3(modelo, d, h,g):
                if h == min(modelo.HORAS) or h == max(modelo.HORAS):
                    return modelo.w[d,h,g] == 0
                else:
                    # Linearización del producto binario
                    return modelo.w[d,h,g] >= modelo.k[d,h,g] + (1 - modelo.z[d,h,g]) - 1  # w >= k + (1 - z) - 1


        # RESTRICCION DE CLASES CONSECUTIVAS
        with etapa_registrada("Restriccion Continuidad de Horas", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                              semestre=semestre, permutacion=permutacion):
            @modelo.Constraint( modelo.DIAS, modelo.HORAS, modelo.GRUPOS,
                doc="Asegura que las clases sean consecutivas en cada día" )
            def restriccion_clases_consecutivas(modelo,d,h,g):
                if h == min(modelo.HORAS):
                    # Si es la hora mínima, debe haber una clase en la siguiente hora
                    return modelo.z[d,h,g] <= modelo.z[d,h+1,g]
                elif h == max(modelo.HORAS):
                    # Si es la hora máxima, debe haber una clase en la hora anterior
                    return modelo.z[d,h,g] <= modelo.z[d,h-1,g]
                else:
                    # Para horas intermedias, debe haber clase en h-1 o h+1
                    return modelo.z[d,h,g] <= modelo.z[d,h-1,g] + modelo.z[d,h+1,g]
            if impresion:
                print("\nRestricción de clases consecutivas definida correctamente")

        # RESTRICCION DE HORAS ANTES
        with etapa_registrada("Restriccion Construccion de S", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                              semestre=semestre, permutacion=permutacion):
            modelo.restriccion_horas_antes = pyo.ConstraintList()
            for d in modelo.DIAS:
                for h in modelo.HORAS:
                    for g in modelo.GRUPOS:
                        if h == min(modelo.HORAS):
                            modelo.restriccion_horas_antes.add(modelo.s[d,h,g] == 0)
                        else:
                            for k in modelo.HORAS:
                                if k < h:
                                    modelo.restriccion_horas_antes.add(
                                        modelo.s[d,h,g] >= modelo.z[d,k,g]
                                    )
            if impresion:
                print("\nRestricción de horas antes definida correctamente")

        # RESTRICCION DE HORAS DESPUES
        with etapa_registrada("Restriccion Construccion de T", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                              semestre=semestre, permutacion=permutacion):
            modelo.restriccion_horas_despues = pyo.ConstraintList()
            for d in modelo.DIAS:
                for h in modelo.HORAS:
                    for g in modelo.GRUPOS:
                        if h == max(modelo.HORAS):
                            modelo.restriccion_horas_despues.add(modelo.t[d,h,g] == 0)
                        else:
                            for k in modelo.HORAS:
                                if k > h:
                                    modelo.restriccion_horas_despues.add(
                                        modelo.t[d,h,g] >= modelo.z[d,k,g]
                                    )

            if impresion:
                print("\nRestricción de horas despues definida correctamente")

    #PRODUCTO DE PREFRENCIAS
    if preferencias:
        with etapa_registrada("Restriccion Construccion de R", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                              semestre=semestre, permutacion=permutacion):
            @modelo.Constraint( modelo.PROFESORES, modelo.MATERIAS, modelo.DIAS, modelo.HORAS,modelo.AULAS, modelo.GRUPOS,
                                doc="Producto de preferencias de materias por dia y grupos por hora" )
            def producto_de_preferencias(modelo,p,m,d,h,a,g):
                return modelo.r[p,m,d,h,a,g] == modelo.prio[p,m] * modelo.ags[a,g] * modelo.md[m,d] * modelo.tn[d,h,g] * modelo.dis_pref[p,d,h] * modelo.x[p,m,d,h,a,g]
            if impresion:
                print("\nRestricción de producto de preferencias definida correctamente")


    if huecos_prof:
        # RESTRICCIÓN PARA DEFINIR SI HAY CLASE EN UNA HORA
        with etapa_registrada("Restriccion Construccion de E", iteracion_actual, modelo, version=versio_modelo, registros=registros):
            @modelo.Constraint( modelo.PROFESORES,modelo.DIAS, modelo.HORAS,
                 doc="Define si hay alguna clase el día d en la hora h en el grupo g" )
            def restriccion_hora_ocupada_profesores(modelo,p,d,h):
                return modelo.e[p,d,h] == sum(modelo.x[p,m,d,h,a,g]
                                            for m in modelo.MATERIAS
                                            for a in modelo.AULAS
                                            for g in modelo.GRUPOS)
            if impresion:
                print("\nRestricción de hora ocupada del profesor definida correctamente")



        # RESTRICCIÓN PARA DEFINIR SI HAY CLASE ANTES Y DESPUES
        with etapa_registrada("Restriccion Construccion de F", iteracion_actual, modelo, version=versio_modelo, registros=registros):
            @modelo.Constraint(modelo.PROFESORES, modelo.DIAS, modelo.HORAS)
            def restriccion_aux_hueco_profesores(modelo,p,d,h):
                if h == min(modelo.HORAS) or h == max(modelo.HORAS):
                    return modelo.f[p,d,h] == 0
                return modelo.f[p,d,h] == modelo.i[p,d,h] + modelo.j[p,d,h] - 1



        # Linearizar el producto k * (1 - z)
        with etapa_registrada("Restriccion Construccion de L1", iteracion_actual, modelo, version=versio_modelo, registros=registros):
            @modelo.Constraint( modelo.PROFESORES, modelo.DIAS, modelo.HORAS,
                doc="Fuerza w = 1 cuando hay un hueco")
            def restriccion_huecos_forzar_profesores_1(modelo,p,d,h):
                if h == min(modelo.HORAS) or h == max(modelo.HORAS):
                    return modelo.l[p,d,h] == 0
                else:
                    # Linearización del producto binario
                    return modelo.l[p,d,h] <= modelo.f[p,d,h]                   # w <= k


        # Linearizar el producto k * (1 - z)
        with etapa_registrada("Restriccion Construccion de L2", iteracion_actual, modelo, version=versio_modelo, registros=registros):
            @modelo.Constraint(modelo.PROFESORES, modelo.DIAS, modelo.HORAS,
                doc="Fuerza w[d,h] = 1 cuando hay un hueco" )
            def restriccion_huecos_forzar_profesores_2(modelo,p,d,h):
                if h == min(modelo.HORAS) or h == max(modelo.HORAS):
                    return modelo.l[p,d,h] == 0
                else:
                    # Linearización del producto binario
                    return modelo.l[p,d,h] <= 1 - modelo.e[p,d,h]                # w <= 1 - z


        # Linearizar el producto k * (1 - z)
        with etapa_registrada("Restriccion Construccion de L3", iteracion_actual, modelo, version=versio_modelo, registros=registros):
            @modelo.Constraint( modelo.PROFESORES, modelo.DIAS, modelo.HORAS,
                doc="Fuerza w[d,h] = 1 cuando hay un hueco" )
            def restriccion_huecos_forzar_profesores_3(modelo, p, d, h):
                if h == min(modelo.HORAS) or h == max(modelo.HORAS):
                    return modelo.l[p,d,h] == 0
                else:
                    # Linearización del producto binario
                    return modelo.l[p,d,h] >= modelo.f[p,d,h] + (1 - modelo.e[p,d,h]) - 1  # w >= k + (1 - z) - 1


        # RESTRICCION DE HORAS CONSECUTIVAS
        with etapa_registrada("Restriccion de Continuidad de E", iteracion_actual, modelo, version=versio_modelo, registros=registros):
            @modelo.Constraint( modelo.PROFESORES, modelo.DIAS, modelo.HORAS,
                  doc="Asegura que las clases sean consecutivas en cada día" )
            def restriccion_clases_consecutivas_profesores(modelo,p,d,h):
                if h == min(modelo.HORAS):
                    # Si es la hora mínima, debe haber una clase en la siguiente hora
                    return modelo.e[p,d,h] <= modelo.e[p,d,h+1]
                elif h == max(modelo.HORAS):
                    # Si es la hora máxima, debe haber una clase en la hora anterior
                    return modelo.e[p,d,h] >= modelo.e[p,d,h-1]
                else:
                    # Para horas intermedias, debe haber clase en h-1 o h+1
                    return modelo.e[p,d,h] <= modelo.e[p,d,h-1] + modelo.e[p,d,h+1]
            if impresion:
                print("\nRestricción de clases consecutivas definida correctamente")

        # RESTRICCION DE HORAS ANTES
        with etapa_registrada("Restriccion Construccion de I", iteracion_actual, modelo, version=versio_modelo, registros=registros):
            modelo.restriccion_horas_antes_profesores = pyo.ConstraintList()
            for p in modelo.PROFESORES:
                for d in modelo.DIAS:
                    for h in modelo.HORAS:
                        if h == min(modelo.HORAS):
                            modelo.restriccion_horas_antes_profesores.add(modelo.i[p,d,h] == 0)
                        else:
                            for k in modelo.HORAS:
                                if k < h:
                                    modelo.restriccion_horas_antes_profesores.add(
                                        modelo.i[p,d,h] >= modelo.e[p,d,k]
                                    )
            if impresion:
                print("\nRestricción de horas antes definida correctamente")

        # RESTRICCION DE HORAS DESPUES
        with etapa_registrada("Restriccion Construccion de J", iteracion_actual, modelo, version=versio_modelo, registros=registros):
            modelo.restriccion_horas_despues_profesores = pyo.ConstraintList()
            for p in modelo.PROFESORES:
                for d in modelo.DIAS:
                    for h in modelo.HORAS:
                        if h == max(modelo.HORAS):
                            modelo.restriccion_horas_despues_profesores.add(modelo.j[p,d,h] == 0)
                        else:
                            for k in modelo.HORAS:
                                if k > h:
                                    modelo.restriccion_horas_despues_profesores.add(
                                        modelo.j[p,d,h] >= modelo.e[p,d,k]
                                    )
            if impresion:
                print("\nRestricción de horas despues definida correctamente")

    # RESTRICCION QUE RELACIONA X CON Y
    with etapa_registrada("Restricion X Y", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint( modelo.PROFESORES, modelo.MATERIAS, modelo.DIAS, modelo.HORAS, modelo.AULAS, modelo.GRUPOS,
              doc="Solo se pueden asignar horas a materias que el profesor tiene asignadas" )
        def restriccion_xy(modelo,p,m,d,h,a,g):
            return modelo.x[p,m,d,h,a,g] <= modelo.y[p,m]
        if impresion:
            print("\nRestricción que limita que profesor puede dar que materia")

    # RESTRICCION DE DISPONIBILIDAD DE HORARIO DEL PROFESOR
    with etapa_registrada("Restriccion Disponibilidad de Horas Profesor", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint( modelo.PROFESORES, modelo.DIAS, modelo.HORAS,
                           doc="Restricción de disponibilidad de horario del profesor" )
        def restriccion_disponibilidad(modelo,p,d,h):
            return sum(modelo.x[p,m,d,h,a,g]
                    for m in modelo.MATERIAS
                    for a in modelo.AULAS
                    for g in modelo.GRUPOS) <= modelo.dis_bin[p,d,h]
        if impresion:
            print("\nRestricción de disponibilidad del profesor definida correctamente")

    # RESTRICCIÓN DE DISPONIBILIDAD DEL AULA
    with etapa_registrada("Restriccion Disponibilidad de Aula", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint(modelo.AULAS, modelo.DIAS, modelo.HORAS,
            doc="Restricción de disponibilidad de horario del aula" )
        def restriccion_disponibilidad_aula(modelo,a,d,h):
            return sum(modelo.x[p,m,d,h,a,g]
                    for p in modelo.PROFESORES
                    for m in modelo.MATERIAS
                    for g in modelo.GRUPOS) <= modelo.dia[d,h,a]
        if impresion:
            print("\nRestricción de disponibilidad de horario del aula definida correctamente")

    # RESTRICCIÓN QUE RELACIONA X CON U
    with etapa_registrada("Restriccion Grupos Ofertados", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint(modelo.PROFESORES, modelo.MATERIAS, modelo.DIAS, modelo.HORAS, modelo.AULAS, modelo.GRUPOS,
            doc="Materias por grupo y semestres que se ofertaran" )
        def restriccion_xu(modelo,p,m,d,h,a,g):
            return modelo.x[p,m,d,h,a,g] <= modelo.u[m,g]
        if impresion:
            print("\nRestricción que relaciona x con u definida correctamente")

    # RESTRICCIÓN DE HORAS MÁXIMAS POR PROFESOR
    with etapa_registrada("Restriccion Horas Maximas Profesor", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint(modelo.PROFESORES,
                          doc="Cada profesor no debe exceder su máximo de horas de clase" )
        def restriccion_horas_maximas(modelo, p):
            return sum(modelo.x[p,m,d,h,a,g]
                    for m in modelo.MATERIAS
                    for d in modelo.DIAS
                    for h in modelo.HORAS
                    for a in modelo.AULAS
                    for g in modelo.GRUPOS) + modelo.base <= modelo.h_max[p]
        if impresion:
            print("\nRestricción de horas máximas por profesor definida correctamente")

    # RESTRICCION DE HORAS POR MATERIA
    with etapa_registrada("Restriccion de Horas por Materia", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint(modelo.MATERIAS, modelo.GRUPOS,
            doc="Cada materia debe cumplir exactamente sus horas requeridas por semana" )
        def restriccion_horas_materia(modelo,m,g):
            return sum(modelo.x[p,m,d,h,a,g]
                    for p in modelo.PROFESORES
                    for d in modelo.DIAS
                    for h in modelo.HORAS
                    for a in modelo.AULAS) + modelo.base == modelo.h_mat[m] * modelo.u[m,g]
        if impresion:
            print("\nRestricción de horas por materia definida correctamente")

    # RESTRICCION DE HORAS CONTINUAS POR DIA
    with etapa_registrada("Restriccion de Horas por Dia", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint( modelo.MATERIAS, modelo.DIAS, modelo.GRUPOS,
             doc="No se pueden asignar más horas continuas por día que las permitidas para cada materia")
        def restriccion_horas_continuas(modelo,m,d,g):
            return sum(modelo.x[p,m,d,h,a,g] for p in modelo.PROFESORES
                                            for h in modelo.HORAS
                                            for a in modelo.AULAS) + modelo.base <= modelo.h_con[m]
        if impresion:
            print("\nRestricción de horas continuas por día definida correctamente")

    # RELACION ENTRE LA VARIABLE X Y VARIABLE DE ACTIVACION V
    with etapa_registrada("Restriccion Variable Continuidad Horizontal", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint(modelo.PROFESORES, modelo.MATERIAS, modelo.DIAS, modelo.HORAS, modelo.AULAS, modelo.GRUPOS,
                            doc="Relacion entre la pyo.varible x y la varaible de activacion v" )
        def restriccion_xv(modelo,p,m,d,h,a,g):
            if (m in modelo.MATERIAS_SEM) or (m in modelo.MATERIAS_VAR): #modelo.h_con[m]==1:
                #print(f'Restrccion de FIN generadao para {m} en {d} en {h} en {a} en {g}')
                return modelo.x[p,m,d,h,a,g] <= modelo.v[p,m,h,a,g]
            return pyo.Constraint.Skip
        if impresion:
            print("\nRestricción que relaciona x con v definida correctamente")

    # RELACION ENTRE LA VARIABLE X Y VARIABLE DE ACTIVACION V
    #@modelo.Constraint( modelo.PROFESORES, modelo.MATERIAS_SEM,modelo.DIAS, modelo.HORAS, modelo.AULAS, modelo.GRUPOS,
    #                    doc="Relacion entre la pyo.varible x y la varaible de activacion v" )
    #def restriccion_xv(modelo,p,m,d,h,a,g):
    #    return modelo.x[p,m,d,h,a,g] <= modelo.v[p,m,h,a,g]
    #if impresion:
    #    print("\nRestricción que relaciona x con v definida correctamente")


    with etapa_registrada("Restriccion Continuidad Horizontal", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint( modelo.PROFESORES, modelo.MATERIAS_SEM, modelo.HORAS, modelo.AULAS, modelo.GRUPOS,
            doc="Restricción para asegurar que si u=1, las clases se programen en la misma hora en diferentes días")
        def restriccion_misma_hora(modelo,p,m,h,a,g):
        #    if (m in modelo.MATERIAS_SEM) or (m in modelo.MATERIAS_VAR): #modelo.h_con[m]==1:
            # Esto equivale a: if u[p,m] == 1, entonces sum(...) == h_mat[m] * v[p,m,h]
            return sum(modelo.x[p,m,d,h,a,g]
                            for d in modelo.DIAS) + modelo.base == modelo.h_mat[m] * modelo.v[p,m,h,a,g]# + modelo.M * (1 - modelo.u[p, m])
            #return pyo.Constraint.Skip
        if impresion:
            print("\nRestricción de misma hora definida correctamente")


    # Relacion entre la pyo.varible x y la varaible de activacion v
    with etapa_registrada("Restriccion Variable, continuidad Vertical", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint(modelo.PROFESORES, modelo.MATERIAS, modelo.DIAS, modelo.HORAS, modelo.AULAS, modelo.GRUPOS,
            doc="Relacion entre la pyo.varible x y la varaible de activacion v" )
        def restriccion_xq(modelo,p,m,d,h,a,g):
            if (m in modelo.MATERIAS_FIN) or (m in modelo.MATERIAS_VAR) or (m in modelo.MATERIAS_LAB):#modelo.mta[m] in modelo.AULAS_LAB:
                #print(f'Restrccion de FIN generadao para {m} en {d} en {h} en {a} en {g}')
                return modelo.x[p,m,d,h,a,g] <= modelo.q[p,m,d,a,g]
            return pyo.Constraint.Skip
        if impresion:
            print("\nRestricción que relaciona x con v definida correctamente")


    #Restricciones de laboratorios
    with etapa_registrada("Restriccion Continuidad Vetical", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint(modelo.PROFESORES, modelo.MATERIAS_FIN, modelo.DIAS, modelo.AULAS, modelo.GRUPOS,
             doc="Restricción para asegurar que si u=1, las clases se programen en la misma hora en diferentes días")
        def restriccion_mismo_dia(modelo,p,m,d,a,g):
            if  modelo.mta[m] in modelo.AULAS_LAB:
                aula = modelo.mta[m]
            else:
                aula = a
            #print(f'Restriccion creada para Materia {m} en el aula {aula}')
            return sum(modelo.x[p,m,d,h,aula,g]
                        for h in modelo.HORAS) == modelo.h_mat[m] * modelo.q[p,m,d,a,g]# + modelo.M * (1 - modelo.u[p, m])
            #return pyo.Constraint.Skip

    with etapa_registrada("Restriccion Aulas Laboratorios", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint(modelo.PROFESORES, modelo.MATERIAS_LAB, modelo.DIAS, modelo.AULAS_LAB, modelo.GRUPOS,
                           doc="Restriccion que define que las clases de laboratorio se programan en su aula de laboratorio correspondiente")
        def restriccion_aulas_laboratorios(modelo,p,m,d,a,g):
            return sum(modelo.x[p,m,d,h,modelo.mta[m],g] for h in modelo.HORAS) == modelo.h_mat[m] * modelo.q[p,m,d,a,g]


    if disjuntives:
        #APLICACION DE DISJUNTIVAS
        with etapa_registrada("Restricciones Disyuntivas", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                              semestre=semestre, permutacion=permutacion):
            @modelo.Disjunction(modelo.PROFESORES, modelo.MATERIAS_VAR, modelo.DIAS, modelo.HORAS, modelo.AULAS, modelo.GRUPOS, xor=True)
            def restrcciones_disjutivas(modelo,p,m,d,h,a,g):
                return [
                    [sum(modelo.x[p,m,d,h,a,g] for d in modelo.DIAS) == modelo.h_mat[m] * modelo.v[p,m,h,a,g]],
                    [sum(modelo.x[p,m,d,h,a,g] for h in modelo.HORAS) == modelo.h_mat[m] * modelo.q[p,m,d,a,g]]
                ]

    #RESTRICCION DE CLASES CONSECUTIVAS EN LABORATORIOS
    with etapa_registrada("Restricciones Horas Consecutivas", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint(modelo.PROFESORES, modelo.MATERIAS_LAB, modelo.DIAS, modelo.HORAS, modelo.AULAS_LAB, modelo.GRUPOS,
              doc="Asegura que las clases sean consecutivas en cada día" )
        def restriccion_clases_consecutivas_laboratorio(modelo,p,m,d,h,a,g):
            if h == min(modelo.HORAS):
                # Si es la hora mínima, debe haber una clase en la siguiente hora
                return modelo.x[p,m,d,h,a,g] <= modelo.x[p,m,d,h+1,a,g]
            elif h == max(modelo.HORAS):
                # Si es la hora máxima, debe haber una clase en la hora anterior
                return modelo.x[p,m,d,h,a,g] <= modelo.x[p,m,d,h-1,a,g]
            else:
                # Para horas intermedias, debe haber clase en h-1 o h+1
                return modelo.x[p,m,d,h,a,g] <= modelo.x[p,m,d,h-1,a,g] + modelo.x[p,m,d,h+1,a,g]
        if impresion:
            print("\nRestricción de clases consecutivas definida correctamente")

    #RESTRICCIONES DE UNICIDAD
    #Restriccion unicidad de profesores
    with etapa_registrada("Restriccion Unicidad Profesro", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint( modelo.PROFESORES, modelo.DIAS,modelo.HORAS,
            doc="No se puede dar mas de una materia a la vez" )
        def restriccion_unicidad_profesores(modelo,p,d,h):
            return sum(modelo.x[p,m,d,h,a,g]
                    for m in modelo.MATERIAS
                    for a in modelo.AULAS
                    for g in modelo.GRUPOS
                    ) + modelo.base <=1
        if impresion:
            print("\nRestricción de unicidad de profesores definida correctamente")

    #Restriccion unicidad de MATERIAS por GRUPO
    with etapa_registrada("Restriccion Unicidad Materias por Grupo", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint( modelo.DIAS, modelo.HORAS, modelo.GRUPOS,
              doc="Un profesor no puede dar mas de una materia a la vez" )
        def restriccion_unicidad_materias_grupo_semestres(modelo,d,h,g):
            return sum(modelo.x[p,m,d,h,a,g]
                    for p in modelo.PROFESORES
                    for m in modelo.MATERIAS
                    for a in modelo.AULAS) + modelo.base <= 1
        if impresion:
            print("\nRestricción de unicidad de materias por grupo y semestre definida correctamente")

    # Restricción unicidad de aulas
    with etapa_registrada("Restriccion Unicidad de Aulas", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        @modelo.Constraint( modelo.DIAS, modelo.HORAS, modelo.AULAS,
                            doc="No puede haber más de una materia asignada por aula, día, y hora")
        def restriccion_unicidad_aulas(modelo,d,h,a):
            return sum(modelo.x[p,m,d,h,a,g]
                    for p in modelo.PROFESORES
                    for m in modelo.MATERIAS
                    for g in modelo.GRUPOS
                    ) + modelo.base <= 1
        if impresion:
            print("\nRestricción de unicidad de aulas definida correctamente")

    # # Resolver el modelo en local
    print("\nTransformando Modelo..")

    with etapa_registrada("Transformar el Modelo", iteracion_actual, modelo, version=versio_modelo, registros=registros,
                          semestre=semestre, permutacion=permutacion):
        pyo.TransformationFactory('gdp.bigm').apply_to(modelo)

    # === Guardar o actualizar el CSV ===
    guardar_registro_csv(registros, archivo_csv)
    guardar_registro_sqlite(registros)

    return modelo