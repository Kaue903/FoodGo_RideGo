"""
controller.py — camada CONTROLLER do padrão MVC.

Uma única classe, `AppController`, cuidando de TODA a regra de negócio
do app: consultar/filtrar restaurantes, gerenciar o carrinho, gerenciar
o histórico de pedidos e persistir tudo isso em disco. As Views
(`views.py`) só chamam métodos daqui — nunca calculam totais, nunca
leem/gravam SharedPreferences diretamente.

ENCAPSULAMENTO: o estado (`_cart`, `_orders`, etc.) fica em atributos
"privados" (prefixo `_`); o resto do app só acessa através de
propriedades (`cart`, `cart_count`, ...) e métodos (`add_item`,
`change_qty`, ...), que sabem manter tudo consistente (ex.: salvar em
disco depois de cada mudança).

--------------------------------------------------------------------------
SOBRE O "SALVAMENTO EM SEGUNDO PLANO" (fire-and-forget)
--------------------------------------------------------------------------
Cada ação do carrinho (adicionar item, +1, -1) precisa:
    1) mudar os dados em memória (o que a tela mostra), e
    2) gravar essa mudança em disco, para não se perder ao fechar o app.

Se o passo 2 fosse sempre feito com `await` (esperando terminar antes de
liberar a tela), o app pareceria "lento" a cada toque, porque gravar em
disco (ou no navegador, na versão web) pode levar um tempinho perceptível.
A solução: o passo 1 é imediato, e o passo 2 roda "por trás", disparado
com `asyncio.create_task(...)` em vez de `await` — a tela já pode ser
redesenhada enquanto o salvamento termina sozinho (ver `_fire_and_forget`).
"""
import asyncio
import json
import uuid
from datetime import datetime

import flet as ft

from models import RESTAURANTS, CartLine, Order, Restaurant

CART_KEY = "foodgo_cart"
ORDERS_KEY = "foodgo_orders"
DELIVERY_FEE_DEFAULT = 0.0

# Sequência de status que o botão "Avançar status" percorre, nessa ordem.
STATUS_FLOW = ["Em preparo", "A caminho", "Entregue"]


