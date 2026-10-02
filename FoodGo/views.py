"""
views.py — camada VIEW do padrão MVC.

Um único arquivo com TODAS as telas do FoodGo. Cada tela é uma classe
que herda de `BaseView` e implementa `build()`, devolvendo um
`flet.View` pronto. As Views só chamam métodos do `AppController`
(`controller.py`) para ler/alterar dados — nunca fazem contas de
negócio nem mexem em armazenamento local.

"""
import asyncio
from abc import ABC, abstractmethod

import flet as ft

# ==========================================================================
# 1) Paleta de cores e estilos (constantes + funções utilitárias)
# ==========================================================================
PRIMARY = "#FF6B35"       # laranja vibrante (cor principal da marca)
SECONDARY = "#EC186A"     # rosa/vermelho vibrante (usado em gradientes)
BG = "#FFF7F2"            # fundo geral do app
SURFACE = "#FFFFFF"       # fundo dos cartões
MUTED = "#8A8A8E"         # cinza usado em textos secundários
TEXT_DARK = "#1A1A1A"     # cor de texto principal

CARD_SHADOW = ft.BoxShadow(
    spread_radius=0,
    blur_radius=16,
    color=ft.Colors.with_opacity(0.07, ft.Colors.BLACK),
    offset=ft.Offset(0, 4),
)

# "Pilulazinha" de status usada no histórico de pedidos: (fundo, texto).
STATUS_COLORS = {
    "Em preparo": ("#FFF3CD", "#8A6D00"),
    "A caminho": ("#DCEBFF", "#0B5ED7"),
    "Entregue": ("#DDF4E4", "#1E7A34"),
}


def gradient(colors) -> ft.LinearGradient:
    """Cria um gradiente diagonal a partir de uma lista/tupla de cores."""
    return ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT, colors=list(colors))


def border_all(width: float, color: str) -> ft.Border:
    """Cria uma borda igual nos 4 lados de um Container."""
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, bottom=side, left=side, right=side)


def build_theme() -> ft.Theme:
    """Tema Material 3 do app: cor semente laranja (combina com o logo)."""
    return ft.Theme(color_scheme_seed=PRIMARY, use_material3=True)


# ==========================================================================
# 2) Componentes visuais reutilizáveis (usados em mais de uma tela)
# ==========================================================================
def branded_appbar(title_text: str, *, show_logo: bool = False) -> ft.AppBar:
    """Barra superior padrão: fundo laranja, título branco e, na tela
    inicial, o logo do app do lado esquerdo."""
    leading = None
    if show_logo:
        leading = ft.Container(
            padding=ft.Padding(14, 0, 0, 0),
            content=ft.Container(width=32, height=32, border_radius=9, content=ft.Image(src="icon.png", fit=ft.BoxFit.CONTAIN)),
        )
    return ft.AppBar(
        title=ft.Text(title_text, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=20),
        center_title=False,
        bgcolor=PRIMARY,
        leading=leading,
        leading_width=52 if show_logo else None,
    )


def white_pill(text: str) -> ft.Container:
    """"Pilulazinha" translúcida branca, usada sobre fundos coloridos."""
    return ft.Container(
        padding=ft.Padding(10, 5, 10, 5),
        border_radius=20,
        bgcolor=ft.Colors.with_opacity(0.22, ft.Colors.WHITE),
        content=ft.Text(text, size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
    )


def row_kv(key: str, value: str, bold: bool = False) -> ft.Row:
    """Linha "rótulo : valor" alinhada nas pontas (resumo do carrinho/checkout)."""
    weight = ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL
    size = 16 if bold else 14
    return ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Text(key, weight=weight, size=size, color=TEXT_DARK if bold else MUTED),
            ft.Text(value, weight=weight, size=size, color=TEXT_DARK),
        ],
    )


def gradient_button(text: str, *, icon=None, on_click=None) -> ft.Container:
    """Botão principal do app: fundo em gradiente laranja -> rosa."""
    row_controls = []
    if icon:
        row_controls.append(ft.Icon(icon, color=ft.Colors.WHITE, size=18))
    row_controls.append(ft.Text(text, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=15))
    return ft.Container(
        gradient=gradient([PRIMARY, SECONDARY]),
        border_radius=14,
        content=ft.TextButton(
            content=ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=8, controls=row_controls),
            on_click=on_click,
            style=ft.ButtonStyle(padding=16, shape=ft.RoundedRectangleBorder(radius=14)),
        ),
    )


