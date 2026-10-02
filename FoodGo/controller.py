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

from models import RESTAURANTS, CartItem, Order, Restaurant

CART_KEY = "foodgo_cart"
ORDERS_KEY = "foodgo_orders"
DELIVERY_FEE = 0.0  # taxa fixa de entrega, em reais
DELIVERY_FEE_DEFAULT = DELIVERY_FEE

# Sequencia de status que o botão "Avançar status" percorre, nessa ordem.
STATUS_FLOW = ["Em preparo", "Saiu para entrega", "Entregue"]

class AppController:
    """
    Controlador do app, camada CONTROLLER do padrão MVC.

    Responsável por:
        - consultar/filtrar restaurantes,
        - gerenciar o carrinho,
        - gerenciar o histórico de pedidos,
        - persistir tudo isso em disco.
    """

    def __init__(self):
        self._restaurants: list[Restaurant] = RESTAURANTS
        self._cart: list[CartItem] = []
        self._orders: list[Order] = []
        self._delivery_fee: float = DELIVERY_FEE_DEFAULT
        self._address: str = ""
        self._prefs: ft.SharedPreferences  | None = None

    def bind(self, prefs: ft.SharedPreferences) -> None:
        """
        Vincula o controlador a um objeto SharedPreferences, para
        poder ler/gravar dados persistentes (carrinho e histórico de pedidos).
        """
        self._prefs = prefs
    @staticmethod
    def _fire_and_forget(coro) -> None:
        """
        Dispara uma coroutine em segundo plano, sem esperar terminar.

        Útil para salvar dados em disco sem travar a tela.
        """
        task = asyncio.create_task(coro)
        task.add_done_callback(_log_if_failed)
        def _log_if_failed(t: asyncio.Task) -> None:
            error = t.exception()
            if error is not None:
                print(f"Erro ao salvar em disco: {error}")
        task.add_done_callback(_log_if_failed)

    #--------Pestistencia (carregar/gravar carrinho e pedidos)--------
    async def load(self) -> None:
        """
        Carrega carrinho e histórico de pedidos do SharedPreferences.
        """
        raw_cart = await self._prefs.get(CART_KEY)
        raw_orders = await self._prefs.get(ORDERS_KEY)
        try:
            self._cart = [CartItem.from_dict(d) for d in json.loads(raw_cart or "[]")] if raw_cart else []
        except(json.JSONDecodeError, TypeError):
            self._cart = []
        try:
            self._orders = [Order.from_dict(d) for d in json.loads(raw_orders or "[]")] if raw_orders else []
        except(json.JSONDecodeError, TypeError):
            self._orders = []

    async def save_cart(self) -> None:
        await self._prefs.set(CART_KEY, json.dumps([item.to_dict() for item in self._cart]))

    async def save_orders(self) -> None:
        await self._prefs.set(ORDERS_KEY, json.dumps([order.to_dict() for order in self._orders]))

    #Restaurantes (consulta/filtro - dados fictícios d emodels.py)
    def list_restaurantes(self) -> list[Restaurant]:
        """
        Retorna a lista de restaurantes disponíveis.
        """
        return self._restaurants

    def list_categories(self) -> list[str]:
        """
        Retorna a lista de categorias de restaurantes disponíveis.
        """
        return["Todos"] + sorted(set(r.category for r in self._restaurants))

    def find_restaurant(self, restaurant_id: str) -> Restaurant | None:
        """
        Retorna o restaurante com o ID fornecido, ou None se não existir.
        """
        return next((r for r in self._restaurants if r.id == restaurant_id), None)

    def search_restaurants(self, text: str, category: str | None) -> list[Restaurant]:
        """
        Retorna a lista de restaurantes cujo nome contém a string `query`
        (case-insensitive).
        """
        needle = (text or "").lower().strip()

        def matches(r: Restaurant) -> bool:
            category_ok = category == "Todos" or r.category == category
            text_ok = needle in r.name.lower() or needle in r.category.lower()
            return text_ok and category_ok

        return [r for r in self._restaurants if matches(r)]

    # Carrinho (adicionar/remover itens, calcular totais, etc.)
    @property
    def cart(self) -> list[CartItem]:
        """
        Retorna a lista de itens do carrinho.
        """
        return self._cart

    @property
    def cart_count(self) -> int:
        """
        Retorna a quantidade total de itens no carrinho.
        """
        return sum(item.qty for item in self._cart)

    @property
    def cart_count(self) -> int:
        """
        Retorna a quantidade total de itens no carrinho.
        """
        return sum(item.qty for item in self._cart)

    @property
    def cart_subtotal(self) -> float:
        """
        Retorna o subtotal do carrinho (soma dos preços dos itens, sem taxa de entrega).
        """
        return round(sum(line.line_total for line in self._cart), 2)

    @property
    def cart_restaurant_id(self) -> str | None:
        """
        Retorna o ID do restaurante ao qual os itens no carrinho pertencem.
        """
        if self._cart:
            return self._cart[0].restaurant_id
        return None

    @property
    def delivery_fee(self) -> float:
        """
        Retorna a taxa de entrega do carrinho.
        """
        return self._delivery_fee

    @property
    def address(self) -> float:
        """
        Retorna o endereço de entrega do carrinho.
        """
        return self._address

    @address.setter
    def address(self, value: str) -> None:
        """
        Define o endereço de entrega do carrinho.
        """
        self._address = value

    def qty_off(self, item_id: str) -> int:
        """
        Retorna a quantidade do item com o ID fornecido no carrinho.
        """
        line = next((line for line in self._cart if line.item_id == item_id), None)
        return line.qty if line else 0

    async def add_item(self, restaurant: Restaurant, item) -> None:
        """
        Adiciona um item ao carrinho. Se o item já estiver no carrinho,
        apenas aumenta a quantidade em 1.

        Se o carrinho já tiver itens de outro restaurante, limpa o
        carrinho antes de adicionar o novo item.
        """
        if self._cart and self.cart_restaurant_id != restaurant.id:
            self._cart.clear()
        line = next((line for line in self._cart if line.item_id == item.id), None)
        if line:
            line.qty += 1
        else:
            self._cart.append(CartItem(
                restaurant_id=restaurant.id,
                item_id=item.id,
                name=item.name,
                price=item.price,
                qty=1
            ))
        self._fire_and_forget(self.save_cart())


    async def change_qty(self, item_id: str, new_qty: int) -> None:
        """
        Altera a quantidade de um item no carrinho. Se a nova quantidade for
        0, remove o item do carrinho.
        """
        line = next((line for line in self._cart if line.item_id == item_id), None)
        if not line:
            return
        line.qty += delta
        if line.qty <= 0:
            self._cart.remove(line)
        self._fire_and_forget(self.save_cart())

    async def clear_cart(self) -> None:
        """
        Limpa o carrinho.
        """
        self._cart.clear()
        self._fire_and_forget(self.save_cart())

    #-------Pedidos (histórico, status, etc.)--------
    @property
    def orders(self) -> list[Order]:
        """
        Retorna a lista de pedidos do histórico.
        """
        return self._orders

    def next_status(self, order_id: str) -> str | None:
        """
        Avança o status do pedido com o ID fornecido para o próximo status
        na sequência definida em STATUS_FLOW.
        """
        order = next((o for o in self._orders if o.id == order_id), None)
        if order is None or order.status == STATUS_FLOW[-1]:
            return None
        idx = STATUS_FLOW.index(order.status)
        if idx + 1 < len(STATUS_FLOW):
            return STATUS_FLOW[idx + 1]
        return None

    async def place_order(self, resturant_name: str, address: str, payment: str) -> Order:
        """
        Cria um novo pedido a partir do carrinho atual, adiciona ao histórico
        e limpa o carrinho.
        """
        order = Order(
            id=str(uuid.uuid4()),
            restaurant_name=resturant_name,
            address=address,
            payment=payment,
            items=self._cart.copy(),
            subtotal=self.cart_subtotal,
            delivery_fee=self.delivery_fee,
            total=self.cart_subtotal + self.delivery_fee,
            status=STATUS_FLOW[0],
            created_at=datetime.now()
        )
        self._orders.append(order)
        self._cart.clear()
        self._fire_and_forget(self.save_cart())
        self._fire_and_forget(self.save_orders())
        return order

    async def advance_order_status(self, order_id: str) -> None:
        """
        Avança o status do pedido com o ID fornecido para o próximo status
        na sequência definida em STATUS_FLOW.
        """
        order = next((o for o in self._orders if o.id == order_id), None)
        if order is None:
            return
        new_status = self.next_status(order_id)
        if new_status is None:
            return
        order.status = new_status
        self._fire_and_forget(self.save_orders())

    async def delete_order(self, order_id: str) -> None:
        """
        Remove o pedido com o ID fornecido do histórico.
        """
        self._orders = [o for o in self._orders if o.id != order_id]
        self._fire_and_forget(self.save_orders())