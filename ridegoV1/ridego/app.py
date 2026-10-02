"""
`App` — o "front controller" que amarra as três camadas do MVC.

É aqui (e só aqui) que Model, View e Controller se conhecem:

1. Cria o `RideController` (que por sua vez cria o `RideState` — o Model).
2. Mantém um "registro de rotas" (`_routes`) ligando cada caminho (`/`,
   `/categories`, ...) à classe de View responsável por aquela tela.
3. A cada troca de rota do Flet, instancia a View certa e chama
   `view.build()` — sempre da mesma forma, não importa qual tela seja
   (POLIMORFISMO: o código deste arquivo nunca precisa de um
   `if isinstance(view, HomeView)` para saber o que fazer).
"""
from __future__ import annotations

import flet as ft

from ridego.controller import RideController
from ridego.views import (
    BaseView,
    CategoriesView,
    HistoryView,
    HomeView,
    MatchingView,
    RateView,
    SplashView,
    Theme,
)


class App:
    """Ponto único de montagem do app: configura a página, inicializa o Model/Controller e roteia as Views."""

    #: largura "de celular" usada tanto na janela desktop quanto na
    #: moldura aplicada quando o app roda numa aba de navegador larga.
    PHONE_WIDTH = 402
    PHONE_HEIGHT = 874

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.controller = RideController(page)

        # "Registro de rotas": cada rota aponta para a CLASSE da tela (não
        # uma instância) — uma instância nova é criada a cada navegação,
        # sempre com os dados mais atuais do controller.
        self._routes: dict[str, type[BaseView]] = {
            HomeView.route: HomeView,
            CategoriesView.route: CategoriesView,
            MatchingView.route: MatchingView,
            RateView.route: RateView,
            HistoryView.route: HistoryView,
        }

    async def run(self) -> None:
        """Ponto de entrada chamado pelo `main.py` assim que a sessão do Flet começa."""
        await self._configure_page()
        await self.controller.initialize()
        await self._show_splash_screen()

        self.page.on_route_change = self._handle_route_change
        self.page.on_view_pop = self._handle_view_pop
        # Se a janela/aba for redimensionada (ex.: usuário arrasta a borda
        # da janela desktop), reconstruímos a tela atual para a "moldura de
        # celular" (ver `_apply_phone_frame`) reavaliar se ainda é
        # necessária.
        self.page.on_resize = lambda e: self._handle_route_change()
        self._handle_route_change()  # desenha a primeira tela "de verdade" (Home)

    # ------------------------------------------------------------------
    # Configuração inicial da página
    # ------------------------------------------------------------------
    async def _configure_page(self) -> None:
        self.page.title = "RideGo — exercício de clone de app de mobilidade"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = Theme.build_flet_theme()
        self.page.bgcolor = Theme.BG

        # Tamanho da janela quando rodado como app DESKTOP (`python main.py`).
        # Isso não tem efeito nenhum num navegador (`flet run --web`) nem
        # num celular de verdade — nos dois casos o app já ocupa a
        # tela/aba inteira, que é o comportamento correto. Para o caso do
        # navegador, veja `_apply_phone_frame` logo abaixo.
        self.page.window.width = self.PHONE_WIDTH
        self.page.window.height = self.PHONE_HEIGHT
        self.page.window.resizable = True

        # `window.center()` só existe de verdade numa JANELA (desktop). No
        # celular (Android/iOS) e no navegador não há janela nenhuma pra
        # centralizar — chamar isso lá trava o app com um
        # `TimeoutException`, porque o cliente nunca responde a um comando
        # que não faz sentido pra ele. `page.platform.is_desktop()` avisa
        # se estamos rodando em Windows/macOS/Linux; só nesse caso vale a
        # pena centralizar (e usamos `await`, porque nesta versão do Flet
        # `window.center()` é assíncrono).
        if self.page.platform is not None and self.page.platform.is_desktop():
            await self.page.window.center()

    # ------------------------------------------------------------------
    # Splash screen (~3s)
    # ------------------------------------------------------------------
    async def _show_splash_screen(self) -> None:
        """
        Mostra a `SplashView` diretamente (fora do sistema de rotas), então
        ela não fica no histórico de navegação e o botão "voltar" nunca
        retorna para ela.

        IMPORTANTE: não fazemos `page.views.clear()` aqui antes de
        `_handle_route_change()` rodar — isso deixaria `page.views` vazio
        bem no momento em que `HomeView.build()` tenta registrar serviços
        de página (que internamente dependem de `page.views[0]` existir),
        causando `RuntimeError: views list is empty.`. Por isso a splash
        continua no lugar; é o próprio `_handle_route_change()` (abaixo)
        quem constrói a tela seguinte primeiro e só depois troca a view.
        """
        splash = SplashView(self.page, self.controller)
        self.page.views.append(self._apply_phone_frame(splash.build()))
        await splash.play_intro_and_wait()

    # ------------------------------------------------------------------
    # Roteamento
    # ------------------------------------------------------------------
    def _resolve_view(self) -> BaseView:
        """Descobre qual classe de View corresponde à rota atual (com `HomeView` como padrão)."""
        view_class = self._routes.get(self.page.route, HomeView)
        return view_class(self.page, self.controller)

    def _handle_route_change(self, e: ft.RouteChangeEvent | None = None) -> None:
        # CORREÇÃO DO BUG "views list is empty": construímos a nova tela
        # primeiro (quando a lista de views antiga ainda existe e não está
        # vazia) e só depois limpamos + inserimos a tela nova.
        view = self._resolve_view()
        new_view = view.build()  # polimorfismo: mesma chamada para qualquer tela
        new_view = self._apply_phone_frame(new_view)

        self.page.views.clear()
        self.page.views.append(new_view)
        self.page.update()

    def _apply_phone_frame(self, view: ft.View) -> ft.View:
        """
        Garante que o app sempre pareça um app de celular, mesmo quando
        aberto numa aba de navegador larga (`flet run --web` numa tela de
        desktop): o conteúdo real da tela fica centralizado num "quadro"
        de `PHONE_WIDTH` pixels, com uma faixa neutra escura nas laterais
        — como o preview de um celular. Em telas já estreitas (celular de
        verdade, ou a janela desktop no tamanho definido em
        `_configure_page`), a condição abaixo detecta que não há espaço
        sobrando e devolve a view sem nenhuma alteração.
        """
        page_width = self.page.width
        if page_width is None or page_width <= self.PHONE_WIDTH + 24:
            return view

        original_bgcolor = view.bgcolor or Theme.BG
        original_controls = view.controls
        view.controls = [
            ft.Container(
                expand=True,
                bgcolor="#0F0B1A",
                alignment=ft.Alignment.CENTER,
                content=ft.Container(
                    width=self.PHONE_WIDTH,
                    height=self.PHONE_HEIGHT,
                    bgcolor=original_bgcolor,
                    border_radius=28,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    shadow=ft.BoxShadow(
                        blur_radius=48,
                        color=ft.Colors.with_opacity(0.5, "#000000"),
                        offset=ft.Offset(0, 0),
                    ),
                    content=ft.Column(expand=True, spacing=0, controls=original_controls),
                ),
            )
        ]
        return view

    async def _handle_view_pop(self, e: ft.ViewPopEvent) -> None:
        if e.view is not None and len(self.page.views) > 1:
            self.page.views.remove(e.view)
            await self.page.push_route(self.page.views[-1].route)
