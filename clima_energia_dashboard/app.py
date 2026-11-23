# -*- coding: utf-8 -*-
"""
CLIMA & ENERGIA
Dashboard interativo: temperatura na Asa Sul x consumo elétrico no DF.
Desenvolvido com Streamlit, Pandas e Plotly.
"""

from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import pearsonr, spearmanr

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Clima & Energia | Brasília",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "dados_originais"
DEFAULT_CONSUMO = DATA_DIR / "Dados_abertos_Consumo_Mensal.xlsx"
DEFAULT_CLIMA = DATA_DIR / "serie_diaria_asa_sul_1976_2026.csv"

MESES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}
MESES_LONGOS = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}
CORES = {
    "azul": "#39A9DB",
    "azul_escuro": "#153B5B",
    "laranja": "#FF9F43",
    "verde": "#2ECC9A",
    "roxo": "#9B8AFB",
    "vermelho": "#FF6B6B",
    "cinza": "#9AA9B8",
}

# ---------------------------------------------------------------------
# ESTILO VISUAL
# ---------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp {
  background:
    radial-gradient(circle at 85% 0%, rgba(57,169,219,.12), transparent 28%),
    linear-gradient(180deg, #081522 0%, #0B1D2D 100%);
  color: #EDF5FA;
}
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1500px; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; color: #F4FAFF; }
[data-testid="stSidebar"] { background: #0C2031; border-right: 1px solid rgba(255,255,255,.08); }
[data-testid="stMetric"] {
  background: linear-gradient(145deg, rgba(24,54,78,.96), rgba(14,37,57,.96));
  border: 1px solid rgba(100,190,230,.20);
  border-radius: 16px; padding: 16px 18px;
}
[data-testid="stMetricLabel"] { color: #AFC5D5 !important; }
[data-testid="stMetricValue"] { color: #F5FBFF !important; font-family: 'Space Grotesk', sans-serif; }
div[data-testid="stTabs"] button { color: #C8DCE9; }
div[data-testid="stTabs"] button[aria-selected="true"] { color: #57C7F2; }
.stButton button, .stDownloadButton button {
  border-radius: 12px; border: 1px solid rgba(57,169,219,.45);
  background: linear-gradient(90deg,#1677A8,#245B91); color: white; font-weight: 700;
}
div[data-testid="stAlert"] { border-radius: 12px; }
.hero {
  padding: 25px 28px; border-radius: 22px; margin-bottom: 18px;
  background: linear-gradient(115deg, rgba(20,75,110,.95), rgba(20,45,72,.92) 58%, rgba(80,75,140,.75));
  border: 1px solid rgba(117,204,241,.25);
  box-shadow: 0 14px 45px rgba(0,0,0,.18);
}
.hero-kicker { color:#8EDBFF; font-size: .78rem; letter-spacing: .16em; font-weight:800; }
.hero-title { font-family:'Space Grotesk',sans-serif; font-size:2.25rem; font-weight:700; line-height:1.1; margin:.35rem 0; color:#fff; }
.hero-sub { color:#D2E5F1; font-size:1rem; }
.section-note { color:#A9C0D0; font-size:.88rem; }
.small-pill {
 display:inline-block; padding:5px 10px; border-radius:20px; margin:3px 4px 3px 0;
 background:rgba(57,169,219,.14); border:1px solid rgba(57,169,219,.28); color:#A8E5FF; font-size:.78rem;
}
div[data-testid="stDataFrame"] { border:1px solid rgba(130,180,210,.18); border-radius:12px; overflow:hidden; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# LEITURA E PREPARAÇÃO DOS DADOS
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def carregar_clima(arquivo_bytes=None, caminho=None):
    if arquivo_bytes is not None:
        from io import BytesIO
        clima = pd.read_csv(BytesIO(arquivo_bytes))
    elif caminho and Path(caminho).exists():
        clima = pd.read_csv(caminho)
    else:
        raise FileNotFoundError("Arquivo de temperatura não encontrado.")
    obrigatorias = {"date", "tmax_c", "tmin_c", "tmed_c"}
    faltantes = obrigatorias - set(clima.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes no CSV climático: {', '.join(sorted(faltantes))}")
    clima["date"] = pd.to_datetime(clima["date"], errors="coerce")
    for col in ["tmax_c", "tmin_c", "tmed_c"]:
        clima[col] = pd.to_numeric(clima[col], errors="coerce")
    clima = clima.dropna(subset=["date"]).copy()
    clima["mes_ref"] = clima["date"].dt.to_period("M").dt.to_timestamp()
    return clima.sort_values("date")

@st.cache_data(show_spinner=False)
def carregar_consumo(arquivo_bytes=None, caminho=None):
    if arquivo_bytes is not None:
        from io import BytesIO
        consumo = pd.read_excel(BytesIO(arquivo_bytes), sheet_name="CONSUMO E NUMCONS SAM UF")
    elif caminho and Path(caminho).exists():
        consumo = pd.read_excel(caminho, sheet_name="CONSUMO E NUMCONS SAM UF")
    else:
        raise FileNotFoundError("Arquivo Excel de consumo não encontrado.")

    obrigatorias = {"DataExcel", "UF", "Classe", "TipoConsumidor", "Consumo", "Consumidores"}
    faltantes = obrigatorias - set(consumo.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes na aba de consumo: {', '.join(sorted(faltantes))}")

    consumo["DataExcel"] = pd.to_datetime(consumo["DataExcel"], errors="coerce")
    consumo["Consumo"] = pd.to_numeric(consumo["Consumo"], errors="coerce")
    consumo["Consumidores"] = pd.to_numeric(consumo["Consumidores"], errors="coerce")
    consumo = consumo.dropna(subset=["DataExcel"]).copy()
    consumo = consumo[
        (consumo["UF"].astype(str).str.upper().str.strip() == "DF")
        & (consumo["Classe"].astype(str).str.strip().isin(["Residencial", "Comercial"]))
    ].copy()
    consumo["mes_ref"] = consumo["DataExcel"].dt.to_period("M").dt.to_timestamp()

    # Soma cativo + livre, quando ambas as categorias existem.
    # Em alguns meses/anos, a EPE não apresenta linha de mercado livre para a classe.
    mensal = (
        consumo.groupby(["mes_ref", "Classe"], as_index=False)
        .agg(
            consumo_mwh=("Consumo", "sum"),
            consumidores=("Consumidores", "sum"),
            linhas_origem=("TipoConsumidor", "size"),
        )
    )
    mensal["consumo_kwh"] = mensal["consumo_mwh"] * 1000
    mensal["kwh_por_consumidor"] = np.where(
        mensal["consumidores"] > 0,
        mensal["consumo_kwh"] / mensal["consumidores"],
        np.nan
    )
    return mensal

def montar_base(clima_diario, consumo_mensal, inicio, fim, p_quente):
    clima = clima_diario[
        (clima_diario["date"] >= pd.Timestamp(inicio))
        & (clima_diario["date"] <= pd.Timestamp(fim))
    ].copy()

    # Limiar fixo para comparabilidade: percentil calculado sempre na referência
    # 2005-2025, independentemente do intervalo visualizado no filtro.
    referencia = clima_diario[
        (clima_diario["date"] >= pd.Timestamp("2005-01-01"))
        & (clima_diario["date"] <= pd.Timestamp("2025-12-31"))
    ]["tmax_c"].dropna()
    limiar = referencia.quantile(p_quente / 100) if not referencia.empty else np.nan

    clima_m = (
        clima.groupby("mes_ref", as_index=False)
        .agg(
            temperatura_media=("tmed_c", "mean"),
            temperatura_maxima_media=("tmax_c", "mean"),
            temperatura_minima_media=("tmin_c", "mean"),
            amplitude_media=("tmax_c", lambda s: np.nan),
            dias_com_dado=("tmed_c", "count"),
            dias_calendario=("date", "nunique"),
        )
    )
    # Amplitude calculada como média das amplitudes diárias, quando disponível.
    if "amplitude_c" in clima.columns:
        amp = clima.groupby("mes_ref")["amplitude_c"].mean()
        clima_m["amplitude_media"] = clima_m["mes_ref"].map(amp)
    else:
        clima_m["amplitude_media"] = clima_m["temperatura_maxima_media"] - clima_m["temperatura_minima_media"]

    clima["dia_muito_quente"] = clima["tmax_c"] > limiar
    quentes = clima.groupby("mes_ref")["dia_muito_quente"].sum()
    clima_m["dias_muito_quentes"] = clima_m["mes_ref"].map(quentes).fillna(0).astype(int)
    clima_m["limiar_dia_quente_c"] = limiar

    cons = consumo_mensal[
        (consumo_mensal["mes_ref"] >= pd.Timestamp(inicio).to_period("M").to_timestamp())
        & (consumo_mensal["mes_ref"] <= pd.Timestamp(fim).to_period("M").to_timestamp())
    ].copy()

    largo = cons.pivot(index="mes_ref", columns="Classe",
                       values=["consumo_mwh", "consumo_kwh", "consumidores", "kwh_por_consumidor"])
    largo.columns = [f"{metrica}_{classe.lower()}" for metrica, classe in largo.columns]
    largo = largo.reset_index()

    base = clima_m.merge(largo, on="mes_ref", how="inner")
    base = base.sort_values("mes_ref").reset_index(drop=True)
    base["ano"] = base["mes_ref"].dt.year
    base["numero_mes"] = base["mes_ref"].dt.month
    base["mes"] = base["numero_mes"].map(MESES_LONGOS)
    base["mes_abrev"] = base["numero_mes"].map(MESES)
    base["consumo_total_mwh"] = base.get("consumo_mwh_residencial", 0).fillna(0) + base.get("consumo_mwh_comercial", 0).fillna(0)
    base["consumo_total_kwh"] = base["consumo_total_mwh"] * 1000
    base["consumo_por_consumidor_total"] = (
        base["consumo_total_kwh"] /
        (base.get("consumidores_residencial", 0).fillna(0) + base.get("consumidores_comercial", 0).fillna(0)).replace(0, np.nan)
    )
    base["variacao_residencial_a/a_%"] = base["consumo_mwh_residencial"].pct_change(12) * 100
    base["variacao_comercial_a/a_%"] = base["consumo_mwh_comercial"].pct_change(12) * 100
    return base, limiar

def fmt_num(valor, casas=1):
    if pd.isna(valor):
        return "—"
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def correlacao_segura(x, y, metodo="pearson"):
    pares = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(pares) < 3 or pares["x"].nunique() < 2 or pares["y"].nunique() < 2:
        return np.nan, np.nan, len(pares)
    try:
        if metodo == "pearson":
            r, p = pearsonr(pares["x"], pares["y"])
        else:
            r, p = spearmanr(pares["x"], pares["y"])
        return float(r), float(p), len(pares)
    except Exception:
        return np.nan, np.nan, len(pares)

# ---------------------------------------------------------------------
# CABEÇALHO E CARREGAMENTO
# ---------------------------------------------------------------------
st.markdown("""
<div class="hero">
  <div class="hero-kicker">PAINEL DE INTELIGÊNCIA CLIMÁTICA E ENERGÉTICA</div>
  <div class="hero-title">⚡ CLIMA & ENERGIA</div>
  <div class="hero-sub">A relação entre temperatura na Asa Sul e consumo elétrico no Distrito Federal</div>
  <div style="margin-top:12px">
    <span class="small-pill">🌡️ Série climática diária</span>
    <span class="small-pill">⚡ Consumo mensal EPE</span>
    <span class="small-pill">📊 Análise estatística</span>
    <span class="small-pill">📍 Brasília — DF</span>
  </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🎛️ Central de filtros")
    st.caption("Os arquivos originais podem ser carregados aqui. Se estiverem na pasta dados_originais, o app os encontra automaticamente.")
    clima_up = st.file_uploader("Arquivo de temperatura (CSV)", type=["csv"])
    consumo_up = st.file_uploader("Arquivo de consumo (Excel)", type=["xlsx", "xls"])
    st.divider()

try:
    clima_diario = carregar_clima(
        clima_up.getvalue() if clima_up else None,
        str(DEFAULT_CLIMA) if DEFAULT_CLIMA.exists() else None
    )
    consumo_mensal = carregar_consumo(
        consumo_up.getvalue() if consumo_up else None,
        str(DEFAULT_CONSUMO) if DEFAULT_CONSUMO.exists() else None
    )
except Exception as exc:
    st.error(f"Não foi possível carregar os dados: {exc}")
    st.info("Coloque os dois arquivos originais na pasta 'dados_originais' ou envie-os pelos campos de upload na barra lateral.")
    st.stop()

# Interseção temporal real: meses que existem nas duas fontes.
clima_meses = set(clima_diario["mes_ref"].dropna().unique())
cons_meses = set(consumo_mensal["mes_ref"].dropna().unique())
meses_comuns = sorted(clima_meses.intersection(cons_meses))
if not meses_comuns:
    st.error("Não há meses em comum entre as duas fontes.")
    st.stop()

min_comum = pd.Timestamp(meses_comuns[0])
max_comum = pd.Timestamp(meses_comuns[-1])
min_data = min_comum.date()
max_data = (max_comum + pd.offsets.MonthEnd(0)).date()

with st.sidebar:
    st.markdown("### 📅 Período comparável")
    st.caption(f"Interseção encontrada: {min_comum:%m/%Y} até {max_comum:%m/%Y}")
    # Abre por padrão no recorte principal do projeto (2005-2025),
    # mas deixa o usuário explorar toda a interseção disponível.
    inicio_padrao = max(min_data, pd.Timestamp("2005-01-01").date())
    fim_padrao = min(max_data, pd.Timestamp("2025-12-31").date())
    periodo = st.date_input(
        "Selecione o intervalo",
        value=(inicio_padrao, fim_padrao),
        min_value=min_data,
        max_value=max_data,
        format="DD/MM/YYYY"
    )
    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio, fim = periodo
    else:
        inicio, fim = min_data, max_data
    if inicio > fim:
        inicio, fim = fim, inicio

    st.markdown("### 🌡️ Definição de dia muito quente")
    p_quente = st.slider(
        "Percentil da temperatura máxima diária",
        min_value=80, max_value=99, value=90, step=1,
        help="O limiar em °C é calculado uma única vez usando as máximas diárias de 2005-2025. Assim, a definição permanece estável quando você muda o período visualizado."
    )

    st.markdown("### 🌦️ Períodos climáticos")
    meses_chuvosos = st.multiselect(
        "Meses classificados como período chuvoso",
        options=list(range(1, 13)),
        default=[10, 11, 12, 1, 2, 3, 4],
        format_func=lambda x: MESES_LONGOS[x]
    )
    st.caption("Os meses restantes serão classificados como estiagem. Essa é uma classificação sazonal simplificada, não uma medição mensal de chuva.")

    st.markdown("### ⚡ Classe de consumo")
    classe_visao = st.radio("Exibir nos gráficos", ["Residencial", "Comercial", "Comparar as duas"], index=2)

base, limiar_quente = montar_base(clima_diario, consumo_mensal, inicio, fim, p_quente)
if base.empty:
    st.warning("Não há meses completos em comum no intervalo selecionado. Ajuste o período.")
    st.stop()

base["periodo_climatico"] = np.where(base["numero_mes"].isin(meses_chuvosos), "Chuvas", "Estiagem")
base["data_label"] = base["mes_abrev"] + "/" + base["ano"].astype(str)

# Seletor de variável de consumo usado em algumas visualizações
if classe_visao == "Residencial":
    col_consumo = "consumo_mwh_residencial"
    col_kwh = "kwh_por_consumidor_residencial"
    label_consumo = "Residencial"
elif classe_visao == "Comercial":
    col_consumo = "consumo_mwh_comercial"
    col_kwh = "kwh_por_consumidor_comercial"
    label_consumo = "Comercial"
else:
    col_consumo = "consumo_total_mwh"
    col_kwh = "consumo_por_consumidor_total"
    label_consumo = "Residencial + Comercial"

# ---------------------------------------------------------------------
# NAVEGAÇÃO
# ---------------------------------------------------------------------
paginas = st.tabs([
    "✨ Visão geral",
    "🌡️ Temperatura × consumo",
    "🌧️ Sazonalidade",
    "🧠 Correlações & insights",
    "🗂️ Dados & metodologia"
])

# ---------------------------------------------------------------------
# PÁGINA 1 - VISÃO GERAL
# ---------------------------------------------------------------------
with paginas[0]:
    st.subheader("Resumo executivo")
    st.markdown('<div class="section-note">Indicadores calculados a partir dos meses disponíveis simultaneamente nas duas bases.</div>', unsafe_allow_html=True)
    total_meses = len(base)
    consumo_medio = base[col_consumo].mean()
    temp_media = base["temperatura_media"].mean()
    dias_quentes = int(base["dias_muito_quentes"].sum())
    r_geral, p_geral, n_geral = correlacao_segura(base["temperatura_media"], base[col_consumo], "pearson")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Meses comparados", f"{total_meses}")
    k2.metric("Temperatura média", f"{fmt_num(temp_media)} °C")
    k3.metric(f"Consumo médio ({label_consumo})", f"{fmt_num(consumo_medio)} MWh")
    k4.metric("Dias muito quentes", f"{dias_quentes:,}".replace(",", "."))
    k5.metric("Correlação de Pearson", "—" if pd.isna(r_geral) else f"{r_geral:.2f}")

    st.markdown("#### 📈 Evolução ao longo do período")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=base["mes_ref"], y=base["temperatura_media"], name="Temperatura média (°C)",
        mode="lines", line=dict(color=CORES["azul"], width=2.5), yaxis="y"
    ))
    fig.add_trace(go.Scatter(
        x=base["mes_ref"], y=base[col_consumo], name=f"Consumo {label_consumo} (MWh)",
        mode="lines", line=dict(color=CORES["laranja"], width=2.5), yaxis="y2"
    ))
    fig.update_layout(
        template="plotly_dark", height=420, hovermode="x unified",
        margin=dict(l=15,r=15,t=25,b=15),
        yaxis=dict(title="Temperatura (°C)", gridcolor="rgba(255,255,255,.08)"),
        yaxis2=dict(title="Consumo (MWh)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.12), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)

    a, b = st.columns(2)
    with a:
        st.markdown("#### 🏆 Maiores meses de consumo")
        top = base.nlargest(10, col_consumo)[["data_label", col_consumo, "temperatura_media"]].copy()
        top = top.sort_values(col_consumo)
        fig_top = px.bar(top, x=col_consumo, y="data_label", orientation="h",
                         color=col_consumo, color_continuous_scale=["#24658C", "#42C5E8"],
                         labels={col_consumo:"Consumo (MWh)", "data_label":"Mês"})
        fig_top.update_layout(template="plotly_dark", height=390, coloraxis_showscale=False,
                              margin=dict(l=10,r=10,t=15,b=10), paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_top, use_container_width=True)
    with b:
        st.markdown("#### 🌡️ Temperatura e dias muito quentes")
        fig_hot = px.bar(base, x="mes_ref", y="dias_muito_quentes",
                         color="dias_muito_quentes", color_continuous_scale=["#1D5B7A", "#FF9F43"],
                         labels={"mes_ref":"Mês", "dias_muito_quentes":"Dias muito quentes"})
        fig_hot.update_layout(template="plotly_dark", height=390, coloraxis_showscale=False,
                              margin=dict(l=10,r=10,t=15,b=10), paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_hot, use_container_width=True)

    st.info(
        f"**Leitura rápida:** foram encontrados {total_meses} meses comparáveis no intervalo selecionado. "
        f"O limiar de dia muito quente é {fmt_num(limiar_quente, 2)} °C (percentil {p_quente} da referência fixa 2005–2025). "
        "Correlação indica associação estatística, não prova que a temperatura causou a mudança no consumo."
    )

# ---------------------------------------------------------------------
# PÁGINA 2 - TEMPERATURA X CONSUMO
# ---------------------------------------------------------------------
with paginas[1]:
    st.subheader("🌡️ A temperatura acompanha o consumo?")
    st.markdown('<div class="section-note">Explore a evolução temporal e a relação entre variáveis. Use a seleção de classe na barra lateral.</div>', unsafe_allow_html=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=base["mes_ref"], y=base["temperatura_media"], name="Temperatura média",
                              line=dict(color=CORES["azul"], width=2.7)))
    fig2.add_trace(go.Scatter(x=base["mes_ref"], y=base[col_consumo], name=f"Consumo {label_consumo}",
                              yaxis="y2", line=dict(color=CORES["laranja"], width=2.7)))
    fig2.update_layout(
        template="plotly_dark", height=440, hovermode="x unified",
        yaxis=dict(title="Temperatura média (°C)"),
        yaxis2=dict(title="Consumo (MWh)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.12), margin=dict(l=10,r=10,t=30,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig2, use_container_width=True)

    c1, c2 = st.columns([1.15, .85])
    with c1:
        st.markdown("#### 🔎 Dispersão: cada ponto representa um mês")
        dispersao = base.dropna(subset=["temperatura_media", col_consumo]).copy()
        fig_sc = px.scatter(
            dispersao, x="temperatura_media", y=col_consumo,
            color="periodo_climatico", size="dias_muito_quentes",
            hover_data={"data_label":True, "ano":True, "mes":True, "dias_muito_quentes":True},
            color_discrete_map={"Chuvas":CORES["azul"], "Estiagem":CORES["laranja"]},
            labels={"temperatura_media":"Temperatura média (°C)", col_consumo:"Consumo (MWh)",
                    "periodo_climatico":"Período"}
        )
        fig_sc.update_layout(template="plotly_dark", height=430, paper_bgcolor="rgba(0,0,0,0)",
                             plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig_sc, use_container_width=True)
    with c2:
        st.markdown("#### 📌 Indicadores de correlação")
        rp, pp, nn = correlacao_segura(base["temperatura_media"], base[col_consumo], "pearson")
        rs, ps, _ = correlacao_segura(base["temperatura_media"], base[col_consumo], "spearman")
        st.metric("Pearson (linear)", "—" if pd.isna(rp) else f"{rp:.3f}")
        st.metric("Spearman (monotônica)", "—" if pd.isna(rs) else f"{rs:.3f}")
        st.caption(f"Observações válidas: {nn}. p-valor de Pearson: {'—' if pd.isna(pp) else f'{pp:.4g}'}.")
        if not pd.isna(rp):
            intensidade = "fraca" if abs(rp)<.3 else "moderada" if abs(rp)<.7 else "forte"
            sentido = "positiva" if rp>0 else "negativa" if rp<0 else "nula"
            st.write(f"Associação linear **{sentido} e {intensidade}** no intervalo selecionado.")
        st.warning("A correlação bruta pode refletir sazonalidade e tendência temporal. Compare também meses equivalentes e variações ano contra ano antes de interpretar causalidade.")

    st.markdown("#### 🔁 Comparação com o mesmo mês do ano anterior")
    var_col = "variacao_residencial_a/a_%" if classe_visao == "Residencial" else "variacao_comercial_a/a_%"
    if classe_visao == "Comparar as duas":
        var_df = base[["mes_ref","variacao_residencial_a/a_%","variacao_comercial_a/a_%"]].melt(
            id_vars="mes_ref", var_name="Classe", value_name="Variação (%)")
        var_df["Classe"] = var_df["Classe"].str.replace("variacao_", "", regex=False).str.replace("_a/a_%", "", regex=False).str.title()
        fig_var = px.line(var_df, x="mes_ref", y="Variação (%)", color="Classe",
                          color_discrete_sequence=[CORES["azul"], CORES["laranja"]])
    else:
        fig_var = px.line(base, x="mes_ref", y=var_col, labels={var_col:"Variação anual (%)", "mes_ref":"Mês"})
    fig_var.add_hline(y=0, line_dash="dot", line_color="#AAB8C2")
    fig_var.update_layout(template="plotly_dark", height=340, paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=10,t=15,b=10))
    st.plotly_chart(fig_var, use_container_width=True)

# ---------------------------------------------------------------------
# PÁGINA 3 - SAZONALIDADE
# ---------------------------------------------------------------------
with paginas[2]:
    st.subheader("🌧️ Estiagem, chuvas e sazonalidade")
    st.markdown('<div class="section-note">A classificação sazonal é configurável. Por padrão: chuvas = outubro a abril; estiagem = maio a setembro.</div>', unsafe_allow_html=True)

    saz = base.groupby("periodo_climatico", as_index=False).agg(
        consumo_medio=(col_consumo, "mean"),
        consumo_por_consumidor=(col_kwh, "mean"),
        temperatura_media=("temperatura_media", "mean"),
        dias_quentes_medio=("dias_muito_quentes", "mean"),
        meses=("mes_ref", "count")
    )
    s1, s2 = st.columns(2)
    with s1:
        fig_saz = px.bar(saz, x="periodo_climatico", y="consumo_medio", color="periodo_climatico",
                         color_discrete_map={"Chuvas":CORES["azul"],"Estiagem":CORES["laranja"]},
                         labels={"periodo_climatico":"Período","consumo_medio":"Consumo médio (MWh)"})
        fig_saz.update_layout(template="plotly_dark", height=370, showlegend=False,
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_saz, use_container_width=True)
    with s2:
        fig_saz2 = px.bar(saz, x="periodo_climatico", y="temperatura_media", color="periodo_climatico",
                          color_discrete_map={"Chuvas":CORES["azul"],"Estiagem":CORES["laranja"]},
                          labels={"periodo_climatico":"Período","temperatura_media":"Temperatura média (°C)"})
        fig_saz2.update_layout(template="plotly_dark", height=370, showlegend=False,
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_saz2, use_container_width=True)

    st.markdown("#### 📆 Perfil médio de cada mês do ano")
    perfil = base.groupby("numero_mes", as_index=False).agg(
        consumo_medio=(col_consumo, "mean"),
        temperatura_media=("temperatura_media", "mean"),
        consumo_pc=(col_kwh, "mean")
    )
    perfil["Mês"] = perfil["numero_mes"].map(MESES_LONGOS)
    fig_perfil = go.Figure()
    fig_perfil.add_trace(go.Bar(x=perfil["Mês"], y=perfil["consumo_medio"], name="Consumo médio (MWh)",
                                marker_color=CORES["laranja"]))
    fig_perfil.add_trace(go.Scatter(x=perfil["Mês"], y=perfil["temperatura_media"], name="Temperatura média (°C)",
                                    yaxis="y2", mode="lines+markers",
                                    line=dict(color=CORES["azul"], width=3)))
    fig_perfil.update_layout(template="plotly_dark", height=420, yaxis=dict(title="Consumo médio (MWh)"),
                             yaxis2=dict(title="Temperatura (°C)", overlaying="y", side="right", showgrid=False),
                             legend=dict(orientation="h", y=1.12), paper_bgcolor="rgba(0,0,0,0)",
                             plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_perfil, use_container_width=True)

    st.markdown("#### 🏅 Ranking dos meses com maior consumo")
    ranking = base.groupby("mes", as_index=False).agg(
        consumo_medio=(col_consumo, "mean"),
        consumo_maximo=(col_consumo, "max"),
        temperatura_media=("temperatura_media", "mean"),
        dias_quentes=("dias_muito_quentes", "mean")
    ).sort_values("consumo_medio", ascending=False)
    ranking.insert(0, "Posição", range(1, len(ranking)+1))
    st.dataframe(
        ranking.rename(columns={"mes":"Mês","consumo_medio":"Consumo médio (MWh)",
                                "consumo_maximo":"Maior consumo mensal (MWh)",
                                "temperatura_media":"Temperatura média (°C)",
                                "dias_quentes":"Média de dias muito quentes"}),
        use_container_width=True, hide_index=True,
        column_config={
            "Consumo médio (MWh)": st.column_config.NumberColumn(format="%.1f"),
            "Maior consumo mensal (MWh)": st.column_config.NumberColumn(format="%.1f"),
            "Temperatura média (°C)": st.column_config.NumberColumn(format="%.2f"),
            "Média de dias muito quentes": st.column_config.NumberColumn(format="%.1f"),
        }
    )

    st.markdown("#### 📊 Consumo por consumidor")
    pc_cols = ["kwh_por_consumidor_residencial", "kwh_por_consumidor_comercial"]
    pc_labels = ["Residencial", "Comercial"]
    pc_df = base[["mes_ref"] + pc_cols].melt(id_vars="mes_ref", var_name="Classe", value_name="kWh por consumidor")
    pc_df["Classe"] = pc_df["Classe"].map({pc_cols[0]:"Residencial", pc_cols[1]:"Comercial"})
    fig_pc = px.line(pc_df, x="mes_ref", y="kWh por consumidor", color="Classe",
                     color_discrete_map={"Residencial":CORES["azul"],"Comercial":CORES["laranja"]})
    fig_pc.update_layout(template="plotly_dark", height=360, paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_pc, use_container_width=True)

# ---------------------------------------------------------------------
# PÁGINA 4 - CORRELAÇÕES E INSIGHTS
# ---------------------------------------------------------------------
with paginas[3]:
    st.subheader("🧠 Correlações e descobertas")
    variaveis = {
        "Temperatura média (°C)": "temperatura_media",
        "Temperatura máxima média (°C)": "temperatura_maxima_media",
        "Temperatura mínima média (°C)": "temperatura_minima_media",
        "Dias muito quentes": "dias_muito_quentes",
        "Consumo residencial (MWh)": "consumo_mwh_residencial",
        "Consumo comercial (MWh)": "consumo_mwh_comercial",
        "Consumo por consumidor residencial (kWh)": "kwh_por_consumidor_residencial",
        "Consumo por consumidor comercial (kWh)": "kwh_por_consumidor_comercial",
    }
    c_a, c_b = st.columns(2)
    with c_a:
        var_x_label = st.selectbox("Variável do eixo X", list(variaveis.keys()), index=0)
    with c_b:
        var_y_label = st.selectbox("Variável do eixo Y", list(variaveis.keys()), index=4)
    xcol, ycol = variaveis[var_x_label], variaveis[var_y_label]
    r, p, n = correlacao_segura(base[xcol], base[ycol], "pearson")
    rs, ps, _ = correlacao_segura(base[xcol], base[ycol], "spearman")
    m1, m2, m3 = st.columns(3)
    m1.metric("Pearson", "—" if pd.isna(r) else f"{r:.3f}")
    m2.metric("Spearman", "—" if pd.isna(rs) else f"{rs:.3f}")
    m3.metric("Meses válidos", str(n))
    if not pd.isna(r):
        st.caption(f"p-valor de Pearson: {p:.4g}. Um p-valor pequeno não elimina possíveis confundidores nem demonstra causalidade.")
    scatter = base.dropna(subset=[xcol, ycol]).copy()
    fig_corr = px.scatter(scatter, x=xcol, y=ycol, color="periodo_climatico",
                          hover_data=["data_label", "ano", "mes"],
                          color_discrete_map={"Chuvas":CORES["azul"],"Estiagem":CORES["laranja"]},
                          trendline="ols",
                          labels={xcol:var_x_label, ycol:var_y_label, "periodo_climatico":"Período"})
    fig_corr.update_layout(template="plotly_dark", height=470, paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_corr, use_container_width=True)

    st.markdown("#### 🧩 Matriz de correlação")
    cols_corr = [
        "temperatura_media", "temperatura_maxima_media", "dias_muito_quentes",
        "consumo_mwh_residencial", "consumo_mwh_comercial",
        "kwh_por_consumidor_residencial", "kwh_por_consumidor_comercial"
    ]
    matriz = base[cols_corr].corr(method="pearson")
    matriz.index = ["Temp. média", "Temp. máx. média", "Dias quentes", "Consumo residencial",
                    "Consumo comercial", "kWh/consumidor residencial", "kWh/consumidor comercial"]
    matriz.columns = matriz.index
    fig_heat = px.imshow(matriz, text_auto=".2f", aspect="auto",
                         color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
    fig_heat.update_layout(template="plotly_dark", height=560, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_heat, use_container_width=True)

    st.warning("Interpretação: correlações calculadas com séries mensais podem ser influenciadas por sazonalidade, tendência, crescimento populacional, tarifas, renda e mudanças econômicas. O dashboard descreve associações; não estima causalidade.")

# ---------------------------------------------------------------------
# PÁGINA 5 - DADOS E METODOLOGIA
# ---------------------------------------------------------------------
with paginas[4]:
    st.subheader("🗂️ Dados, filtros e metodologia")
    st.markdown("#### Fontes carregadas")
    info1, info2 = st.columns(2)
    with info1:
        st.markdown("**🌡️ Temperatura**")
        st.write(f"- Registros diários carregados: {len(clima_diario):,}".replace(",", "."))
        st.write(f"- Cobertura: {clima_diario['date'].min():%d/%m/%Y} a {clima_diario['date'].max():%d/%m/%Y}")
        st.write("- Local informado no nome da base: Asa Sul, Brasília")
        st.write("- Variáveis utilizadas: tmax_c, tmin_c, tmed_c")
    with info2:
        st.markdown("**⚡ Consumo elétrico**")
        st.write(f"- Registros após filtro DF e classes: {len(consumo_mensal):,}".replace(",", "."))
        st.write(f"- Cobertura: {consumo_mensal['mes_ref'].min():%m/%Y} a {consumo_mensal['mes_ref'].max():%m/%Y}")
        st.write("- Aba: CONSUMO E NUMCONS SAM UF")
        st.write("- UF: DF | Classes: Residencial e Comercial")
        st.write("- Tipos de consumidor: Cativo e Livre, somados por mês/classe")

    st.markdown("#### Intervalo selecionado e cobertura efetiva")
    st.write(f"Período solicitado: **{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}**")
    st.write(f"Meses após cruzamento interno (inner join): **{len(base)}**")
    st.write(f"Primeiro mês comparável: **{base['mes_ref'].min():%m/%Y}**")
    st.write(f"Último mês comparável: **{base['mes_ref'].max():%m/%Y}**")
    esperados = pd.period_range(pd.Timestamp(inicio).to_period("M"), pd.Timestamp(fim).to_period("M"), freq="M")
    st.write(f"Meses esperados no intervalo: **{len(esperados)}** | Meses efetivamente comparados: **{len(base)}**")

    st.markdown("#### Regras metodológicas")
    st.markdown("""
    - A base climática diária é agregada para mês: médias das temperaturas diárias.
    - Dias muito quentes são dias cuja temperatura máxima diária supera o percentil escolhido no filtro. O limiar é calculado na referência fixa 2005–2025, para permitir comparações justas entre intervalos diferentes.
    - O consumo da EPE é filtrado para UF = DF e classes Residencial/Comercial.
    - Cativo e Livre são somados quando disponíveis. A ausência de uma linha de mercado livre em um mês não é tratada como ausência de toda a classe.
    - Consumo por consumidor = consumo mensal em kWh dividido pela quantidade mensal de consumidores.
    - O cruzamento é feito pela competência mensal; apenas meses presentes nas duas fontes entram na análise.
    - Período chuvoso/estiagem é uma classificação sazonal configurável por mês, não uma medição direta de precipitação.
    - Correlação mede associação estatística e não demonstra causalidade.
    """)

    st.markdown("#### Prévia da base mensal consolidada")
    mostrar = [
        "mes_ref", "temperatura_media", "temperatura_maxima_media", "temperatura_minima_media",
        "dias_muito_quentes", "consumo_mwh_residencial", "consumo_mwh_comercial",
        "consumidores_residencial", "consumidores_comercial",
        "kwh_por_consumidor_residencial", "kwh_por_consumidor_comercial", "periodo_climatico"
    ]
    st.dataframe(base[mostrar].rename(columns={"mes_ref":"Mês"}), use_container_width=True, hide_index=True)

    csv_bytes = base.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    st.download_button("⬇️ Baixar base consolidada (CSV)", data=csv_bytes,
                       file_name="base_clima_energia_mensal.csv", mime="text/csv")

    st.markdown("#### Verificação de valores ausentes")
    ausentes = base[mostrar].isna().sum().rename("Valores ausentes").to_frame()
    st.dataframe(ausentes, use_container_width=True)

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#8299AA;font-size:.8rem'>CLIMA & ENERGIA • Projeto acadêmico de análise de dados • "
    "Temperatura: Asa Sul | Consumo: Distrito Federal</div>",
    unsafe_allow_html=True
)
