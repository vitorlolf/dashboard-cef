import requests
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import io
import base64
import os
import webbrowser
from login import layout_login

API_TOKEN = 'eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NDI5MDczMTAsImp0aSI6ImZiOTQzNmNiLWUyZjYtNDcwNy1iODZjLTEzODE3ZTMxOTU2MiIsInN1YiI6MzA1ODYwNjQ0LCJ1c2VyIjp7ImlkIjozMDU4NjA2NDQsImVtYWlsIjoidml0b3IuZnJhbmNvQHNlcmdlcy5vcmcifX0.lbFXscA19fn2_XUT-QdT2DuJBRMxyDArQ03CRNgDkTXicsC-9ii1gl5DFjrA49_2tGUyPZmEhMJlw8mQNgy9Hg'
phases = [
    {"id": 334867668, "name": "Em Aberto"},
    {"id": 334867669, "name": "Em Captação"},
    {"id": 334867674, "name": "Cadastro Médico"},
    {"id": 334867670, "name": "Aguardando Agenda"},
    {"id": 334867673, "name": "Confirmação CEF"},
    {"id": 334867671, "name": "Aguardando/Em Atendimento"},
    {"id": 334867678, "name": "Cancelado/Reagendado"},
    {"id": 334867672, "name": "Atendimento Realizado"},
    {"id": 334867677, "name": "Conferência do Atendimento"},
    {"id": 334867683, "name": "Liberado para Pagamento"},
    {"id": 334867675, "name": "NF Solicitada"},
    {"id": 334867679, "name": "NF recebida"},
    {"id": 334867680, "name": "Pagamento realizado"},
    {"id": 334867676, "name": "Excluído da Previsão"},
]

print("🔄 Iniciando coleta de dados...")
url = "https://api.pipefy.com/graphql"
headers = {"Authorization": f"Bearer {API_TOKEN}"}
todos_os_registros = []

for fase in phases:
    print(f"🔍 Coletando fase: {fase['name']}")
    has_next_page = True
    end_cursor = None

    while has_next_page:
        after_clause = f', after: "{end_cursor}"' if end_cursor else ''
        query = f"""
        {{
          phase(id: {fase['id']}) {{
            name
            cards(first: 100{after_clause}) {{
              pageInfo {{ hasNextPage endCursor }}
              edges {{
                node {{
                  title
                  createdAt
                  current_phase {{ name }}
                  fields {{ name value }}
                }}
              }}
            }}
          }}
        }}
        """

        response = requests.post(url, json={"query": query}, headers=headers)
        data = response.json()
        cards_data = data["data"]["phase"]["cards"]
        cards = cards_data["edges"]

        for card in cards:
            node = card["node"]
            registro = {
                "Título": node["title"],
                "Fase Atual": node["current_phase"]["name"],
                "Fase de Origem": fase["name"]
            }
            for campo in node["fields"]:
                nome = campo["name"]
                valor = campo["value"]
                registro[nome] = valor
                if nome == "EPS Previstos":
                    try:
                        eps_valor = float(valor)
                        registro["EPS Previstos (Fase Inicial)"] = eps_valor
                    except:
                        registro["EPS Previstos (Fase Inicial)"] = None
            todos_os_registros.append(registro)

        has_next_page = cards_data["pageInfo"]["hasNextPage"]
        end_cursor = cards_data["pageInfo"]["endCursor"]

    print(f"✅ Fase coletada: {fase['name']}")

print(f"\n✅ Total geral de cards coletados: {len(todos_os_registros)}\n")

df = pd.DataFrame(todos_os_registros)

for col in ["EPS Previstos", "EPS Realizados", "EPS Previstos (Fase Inicial)"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    dcc.Location(id='url'),
    html.Div(id='pagina-conteudo', children=layout_login)
])

