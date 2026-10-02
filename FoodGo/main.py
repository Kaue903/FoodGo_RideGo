# FoodGo — exercício de clone de app de delivery (estilo Keeta/iFood/UberEats)
#
# Sem usar nome, logo ou marca de nenhum app real: só a experiência (telas,
# fluxo de pedido, carrinho, checkout) recriada com dados fictícios.
#
# --------------------------------------------------------------------------
# ARQUITETURA: MVC (Model - View - Controller), versão enxuta
# --------------------------------------------------------------------------
#   models.py      -> MODEL: MenuItem, Restaurant, CartLine, Order (dados +
#                     regrinhas próprias) e a lista fictícia de restaurantes.
#   controller.py   -> CONTROLLER: a classe `AppController`, que guarda o
#                     estado do app (carrinho, pedidos) e faz TODA a regra
#                     de negócio — é o que as Views chamam para ler/mudar dados.
#   views.py        -> VIEW: uma classe por tela (todas herdando de
#                     `BaseView`) — só desenham a interface e reagem a
#                     toques, sem nenhuma regra de negócio própria.
#
# Este arquivo (`main.py`) é o "ponto de entrada": cria o AppController,
# conecta a persistência local e liga o roteamento entre as telas.
#
import flet as ft

from controller import AppController
from views import (
    BG,
    CartView,
    CheckoutView,
    HomeView,
    OrdersView,
    RestaurantView,
    SplashView,
    build_theme,
)


def _build_view_for_route(page: ft.Page, app: AppController) -> ft.View:
    """Roteador: decide qual tela (View) construir para a rota atual.

    POLIMORFISMO em ação: não importa qual classe seja escolhida aqui
    (`HomeView`, `RestaurantView`, `CartView`, ...) — todas "são uma"
    `BaseView` e respondem da mesma forma à chamada `.build()`."""
    troute = ft.TemplateRoute(page.route)

    if troute.match("/restaurant/:id"):
        view = RestaurantView(page, app, troute.id)
    elif page.route == "/cart":
        view = CartView(page, app)
    elif page.route == "/checkout":
        view = CheckoutView(page, app)
    elif page.route == "/orders":
        view = OrdersView(page, app)
    else:
        view = HomeView(page, app)

    return view.build()


async def main(page: ft.Page):
    # ---- Configurações gerais da página/app ----
    page.title = "FoodGo — exercício de clone de app de delivery"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = build_theme()
    page.bgcolor = BG

    # Define o tamanho da janela (largura e altura em pixels) — usamos uma
    # proporção parecida com a de um celular, já que o FoodGo foi pensado
    # como um app mobile. Ajuste esses números se quiser uma janela maior
    # ou menor ao testar no computador.
    page.window.width = 320
    page.window.height = 600
    # Trava o redimensionamento e fixa o mín/máx no mesmo valor — isso evita
    # que a janela "pule" para outro tamanho ao carregar (bug conhecido do
    # Flet quando width/height não vêm acompanhados de min/max travados).
    page.window.min_width = 320
    page.window.max_width = 320
    page.window.min_height = 600
    page.window.max_height = 600
    page.window.resizable = False
    # IMPORTANTE: sem esse page.update() aqui, o Flet às vezes ignora o
    # tamanho definido acima e abre a janela com o tamanho padrão/da tela —
    # é um bug conhecido do Flet quando não se força uma atualização logo
    # após configurar a janela, antes de qualquer outro await.
    page.update()
    try:
        # Centraliza a janela na tela (disponível em builds desktop; em
        # alguns ambientes web esse método pode não existir/fazer sentido,
        # por isso o try/except para não quebrar o app nesses casos).
        await page.window.center()
    except Exception:
        pass

    # ---- Controller (Model já vem "dentro" dele, importado de models.py) ----
    app_controller = AppController()
    prefs = ft.SharedPreferences()
    page.services.append(prefs)
    app_controller.bind(prefs)
    await app_controller.load()

    def route_change(e=None):
        page.views.clear()
        page.views.append(_build_view_for_route(page, app_controller))
        page.update()

    async def view_pop(e: ft.ViewPopEvent):
        if e.view is not None and len(page.views) > 1:
            page.views.remove(e.view)
            await page.push_route(page.views[-1].route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # ---- Splash screen: aparece primeiro, por 3 segundos ----
    # A navegação normal (route_change) só é ligada e disparada DEPOIS que
    # a splash termina, para o usuário sempre ver a tela de abertura antes
    # de qualquer outra tela, não importa qual rota o app abriria.
    await SplashView(page, app_controller).show()
    page.route = page.route if page.route not in (None, "/splash") else "/"
    route_change()


if __name__ == "__main__":
    # `assets_dir="assets"` diz ao Flet onde procurar arquivos estáticos
    # (aqui, o logo.png usado na splash screen e na barra superior).
    ft.run(main, assets_dir="assets")
