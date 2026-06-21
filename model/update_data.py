def actualizar_disponibilidades(solucion, datos):
    """
    Actualiza la disponibilidad de profesores y aulas basado en una solución de variables tipo x[...].

    Cada variable representa una asignación con el siguiente formato:
    x[PF001,IIS01,Lunes,9,A401,C]

    Parámetros:
    ----------
    solucion : dict
        Diccionario con variables como claves (e.g., 'x[PF001,IIS01,Lunes,9,A401,C]') y valores (1.0 o 0.0),
        típicamente derivado de la solución de un modelo de optimización.

    datos : dict
        Diccionario de DataFrames que contiene:
            - "df_profesores": DataFrame con profesores y horas disponibles.
            - "df_profesores_disponibles": Disponibilidad original de profesores (formato expandido).
            - "df_profesores_disp_bin": Disponibilidad binaria de profesores por día y hora.
            - "df_aulas_disponibles": Disponibilidad de aulas por día y hora.

    Retorna:
    -------
    datos : dict
        Diccionario actualizado con las nuevas disponibilidades y reducción de horas para profesores.
    """
    import pandas as pd

    imprimir = False  # Cambiar a False si no deseas imprimir cada asignación

    # Extraer los DataFrames del diccionario
    df_profesores = datos["df_profesores"]
    df_profesores_disponibles = datos["df_profesores_disponibles"]
    df_profesores_disp_bin = datos["df_profesores_disp_bin"]
    df_aulas_disponibles = datos["df_aulas_disponibles"]

    # Guardar copias para comparación posterior
    df_aulas_disponibles_original = df_aulas_disponibles.copy()
    df_profesores_disp_bin_original = df_profesores_disp_bin.copy()

    for var, val in solucion.items():
        # Solo procesar variables activas que empiecen con 'x['
        if not var.startswith("x[") or val != 1.0:
            continue
        try:
            # Extraer el contenido dentro de los corchetes
            contenido = var[2:-1]  # Remueve "x[" al inicio y "]" al final
            profe_id, grupo, dia, hora, aula, tipo = contenido.split(",")
            hora = int(hora)

            # 1. Reducir las horas máximas del profesor asignado
            idx = df_profesores[df_profesores["id"] == profe_id].index
            if not idx.empty:
                df_profesores.at[idx[0], "horas_max"] -= 1

            # 2. Eliminar esa hora de disponibilidad detallada
            df_profesores_disponibles = df_profesores_disponibles[
                ~((df_profesores_disponibles["ID_PROFESOR"] == profe_id) &
                  (df_profesores_disponibles["HORA"] == hora))
            ]

            # 3. Marcar como NO disponible en disponibilidad binaria
            bin_mask = (
                    (df_profesores_disp_bin["ID_PROFESOR"] == profe_id) &
                    (df_profesores_disp_bin["DIA"] == dia) &
                    (df_profesores_disp_bin["HORA"] == hora)
            )
            df_profesores_disp_bin.loc[bin_mask, "DISPONIBLE"] = 0

            # 4. Marcar como NO disponible el aula en ese horario
            aula_mask = (
                    (df_aulas_disponibles["ID_AULA"] == aula) &
                    (df_aulas_disponibles["DIA"] == dia) &
                    (df_aulas_disponibles["HORA"] == hora)
            )
            df_aulas_disponibles.loc[aula_mask, "DISPONIBLE"] = 0

            # Imprimir asignación
            if imprimir:
                print(f"✔️ {profe_id} asignado el {dia} a las {hora}h en aula {aula}.")

        except Exception as e:
            print(f"⚠️ Error procesando variable {var}: {e}")

    # Comparar con los datos originales para detectar cambios
    if not df_aulas_disponibles.equals(df_aulas_disponibles_original):
        print("✅ Se modificó la disponibilidad de aulas.")
    else:
        print("❌ No hubo cambios en la disponibilidad de aulas.")

    if not df_profesores_disp_bin.equals(df_profesores_disp_bin_original):
        print("✅ Se modificó la disponibilidad de profesor.")
    else:
        print("❌ No hubo cambios en la disponibilidad de profesor.")

    # Actualizar el diccionario de datos con los nuevos DataFrames
    datos["df_profesores"] = df_profesores
    datos["df_profesores_disponibles"] = df_profesores_disponibles
    datos["df_aulas_disponibles"] = df_aulas_disponibles
    datos["df_profesores_disp_bin"] = df_profesores_disp_bin

    return datos