def empty_state(icon, text: str, button_text: str | None = None, on_click=None) -> ft.Container:
    """Estado "vazio" reutilizável (carrinho vazio, sem pedidos, sem resultado)."""
    controls = [
        ft.Icon(icon, size=56, color=ft.Colors.with_opacity(0.35, PRIMARY)),
        ft.Container(height=10),
        ft.Text(text, color=MUTED, size=14, text_align=ft.TextAlign.CENTER),
    ]
    if button_text and on_click:
        controls += [ft.Container(height=18), gradient_button(button_text, on_click=on_click)]
    return ft.Container(padding=40, content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=controls))


def category_chip(label: str, active: bool, on_click) -> ft.Container:
    """"Chip" de categoria clicável, usado nos filtros da tela inicial."""
    return ft.Container(
        padding=ft.Padding(16, 8, 16, 8),
        border_radius=20,
        bgcolor=PRIMARY if active else ft.Colors.WHITE,
        border=None if active else border_all(1, ft.Colors.with_opacity(0.15, ft.Colors.BLACK)),
        on_click=on_click,
        content=ft.Text(
            label, size=13,
            color=ft.Colors.WHITE if active else "#444444",
            weight=ft.FontWeight.W_600 if active else ft.FontWeight.NORMAL,
        ),
    )


def circle_icon_button(icon, *, filled: bool, on_click, icon_size: int = 18, tooltip: str | None = None) -> ft.IconButton:
    """Botãozinho redondo dos seletores de quantidade (+/-)."""
    return ft.IconButton(
        icon,
        icon_size=icon_size,
        icon_color=ft.Colors.WHITE if filled else PRIMARY,
        bgcolor=PRIMARY if filled else ft.Colors.with_opacity(0.10, PRIMARY),
        style=ft.ButtonStyle(shape=ft.CircleBorder()),
        tooltip=tooltip,
        on_click=on_click,
    )


# ==========================================================================
# 3) BaseView — classe-mãe (abstrata) de todas as telas
# ==========================================================================
class BaseView(ABC):
    """Contrato + utilitários comuns a todas as telas do app."""

    def __init__(self, page: ft.Page, app):
        self.page = page
        self.app = app  # o AppController (camada Controller)

    @abstractmethod
    def build(self) -> ft.View:
        """Constrói e devolve o `ft.View` desta tela. Toda subclasse
        concreta é OBRIGADA a implementar isto (o `abstractmethod`
        garante: esquecer de implementar dá erro na hora de instanciar)."""
        raise NotImplementedError

    # ---- barra de navegação inferior (Início / Carrinho / Pedidos) ----
    def _nav_content(self, active: str) -> ft.Row:
        def tab(icon_outline, icon_filled, label, route, key, badge: int = 0):
            is_active = key == active
            color = PRIMARY if is_active else MUTED
            icon_stack = [ft.Icon(icon_filled if is_active else icon_outline, color=color, size=24)]
            if badge:
                icon_stack.append(
                    ft.Container(
                        top=-4, right=-10,
                        padding=ft.Padding(5, 1, 5, 1),
                        bgcolor=SECONDARY,
                        border_radius=20,
                        content=ft.Text(str(badge), size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    )
                )
            return ft.Container(
                expand=True,
                padding=8,
                on_click=lambda e: self.page.navigate(route),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                    controls=[
                        # clip_behavior=NONE é essencial: por padrão o Stack
                        # CORTA qualquer filho que ultrapasse sua caixa, e o
                        # badge é posicionado de propósito um pouco para
                        # fora (top=-4, right=-10) para ficar no "cantinho"
                        # do ícone — sem isso, o balãozinho ficava cortado.
                        ft.Stack(controls=icon_stack, width=34, height=24, clip_behavior=ft.ClipBehavior.NONE),
                        ft.Text(label, size=11, color=color, weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL),
                    ],
                ),
            )

        return ft.Row(
            controls=[
                tab(ft.Icons.HOME_OUTLINED, ft.Icons.HOME_ROUNDED, "Início", "/", "home"),
                tab(ft.Icons.SHOPPING_CART_OUTLINED, ft.Icons.SHOPPING_CART_ROUNDED, "Carrinho", "/cart", "cart", badge=self.app.cart_count),
                tab(ft.Icons.RECEIPT_LONG_OUTLINED, ft.Icons.RECEIPT_LONG_ROUNDED, "Pedidos", "/orders", "orders", badge=len(self.app.orders)),
            ],
        )

    def _nav_bar(self, active: str) -> ft.Container:
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border=ft.Border(top=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.BLACK))),
            padding=ft.Padding(0, 8, 0, 8),
            content=self._nav_content(active),
        )

    def _refresh_nav(self, nav_container: ft.Container, active: str) -> None:
        """Reconstrói o conteúdo da barra inferior com os números mais
        recentes de carrinho/pedidos — chamado sempre que eles mudam
        enquanto o usuário continua na mesma tela."""
        nav_container.content = self._nav_content(active)

    # ---- "esqueleto" comum às telas com barra inferior ----
    def _scaffold(self, route: str, active_tab: str, appbar: ft.AppBar, body: list) -> tuple[ft.View, ft.Container]:
        nav_container = self._nav_bar(active_tab)
        view = ft.View(
            route=route,
            padding=0,
            bgcolor=BG,
            controls=[
                ft.SafeArea(
                    expand=True,
                    content=ft.Column(
                        expand=True,
                        spacing=0,
                        controls=[
                            appbar,
                            ft.Container(expand=True, bgcolor=BG, content=ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=body)),
                            nav_container,
                        ],
                    ),
                )
            ],
        )
        return view, nav_container


