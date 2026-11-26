"""Exporta los gráficos principales del EDA a la carpeta img/ para usarlos en el README.

Reproduce los gráficos del notebook 01_exploracion.ipynb (sin modificarlo) y suma
los de cobertura y reinternaciones, con el mismo estilo. Usa las tablas limpias de
data/staging.

Uso (desde la raíz del proyecto):
    python scripts/exportar_graficos.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
STAGING = RAIZ / "data" / "staging"
IMG = RAIZ / "img"
IMG.mkdir(exist_ok=True)

TIPOS = {
    "ambulatory": "Ambulatoria",
    "outpatient": "Externa",
    "urgentcare": "Urgencia leve",
    "emergency": "Emergencia",
    "wellness": "Control de rutina",
    "inpatient": "Internación",
}

pacientes = pd.read_csv(STAGING / "pacientes_limpio.csv", dtype={"ZIP": str})
consultas = pd.read_csv(STAGING / "consultas_limpio.csv", parse_dates=["START", "STOP"])
aseguradoras = pd.read_csv(STAGING / "aseguradoras_limpio.csv", dtype={"ZIP": str})
consultas["TIPO"] = consultas["ENCOUNTERCLASS"].map(TIPOS)


def guardar(nombre):
    plt.savefig(IMG / nombre, dpi=150, bbox_inches="tight")
    plt.close()
    print("Guardado:", IMG / nombre)


# 1. Distribución de edad (igual al notebook)
plt.figure(figsize=(10, 5))
plt.hist(pacientes["EDAD"], bins=14, edgecolor="black", color="teal")
plt.title("Distribución de edad de los pacientes")
plt.xlabel("Edad")
plt.ylabel("Cantidad de pacientes")
guardar("eda_pacientes_edad.png")

# 2. Consultas por año y por tipo (2011-2021, 2022 está incompleto)
por_anio_tipo = (
    consultas[consultas["AÑO"] < 2022]
    .groupby(["AÑO", "TIPO"]).size().unstack(fill_value=0)
)
orden = por_anio_tipo.sum().sort_values(ascending=False).index
por_anio_tipo[orden].plot(
    kind="bar", stacked=True, figsize=(10, 5), edgecolor="black",
    color=plt.cm.GnBu_r([i / len(orden) for i in range(len(orden))]),
)
plt.title("Cantidad de consultas por año y por tipo (2011-2021)")
plt.xlabel("Año")
plt.ylabel("Cantidad de consultas")
plt.xticks(rotation=0)
plt.legend(title="Tipo de consulta", bbox_to_anchor=(1.01, 1), loc="upper left")
guardar("eda_evolucion_anual.png")

# 3. % de consultas y % del costo por tipo (igual al notebook)
costos_por_tipo = consultas.groupby("TIPO").agg(
    consultas=("Id", "count"), costo_total=("TOTAL_CLAIM_COST", "sum")
)
costos_por_tipo["%_consultas"] = costos_por_tipo["consultas"] / costos_por_tipo["consultas"].sum() * 100
costos_por_tipo["%_costo"] = costos_por_tipo["costo_total"] / costos_por_tipo["costo_total"].sum() * 100
comparacion = costos_por_tipo.sort_values("%_costo", ascending=False)[["%_consultas", "%_costo"]]
comparacion.plot(kind="bar", figsize=(10, 5), color=["lightgray", "teal"], edgecolor="black")
plt.title("Porcentaje de consultas y porcentaje del costo, por tipo de consulta")
plt.xlabel("Tipo de consulta")
plt.ylabel("Porcentaje (%)")
plt.xticks(rotation=0)
plt.legend(["% de las consultas", "% del costo"])
guardar("eda_costos_por_tipo.png")

# 4. Cobertura: % del costo cubierto por aseguradora y por año
con_seguro = consultas.merge(
    aseguradoras[["Id", "NAME"]], left_on="PAYER", right_on="Id",
    how="left", suffixes=("", "_payer"),
)
por_aseguradora = con_seguro.groupby("NAME")[["TOTAL_CLAIM_COST", "PAYER_COVERAGE"]].sum()
por_aseguradora = (por_aseguradora["PAYER_COVERAGE"] / por_aseguradora["TOTAL_CLAIM_COST"] * 100).sort_values()
por_anio = consultas[consultas["AÑO"] < 2022].groupby("AÑO")[["TOTAL_CLAIM_COST", "PAYER_COVERAGE"]].sum()
por_anio = por_anio["PAYER_COVERAGE"] / por_anio["TOTAL_CLAIM_COST"] * 100

fig, (izq, der) = plt.subplots(1, 2, figsize=(14, 5))
izq.barh(por_aseguradora.index, por_aseguradora.values, color="teal", edgecolor="black")
izq.set_title("% del costo que cubre cada aseguradora")
izq.set_xlabel("Porcentaje cubierto (%)")
der.bar(por_anio.index, por_anio.values, color="teal", edgecolor="black")
der.set_title("% del costo cubierto por los seguros, por año (2011-2021)")
der.set_xlabel("Año")
der.set_ylabel("Porcentaje cubierto (%)")
der.set_xticks(por_anio.index)
der.tick_params(axis="x", rotation=45)
plt.tight_layout()
guardar("eda_cobertura.png")

# 5. Reinternaciones: top 10 pacientes (misma lógica del notebook)
internaciones = consultas[consultas["ENCOUNTERCLASS"] == "inpatient"].sort_values(["PATIENT", "START"]).copy()
internaciones["ALTA_ANTERIOR"] = internaciones.groupby("PATIENT")["STOP"].shift(1)
internaciones["DIAS_DESDE_ALTA"] = (internaciones["START"] - internaciones["ALTA_ANTERIOR"]).dt.days
internaciones["REINTERNACION"] = internaciones["DIAS_DESDE_ALTA"].between(0, 30)
por_paciente = (
    internaciones[internaciones["REINTERNACION"]].groupby("PATIENT").size().sort_values(ascending=False)
)
top_10 = por_paciente.head(10)
porcentaje = top_10.sum() / por_paciente.sum() * 100

plt.figure(figsize=(10, 5))
etiquetas = [f"Paciente {i}" for i in range(1, 11)]
plt.barh(etiquetas[::-1], top_10.values[::-1], color="teal", edgecolor="black")
plt.title(f"Los 10 pacientes con más reinternaciones ({porcentaje:.1f}% del total)")
plt.xlabel("Cantidad de reinternaciones")
guardar("eda_reinternaciones.png")