class AppController:
    """Guarda o carrinho e o histórico de pedidos em memória, oferece
    consulta/filtro de restaurantes, e cuida de ler/gravar tudo isso no
    armazenamento local do dispositivo."""

    def __init__(self):
        # ENCAPSULAMENTO: atributos "privados" — só os métodos desta
        # classe devem alterá-los diretamente.
        self._restaurants: list[Restaurant] = RESTAURANTS
        self._cart: list[CartLine] = []
        self._orders: list[Order] = []
        self._delivery_fee: float = DELIVERY_FEE_DEFAULT
        self._address: str = ""
        self._prefs: ft.SharedPreferences | None = None

    def bind(self, prefs: ft.SharedPreferences) -> None:
        """Conecta este controller ao serviço de armazenamento local do
        Flet. Precisa ser chamado uma vez, no início do app (veja main.py)."""
        self._prefs = prefs

    @staticmethod
    def _fire_and_forget(coro) -> None:
        """Executa uma tarefa assíncrona (ex.: salvar em disco) sem fazer
        a tela esperar por ela — veja a explicação completa no topo do
        arquivo. Qualquer erro é apenas registrado no console."""
        task = asyncio.create_task(coro)

        def _log_if_failed(t: asyncio.Task) -> None:
            error = t.exception()
            if error is not None:
                print(f"[FoodGo] Falha ao salvar dados em segundo plano: {error}")

        task.add_done_callback(_log_if_failed)

    # ------------------------------------------------------------------
    # Persistência (carregar/gravar carrinho e pedidos)
    # ------------------------------------------------------------------
    async def load(self) -> None:
        """Carrega carrinho e pedidos salvos anteriormente (se existirem).
        Chamado uma única vez, ao abrir o app."""
        raw_cart = await self._prefs.get(CART_KEY)
        raw_orders = await self._prefs.get(ORDERS_KEY)
        try:
            self._cart = [CartLine.from_dict(d) for d in json.loads(raw_cart)] if raw_cart else []
        except (json.JSONDecodeError, TypeError):
            self._cart = []  # dado salvo corrompido/antigo — melhor começar do zero
        try:
            self._orders = [Order.from_dict(d) for d in json.loads(raw_orders)] if raw_orders else []
        except (json.JSONDecodeError, TypeError):
            self._orders = []

    async def _save_cart(self) -> None:
        await self._prefs.set(CART_KEY, json.dumps([c.to_dict() for c in self._cart]))

    async def _save_orders(self) -> None:
        await self._prefs.set(ORDERS_KEY, json.dumps([o.to_dict() for o in self._orders]))

    # ------------------------------------------------------------------
    # Restaurantes (consulta/filtro — dados fictícios de models.py)
    # ------------------------------------------------------------------
    def list_restaurants(self) -> list[Restaurant]:
        return list(self._restaurants)

    def list_categories(self) -> list[str]:
        """Categorias para os chips de filtro. "Todos" sempre primeiro,
        depois em ordem alfabética."""
        return ["Todos"] + sorted({r.category for r in self._restaurants})

    def find_restaurant(self, restaurant_id: str) -> Restaurant | None:
        return next((r for r in self._restaurants if r.id == restaurant_id), None)

    def search_restaurants(self, text: str, category: str) -> list[Restaurant]:
        """Filtra restaurantes por texto (nome/categoria) e por categoria
        selecionada ("Todos" não filtra por categoria). Usado pela busca
        em tempo real da tela inicial."""
        needle = (text or "").lower().strip()

        def matches(r: Restaurant) -> bool:
            category_ok = category == "Todos" or r.category == category
            text_ok = needle in r.name.lower() or needle in r.category.lower()
            return category_ok and text_ok

        return [r for r in self._restaurants if matches(r)]

    # ------------------------------------------------------------------
    # Carrinho
    # ------------------------------------------------------------------
    @property
    def cart(self) -> list[CartLine]:
        """Devolve uma CÓPIA da lista interna (encapsulamento: ninguém
        de fora consegue alterar o carrinho de verdade por engano)."""
        return list(self._cart)

    @property
    def cart_count(self) -> int:
        return sum(line.qty for line in self._cart)

    @property
    def cart_subtotal(self) -> float:
        return round(sum(line.line_total for line in self._cart), 2)

    @property
    def cart_restaurant_id(self) -> str | None:
        """Carrinho é sempre de um único restaurante por vez."""
        return self._cart[0].restaurant_id if self._cart else None

    @property
    def delivery_fee(self) -> float:
        return self._delivery_fee

    @property
    def address(self) -> str:
        return self._address

    @address.setter
    def address(self, value: str) -> None:
        self._address = value

    def qty_of(self, item_id: str) -> int:
        line = next((c for c in self._cart if c.item_id == item_id), None)
        return line.qty if line else 0

    async def add_item(self, restaurant: Restaurant, item) -> None:
        """Adiciona 1 unidade de um item ao carrinho (ou soma +1 se já
        estiver lá)."""
        # Carrinho é de um restaurante por vez — trocar de restaurante esvazia o carrinho.
        if self._cart and self.cart_restaurant_id != restaurant.id:
            self._cart.clear()
        line = next((c for c in self._cart if c.item_id == item.id), None)
        if line:
            line.qty += 1
        else:
            self._cart.append(CartLine(restaurant.id, item.id, item.name, item.price, item.emoji, 1))
        self._fire_and_forget(self._save_cart())

    async def change_qty(self, item_id: str, delta: int) -> None:
        """Aumenta/diminui a quantidade de um item já no carrinho (remove
        a linha se a quantidade chegar a zero)."""
        line = next((c for c in self._cart if c.item_id == item_id), None)
        if not line:
            return
        line.qty += delta
        if line.qty <= 0:
            self._cart.remove(line)
        self._fire_and_forget(self._save_cart())

    async def clear_cart(self) -> None:
        """Esvazia o carrinho por completo (usado após finalizar um
        pedido). Usa `await` de verdade (ação única, não uma sequência de
        toques rápidos) para garantir que salvou antes de prosseguir."""
        self._cart.clear()
        await self._save_cart()

    # ------------------------------------------------------------------
    # Pedidos
    # ------------------------------------------------------------------
    @property
    def orders(self) -> list[Order]:
        return list(self._orders)

    def next_status(self, order_id: str) -> str | None:
        """Devolve qual seria o próximo status de um pedido (ou None se
        ele já estiver em 'Entregue', fim da linha)."""
        order = next((o for o in self._orders if o.id == order_id), None)
        if order is None or order.status not in STATUS_FLOW:
            return None
        idx = STATUS_FLOW.index(order.status)
        if idx + 1 >= len(STATUS_FLOW):
            return None
        return STATUS_FLOW[idx + 1]

    async def place_order(self, restaurant_name: str, address: str, payment: str) -> Order:
        """Transforma o carrinho atual em um pedido confirmado, salva no
        histórico e esvazia o carrinho. Usado na tela de checkout."""
        order = Order(
            id=uuid.uuid4().hex[:8],
            restaurant_name=restaurant_name,
            items=[c.to_dict() for c in self._cart],
            subtotal=self.cart_subtotal,
            delivery_fee=self._delivery_fee,
            total=round(self.cart_subtotal + self._delivery_fee, 2),
            address=address,
            payment=payment,
            created_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
        )
        self._orders.insert(0, order)
        await self._save_orders()
        await self.clear_cart()
        return order

    async def advance_order_status(self, order_id: str) -> None:
        """Avança manualmente o status de um pedido para o próximo da
        sequência (Em preparo -> A caminho -> Entregue)."""
        new_status = self.next_status(order_id)
        if new_status is None:
            return
        order = next((o for o in self._orders if o.id == order_id), None)
        order.status = new_status
        self._fire_and_forget(self._save_orders())

    async def delete_order(self, order_id: str) -> None:
        """Remove um pedido do histórico permanentemente."""
        self._orders = [o for o in self._orders if o.id != order_id]
        self._fire_and_forget(self._save_orders())