# ==========================================================================
# 4) SplashView — tela de abertura (animação de entrada)
# ==========================================================================
class SplashView(BaseView):
    """HERANÇA: também "é uma" BaseView; além de `build()`, oferece o
    método extra `show()` (chamado direto pelo main.py) por precisar
    tocar uma animação e esperar um tempo antes de sumir."""

    def __init__(self, page: ft.Page, app):
        super().__init__(page, app)
        fade_in = ft.Animation(650, ft.AnimationCurve.EASE_OUT)
        self._logo_box = ft.Container(
            width=150, height=150, border_radius=34,
            content=ft.Image(src="icon.png", fit=ft.BoxFit.CONTAIN),
            opacity=0, scale=0.75, animate_opacity=fade_in, animate_scale=fade_in,
            shadow=ft.BoxShadow(blur_radius=30, color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK), offset=ft.Offset(0, 10)),
        )
        self._title = ft.Text("FoodGo", size=34, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, opacity=0, animate_opacity=fade_in)
        self._subtitle = ft.Text(
            "Sua comida favorita, sempre por perto", size=13,
            color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE), opacity=0, animate_opacity=fade_in,
        )
        self._loader = ft.ProgressRing(width=22, height=22, stroke_width=2.5, color=ft.Colors.WHITE, opacity=0, animate_opacity=fade_in)

    def build(self) -> ft.View:
        return ft.View(
            route="/splash",
            padding=0,
            controls=[
                ft.Container(
                    expand=True,
                    gradient=gradient([PRIMARY, SECONDARY]),
                    content=ft.Column(
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=18,
                        controls=[
                            self._logo_box,
                            ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, controls=[self._title, self._subtitle]),
                            ft.Container(height=24),
                            self._loader,
                        ],
                    ),
                )
            ],
        )

    async def show(self) -> None:
        """Mostra a splash e conduz a animação de entrada, por um total
        de 3 segundos, antes de devolver o controle ao main.py."""
        self.page.views.append(self.build())
        self.page.update()
        await asyncio.sleep(0.15)
        self._logo_box.opacity = 1
        self._logo_box.scale = 1
        self._title.opacity = 1
        self._subtitle.opacity = 1
        self._loader.opacity = 1
        self.page.update()
        await asyncio.sleep(2.85)