layout_dashboard = html.Div([
    html.Div([
        html.H1("DASHBOARD - EPS CEF 2025", style={"textAlign": "center", "color": "white"}),
        html.Div(
            html.A("📥 Baixar Excel", id="download-link", download="dados_filtrados.xlsx", href="", target="_blank",
                   style={
                       "padding": "8px 16px",
                       "backgroundColor": "#1e1e1e",
                       "border": "1px solid white",
                       "color": "white",
                       "fontWeight": "bold",
                       "borderRadius": "6px",
                       "textDecoration": "none",
                       "transition": "0.3s"
                   }),
            style={"position": "absolute", "top": "10px", "right": "30px"}
        )
    ], style={"position": "relative"}),

    html.Div([
        dash_table.DataTable(
            id='tabela-dados',
            columns=[{"name": i, "id": i} for i in df.columns if i not in ["Data de Criação"]],
            data=df.to_dict('records'),
            page_size=10,
            filter_action="native",
            style_table={"overflowX": "auto"},
            style_header={"backgroundColor": "#333", "color": "white", "fontWeight": "bold"},
            style_cell={"backgroundColor": "#1e1e1e", "color": "white", "textAlign": "left"}
        ),
        html.Br(),
        html.Div([
            html.Div([
                html.Label("PERÍODO", style={"fontWeight": "bold", "textTransform": "uppercase", "color": "white", "fontSize": "12px"}),
                dcc.Dropdown(id="filtro-periodo", options=[{"label": p, "value": p} for p in sorted(df["Período"].dropna().unique())] if "Período" in df.columns else [], multi=True, style={"fontSize": "12px"})
            ], style={"width": "200px", "margin": "0 10px"}),

            html.Div([
                html.Label("REGIÃO", style={"fontWeight": "bold", "textTransform": "uppercase", "color": "white", "fontSize": "12px"}),
                dcc.Dropdown(id="filtro-estado", options=[{"label": e, "value": e} for e in sorted(df["Estado"].dropna().unique())] if "Estado" in df.columns else [], multi=True, style={"fontSize": "12px"})
            ], style={"width": "200px", "margin": "0 10px"})
        ], style={"display": "flex", "justifyContent": "center"})
    ]),

    html.Br(),
    dcc.Graph(id="grafico-fases", style={"transform": "scale(0.95)", "transformOrigin": "top"}),
    html.Div(id="porcentagem-info", style={"color": "white", "textAlign": "center", "marginBottom": "40px"}),
    dcc.Graph(id="grafico-eps", style={"transform": "scale(0.95)", "transformOrigin": "top"})

], style={"backgroundColor": "#1e1e1e", "padding": "20px"})

@app.callback(
    Output("pagina-conteudo", "children"),
    Input("botao-login", "n_clicks"),
    State("usuario", "value"),
    State("senha", "value")
)
def autenticar(n, usuario, senha):
    if usuario == "projetos.cef@serges.org" and senha == "SERGES@2025":
        return layout_dashboard
    return layout_login

@app.callback(
    Output("grafico-fases", "figure"),
    Output("grafico-eps", "figure"),
    Output("porcentagem-info", "children"),
    Input("filtro-estado", "value"),
    Input("filtro-periodo", "value")
)
def atualizar_graficos(estados, periodos):
    df_filtrado = df.copy()
    if estados:
        df_filtrado = df_filtrado[df_filtrado["Estado"].isin(estados)]
    if periodos:
        df_filtrado = df_filtrado[df_filtrado["Período"].isin(periodos)]

    df_contagem = df_filtrado["Fase Atual"].value_counts().reset_index()
    df_contagem.columns = ["Fase Atual", "Total"]
    df_contagem["%"] = (df_contagem["Total"] / df_contagem["Total"].sum()) * 100

    fig1 = px.bar(
        df_contagem,
        x="Fase Atual",
        y="%",
        text="%",
        title="Distribuição por Status dos Cards",
        labels={"%": "% de cards"},
        color_discrete_sequence=["#0056b3"]
    )
    fig1.update_traces(
        texttemplate="%{y:.1f}%",
        textposition="outside",
        textfont={"size": 14, "color": "white", "family": "Arial", "weight": "bold"},
        hovertemplate="<b>%{x}</b><br>%{y:.1f}%<br>Total: %{customdata[0]} cards<extra></extra>",
        customdata=df_contagem[["Total"]]
    )
    fig1.update_layout(
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e",
        font_color="white",
        margin=dict(t=60, b=60),
        uniformtext_minsize=12,
        uniformtext_mode='hide'
    )

    porcentagem_texto = f"Total de cards filtrados: {df_filtrado.shape[0]}"

    if "EPS Previstos (Fase Inicial)" in df_filtrado.columns:
        df_eps = df_filtrado[df_filtrado["EPS Previstos (Fase Inicial)"].notna()]
        df_eps = df_eps.groupby("Período")["EPS Previstos (Fase Inicial)"].sum().reset_index()

        fig2 = px.line(df_eps, x="Período", y="EPS Previstos (Fase Inicial)",
                       markers=True, title="EPS Previstos por Período",
                       color_discrete_sequence=["#0056b3"])
        fig2.update_layout(
            plot_bgcolor="#1e1e1e",
            paper_bgcolor="#1e1e1e",
            font_color="white",
            yaxis=dict(tickformat=",d")
        )
    else:
        fig2 = px.line(title="Dados de EPS não disponíveis")
        fig2.update_layout(plot_bgcolor="#1e1e1e", paper_bgcolor="#1e1e1e", font_color="white")

    return fig1, fig2, porcentagem_texto

@app.callback(
    Output("download-link", "href"),
    Input("filtro-estado", "value"),
    Input("filtro-periodo", "value")
)
def exportar_excel(estados, periodos):
    df_filtrado = df.copy()
    if estados:
        df_filtrado = df_filtrado[df_filtrado["Estado"].isin(estados)]
    if periodos:
        df_filtrado = df_filtrado[df_filtrado["Período"].isin(periodos)]

    df_export = df_filtrado.drop(columns=["Data de Criação"] if "Data de Criação" in df_filtrado.columns else [])
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Dados")
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode()
    return f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{encoded}"

app = Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Meu App"
server = app.server

if __name__ == "__main__":
    print("✅ Iniciando dashboard com login...")
    app.run(debug=True)
