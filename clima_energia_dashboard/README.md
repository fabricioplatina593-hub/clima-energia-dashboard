# CLIMA & ENERGIA — Dashboard em Python

Dashboard interativo para investigar a associação entre temperatura diária na Asa Sul e consumo mensal de energia elétrica no Distrito Federal.

## O que o aplicativo faz
- Lê automaticamente os arquivos originais na pasta `dados_originais/`.
- Permite também enviar arquivos pela barra lateral.
- Descobre a interseção real entre os meses disponíveis nas duas bases.
- Permite selecionar o período comparável no próprio dashboard.
- Filtra consumo para UF = DF e classes Residencial e Comercial.
- Soma Cativo e Livre quando houver registros para a competência.
- Agrega temperaturas diárias em indicadores mensais.
- Calcula consumo por consumidor, dias muito quentes, variação anual e correlações.
- Permite exportar a base mensal consolidada.

## Arquivos esperados
Os nomes abaixo já estão incluídos na pasta `dados_originais/`:
- `Dados_abertos_Consumo_Mensal.xlsx`
- `serie_diaria_asa_sul_1976_2026.csv`

## Como executar no Windows
1. Instale o Python 3.10 ou superior: https://www.python.org/downloads/
2. Extraia o ZIP para uma pasta do computador.
3. Abra essa pasta no VS Code.
4. Abra o terminal do VS Code (Terminal > Novo Terminal).
5. Execute:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

O navegador abrirá o dashboard. Se não abrir automaticamente, copie o endereço local exibido no terminal (normalmente http://localhost:8501).

## Como usar
- Na barra lateral, os arquivos podem ser enviados novamente, se necessário.
- O app mostra automaticamente o intervalo de meses existente nas duas bases e abre por padrão em 2005–2025; você pode explorar qualquer outro intervalo dentro da interseção disponível.
- Selecione o intervalo desejado. Para a configuração original do projeto, escolha janeiro/2005 a dezembro/2025.
- Ajuste o percentil para definir o critério de dia muito quente.
- Ajuste os meses considerados chuvosos; os demais serão classificados como estiagem.
- Escolha Residencial, Comercial ou comparação das duas classes.

## Observações metodológicas importantes
- A temperatura é representativa da série fornecida para a Asa Sul; o consumo é agregado para todo o Distrito Federal. Não é uma comparação espacial perfeitamente equivalente.
- O consumo por consumidor é calculado como MWh × 1.000 / número de consumidores.
- O arquivo EPE contém linhas Cativo e Livre. O aplicativo soma os tipos disponíveis por mês e classe; não interpreta a falta de linha Livre como consumo zero separado.
- O limite de "dia muito quente" é o percentil escolhido das máximas diárias na referência fixa 2005–2025, mantendo a mesma definição ao mudar o período visualizado. É uma definição operacional para análise, não um alerta meteorológico oficial.
- A classificação de estiagem/chuvas é baseada nos meses selecionados pelo usuário, não em precipitação observada, pois a planilha climática fornecida não contém chuva.
- Correlação não implica causalidade. Tendências de população, renda, tarifa, atividade econômica e sazonalidade podem influenciar o consumo.

## Fontes dos arquivos
- Consumo mensal: planilha da EPE fornecida pelo usuário.
- Temperatura diária: série da Asa Sul fornecida pelo usuário.