# ==========================================================================
# 5) HomeView — lista de restaurantes com busca e filtro por categoria
# ==========================================================================
class HomeView(BaseView):
    def __init__(self, page: ft.Page, app):
        super().__init__(page, app)
        self._query_text: str = ""
        self._query_category: str = "Todos"
        self._restaurant_list = ft.Column(spacing=12)
        self._chips_row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=8)

    def _restaurant_card(self, r) -> ft.Container:
        c1, c2 = r.banner_colors
        return ft.Container(
            padding=12, border_radius=16, bgcolor=SURFACE, shadow=CARD_SHADOW,
            on_click=lambda e, rid=r.id: self.page.navigate(f"/restaurant/{rid}"),
            content=ft.Row(
                spacing=12,
                controls=[
                    ft.Container(width=64, height=64, border_radius=16, gradient=gradient([c1, c2]), alignment=ft.Alignment.CENTER, content=ft.Text(r.emoji, size=30)),
                    ft.Column(
                        expand=True, spacing=3,
                        controls=[
                            ft.Text(r.name, weight=ft.FontWeight.BOLD, size=15, color=TEXT_DARK),
                            ft.Text(r.category, size=12, color=MUTED),
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Container(
                                        padding=ft.Padding(6, 2, 6, 2), border_radius=8,
                                        bgcolor=ft.Colors.with_opacity(0.12, "#FFA000"),
                                        content=ft.Row(spacing=2, controls=[
                                            ft.Icon(ft.Icons.STAR_ROUNDED, size=13, color="#FFA000"),
                                            ft.Text(f"{r.rating}", size=11, weight=ft.FontWeight.BOLD, color="#FFA000"),
                                        ]),
                                    ),
                                    ft.Text("•  " + r.delivery_time, size=12, color=MUTED),
                                ],
                            ),
                            ft.Text("Entrega grátis" if r.delivery_fee == 0 else f"Taxa R$ {r.delivery_fee:.2f}", size=12, color=MUTED),
                        ],
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=MUTED),
                ],
            ),
        )

    def _refresh_list(self) -> None:
        found = [self._restaurant_card(r) for r in self.app.search_restaurants(self._query_text, self._query_category)]
        self._restaurant_list.controls = found or [empty_state(ft.Icons.SEARCH_OFF_ROUNDED, "Nenhum restaurante encontrado.")]
        self.page.update()

    def _rebuild_chips(self) -> None:
        def select(e, category: str):
            self._query_category = category
            self._refresh_list()
            self._rebuild_chips()

        self._chips_row.controls = [
            category_chip(cat, cat == self._query_category, lambda e, c=cat: select(e, c))
            for cat in self.app.list_categories()
        ]
        self.page.update()

    def _on_search_change(self, e) -> None:
        self._query_text = e.control.value
        self._refresh_list()

    def build(self) -> ft.View:
        self._rebuild_chips()
        self._refresh_list()

        appbar = branded_appbar("FoodGo", show_logo=True)
        body = [
            ft.Container(
                padding=ft.Padding(16, 16, 16, 0),
                content=ft.TextField(
                    hint_text="Buscar restaurante ou categoria...",
                    prefix_icon=ft.Icons.SEARCH_ROUNDED,
                    border_radius=14, filled=True, fill_color=SURFACE,
                    border_color=ft.Colors.TRANSPARENT, focused_border_color=PRIMARY,
                    content_padding=ft.Padding(16, 4, 16, 4),
                    on_change=self._on_search_change,
                ),
            ),
            ft.Container(padding=ft.Padding(16, 14, 16, 0), content=self._chips_row),
            ft.Container(padding=16, content=self._restaurant_list),
        ]
        view, _nav_container = self._scaffold("/", "home", appbar, body)
        return view


