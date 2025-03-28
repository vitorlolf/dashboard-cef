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

API_TOKEN = ("eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NDMxMDEwOTAsImp0aSI6ImVlZmVlM2Q1LTQzM2EtNGJlOS04MmVjLWFiMDBhNzgzMmIxZCIsInN1YiI6MzA1ODYwNjQ0LCJ1c2VyIjp7ImlkIjozMDU4NjA2NDQsImVtYWlsIjoidml0b3IuZnJhbmNvQHNlcmdlcy5vcmcifX0.7t8mcnmeeEYF7NUPeYOohLfGU2hiN7s47oUJN7-4mElzdnGHWyIFCW3H1TFhB66k63PAuaiF8Z4QptIoUjNfEg")
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

def coletar_dados():
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
            try:
                cards_data = response.json()["data"]["phase"]["cards"]
            except KeyError:
                print("❌ A resposta da API NÃO contém 'data'. Veja o conteúdo completo:")
                print(response.json())
                return pd.DataFrame()

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

    return df

df = coletar_dados()

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    dcc.Location(id='url'),
    html.Div(id='pagina-conteudo', children=layout_login)
])

layout_dashboard = dbc.Container([
    dbc.Row([
        dbc.Col(html.H2("ACOMPANHAMENTO EPS - 2025", className="text-center text-info mb-4 fw-bold", style={"fontSize": "28px"}))
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Tabela Detalhada", className="bg-dark text-white"),
                dbc.CardBody([
                    dash_table.DataTable(
                        id='tabela-dados',
                        columns=[{"name": i, "id": i} for i in df.columns if i not in ["Data de Criação"]],
                        data=df.to_dict('records'),
                        page_size=10,
                        filter_action="native",
                        style_table={"overflowX": "auto", "maxWidth": "100%"},
                        style_header={"backgroundColor": "#2c2f33", "color": "white", "fontWeight": "bold"},
                        style_cell={"backgroundColor": "#1e1e1e", "color": "white", "textAlign": "left"},
                        style_filter={"backgroundColor": "#2c2f33", "color": "white"}
                    )
                ])
            ])
        ])
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("PERÍODO", className="fw-bold text-uppercase text-light small"),
                            dcc.Dropdown(id="filtro-periodo", options=[{"label": p, "value": p} for p in sorted(df["Período"].dropna().unique())] if "Período" in df.columns else [], multi=True)
                        ], md=4),

                        dbc.Col([
                            html.Label("REGIÃO", className="fw-bold text-uppercase text-light small"),
                            dcc.Dropdown(id="filtro-estado", options=[{"label": e, "value": e} for e in sorted(df["Estado"].dropna().unique())] if "Estado" in df.columns else [], multi=True)
                        ], md=4),

                        dbc.Col([
                            html.Label("", className="d-none d-md-block"),
                            dbc.Button("\U0001F4C5 Baixar Excel", id="download-link", color="info", className="w-100", href="", target="_blank")
                        ], md=4, className="d-flex align-items-end justify-content-end")
                    ])
                ], className="bg-secondary")
            ])
        ])
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Distribuição por Status dos Cards", className="bg-dark text-white"),
                dbc.CardBody([
                    dcc.Graph(id="grafico-fases")
                ])
            ])
        ])
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.Div(id="porcentagem-info", className="text-center text-light mb-4")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("EPS Previstos por Período", className="bg-dark text-white"),
                dbc.CardBody([
                    dcc.Graph(id="grafico-eps")
                ])
            ])
        ])
    ])

], fluid=True, className="bg-dark p-4")

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port)
