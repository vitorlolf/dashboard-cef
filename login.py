from dash import html, dcc
import dash_bootstrap_components as dbc

layout_login = html.Div(
    style={
        "backgroundColor": "#1e1e1e",
        "minHeight": "100vh",
        "display": "flex",
        "flexDirection": "column",
        "justifyContent": "center",
        "alignItems": "center",
        "padding": "40px"
    },
    children=[
        html.H1("Portal do Cliente", style={"color": "white", "marginBottom": "20px"}),

        html.Img(src="/assets/image.png", style={"height": "250px", "marginBottom": "10px"}),

        html.Div([
            html.H4("Acesse o Portal", style={"color": "white", "marginBottom": "20px", "textAlign": "center"}),

            dbc.Input(id="usuario", placeholder="Usuário (e-mail)", type="email", style={"marginBottom": "10px"}),
            dbc.Input(id="senha", placeholder="Senha", type="password", style={"marginBottom": "20px"}),

            dbc.Button("Entrar", id="botao-login", color="dark", style={"width": "100%", "fontWeight": "bold"})
        ], style={
            "backgroundColor": "#2c2c2c",
            "padding": "30px",
            "borderRadius": "10px",
            "width": "100%",
            "maxWidth": "400px",
            "boxShadow": "0px 4px 10px rgba(0, 0, 0, 0.4)"
        }),

        html.Div("by lab serges", style={"color": "white", "fontSize": "12px", "marginTop": "20px"})
    ]
)