# ==========================================================================
# 6) RestaurantView — cardápio de um restaurante
# ==========================================================================
class RestaurantView(BaseView):
    """Tem AppBar própria (cor do banner do restaurante) em vez do
    "esqueleto" padrão, então monta seu próprio `ft.View` — mas ainda
    reaproveita os componentes compartilhados (`gradient_button`, etc.)."""

    def __init__(self, page: ft.Page, app, restaurant_id: str):
        super().__init__(page, app)
        self._restaurant = app.find_restaurant(restaurant_id)
        self._items_col = ft.Column(spacing=10)
        self._cart_bar = ft.Container(
            padding=14, border_radius=14,
            gradient=gradient([PRIMARY, SECONDARY]),
            shadow=ft.BoxShadow(blur_radius=18, color=ft.Colors.with_opacity(0.35, SECONDARY), offset=ft.Offset(0, 8)),
            on_click=self._go_to_cart,
            visible=False,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=14),
                    ft.Text("", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=14),
                ],
            ),
        )

    async def _go_to_cart(self, e) -> None:
        await self.page.push_route("/cart")

    def _render(self) -> None:
        """Redesenha a lista de itens E a barra flutuante do carrinho."""
        self._items_col.controls = [self._item_row(i) for i in self._restaurant.menu]
        count = self.app.cart_count
        self._cart_bar.visible = count > 0
        label = "item" if count == 1 else "itens"
        self._cart_bar.content.controls[0].value = f"🛒 Ver carrinho ({count} {label})"
        self._cart_bar.content.controls[1].value = f"R$ {self.app.cart_subtotal:.2f}"
        self.page.update()

    def _show_item_details(self, item) -> None:
        """Diálogo com descrição completa, preço e seletor de quantidade,
        para o usuário decidir com calma antes de confirmar."""
        qty_box = {"n": max(1, self.app.qty_of(item.id))}
        qty_text = ft.Text(str(qty_box["n"]), weight=ft.FontWeight.BOLD, size=16)

        def dec(e):
            if qty_box["n"] > 1:
                qty_box["n"] -= 1
                qty_text.value = str(qty_box["n"])
                dialog.update()

        def inc(e):
            qty_box["n"] += 1
            qty_text.value = str(qty_box["n"])
            dialog.update()

        def close(e):
            self.page.pop_dialog()

        async def confirm_add(e):
            # Aplica a quantidade final escolhida (em vez de só somar +1).
            current = self.app.qty_of(item.id)
            delta = qty_box["n"] - current
            if delta > 0:
                for _ in range(delta):
                    await self.app.add_item(self._restaurant, item)
            elif delta < 0:
                await self.app.change_qty(item.id, delta)
            self.page.pop_dialog()
            self._render()

        dialog = ft.AlertDialog(
            title=ft.Row(spacing=10, controls=[
                ft.Container(width=44, height=44, border_radius=12, bgcolor=ft.Colors.with_opacity(0.08, PRIMARY), alignment=ft.Alignment.CENTER, content=ft.Text(item.emoji, size=22)),
                ft.Text(item.name, weight=ft.FontWeight.BOLD, size=16),
            ]),
            content=ft.Column(
                spacing=14, width=260,
                controls=[
                    ft.Text(item.description, size=13, color=MUTED),
                    ft.Text(f"R$ {item.price:.2f}", size=18, weight=ft.FontWeight.BOLD, color=PRIMARY),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Text("Quantidade", size=13, color=MUTED),
                        ft.Row(spacing=10, controls=[
                            circle_icon_button(ft.Icons.REMOVE_ROUNDED, filled=False, on_click=dec, icon_size=16),
                            qty_text,
                            circle_icon_button(ft.Icons.ADD_ROUNDED, filled=True, on_click=inc, icon_size=16),
                        ]),
                    ]),
                ],
            ),
            actions=[ft.TextButton("Cancelar", on_click=close), gradient_button("Adicionar ao carrinho", on_click=confirm_add)],
        )
        self.page.show_dialog(dialog)

    def _item_row(self, item) -> ft.Container:
        qty = self.app.qty_of(item.id)

        async def add(e):
            await self.app.add_item(self._restaurant, item)
            self._render()

        async def remove(e):
            await self.app.change_qty(item.id, -1)
            self._render()

        top_info = ft.Container(
            # Imagem + nome/descrição/preço abrem os detalhes ao toque —
            # os controles de quantidade (linha separada abaixo) ficam
            # fora daqui, então não abrem o diálogo sem querer.
            on_click=lambda e, it=item: self._show_item_details(it),
            content=ft.Row(
                spacing=12, vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Container(width=52, height=52, border_radius=14, bgcolor=ft.Colors.with_opacity(0.08, PRIMARY), alignment=ft.Alignment.CENTER, content=ft.Text(item.emoji, size=26)),
                    ft.Column(
                        expand=True, spacing=2,
                        controls=[
                            # Nome/descrição ocupam a largura inteira do
                            # cartão (não dividem espaço com os controles
                            # de quantidade) — evita quebrar no meio da
                            # palavra quando a quantidade tem 2+ dígitos.
                            ft.Text(item.name, weight=ft.FontWeight.BOLD, size=14, color=TEXT_DARK, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(item.description, size=12, color=MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"R$ {item.price:.2f}", size=13, weight=ft.FontWeight.BOLD, color=PRIMARY),
                        ],
                    ),
                ],
            ),
        )

        if qty:
            qty_controls = ft.Row(spacing=6, controls=[
                circle_icon_button(ft.Icons.REMOVE_ROUNDED, filled=False, on_click=remove),
                ft.Text(str(qty), weight=ft.FontWeight.BOLD, size=14),
                circle_icon_button(ft.Icons.ADD_ROUNDED, filled=True, on_click=add),
            ])
        else:
            qty_controls = circle_icon_button(ft.Icons.ADD_ROUNDED, filled=True, on_click=add)

        return ft.Container(
            padding=12, border_radius=16, bgcolor=SURFACE, shadow=CARD_SHADOW,
            content=ft.Column(spacing=8, controls=[top_info, ft.Row(alignment=ft.MainAxisAlignment.END, controls=[qty_controls])]),
        )

    def _not_found_view(self) -> ft.View:
        return ft.View(
            route=self.page.route, bgcolor=BG,
            controls=[ft.SafeArea(content=ft.Column(controls=[
                ft.AppBar(title=ft.Text("Restaurante não encontrado"), bgcolor=PRIMARY),
                empty_state(ft.Icons.ERROR_OUTLINE_ROUNDED, "Volte e tente outro restaurante.", "Voltar ao início", lambda e: self.page.navigate("/")),
            ]))],
        )

    def build(self) -> ft.View:
        if self._restaurant is None:
            return self._not_found_view()

        restaurant = self._restaurant
        self._render()

        header = ft.Container(
            padding=ft.Padding(20, 24, 20, 28),
            gradient=gradient(restaurant.banner_colors),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.START, spacing=10,
                controls=[
                    ft.Container(width=72, height=72, border_radius=20, bgcolor=ft.Colors.with_opacity(0.25, ft.Colors.WHITE), alignment=ft.Alignment.CENTER, content=ft.Text(restaurant.emoji, size=38)),
                    ft.Text(restaurant.name, size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Row(spacing=8, controls=[
                        white_pill(f"⭐ {restaurant.rating}"),
                        white_pill(restaurant.delivery_time),
                        white_pill("Entrega grátis" if restaurant.delivery_fee == 0 else f"Taxa R$ {restaurant.delivery_fee:.2f}"),
                    ]),
                ],
            ),
        )

        return ft.View(
            route=self.page.route, padding=0, bgcolor=BG,
            controls=[
                ft.SafeArea(
                    expand=True,
                    content=ft.Column(
                        expand=True, spacing=0,
                        controls=[
                            ft.AppBar(
                                title=ft.Text(restaurant.name, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                bgcolor=restaurant.banner_colors[1],
                                leading=ft.IconButton(ft.Icons.ARROW_BACK_ROUNDED, icon_color=ft.Colors.WHITE, on_click=lambda e: self.page.navigate("/")),
                            ),
                            ft.Column(expand=True, spacing=0, scroll=ft.ScrollMode.AUTO, controls=[header, ft.Container(padding=16, content=self._items_col)]),
                            ft.Container(padding=16, content=self._cart_bar),
                        ],
                    ),
                )
            ],
        )


# ==========================================================================
# 7) CartView — ajustar quantidades e ver o resumo de valores
# ==========================================================================
class CartView(BaseView):
    def __init__(self, page: ft.Page, app):
        super().__init__(page, app)
        self._lines_col = ft.Column(spacing=10)
        self._summary = ft.Column()

    def _cart_line_card(self, line) -> ft.Container:
        async def dec(e, item_id=line.item_id):
            await self.app.change_qty(item_id, -1)
            self._render()

        async def inc(e, item_id=line.item_id):
            await self.app.change_qty(item_id, 1)
            self._render()

        return ft.Container(
            padding=12, border_radius=16, bgcolor=SURFACE, shadow=CARD_SHADOW,
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Container(width=44, height=44, border_radius=12, bgcolor=ft.Colors.with_opacity(0.08, PRIMARY), alignment=ft.Alignment.CENTER, content=ft.Text(line.emoji, size=22)),
                    ft.Column(expand=True, spacing=2, controls=[
                        ft.Text(line.name, weight=ft.FontWeight.BOLD, size=14, color=TEXT_DARK),
                        ft.Text(f"R$ {line.price:.2f} un.", size=12, color=MUTED),
                    ]),
                    circle_icon_button(ft.Icons.REMOVE_ROUNDED, filled=False, on_click=dec, icon_size=16),
                    ft.Text(str(line.qty), weight=ft.FontWeight.BOLD),
                    circle_icon_button(ft.Icons.ADD_ROUNDED, filled=True, on_click=inc, icon_size=16),
                ],
            ),
        )

    def _render(self) -> None:
        if not self.app.cart:
            self._lines_col.controls = [empty_state(ft.Icons.SHOPPING_CART_OUTLINED, "Seu carrinho está vazio.", "Explorar restaurantes", lambda e: self.page.navigate("/"))]
            self._summary.controls = []
            self._refresh_nav(self._nav_container, "cart")
            self.page.update()
            return

        self._lines_col.controls = [self._cart_line_card(line) for line in self.app.cart]
        fee = self.app.delivery_fee
        total = self.app.cart_subtotal + fee
        self._summary.controls = [
            ft.Container(height=6),
            ft.Container(
                padding=16, border_radius=16, bgcolor=SURFACE, shadow=CARD_SHADOW,
                content=ft.Column(spacing=10, controls=[
                    row_kv("Subtotal", f"R$ {self.app.cart_subtotal:.2f}"),
                    row_kv("Taxa de entrega", "Grátis" if fee == 0 else f"R$ {fee:.2f}"),
                    ft.Divider(height=1),
                    row_kv("Total", f"R$ {total:.2f}", bold=True),
                ]),
            ),
            ft.Container(height=14),
            gradient_button("Ir para o checkout", icon=ft.Icons.ARROW_FORWARD_ROUNDED, on_click=lambda e: self.page.navigate("/checkout")),
        ]
        self._refresh_nav(self._nav_container, "cart")
        self.page.update()

    def build(self) -> ft.View:
        appbar = branded_appbar("Seu carrinho")
        body = [ft.Container(padding=16, content=ft.Column(controls=[self._lines_col, self._summary]))]
        view, self._nav_container = self._scaffold("/cart", "cart", appbar, body)
        self._render()
        return view


# ==========================================================================
# 8) CheckoutView — endereço, pagamento e confirmação (mock)
# ==========================================================================
class CheckoutView(BaseView):
    def build(self) -> ft.View:
        address_field = ft.TextField(
            label="Endereço de entrega", value=self.app.address, multiline=True,
            border_radius=12, filled=True, fill_color=SURFACE,
            border_color=ft.Colors.TRANSPARENT, focused_border_color=PRIMARY,
        )
        payment = ft.RadioGroup(
            value="Cartão",
            content=ft.Column(controls=[
                ft.Radio(value="Cartão", label="💳 Cartão de crédito"),
                ft.Radio(value="Pix", label="🔑 Pix"),
                ft.Radio(value="Dinheiro", label="💵 Dinheiro"),
            ]),
        )
        items_summary = ft.Column(controls=[ft.Text(f"{c.qty}x {c.name}", size=13, color=TEXT_DARK) for c in self.app.cart])
        total = self.app.cart_subtotal + self.app.delivery_fee

        def clear_address_error(e):
            if address_field.error:
                address_field.error = None
                self.page.update()

        address_field.on_change = clear_address_error

        async def confirm(e):
            if not address_field.value:
                address_field.error = "Informe o endereço de entrega"
                self.page.update()
                self.page.show_dialog(ft.SnackBar(ft.Text("⚠️ Informe o endereço de entrega para continuar.")))
                return
            if not self.app.cart:
                self.page.show_dialog(ft.SnackBar(ft.Text("Seu carrinho está vazio.")))
                return
            restaurant = self.app.find_restaurant(self.app.cart_restaurant_id)
            self.app.address = address_field.value
            await self.app.place_order(restaurant.name if restaurant else "Restaurante", address_field.value, payment.value)
            self.page.show_dialog(ft.SnackBar(ft.Text("✅ Pedido confirmado! Acompanhe em 'Pedidos'.")))
            await self.page.push_route("/orders")

        def section(title: str, content) -> ft.Container:
            return ft.Container(
                padding=16, border_radius=16, bgcolor=SURFACE, shadow=CARD_SHADOW,
                content=ft.Column(spacing=10, controls=[ft.Text(title, weight=ft.FontWeight.BOLD, size=14), content]),
            )

        appbar = ft.AppBar(
            title=ft.Text("Finalizar pedido", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            bgcolor=PRIMARY,
            leading=ft.IconButton(ft.Icons.ARROW_BACK_ROUNDED, icon_color=ft.Colors.WHITE, on_click=lambda e: self.page.navigate("/cart")),
        )
        body = [
            ft.Container(
                padding=16,
                content=ft.Column(spacing=14, controls=[
                    section("Resumo do pedido", items_summary),
                    section("Endereço de entrega", address_field),
                    section("Forma de pagamento", payment),
                    ft.Container(
                        padding=16, border_radius=16, bgcolor=SURFACE, shadow=CARD_SHADOW,
                        content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                            ft.Text("Total", size=16, weight=ft.FontWeight.BOLD, color=TEXT_DARK),
                            ft.Text(f"R$ {total:.2f}", size=18, weight=ft.FontWeight.BOLD, color=PRIMARY),
                        ]),
                    ),
                    gradient_button("Confirmar pedido (mock)", icon=ft.Icons.CHECK_CIRCLE_ROUNDED, on_click=confirm),
                ]),
            )
        ]
        return ft.View(
            route="/checkout", padding=0, bgcolor=BG,
            controls=[ft.SafeArea(expand=True, content=ft.Column(expand=True, spacing=0, controls=[appbar, ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=body)]))],
        )


# ==========================================================================
# 9) OrdersView — histórico de pedidos (avançar status / excluir)
# ==========================================================================
class OrdersView(BaseView):
    def __init__(self, page: ft.Page, app):
        super().__init__(page, app)
        self._orders_col = ft.Column(spacing=12)

    def _order_card(self, order) -> ft.Container:
        bg, fg = STATUS_COLORS.get(order.status, ("#EEEEEE", "#444444"))
        next_status = self.app.next_status(order.id)

        async def advance(e):
            await self.app.advance_order_status(order.id)
            self._render()

        def ask_delete(e):
            def do_delete(e2):
                self.page.pop_dialog()

                async def _delete():
                    await self.app.delete_order(order.id)
                    self._render()

                self.page.run_task(_delete)

            def cancel(e2):
                self.page.pop_dialog()

            confirm_dialog = ft.AlertDialog(
                title=ft.Text("Excluir pedido?"),
                content=ft.Text(f"Tem certeza que deseja excluir o pedido de \"{order.restaurant_name}\"? Essa ação não pode ser desfeita."),
                actions=[
                    ft.TextButton("Cancelar", on_click=cancel),
                    ft.TextButton("Excluir", on_click=do_delete, style=ft.ButtonStyle(color=ft.Colors.RED_600)),
                ],
            )
            self.page.show_dialog(confirm_dialog)

        action_buttons = [
            ft.TextButton("Excluir", icon=ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=ft.Colors.RED_400, style=ft.ButtonStyle(color=ft.Colors.RED_400), on_click=ask_delete),
        ]
        if next_status:
            action_buttons.append(
                ft.IconButton(
                    ft.Icons.ARROW_FORWARD_ROUNDED, icon_size=16, icon_color=ft.Colors.WHITE, bgcolor=PRIMARY,
                    style=ft.ButtonStyle(shape=ft.CircleBorder()), tooltip=f'Avançar para "{next_status}"', on_click=advance,
                )
            )

        return ft.Container(
            padding=14, border_radius=16, bgcolor=SURFACE, shadow=CARD_SHADOW,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START, controls=[
                        ft.Text(order.restaurant_name, weight=ft.FontWeight.BOLD, size=15, color=TEXT_DARK, expand=True),
                        ft.Container(padding=ft.Padding(9, 3, 9, 3), border_radius=20, bgcolor=bg, content=ft.Text(order.status, size=11, color=fg, weight=ft.FontWeight.BOLD)),
                    ]),
                    ft.Text(order.created_at, size=12, color=MUTED),
                    ft.Text(", ".join(f"{i['qty']}x {i['name']}" for i in order.items), size=12, color="#444444"),
                    ft.Divider(height=1),
                    # Total e botões em linhas separadas — assim um total
                    # muito alto nunca empurra os botões para fora do cartão.
                    ft.Text(f"Total: R$ {order.total:.2f}", weight=ft.FontWeight.BOLD, size=15, color=PRIMARY),
                    ft.Row(alignment=ft.MainAxisAlignment.END, spacing=6, controls=action_buttons),
                ],
            ),
        )

    def _render(self) -> None:
        orders = self.app.orders
        if not orders:
            self._orders_col.controls = [empty_state(ft.Icons.RECEIPT_LONG_OUTLINED, "Você ainda não fez nenhum pedido.", "Fazer meu primeiro pedido", lambda e: self.page.navigate("/"))]
        else:
            self._orders_col.controls = [self._order_card(o) for o in orders]
        self._refresh_nav(self._nav_container, "orders")
        self.page.update()

    def build(self) -> ft.View:
        appbar = branded_appbar("Meus pedidos")
        body = [ft.Container(padding=16, content=self._orders_col)]
        view, self._nav_container = self._scaffold("/orders", "orders", appbar, body)
        self._render()
        return view
